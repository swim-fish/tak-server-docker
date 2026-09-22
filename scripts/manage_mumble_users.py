#!/usr/bin/env python3
"""Local Compose Mumble registration management for Remove-MumbleUsers.ps1."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sqlite3
import ssl
import subprocess
import sys
import time
import uuid
from pathlib import Path

import provision_mumble_channel as protocol

PROJECT = Path(__file__).resolve().parents[1]
ADMIN_DIR = PROJECT / "runtime" / "mumble-admin"


def run(*args: str) -> str:
    result = subprocess.run(args, cwd=PROJECT, capture_output=True, timeout=45)
    if result.returncode:
        # Docker/database diagnostics may contain local deployment details.
        raise RuntimeError(f"{args[0]} operation failed (exit {result.returncode}). Check Docker and the mumble service.")
    return result.stdout.decode("utf-8")


def target() -> dict:
    cid = run("docker", "compose", "ps", "-q", "mumble").strip()
    if not cid or "\n" in cid:
        raise RuntimeError("Expected exactly one running Compose mumble container.")
    ports = json.loads(run("docker", "inspect", "--format", "{{json .NetworkSettings.Ports}}", cid))
    bindings = ports.get("64738/tcp") or []
    if len(bindings) != 1:
        raise RuntimeError("Expected one published Mumble TCP binding; refusing an ambiguous target.")
    host = bindings[0]["HostIp"]
    return {"container": cid, "host": "127.0.0.1" if host == "0.0.0.0" else host,
            "port": int(bindings[0]["HostPort"])}


def fingerprints(rows: list[dict], info: list[dict]) -> dict[int, dict]:
    output = {}
    for row in rows:
        uid = row["user_id"]
        if uid <= 0:
            continue
        identity = {"account": row, "info": sorted(
            [v for v in info if v["user_id"] == uid], key=lambda v: v["key"])}
        digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        output[uid] = {"id": uid, "name": row["name"], "fingerprint": digest}
    return output


def database_users(cid: str) -> dict[int, dict]:
    rows = json.loads(run("docker", "exec", cid, "sqlite3", "-readonly", "-json",
        "/data/mumble-server.sqlite", "SELECT user_id,name,pw,salt,kdfiterations FROM users WHERE server_id=1 AND user_id>0") or "[]")
    info = json.loads(run("docker", "exec", cid, "sqlite3", "-readonly", "-json",
        "/data/mumble-server.sqlite", "SELECT user_id,key,value FROM user_info WHERE server_id=1 AND user_id>0") or "[]")
    return fingerprints(rows, info)


def backup_database(cid: str) -> Path:
    ADMIN_DIR.mkdir(parents=True, exist_ok=True)
    name = f"before-unregister-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex}.sqlite"
    remote = "/tmp/" + name
    output = ADMIN_DIR / name
    run("docker", "exec", cid, "sqlite3", "-readonly", "/data/mumble-server.sqlite", f".backup '{remote}'")
    run("docker", "cp", f"{cid}:{remote}", str(output))
    with sqlite3.connect(output.as_uri() + "?mode=ro", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Backup integrity check failed; no registrations were removed.")
    run("docker", "exec", cid, "rm", "--", remote)
    return output


class Admin:
    def __init__(self, endpoint: dict, server_name: str):
        self.endpoint = endpoint
        self.server_name = server_name
        self.users: dict[int, dict] = {}
        self.channels: dict[int, str] = {}

    def __enter__(self):
        context = ssl.create_default_context(cafile=str(protocol.ROOT_CA))
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        raw = socket.create_connection((self.endpoint["host"], self.endpoint["port"]), timeout=5)
        try:
            self.connection = context.wrap_socket(raw, server_hostname=self.server_name)
            self.send(0, protocol.protobuf_string(2, "tak-local-user-manager"))
            self.send(2, protocol.protobuf_string(1, "SuperUser")
                      + protocol.protobuf_string(2, protocol.SUPERUSER_PASSWORD.read_text().strip())
                      + protocol.protobuf_varint(5, 1))
            self.until(5)
            return self
        except BaseException:
            if hasattr(self, "connection"):
                self.connection.close()
            raw.close()
            raise

    def __exit__(self, *_):
        self.connection.close()

    def send(self, kind: int, payload: bytes):
        protocol.send_message(self.connection, kind, payload)

    def receive(self):
        kind, payload = protocol.read_message(self.connection)
        fields = protocol.parse_protobuf(payload)
        if kind in (4, 12):
            raise RuntimeError(f"Mumble rejected the management request (message type {kind}).")
        if kind == 9:
            sid = protocol.integer_field(fields, 1)
            self.users.setdefault(sid, {}).update(fields)
        elif kind == 8:
            self.users.pop(protocol.integer_field(fields, 1), None)
        elif kind == 7:
            self.channels[protocol.integer_field(fields, 1)] = protocol.text_field(fields, 3)
        return kind, fields

    def until(self, kind: int):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            received, fields = self.receive()
            if received == kind:
                return fields
        raise RuntimeError("Mumble management response timed out.")

    def registered(self) -> dict[int, str]:
        self.send(18, b"")
        fields = self.until(18)
        rows = [protocol.parse_protobuf(v) for v in fields.get(1, [])]
        return {protocol.integer_field(v, 1): protocol.text_field(v, 2) for v in rows}

    def disconnect(self, sessions: dict[int, dict]) -> list[int]:
        disconnected = []
        for sid, original in sessions.items():
            current = self.users.get(sid)
            if current is None:
                continue
            # Never kick a reused session belonging to another certificate/name.
            if any(protocol.text_field(current, key) != protocol.text_field(original, key) for key in (3, 15)):
                raise RuntimeError("Session identity changed; disconnect was not sent.")
            self.send(8, protocol.protobuf_varint(1, sid)
                      + protocol.protobuf_string(3, "Registration removed by administrator. Reconnect to authenticate.")
                      + protocol.protobuf_varint(4, 0))
            deadline = time.monotonic() + 8
            while sid in self.users and time.monotonic() < deadline:
                self.receive()
            if sid in self.users:
                raise RuntimeError("Registration removed, but session disconnection was not confirmed.")
            disconnected.append(sid)
        return disconnected


def checked_users(admin: Admin, cid: str) -> dict[int, dict]:
    database = database_users(cid)
    listed = admin.registered()
    if listed != {uid: row["name"] for uid, row in database.items()}:
        raise RuntimeError("Protocol and local database disagree; refresh the user list.")
    return database


def validate_selection(snapshot: dict, current: dict[int, dict], ids: list[int]):
    if not ids or len(set(ids)) != len(ids) or any(uid <= 0 for uid in ids):
        raise ValueError("Select unique non-SuperUser IDs; an empty selection cannot remove users.")
    expected = {v["id"]: v for v in snapshot["users"]}
    for uid in ids:
        if uid not in expected or uid not in current or any(
            expected[uid][key] != current[uid][key] for key in ("name", "fingerprint")
        ):
            raise RuntimeError(f"Registration {uid} changed or disappeared; refresh and select again.")


def write_json(path: Path, value: dict):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True), encoding="utf-8")


def apply_selection(snapshot: dict, endpoint: dict, admin: Admin, ids: list[int]) -> dict:
    if snapshot["endpoint"] != endpoint:
        raise RuntimeError("Compose container or port changed; refresh the user list.")
    validate_selection(snapshot, checked_users(admin, endpoint["container"]), ids)
    backup = backup_database(endpoint["container"])
    current = checked_users(admin, endpoint["container"])
    validate_selection(snapshot, current, ids)
    sessions = {sid: dict(v) for sid, v in admin.users.items() if protocol.integer_field(v, 4) in ids}
    journal = backup.with_suffix(".operation.json")
    result = {"status": "pending", "selected_ids": ids, "backup": str(backup),
              "disconnected_sessions": [], "journal": str(journal)}
    write_json(journal, result)
    try:
        # An ID-only entry in UserList requests unregister; omit the name field.
        admin.send(18, b"".join(protocol.protobuf_bytes(1, protocol.protobuf_varint(1, uid)) for uid in ids))
        remaining = admin.registered()
        if set(ids) & set(remaining):
            raise RuntimeError("Some selected registrations remain; inspect the operation journal before retrying.")
        result["disconnected_sessions"] = admin.disconnect(sessions)
        final = checked_users(admin, endpoint["container"])
        if set(ids) & set(final):
            raise RuntimeError("A selected ID is registered again; inspect client auto-registration.")
        for uid in set(current) - set(ids):
            if uid not in final or final[uid]["fingerprint"] != current[uid]["fingerprint"]:
                raise RuntimeError("Another registration changed during the operation; inspect the backup.")
        result.update(status="complete", remaining_ids=sorted(final))
    except BaseException:
        result["status"] = "incomplete-check-server-before-retry"
        write_json(journal, result)
        print(f"Operation may be partial. Backup: {backup}; journal: {journal}", file=sys.stderr)
        raise
    write_json(journal, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("list", "apply"))
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--server-name", default="takbox.local")
    parser.add_argument("--ids", type=int, nargs="+")
    args = parser.parse_args()
    ADMIN_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = args.snapshot.resolve()
    if not snapshot_path.is_relative_to(ADMIN_DIR.resolve()):
        raise ValueError("Snapshot must be inside runtime/mumble-admin.")
    endpoint = target()
    with Admin(endpoint, args.server_name) as admin:
        if args.action == "list":
            rows = checked_users(admin, endpoint["container"])
            for uid, row in rows.items():
                row["sessions"] = sum(protocol.integer_field(v, 4) == uid for v in admin.users.values())
            write_json(snapshot_path, {"endpoint": endpoint, "server_name": args.server_name,
                                      "users": [rows[uid] for uid in sorted(rows)]})
        else:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            if snapshot["server_name"] != args.server_name:
                raise ValueError("TLS server name changed; refresh the user list.")
            result = apply_selection(snapshot, endpoint, admin, args.ids or [])
            print("Removed registered IDs: " + ", ".join(map(str, args.ids)))
            print("Disconnected sessions: " + str(len(result["disconnected_sessions"])))
            print("Backup: " + result["backup"])
            print("Journal: " + result["journal"])


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        print(f"Mumble user management stopped: {error}", file=sys.stderr)
        sys.exit(1)
