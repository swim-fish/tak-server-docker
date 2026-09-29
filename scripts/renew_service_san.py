#!/usr/bin/env python3
"""Reissue only the three service leaves with DNS and current bind-IP SANs.

The issuing CA, service private keys, client identities, and passwords stay in place.
Stage first, stop the three services, apply, then recreate their containers.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtendedKeyUsageOID

from bootstrap_local import dns_name
from local_network import bind_ip


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
PKI = RUNTIME / "pki"
PRIVATE = PKI / "private"
PUBLIC = PKI / "public"
SECRETS = RUNTIME / "secrets"
STAGES = PKI / "service-san-renewals"
TARGETS = {
    "runtime/pki/public/takserver.crt.pem": "public/takserver.crt.pem",
    "runtime/pki/private/takserver.csr.pem": "private/takserver.csr.pem",
    "runtime/pki/private/takserver.ext": "private/takserver.ext",
    "runtime/pki/private/takserver.p12": "private/takserver.p12",
    "runtime/tak/certs/takserver.jks": "tak/takserver.jks",
    "runtime/pki/public/mumble.crt.pem": "public/mumble.crt.pem",
    "runtime/pki/private/mumble.csr.pem": "private/mumble.csr.pem",
    "runtime/pki/private/mumble.ext": "private/mumble.ext",
    "runtime/pki/mumble-fullchain.pem": "mumble-fullchain.pem",
    "runtime/pki/public/mediamtx.crt.pem": "public/mediamtx.crt.pem",
    "runtime/pki/mediamtx-fullchain.pem": "mediamtx-fullchain.pem",
}
SERVICES = {
    "takserver": (PRIVATE / "takserver.key.pem", "serverAuth,clientAuth"),
    "mumble": (PRIVATE / "mumble.key.pem", "serverAuth"),
    "mediamtx": (PKI / "mediamtx-server.key.pem", "serverAuth"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(*args: str, env: dict[str, str] | None = None, timeout: int = 120) -> str:
    result = subprocess.run(args, cwd=PROJECT, env=env, capture_output=True, text=True,
                            timeout=timeout,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        detail = result.stderr.strip()[-500:]
        raise RuntimeError(f"{Path(args[0]).name} failed: {detail}")
    return result.stdout


def tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} is unavailable")
    return found


def secret_env() -> dict[str, str]:
    env = os.environ.copy()
    for variable, file_name in (("TAK_INTERMEDIATE_PASS", "intermediate_ca_password"),
                                ("TAK_LEAF_PASS", "leaf_key_password"),
                                ("TAK_STORE_PASS", "tak_store_password")):
        value = (SECRETS / file_name).read_text(encoding="ascii").strip()
        if not value:
            raise RuntimeError(f"Empty secret file: {file_name}")
        env[variable] = value
    return env


def active_ca_id() -> str:
    cert = x509.load_pem_x509_certificate((PUBLIC / "intermediate.crt.pem").read_bytes())
    return cert.fingerprint(hashes.SHA256()).hex()


def check_rotation_idle() -> None:
    job = RUNTIME / "tak-cert-control" / "ca-rotation-job.json"
    if job.exists():
        state = json.loads(job.read_text(encoding="utf-8")).get("state")
        if state in {"staging", "cutover", "renewing", "revoking"}:
            raise RuntimeError("A CA rotation is active; finish it before renewing service SANs")


def check_certificate(path: Path, dns: str, ip: str, *, exact_san: bool) -> x509.Certificate:
    openssl = tool("openssl")
    common = ("-purpose", "sslserver", "-CAfile", str(PUBLIC / "root-ca.crt.pem"),
              "-untrusted", str(PUBLIC / "intermediate.crt.pem"))
    command(openssl, "verify", *common, "-verify_hostname", dns, str(path))
    if exact_san:
        command(openssl, "verify", *common, "-verify_ip", ip, str(path))
    cert = x509.load_pem_x509_certificate(path.read_bytes())
    if exact_san:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        names = set(san.get_values_for_type(x509.DNSName))
        addresses = set(san.get_values_for_type(x509.IPAddress))
        if names != {dns} or addresses != {ipaddress.ip_address(ip)}:
            raise RuntimeError(f"Unexpected SAN in {path.name}")
        basic = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        if basic.ca or ExtendedKeyUsageOID.SERVER_AUTH not in eku:
            raise RuntimeError(f"Invalid service certificate extensions in {path.name}")
    return cert


def check_key_matches(openssl: str, key: Path, cert: Path, *, encrypted: bool,
                      env: dict[str, str]) -> None:
    options = ("-passin", "env:TAK_LEAF_PASS") if encrypted else ()
    public_key = command(openssl, "pkey", "-in", str(key), *options, "-pubout", env=env)
    certificate_key = command(openssl, "x509", "-in", str(cert), "-pubkey", "-noout")
    if public_key.strip() != certificate_key.strip():
        raise RuntimeError(f"Private key and certificate do not match: {cert.name}")


def concat(output: Path, *sources: Path) -> None:
    output.write_bytes(b"".join(source.read_bytes().rstrip(b"\n") + b"\n" for source in sources))


def stage(dns: str, ip: str) -> Path:
    dns = dns_name(dns)
    ip = str(ipaddress.IPv4Address(ip))
    if ip != bind_ip():
        raise RuntimeError("Requested IP SAN must equal the configured TAK_BIND_IP")
    check_rotation_idle()
    openssl, keytool = tool("openssl"), tool("keytool")
    env = secret_env()
    required = [PRIVATE / "issuing-ca.cnf", PUBLIC / "root-ca.crt.pem",
                PUBLIC / "intermediate.crt.pem", PUBLIC / "ca-chain.pem"]
    required += [PROJECT / target for target in TARGETS]
    required += [key for key, _ in SERVICES.values()]
    if any(not path.is_file() or path.is_symlink() for path in required):
        raise RuntimeError("An existing PKI, keystore, or service file is missing or is a symlink")
    old_ca = active_ca_id()
    STAGES.mkdir(parents=True, exist_ok=True)
    stage_path = STAGES / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                           + "-" + uuid.uuid4().hex[:8])
    stage_path.mkdir()
    for part in ("public", "private", "tak"):
        (stage_path / part).mkdir()
    metadata = {}
    for name, (key, eku) in SERVICES.items():
        current = PUBLIC / f"{name}.crt.pem"
        old = check_certificate(current, dns, ip, exact_san=False)
        encrypted = name != "mediamtx"
        check_key_matches(openssl, key, current, encrypted=encrypted, env=env)
        csr = stage_path / "private" / f"{name}.csr.pem"
        ext = stage_path / "private" / f"{name}.ext"
        cert = stage_path / "public" / f"{name}.crt.pem"
        ext.write_text("[leaf_ext]\nbasicConstraints=critical,CA:FALSE\n"
                       "keyUsage=critical,digitalSignature,keyEncipherment\n"
                       f"extendedKeyUsage={eku}\nsubjectKeyIdentifier=hash\n"
                       "authorityKeyIdentifier=keyid,issuer\n"
                       f"subjectAltName=DNS:{dns},IP:{ip}\n", encoding="ascii", newline="\n")
        options = ("-passin", "env:TAK_LEAF_PASS") if encrypted else ()
        command(openssl, "req", "-new", "-sha256", "-key", str(key), *options,
                "-subj", f"/C=TW/O=TAK Local/OU=Local Test/CN={dns}",
                "-out", str(csr), env=env)
        command(openssl, "ca", "-batch", "-config", str(PRIVATE / "issuing-ca.cnf"),
                "-extensions", "leaf_ext", "-extfile", str(ext), "-days", "730", "-notext",
                "-in", str(csr), "-out", str(cert), "-passin", "env:TAK_INTERMEDIATE_PASS",
                env=env)
        new = check_certificate(cert, dns, ip, exact_san=True)
        check_key_matches(openssl, key, cert, encrypted=encrypted, env=env)
        metadata[name] = {"old_serial": format(old.serial_number, "X"),
                          "new_serial": format(new.serial_number, "X"),
                          "old_sha256": old.fingerprint(hashes.SHA256()).hex(),
                          "new_sha256": new.fingerprint(hashes.SHA256()).hex()}
    concat(stage_path / "mumble-fullchain.pem", stage_path / "public/mumble.crt.pem",
           PUBLIC / "intermediate.crt.pem")
    concat(stage_path / "mediamtx-fullchain.pem", stage_path / "public/mediamtx.crt.pem",
           PUBLIC / "intermediate.crt.pem")
    command(openssl, "pkcs12", "-export", "-name", "takserver",
            "-inkey", str(PRIVATE / "takserver.key.pem"), "-passin", "env:TAK_LEAF_PASS",
            "-in", str(stage_path / "public/takserver.crt.pem"),
            "-certfile", str(PUBLIC / "ca-chain.pem"),
            "-out", str(stage_path / "private/takserver.p12"),
            "-passout", "env:TAK_STORE_PASS", env=env)
    command(keytool, "-importkeystore", "-noprompt", "-srckeystore",
            str(stage_path / "private/takserver.p12"), "-srcstoretype", "PKCS12",
            "-srcstorepass:env", "TAK_STORE_PASS", "-destkeystore",
            str(stage_path / "tak/takserver.jks"), "-deststoretype", "JKS",
            "-deststorepass:env", "TAK_STORE_PASS", "-destkeypass:env", "TAK_STORE_PASS",
            env=env)
    exported = stage_path / "tak/exported.crt.pem"
    command(keytool, "-exportcert", "-rfc", "-alias", "takserver", "-keystore",
            str(stage_path / "tak/takserver.jks"), "-storepass:env", "TAK_STORE_PASS",
            "-file", str(exported), env=env)
    embedded = x509.load_pem_x509_certificate(exported.read_bytes())
    if embedded.fingerprint(hashes.SHA256()).hex() != metadata["takserver"]["new_sha256"]:
        raise RuntimeError("The staged TAK keystore contains a different certificate")
    if active_ca_id() != old_ca:
        raise RuntimeError("The active issuing CA changed during staging")
    manifest = {"state": "staged", "created_at": datetime.now(timezone.utc).isoformat(),
                "dns": dns, "ip": ip, "ca_sha256": old_ca, "certificates": metadata,
                "files": {target: {"old_sha256": digest(PROJECT / target),
                                   "new_sha256": digest(stage_path / source), "source": source}
                          for target, source in TARGETS.items()}}
    (stage_path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return stage_path


def load_stage(path: Path, state: str) -> tuple[Path, dict]:
    if path.is_symlink():
        raise RuntimeError("A symlinked stage is not supported")
    path = path.resolve(strict=True)
    if path.parent != STAGES.resolve(strict=True):
        raise RuntimeError("Stage must be a direct child of runtime/pki/service-san-renewals")
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("state") != state or set(manifest.get("files", {})) != set(TARGETS):
        raise RuntimeError(f"Stage is not in the expected {state} state")
    if manifest.get("ca_sha256") != active_ca_id():
        raise RuntimeError("The active issuing CA changed after staging")
    for target, source in TARGETS.items():
        if manifest["files"][target].get("source") != source:
            raise RuntimeError("Stage file mapping is invalid")
    return path, manifest


def require_services_stopped() -> None:
    output = command(tool("docker"), "compose", "ps", "--all", "--format", "json").strip()
    rows = json.loads(output) if output.startswith("[") else [
        json.loads(line) for line in output.splitlines() if line.strip()]
    states = {row.get("Service"): row.get("State") for row in rows}
    for service in ("tak-server", "mumble", "mediamtx"):
        if states.get(service) != "exited":
            raise RuntimeError(f"Stop {service} before replacing its certificate")


def replace(source: Path, target: Path) -> None:
    pending = target.with_name(target.name + ".san-renew-pending")
    shutil.copy2(source, pending)
    os.replace(pending, target)


def save_manifest(path: Path, manifest: dict) -> None:
    pending = path / "manifest.pending"
    pending.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, path / "manifest.json")


def apply(path: Path) -> None:
    path, manifest = load_stage(path, "staged")
    check_rotation_idle()
    require_services_stopped()
    for target, record in manifest["files"].items():
        source = path / record["source"]
        if source.is_symlink() or digest(source) != record["new_sha256"]:
            raise RuntimeError(f"Staged file changed: {record['source']}")
        if digest(PROJECT / target) != record["old_sha256"]:
            raise RuntimeError(f"Active file changed since staging: {target}")
    for name in SERVICES:
        check_certificate(path / f"public/{name}.crt.pem", manifest["dns"],
                          manifest["ip"], exact_san=True)
    backup = path / "backup"
    backup.mkdir(exist_ok=False)
    for target in TARGETS:
        saved = backup / target
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT / target, saved)
        if digest(saved) != manifest["files"][target]["old_sha256"]:
            raise RuntimeError(f"Backup verification failed: {target}")
    try:
        for target, record in manifest["files"].items():
            replace(path / record["source"], PROJECT / target)
            if digest(PROJECT / target) != record["new_sha256"]:
                raise RuntimeError(f"Deployment verification failed: {target}")
    except Exception:
        for target in TARGETS:
            replace(backup / target, PROJECT / target)
        raise
    manifest["state"] = "applied"
    manifest["applied_at"] = datetime.now(timezone.utc).isoformat()
    save_manifest(path, manifest)


def rollback(path: Path) -> None:
    path, manifest = load_stage(path, "applied")
    require_services_stopped()
    for target, record in manifest["files"].items():
        if digest(PROJECT / target) != record["new_sha256"]:
            raise RuntimeError(f"Active file changed since application: {target}")
        if digest(path / "backup" / target) != record["old_sha256"]:
            raise RuntimeError(f"Backup changed: {target}")
    for target in TARGETS:
        replace(path / "backup" / target, PROJECT / target)
        if digest(PROJECT / target) != manifest["files"][target]["old_sha256"]:
            raise RuntimeError(f"Rollback verification failed: {target}")
    manifest["state"] = "rolled_back"
    manifest["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
    save_manifest(path, manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    staging = sub.add_parser("stage", help="Sign and validate replacement service leaves")
    staging.add_argument("--dns", default="takbox.local")
    staging.add_argument("--ip", default=bind_ip())
    for action in ("apply", "rollback"):
        sub.add_parser(action).add_argument("stage", type=Path)
    args = parser.parse_args()
    if args.action == "stage":
        path = stage(args.dns, args.ip)
        print(f"Validated service SAN renewal stage: {path}")
    elif args.action == "apply":
        apply(args.stage)
        print("Service certificates installed; recreate tak-server, mumble, and mediamtx.")
    else:
        rollback(args.stage)
        print("Previous service certificates restored; recreate tak-server, mumble, and mediamtx.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
