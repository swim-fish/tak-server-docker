#!/usr/bin/env python3
"""Read Mumble registrations and make consistent backups through its Compose volume."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path


DATABASE = Path("/data/mumble-server.sqlite")
BACKUP_DIR = Path("/backup")
BACKUP_NAME = re.compile(r"before-unregister-\d{8}-\d{6}-[0-9a-f]{32}\.sqlite\Z")


def open_source() -> sqlite3.Connection:
    if not DATABASE.is_file():
        raise RuntimeError("Mumble database is missing")
    connection = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def list_users(source: sqlite3.Connection) -> list[dict]:
    accounts = [dict(row) for row in source.execute(
        "SELECT user_id,name,pw,salt,kdfiterations FROM users WHERE server_id=1 AND user_id>0")]
    info = [dict(row) for row in source.execute(
        "SELECT user_id,key,value FROM user_info WHERE server_id=1 AND user_id>0")]
    result = []
    for account in accounts:
        identity = {"account": account, "info": sorted(
            (item for item in info if item["user_id"] == account["user_id"]),
            key=lambda item: item["key"])}
        result.append({"id": account["user_id"], "name": account["name"],
                       "fingerprint": hashlib.sha256(
                           json.dumps(identity, sort_keys=True).encode()).hexdigest()})
    return sorted(result, key=lambda item: item["id"])


def backup(source: sqlite3.Connection, name: str) -> None:
    if not BACKUP_NAME.fullmatch(name):
        raise ValueError("Invalid backup name")
    if not BACKUP_DIR.is_dir():
        raise RuntimeError("Backup directory is missing")
    target = BACKUP_DIR / name
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with sqlite3.connect(target) as destination:
            source.backup(destination)
        with sqlite3.connect(f"file:{target}?mode=ro", uri=True) as saved:
            if saved.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Mumble backup integrity check failed")
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("list", "backup"))
    parser.add_argument("name", nargs="?")
    args = parser.parse_args()
    with open_source() as source:
        if args.action == "list":
            if args.name:
                parser.error("list does not take a backup name")
            print(json.dumps(list_users(source), separators=(",", ":")))
        else:
            if not args.name:
                parser.error("backup requires a filename")
            backup(source, args.name)
            print(args.name)


if __name__ == "__main__":
    main()
