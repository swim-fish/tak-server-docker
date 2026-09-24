#!/usr/bin/env python3
"""Issue a dedicated MediaMTX certificate and render its local configuration."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

from bootstrap_local import dns_name, ip_literal
from media_registry import load as load_media_registry, render_config


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
PKI = RUNTIME / "pki"
PRIVATE = PKI / "private"
PUBLIC = PKI / "public"
SECRETS = RUNTIME / "secrets"
CONFIG = RUNTIME / "mediamtx" / "mediamtx.yml"
TEMPLATE = PROJECT / "config" / "mediamtx" / "mediamtx.yml.template"
KEY = PKI / "mediamtx-server.key.pem"
CERT = PUBLIC / "mediamtx.crt.pem"
FULLCHAIN = PKI / "mediamtx-fullchain.pem"


def invoke(openssl: str, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run([openssl, *args], check=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dns", type=dns_name, help="DNS name used by clients")
    parser.add_argument("--ip", type=ip_literal, help="IP address used by clients")
    args = parser.parse_args()
    if not args.dns and not args.ip:
        parser.error("Specify --dns and/or --ip")

    openssl = shutil.which("openssl")
    if not openssl:
        raise SystemExit("openssl must be available on PATH")
    for required in (PRIVATE / "issuing-ca.cnf", PUBLIC / "intermediate.crt.pem",
                     PUBLIC / "root-ca.crt.pem", SECRETS / "intermediate_ca_password"):
        if not required.is_file():
            raise SystemExit(f"Missing existing TAK PKI file: {required}")
    outputs = (KEY, CERT, FULLCHAIN)
    present = [path.exists() for path in outputs]
    if any(present) and not all(present):
        raise SystemExit("MediaMTX certificate files are incomplete; inspect them before retrying")

    san = ",".join(part for part in
                   (f"DNS:{args.dns}" if args.dns else "", f"IP:{args.ip}" if args.ip else "") if part)
    env = os.environ.copy()
    env["TAK_INTERMEDIATE_PASS"] = (SECRETS / "intermediate_ca_password").read_text(encoding="ascii").strip()

    if not all(present):
        with tempfile.TemporaryDirectory(prefix="mediamtx-", dir=PRIVATE) as stage_name:
            stage = Path(stage_name)
            key = stage / "server.key.pem"
            csr = stage / "server.csr.pem"
            cert = stage / "server.crt.pem"
            ext = stage / "server.ext"
            ext.write_text("[leaf_ext]\nbasicConstraints=critical,CA:FALSE\n"
                           "keyUsage=critical,digitalSignature,keyEncipherment\n"
                           "extendedKeyUsage=serverAuth\nsubjectKeyIdentifier=hash\n"
                           "authorityKeyIdentifier=keyid,issuer\n"
                           f"subjectAltName={san}\n", encoding="ascii", newline="\n")
            invoke(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072",
                   "-out", str(key))
            invoke(openssl, "req", "-new", "-sha256", "-key", str(key),
                   "-subj", f"/C=TW/O=TAK Local/OU=Local Test/CN={args.dns or args.ip}",
                   "-out", str(csr))
            invoke(openssl, "ca", "-batch", "-config", str(PRIVATE / "issuing-ca.cnf"),
                   "-extensions", "leaf_ext", "-extfile", str(ext), "-days", "730",
                   "-notext", "-in", str(csr), "-out", str(cert),
                   "-passin", "env:TAK_INTERMEDIATE_PASS", env=env)
            verify_certificate(openssl, cert, args)
            PUBLIC.mkdir(parents=True, exist_ok=True)
            PKI.mkdir(parents=True, exist_ok=True)
            FULLCHAIN.write_bytes(cert.read_bytes() + (PUBLIC / "intermediate.crt.pem").read_bytes())
            shutil.copy2(cert, CERT)
            shutil.copy2(key, KEY)
    else:
        verify_certificate(openssl, CERT, args)

    SECRETS.mkdir(parents=True, exist_ok=True)
    publish = secret_file(SECRETS / "mediamtx_publish_password")
    read = secret_file(SECRETS / "mediamtx_read_password")
    api = secret_file(SECRETS / "mediamtx_api_password")
    registry_path = CONFIG.parent / "publishers.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {"version": 1, "publishers": {}}
    config = render_config(TEMPLATE.read_text(encoding="utf-8"), registry, publish, read, api)
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temp_config = CONFIG.with_suffix(".yml.tmp")
    temp_config.write_text(config, encoding="utf-8", newline="\n")
    temp_config.replace(CONFIG)
    viewer_state = CONFIG.parent / "viewer_state.json"
    state = json.loads(viewer_state.read_text(encoding="utf-8")) if viewer_state.exists() else {"enabled": True}
    if type(state.get("enabled")) is not bool:
        raise SystemExit("Invalid MediaMTX viewer state")
    admin_password = secret_file(SECRETS / "share_admin_password")
    for name, content in viewer_configs(read, api, admin_password).items():
        output = CONFIG.parent / name
        pending = output.with_suffix(".next")
        pending.write_text(content, encoding="utf-8", newline="\n")
        pending.replace(output)
    if not viewer_state.exists():
        viewer_state.write_text(json.dumps(state), encoding="utf-8")
    print("MediaMTX certificate, full chain, credentials, and configuration are ready.")
    return 0


def verify_certificate(openssl: str, cert: Path, args: argparse.Namespace) -> None:
    base = ["verify", "-purpose", "sslserver", "-CAfile", str(PUBLIC / "root-ca.crt.pem"),
            "-untrusted", str(PUBLIC / "intermediate.crt.pem")]
    if args.dns:
        invoke(openssl, *base, "-verify_hostname", args.dns, str(cert))
    if args.ip:
        invoke(openssl, *base, "-verify_ip", args.ip, str(cert))


def secret_file(path: Path) -> str:
    if not path.exists():
        path.write_text(secrets.token_urlsafe(32), encoding="ascii", newline="\n")
    value = path.read_text(encoding="ascii").strip()
    if not value:
        raise SystemExit(f"Empty secret: {path}")
    return value


def viewer_configs(read_password: str, api_password: str, admin_password: str,
                   ) -> dict[str, str]:
    upstream = json.dumps("rtsp://atak-viewer:" + read_password + "@mediamtx:8554/$G1")
    paths = ("paths:\n  '~^(live/.+)$':\n    source: " + upstream
             + "\n    sourceOnDemand: true\n    rtspTransport: tcp\n    rtspDemuxMpegts: true\n")
    base = ("logLevel: info\nrtsp: false\nrtmp: false\nhls: false\nsrt: false\nmoq: false\n"
            "metrics: false\npprof: false\nplayback: false\n"
            "authMethod: internal\n")
    public = (base + "authInternalUsers:\n"
              "  - user: any\n    pass:\n    ips: []\n    permissions:\n"
              "      - action: read\n        path: '~^live/.+$'\n"
              "  - user: tak-console\n    pass: " + json.dumps(api_password) +
              "\n    ips: []\n    permissions:\n      - action: api\n"
              "api: true\napiAddress: :9997\n"
              "webrtc: true\n"
              "webrtcAddress: :8889\nwebrtcLocalUDPAddress: :8189\n"
              "webrtcLocalTCPAddress: :8189\n"
              "webrtcAdditionalHosts: [takbox.local, 192.168.137.1]\n" + paths)
    preview = (base + "authInternalUsers:\n"
               "  - user: admin\n    pass: " + json.dumps(admin_password) +
               "\n    ips: []\n    permissions:\n"
               "      - action: read\n        path: '~^live/.+$'\n"
               "api: false\nwebrtc: true\nwebrtcAddress: :8889\n"
               "webrtcLocalUDPAddress: :8190\nwebrtcLocalTCPAddress: :8190\n"
               "webrtcAdditionalHosts: [127.0.0.1]\n" + paths)
    return {"viewer-public.yml": public, "viewer-preview.yml": preview}


if __name__ == "__main__":
    raise SystemExit(main())
