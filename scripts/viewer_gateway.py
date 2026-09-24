"""LAN-facing, read-only WebRTC gateway with a persistent kill switch."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, Response, redirect, request


STATE = Path(os.environ.get("MEDIA_VIEWER_STATE_FILE", "/media-config/viewer_state.json"))
UPSTREAM = "http://media-viewer:8889"
MAX_BODY = 1024 * 1024
app = Flask(__name__)


@app.route("/healthz")
def healthz() -> str:
    return "ok"


@app.route("/", defaults={"path": ""}, methods=["GET", "HEAD", "OPTIONS", "POST", "PATCH", "DELETE"])
@app.route("/<path:path>", methods=["GET", "HEAD", "OPTIONS", "POST", "PATCH", "DELETE"])
def proxy(path: str) -> Response:
    try:
        enabled = json.loads(STATE.read_text(encoding="utf-8"))["enabled"] is True
    except (OSError, ValueError, KeyError):
        enabled = False
    if not enabled:
        return Response("Public viewing is stopped", 503, headers={"Cache-Control": "no-store"})
    if not path.startswith("live/") or "/whip" in path.lower() or "/v3/" in path.lower():
        return Response("Not found", 404)
    if request.method == "GET" and "text/html" in request.headers.get("Accept", "") and not path.endswith("/"):
        return redirect(request.path + "/" + ("?" + request.query_string.decode("ascii", "ignore") if request.query_string else ""), code=308)
    if request.method in {"POST", "PATCH", "DELETE"} and not (
            path.endswith("/whep") or "/whep/" in path):
        return Response("Method not allowed", 405)
    if request.content_length is not None and request.content_length > MAX_BODY:
        return Response("Request too large", 413)
    body = request.get_data(cache=False)
    if len(body) > MAX_BODY:
        return Response("Request too large", 413)
    headers = {}
    for key in ("Content-Type", "Accept", "If-Match", "If-None-Match"):
        if request.headers.get(key):
            headers[key] = request.headers[key]
    target = UPSTREAM + "/" + path
    if request.query_string:
        target += "?" + request.query_string.decode("ascii", "ignore")
    upstream = Request(target, data=body if request.method in {"POST", "PATCH"} else None,
                       method=request.method, headers=headers)
    try:
        response = urlopen(upstream, timeout=20)
    except HTTPError as exc:
        response = exc
    except (OSError, URLError):
        return Response("Viewer backend unavailable", 502)
    with response:
        output = response.read(MAX_BODY + 1)
        if len(output) > MAX_BODY:
            return Response("Viewer response too large", 502)
        relay = {}
        for key in ("Content-Type", "Location", "ETag", "Link", "Allow", "Access-Control-Expose-Headers"):
            value = response.headers.get(key)
            if value:
                relay[key] = value.replace(UPSTREAM + "/", "/") if key == "Location" else value
        relay["Cache-Control"] = "no-store"
        return Response(output, status=response.status, headers=relay)
