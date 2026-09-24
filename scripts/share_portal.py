#!/usr/bin/env python3
"""Local TAK package and ICU profile sharing portal."""

from __future__ import annotations

import html
import io
import os
import secrets
import shutil
import sqlite3
import threading
import time
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import qrcode
from flask import Flask, Response, request

from build_icu_qr import build_profile, build_uri


STATE_DIR = Path(os.environ.get("SHARE_STATE_DIR", "/state"))
FILE_DIR = Path(os.environ.get("SHARE_FILE_DIR", "/files"))
PACKAGE_DIR = Path(os.environ.get("SHARE_PACKAGE_DIR", "/imports/packages"))
ICU_DIR = Path(os.environ.get("SHARE_ICU_DIR", "/imports/icu"))
PUBLIC_BASE = os.environ.get("SHARE_PUBLIC_BASE", "http://takbox.local:8765").rstrip("/")
ADMIN_PASSWORD_FILE = Path(os.environ.get("SHARE_ADMIN_PASSWORD_FILE", "/run/secrets/share_admin_password"))
PUBLISH_PASSWORD_FILE = Path(os.environ.get("SHARE_PUBLISH_PASSWORD_FILE", "/run/secrets/mediamtx_publish_password"))
DB_PATH = STATE_DIR / "shares.sqlite3"
TIMEZONE = timezone(timedelta(hours=8), "Asia/Taipei")
MAX_FILE_SIZE = 512 * 1024 * 1024
VX_DOWNLOAD_ACTION = b"com.atakmap.android.gbr.multicastvoice.sharing.downloaded"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def local_time(timestamp: int | None) -> str:
    if timestamp is None:
        return "未設定"
    return datetime.fromtimestamp(timestamp, TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def connection():
    db = sqlite3.connect(DB_PATH, timeout=20, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=20000")
    try:
        yield db
    finally:
        db.close()


def initialize() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    FILE_DIR.mkdir(parents=True, exist_ok=True)
    with connection() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS shares (
            id TEXT PRIMARY KEY, token TEXT UNIQUE NOT NULL, kind TEXT NOT NULL,
            filename TEXT NOT NULL, stored_name TEXT NOT NULL,
            created_at INTEGER NOT NULL, expires_at INTEGER,
            max_downloads INTEGER, accepted INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active'
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS downloads (
            id TEXT PRIMARY KEY, share_id TEXT NOT NULL, started_at INTEGER NOT NULL,
            finished_at INTEGER, outcome TEXT NOT NULL, bytes_sent INTEGER NOT NULL DEFAULT 0
        )""")
        db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('paused', '0')")


def is_paused(db: sqlite3.Connection) -> bool:
    return db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0] == "1"


def share_status(row: sqlite3.Row, paused: bool, now: int | None = None) -> str:
    now = int(time.time()) if now is None else now
    if row["status"] == "stopped":
        return "已手動停止"
    if row["expires_at"] is not None and now >= row["expires_at"]:
        return "時間到期"
    if row["max_downloads"] is not None and row["accepted"] >= row["max_downloads"]:
        return "次數額滿"
    if paused:
        return "全部暫停"
    return "分享中"


def get_share(token: str) -> sqlite3.Row | None:
    if len(token) > 96:
        return None
    with connection() as db:
        return db.execute("SELECT * FROM shares WHERE token=?", (token,)).fetchone()


def list_shares() -> tuple[list[sqlite3.Row], bool]:
    with connection() as db:
        return list(db.execute("SELECT * FROM shares ORDER BY created_at DESC, rowid DESC")), is_paused(db)


def reserve_download(token: str) -> tuple[sqlite3.Row, str] | None:
    now = int(time.time())
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM shares WHERE token=?", (token,)).fetchone()
        if row is None or share_status(row, is_paused(db), now) != "分享中":
            db.rollback()
            return None
        download_id = uuid.uuid4().hex
        db.execute("UPDATE shares SET accepted=accepted+1 WHERE id=?", (row["id"],))
        db.execute("INSERT INTO downloads (id,share_id,started_at,outcome) VALUES (?,?,?,'started')",
                   (download_id, row["id"], now))
        db.commit()
        return row, download_id


def finish_download(share_id: str, download_id: str, completed: bool, bytes_sent: int) -> None:
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("UPDATE downloads SET finished_at=?,outcome=?,bytes_sent=? WHERE id=?",
                   (int(time.time()), "completed" if completed else "failed", bytes_sent, download_id))
        if completed:
            db.execute("UPDATE shares SET completed=completed+1 WHERE id=?", (share_id,))
        db.commit()


def import_choices() -> list[tuple[str, list[tuple[str, str]]]]:
    groups: list[tuple[str, list[tuple[str, str]]]] = []
    for label, title, directory, suffixes in (
        ("icu", "runtime/packages/icu", ICU_DIR, {".prefs"}),
        ("atak", "runtime/packages/atak", PACKAGE_DIR, {".dpk", ".zip"}),
    ):
        choices: list[tuple[str, str]] = []
        if not directory.is_dir():
            continue
        for item in sorted(directory.iterdir(), key=lambda path: path.name.lower()):
            if (item.is_file() and not item.is_symlink()
                    and item.suffix.lower() in suffixes
                    and 0 < item.stat().st_size <= (1024 * 1024 if label == "icu" else MAX_FILE_SIZE)
                    and not (label == "atak" and is_vx_mission_package(item))):
                choices.append((f"{label}:{item.name}", f"{item.name} ({item.stat().st_size:,} bytes)"))
        if choices:
            groups.append((title, choices))
    return groups


def is_vx_mission_package(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            manifest = archive.getinfo("MANIFEST/manifest.xml")
            if manifest.file_size > 65536:
                return False
            return VX_DOWNLOAD_ACTION in archive.read(manifest)
    except (KeyError, OSError, zipfile.BadZipFile):
        return False


def source_file(value: str, kind: str = "file") -> Path:
    if ":" not in value:
        raise ValueError("請選擇來源檔案")
    label, filename = value.split(":", 1)
    roots = {"atak": PACKAGE_DIR, "icu": ICU_DIR}
    if label not in roots or not filename or Path(filename).name != filename:
        raise ValueError("來源檔案無效")
    if (kind == "icu") != (label == "icu"):
        raise ValueError("檔案類型與來源資料夾不符")
    path = roots[label] / filename
    if (not path.is_file() or path.is_symlink()
            or path.suffix.lower() not in ({".prefs"} if kind == "icu" else {".dpk", ".zip"})
            or not 0 < path.stat().st_size <= (1024 * 1024 if kind == "icu" else MAX_FILE_SIZE)):
        raise ValueError("來源檔案不存在或超過大小限制")
    if kind == "file" and not zipfile.is_zipfile(path):
        raise ValueError("來源檔案不是有效的 ZIP／DPK")
    if kind == "file" and is_vx_mission_package(path):
        raise ValueError("Vx 任務必須從 TAK Server Data Packages 下載")
    return path


def create_share(kind: str, source: str, ttl_minutes: int | None,
                 max_downloads: int | None) -> str:
    if ttl_minutes is None and max_downloads is None:
        raise ValueError("截止時間與下載上限至少填一項")
    if ttl_minutes is not None and not 1 <= ttl_minutes <= 10080:
        raise ValueError("分享時間須介於 1 分鐘與 7 天")
    if max_downloads is not None and not 1 <= max_downloads <= 10000:
        raise ValueError("下載上限須介於 1 與 10000 次")
    if kind not in {"icu", "file"}:
        raise ValueError("分享種類無效")
    share_id = uuid.uuid4().hex
    stored_name = uuid.uuid4().hex
    target = FILE_DIR / stored_name
    if kind == "icu" and not source:
        password = PUBLISH_PASSWORD_FILE.read_text(encoding="utf-8").rstrip("\r\n")
        data = build_profile("takbox.local", 8322, "live/", "atak-publisher", password)
        target.write_bytes(data)
        filename = "initial.prefs"
    else:
        original = source_file(source, kind)
        filename = original.name
        with original.open("rb") as src, target.open("xb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
    try:
        now = int(time.time())
        with connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""INSERT INTO shares
                (id,token,kind,filename,stored_name,created_at,expires_at,max_downloads)
                VALUES (?,?,?,?,?,?,?,?)""",
                (share_id, secrets.token_urlsafe(24), kind, filename, stored_name,
                 now, now + ttl_minutes * 60 if ttl_minutes is not None else None,
                 max_downloads))
            db.commit()
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return share_id


def update_status(share_id: str) -> None:
    with connection() as db:
        db.execute("UPDATE shares SET status='stopped' WHERE id=?", (share_id,))


def stop_file_shares(filename: str) -> int:
    """Stop every copied download snapshot for a certificate package."""
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        result = db.execute("UPDATE shares SET status='stopped' WHERE kind='file' AND filename=? "
                            "AND status='active'", (filename,))
        db.commit()
        return result.rowcount


def set_paused(paused: bool) -> None:
    with connection() as db:
        db.execute("UPDATE settings SET value=? WHERE key='paused'", ("1" if paused else "0",))


def file_url(row: sqlite3.Row) -> str:
    base = f"{PUBLIC_BASE}/d/{row['token']}"
    if row["kind"] == "file":
        return f"{base}/{quote(row['filename'])}"
    return base


def qr_value(row: sqlite3.Row) -> str:
    if row["kind"] == "icu":
        return build_uri(file_url(row))
    return "tak://com.atakmap.app/import?url=" + quote(file_url(row), safe="")


def qr_png(row: sqlite3.Row) -> bytes:
    output = io.BytesIO()
    qrcode.make(qr_value(row)).save(output, format="PNG")
    return output.getvalue()


def remaining_text(seconds: int) -> str:
    days, remainder = divmod(max(0, seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days:
        return f"剩餘 {days} 天 {hours:02}:{minutes:02}:{seconds:02}"
    if hours:
        return f"剩餘 {hours}:{minutes:02}:{seconds:02}"
    return f"剩餘 {minutes:02}:{seconds:02}"


def page(title: str, body: str, script: str = "", layout: str = "public") -> bytes:
    return (f"<!doctype html><html lang='zh-Hant-TW' data-bs-theme='dark'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{esc(title)}</title>"
            "<link rel='stylesheet' href='/static/bootstrap/bootstrap.min.css'>"
            "<link rel='stylesheet' href='/static/console.css'>"
            "</head><body class='portal-page layout-" + esc(layout) + "'><main>" + body
            + "</main>" + script + "</body></html>").encode("utf-8")


def admin_page(csrf: str) -> bytes:
    rows, paused = list_shares()
    now = int(time.time())
    active_rows = [row for row in rows if share_status(row, paused) == "分享中"]
    live_links = "".join(
        f"<li id='active-{row['id']}'><strong>{esc(row['filename'])}</strong>"
        f"<a data-qr-open data-share-id='{row['id']}' data-qr-name='{esc(row['filename'])}' data-qr-image='/qr.png/{esc(row['token'])}' href='{esc(PUBLIC_BASE)}/q/{esc(row['token'])}'>"
        f"{esc(PUBLIC_BASE)}/q/{esc(row['token'])}</a></li>" for row in active_rows)
    options = "<optgroup label='即時產生'><option value='icu:new'>使用目前發布密碼建立 ICU 設定</option></optgroup>" + "".join(
        f"<optgroup label='{esc(group)}'>" + "".join(
            f"<option value='{esc(value)}'>{esc(label)}</option>" for value, label in choices)
        + "</optgroup>" for group, choices in import_choices())
    table = "".join(
        f"<tr id='row-{row['id']}' class='{'inactive' if terminal else ''}'>"
        f"<td data-label='檔案'>{esc(row['filename'])}<br><small>{esc(row['kind'])}</small></td>"
        f"<td data-label='狀態' class='{'status-live' if status == '分享中' else 'status-muted'}' id='status-{row['id']}' data-expiry='{row['expires_at'] or ''}'><span class='share-state'>{esc(status)}</span>"
        f"<small class='share-countdown' {'hidden' if status != '分享中' else ''}>{remaining_text(row['expires_at'] - now) if row['expires_at'] else '無時間限制'}</small></td>"
        f"<td data-label='已使用／上限' id='count-{row['id']}'>{row['accepted']} / {row['max_downloads'] or '∞'}"
        f"<br><small>完成 {row['completed']}</small></td>"
        f"<td data-label='建立／截止時間'>{esc(local_time(row['created_at']))}<br>截止：{esc(local_time(row['expires_at']))}</td>"
        f"<td data-label='查看'><a class='btn btn-outline-info view' data-qr-open data-share-id='{row['id']}' data-qr-name='{esc(row['filename'])}' data-qr-image='/qr.png/{esc(row['token'])}' href='{esc(PUBLIC_BASE)}/q/{esc(row['token'])}' {'hidden' if status != '分享中' else ''}>檢視 QR</a>"
        f"<span data-ended {'hidden' if status == '分享中' else ''}>{'已暫停' if status == '全部暫停' else '已結束'}</span></td>"
        f"<td data-label='控制' class='action-danger'><form data-active method='post' action='/stop' {'hidden' if terminal else ''}><input type='hidden' name='csrf' value='{csrf}'>"
        f"<input type='hidden' name='id' value='{row['id']}'>"
        f"<button class='btn btn-danger stop'>停止此分享</button></form></td></tr>"
        for row in rows for status in [share_status(row, paused, now)]
        for terminal in [share_status(row, False, now) != "分享中"])
    master = (f"<section id='master-panel' class='card master{' paused' if paused else ''}'>"
            f"<div id='master-icon' class='master-icon' aria-hidden='true'>{'⏸' if paused else '✓'}</div>"
            "<div><h2>總開關</h2><p id='master-status' class='master-status' role='status'>"
            + ("所有分享下載已暫停" if paused else "分享下載開放中") + "</p>"
            "<p id='master-detail' class='master-detail'>"
            + ("公開下載已停止" if paused else "公開連結可正常下載") + "</p></div>"
            f"<form id='master-form' method='post' action='/{'resume' if paused else 'pause'}'>"
            f"<input type='hidden' name='csrf' value='{csrf}'>"
            f"<button id='master-button' class='btn {'btn-primary' if paused else 'btn-danger stop'}'>{'恢復所有分享下載' if paused else '暫停所有分享下載'}</button>"
            "</form></section>")
    body = ("<header class='page-header'><nav class='portal-nav nav nav-pills' aria-label='控制台頁面'><a class='nav-link active' aria-current='page' href='/'>檔案分享</a><a class='nav-link' href='/mumble'>Mumble 管理</a><a class='nav-link' href='/certificates'>用戶端憑證</a></nav><h1>TAK 控制台</h1>"
            "<p class='muted'>公開入口 <code>" + esc(PUBLIC_BASE) + "</code>　｜　管理入口僅限本機　｜　"
            "<span id='live-sync' role='status' aria-live='polite'>正在同步狀態…</span></p></header>"
            + master +
            "<section class='card live'><h2>目前分享中的連結　<span id='live-count'>" + str(len(active_rows)) + "</span></h2>"
            "<p id='live-empty' class='muted' " + ("hidden" if active_rows else "") + ">目前沒有可下載的連結。</p>"
            "<ul id='live-links' class='live-links'>" + live_links + "</ul></section>"
            "<section class='card create'><h2>新增分享</h2><form class='create-form' method='post' action='/create'>"
            f"<input type='hidden' name='csrf' value='{csrf}'>"
            "<label class='field-source'>檔案來源 <select class='form-select' id='source-select' name='source' required>" + options + "</select></label>"
            "<label>停止時間（分鐘） <input class='form-control' name='ttl' type='number' min='1' max='10080' value='15'></label>"
            "<label>下載上限（次） <input class='form-control' name='limit' type='number' min='1' max='10000' value='3'></label>"
            "<p class='muted'>可只填一項；同時填寫時先達到者停止。Vx Mission 套件須從 TAK Server Data Packages 下載，不列入此 QR 分享。</p>"
            "<button class='btn btn-primary'>啟用這筆分享</button></form></section>"
            "<section class='card records share-records'><h2>分享紀錄</h2><table class='table responsive-table align-middle'><thead><tr><th>檔案</th><th>狀態</th>"
            "<th>已使用／上限</th><th>建立／截止時間</th><th>查看</th><th>控制</th></tr></thead><tbody id='share-rows' data-server-now='" + str(now) + "'>"
            + table + "</tbody></table></section>"
            "<div class='modal fade' id='share-qr-dialog' tabindex='-1' aria-labelledby='share-qr-title' aria-hidden='true'>"
            "<div class='modal-dialog modal-dialog-centered'><div class='modal-content'>"
            "<div class='modal-header'><h2 class='modal-title fs-5' id='share-qr-title'>分享 QR Code</h2>"
            "<button type='button' class='btn-close' data-bs-dismiss='modal' aria-label='關閉'></button></div>"
            "<div class='modal-body share-qr-body'><strong id='share-qr-name'></strong>"
            "<img id='share-qr-image' class='qr img-fluid rounded' alt='分享 QR Code'>"
            "<a id='share-qr-url' target='_blank' rel='noreferrer noopener'></a>"
            "<p class='muted'>掃描後請點相機顯示的完整連結。</p></div></div></div></div>")
    script = "<script src='/static/bootstrap/bootstrap.bundle.min.js' defer></script><script src='/admin.js' defer></script>"
    return page("TAK 分享管理", body, script, layout="admin")


def public_page(row: sqlite3.Row, qr: bool) -> bytes:
    kind = "TAK ICU 設定" if row["kind"] == "icu" else "ATAK Data Package／ZIP"
    uri = qr_value(row)
    body = (f"<h1>{esc(kind)}</h1><section class='card'><p>檔案：{esc(row['filename'])}</p>"
            f"<p>截止時間：{esc(local_time(row['expires_at']))}</p>"
            f"<p>下載上限：{row['max_downloads'] or '未設定'}</p>")
    if qr:
        body += (f"<img class='qr img-fluid rounded'  src='/qr.png/{esc(row['token'])}' alt='分享 QR Code'>"
                 f"<p><a class='btn btn-primary' href='{esc(uri)}'>"
                 + ("開啟 TAK ICU" if row["kind"] == "icu" else "交給 ATAK 匯入") + "</a></p>"
                 "<p class='muted'>掃描後請點相機顯示的完整連結。</p>")
    else:
        body += (f"<p><a class='btn btn-primary' href='{esc(file_url(row))}'>下載檔案</a></p>"
                 "<p class='muted'>一般瀏覽器下載後仍需手動匯入；請使用 QR 連結測試 ATAK 匯入流程。</p>")
    return page(kind, body + "</section>")


STATIC_DIR = Path(__file__).resolve().parent / "static"
if not STATIC_DIR.is_dir():
    STATIC_DIR = Path(__file__).resolve().parents[1] / "docker/share-portal/static"
app = Flask(__name__, static_folder=str(STATIC_DIR))
_init_lock = threading.Lock()
_initialized = False


@app.before_request
def prepare_public() -> None:
    global _initialized
    if not _initialized:
        with _init_lock:
            if not _initialized:
                initialize()
                _initialized = True


@app.after_request
def public_security_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; img-src 'self'; style-src 'self'; "
        "script-src 'unsafe-inline'; connect-src 'self'; form-action 'self'; base-uri 'none'")
    return response


@app.get("/healthz")
def public_healthz() -> Response:
    return Response("ok", mimetype="text/plain")


def active_share(token: str) -> tuple[sqlite3.Row | None, Response | None]:
    row = get_share(token)
    if row is None:
        return None, Response("Not found", 404)
    with connection() as db:
        status = share_status(row, is_paused(db))
    if status != "分享中":
        return None, Response("分享已停止", 410)
    return row, None


def download_response(row: sqlite3.Row, token: str) -> Response:
    path = FILE_DIR / row["stored_name"]
    if not path.is_file():
        return Response("Not found", 404)
    size = path.stat().st_size
    content_type = "application/xml; charset=utf-8" if row["kind"] == "icu" else "application/octet-stream"
    fallback = "".join(
        char if (char.isascii() and char.isalnum()) or char in "._-" else "_"
        for char in row["filename"])
    headers = {
        "Content-Length": str(size),
        "Content-Disposition": f"attachment; filename=\"{fallback}\"; filename*=UTF-8''" + quote(row["filename"]),
    }
    if request.method == "HEAD":
        return Response(status=200, content_type=content_type, headers=headers)
    reservation = reserve_download(token)
    if reservation is None:
        return Response("分享已停止", 410)
    reserved_row, download_id = reservation

    def stream_file():
        sent = 0
        completed = False
        try:
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    sent += len(chunk)
                    yield chunk
                completed = sent == size
        finally:
            finish_download(reserved_row["id"], download_id, completed, sent)

    return Response(stream_file(), status=200, content_type=content_type, headers=headers)


@app.route("/<action>/<token>", methods=["GET", "HEAD"])
def public_route(action: str, token: str) -> Response:
    if action not in {"q", "s", "qr.png", "d"}:
        return Response("Not found", 404)
    row, error = active_share(token)
    if error is not None:
        return error
    assert row is not None
    if action == "q":
        return Response(public_page(row, True), content_type="text/html; charset=utf-8")
    if action == "s" and row["kind"] == "file":
        return Response(public_page(row, False), content_type="text/html; charset=utf-8")
    if action == "qr.png":
        return Response(qr_png(row), content_type="image/png")
    if action == "d":
        return download_response(row, token)
    return Response("Not found", 404)


@app.route("/d/<token>/<path:filename>", methods=["GET", "HEAD"])
def named_download(token: str, filename: str) -> Response:
    row, error = active_share(token)
    if error is not None:
        return error
    assert row is not None
    if row["kind"] != "file" or filename != row["filename"]:
        return Response("Not found", 404)
    return download_response(row, token)
