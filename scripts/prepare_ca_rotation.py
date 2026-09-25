#!/usr/bin/env python3
"""Create a local, ignored snapshot before an intermediate CA rotation test."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
BACKUPS = RUNTIME / "backups"
SOURCES = (
    Path(".env"),
    Path("runtime/pki"),
    Path("runtime/secrets"),
    Path("runtime/tak"),
    Path("runtime/mediamtx"),
    Path("runtime/packages/atak"),
    Path("runtime/tak-cert-control"),
)


def source_files() -> list[tuple[Path, Path]]:
    files = []
    for relative in SOURCES:
        source = PROJECT / relative
        if not source.exists() or source.is_symlink():
            raise RuntimeError(f"Required source is missing or is a symlink: {relative}")
        candidates = [source] if source.is_file() else sorted(source.rglob("*"))
        for candidate in candidates:
            if candidate.is_symlink():
                raise RuntimeError(f"Symlink is not supported in snapshot: {candidate.relative_to(PROJECT)}")
            if candidate.is_file():
                if candidate.name in {"worker.lock", "worker.log", "heartbeat"}:
                    continue
                files.append((candidate, candidate.relative_to(PROJECT)))
    return files


def create_snapshot() -> Path:
    files = source_files()
    if not files:
        raise RuntimeError("No files to snapshot")
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = BACKUPS / f"ca-rotation-{stamp}-{uuid.uuid4().hex[:8]}"
    destination.mkdir(exist_ok=False)
    manifest = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "files": {}}
    for source, relative in files:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(source, target)
        except OSError as exc:
            raise RuntimeError(f"Could not snapshot {relative}; incomplete snapshot: {destination}") from exc
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        copied_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if original_hash != copied_hash:
            raise RuntimeError(f"Snapshot mismatch: {relative}")
        manifest["files"][relative.as_posix()] = {"sha256": copied_hash, "bytes": target.stat().st_size}
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Show only source counts; do not copy")
    args = parser.parse_args()
    if args.list:
        files = source_files()
        print(f"Snapshot sources ready: {len(files)} files, {sum(path.stat().st_size for path, _ in files)} bytes")
    else:
        destination = create_snapshot()
        print(f"Local CA rotation snapshot: {destination.relative_to(PROJECT)}")
        print("Contains secrets and private keys; keep under ignored runtime/ and never publish it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
