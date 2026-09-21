#!/usr/bin/env python3
"""Revoke one certificate with the TAK issuing CA and publish a new CRL."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
PRIVATE = RUNTIME / "pki" / "private"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("certificate", type=Path, help="Issued PEM certificate to revoke")
    parser.add_argument("--reason", default="cessationOfOperation", choices=("unspecified", "keyCompromise", "CACompromise", "affiliationChanged", "superseded", "cessationOfOperation", "certificateHold", "removeFromCRL"))
    args = parser.parse_args()

    certificate = args.certificate.resolve()
    if not certificate.is_file():
        raise SystemExit(f"Certificate not found: {certificate}")
    openssl = shutil.which("openssl")
    if not openssl:
        raise SystemExit("openssl must be available on PATH")

    password_file = RUNTIME / "secrets" / "intermediate_ca_password"
    env = os.environ.copy()
    env["TAK_INTERMEDIATE_PASS"] = password_file.read_text(encoding="ascii").strip()
    config = PRIVATE / "issuing-ca.cnf"
    subprocess.run([openssl, "ca", "-config", str(config), "-revoke", str(certificate), "-crl_reason", args.reason, "-passin", "env:TAK_INTERMEDIATE_PASS"], check=True, env=env)
    subprocess.run([sys.executable, str(PROJECT / "scripts" / "refresh_tak_crls.py")], check=True)
    print("Revoked certificate and published updated CRLs. Restart tak-server to load them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
