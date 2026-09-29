"""Read-only, layered health checks for the local management console."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

import media_registry as media


WORKERS = {
    "service": Path("/service-control/heartbeat"),
    "certificate": Path("/cert-control/heartbeat"),
    "mumble": Path("/control/heartbeat"),
}
SERVICE_LABELS = {
    "tak-db": "PostgreSQL", "tak-server": "TAK Server", "mumble": "Mumble",
    "mediamtx": "MediaMTX", "media-viewer": "WebRTC viewer",
    "media-viewer-gateway": "WebRTC gateway", "media-preview": "管理頁預覽",
    "share-admin": "管理頁", "share-public": "QR 分享入口",
}
CONTROLLABLE = {"mumble", "mediamtx", "media-viewer", "media-viewer-gateway",
                "media-preview", "share-public"}
REQUIRED = set(SERVICE_LABELS) - {"share-public"}
HEALTH_REQUIRED = {"tak-db", "tak-server", "mumble", "share-admin"}


def worker_state(path: Path) -> str:
    try:
        return "ready" if time.time() - path.stat().st_mtime <= 5 else "down"
    except OSError:
        return "down"


def api_probe(base_url: str) -> str:
    try:
        media.api_request("/v3/config/global/get", base_url=base_url)
        return "ready"
    except (OSError, ValueError, RuntimeError):
        return "down"


def http_probe(url: str) -> str:
    try:
        with urlopen(url, timeout=3) as response:
            return "ready" if response.status == 200 else "down"
    except (OSError, ValueError):
        return "down"


def collect(containers: dict | None = None) -> dict:
    """Keep Compose state, app readiness, and host workers distinct."""
    containers = containers or {}
    probes = {
        "mediamtx": lambda: api_probe(media.API_URL),
        "media-viewer": lambda: api_probe(media.VIEWER_API_URL),
        "media-viewer-gateway": lambda: http_probe("http://media-viewer-gateway:8889/healthz"),
        "share-public": lambda: http_probe("http://share-public:8765/healthz"),
    }
    active = {name: probe for name, probe in probes.items()
              if containers.get(name, {}).get("state") in {"running", None}}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {name: pool.submit(probe) for name, probe in active.items()}
        application = {name: future.result() for name, future in futures.items()}
    for name in probes:
        if name not in application:
            application[name] = "disabled" if containers.get(name, {}).get("state") in {"exited", "absent"} else "unknown"
    workers = {name: worker_state(path) for name, path in WORKERS.items()}
    if not containers:
        overall = "unknown"
    elif any(containers.get(name, {}).get("state") != "running" or
             (name in HEALTH_REQUIRED and containers.get(name, {}).get("health") != "healthy") or
             containers.get(name, {}).get("health") == "unhealthy" for name in REQUIRED):
        overall = "degraded"
    elif any(application[name] != "ready" for name in
             ("mediamtx", "media-viewer", "media-viewer-gateway")):
        overall = "degraded"
    elif any(state == "down" for state in workers.values()):
        overall = "degraded"
    else:
        overall = "ready"
    return {"overall": overall, "containers": containers, "application": application,
            "workers": workers}
