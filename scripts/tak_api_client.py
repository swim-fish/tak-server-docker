#!/usr/bin/env python3
"""Authenticated TAK Server administration API client for the Windows worker."""

from __future__ import annotations

import json
import http.client
import os
import re
import socket
import ssl
from pathlib import Path
from urllib.parse import quote


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
CERTS = RUNTIME / "tak" / "certs"
KEY = RUNTIME / "pki" / "private" / "admin.key.pem"
KEY_PASSWORD = RUNTIME / "secrets" / "leaf_key_password"
API_ROOT = "/Marti/api/user-management/api"
HOST = "takbox.local"
HOTSPOT_IP = "192.168.137.1"


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
        raw = socket.create_connection((HOTSPOT_IP, self.port), timeout=self.timeout)
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
