#!/usr/bin/env python3
"""Prepare local storage and a separate password for the sharing admin page."""

from __future__ import annotations

import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = ROOT / "runtime" / "secrets" / "share_admin_password"
ICU_PACKAGES = ROOT / "runtime" / "packages" / "icu"
ATAK_PACKAGES = ROOT / "runtime" / "packages" / "atak"
CONTROL = ROOT / "runtime" / "share-control"


def main() -> None:
    ICU_PACKAGES.mkdir(parents=True, exist_ok=True)
    ATAK_PACKAGES.mkdir(parents=True, exist_ok=True)
    (CONTROL / "inbox").mkdir(parents=True, exist_ok=True)
    (CONTROL / "outbox").mkdir(parents=True, exist_ok=True)
    (CONTROL / "backups").mkdir(parents=True, exist_ok=True)
    PASSWORD.parent.mkdir(parents=True, exist_ok=True)
    if PASSWORD.exists():
        if not PASSWORD.is_file() or len(PASSWORD.read_text(encoding="utf-8").strip()) < 24:
            raise SystemExit("Existing share admin password is invalid; fix it manually.")
        print("Share admin password already exists; preserved.")
        return
    with PASSWORD.open("x", encoding="utf-8") as output:
        output.write(secrets.token_urlsafe(36) + "\n")
    print("Created runtime/secrets/share_admin_password and package directories.")


if __name__ == "__main__":
    main()
