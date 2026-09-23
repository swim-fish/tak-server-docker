#!/usr/bin/env python3
"""Build a TAK ICU 7.5.1 preference profile and download QR code."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import quote, urlsplit
from xml.etree import ElementTree as ET


DESTINATION = "RTSP-Push (Video Management System)"


def build_profile(host: str, port: int, stream_path: str, username: str,
                  password: str | None = None) -> bytes:
    if not host or "://" in host or "/" in host:
        raise ValueError("--host must be a DNS name or IP address without a scheme or path")
    if not 1 <= port <= 65535:
        raise ValueError("--port must be between 1 and 65535")
    if not stream_path.startswith("live/"):
        raise ValueError("--stream-path must start with live/")
    if not username:
        raise ValueError("--username is required")

    root = ET.Element("preferences")
    group = ET.SubElement(root, "preference", {"version": "1", "name": "ICU"})
    values = {
        "broadcast_destination_type": ("class java.lang.String", DESTINATION),
        "videoServerIP": ("class java.lang.String", host),
        "videoServerPort": ("class java.lang.String", str(port)),
        "videoServerPath": ("class java.lang.String", stream_path),
        "videoServerSSL": ("class java.lang.Boolean", "true"),
        "videoServerUsername": ("class java.lang.String", username),
    }
    if password is not None:
        if not password or "\n" in password or "\r" in password:
            raise ValueError("Publishing password must be a nonempty single line")
        values["videoServerPassword"] = ("class java.lang.String", password)
    for key, (type_name, value) in values.items():
        ET.SubElement(group, "entry", {"key": key, "class": type_name}).text = value
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def build_uri(profile_url: str) -> str:
    parsed = urlsplit(profile_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("--profile-url must be an absolute HTTP or HTTPS URL")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("--profile-url must not contain credentials or a fragment")
    return "icu://download?url=" + quote(profile_url, safe="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=8322)
    parser.add_argument("--stream-path", default="live/")
    parser.add_argument("--username", default="atak-publisher")
    parser.add_argument("--profile-url", required=True)
    parser.add_argument("--password-file", type=Path,
                        help="Read the MediaMTX publishing password from a local file")
    parser.add_argument("--allow-http-password", action="store_true",
                        help="Explicitly allow password delivery over plain HTTP on a trusted LAN")
    parser.add_argument("--output-dir", type=Path, default=Path("runtime/packages/icu"))
    args = parser.parse_args()

    uri = build_uri(args.profile_url)
    password = None
    if args.password_file:
        if urlsplit(args.profile_url).scheme == "http" and not args.allow_http_password:
            parser.error("HTTP delivery of a password requires --allow-http-password")
        password = args.password_file.read_text(encoding="utf-8").rstrip("\r\n")
    profile = build_profile(args.host, args.port, args.stream_path, args.username, password)
    try:
        import qrcode
    except ImportError as exc:
        raise SystemExit("Install qrcode==8.2 and Pillow to generate the PNG") from exc

    args.output_dir.mkdir(parents=True, exist_ok=True)
    profile_path = args.output_dir / "initial.prefs"
    uri_path = args.output_dir / "icu-setup-uri.txt"
    qr_path = args.output_dir / "icu-setup.png"
    profile_path.write_bytes(profile)
    uri_path.write_text(uri + "\n", encoding="utf-8")
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(qr_path)
    print(f"Profile: {profile_path}")
    print(f"QR URI:  {uri_path}")
    print(f"QR PNG:  {qr_path}")
    print("Publishing password included in profile." if password is not None
          else "No publishing password included; enter it manually in TAK ICU if needed.")


if __name__ == "__main__":
    main()
