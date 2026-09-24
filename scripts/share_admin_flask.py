#!/usr/bin/env python3
"""Loopback-only Flask administration for TAK file sharing and Mumble."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_file, url_for
from markupsafe import Markup

import share_portal as portal
import media_registry as media
from console_ui import breadcrumb, navbar
from build_icu_qr import build_profile
from icu_profiles import SQUADS, stream_path


CONTROL_DIR = Path(os.environ.get("MUMBLE_CONTROL_DIR", "/control"))
CERT_CONTROL_DIR = Path(os.environ.get("TAK_CERT_CONTROL_DIR", "/cert-control"))
OPERATIONS_DIR = portal.STATE_DIR / "operations"
ADMIN_PASSWORD = portal.ADMIN_PASSWORD_FILE.read_text(encoding="utf-8").strip()
if len(ADMIN_PASSWORD) < 24:
    raise RuntimeError("Share admin password must contain at least 24 characters")
CSRF = hmac.new(ADMIN_PASSWORD.encode(), b"share-admin-csrf-v1", hashlib.sha256).hexdigest()
portal.initialize()
OPERATIONS_DIR.mkdir(parents=True, exist_ok=True)
APP_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
if not TEMPLATE_DIR.is_dir():
    TEMPLATE_DIR = APP_DIR.parent / "docker/share-portal/templates"
if not STATIC_DIR.is_dir():
    STATIC_DIR = APP_DIR.parent / "docker/share-portal/static"
app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))


@app.context_processor
def shared_console_navigation() -> dict:
    return {
        "console_nav": Markup(navbar(request.path)),
        "console_breadcrumb": lambda items: Markup(breadcrumb(items)),
    }


@app.after_request
def security_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN" if request.path.startswith("/media/preview/") else "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; img-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-src 'self'; "
        "frame-ancestors 'self'; form-action 'self'; base-uri 'none'")
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
    if request.method in {"POST", "PATCH", "DELETE"}:
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
        preview_whep = request.path.startswith("/media/preview/live/") and (
            request.path.endswith("/whep") or "/whep/" in request.path)
        if preview_whep and origin is None:
            abort(403)
        if not preview_whep and not hmac.compare_digest(request.form.get("csrf", ""), CSRF):
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
    return worker_control(CERT_CONTROL_DIR, action, timeout=600 if action in {"batch_issue", "group_batch"} else 270,
                          **parameters)


def operation_path(operation_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", operation_id):
        raise ValueError("Invalid operation ID")
    return OPERATIONS_DIR / (operation_id + ".json")


def read_operation(operation_id: str, kind: str) -> dict:
    path = operation_path(operation_id)
    if not path.is_file():
        raise ValueError("Operation was not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("kind") != kind:
        raise ValueError("Operation type does not match")
    return data


def save_operation(operation_id: str, data: dict) -> None:
    path = operation_path(operation_id)
    pending = path.with_suffix("." + uuid.uuid4().hex + ".pending")
    pending.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(pending, path)


def begin_operation(operation_id: str, kind: str) -> bool:
    path = operation_path(operation_id)
    try:
        with path.open("x", encoding="utf-8") as output:
            json.dump({"kind": kind, "state": "processing", "results": []}, output)
        return True
    except FileExistsError:
        read_operation(operation_id, kind)
        return False


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


def provision_values() -> dict:
    kind = request.form.get("kind", "")
    ttl = int(request.form.get("ttl", "20"))
    limit = int(request.form.get("limit", "3"))
    if not 1 <= ttl <= 10080 or not 1 <= limit <= 10000:
        raise ValueError("Share expiry or download limit is invalid")
    values = {"kind": kind, "ttl": ttl, "limit": limit}
    if kind == "tak":
        chosen = selected_certificates()
        records = cert_control("validate_selection", selected=chosen)["certificates"]
        if len(records) != len(chosen):
            raise ValueError("Certificate selection changed; refresh the page")
        for record in records:
            if record.get("revoked") or record.get("expired") or record.get("registered") is not True or not record.get("package"):
                raise ValueError("A selected certificate cannot be shared")
        values.update(selected=chosen, records=records)
    elif kind == "device":
        name = request.form.get("name", "").strip()
        path = request.form.get("path", "").strip()
        if not 1 <= len(name) <= 80 or not path:
            raise ValueError("Device name and Stream Path are required")
        values.update(name=name, path=path)
    elif kind == "icu":
        squad = request.form.get("squad", "default")
        person = request.form.get("person", "")
        mode = request.form.get("icu_mode", "standard")
        if mode not in {"standard", "advanced"}:
            raise ValueError("Invalid ICU mode")
        custom = request.form.get("custom", "") if mode == "advanced" else ""
        if mode == "advanced" and not custom:
            raise ValueError("Advanced ICU Stream Path is required")
        path = stream_path(squad, person, custom)
        values.update(squad=squad, person=person, custom=custom, icu_mode=mode,
                      stream_path=path, expected_path=path + "VIDEO_1")
    else:
        raise ValueError("Select a provisioning purpose")
    return values


@app.get("/provision")
def provision() -> str:
    flow = request.args.get("flow", "")
    if flow == "vx":
        return render_template("vx_provision.html", step="configure", job_id=uuid.uuid4().hex, csrf=CSRF)
    if flow == "tak-new":
        group_choices = ["local-test"]
        group_error = None
        try:
            group_choices = sorted(set(cert_control("snapshot").get("group_choices", [])) | {"local-test"})
        except (RuntimeError, OSError, ValueError) as exc:
            group_error = str(exc)
        return render_template("new_certificate_provision.html", step="configure", csrf=CSRF,
                               group_choices=group_choices, group_error=group_error)
    snapshot = None
    error = None
    if flow == "tak":
        try:
            snapshot = cert_control("snapshot")
        except (RuntimeError, OSError, ValueError) as exc:
            error = str(exc)
    return render_template("provision.html", step="configure" if flow else "choose", flow=flow,
                           snapshot=snapshot, error=error, csrf=CSRF, squads=SQUADS)


def new_certificate_values() -> dict:
    names = request.form.getlist("name")
    cns = request.form.getlist("cn")
    ins = request.form.getlist("in_groups")
    outs = request.form.getlist("out_groups")
    if not 1 <= len(names) <= 10 or any(len(values) != len(names) for values in (cns, ins, outs)):
        raise ValueError("Enter between 1 and 10 complete device rows")
    items = []
    seen = set()
    for name, cn, in_text, out_text in zip(names, cns, ins, outs):
        name, cn = name.strip(), cn.strip()
        if (not 1 <= len(name) <= 80 or any(ord(char) < 32 for char in name) or
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,62}", cn) or cn in seen):
            raise ValueError("Each row needs a display name and unique certificate CN")
        groups = []
        for value in (in_text, out_text):
            entries = [part.strip() for part in value.split(",") if part.strip()]
            if len(entries) != len(set(entries)) or len(entries) > 50 or any(
                    not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}", part) for part in entries):
                raise ValueError("Invalid or duplicate group in a device row")
            groups.append(sorted(entries))
        if not any(groups):
            raise ValueError("Each device needs at least one In or Out group")
        seen.add(cn)
        items.append({"name": name, "cn": cn, "in_groups": groups[0], "out_groups": groups[1]})
    ttl = int(request.form.get("ttl", "20"))
    limit = int(request.form.get("limit", "3"))
    if not 1 <= ttl <= 10080 or not 1 <= limit <= 10000:
        raise ValueError("Share expiry or download limit is invalid")
    return {"items": items, "ttl": ttl, "limit": limit}


@app.post("/provision/tak-new/preview")
def new_certificate_preview() -> str | Response:
    try:
        values = new_certificate_values()
    except (ValueError, TypeError) as exc:
        return Response(str(exc), 400)
    return render_template("new_certificate_provision.html", step="preview", values=values,
                           job_id=uuid.uuid4().hex, csrf=CSRF)


def run_certificate_batch(job_id: str, receipt: dict) -> dict:
    batch = cert_control("batch_issue", job_id=job_id, items=receipt["values"]["items"])["batch"]
    receipt["batch"] = batch
    save_operation(job_id, receipt)
    shared = {entry["serial"] for entry in receipt["results"]}
    for entry in batch["items"]:
        if entry["state"] != "registered" or entry["serial"] in shared:
            continue
        try:
            share_id = portal.create_share("file", f"atak:{entry['package']}",
                                           receipt["values"]["ttl"], receipt["values"]["limit"],
                                           display_name=f"{entry['request']['cn']}-{entry['serial']}")
            receipt["results"].append({"serial": entry["serial"], "label": entry["request"]["name"],
                                       "share_id": share_id})
            save_operation(job_id, receipt)
        except (RuntimeError, OSError, ValueError) as exc:
            receipt["error"] = str(exc)[:300]
    receipt["state"] = "complete" if batch["state"] == "complete" and len(receipt["results"]) == len(
        batch["items"]) else "partial"
    save_operation(job_id, receipt)
    return receipt


@app.post("/provision/tak-new/execute")
def new_certificate_execute() -> Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm certificate issuance before execution", 400)
    job_id = request.form.get("job_id", "")
    try:
        values = json.loads(request.form.get("values", ""))
        if not isinstance(values, dict) or not isinstance(values.get("items"), list):
            raise ValueError("Invalid batch preview")
        if (not 1 <= int(values.get("ttl", 0)) <= 10080 or
                not 1 <= int(values.get("limit", 0)) <= 10000):
            raise ValueError("Invalid batch share limits")
        if begin_operation(job_id, "provision:tak-new"):
            receipt = read_operation(job_id, "provision:tak-new")
            receipt["values"] = values
            save_operation(job_id, receipt)
        else:
            receipt = read_operation(job_id, "provision:tak-new")
            if receipt["values"] != values:
                raise ValueError("Batch settings changed after preview")
        if receipt["state"] != "complete":
            try:
                run_certificate_batch(job_id, receipt)
            except (RuntimeError, OSError, ValueError) as exc:
                receipt.update(state="partial", error=str(exc)[:300])
                save_operation(job_id, receipt)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return Response(str(exc), 400)
    return redirect(url_for("new_certificate_result", job_id=job_id), code=303)


@app.get("/provision/tak-new/result/<job_id>")
def new_certificate_result(job_id: str) -> str | Response:
    try:
        receipt = read_operation(job_id, "provision:tak-new")
    except (ValueError, OSError, json.JSONDecodeError):
        return Response("Batch operation was not found", 404)
    shares = []
    for entry in receipt["results"]:
        row = portal.get_share_by_id(entry["share_id"])
        if row is not None:
            shares.append((entry, row, portal.local_time(row["expires_at"])))
    return render_template("new_certificate_provision.html", step="result", receipt=receipt,
                           shares=shares, csrf=CSRF, public_base=portal.PUBLIC_BASE,
                           job_id=job_id)


@app.post("/provision/tak-new/retry")
def new_certificate_retry() -> Response:
    job_id = request.form.get("job_id", "")
    try:
        receipt = read_operation(job_id, "provision:tak-new")
        if receipt["state"] != "complete":
            run_certificate_batch(job_id, receipt)
    except (RuntimeError, OSError, ValueError) as exc:
        if "receipt" not in locals():
            return Response(str(exc), 409)
        receipt.update(state="partial", error=str(exc)[:300])
        save_operation(job_id, receipt)
    return redirect(url_for("new_certificate_result", job_id=job_id), code=303)


@app.post("/provision/vx/prepare")
def vx_prepare() -> str | Response:
    job_id = request.form.get("job_id", "")
    try:
        package = cert_control("vx_prepare", job_id=job_id)["package"]
        if package["state"] != "prepared":
            return redirect(url_for("vx_result", job_id=job_id), code=303)
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), 409)
    return render_template("vx_provision.html", step="preview", job_id=job_id,
                           package=package, csrf=CSRF)


@app.post("/provision/vx/replace")
def vx_replace() -> Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm fixed-name replacement before execution", 400)
    job_id = request.form.get("job_id", "")
    try:
        cert_control("vx_replace", job_id=job_id)
    except (RuntimeError, OSError, ValueError):
        # The host worker journal records the failed stage and any deleted hashes.
        pass
    return redirect(url_for("vx_result", job_id=job_id), code=303)


@app.get("/provision/vx/result/<job_id>")
def vx_result(job_id: str) -> str | Response:
    try:
        package = cert_control("vx_status", job_id=job_id)["package"]
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), 404)
    return render_template("vx_provision.html", step="result", job_id=job_id,
                           package=package, csrf=CSRF)


@app.post("/provision/vx/restore")
def vx_restore() -> Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm backup restore before execution", 400)
    job_id = request.form.get("job_id", "")
    try:
        cert_control("vx_restore", job_id=job_id)
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("vx_result", job_id=job_id), code=303)


@app.post("/provision/preview")
def provision_preview() -> str | Response:
    try:
        values = provision_values()
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), 400)
    return render_template("provision.html", step="preview", flow=values["kind"], values=values,
                           csrf=CSRF, squads=SQUADS, operation_id=uuid.uuid4().hex)


@app.post("/provision/execute")
def provision_execute() -> str | Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm provisioning before execution", 400)
    try:
        values = provision_values()
        operation_id = request.form.get("operation_id", "")
        if not begin_operation(operation_id, "provision:" + values["kind"]):
            return redirect(url_for("provision_result", operation_id=operation_id), code=303)
        receipt = read_operation(operation_id, "provision:" + values["kind"])
        if values["kind"] == "tak":
            for record in values["records"]:
                share_id = portal.create_share("file", f"atak:{record['package']}", values["ttl"], values["limit"],
                                               display_name=f"{record['cn']}-{record['serial']}")
                receipt["results"].append({"label": record["name"], "share_id": share_id})
                save_operation(operation_id, receipt)
        elif values["kind"] == "icu":
            owner = "squad:" + values["squad"]
            publisher = media.ensure_squad(values["squad"], values["expected_path"])
            profile = build_profile("takbox.local", 8322, values["stream_path"],
                                    publisher["user"], publisher["password"])
            share_id = portal.create_share("icu", "", values["ttl"], values["limit"], profile=profile,
                                           media_owner=owner, media_path=values["stream_path"],
                                           display_name=(f"ICU-ADV-{values['stream_path'].strip('/')}"
                                                         if values["icu_mode"] == "advanced" else
                                                         f"ICU-{values['squad']}-{values['person'] or '未指定'}"))
            receipt["results"].append({"label": values["expected_path"], "share_id": share_id})
            save_operation(operation_id, receipt)
        else:
            receipt["device_key"], _ = media.create_device(values["name"], values["path"])
            save_operation(operation_id, receipt)
        receipt["state"] = "complete"
        save_operation(operation_id, receipt)
    except (RuntimeError, OSError, ValueError) as exc:
        if "receipt" not in locals():
            return Response(str(exc), 409)
        receipt.update(state="failed", error=str(exc))
        save_operation(operation_id, receipt)
    return redirect(url_for("provision_result", operation_id=operation_id), code=303)


@app.get("/provision/result/<operation_id>")
def provision_result(operation_id: str) -> str | Response:
    try:
        kind = read_operation_kind(operation_id)
        if not kind.startswith("provision:"):
            raise ValueError("Operation type does not match")
        receipt = read_operation(operation_id, kind)
    except (OSError, ValueError, json.JSONDecodeError):
        return Response("Operation was not found", 404)
    if receipt["state"] == "processing":
        return Response("Operation is in progress; inspect its state before retrying", 409)
    results = []
    for item in receipt["results"]:
        row = portal.get_share_by_id(item["share_id"])
        if row is not None:
            results.append((item["label"], row, portal.local_time(row["expires_at"])))
    return render_template("provision.html", step="result", flow=receipt["kind"].removeprefix("provision:"),
                           results=results, device_key=receipt.get("device_key"),
                           error=receipt.get("error"), public_base=portal.PUBLIC_BASE, csrf=CSRF)


def read_operation_kind(operation_id: str) -> str:
    return json.loads(operation_path(operation_id).read_text(encoding="utf-8"))["kind"]


@app.get("/media")
def media_management() -> str:
    registry, paths, viewer, error = {"publishers": {}}, [], None, None
    try:
        registry = media.load()
        paths = [{**item, "public_url": "http://takbox.local:8889/" + quote(item["name"], safe="/") + "/",
                  "preview_url": "/media/preview/" + quote(item["name"], safe="/") + "/"}
                 for item in media.active_paths()]
        viewer = media.viewer_status()
    except (RuntimeError, OSError, ValueError) as exc:
        error = str(exc)
    rows = [(key, item) for key, item in registry["publishers"].items()]
    return render_template("media.html", rows=rows, paths=paths, viewer=viewer, error=error, csrf=CSRF,
                           result=request.args.get("result", ""), operation_id=uuid.uuid4().hex)


@app.get("/media/status")
def media_live_status() -> Response:
    try:
        return jsonify(media.viewer_status())
    except (RuntimeError, OSError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 503


@app.route("/media/preview/<path:path>", methods=["GET", "HEAD", "OPTIONS", "POST", "PATCH", "DELETE"])
def media_preview_proxy(path: str) -> Response:
    """Relay only the local WebRTC reader through the authenticated admin origin."""
    if not path.startswith("live/") or "/whip" in path.lower() or "/v3/" in path.lower():
        return Response("Not found", 404)
    is_whep = path.endswith("/whep") or "/whep/" in path
    if request.method in {"POST", "PATCH", "DELETE"} and not is_whep:
        return Response("Method not allowed", 405)
    if request.method == "GET" and "text/html" in request.headers.get("Accept", "") and not path.endswith("/"):
        suffix = "?" + request.query_string.decode("ascii", "ignore") if request.query_string else ""
        return redirect(request.path + "/" + suffix, code=308)
    max_body = 1024 * 1024
    if request.content_length is not None and request.content_length > max_body:
        return Response("Request too large", 413)
    body = request.get_data(cache=False)
    if len(body) > max_body:
        return Response("Request too large", 413)
    credential = base64.b64encode(("admin:" + ADMIN_PASSWORD).encode()).decode("ascii")
    headers = {"Authorization": "Basic " + credential}
    for key in ("Content-Type", "Accept", "If-Match", "If-None-Match"):
        if request.headers.get(key):
            headers[key] = request.headers[key]
    upstream = "http://media-preview:8889/" + path
    if request.query_string:
        upstream += "?" + request.query_string.decode("ascii", "ignore")
    relay_request = Request(upstream, data=body if request.method in {"POST", "PATCH"} else None,
                            method=request.method, headers=headers)
    try:
        relay_response = urlopen(relay_request, timeout=20)
    except HTTPError as exc:
        relay_response = exc
    except (OSError, URLError):
        return Response("Preview backend unavailable", 502)
    with relay_response:
        output = relay_response.read(max_body + 1)
        if len(output) > max_body:
            return Response("Preview response too large", 502)
        result_headers = {}
        for key in ("Content-Type", "Location", "ETag", "Link", "Allow", "Access-Control-Expose-Headers"):
            value = relay_response.headers.get(key)
            if value:
                if key == "Location":
                    value = value.replace("http://media-preview:8889/", "/media/preview/")
                    if value.startswith("/live/"):
                        value = "/media/preview" + value
                result_headers[key] = value
        return Response(output, status=relay_response.status, headers=result_headers)


@app.post("/media/viewer")
def media_viewer_switch() -> Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm public viewer switch", 400)
    try:
        media.set_viewer_enabled(request.form.get("enabled") == "yes")
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("media_management", result="viewer"), code=303)


@app.post("/media/device/reveal")
def media_device_reveal() -> Response:
    key = request.form.get("key", "")
    item = media.load()["publishers"].get(key)
    if not item or item["kind"] != "device" or not item["enabled"]:
        return Response("Device is unavailable", 404)
    return jsonify({scheme: media.device_url(item, scheme) for scheme in ("rtsp", "rtsps")})


@app.get("/media/device/qr/<key>/<scheme>")
def media_device_qr(key: str, scheme: str) -> Response:
    if scheme not in {"rtsp", "rtsps"}:
        return Response("Unsupported protocol", 404)
    item = media.load()["publishers"].get(key)
    if not item or item["kind"] != "device" or not item["enabled"]:
        return Response("Device is unavailable", 404)
    import io
    import qrcode
    output = io.BytesIO()
    qrcode.make(media.device_url(item, scheme)).save(output, format="PNG")
    return Response(output.getvalue(), content_type="image/png")


@app.post("/media/update")
def media_update() -> str | Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm publisher changes", 400)
    action = request.form.get("action", "")
    keys = request.form.getlist("publisher")
    try:
        ttl = int(request.form.get("ttl", "20"))
        limit = int(request.form.get("limit", "3"))
        if not 1 <= ttl <= 10080 or not 1 <= limit <= 10000:
            raise ValueError("Invalid QR expiry or download limit")
        operation_id = request.form.get("operation_id", "")
        if not begin_operation(operation_id, "media:update"):
            return redirect(url_for("media_result", operation_id=operation_id), code=303)
        receipt = read_operation(operation_id, "media:update")
        receipt["action"] = action
        save_operation(operation_id, receipt)
        if action == "reshare":
            if not 1 <= len(keys) <= 100 or len(keys) != len(set(keys)):
                raise ValueError("Select between 1 and 100 ICU squads")
            registry = media.load()["publishers"]
            if any(key not in registry or registry[key]["kind"] != "squad" or not registry[key]["enabled"]
                   for key in keys):
                raise ValueError("Select enabled ICU squads only")
            changed = [(key, registry[key]) for key in keys]
        else:
            changed = media.update_many(keys, action)
        previous_labels = {(row["media_owner"], row["media_path"]): portal.share_label(row)
                           for row in reversed(portal.list_shares()[0]) if row["media_owner"] and row["media_path"]}
        for key, item in changed:
            stopped = portal.stop_media_shares(key) if action != "reshare" else 0
            kicked = media.kick_publishers({item["user"]}) if action != "reshare" else []
            shares = []
            if action in {"reset", "reshare"} and item["kind"] == "squad":
                for actual in item["paths"]:
                    path = actual.removesuffix("VIDEO_1")
                    profile = build_profile("takbox.local", 8322, path, item["user"], item["password"])
                    share_id = portal.create_share("icu", "", ttl, limit, profile=profile,
                                                   media_owner=key, media_path=path,
                                                   display_name=previous_labels.get((key, path)))
                    shares.append(portal.get_share_by_id(share_id))
            receipt["results"].append({"key": key, "name": item["name"], "stopped": stopped,
                                       "kicked": len(kicked), "share_ids": [row["id"] for row in shares]})
            save_operation(operation_id, receipt)
        receipt["state"] = "complete"
        save_operation(operation_id, receipt)
    except (RuntimeError, OSError, ValueError) as exc:
        if "receipt" not in locals():
            return Response(str(exc), 409)
        receipt.update(state="failed", error=str(exc))
        save_operation(operation_id, receipt)
    return redirect(url_for("media_result", operation_id=operation_id), code=303)


@app.get("/media/result/<operation_id>")
def media_result(operation_id: str) -> str | Response:
    try:
        receipt = read_operation(operation_id, "media:update")
    except (OSError, ValueError, json.JSONDecodeError):
        return Response("Operation was not found", 404)
    if receipt["state"] == "processing":
        return Response("Operation is in progress; inspect its state before retrying", 409)
    results = []
    for item in receipt["results"]:
        shares = [portal.get_share_by_id(share_id) for share_id in item["share_ids"]]
        results.append({**item, "shares": [row for row in shares if row is not None]})
    return render_template("media_result.html", action=receipt.get("action"), results=results,
                           error=receipt.get("error"), public_base=portal.PUBLIC_BASE, csrf=CSRF)


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
         "filename": row["filename"], "display_name": portal.share_label(row),
         "kind": row["kind"],
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


def certificate_group_index(records: list[dict], choices: list[str] | None = None) -> tuple[list[dict], list[dict]]:
    groups: dict[str, dict] = {name: {"name": name, "in": [], "out": [], "both": []}
                               for name in (choices or [])}
    unassigned = []
    for record in records:
        in_groups = set(record.get("in_groups") or [])
        out_groups = set(record.get("out_groups") or [])
        if not in_groups and not out_groups:
            unassigned.append(record)
        for name in in_groups | out_groups:
            lanes = groups.setdefault(name, {"name": name, "in": [], "out": [], "both": []})
            lane = "both" if name in in_groups and name in out_groups else "in" if name in in_groups else "out"
            lanes[lane].append(record)
    return [groups[name] for name in sorted(groups, key=str.casefold)], unassigned


@app.get("/certificates/groups")
def certificate_groups_overview() -> str:
    snapshot, error = None, None
    try:
        snapshot = cert_control("snapshot")
    except (RuntimeError, OSError, ValueError) as exc:
        error = str(exc)
    groups, unassigned = certificate_group_index(snapshot["certificates"], snapshot.get("group_choices")) if snapshot else ([], [])
    records = [{key: record.get(key) for key in ("serial", "fingerprint", "name", "cn", "in_groups",
                                                 "out_groups", "revoked", "expired", "registered")}
               for record in snapshot["certificates"]] if snapshot else []
    last = snapshot.get("last_result") if snapshot else None
    batch_result = last.get("result", {}).get("batch") if request.args.get("result") and last and last.get("action") == "group_batch" else None
    return render_template("certificate_groups.html", groups=groups, unassigned=unassigned,
                           records=records, total=len(records), error=error, csrf=CSRF,
                           batch_result=batch_result)


@app.post("/certificates/groups/batch")
def certificate_groups_batch() -> Response:
    if request.form.get("confirmation") != "yes":
        return Response("Confirm certificate group changes", 400)
    try:
        changes = json.loads(request.form.get("changes", ""))
        if not isinstance(changes, list) or not 1 <= len(changes) <= 100:
            raise ValueError("Select between 1 and 100 certificate group changes")
        result = cert_control("group_batch", changes=changes)["batch"]
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
        return Response(str(exc), 409)
    return redirect(url_for("certificate_groups_overview", result=result["state"]), code=303)


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
        portal.create_share("file", f"atak:{record['package']}", 20, 3,
                            display_name=f"{record['cn']}-{record['serial']}")
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
