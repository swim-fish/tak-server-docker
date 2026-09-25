"""Rotate the local issuing CA and optionally reissue selected client identities."""

from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from certificate_validity import requested_expiry

import cutover_ca_rotation as legacy
import drop_revoked_ca_trust_anchor
import prepare_ca_rotation
import stage_ca_rotation
import stage_ca_rotation_artifacts
import tak_certificate_host as host


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
PRIVATE = RUNTIME / "pki" / "private"
PUBLIC = RUNTIME / "pki" / "public"
TAK_CERTS = RUNTIME / "tak" / "certs"
PACKAGES = RUNTIME / "packages" / "atak"


def ca_id(path: Path) -> str:
    return x509.load_pem_x509_certificate(path.read_bytes()).fingerprint(hashes.SHA256()).hex().upper()


def prepare_selection(items: object) -> list[dict]:
    """Pin each requested renewal to the current certificate and its original identity."""
    if not isinstance(items, list) or len(items) > 100:
        raise ValueError("Select at most 100 certificates to reissue")
    seen = set()
    result = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid renewal selection")
        record = host.checked_record(item.get("serial"), item.get("fingerprint"), active=True)
        if record["serial"] in seen or record.get("registered") is not True:
            raise ValueError("Each selected certificate must be active and registered once")
        expiry = item.get("expires_at")
        if not isinstance(expiry, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", expiry):
            raise ValueError("Choose a valid renewal expiry for every selected certificate")
        old_cert = x509.load_pem_x509_certificate(host.certificate_path(record["serial"]).read_bytes())
        if ca_id(PUBLIC / "intermediate.crt.pem") != record["issuer_ca_id"]:
            raise ValueError("A selected certificate belongs to another issuing CA")
        if old_cert.not_valid_after_utc <= datetime.now(timezone.utc):
            raise ValueError("Expired certificates cannot be renewed in CA replacement")
        requested_expiry(expiry)
        seen.add(record["serial"])
        result.append({"old_serial": record["serial"], "cn": record["cn"],
                       "name": record["name"], "in_groups": record["in_groups"],
                       "out_groups": record["out_groups"], "expires_at": expiry})
    if len({item["cn"] for item in result}) != len(result):
        raise ValueError("Renewal CN values must be unique")
    return result


def active_ca_summary() -> dict:
    certificate = x509.load_pem_x509_certificate((PUBLIC / "intermediate.crt.pem").read_bytes())
    return {"id": certificate.fingerprint(hashes.SHA256()).hex().upper(),
            "serial": format(certificate.serial_number, "X"),
            "expires_at": certificate.not_valid_after_utc.isoformat()}


def prepared_authentication(artifacts: Path, records: list[dict]) -> bytes:
    tree = host.authentication_tree()
    root = tree.getroot()
    administrator = host.authentication_user(tree, "admin")
    if administrator is None or administrator.get("role") != "ROLE_ADMIN":
        raise RuntimeError("Administrator authentication entry is unexpected")
    admin_id = ca_id(artifacts / "public" / "admin.crt.pem")
    administrator.set("fingerprint", ":".join(admin_id[index:index + 2] for index in range(0, 64, 2)))
    for record in records:
        user = host.authentication_user(tree, record["cn"])
        if user is None:
            continue
        if user.get("role", "ROLE_ANONYMOUS") != "ROLE_ANONYMOUS" or "password" in user.attrib:
            raise RuntimeError("A client CN belongs to a privileged or password user")
        if user.get("fingerprint", "").replace(":", "").upper() != record["fingerprint"].upper():
            raise RuntimeError("A client CN fingerprint changed before CA replacement")
        root.remove(user)
    ElementTree.register_namespace("", host.AUTH_NAMESPACE)
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def prepared_core(old_id: str) -> tuple[bytes, str]:
    name = f"old-intermediate-ca-{old_id[:12].lower()}.crl.pem"
    core = (RUNTIME / "tak" / "CoreConfig.xml").read_text(encoding="utf-8")
    marker = '<crl _name="TAK Local Issuing CA" crlFile="/opt/tak/certs/files/intermediate-ca.crl.pem" />'
    if core.count(marker) != 1 or name in core or 'crlFile="/opt/tak/certs/files/root-ca.crl.pem"' not in core:
        raise RuntimeError("TAK CRL configuration differs from the expected multi-CA state")
    old_entry = (f'<crl _name="TAK Previous Issuing CA {old_id[:12]}" '
                 f'crlFile="/opt/tak/certs/files/{name}" />')
    payload = core.replace(marker, marker + "\n      " + old_entry).encode("utf-8")
    ElementTree.fromstring(payload)
    return payload, name


def service_cutover(stage: Path, old_records: list[dict]) -> tuple[Path, str]:
    """Activate the new service chain; keep the old CA unrevoked until renewals finish."""
    artifacts = stage / "artifacts"
    manifest = json.loads((artifacts / "manifest.json").read_text(encoding="utf-8"))
    old_id = (stage / "old-ca-id.txt").read_text(encoding="ascii").strip()
    new_id = (stage / "ca-id.txt").read_text(encoding="ascii").strip()
    if manifest["new_ca_id"] != new_id or manifest["devices"] or ca_id(PUBLIC / "intermediate.crt.pem") != old_id:
        raise RuntimeError("CA candidate or active CA changed before cutover")
    expected_sources = [stage / "intermediate.key.pem", stage / "intermediate.csr.pem",
                        stage / "intermediate.ext", stage / "intermediate.password",
                        stage / "intermediate.crt.pem",
                        stage / "intermediate-ca.crl.pem", stage / "root-ca.crl.pem",
                        artifacts / "ca-chain.pem", artifacts / "packages" / "caCert.p12",
                        artifacts / "tak-certs" / "takserver.jks",
                        artifacts / "tak-certs" / "truststore-root.jks",
                        artifacts / "tak-certs" / "fed-truststore.jks",
                        artifacts / "tak-certs" / "admin.p12",
                        artifacts / "tak-certs" / "admin.pem",
                        artifacts / "mumble-fullchain.pem", artifacts / "mediamtx-fullchain.pem",
                        artifacts / "private" / "leaf.password", artifacts / "private" / "takserver.p12"]
    for name in ("takserver", "admin", "mumble", "mediamtx"):
        expected_sources.append(artifacts / "public" / f"{name}.crt.pem")
        expected_sources.append(artifacts / "private" / f"{name}.key.pem")
        if name != "mediamtx":
            expected_sources.append(artifacts / "private" / f"{name}.csr.pem")
    if any(not path.is_file() or path.is_symlink() for path in expected_sources):
        raise RuntimeError("Staged CA or service certificate artifacts are incomplete")
    root = x509.load_pem_x509_certificate((PUBLIC / "root-ca.crt.pem").read_bytes())
    old = x509.load_pem_x509_certificate((PUBLIC / "intermediate.crt.pem").read_bytes())
    new = x509.load_pem_x509_certificate((stage / "intermediate.crt.pem").read_bytes())
    root_crl = x509.load_pem_x509_crl((stage / "root-ca.crl.pem").read_bytes())
    if (root_crl.issuer != root.subject or not root_crl.is_signature_valid(root.public_key())
            or root_crl.next_update_utc <= datetime.now(timezone.utc)
            or root_crl.get_revoked_certificate_by_serial_number(old.serial_number) is None
            or root_crl.get_revoked_certificate_by_serial_number(new.serial_number) is not None):
        raise RuntimeError("Staged Root CRL does not revoke exactly the former issuing CA")
    archive = RUNTIME / "pki" / "archive" / old_id
    archive_record = RUNTIME / "tak-cert-control" / "archive" / f"{old_id}.json"
    if archive.exists() or archive_record.exists():
        raise RuntimeError("Active issuing CA has already been archived")
    auth = prepared_authentication(artifacts, old_records)
    core, old_crl_name = prepared_core(old_id)
    backup = prepare_ca_rotation.create_snapshot()
    archive.mkdir(parents=True, exist_ok=False)
    archive_record.parent.mkdir(parents=True, exist_ok=True)
    archive_record.write_text(json.dumps({"ca_id": old_id,
                                          "issuer_serial": active_ca_summary()["serial"],
                                          "archived_at": datetime.now(timezone.utc).isoformat(),
                                          "certificates": old_records}, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    legacy.put(PUBLIC / "intermediate.crt.pem", archive / "intermediate.crt.pem")
    legacy.put(PUBLIC / "intermediate-ca.crl.pem", archive / "intermediate-ca.crl.pem")
    legacy.put(RUNTIME / "tak-cert-control" / "registry.json", archive / "registry.json")
    legacy.run("docker", "compose", "stop", "tak-server", "mumble", "mediamtx", timeout=240)
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
            (archive / "intermediate.crt.pem", TAK_CERTS / f"old-intermediate-ca-{old_id[:12].lower()}.pem"),
            (archive / "intermediate-ca.crl.pem", TAK_CERTS / old_crl_name),
            (artifacts / "mumble-fullchain.pem", RUNTIME / "pki" / "mumble-fullchain.pem"),
            (artifacts / "private" / "mumble.key.pem", RUNTIME / "pki" / "mumble-server.key.pem"),
            (artifacts / "mediamtx-fullchain.pem", RUNTIME / "pki" / "mediamtx-fullchain.pem"),
            (artifacts / "private" / "mediamtx.key.pem", RUNTIME / "pki" / "mediamtx-server.key.pem"),
            (artifacts / "packages" / "caCert.p12", PACKAGES / "caCert.p12"),
        ):
            legacy.put(source, target)
        for name in ("takserver", "admin", "mumble", "mediamtx"):
            legacy.put(artifacts / "public" / f"{name}.crt.pem", PUBLIC / f"{name}.crt.pem")
            if name != "mediamtx":
                legacy.put(artifacts / "private" / f"{name}.key.pem", PRIVATE / f"{name}.key.pem")
                legacy.put(artifacts / "private" / f"{name}.csr.pem", PRIVATE / f"{name}.csr.pem")
        (RUNTIME / "secrets" / "intermediate_ca_password").write_bytes((stage / "intermediate.password").read_bytes())
        (RUNTIME / "secrets" / "leaf_key_password").write_bytes((artifacts / "private" / "leaf.password").read_bytes())
        env = os.environ.copy()
        env["TAK_NEW_INTERMEDIATE_PASS"] = (stage / "intermediate.password").read_text().strip()
        env["TAK_STORE_PASS"] = (RUNTIME / "secrets" / "tak_store_password").read_text().strip()
        legacy.run("openssl", "pkcs12", "-export", "-name", "tak-issuing-ca", "-inkey",
                   str(PRIVATE / "intermediate.key.pem"), "-passin", "env:TAK_NEW_INTERMEDIATE_PASS",
                   "-in", str(PUBLIC / "intermediate.crt.pem"), "-certfile", str(PUBLIC / "root-ca.crt.pem"),
                   "-out", str(PRIVATE / "intermediate-signing.p12"), "-passout", "env:TAK_STORE_PASS", env=env)
        previous_crls = [path.read_bytes() for path in sorted(TAK_CERTS.glob("old-intermediate-ca*.crl.pem"))]
        chain = (PUBLIC / "intermediate-ca.crl.pem").read_bytes() + b"".join(previous_crls) + (PUBLIC / "root-ca.crl.pem").read_bytes()
        (PUBLIC / "ca-chain.crl.pem").write_bytes(chain)
        (TAK_CERTS / "ca-chain.crl.pem").write_bytes(chain)
        (RUNTIME / "tak" / "CoreConfig.xml").write_bytes(core)
        with host.authentication_file().open("r+b") as output:
            output.seek(0)
            output.write(auth)
            output.truncate()
            output.flush()
            os.fsync(output.fileno())
        host.save_registry({})
        if ca_id(PUBLIC / "intermediate.crt.pem") != new_id:
            raise RuntimeError("Active CA does not match the staged candidate")
        legacy.run("docker", "compose", "up", "-d", "--no-build", "--no-deps", "--force-recreate",
                   "tak-server", "mumble", "mediamtx", timeout=300)
        host.check_server_running()
        if not host.wait_for_cot_listener(timeout=120):
            raise RuntimeError("TAK CoT listener did not recover after service certificate cutover")
    except BaseException:
        raise RuntimeError(f"CA cutover stopped; restore the snapshot under {backup.relative_to(PROJECT)}")
    return archive, old_crl_name


def publish_old_ca_revocation(stage: Path, archive: Path) -> None:
    """Publish the staged Root CRL after every selected renewal has succeeded."""
    old = x509.load_pem_x509_certificate((archive / "intermediate.crt.pem").read_bytes())
    new = x509.load_pem_x509_certificate((PUBLIC / "intermediate.crt.pem").read_bytes())
    staged_crl = x509.load_pem_x509_crl((stage / "root-ca.crl.pem").read_bytes())
    root = x509.load_pem_x509_certificate((PUBLIC / "root-ca.crt.pem").read_bytes())
    if (staged_crl.issuer != root.subject or not staged_crl.is_signature_valid(root.public_key())
            or staged_crl.next_update_utc <= datetime.now(timezone.utc)
            or staged_crl.get_revoked_certificate_by_serial_number(old.serial_number) is None
            or staged_crl.get_revoked_certificate_by_serial_number(new.serial_number) is not None):
        raise RuntimeError("Staged Root CRL is not valid for this CA replacement")
    if (archive / "root-ca-db-before-revocation").exists():
        raise RuntimeError("Root database has already been replaced for this CA")
    prepare_ca_rotation.create_snapshot()
    legacy.run("docker", "compose", "stop", "tak-server", timeout=120)
    shutil.move(str(PRIVATE / "root-ca-db"), str(archive / "root-ca-db-before-revocation"))
    shutil.copytree(stage / "root-ca-db", PRIVATE / "root-ca-db")
    crl_bytes = (stage / "root-ca.crl.pem").read_bytes()
    (PUBLIC / "root-ca.crl.pem").write_bytes(crl_bytes)
    (TAK_CERTS / "root-ca.crl.pem").write_bytes(crl_bytes)
    old_crls = [path.read_bytes() for path in sorted(TAK_CERTS.glob("old-intermediate-ca*.crl.pem"))]
    chain = (PUBLIC / "intermediate-ca.crl.pem").read_bytes() + b"".join(old_crls) + crl_bytes
    (PUBLIC / "ca-chain.crl.pem").write_bytes(chain)
    (TAK_CERTS / "ca-chain.crl.pem").write_bytes(chain)
    legacy.run("docker", "compose", "up", "-d", "--no-build", "tak-server", timeout=240)
    drop_revoked_ca_trust_anchor.apply(ca_id(archive / "intermediate.crt.pem"))
    if not host.wait_for_cot_listener():
        raise RuntimeError("TAK CoT listener did not recover after old CA revocation")


def rotate(selected: list[dict], progress) -> dict:
    """Run one checked local CA replacement. Caller must enforce a single active job."""
    old_records = host.inventory()
    old_id = active_ca_summary()["id"]
    chosen = prepare_selection(selected)
    progress("staging", "Signing a replacement issuing CA and service certificates")
    stage = stage_ca_rotation.stage(old_id)
    stage_ca_rotation_artifacts.prepare(stage, include_test_devices=False)
    progress("cutover", "Switching service certificates to the replacement CA")
    archive, _ = service_cutover(stage, old_records)
    renewed = []
    if chosen:
        progress("renewing", "Reissuing selected client certificates")
        for start in range(0, len(chosen), 10):
            group = chosen[start:start + 10]
            job = host.issue_batch(uuid.uuid4().hex, [{key: item[key] for key in
                                    ("name", "cn", "in_groups", "out_groups", "expires_at")}
                                   for item in group])
            if job["state"] != "complete":
                raise RuntimeError("Some selected certificates were not reissued; previous CA remains unrevoked")
            renewed.extend({"old_serial": old["old_serial"], "new_serial": entry["serial"],
                            "cn": old["cn"]} for old, entry in zip(group, job["items"]))
    progress("revoking", "Publishing Root CRL and removing the former CA trust anchor")
    publish_old_ca_revocation(stage, archive)
    return {"old_ca_id": old_id, "new_ca_id": active_ca_summary()["id"], "renewed": renewed,
            "old_certificate_count": len(old_records), "snapshot_archive": str(archive.relative_to(PROJECT))}
