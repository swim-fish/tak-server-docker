#!/usr/bin/env python3
"""Authenticated TAK Server administration API client for the Windows worker."""

from __future__ import annotations

import json
import http.client
import os
import re
import socket
import ssl
import hashlib
from pathlib import Path
from urllib.parse import quote
from local_network import bind_ip


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
CERTS = RUNTIME / "tak" / "certs"
KEY = RUNTIME / "pki" / "private" / "admin.key.pem"
KEY_PASSWORD = RUNTIME / "secrets" / "leaf_key_password"
API_ROOT = "/Marti/api/user-management/api"
HOST = "takbox.local"


def api_port() -> int:
    value = os.environ.get("TAK_HTTPS_HOST_PORT")
    if value is None:
        dotenv = PROJECT / ".env"
        if dotenv.is_file():
            for line in dotenv.read_text(encoding="utf-8").splitlines():
                if line.startswith("TAK_HTTPS_HOST_PORT="):
                    value = line.partition("=")[2].strip().strip('"\'')
                    break
    value = value or "8443"
    if not re.fullmatch(r"\d{1,5}", value) or not 1 <= int(value) <= 65535:
        raise RuntimeError("Invalid TAK HTTPS host port")
    return int(value)


class TakConnection(http.client.HTTPSConnection):
    def connect(self) -> None:
        raw = socket.create_connection((bind_ip(), self.port), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def request(method: str, path: str, payload: dict | None = None) -> object:
    if method not in {"GET", "PUT", "POST", "DELETE"} or not path.startswith(API_ROOT + "/"):
        raise ValueError("Unsupported TAK administration request")
    context = ssl.create_default_context(cafile=str(CERTS / "root-ca.pem"))
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(CERTS / "admin.pem"), keyfile=str(KEY),
                            password=KEY_PASSWORD.read_text(encoding="ascii").strip())
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    connection = TakConnection(HOST, api_port(), context=context, timeout=20)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        content = response.read(1024 * 1024 + 1)
        if len(content) > 1024 * 1024:
            raise RuntimeError("TAK API response exceeded the size limit")
        if not 200 <= response.status < 300:
            raise RuntimeError(f"TAK API returned HTTP {response.status}")
        return json.loads(content) if content.strip() else None
    finally:
        connection.close()


def package_request(method: str, path: str, body: bytes | None = None,
                    content_type: str | None = None) -> bytes:
    """Limit raw TAK package calls to the endpoints needed by the Vx worker."""
    file_path = re.fullmatch(r"/Marti/api/files/[0-9a-fA-F]{64}", path)
    metadata_path = re.fullmatch(r"/Marti/api/sync/metadata/[0-9a-fA-F]{64}/(?:tool|keywords)", path)
    search_path = path.startswith("/Marti/api/sync/search?")
    allowed = ((method == "GET" and (file_path or search_path)) or
               (method == "DELETE" and file_path) or
               (method == "POST" and path == "/Marti/sync/upload") or
               (method == "PUT" and metadata_path))
    if not allowed or (body is not None and len(body) > 12 * 1024 * 1024):
        raise ValueError("Unsupported TAK package request")
    context = ssl.create_default_context(cafile=str(CERTS / "root-ca.pem"))
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(CERTS / "admin.pem"), keyfile=str(KEY),
                            password=KEY_PASSWORD.read_text(encoding="ascii").strip())
    headers = {"Content-Type": content_type} if content_type else {}
    connection = TakConnection(HOST, api_port(), context=context, timeout=30)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        content = response.read(12 * 1024 * 1024 + 1)
        if len(content) > 12 * 1024 * 1024:
            raise RuntimeError("TAK package response exceeded the size limit")
        if not 200 <= response.status < 300:
            raise RuntimeError(f"TAK package API returned HTTP {response.status}")
        if method == "GET" and file_path and hashlib.sha256(content).hexdigest().lower() != path.rsplit("/", 1)[-1].lower():
            raise RuntimeError("Downloaded TAK package SHA-256 does not match its hash")
        return content
    finally:
        connection.close()


def video_request(method: str, uid: str | None = None, *, groups: list[str] | None = None,
                  payload: dict | None = None) -> object:
    """Use only the Video V2 endpoints required for managed aliases."""
    import uuid
    from urllib.parse import urlencode

    if uid is not None:
        try:
            uid = str(uuid.UUID(uid))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Invalid video alias UID") from exc
    if method == "GET" and (groups is not None or payload is not None):
        raise ValueError("Invalid video read request")
    if method == "DELETE" and (uid is None or groups is not None or payload is not None):
        raise ValueError("Invalid video delete request")
    if method == "POST" and (uid is not None or not groups or len(groups) > 20 or
                              len(set(groups)) != len(groups) or payload is None):
        raise ValueError("Invalid video create request")
    if method not in {"GET", "DELETE", "POST"}:
        raise ValueError("Unsupported video request")
    if groups and any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}", group)
                      for group in groups):
        raise ValueError("Invalid video group")
    path = "/Marti/api/video" + ("/" + uid if uid else "")
    if groups:
        path += "?" + urlencode([("group", group) for group in groups])
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload is not None else None
    if body is not None and len(body) > 256 * 1024:
        raise ValueError("Video alias request is too large")
    context = ssl.create_default_context(cafile=str(CERTS / "root-ca.pem"))
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(CERTS / "admin.pem"), keyfile=str(KEY),
                            password=KEY_PASSWORD.read_text(encoding="ascii").strip())
    connection = TakConnection(HOST, api_port(), context=context, timeout=20)
    try:
        connection.request(method, path, body=body,
                           headers={"Content-Type": "application/json"} if body is not None else {})
        response = connection.getresponse()
        content = response.read(1024 * 1024 + 1)
        if len(content) > 1024 * 1024:
            raise RuntimeError("TAK video API response exceeded the size limit")
        if method == "GET" and response.status == 404:
            return None
        if not 200 <= response.status < 300:
            raise RuntimeError(f"TAK video API returned HTTP {response.status}")
        return json.loads(content) if content.strip() else None
    finally:
        connection.close()


def get_groups(username: str) -> dict:
    data = request("GET", f"{API_ROOT}/get-groups-for-user/{quote(username, safe='')}")
    if not isinstance(data, dict) or data.get("username") != username:
        raise RuntimeError("TAK API group identity did not match the requested user")
    return data


def update_groups(username: str, in_groups: list[str], out_groups: list[str]) -> None:
    both = sorted(set(in_groups) & set(out_groups))
    payload = {"username": username, "groupList": both,
               "groupListIN": sorted(set(in_groups) - set(both)),
               "groupListOUT": sorted(set(out_groups) - set(both))}
    request("PUT", f"{API_ROOT}/update-groups", payload)
