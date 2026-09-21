#!/usr/bin/env python3
"""Regenerate and publish the root and issuing CA CRLs for local TAK."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
PRIVATE = RUNTIME / "pki" / "private"
PUBLIC = RUNTIME / "pki" / "public"
TAK_CERTS = RUNTIME / "tak" / "certs"
ROOT_CA_DB = PRIVATE / "root-ca-db"


def write_if_missing(path: Path, value: str) -> None:
    if not path.exists():
        path.write_text(value, encoding="ascii", newline="\n")


def main() -> int:
    openssl = shutil.which("openssl")
    if not openssl:
        raise SystemExit("openssl must be available on PATH")

    root_key = PRIVATE / "root-ca.key.pem"
    root_cert = PUBLIC / "root-ca.crt.pem"
    issuing_config = PRIVATE / "issuing-ca.cnf"
    required = (
        root_key,
        root_cert,
        issuing_config,
        RUNTIME / "secrets" / "root_ca_password",
        RUNTIME / "secrets" / "intermediate_ca_password",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Missing local PKI files:\n" + "\n".join(missing))

    (ROOT_CA_DB / "newcerts").mkdir(parents=True, exist_ok=True)
    write_if_missing(ROOT_CA_DB / "index.txt", "")
    write_if_missing(ROOT_CA_DB / "index.txt.attr", "unique_subject = no\n")
    write_if_missing(ROOT_CA_DB / "serial", "1000\n")
    write_if_missing(ROOT_CA_DB / "crlnumber", "1000\n")

    root_config = PRIVATE / "root-ca.cnf"
    if not root_config.exists():
        root_config.write_text(f'''[ca]
default_ca = root_ca

[root_ca]
dir = {ROOT_CA_DB.as_posix()}
database = $dir/index.txt
new_certs_dir = $dir/newcerts
certificate = {root_cert.as_posix()}
private_key = {root_key.as_posix()}
serial = $dir/serial
crlnumber = $dir/crlnumber
default_md = sha256
default_days = 1825
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
''', encoding="ascii", newline="\n")

    env = os.environ.copy()
    env["TAK_ROOT_PASS"] = (RUNTIME / "secrets" / "root_ca_password").read_text(encoding="ascii").strip()
    env["TAK_INTERMEDIATE_PASS"] = (RUNTIME / "secrets" / "intermediate_ca_password").read_text(encoding="ascii").strip()

    root_crl = PUBLIC / "root-ca.crl.pem"
    issuing_crl = PUBLIC / "intermediate-ca.crl.pem"
    bundle = PUBLIC / "ca-chain.crl.pem"
    subprocess.run([openssl, "ca", "-gencrl", "-config", str(root_config), "-out", str(root_crl), "-passin", "env:TAK_ROOT_PASS"], check=True, env=env)
    subprocess.run([openssl, "ca", "-gencrl", "-config", str(issuing_config), "-out", str(issuing_crl), "-passin", "env:TAK_INTERMEDIATE_PASS"], check=True, env=env)
    bundle.write_bytes(issuing_crl.read_bytes() + root_crl.read_bytes())

    TAK_CERTS.mkdir(parents=True, exist_ok=True)
    for source in (root_crl, issuing_crl, bundle):
        shutil.copy2(source, TAK_CERTS / source.name)
        subprocess.run([openssl, "crl", "-in", str(source), "-noout", "-issuer", "-lastupdate", "-nextupdate"], check=True)

    print("Published root, issuing, and chain CRLs. Restart tak-server to load them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
