#!/usr/bin/env python3
"""Loopback-only Flask administration for TAK file sharing and Mumble."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_file, url_for

import share_portal as portal


CONTROL_DIR = Path(os.environ.get("MUMBLE_CONTROL_DIR", "/control"))
CERT_CONTROL_DIR = Path(os.environ.get("TAK_CERT_CONTROL_DIR", "/cert-control"))
ADMIN_PASSWORD = portal.ADMIN_PASSWORD_FILE.read_text(encoding="utf-8").strip()
if len(ADMIN_PASSWORD) < 24:
    raise RuntimeError("Share admin password must contain at least 24 characters")
CSRF = hmac.new(ADMIN_PASSWORD.encode(), b"share-admin-csrf-v1", hashlib.sha256).hexdigest()
portal.initialize()
APP_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
if not TEMPLATE_DIR.is_dir():
    TEMPLATE_DIR = APP_DIR.parent / "docker/share-portal/templates"
if not STATIC_DIR.is_dir():
    STATIC_DIR = APP_DIR.parent / "docker/share-portal/static"
app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))


@app.after_request
def security_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; img-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; connect-src 'self'; form-action 'self'; base-uri 'none'")
    return response


@app.before_request
def require_login() -> None:
    if request.path == "/healthz":
        return
    raw = request.headers.get("Authorization", "")
    try:
        scheme, encoded = raw.split(" ", 1)
        username, password = base64.b64decode(encoded, validate=True).decode().split(":", 1)
        valid = scheme.lower() == "basic" and username == "admin" and hmac.compare_digest(
            password, ADMIN_PASSWORD)
    except (ValueError, UnicodeError, binascii.Error):
        valid = False
    if not valid:
        return Response("Authentication required", 401,
                        {"WWW-Authenticate": 'Basic realm="TAK Share Admin"'})
    if request.method == "POST":
        origin = request.headers.get("Origin")
        admin_port = os.environ.get("SHARE_ADMIN_HOST_PORT", "8766")
        loopback_hosts = (f"127.0.0.1:{admin_port}", f"localhost:{admin_port}")
        same_origin = origin in (None, *(f"http://{host}" for host in loopback_hosts))
        # Some Chrome configurations send Origin: null for local form submissions.
        same_origin = same_origin or (
            origin == "null" and request.headers.get("Sec-Fetch-Site") == "same-origin"
            and request.host in loopback_hosts)
        if not same_origin:
            app.logger.warning("Rejected admin POST %s: unexpected Origin or fetch site", request.path)
            abort(403)
        if not hmac.compare_digest(request.form.get("csrf", ""), CSRF):
            app.logger.warning("Rejected admin POST %s: invalid CSRF token", request.path)
            abort(403)


def worker_control(directory: Path, action: str, *, timeout: int = 75,
                   **parameters: object) -> dict:
    inbox, outbox = directory / "inbox", directory / "outbox"
    heartbeat = directory / "heartbeat"
    if not heartbeat.is_file() or time.time() - heartbeat.stat().st_mtime > 5:
        raise RuntimeError("Start the matching Windows management worker first")
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    operation_id = uuid.uuid4().hex
    pending = inbox / (operation_id + ".pending")
    request_path = inbox / (operation_id + ".json")
    response_path = outbox / (operation_id + ".json")
    pending.write_text(json.dumps({"id": operation_id, "action": action, **parameters}), encoding="utf-8")
    os.replace(pending, request_path)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if response_path.exists():
            result = json.loads(response_path.read_text(encoding="utf-8"))
            response_path.unlink(missing_ok=True)
            if not result.get("ok"):
                raise RuntimeError(result.get("error", "Host worker operation failed"))
            return result
        time.sleep(0.15)
    raise RuntimeError(f"Host worker did not answer within {timeout} seconds")


def control(action: str, **parameters: object) -> dict:
    return worker_control(CONTROL_DIR, action, **parameters)


def cert_control(action: str, **parameters: object) -> dict:
    return worker_control(CERT_CONTROL_DIR, action, timeout=270, **parameters)


def selected_certificates() -> list[dict]:
    items = []
    seen = set()
    for value in request.form.getlist("certificate"):
        serial, separator, fingerprint = value.partition(":")
        if (not separator or not 1 <= len(serial) <= 40 or
                any(c not in "0123456789ABCDEF" for c in serial) or
                len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint) or
                serial in seen):
            raise ValueError("Invalid or duplicate certificate selection")
        seen.add(serial)
        items.append({"serial": serial, "fingerprint": fingerprint})
    if not 1 <= len(items) <= 100:
        raise ValueError("Select between 1 and 100 certificates")
    return items


def group_values(prefix: str) -> list[str]:
    values = request.form.getlist(prefix + "_group")
    extra = request.form.get(prefix + "_extra", "").strip()
    if extra:
        values.extend(item.strip() for item in extra.split(","))
    return values


def selected(field: str) -> list[dict]:
    items = []
    seen = set()
    for value in request.form.getlist(field):
        identifier, separator, fingerprint = value.partition(":")
        if not separator or not identifier.isdecimal() or len(fingerprint) != 64:
            raise ValueError("Invalid Mumble selection; refresh the list")
        number = int(identifier)
        if number <= 0 or number in seen or any(char not in "0123456789abcdef" for char in fingerprint):
            raise ValueError("Invalid or duplicate Mumble selection")
        seen.add(number)
        items.append({"id": number, "fingerprint": fingerprint})
    if not items or len(items) > 100:
        raise ValueError("Select between 1 and 100 entries")
    return items


@app.get("/healthz")
def healthz() -> str:
    return "ok"


@app.get("/")
def index() -> Response:
    return Response(portal.admin_page(CSRF), mimetype="text/html")


@app.get("/admin.js")
def admin_script() -> Response:
    return send_file(Path(__file__).with_name("share_admin.js"), mimetype="text/javascript")


@app.get("/qr.png/<token>")
def admin_qr_image(token: str) -> Response:
    row, error = portal.active_share(token)
    if error is not None:
        return error
    assert row is not None
    return Response(portal.qr_png(row), content_type="image/png")


@app.get("/stats")
def stats() -> Response:
    rows, paused = portal.list_shares()
    now = int(time.time())
    return jsonify({"paused": paused, "server_now": now,
                    "sources": portal.import_choices(), "shares": [
        {"id": row["id"], "status": portal.share_status(row, paused, now),
         "inactive": portal.share_status(row, False, now) != "分享中",
         "filename": row["filename"], "kind": row["kind"],
         "created_at": portal.local_time(row["created_at"]),
         "expires_at": portal.local_time(row["expires_at"]),
         "expires_at_epoch": row["expires_at"],
         "qr_url": f"{portal.PUBLIC_BASE}/q/{row['token']}",
         "qr_image_url": f"/qr.png/{row['token']}",
         "accepted": row["accepted"], "completed": row["completed"],
         "max_downloads": row["max_downloads"]} for row in rows]})


@app.post("/create")
def create() -> Response:
    try:
        ttl = int(request.form["ttl"]) if request.form.get("ttl") else None
        limit = int(request.form["limit"]) if request.form.get("limit") else None
        source = request.form.get("source", "")
        kind = "icu" if source.startswith("icu:") else "file"
        portal.create_share(kind, "" if source == "icu:new" else source, ttl, limit)
    except (ValueError, OSError) as exc:
        return Response(str(exc), 400)
    return redirect(url_for("index"), code=303)


@app.post("/stop")
def stop() -> Response:
    portal.update_status(request.form.get("id", ""))
    return redirect(url_for("index"), code=303)


@app.post("/pause")
def pause() -> Response:
    portal.set_paused(True)
    return redirect(url_for("index"), code=303)


@app.post("/resume")
def resume() -> Response:
    portal.set_paused(False)
    return redirect(url_for("index"), code=303)


@app.get("/mumble")
def mumble() -> str:
    snapshot, error = None, None
    try:
        snapshot = control("snapshot")
    except (RuntimeError, OSError, ValueError) as exc:
        error = str(exc)
    return render_template("mumble.html", snapshot=snapshot, error=error, csrf=CSRF,
                           result=request.args.get("result", ""))


@app.post("/mumble/kick")
def mumble_kick() -> Response:
    try:
        control("kick", selected=selected("session"))
    except (RuntimeError, ValueError, OSError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("mumble", result="kick"), code=303)


@app.post("/mumble/unregister")
def mumble_unregister() -> Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm registration removal in the dialog", 400)
    try:
        control("unregister", selected=selected("registration"))
    except (RuntimeError, ValueError, OSError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("mumble", result="unregister"), code=303)


@app.post("/mumble/restart")
def mumble_restart() -> Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm Mumble restart in the dialog", 400)
    try:
        control("restart")
    except (RuntimeError, OSError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("mumble", result="restart"), code=303)


@app.post("/mumble/reset-password")
def mumble_reset_password() -> Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm password reset in the dialog", 400)
    try:
        control("reset_password")
    except (RuntimeError, OSError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("mumble", result="reset"), code=303)


@app.get("/certificates")
def certificates() -> str:
    snapshot, error = None, None
    try:
        snapshot = cert_control("snapshot")
    except (RuntimeError, OSError, ValueError) as exc:
        error = str(exc)
    rows, paused = portal.list_shares()
    shares = {}
    if snapshot:
        for record in snapshot["certificates"]:
            shares[record["serial"]] = [
                {"url": f"{portal.PUBLIC_BASE}/q/{row['token']}",
                 "status": portal.share_status(row, paused), "accepted": row["accepted"]}
                for row in rows if row["filename"] == record["package"]
                and portal.share_status(row, paused) == "分享中"]
    return render_template("certificates.html", snapshot=snapshot, shares=shares,
                           csrf=CSRF, error=error, result=request.args.get("result", ""))


@app.get("/certificates/<serial>")
def certificate_detail(serial: str) -> str | Response:
    try:
        snapshot = cert_control("snapshot")
        record = next((item for item in snapshot["certificates"] if item["serial"] == serial), None)
        if record is None:
            abort(404)
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), 409)
    status_error = None
    try:
        details = cert_control("status", serial=serial, fingerprint=record["fingerprint"])["status"]
    except (RuntimeError, OSError, ValueError) as exc:
        status_error = str(exc)
        details = {"username": None, "in_groups": [], "out_groups": []}
    groups = sorted(set(details["in_groups"] + details["out_groups"]
                        + snapshot.get("group_choices", ["local-test"])))
    return render_template("certificate_detail.html", record=record, details=details,
                           groups=groups, status_error=status_error, csrf=CSRF,
                           result=request.args.get("result", ""))


@app.post("/certificates/groups")
def certificate_groups() -> Response:
    try:
        serial = request.form.get("serial", "")
        cert_control("groups", serial=serial, fingerprint=request.form.get("fingerprint", ""),
                     in_groups=group_values("in"), out_groups=group_values("out"))
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("certificate_detail", serial=serial, result="groups"), code=303)


@app.post("/certificates/issue")
def certificate_issue() -> Response:
    try:
        result = cert_control("issue", name=request.form.get("name", ""),
                              cn=request.form.get("cn", ""),
                              in_groups=group_values("in"), out_groups=group_values("out"))
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("certificate_detail", serial=result["serial"], result="issued"), code=303)


@app.post("/certificates/share")
def certificate_share() -> Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm private-key package delivery", 400)
    try:
        serial = request.form.get("serial", "")
        fingerprint = request.form.get("fingerprint", "")
        snapshot = cert_control("snapshot")
        record = next((item for item in snapshot["certificates"] if item["serial"] == serial
                       and item["fingerprint"] == fingerprint), None)
        if not record or record["revoked"] or record["expired"] or not record["package"]:
            raise ValueError("Certificate package is unavailable; refresh the page")
        if record["registered"] is False:
            raise ValueError("TAK registration must be verified before sharing")
        portal.create_share("file", f"atak:{record['package']}", 20, 3)
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("certificates", result="shared"), code=303)


@app.post("/certificates/revoke")
def certificate_revoke() -> Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm irreversible certificate revocation", 400)
    try:
        selected = selected_certificates()
        records = cert_control("validate_selection", selected=selected)["certificates"]
        for record in records:
            if record["package"]:
                portal.stop_file_shares(record["package"])
        cert_control("revoke", selected=selected)
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("certificates", result="revoked"), code=303)


@app.post("/certificates/republish")
def certificate_republish() -> Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm CRL publication and TAK restart", 400)
    try:
        cert_control("republish")
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("certificates", result="republished"), code=303)
