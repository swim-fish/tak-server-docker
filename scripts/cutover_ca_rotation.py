#!/usr/bin/env python3
"""Switch the local test stack to a staged issuing CA without publishing Root revocation."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

from cryptography import x509
from cryptography.hazmat.primitives import hashes

import prepare_ca_rotation
import tak_certificate_host as host


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
PRIVATE = RUNTIME / "pki" / "private"
PUBLIC = RUNTIME / "pki" / "public"
TAK_CERTS = RUNTIME / "tak" / "certs"
PACKAGES = RUNTIME / "packages" / "atak"
STAGES = RUNTIME / "ca-rotation-stage"


def cert(path: Path) -> x509.Certificate:
    return x509.load_pem_x509_certificate(path.read_bytes())


def fingerprint(path: Path) -> str:
    return cert(path).fingerprint(hashes.SHA256()).hex().upper()


def run(*args: str, env: dict[str, str] | None = None, timeout: int = 180) -> None:
    result = subprocess.run(args, cwd=PROJECT, env=env, timeout=timeout, capture_output=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        detail = (result.stderr or result.stdout).decode("utf-8", "replace").strip()[-600:]
        raise RuntimeError(f"{Path(args[0]).name} failed: {detail}")


def stage_paths(path: Path) -> tuple[Path, Path, dict]:
    stage = path.resolve(strict=True)
    if stage.parent != STAGES.resolve(strict=True) or not stage.name.startswith("issuing-"):
        raise ValueError("Select an issuing stage directly under runtime/ca-rotation-stage")
    artifacts = stage / "artifacts"
    manifest = json.loads((artifacts / "manifest.json").read_text(encoding="utf-8"))
    if fingerprint(stage / "intermediate.crt.pem") != manifest["new_ca_id"]:
        raise RuntimeError("Candidate CA fingerprint differs from its artifact manifest")
    if fingerprint(PUBLIC / "intermediate.crt.pem") != (stage / "old-ca-id.txt").read_text().strip():
        raise RuntimeError("The active issuing CA changed after this stage was prepared")
    if not (artifacts / "packages" / manifest["devices"]["alpha"]["package"]).is_file():
        raise RuntimeError("Alpha replacement DPK is missing")
    if (PRIVATE / "ca-db" / "index.txt").read_bytes() == (stage / "ca-db" / "index.txt").read_bytes():
        raise RuntimeError("The candidate may already be active")
    return stage, artifacts, manifest


def put(source: Path, target: Path) -> None:
    if not source.is_file() or source.is_symlink():
        raise RuntimeError(f"Candidate source is missing or unsafe: {source.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def prepare_authentication(artifacts: Path, alpha: dict) -> bytes:
    tree = ElementTree.parse(RUNTIME / "tak" / "UserAuthenticationFile.xml")
    root = tree.getroot()
    namespace = "http://bbn.com/marti/xml/bindings"
    admin = next((item for item in root if item.get("identifier") == "admin"), None)
    if admin is None or admin.get("role") != "ROLE_ADMIN" or "fingerprint" not in admin.attrib:
        raise RuntimeError("Administrator authentication entry is unexpected")
    admin_fp = fingerprint(artifacts / "public" / "admin.crt.pem")
    admin.set("fingerprint", ":".join(admin_fp[index:index + 2] for index in range(0, 64, 2)))
    if any(item.get("identifier") == alpha["cn"] for item in root):
        raise RuntimeError("The replacement Alpha CN is already registered")
    user = ElementTree.SubElement(root, f"{{{namespace}}}User", {
        "identifier": alpha["cn"],
        "fingerprint": ":".join(alpha["fingerprint"][index:index + 2]
                                for index in range(0, 64, 2)),
    })
    ElementTree.SubElement(user, f"{{{namespace}}}groupList").text = "team-alpha"
    ElementTree.register_namespace("", namespace)
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def prepared_core_config(old_crl_name: str) -> bytes:
    config = (RUNTIME / "tak" / "CoreConfig.xml").read_text(encoding="utf-8")
    pattern = r'<crl _name="TAK Local Issuing CA" crlFile="/opt/tak/certs/files/intermediate-ca\.crl\.pem"\s*/>'
    matches = list(re.finditer(pattern, config))
    if len(matches) != 1 or old_crl_name in config:
        raise RuntimeError("TAK TLS CRL configuration has changed")
    previous = (f'<crl _name="TAK Previous Issuing CA" '
                f'crlFile="/opt/tak/certs/files/{old_crl_name}" />')
    match = matches[0]
    return (config[:match.end()] + "\n      " + previous + config[match.end():]).encode("utf-8")


def cutover(path: Path) -> None:
    stage, artifacts, manifest = stage_paths(path)
    alpha = manifest["devices"]["alpha"]
    old_ca_id = fingerprint(PUBLIC / "intermediate.crt.pem")
    new_ca_id = manifest["new_ca_id"]
    archive = RUNTIME / "pki" / "archive" / old_ca_id
    archive_record = RUNTIME / "tak-cert-control" / "archive" / f"{old_ca_id}.json"
    if archive.exists() or archive_record.exists():
        raise RuntimeError("The active CA has already been archived")
    if archive.parent.resolve() != (RUNTIME / "pki" / "archive").resolve():
        raise RuntimeError("Archive path is outside the local runtime")
    if (PRIVATE / "ca-db").resolve(strict=True).parent != PRIVATE.resolve(strict=True):
        raise RuntimeError("Active CA database path is outside the local runtime")
    auth_xml = prepare_authentication(artifacts, alpha)
    old_crl_name = "old-intermediate-ca.crl.pem"
    core_xml = prepared_core_config(old_crl_name)
    old_inventory = host.inventory()
    backup = prepare_ca_rotation.create_snapshot()
    archive.mkdir(parents=True, exist_ok=False)
    archive_record.parent.mkdir(parents=True, exist_ok=True)
    archive_record.write_text(json.dumps({"ca_id": old_ca_id,
                                          "issuer_serial": format(cert(PUBLIC / "intermediate.crt.pem").serial_number, "X"),
                                          "archived_at": datetime.now(timezone.utc).isoformat(),
                                          "certificates": old_inventory}, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    put(PUBLIC / "intermediate.crt.pem", archive / "intermediate.crt.pem")
    put(PUBLIC / "intermediate-ca.crl.pem", archive / "intermediate-ca.crl.pem")
    put(RUNTIME / "tak-cert-control" / "registry.json", archive / "registry.json")
    run("docker", "compose", "down", timeout=240)
    try:
        shutil.move(str(PRIVATE / "ca-db"), str(archive / "ca-db"))
        shutil.copytree(stage / "ca-db", PRIVATE / "ca-db")
        for source, target in (
            (stage / "intermediate.key.pem", PRIVATE / "intermediate.key.pem"),
            (stage / "intermediate.csr.pem", PRIVATE / "intermediate.csr.pem"),
            (stage / "intermediate.ext", PRIVATE / "intermediate.ext"),
            (stage / "intermediate.crt.pem", PUBLIC / "intermediate.crt.pem"),
            (artifacts / "ca-chain.pem", PUBLIC / "ca-chain.pem"),
            (stage / "intermediate-ca.crl.pem", PUBLIC / "intermediate-ca.crl.pem"),
            (artifacts / "private" / "takserver.p12", PRIVATE / "takserver.p12"),
            (artifacts / "tak-certs" / "takserver.jks", TAK_CERTS / "takserver.jks"),
            (artifacts / "tak-certs" / "truststore-root.jks", TAK_CERTS / "truststore-root.jks"),
            (artifacts / "tak-certs" / "fed-truststore.jks", TAK_CERTS / "fed-truststore.jks"),
            (artifacts / "tak-certs" / "admin.p12", TAK_CERTS / "admin.p12"),
            (artifacts / "tak-certs" / "admin.pem", TAK_CERTS / "admin.pem"),
            (stage / "intermediate.crt.pem", TAK_CERTS / "intermediate-ca.pem"),
            (stage / "intermediate-ca.crl.pem", TAK_CERTS / "intermediate-ca.crl.pem"),
            (archive / "intermediate.crt.pem", TAK_CERTS / "old-intermediate-ca.pem"),
            (archive / "intermediate-ca.crl.pem", TAK_CERTS / old_crl_name),
            (artifacts / "mumble-fullchain.pem", RUNTIME / "pki" / "mumble-fullchain.pem"),
            (artifacts / "private" / "mumble.key.pem", RUNTIME / "pki" / "mumble-server.key.pem"),
            (artifacts / "mediamtx-fullchain.pem", RUNTIME / "pki" / "mediamtx-fullchain.pem"),
            (artifacts / "private" / "mediamtx.key.pem", RUNTIME / "pki" / "mediamtx-server.key.pem"),
            (artifacts / "packages" / "caCert.p12", PACKAGES / "caCert.p12"),
            (artifacts / "packages" / "atak-alpha-rotated.p12", PACKAGES / "clientCert.p12"),
        ):
            put(source, target)
        for name in ("takserver", "admin", "mumble", "mediamtx"):
            put(artifacts / "public" / f"{name}.crt.pem", PUBLIC / f"{name}.crt.pem")
            if name != "mediamtx":
                put(artifacts / "private" / f"{name}.key.pem", PRIVATE / f"{name}.key.pem")
                put(artifacts / "private" / f"{name}.csr.pem", PRIVATE / f"{name}.csr.pem")
        put(artifacts / "public" / "alpha.crt.pem", PUBLIC / "atak-client.crt.pem")
        put(artifacts / "private" / "alpha.key.pem", PRIVATE / "atak-client.key.pem")
        put(artifacts / "private" / "alpha.csr.pem", PRIVATE / "atak-client.csr.pem")
        (TAK_CERTS / "atak-client.pem").write_bytes(
            (artifacts / "public" / "alpha.crt.pem").read_bytes() +
            (stage / "intermediate.crt.pem").read_bytes() +
            (PUBLIC / "root-ca.crt.pem").read_bytes())
        (RUNTIME / "secrets" / "intermediate_ca_password").write_bytes(
            (stage / "intermediate.password").read_bytes())
        (RUNTIME / "secrets" / "leaf_key_password").write_bytes(
            (artifacts / "private" / "leaf.password").read_bytes())
        new_chain_crl = (stage / "intermediate-ca.crl.pem").read_bytes() + (
            archive / "intermediate-ca.crl.pem").read_bytes() + (PUBLIC / "root-ca.crl.pem").read_bytes()
        (PUBLIC / "ca-chain.crl.pem").write_bytes(new_chain_crl)
        (TAK_CERTS / "ca-chain.crl.pem").write_bytes(new_chain_crl)
        (RUNTIME / "tak" / "CoreConfig.xml").write_bytes(core_xml)
        (RUNTIME / "tak" / "UserAuthenticationFile.xml").write_bytes(auth_xml)
        env = os.environ.copy()
        env["TAK_NEW_INTERMEDIATE_PASS"] = (stage / "intermediate.password").read_text().strip()
        env["TAK_STORE_PASS"] = (RUNTIME / "secrets" / "tak_store_password").read_text().strip()
        run("openssl", "pkcs12", "-export", "-name", "tak-issuing-ca", "-inkey",
            str(PRIVATE / "intermediate.key.pem"), "-passin", "env:TAK_NEW_INTERMEDIATE_PASS",
            "-in", str(PUBLIC / "intermediate.crt.pem"), "-certfile", str(PUBLIC / "root-ca.crt.pem"),
            "-out", str(PRIVATE / "intermediate-signing.p12"), "-passout", "env:TAK_STORE_PASS", env=env)
        package_name = f"atak-alpha-ca-{new_ca_id[:12]}.dpk"
        put(artifacts / "packages" / alpha["package"], PACKAGES / package_name)
        client_dir = PRIVATE / "clients" / uuid.uuid4().hex[:16]
        client_dir.mkdir(parents=True, exist_ok=False)
        put(artifacts / "private" / "alpha.key.pem", client_dir / "key.pem")
        put(artifacts / "public" / "alpha.crt.pem", client_dir / "client.pem")
        put(artifacts / "private" / "leaf.password", client_dir / "key.password")
        put(RUNTIME / "secrets" / "tak_store_password", client_dir / "store.password")
        registry = host.load_registry()
        registry[alpha["serial"]] = {"name": "Alpha CA rotation", "cn": alpha["cn"],
                                     "created_at": datetime.now(timezone.utc).isoformat(),
                                     "package": package_name, "key_dir": client_dir.name,
                                     "registered": True, "username": alpha["cn"],
                                     "in_groups": ["team-alpha"], "out_groups": ["team-alpha"],
                                     "issuer_ca_id": new_ca_id}
        host.save_registry(registry)
        if fingerprint(PUBLIC / "intermediate.crt.pem") != new_ca_id:
            raise RuntimeError("Active CA readback differs from the candidate")
        run("docker", "compose", "up", "-d", "--no-build", timeout=300)
    except BaseException:
        print(f"Cutover interrupted. Restore files from {backup.relative_to(PROJECT)} before retrying.")
        raise
    print(f"Cutover started with CA {new_ca_id}; backup: {backup.relative_to(PROJECT)}")
    print(f"Alpha DPK: {package_name}. Root revocation CRL has NOT been published.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("--apply", action="store_true", help="Stop and recreate Compose with replacement certificates")
    args = parser.parse_args()
    stage, _, manifest = stage_paths(args.stage)
    if not args.apply:
        prepare_authentication(stage / "artifacts", manifest["devices"]["alpha"])
        prepared_core_config("old-intermediate-ca.crl.pem")
        prepare_ca_rotation.source_files()
        print(f"Ready candidate: {stage.relative_to(PROJECT)}")
        print(f"New CA ID: {manifest['new_ca_id']}")
        print("Use --apply to create a backup and switch the local Compose services.")
        return 0
    cutover(stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
