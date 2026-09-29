#!/usr/bin/env python3
"""Allowlisted Docker Compose service control from the Windows host."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Thread


PROJECT = Path(__file__).resolve().parents[1]
CONTROL = PROJECT / "runtime" / "service-control"
SERVICES = (
    "tak-db", "tak-server", "mumble", "mediamtx", "media-viewer",
    "media-viewer-gateway", "media-preview", "share-admin", "share-public",
)
# The console cannot control itself. Core TAK services require the existing
# operator procedures because stopping them can interrupt certificate work.
CONTROLLABLE = frozenset({"mumble", "mediamtx", "media-viewer",
                          "media-viewer-gateway", "media-preview", "share-public"})
ACTIONS = frozenset({"start", "stop", "restart"})
IDENTIFIER = re.compile(r"[0-9a-f]{32}\Z")


def compose(*args: str, timeout: int = 30) -> str:
    command = ["docker", "compose", "--project-directory", str(PROJECT),
               "--profile", "sharing", "-f", str(PROJECT / "compose.yaml"), *args]
    try:
        result = subprocess.run(command, cwd=PROJECT, capture_output=True, text=True,
                                timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Docker Compose is unavailable or timed out") from exc
    if result.returncode:
        # Docker can echo URLs and credentials in diagnostics. Keep them in the
        # local worker log, not in the browser response.
        raise RuntimeError(f"Docker Compose {args[0]} failed; inspect the Windows worker log")
    return result.stdout


def parse_ps(output: str) -> dict[str, dict]:
    output = output.strip()
    if not output:
        rows = []
    elif output.startswith("["):
        rows = json.loads(output)
    else:
        rows = [json.loads(line) for line in output.splitlines() if line.strip()]
    result = {name: {"state": "absent", "health": "none"} for name in SERVICES}
    for row in rows:
        name = row.get("Service")
        if name in result:
            result[name] = {"state": str(row.get("State") or "unknown").lower(),
                            "health": str(row.get("Health") or "none").lower()}
    return result


def snapshot() -> dict:
    return {"services": parse_ps(compose("ps", "--all", "--format", "json"))}


def execute(payload: dict) -> dict:
    action = payload.get("action")
    if action == "snapshot":
        return snapshot()
    if action != "control":
        raise ValueError("Unsupported service operation")
    service = payload.get("service")
    verb = payload.get("verb")
    if service not in CONTROLLABLE or verb not in ACTIONS:
        raise ValueError("Service or action is not allowed")
    before = snapshot()["services"][service]
    if before["state"] == "absent":
        raise RuntimeError("Service has not been deployed; use the setup procedure")
    compose(verb, service, timeout=120)
    after = snapshot()["services"][service]
    if verb == "stop" and after["state"] != "exited":
        raise RuntimeError("Stop was not confirmed; inspect the service status")
    if verb in {"start", "restart"} and after["state"] != "running":
        raise RuntimeError("Start was not confirmed; inspect the service status")
    record = {"at": datetime.now(timezone.utc).isoformat(), "service": service,
              "action": verb, "state": after["state"]}
    with (CONTROL / "actions.jsonl").open("a", encoding="utf-8") as journal:
        journal.write(json.dumps(record) + "\n")
    return {"operation": record}


def main() -> None:
    inbox, outbox = CONTROL / "inbox", CONTROL / "outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    heartbeat = CONTROL / "heartbeat"
    heartbeat_stop = Event()

    def keep_heartbeat() -> None:
        while not heartbeat_stop.wait(1):
            heartbeat.touch()

    heartbeat.touch()
    heartbeat_thread = Thread(target=keep_heartbeat, name="tak-service-heartbeat", daemon=True)
    heartbeat_thread.start()
    try:
        while True:
            for path in sorted(inbox.glob("*.json")):
                operation_id = path.stem
                if not IDENTIFIER.fullmatch(operation_id):
                    path.unlink(missing_ok=True)
                    continue
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if payload.get("id") != operation_id:
                        raise ValueError("Invalid request ID")
                    result = {"ok": True, **execute(payload)}
                except Exception as exc:
                    print(f"Service operation failed: {type(exc).__name__}: {exc}", flush=True)
                    result = {"ok": False, "error": str(exc) if isinstance(exc, (ValueError, RuntimeError))
                              else "Service operation failed; inspect the Windows worker log"}
                pending = outbox / (operation_id + ".pending")
                pending.write_text(json.dumps(result), encoding="utf-8")
                os.replace(pending, outbox / (operation_id + ".json"))
                path.unlink(missing_ok=True)
            time.sleep(0.2)
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=2)
        heartbeat.unlink(missing_ok=True)


if __name__ == "__main__":
    from host_worker_lock import exclusive_worker

    try:
        with exclusive_worker(CONTROL):
            main()
    except KeyboardInterrupt:
        print("Service worker stopped.", flush=True)
