#!/usr/bin/env python3
"""Foreground Windows worker for the loopback Flask Mumble management page."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import time
import uuid
from pathlib import Path

import manage_mumble_users as manager
import provision_mumble_channel as protocol

PROJECT = Path(__file__).resolve().parents[1]
CONTROL = PROJECT / "runtime" / "share-control"
PASSWORD = PROJECT / "runtime" / "secrets" / "mumble_server_password"
SERVER_NAME = "takbox.local"


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sessions(admin: manager.Admin) -> dict[int, dict]:
    output = {}
    for sid, fields in admin.users.items():
        name = protocol.text_field(fields, 3)
        if not sid or name == "SuperUser":
            continue
        identity = {"id": sid, "name": name, "registered_id": protocol.integer_field(fields, 4),
                    "cert": protocol.text_field(fields, 15)}
        output[sid] = {**identity, "fingerprint": fingerprint(identity)}
    return output


def registrations(admin: manager.Admin, cid: str) -> dict[int, dict]:
    records = manager.checked_users(admin, cid)
    online = sessions(admin)
    return {uid: {"id": uid, "name": item["name"], "fingerprint": item["fingerprint"],
                  "online": sum(session["registered_id"] == uid for session in online.values())}
            for uid, item in records.items()}


def checked_selection(selected: object, current: dict[int, dict]) -> list[int]:
    if not isinstance(selected, list) or not 1 <= len(selected) <= 100:
        raise ValueError("Select between 1 and 100 entries")
    ids = []
    for item in selected:
        if not isinstance(item, dict) or type(item.get("id")) is not int:
            raise ValueError("Invalid selection")
        uid = item["id"]
        if uid in ids:
            raise ValueError("Duplicate selection")
        if uid <= 0 or uid not in current or item.get("fingerprint") != current[uid]["fingerprint"]:
            raise RuntimeError("Selection changed; refresh the Mumble page")
        ids.append(uid)
    return ids


def kick(admin: manager.Admin, selected: object) -> dict:
    ids = checked_selection(selected, sessions(admin))
    for sid in ids:
        admin.send(8, protocol.protobuf_varint(1, sid)
                   + protocol.protobuf_string(3, "Disconnected by administrator")
                   + protocol.protobuf_varint(4, 0))
        deadline = time.monotonic() + 8
        while sid in admin.users and time.monotonic() < deadline:
            admin.receive()
        if sid in admin.users:
            raise RuntimeError("Mumble did not confirm all disconnections; refresh the page")
    return {"count": len(ids)}


def unregister(admin: manager.Admin, endpoint: dict, selected: object) -> dict:
    current = registrations(admin, endpoint["container"])
    ids = checked_selection(selected, current)
    snapshot = {"endpoint": endpoint, "server_name": SERVER_NAME,
                "users": [current[uid] for uid in ids]}
    result = manager.apply_selection(snapshot, endpoint, admin, ids)
    return {"count": len(ids), "disconnected": len(result["disconnected_sessions"]),
            "backup": Path(result["backup"]).name}


def recreate_mumble() -> None:
    result = subprocess.run(["docker", "compose", "up", "-d", "--force-recreate", "--no-deps", "mumble"],
                            cwd=PROJECT, capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError("Docker could not recreate the Mumble container; check Docker Desktop")


def reset_password() -> dict:
    old = PASSWORD.read_bytes()
    if not old:
        raise RuntimeError("Existing Mumble password is empty")
    backup_dir = CONTROL / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"before-password-reset-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex}.txt"
    with backup.open("xb") as output:
        output.write(old)
        output.flush()
        os.fsync(output.fileno())
    replacement = secrets.token_urlsafe(36).encode() + b"\n"
    with PASSWORD.open("r+b") as secret_file:
        secret_file.seek(0)
        secret_file.write(replacement)
        secret_file.truncate()
        secret_file.flush()
        os.fsync(secret_file.fileno())
    try:
        recreate_mumble()
    except Exception:
        with PASSWORD.open("r+b") as secret_file:
            secret_file.seek(0)
            secret_file.write(old)
            secret_file.truncate()
            secret_file.flush()
            os.fsync(secret_file.fileno())
        raise
    return {"backup": backup.name}


def execute(request: dict) -> dict:
    action = request.get("action")
    if action == "restart":
        recreate_mumble()
        return {}
    if action == "reset_password":
        return reset_password()
    if action not in {"snapshot", "kick", "unregister"}:
        raise ValueError("Unsupported Mumble action")
    endpoint = manager.target()
    with manager.Admin(endpoint, SERVER_NAME) as admin:
        if action == "snapshot":
            return {"sessions": sorted(sessions(admin).values(), key=lambda item: item["id"]),
                    "registrations": sorted(registrations(admin, endpoint["container"]).values(),
                                            key=lambda item: item["id"])}
        if action == "kick":
            return kick(admin, request.get("selected"))
        return unregister(admin, endpoint, request.get("selected"))


def main() -> None:
    inbox, outbox = CONTROL / "inbox", CONTROL / "outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    print("Mumble management worker ready. Press Ctrl+C to stop.", flush=True)
    heartbeat = CONTROL / "heartbeat"
    try:
        while True:
            heartbeat.write_text(str(time.time()), encoding="ascii")
            for path in sorted(inbox.glob("*.json")):
                operation_id = path.stem
                if len(operation_id) != 32 or any(c not in "0123456789abcdef" for c in operation_id):
                    path.unlink(missing_ok=True)
                    continue
                try:
                    request = json.loads(path.read_text(encoding="utf-8"))
                    if request.get("id") != operation_id:
                        raise ValueError("Invalid request ID")
                    result = {"ok": True, **execute(request)}
                except Exception as error:
                    print(f"Mumble operation failed: {type(error).__name__}", flush=True)
                    result = {"ok": False, "error": str(error) if isinstance(error, (ValueError, RuntimeError))
                              else "Mumble operation failed; inspect the local worker"}
                pending = outbox / (operation_id + ".pending")
                pending.write_text(json.dumps(result), encoding="utf-8")
                os.replace(pending, outbox / (operation_id + ".json"))
                path.unlink(missing_ok=True)
            time.sleep(0.2)
    finally:
        heartbeat.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Mumble management worker stopped.", flush=True)
