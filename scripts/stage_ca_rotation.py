#!/usr/bin/env python3
"""Stage a new issuing CA and Root CRL without changing the active deployment."""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
PRIVATE = RUNTIME / "pki" / "private"
PUBLIC = RUNTIME / "pki" / "public"
STAGES = RUNTIME / "ca-rotation-stage"


def command(*args: str, env: dict[str, str]) -> None:
    result = subprocess.run(args, cwd=PROJECT, env=env, capture_output=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        error = result.stderr.decode("utf-8", "replace").strip()[-500:]
        raise RuntimeError(f"{Path(args[0]).name} failed: {error}")


def fingerprint(cert: Path) -> str:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes

    return x509.load_pem_x509_certificate(cert.read_bytes()).fingerprint(hashes.SHA256()).hex().upper()


def root_config(stage: Path) -> Path:
    source = PRIVATE / "root-ca.cnf"
    old_db = (PRIVATE / "root-ca-db").as_posix()
    text = source.read_text(encoding="ascii")
    if text.count(old_db) != 1:
        raise RuntimeError("Unexpected Root CA configuration; database path was not unique")
    output = stage / "root-ca.cnf"
    output.write_text(text.replace(old_db, (stage / "root-ca-db").as_posix()),
                      encoding="ascii", newline="\n")
    return output


def issuer_config(stage: Path) -> Path:
    db = (stage / "ca-db").as_posix()
    cert = (stage / "intermediate.crt.pem").as_posix()
    key = (stage / "intermediate.key.pem").as_posix()
    output = stage / "issuing-ca.cnf"
    output.write_text(f"""[ca]
default_ca = issuing_ca

[issuing_ca]
dir = {db}
database = $dir/index.txt
new_certs_dir = $dir/newcerts
certificate = {cert}
private_key = {key}
serial = $dir/serial
crlnumber = $dir/crlnumber
default_md = sha256
default_days = 730
default_crl_days = 30
unique_subject = no
copy_extensions = none
policy = policy_any

[policy_any]
countryName = supplied
stateOrProvinceName = optional
localityName = optional
organizationName = supplied
organizationalUnitName = supplied
commonName = supplied
emailAddress = optional
""", encoding="ascii", newline="\n")
    return output


def stage(expected_old_fingerprint: str) -> Path:
    openssl = shutil.which("openssl")
    if not openssl:
        raise RuntimeError("openssl is not available on PATH")
    old_cert = PUBLIC / "intermediate.crt.pem"
    root_cert = PUBLIC / "root-ca.crt.pem"
    root_key = PRIVATE / "root-ca.key.pem"
    root_db = PRIVATE / "root-ca-db"
    old_fingerprint = fingerprint(old_cert)
    if old_fingerprint != expected_old_fingerprint.upper():
        raise RuntimeError("Active issuing CA fingerprint differs from the expected certificate")
    if not all(path.is_file() for path in (root_cert, root_key, root_db / "index.txt",
                                            root_db / "serial", root_db / "crlnumber")):
        raise RuntimeError("Root CA files are incomplete")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    STAGES.mkdir(parents=True, exist_ok=True)
    target = STAGES / f"issuing-{stamp}-{uuid.uuid4().hex[:8]}"
    target.mkdir(exist_ok=False)
    shutil.copytree(root_db, target / "root-ca-db")
    issuer_db = target / "ca-db"
    (issuer_db / "newcerts").mkdir(parents=True)
    existing_serials = {line.split("\t")[3].upper() for line in
                        (PRIVATE / "ca-db" / "index.txt").read_text(encoding="ascii").splitlines()
                        if len(line.split("\t")) >= 4}
    while True:
        first_serial = secrets.randbelow(0xE0000000) + 0x10000000
        if all(f"{first_serial + offset:X}" not in existing_serials for offset in range(100)):
            break
    for name, value in (("index.txt", ""), ("index.txt.attr", "unique_subject = no\n"),
                        ("serial", f"{first_serial:X}\n"), ("crlnumber", "1000\n")):
        (issuer_db / name).write_text(value, encoding="ascii", newline="\n")
    root_cfg = root_config(target)
    issuer_cfg = issuer_config(target)
    intermediate_password = secrets.token_urlsafe(36)
    (target / "intermediate.password").write_text(intermediate_password + "\n", encoding="ascii")
    env = os.environ.copy()
    env["TAK_ROOT_PASS"] = (RUNTIME / "secrets/root_ca_password").read_text(encoding="ascii").strip()
    env["TAK_NEW_INTERMEDIATE_PASS"] = intermediate_password
    key = target / "intermediate.key.pem"
    csr = target / "intermediate.csr.pem"
    cert = target / "intermediate.crt.pem"
    ext = target / "intermediate.ext"
    ext.write_text("[v3_intermediate_ca]\nbasicConstraints=critical,CA:TRUE,pathlen:0\n"
                   "keyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\n"
                   "authorityKeyIdentifier=keyid,issuer\n", encoding="ascii", newline="\n")
    command(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:4096",
            "-aes-256-cbc", "-pass", "env:TAK_NEW_INTERMEDIATE_PASS", "-out", str(key), env=env)
    common_name = "TAK Local Issuing CA " + stamp[:8]
    command(openssl, "req", "-new", "-sha256", "-key", str(key), "-passin",
            "env:TAK_NEW_INTERMEDIATE_PASS", "-subj",
            f"/C=TW/O=TAK Local/OU=Issuing CA/CN={common_name}", "-out", str(csr), env=env)
    command(openssl, "ca", "-batch", "-config", str(root_cfg), "-extensions",
            "v3_intermediate_ca", "-extfile", str(ext), "-days", "1825", "-notext",
            "-in", str(csr), "-out", str(cert), "-passin", "env:TAK_ROOT_PASS", env=env)
    command(openssl, "verify", "-CAfile", str(root_cert), str(cert), env=env)
    # The copied Root database records the old CA revocation for the future cutover only.
    command(openssl, "ca", "-batch", "-config", str(root_cfg), "-revoke", str(old_cert),
            "-passin", "env:TAK_ROOT_PASS", env=env)
    root_crl = target / "root-ca.crl.pem"
    command(openssl, "ca", "-gencrl", "-config", str(root_cfg), "-out", str(root_crl),
            "-passin", "env:TAK_ROOT_PASS", env=env)
    command(openssl, "verify", "-crl_check", "-CRLfile", str(root_crl),
            "-CAfile", str(root_cert), str(cert), env=env)
    command(openssl, "ca", "-gencrl", "-config", str(issuer_cfg),
            "-out", str(target / "intermediate-ca.crl.pem"),
            "-passin", "env:TAK_NEW_INTERMEDIATE_PASS", env=env)
    (target / "ca-id.txt").write_text(fingerprint(cert) + "\n", encoding="ascii")
    (target / "old-ca-id.txt").write_text(old_fingerprint + "\n", encoding="ascii")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-old-fingerprint", required=True)
    args = parser.parse_args()
    if len(args.expected_old_fingerprint) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in args.expected_old_fingerprint):
        parser.error("Expected a 64-character SHA-256 fingerprint")
    target = stage(args.expected_old_fingerprint)
    print(f"Staged issuing CA and unpublished Root CRL: {target.relative_to(PROJECT)}")
    print(f"New CA ID: {(target / 'ca-id.txt').read_text(encoding='ascii').strip()}")
    print("Active CA, Root database, service certificates and deployed CRLs are unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
