#!/usr/bin/env python3
"""Run one Windows management worker without a console and restart it on failure."""

from __future__ import annotations

import importlib
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from host_worker_lock import exclusive_worker


ROOT = Path(__file__).resolve().parents[1]
WORKERS = {
    "certificate": ("tak_certificate_host", ROOT / "runtime/tak-cert-control"),
    "mumble": ("mumble_control_host", ROOT / "runtime/share-control"),
}


def main(name: str) -> None:
    if name not in WORKERS:
        raise SystemExit("Expected certificate or mumble")
    module_name, directory = WORKERS[name]
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "worker.log").open("a", encoding="utf-8", buffering=1) as log:
        sys.stdout = log
        sys.stderr = log
        with exclusive_worker(directory):
            module = importlib.import_module(module_name)
            while True:
                try:
                    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting {name} worker", flush=True)
                    module.main()
                    print("Worker exited; restarting in 5 seconds", flush=True)
                except Exception:
                    traceback.print_exc(file=log)
                    print("Worker failed; restarting in 5 seconds", flush=True)
                time.sleep(5)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) == 2 else "")
