#!/usr/bin/env python3
"""Remove a revoked previous issuing CA from the TAK trusted CA stores."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes

import prepare_ca_rotation


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
PUBLIC = RUNTIME / "pki" / "public"
TAK_CERTS = RUNTIME / "tak" / "certs"
ALIAS = "tak-issuing-old"
STORES = (TAK_CERTS / "truststore-root.jks", TAK_CERTS / "fed-truststore.jks")


def keytool(store: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env["TAK_STORE_PASS"] = (RUNTIME / "secrets" / "tak_store_password").read_text().strip()
    return subprocess.run(["keytool", *args, "-keystore", str(store),
                           "-storepass:env", "TAK_STORE_PASS"], cwd=PROJECT, env=env,
                          capture_output=True, timeout=45,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def exported(store: Path, alias: str) -> x509.Certificate | None:
    result = keytool(store, "-exportcert", "-rfc", "-alias", alias)
    if result.returncode:
        return None
    return x509.load_pem_x509_certificate(result.stdout)


def preflight(old_id: str) -> None:
    archive = RUNTIME / "pki" / "archive" / old_id
    old_cert = x509.load_pem_x509_certificate((archive / "intermediate.crt.pem").read_bytes())
    if old_cert.fingerprint(hashes.SHA256()).hex().upper() != old_id:
        raise RuntimeError("Archived previous CA ID does not match")
    root_crl = x509.load_pem_x509_crl((PUBLIC / "root-ca.crl.pem").read_bytes())
    if root_crl.get_revoked_certificate_by_serial_number(old_cert.serial_number) is None:
        raise RuntimeError("Previous issuing CA is not in the published Root CRL")
    expected_new = x509.load_pem_x509_certificate((PUBLIC / "intermediate.crt.pem").read_bytes())
    expected_root = x509.load_pem_x509_certificate((PUBLIC / "root-ca.crt.pem").read_bytes())
    for store in STORES:
        for alias, expected in ((ALIAS, old_cert), ("tak-issuing", expected_new),
                                ("tak-root", expected_root)):
            actual = exported(store, alias)
            if actual is None or actual.fingerprint(hashes.SHA256()) != expected.fingerprint(hashes.SHA256()):
                raise RuntimeError(f"Unexpected {alias} certificate in {store.name}")


def apply(old_id: str) -> None:
    preflight(old_id)
    backup = prepare_ca_rotation.create_snapshot()
    subprocess.run(["docker", "compose", "stop", "tak-server"], cwd=PROJECT,
                   capture_output=True, check=True, timeout=120,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        for store in STORES:
            result = keytool(store, "-delete", "-alias", ALIAS)
            if result.returncode or exported(store, ALIAS) is not None:
                raise RuntimeError(f"Could not remove the previous CA from {store.name}")
    except BaseException:
        print(f"Truststore update interrupted. Snapshot: {backup.relative_to(PROJECT)}")
        raise
    subprocess.run(["docker", "compose", "up", "-d", "--no-build", "tak-server"],
                   cwd=PROJECT, capture_output=True, check=True, timeout=240,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    print(f"Previous CA trust anchor removed; backup: {backup.relative_to(PROJECT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old_ca_id")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    old_id = args.old_ca_id.upper()
    if len(old_id) != 64 or any(character not in "0123456789ABCDEF" for character in old_id):
        raise ValueError("Old CA ID must be a SHA-256 fingerprint")
    preflight(old_id)
    if args.apply:
        apply(old_id)
    else:
        print("Ready to remove the revoked previous CA from both TAK truststores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
