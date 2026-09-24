"""Persist MediaMTX publisher identities and render their exact path permissions."""

from __future__ import annotations

import base64
import copy
import json
import os
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REGISTRY = Path(os.environ.get("MEDIA_REGISTRY_FILE", "/media-config/publishers.json"))
CONFIG = Path(os.environ.get("MEDIA_CONFIG_FILE", "/media-config/mediamtx.yml"))
TEMPLATE = Path(os.environ.get("MEDIA_TEMPLATE_FILE", "/app/mediamtx-template.yml"))
PUBLISH_SECRET = Path(os.environ.get("SHARE_PUBLISH_PASSWORD_FILE", "/run/secrets/mediamtx_publish_password"))
READ_SECRET = Path(os.environ.get("MEDIA_READ_PASSWORD_FILE", "/run/secrets/mediamtx_read_password"))
API_SECRET = Path(os.environ.get("MEDIA_API_PASSWORD_FILE", "/run/secrets/mediamtx_api_password"))
API_URL = os.environ.get("MEDIA_API_URL", "http://mediamtx:9997")
VIEWER_API_URL = os.environ.get("MEDIA_VIEWER_API_URL", "http://media-viewer:9997")
VIEWER_STATE = Path(os.environ.get("MEDIA_VIEWER_STATE_FILE", "/media-config/viewer_state.json"))
LOCK = threading.RLock()


def load() -> dict:
    if not REGISTRY.exists():
        return {"version": 1, "publishers": {}}
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("publishers"), dict):
        raise RuntimeError("Media publisher registry has an unsupported format")
    return data


def render_users(registry: dict) -> str:
    lines = []
    for key, item in sorted(registry["publishers"].items()):
        if not item["enabled"]:
            continue
        paths = sorted(set(item["paths"]))
        if not paths:
            continue
        lines.extend([f"  - user: {json.dumps(item['user'])}",
                      f"    pass: {json.dumps(item['password'])}", "    ips: []", "    permissions:"])
        for path in paths:
            lines.extend(["      - action: publish", f"        path: {json.dumps(path)}"])
    return "\n".join(lines)


def render_config(template: str, registry: dict, publish: str, read: str, api: str) -> str:
    replacements = {"__PUBLISH_PASSWORD__": json.dumps(publish),
                    "__READ_PASSWORD__": json.dumps(read),
                    "__API_PASSWORD__": json.dumps(api),
                    "__DYNAMIC_USERS__": render_users(registry)}
    for placeholder, value in replacements.items():
        if placeholder not in template:
            raise RuntimeError(f"MediaMTX template is missing {placeholder}")
        template = template.replace(placeholder, value)
    return template


def api_request(path: str, method: str = "GET", *, base_url: str | None = None,
                payload: dict | None = None) -> dict:
    credential = base64.b64encode(("tak-console:" + API_SECRET.read_text(encoding="ascii").strip()).encode()).decode()
    headers = {"Authorization": "Basic " + credential}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request((base_url or API_URL) + path, method=method, headers=headers, data=data)
    with urlopen(request, timeout=5) as response:
        payload = response.read()
    return json.loads(payload) if payload else {}


def apply(registry: dict) -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    rendered = render_config(template, registry,
                             PUBLISH_SECRET.read_text(encoding="ascii").strip(),
                             READ_SECRET.read_text(encoding="ascii").strip(),
                             API_SECRET.read_text(encoding="ascii").strip())
    previous = CONFIG.read_bytes()
    temporary = CONFIG.with_suffix(".next")
    temporary.write_text(rendered, encoding="utf-8", newline="\n")
    os.replace(temporary, CONFIG)
    try:
        expected = {item["user"]: set(item["paths"]) for item in registry["publishers"].values()
                    if item["enabled"] and item["paths"]}
        for _ in range(30):
            try:
                current = api_request("/v3/config/global/get")
                actual = {item["user"]: {permission["path"] for permission in item.get("permissions", [])
                                          if permission.get("action") == "publish"}
                          for item in current.get("authInternalUsers", [])
                          if item.get("user", "").startswith(("icu-", "device-"))}
                if expected == actual:
                    time.sleep(.3)
                    break
            except (OSError, HTTPError, URLError):
                pass
            time.sleep(.3)
        else:
            raise RuntimeError("MediaMTX did not load the updated publisher permissions")
        temporary = REGISTRY.with_suffix(".next")
        temporary.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, REGISTRY)
    except Exception:
        temporary = CONFIG.with_suffix(".rollback")
        temporary.write_bytes(previous)
        os.replace(temporary, CONFIG)
        raise


def ensure_squad(squad: str, path: str) -> dict:
    from icu_profiles import SQUADS
    if squad not in SQUADS or not path.startswith("live/") or not path.endswith("/VIDEO_1"):
        raise ValueError("Invalid squad or ICU path")
    with LOCK:
        registry = load()
        key = "squad:" + squad
        item = registry["publishers"].get(key)
        if item is None:
            item = {"kind": "squad", "name": squad.title(), "user": "icu-" + squad,
                    "password": secrets.token_urlsafe(30), "enabled": True, "paths": []}
        if not item["enabled"]:
            raise ValueError("This ICU squad is disabled")
        if any(path in existing["paths"] for owner, existing in registry["publishers"].items() if owner != key):
            raise ValueError("Stream Path is already assigned to another publisher")
        if path not in item["paths"]:
            item["paths"].append(path)
            registry["publishers"][key] = item
            apply(registry)
        return copy.deepcopy(item)


def create_device(name: str, path: str) -> tuple[str, dict]:
    from icu_profiles import SEGMENT
    if not 1 <= len(name.strip()) <= 80 or any(ord(char) < 32 for char in name) or not path.startswith("live/") or path.endswith("/") or len(path) > 160:
        raise ValueError("Invalid device name or Stream Path")
    if any(not SEGMENT.fullmatch(part) for part in path.split("/")[1:]):
        raise ValueError("Invalid device Stream Path")
    with LOCK:
        registry = load()
        if any(path in item["paths"] for item in registry["publishers"].values()):
            raise ValueError("Stream Path is already assigned")
        identity = secrets.token_hex(6)
        key = "device:" + identity
        item = {"kind": "device", "name": name.strip(), "user": "device-" + identity,
                "password": secrets.token_urlsafe(30), "enabled": True, "paths": [path]}
        registry["publishers"][key] = item
        apply(registry)
        return key, copy.deepcopy(item)


def update_many(keys: list[str], action: str) -> list[tuple[str, dict]]:
    if action not in {"disable", "reset"} or not 1 <= len(keys) <= 100 or len(set(keys)) != len(keys):
        raise ValueError("Invalid publisher selection")
    with LOCK:
        registry = load()
        for key in keys:
            if key not in registry["publishers"]:
                raise ValueError("Publisher selection changed; refresh the page")
        for key in keys:
            item = registry["publishers"][key]
            if action == "disable":
                item["enabled"] = False
            else:
                if not item["enabled"]:
                    raise ValueError("Cannot reset a disabled publisher")
                item["password"] = secrets.token_urlsafe(30)
        apply(registry)
        return [(key, copy.deepcopy(registry["publishers"][key])) for key in keys]


def active_paths() -> list[dict]:
    result = api_request("/v3/paths/list?itemsPerPage=500")
    return [item for item in result.get("items", []) if item.get("name", "").startswith("live/") and item.get("ready")]


def device_url(item: dict, scheme: str, host: str = "takbox.local") -> str:
    if item["kind"] != "device" or scheme not in {"rtsp", "rtsps"}:
        raise ValueError("Unsupported device publishing protocol")
    port = 8554 if scheme == "rtsp" else 8322
    user = quote(item["user"], safe="")
    password = quote(item["password"], safe="")
    path = quote(item["paths"][0], safe="/")
    return f"{scheme}://{user}:{password}@{host}:{port}/{path}"


def kick_publishers(users: set[str]) -> list[str]:
    result = api_request("/v3/rtsp/sessions/list?itemsPerPage=500")
    kicked = []
    for session in result.get("items", []):
        if session.get("user") in users and session.get("state") == "publish":
            api_request("/v3/rtsp/sessions/kick/" + session["id"], "POST")
            kicked.append(session["id"])
    return kicked


def viewer_status() -> dict:
    desired = json.loads(VIEWER_STATE.read_text(encoding="utf-8"))["enabled"]
    current = api_request("/v3/config/global/get", base_url=VIEWER_API_URL)
    sessions = api_request("/v3/webrtc/sessions/list?itemsPerPage=500", base_url=VIEWER_API_URL) if current.get("webrtc") else {"items": []}
    return {"desired": desired, "running": current.get("webrtc") is True,
            "sessions": len(sessions.get("items", [])), "internet_ready": False,
            "local_base": "http://takbox.local:8889"}


def set_viewer_enabled(enabled: bool) -> dict:
    if type(enabled) is not bool:
        raise ValueError("Invalid viewer switch state")
    with LOCK:
        current = api_request("/v3/config/global/get", base_url=VIEWER_API_URL)
        if current.get("webrtc") is not True:
            raise RuntimeError("Public WebRTC backend is not running")
        pending = VIEWER_STATE.with_suffix(".next")
        pending.write_text(json.dumps({"enabled": enabled}), encoding="utf-8")
        os.replace(pending, VIEWER_STATE)
        if not enabled:
            sessions = api_request("/v3/webrtc/sessions/list?itemsPerPage=500", base_url=VIEWER_API_URL)
            for session in sessions.get("items", []):
                api_request("/v3/webrtc/sessions/kick/" + session["id"], "POST",
                            base_url=VIEWER_API_URL)
            if api_request("/v3/webrtc/sessions/list?itemsPerPage=500",
                           base_url=VIEWER_API_URL).get("items"):
                raise RuntimeError("Public WebRTC sessions are still active")
        return viewer_status()
