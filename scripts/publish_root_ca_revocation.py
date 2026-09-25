#!/usr/bin/env python3
"""Publish a staged Root CRL that revokes the previous local issuing CA."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

from cryptography import x509
from cryptography.hazmat.primitives import hashes

import prepare_ca_rotation


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
PRIVATE = RUNTIME / "pki" / "private"
PUBLIC = RUNTIME / "pki" / "public"
TAK_CERTS = RUNTIME / "tak" / "certs"
STAGES = RUNTIME / "ca-rotation-stage"


def certificate(path: Path) -> x509.Certificate:
    return x509.load_pem_x509_certificate(path.read_bytes())


def ca_id(path: Path) -> str:
    return certificate(path).fingerprint(hashes.SHA256()).hex().upper()


def preflight(path: Path) -> tuple[Path, Path, Path, bytes]:
    stage = path.resolve(strict=True)
    if stage.parent != STAGES.resolve(strict=True) or not stage.name.startswith("issuing-"):
        raise ValueError("Select an issuing stage directly under runtime/ca-rotation-stage")
    old_id = (stage / "old-ca-id.txt").read_text(encoding="ascii").strip()
    new_id = (stage / "ca-id.txt").read_text(encoding="ascii").strip()
    if ca_id(PUBLIC / "intermediate.crt.pem") != new_id:
        raise RuntimeError("The staged issuing CA is not active")
    archive = RUNTIME / "pki" / "archive" / old_id
    old_cert_path = archive / "intermediate.crt.pem"
    if ca_id(old_cert_path) != old_id:
        raise RuntimeError("The archived previous CA does not match the stage")
    root = certificate(PUBLIC / "root-ca.crt.pem")
    old_cert = certificate(old_cert_path)
    new_cert = certificate(PUBLIC / "intermediate.crt.pem")
    root_crl_bytes = (stage / "root-ca.crl.pem").read_bytes()
    crl = x509.load_pem_x509_crl(root_crl_bytes)
    if crl.issuer != root.subject or not crl.is_signature_valid(root.public_key()):
        raise RuntimeError("Staged Root CRL signature or issuer is invalid")
    if crl.next_update_utc <= datetime.now(timezone.utc):
        raise RuntimeError("Staged Root CRL has expired")
    if (crl.get_revoked_certificate_by_serial_number(old_cert.serial_number) is None or
            crl.get_revoked_certificate_by_serial_number(new_cert.serial_number) is not None):
        raise RuntimeError("Staged Root CRL does not revoke exactly the intended CA generation")
    active_crl = x509.load_pem_x509_crl((PUBLIC / "root-ca.crl.pem").read_bytes())
    if active_crl.get_revoked_certificate_by_serial_number(old_cert.serial_number) is not None:
        raise RuntimeError("The old CA is already revoked in the active Root CRL")
    stage_db = stage / "root-ca-db"
    active_db = PRIVATE / "root-ca-db"
    if not (stage_db / "index.txt").is_file() or not (active_db / "index.txt").is_file():
        raise RuntimeError("Root CA database is incomplete")
    lines = (stage_db / "index.txt").read_text(encoding="ascii").splitlines()
    old_serial = format(old_cert.serial_number, "X")
    new_serial = format(new_cert.serial_number, "X")
    if not any(line.startswith("R\t") and f"\t{old_serial}\t" in line for line in lines):
        raise RuntimeError("Staged Root database does not mark the old CA revoked")
    if not any(line.startswith("V\t") and f"\t{new_serial}\t" in line for line in lines):
        raise RuntimeError("Staged Root database does not mark the new CA valid")
    core_path = RUNTIME / "tak" / "CoreConfig.xml"
    core = core_path.read_text(encoding="utf-8")
    previous = '<crl _name="TAK Previous Issuing CA" crlFile="/opt/tak/certs/files/old-intermediate-ca.crl.pem" />'
    if core.count(previous) != 1 or 'crlFile="/opt/tak/certs/files/root-ca.crl.pem"' in core:
        raise RuntimeError("TAK CRL configuration differs from the expected transition state")
    root_entry = '<crl _name="TAK Root CA" crlFile="/opt/tak/certs/files/root-ca.crl.pem" />'
    updated_core = core.replace(previous, previous + "\n      " + root_entry).encode("utf-8")
    ElementTree.fromstring(updated_core)
    return stage, archive, active_db, updated_core


def publish(path: Path) -> None:
    stage, archive, active_db, updated_core = preflight(path)
    old_db = archive / "root-ca-db-before-revocation"
    if old_db.exists():
        raise RuntimeError("A previous Root database archive already exists")
    if active_db.resolve(strict=True).parent != PRIVATE.resolve(strict=True):
        raise RuntimeError("Root database move target is outside the local runtime")
    if old_db.parent.resolve(strict=True) != archive.resolve(strict=True):
        raise RuntimeError("Root database archive is outside the local runtime")
    backup = prepare_ca_rotation.create_snapshot()
    subprocess.run(["docker", "compose", "stop", "tak-server"], cwd=PROJECT,
                   capture_output=True, check=True, timeout=120,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        shutil.move(str(active_db), str(old_db))
        shutil.copytree(stage / "root-ca-db", active_db)
        root_crl = (stage / "root-ca.crl.pem").read_bytes()
        (PUBLIC / "root-ca.crl.pem").write_bytes(root_crl)
        (TAK_CERTS / "root-ca.crl.pem").write_bytes(root_crl)
        bundle = ((PUBLIC / "intermediate-ca.crl.pem").read_bytes() +
                  (archive / "intermediate-ca.crl.pem").read_bytes() + root_crl)
        (PUBLIC / "ca-chain.crl.pem").write_bytes(bundle)
        (TAK_CERTS / "ca-chain.crl.pem").write_bytes(bundle)
        (RUNTIME / "tak" / "CoreConfig.xml").write_bytes(updated_core)
    except BaseException:
        print(f"Publication interrupted. Snapshot: {backup.relative_to(PROJECT)}")
        raise
    subprocess.run(["docker", "compose", "up", "-d", "--no-build", "tak-server"],
                   cwd=PROJECT, capture_output=True, check=True, timeout=240,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    print(f"Root CRL published; backup: {backup.relative_to(PROJECT)}")
    print("Verify new and old client certificates on 8089 and 8443 separately.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    stage, _, _, _ = preflight(args.stage)
    if args.apply:
        publish(stage)
    else:
        print(f"Ready to publish Root CRL from {stage.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
