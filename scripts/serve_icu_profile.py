#!/usr/bin/env python3
"""Serve one TAK ICU preference profile to devices on the local hotspot."""

from __future__ import annotations

import argparse
from ipaddress import ip_address, ip_network
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from xml.etree import ElementTree as ET


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="192.168.137.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--allow-subnet", default="192.168.137.0/24")
    parser.add_argument("--profile", type=Path, default=Path("runtime/packages/icu/initial.prefs"))
    parser.add_argument("--allow-http-password", action="store_true",
                        help="Explicitly allow serving a publishing password over plain HTTP")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    allowed_subnet = ip_network(args.allow_subnet, strict=False)
    if allowed_subnet.version != 4:
        parser.error("--allow-subnet must be an IPv4 network")
    profile = args.profile.resolve(strict=True)
    if not profile.is_file() or not 0 < profile.stat().st_size <= 32768:
        parser.error("Profile must be a nonempty file of at most 32 KiB")
    if any(entry.get("key") == "videoServerPassword"
           for entry in ET.parse(profile).iter("entry")) and not args.allow_http_password:
        parser.error("Profile contains a password; HTTP serving requires --allow-http-password")

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:
            self._respond(head_only=True)

        def do_GET(self) -> None:
            self._respond(head_only=False)

        def _respond(self, head_only: bool) -> None:
            if ip_address(self.client_address[0]) not in allowed_subnet:
                self.send_error(403)
                return
            if self.path != "/download":
                self.send_error(404)
                return
            data = profile.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head_only:
                self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            print(f"{self.client_address[0]} {format % args}", flush=True)

    with ThreadingHTTPServer((args.bind, args.port), Handler) as server:
        print(f"ICU profile server: http://{args.bind}:{args.port}/download", flush=True)
        print("Press Ctrl+C to stop serving the profile.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
