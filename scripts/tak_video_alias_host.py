"""Publish console-owned ICU Video V2 aliases with stable UIDs and group replacement."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from urllib.parse import quote

import tak_api_client


PROJECT = Path(__file__).resolve().parents[1]
CONTROL = PROJECT / "runtime" / "tak-cert-control"
REGISTRY = CONTROL / "video-aliases.json"
READ_PASSWORD = PROJECT / "runtime" / "secrets" / "mediamtx_read_password"
GROUP = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
SQUADS = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel")


def alias_uid(squad: str, person: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"tak-server-docker:icu:{squad}:{person}"))


def load() -> dict:
    if not REGISTRY.is_file():
        return {"version": 1, "aliases": {}}
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("aliases"), dict):
        raise RuntimeError("Invalid managed video alias registry")
    return data


def save(data: dict) -> None:
    CONTROL.mkdir(parents=True, exist_ok=True)
    pending = REGISTRY.with_name(REGISTRY.name + "." + uuid.uuid4().hex + ".pending")
    try:
        pending.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(pending, REGISTRY)
    finally:
        pending.unlink(missing_ok=True)


def video_url(squad: str, person: int) -> str:
    password = READ_PASSWORD.read_text(encoding="ascii").strip()
    if not password:
        raise RuntimeError("MediaMTX read password is empty")
    return ("rtsp://atak-viewer:" + quote(password, safe="") +
            f"@takbox.local:8554/live/{squad}/{person}/VIDEO_1")


def payload(squad: str, person: int) -> dict:
    uid = alias_uid(squad, person)
    alias = f"ICU {squad.title()} {person}"
    return {"videoConnections": [{"uuid": uid, "active": True, "alias": alias,
            "feeds": [{"uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, uid + ":feed")),
                       "active": True, "alias": alias, "url": video_url(squad, person),
                       "rtspReliable": "1"}]}]}


def matching(uid: str) -> list[dict]:
    response = tak_api_client.video_request("GET")
    if not isinstance(response, dict) or not isinstance(response.get("videoConnections"), list):
        raise RuntimeError("TAK video list has an unexpected format")
    return [row for row in response["videoConnections"] if row.get("uuid") == uid]


def verify(uid: str, expected: dict) -> None:
    rows = matching(uid)
    target = expected["videoConnections"][0]
    if len(rows) != 1 or rows[0].get("alias") != target["alias"]:
        raise RuntimeError("TAK video alias was not uniquely replaced")
    feeds = rows[0].get("feeds")
    if not isinstance(feeds, list) or len(feeds) != 1 or feeds[0].get("url") != target["feeds"][0]["url"]:
        raise RuntimeError("TAK video alias feed did not match the requested URL")


def publish_one(registry: dict, squad: str, person: int, groups: list[str]) -> dict:
    uid = alias_uid(squad, person)
    requested = payload(squad, person)
    entries = registry["aliases"]
    existing = entries.get(uid)
    before = matching(uid)
    if existing is None and before:
        raise RuntimeError("Video alias UID already exists outside this console")
    if existing is not None and (existing.get("squad"), existing.get("person")) != (squad, person):
        raise RuntimeError("Managed video alias identity changed")
    if len(before) > 1:
        raise RuntimeError("Video alias UID has duplicate server rows; inspect before replacing")
    old_groups = existing.get("groups", []) if existing else []
    changed = bool(before) and old_groups != groups
    entries[uid] = {"squad": squad, "person": person, "alias": requested["videoConnections"][0]["alias"],
                    "groups": old_groups, "target_groups": groups, "state": "pending"}
    save(registry)
    try:
        if changed:
            tak_api_client.video_request("DELETE", uid)
            if matching(uid):
                raise RuntimeError("TAK retained the old alias after DELETE")
        tak_api_client.video_request("POST", groups=groups, payload=requested)
        verify(uid, requested)
    except Exception:
        if changed and before:
            try:
                tak_api_client.video_request("DELETE", uid)
                if old_groups:
                    tak_api_client.video_request("POST", groups=old_groups,
                                                 payload={"videoConnections": before})
            except Exception:
                pass
        raise
    entries[uid] = {"squad": squad, "person": person, "alias": requested["videoConnections"][0]["alias"],
                    "groups": groups, "state": "ready"}
    save(registry)
    return {"uid": uid, "alias": entries[uid]["alias"], "person": person, "groups": groups}


def publish_batch(squad: str, people: list[int], groups: list[str]) -> dict:
    if (squad not in SQUADS or not isinstance(people, list) or not 1 <= len(people) <= 10 or
            any(type(person) is not int or not 1 <= person <= 10 for person in people) or
            len(set(people)) != len(people) or
            not isinstance(groups, list) or not 1 <= len(groups) <= 20 or
            len(groups) != len(set(groups)) or
            any(not isinstance(group, str) or not GROUP.fullmatch(group) for group in groups)):
        raise ValueError("Invalid ICU Video Alias batch")
    registry = load()
    results = []
    for person in people:
        try:
            results.append({**publish_one(registry, squad, person, sorted(groups)), "state": "ready"})
        except (OSError, RuntimeError, ValueError) as exc:
            results.append({"person": person, "state": "failed", "error": str(exc)[:200]})
    return {"state": "complete" if all(row["state"] == "ready" for row in results) else "partial",
            "results": results}
