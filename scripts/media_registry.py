"""Persist MediaMTX publisher identities and render their exact path permissions."""

from __future__ import annotations

import base64
import copy
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from icu_profiles import SEGMENT, SQUADS


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
NAMED_SQUADS = set(SQUADS) - {"default"}


def reserved_squad(path: str) -> str | None:
    parts = path.split("/")
    return parts[1] if len(parts) >= 2 and parts[0] == "live" and parts[1] in NAMED_SQUADS else None


def permission_paths(key: str, item: dict) -> list[str]:
    paths = set(item["paths"])
    if item["kind"] == "squad":
        squad = key.removeprefix("squad:")
        if squad in NAMED_SQUADS:
            paths.add(f"~^live/{squad}/(?:[A-Za-z0-9_-]+/)*VIDEO_1$")
    return sorted(paths)


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
        paths = permission_paths(key, item)
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
        expected = {item["user"]: set(permission_paths(key, item))
                    for key, item in registry["publishers"].items() if item["enabled"] and item["paths"]}
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
    if squad not in SQUADS or not path.startswith("live/") or not path.endswith("/VIDEO_1"):
        raise ValueError("Invalid squad or ICU path")
    if squad != "default" and not path.startswith(f"live/{squad}/"):
        raise ValueError("ICU Stream Path must stay within the selected squad")
    if any(not SEGMENT.fullmatch(part) for part in path.split("/")[1:]):
        raise ValueError("Invalid ICU Stream Path segment")
    owner = reserved_squad(path)
    if owner and owner != squad:
        raise ValueError("This member path belongs to another ICU squad")
    with LOCK:
        registry = load()
        key = "squad:" + squad
        if any(reserved_squad(other_path) == squad for other_key, existing in registry["publishers"].items()
               if other_key != key for other_path in existing["paths"]):
            raise ValueError("An ICU member path is assigned to another publisher")
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
    if reserved_squad(path):
        raise ValueError("This Stream Path is reserved for an ICU squad member")
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


def reactivate_device(key: str, rotate_password: bool) -> dict:
    if type(rotate_password) is not bool:
        raise ValueError("Invalid password choice")
    with LOCK:
        registry = load()
        item = registry["publishers"].get(key)
        if not item or item["kind"] != "device":
            raise ValueError("Select an existing device")
        if item["enabled"]:
            raise ValueError("Device is already enabled")
        if any(reserved_squad(path) for path in item["paths"]):
            raise ValueError("Device Stream Path is reserved for an ICU squad member")
        if any(path in other["paths"] for owner, other in registry["publishers"].items()
               if owner != key for path in item["paths"]):
            raise ValueError("Device Stream Path is assigned to another publisher")
        item["enabled"] = True
        if rotate_password:
            item["password"] = secrets.token_urlsafe(30)
        apply(registry)
        return copy.deepcopy(item)


def active_paths() -> list[dict]:
    result = api_request("/v3/paths/list?itemsPerPage=500")
    return [item for item in result.get("items", []) if item.get("name", "").startswith("live/") and item.get("ready")]


def squad_stream_counts(registry: dict, paths: list[dict]) -> dict[str, int]:
    """Count ready streams within each squad publisher's permitted paths."""
    counts = {}
    names = [item.get("name", "") for item in paths if item.get("ready")]
    for key, publisher in registry["publishers"].items():
        if publisher["kind"] != "squad":
            continue
        rules = permission_paths(key, publisher)
        exact = {rule for rule in rules if not rule.startswith("~")}
        patterns = [re.compile(rule[1:]) for rule in rules if rule.startswith("~")]
        counts[key] = sum(name in exact or any(pattern.fullmatch(name) for pattern in patterns)
                          for name in names)
    return counts


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
            "sessions": sessions.get("itemCount", len(sessions.get("items", []))), "internet_ready": False,
            "local_base": "http://takbox.local:8889"}


def viewer_sessions() -> dict:
    """Return only the fields needed to display public WebRTC readers."""
    result = api_request("/v3/webrtc/sessions/list?itemsPerPage=500", base_url=VIEWER_API_URL)
    items = [{"id": item.get("id", ""), "path": item.get("path", ""),
              "remote_addr": item.get("remoteAddr", ""), "created": item.get("created", ""),
              "state": item.get("state", ""),
              "connected": item.get("peerConnectionEstablished") is True,
              "outbound_bytes": item.get("outboundBytes", item.get("bytesSent", 0)),
              "user_agent": item.get("userAgent", "")}
             for item in result.get("items", []) if item.get("state") == "read"]
    return {"items": items, "shown": len(items),
            "total": result.get("itemCount", len(result.get("items", [])))}


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
