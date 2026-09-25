#!/usr/bin/env python3
"""Host-side TAK client certificate operations for the loopback control panel."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock, Thread
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID, NameOID

import tak_api_client
import tak_vx_package_host
from certificate_validity import requested_expiry
from local_network import bind_ip


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
CONTROL = RUNTIME / "tak-cert-control"
PRIVATE = RUNTIME / "pki" / "private"
PUBLIC = RUNTIME / "pki" / "public"
CA_DB = PRIVATE / "ca-db"
TAK_CERTS = RUNTIME / "tak" / "certs"
PACKAGES = RUNTIME / "packages" / "atak"
REGISTRY = CONTROL / "registry.json"
AUDIT = CONTROL / "audit.jsonl"
LAST_RESULT = CONTROL / "last-result.json"
BATCH_JOBS = CONTROL / "batch-jobs"
ROTATION_JOB = CONTROL / "ca-rotation-job.json"
ROTATION_LOCK = Lock()
ROTATION_THREAD: Thread | None = None
TAIPEI = timezone(timedelta(hours=8), "Asia/Taipei")
GROUP = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
COMMON_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,62}\Z")
SERIAL = re.compile(r"[0-9A-F]{1,40}\Z")
AUTH_NAMESPACE = "http://bbn.com/marti/xml/bindings"
AUTH_FILE_NAME = "UserAuthenticationFile.xml"


def command(args: list[str], *, env: dict[str, str] | None = None,
            timeout: int = 90, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(args, cwd=PROJECT, env=env, input=input_bytes,
                            capture_output=True, timeout=timeout,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        detail = (result.stderr or result.stdout).decode("utf-8", "replace").strip()[-500:]
        raise RuntimeError(f"Command failed ({Path(args[0]).name}): {detail}")
    return result


def require_tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} is not available on PATH")
    return found


def load_registry() -> dict:
    if not REGISTRY.is_file():
        return {}
    content = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise RuntimeError("Invalid certificate registry")
    return content


def save_registry(records: dict) -> None:
    CONTROL.mkdir(parents=True, exist_ok=True)
    pending = REGISTRY.with_suffix(".pending")
    pending.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, REGISTRY)


def audit(action: str, serials: list[str], outcome: str) -> None:
    CONTROL.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as output:
        output.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(),
                                 "action": action, "serials": serials, "outcome": outcome}) + "\n")


def certificate_path(serial: str) -> Path:
    if not SERIAL.fullmatch(serial):
        raise ValueError("Invalid certificate serial")
    path = CA_DB / "newcerts" / f"{serial}.pem"
    if not path.is_file():
        path = CA_DB / "newcerts" / f"{serial.lower()}.pem"
    if not path.is_file() or path.is_symlink():
        raise ValueError("Certificate is missing from the issuing CA database")
    return path


def excluded_fingerprints() -> set[str]:
    values = set()
    for name in ("admin", "takserver"):
        path = PUBLIC / f"{name}.crt.pem"
        if path.is_file():
            cert = x509.load_pem_x509_certificate(path.read_bytes())
            values.add(cert.fingerprint(hashes.SHA256()).hex())
    return values


def inventory(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    active_ca = x509.load_pem_x509_certificate((PUBLIC / "intermediate.crt.pem").read_bytes())
    active_ca_id = active_ca.fingerprint(hashes.SHA256()).hex().upper()
    index = CA_DB / "index.txt"
    if not index.is_file():
        raise RuntimeError("Issuing CA database is missing")
    registry = load_registry()
    excluded = excluded_fingerprints()
    records = []
    for line in index.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) < 6 or fields[0] not in {"V", "R", "E"}:
            raise RuntimeError("Invalid issuing CA database row")
        serial = fields[3].upper()
        path = certificate_path(serial)
        cert = x509.load_pem_x509_certificate(path.read_bytes())
        if cert.serial_number != int(serial, 16):
            raise RuntimeError("Issuing CA serial does not match certificate")
        try:
            usage = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value
        except x509.ExtensionNotFound:
            continue
        if ExtendedKeyUsageOID.CLIENT_AUTH not in usage:
            continue
        fingerprint = cert.fingerprint(hashes.SHA256()).hex()
        if fingerprint in excluded:
            continue
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        cn_value = cn[0].value if cn else "(no CN)"
        expiry = cert.not_valid_after_utc
        remaining = expiry - now
        if remaining.total_seconds() <= 0:
            days_text = "已過期"
        elif remaining < timedelta(days=1):
            days_text = "少於 1 天"
        else:
            days_text = f"{remaining.days} 天"
        metadata = registry.get(serial, {})
        package = metadata.get("package")
        if package and (Path(package).name != package or not (PACKAGES / package).is_file()):
            package = None
        records.append({
            "serial": serial, "fingerprint": fingerprint,
            "issuer_ca_id": active_ca_id, "archived": False, "ca_revoked": False,
            "issuer": cert.issuer.rfc4514_string(), "cn": cn_value,
            "name": metadata.get("name", cn_value),
            "expires_at": expiry.astimezone(TAIPEI).strftime("%Y-%m-%d %H:%M:%S"),
            "expires_iso": expiry.isoformat(), "days_left": days_text,
            "expiring_soon": timedelta(0) < remaining <= timedelta(days=30),
            "expired": remaining.total_seconds() <= 0,
            "revoked": fields[0] == "R", "revoked_at": fields[2] if fields[0] == "R" else None,
            "package": package, "registered": metadata.get("registered"),
            "username": metadata.get("username"),
            "in_groups": [group for group in metadata.get("in_groups", [])
                          if isinstance(group, str) and GROUP.fullmatch(group)]
            if isinstance(metadata.get("in_groups", []), list) else [],
            "out_groups": [group for group in metadata.get("out_groups", [])
                           if isinstance(group, str) and GROUP.fullmatch(group)]
            if isinstance(metadata.get("out_groups", []), list) else [],
        })
    return sorted(records, key=lambda item: (item["expires_iso"], item["serial"]))


def archived_inventory(now: datetime | None = None) -> list[dict]:
    archive_dir = CONTROL / "archive"
    if not archive_dir.is_dir():
        return []
    now = now or datetime.now(timezone.utc)
    root = x509.load_pem_x509_certificate((PUBLIC / "root-ca.crt.pem").read_bytes())
    root_crl = x509.load_pem_x509_crl((PUBLIC / "root-ca.crl.pem").read_bytes())
    if (root_crl.issuer != root.subject or not root_crl.is_signature_valid(root.public_key())
            or root_crl.next_update_utc <= now):
        raise RuntimeError("Published Root CRL cannot be verified")
    records = []
    for path in sorted(archive_dir.glob("*.json")):
        ca_id = path.stem.upper()
        if not re.fullmatch(r"[0-9A-F]{64}", ca_id):
            raise RuntimeError("Invalid archived CA ID")
        issuer_path = RUNTIME / "pki" / "archive" / ca_id / "intermediate.crt.pem"
        issuer = x509.load_pem_x509_certificate(issuer_path.read_bytes())
        if issuer.fingerprint(hashes.SHA256()).hex().upper() != ca_id:
            raise RuntimeError("Archived CA certificate does not match its ID")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("ca_id") != ca_id or not isinstance(payload.get("certificates"), list):
            raise RuntimeError("Archived certificate inventory is invalid")
        ca_revoked = root_crl.get_revoked_certificate_by_serial_number(issuer.serial_number) is not None
        for original in payload["certificates"]:
            record = dict(original)
            expiry = datetime.fromisoformat(record["expires_iso"])
            remaining = expiry - now
            record["expired"] = remaining.total_seconds() <= 0
            record["expiring_soon"] = timedelta(0) < remaining <= timedelta(days=30)
            record["days_left"] = ("已過期" if record["expired"] else "少於 1 天"
                                   if remaining < timedelta(days=1) else f"{remaining.days} 天")
            record.update({"issuer_ca_id": ca_id, "archived": True,
                           "ca_revoked": ca_revoked, "package": None})
            records.append(record)
    return sorted(records, key=lambda item: (item["expires_iso"], item["serial"]))


def checked_record(serial: object, fingerprint: object, *, active: bool = False) -> dict:
    if not isinstance(serial, str) or not isinstance(fingerprint, str):
        raise ValueError("Invalid certificate selection")
    record = next((item for item in inventory() if item["serial"] == serial), None)
    if record is None or not secrets.compare_digest(record["fingerprint"], fingerprint):
        raise RuntimeError("Certificate selection changed; refresh the page")
    if active and (record["revoked"] or record["expired"]):
        raise ValueError("Revoked or expired certificates cannot be changed or shared")
    return record


def checked_group_list(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) > 50:
        raise ValueError("Invalid group list")
    groups = sorted(set(value))
    if len(groups) != len(value) or any(not isinstance(item, str) or not GROUP.fullmatch(item)
                                        for item in groups):
        raise ValueError("Invalid or duplicate group")
    return groups


def group_flags(in_groups: list[str], out_groups: list[str]) -> list[str]:
    if not in_groups and not out_groups:
        raise ValueError("Select at least one In or Out group")
    both = set(in_groups) & set(out_groups)
    flags = []
    for group in sorted(both):
        flags.extend(("-g", group))
    for group in sorted(set(in_groups) - both):
        flags.extend(("-ig", group))
    for group in sorted(set(out_groups) - both):
        flags.extend(("-og", group))
    return flags


def authentication_file() -> Path:
    return RUNTIME / "tak" / AUTH_FILE_NAME


def authentication_tree() -> ElementTree.ElementTree:
    tree = ElementTree.parse(authentication_file())
    if tree.getroot().tag != f"{{{AUTH_NAMESPACE}}}UserAuthenticationFile":
        raise RuntimeError("Unexpected TAK user authentication file format")
    return tree


def authentication_user(tree: ElementTree.ElementTree, username: str) -> ElementTree.Element | None:
    matches = [item for item in tree.getroot()
               if item.tag == f"{{{AUTH_NAMESPACE}}}User" and item.get("identifier") == username]
    if len(matches) > 1:
        raise RuntimeError("Duplicate TAK authentication username")
    return matches[0] if matches else None


def authentication_identity(record: dict) -> dict:
    user = authentication_user(authentication_tree(), record["cn"])
    if user is None or user.get("fingerprint", "").replace(":", "").lower() != record["fingerprint"]:
        raise RuntimeError("TAK authentication fingerprint does not match this certificate")
    return {"username": record["cn"], "role": user.get("role", "ROLE_ANONYMOUS"),
            "fingerprint": record["fingerprint"]}


def groups_from_api(data: dict) -> tuple[list[str], list[str]]:
    both, in_only, out_only = (data.get(key) for key in ("groupList", "groupListIN", "groupListOUT"))
    if any(not isinstance(items, list) or any(not isinstance(item, str) or not GROUP.fullmatch(item)
                                              for item in items)
           for items in (both, in_only, out_only)):
        raise RuntimeError("TAK API returned invalid group data")
    return sorted(set(both + in_only)), sorted(set(both + out_only))


def add_authentication_user(tree: ElementTree.ElementTree, record: dict,
                            in_groups: list[str], out_groups: list[str]) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", record["fingerprint"]):
        raise ValueError("Invalid certificate fingerprint")
    user = authentication_user(tree, record["cn"])
    if user is not None:
        if user.get("fingerprint", "").replace(":", "").lower() != record["fingerprint"]:
            raise RuntimeError("TAK authentication username belongs to another certificate")
        if user.get("role", "ROLE_ANONYMOUS") != "ROLE_ANONYMOUS":
            raise RuntimeError("TAK authentication user has a privileged role")
        if "password" in user.attrib:
            raise RuntimeError("TAK authentication user has password credentials")
        user.clear()
        user.attrib.update({"identifier": record["cn"]})
    else:
        user = ElementTree.SubElement(tree.getroot(), f"{{{AUTH_NAMESPACE}}}User", {
            "identifier": record["cn"]})
    user.set("fingerprint", ":".join(
        record["fingerprint"][index:index + 2].upper() for index in range(0, 64, 2)))
    both = sorted(set(in_groups) & set(out_groups))
    for tag, values in (("groupList", both), ("groupListIN", sorted(set(in_groups) - set(both))),
                        ("groupListOUT", sorted(set(out_groups) - set(both)))):
        for value in values:
            ElementTree.SubElement(user, f"{{{AUTH_NAMESPACE}}}{tag}").text = value


def write_authentication_tree(tree: ElementTree.ElementTree) -> None:
    ElementTree.register_namespace("", AUTH_NAMESPACE)
    payload = ElementTree.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
    # Compose bind-mounts this file. Preserve its inode so the container sees the update.
    with authentication_file().open("r+b") as output:
        output.seek(0)
        output.write(payload)
        output.truncate()
        output.flush()
        os.fsync(output.fileno())


def restart_for_authentication() -> None:
    command([require_tool("docker"), "compose", "restart", "tak-server"], timeout=180)
    if not wait_for_cot_listener():
        raise RuntimeError("TAK did not reopen its CoT listener after authentication update")


def wait_for_groups(record: dict, in_groups: list[str], out_groups: list[str],
                    timeout: int = 150) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            groups = groups_from_api(tak_api_client.get_groups(record["cn"]))
            if groups == (sorted(set(in_groups)), sorted(set(out_groups))):
                return
        except (OSError, RuntimeError):
            pass
        time.sleep(2)
    raise RuntimeError("TAK API did not confirm the new certificate groups after restart")


def register_authentication(record: dict, in_groups: list[str], out_groups: list[str]) -> None:
    tree = authentication_tree()
    add_authentication_user(tree, record, in_groups, out_groups)
    write_authentication_tree(tree)
    restart_for_authentication()
    wait_for_groups(record, in_groups, out_groups)


def status(record: dict) -> dict:
    identity = authentication_identity(record)
    in_groups, out_groups = groups_from_api(tak_api_client.get_groups(identity["username"]))
    return {**identity, "in_groups": in_groups, "out_groups": out_groups, "recognized": True}


def set_groups(serial: str, fingerprint: str, in_values: object, out_values: object) -> dict:
    record = checked_record(serial, fingerprint, active=True)
    in_groups = checked_group_list(in_values)
    out_groups = checked_group_list(out_values)
    previous_metadata = load_registry().get(serial, {})
    if previous_metadata.get("registered") is False and not in_groups and not out_groups:
        raise ValueError("Register the certificate with at least one In or Out group")
    if previous_metadata.get("registered") is not False:
        previous = status(record)
        if previous["role"] == "ROLE_ADMIN":
            raise ValueError("Administrator certificates cannot be changed in this console")
    backup = ca_backup()
    if previous_metadata.get("registered") is False:
        register_authentication(record, in_groups, out_groups)
    else:
        tak_api_client.update_groups(record["cn"], in_groups, out_groups)
    details = status(record)
    if details["in_groups"] != in_groups or details["out_groups"] != out_groups:
        audit("groups", [serial], "readback-mismatch")
        raise RuntimeError("TAK group readback differs from the requested groups")
    registry = load_registry()
    metadata = registry.setdefault(serial, {})
    metadata["registered"] = True
    metadata["username"] = details["username"]
    metadata["in_groups"] = in_groups
    metadata["out_groups"] = out_groups
    save_registry(registry)
    audit("groups", [serial], f"verified;backup={backup}")
    return details


def set_group_batch(changes: object) -> dict:
    if not isinstance(changes, list) or not 1 <= len(changes) <= 100:
        raise ValueError("Select between 1 and 100 certificate group changes")
    prepared = []
    seen = set()
    for change in changes:
        if not isinstance(change, dict):
            raise ValueError("Invalid certificate group change")
        record = checked_record(change.get("serial"), change.get("fingerprint"), active=True)
        if record["serial"] in seen or record.get("registered") is not True:
            raise ValueError("Select distinct registered certificates")
        seen.add(record["serial"])
        expected_in = checked_group_list(change.get("expected_in"))
        expected_out = checked_group_list(change.get("expected_out"))
        in_groups = checked_group_list(change.get("in_groups"))
        out_groups = checked_group_list(change.get("out_groups"))
        current = status(record)
        if current["role"] == "ROLE_ADMIN":
            raise ValueError("Administrator certificates cannot be changed in this console")
        if current["in_groups"] != expected_in or current["out_groups"] != expected_out:
            raise RuntimeError("Certificate groups changed in TAK; refresh the group page")
        prepared.append((record, in_groups, out_groups))
    results = []
    for record, in_groups, out_groups in prepared:
        try:
            set_groups(record["serial"], record["fingerprint"], in_groups, out_groups)
            results.append({"serial": record["serial"], "cn": record["cn"], "state": "updated"})
        except (RuntimeError, OSError, ValueError) as exc:
            results.append({"serial": record["serial"], "cn": record["cn"],
                            "state": "failed", "error": str(exc)})
    audit("group_batch", [record["serial"] for record, _, _ in prepared],
          "complete" if all(item["state"] == "updated" for item in results) else "partial")
    return {"results": results, "state": "complete" if all(item["state"] == "updated" for item in results)
            else "partial"}


def ca_backup() -> str:
    backup = CONTROL / "backups" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                                    + "-" + uuid.uuid4().hex[:8])
    backup.mkdir(parents=True, exist_ok=False)
    for name in ("index.txt", "index.txt.attr", "serial", "crlnumber"):
        source = CA_DB / name
        if source.exists():
            shutil.copy2(source, backup / name)
    for name in ("intermediate-ca.crl.pem", "ca-chain.crl.pem"):
        source = PUBLIC / name
        if source.exists():
            shutil.copy2(source, backup / name)
    auth_file = RUNTIME / "tak" / "UserAuthenticationFile.xml"
    if auth_file.is_file():
        shutil.copy2(auth_file, backup / auth_file.name)
    return backup.name


def check_server_running() -> None:
    result = command([require_tool("docker"), "compose", "ps", "--status", "running", "--services"],
                     timeout=20)
    if "tak-server" not in result.stdout.decode("utf-8", "replace").splitlines():
        raise RuntimeError("Start the tak-server Compose service before changing certificates")


def secret_env(**values: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(values)
    return env


def issue(request: dict, *, defer_registration: bool = False) -> dict:
    name = request.get("name", "")
    cn = request.get("cn", "")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or any(ord(c) < 32 for c in name):
        raise ValueError("Device display name must contain 1–80 printable characters")
    if not isinstance(cn, str) or not COMMON_NAME.fullmatch(cn):
        raise ValueError("Certificate CN must use 2–63 ASCII letters, digits, dots, dashes or underscores")
    in_groups = checked_group_list(request.get("in_groups"))
    out_groups = checked_group_list(request.get("out_groups"))
    group_flags(in_groups, out_groups)
    check_server_running()
    if authentication_user(authentication_tree(), cn) is not None:
        raise ValueError("Certificate CN is already registered in TAK")
    if any(item["cn"] == cn and not item["revoked"] for item in inventory()):
        raise ValueError("Certificate CN is already used by an active certificate")
    openssl = require_tool("openssl")
    keytool = require_tool("keytool")
    issuing_ca = x509.load_pem_x509_certificate((PUBLIC / "intermediate.crt.pem").read_bytes())
    expires_at = requested_expiry(request.get("expires_at"),
                                  issuer_not_after=issuing_ca.not_valid_after_utc)
    identity = uuid.uuid4().hex[:16]
    directory = PRIVATE / "clients" / identity
    directory.mkdir(parents=True, exist_ok=False)
    key_password = secrets.token_urlsafe(36)
    store_password = secrets.token_urlsafe(30)
    (directory / "key.password").write_text(key_password + "\n", encoding="ascii")
    (directory / "store.password").write_text(store_password + "\n", encoding="ascii")
    key = directory / "key.pem"
    csr = directory / "request.pem"
    ext = directory / "client.ext"
    cert_file = directory / "client.pem"
    ext.write_text("[client_ext]\nbasicConstraints=critical,CA:FALSE\n"
                   "keyUsage=critical,digitalSignature,keyEncipherment\n"
                   "extendedKeyUsage=clientAuth\nsubjectKeyIdentifier=hash\n"
                   "authorityKeyIdentifier=keyid,issuer\n", encoding="ascii")
    env = secret_env(TAK_CLIENT_KEY_PASS=key_password,
                     TAK_CLIENT_STORE_PASS=store_password,
                     TAK_INTERMEDIATE_PASS=(RUNTIME / "secrets" / "intermediate_ca_password")
                     .read_text(encoding="ascii").strip())
    backup = ca_backup()
    command([openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072",
             "-aes-256-cbc", "-pass", "env:TAK_CLIENT_KEY_PASS", "-out", str(key)], env=env)
    command([openssl, "req", "-new", "-sha256", "-key", str(key), "-passin",
             "env:TAK_CLIENT_KEY_PASS", "-subj", f"/C=TW/O=TAK Local/OU=Client/CN={cn}",
             "-out", str(csr)], env=env)
    command([openssl, "ca", "-batch", "-config", str(PRIVATE / "issuing-ca.cnf"),
             "-extensions", "client_ext", "-extfile", str(ext), "-enddate",
             expires_at.strftime("%Y%m%d%H%M%SZ"), "-notext",
             "-in", str(csr), "-out", str(cert_file), "-passin", "env:TAK_INTERMEDIATE_PASS"],
            env=env)
    cert = x509.load_pem_x509_certificate(cert_file.read_bytes())
    if cert.not_valid_after_utc != expires_at:
        raise RuntimeError("Signed certificate expiry differs from the requested time")
    serial = format(cert.serial_number, "X")
    certificate_path(serial)
    if serial in load_registry():
        raise RuntimeError("New certificate serial already exists in the registry")
    command([openssl, "verify", "-purpose", "sslclient", "-CAfile",
             str(PUBLIC / "root-ca.crt.pem"), "-untrusted", str(PUBLIC / "intermediate.crt.pem"),
             str(cert_file)], env=env)
    registry = load_registry()
    registry[serial] = {"name": name.strip(), "cn": cn,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "requested_expires_at": request.get("expires_at"),
                        "package": None, "key_dir": identity, "registered": False,
                        "in_groups": in_groups, "out_groups": out_groups, "backup": backup,
                        "batch_job": request.get("_batch_job_id") if defer_registration else None}
    save_registry(registry)
    client_store = directory / "clientCert.p12"
    ca_store = directory / "caCert.p12"
    command([openssl, "pkcs12", "-export", "-name", cn, "-inkey", str(key),
             "-passin", "env:TAK_CLIENT_KEY_PASS", "-in", str(cert_file), "-certfile",
             str(PUBLIC / "ca-chain.pem"), "-out", str(client_store),
             "-passout", "env:TAK_CLIENT_STORE_PASS"], env=env)
    for alias, source in (("tak-root", PUBLIC / "root-ca.crt.pem"),
                          ("tak-issuing", PUBLIC / "intermediate.crt.pem")):
        command([keytool, "-importcert", "-noprompt", "-alias", alias, "-file", str(source),
                 "-keystore", str(ca_store), "-storetype", "PKCS12", "-storepass:env",
                 "TAK_CLIENT_STORE_PASS"], env=env)
    prefs = f'''<?xml version="1.0" encoding="UTF-8"?>
<preferences>
  <preference version="1" name="cot_streams">
    <entry key="count" class="class java.lang.Integer">1</entry>
    <entry key="description0" class="class java.lang.String">Local TAK Server 5.8</entry>
    <entry key="connectString0" class="class java.lang.String">takbox.local:8089:ssl</entry>
    <entry key="enabled0" class="class java.lang.Boolean">true</entry>
    <entry key="useAuth0" class="class java.lang.Boolean">false</entry>
    <entry key="caLocation0" class="class java.lang.String">cert/caCert.p12</entry>
    <entry key="caPassword0" class="class java.lang.String">{store_password}</entry>
    <entry key="certificateLocation0" class="class java.lang.String">cert/clientCert.p12</entry>
    <entry key="clientPassword0" class="class java.lang.String">{store_password}</entry>
  </preference>
  <preference version="1" name="com.atakmap.app_preferences">
    <entry key="displayServerConnectionWidget" class="class java.lang.Boolean">true</entry>
  </preference>
</preferences>
'''
    manifest = f'''<?xml version="1.0" encoding="UTF-8"?>
<MissionPackageManifest version="2">
  <Configuration>
    <Parameter name="name" value="ATAK Local TAK 5.8 {escape(cn)}"/>
    <Parameter name="uid" value="{uuid.uuid4()}"/>
    <Parameter name="remarks" value="Device certificate for {escape(name.strip(), {'\"': '&quot;'})}"/>
    <Parameter name="onReceiveImport" value="true"/>
    <Parameter name="onReceiveDelete" value="false"/>
  </Configuration>
  <Contents>
    <Content zipEntry="cert/caCert.p12"><Parameter name="contentType" value="P12 Certificate"/></Content>
    <Content zipEntry="cert/clientCert.p12"><Parameter name="contentType" value="P12 Certificate"/></Content>
    <Content zipEntry="config/servers.pref"><Parameter name="contentType" value="ATAK Preferences"/></Content>
  </Contents>
</MissionPackageManifest>
'''
    PACKAGES.mkdir(parents=True, exist_ok=True)
    package_name = f"atak-{cn}-{serial}.dpk"
    package = PACKAGES / package_name
    if package.exists():
        raise RuntimeError("Target DPK filename already exists")
    pending = package.with_suffix(".pending")
    with zipfile.ZipFile(pending, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("MANIFEST/manifest.xml", manifest)
        archive.writestr("config/servers.pref", prefs)
        archive.write(ca_store, "cert/caCert.p12")
        archive.write(client_store, "cert/clientCert.p12")
    os.replace(pending, package)
    registry[serial]["package"] = package_name
    registry[serial]["sha256"] = hashlib.sha256(package.read_bytes()).hexdigest()
    save_registry(registry)
    if defer_registration:
        audit("issue", [serial], "signed-awaiting-batch-registration")
        return {"serial": serial, "package": package_name}
    try:
        register_authentication(checked_record(serial, cert.fingerprint(hashes.SHA256()).hex()),
                                in_groups, out_groups)
        details = status(checked_record(serial, cert.fingerprint(hashes.SHA256()).hex()))
        if details["in_groups"] != in_groups or details["out_groups"] != out_groups:
            raise RuntimeError("TAK group readback differs after issuance")
        registry[serial]["registered"] = True
        registry[serial]["username"] = details["username"]
        save_registry(registry)
    except Exception:
        audit("issue", [serial], "signed-but-registration-unverified")
        raise RuntimeError(f"Certificate {serial} was signed and DPK created, but TAK registration is unverified")
    audit("issue", [serial], "registered")
    return {"serial": serial, "package": package_name}


def batch_job_path(job_id: str) -> Path:
    if not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise ValueError("Invalid batch operation ID")
    return BATCH_JOBS / (job_id + ".json")


def read_batch_job(job_id: str) -> dict:
    path = batch_job_path(job_id)
    if not path.is_file():
        raise ValueError("Batch operation does not exist")
    return json.loads(path.read_text(encoding="utf-8"))


def save_batch_job(job_id: str, data: dict) -> None:
    path = batch_job_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(".pending")
    pending.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, path)


def validate_batch_items(items: object) -> list[dict]:
    if not isinstance(items, list) or not 1 <= len(items) <= 10:
        raise ValueError("Select between 1 and 10 devices")
    checked = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid device entry")
        name, cn = item.get("name"), item.get("cn")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or any(ord(c) < 32 for c in name):
            raise ValueError("Device display name must contain 1–80 printable characters")
        if not isinstance(cn, str) or not COMMON_NAME.fullmatch(cn) or cn in seen:
            raise ValueError("Each device requires a unique, valid certificate CN")
        in_groups = checked_group_list(item.get("in_groups"))
        out_groups = checked_group_list(item.get("out_groups"))
        group_flags(in_groups, out_groups)
        expires_at = item.get("expires_at")
        if expires_at is not None and (not isinstance(expires_at, str) or
                                       not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", expires_at)):
            raise ValueError("Invalid certificate expiry date or time")
        seen.add(cn)
        checked.append({"name": name.strip(), "cn": cn,
                        "in_groups": in_groups, "out_groups": out_groups,
                        "expires_at": expires_at})
    return checked


def signed_batch_record(job_id: str, item: dict) -> dict | None:
    matches = [record for record in inventory() if record["cn"] == item["cn"] and not record["revoked"]]
    if len(matches) > 1:
        raise RuntimeError("Multiple active certificates use a batch CN")
    if not matches:
        return None
    record = matches[0]
    metadata = load_registry().get(record["serial"], {})
    if (metadata.get("batch_job") != job_id or metadata.get("name") != item["name"] or
            metadata.get("in_groups") != item["in_groups"] or
            metadata.get("out_groups") != item["out_groups"] or
            metadata.get("requested_expires_at") != item["expires_at"] or
            not record.get("package")):
        raise RuntimeError(f"Certificate CN {item['cn']} already exists outside this batch or is incomplete")
    return record


def issue_batch(job_id: str, items: object) -> dict:
    checked = validate_batch_items(items)
    path = batch_job_path(job_id)
    if path.is_file():
        job = read_batch_job(job_id)
        if [entry["request"] for entry in job["items"]] != checked:
            raise RuntimeError("Batch parameters changed after the operation started")
    else:
        check_server_running()
        registered = {item.get("identifier") for item in authentication_tree().getroot()
                      if item.tag == f"{{{AUTH_NAMESPACE}}}User"}
        active = {record["cn"] for record in inventory() if not record["revoked"]}
        if any(item["cn"] in registered or item["cn"] in active for item in checked):
            raise ValueError("A batch CN is already registered or has an active certificate")
        issuing_ca = x509.load_pem_x509_certificate((PUBLIC / "intermediate.crt.pem").read_bytes())
        for item in checked:
            requested_expiry(item["expires_at"], issuer_not_after=issuing_ca.not_valid_after_utc)
        job = {"job_id": job_id, "state": "signing", "created_at": datetime.now(timezone.utc).isoformat(),
               "items": [{"request": item, "state": "pending"} for item in checked]}
        save_batch_job(job_id, job)
    if job["state"] == "complete":
        return job
    check_server_running()
    for entry in job["items"]:
        if entry["state"] in {"registered", "signed"}:
            continue
        item = entry["request"]
        try:
            previous = signed_batch_record(job_id, item)
            result = ({"serial": previous["serial"], "package": previous["package"]}
                      if previous else issue({**item, "_batch_job_id": job_id}, defer_registration=True))
            entry.update(result, state="signed")
            entry.pop("error", None)
        except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
            entry.update(state="failed", error=str(exc)[:300])
        save_batch_job(job_id, job)
    pending = [entry for entry in job["items"] if entry["state"] == "signed"]
    for entry in pending:
        try:
            record = next(item for item in inventory() if item["serial"] == entry["serial"])
            details = status(record)
            selected = entry["request"]
            if (details["in_groups"] == selected["in_groups"] and
                    details["out_groups"] == selected["out_groups"]):
                registry = load_registry()
                registry[entry["serial"]]["registered"] = True
                registry[entry["serial"]]["username"] = selected["cn"]
                save_registry(registry)
                entry["state"] = "registered"
                entry["expires_at"] = record["expires_at"]
                entry.pop("error", None)
                save_batch_job(job_id, job)
        except (RuntimeError, OSError, StopIteration):
            pass
    pending = [entry for entry in job["items"] if entry["state"] == "signed"]
    if pending:
        job["state"] = "registering"
        save_batch_job(job_id, job)
        try:
            tree = authentication_tree()
            for entry in pending:
                record = next(item for item in inventory() if item["serial"] == entry["serial"])
                selected = entry["request"]
                add_authentication_user(tree, record, selected["in_groups"], selected["out_groups"])
            write_authentication_tree(tree)
            restart_for_authentication()
            for entry in pending:
                record = checked_record(entry["serial"], next(
                    item["fingerprint"] for item in inventory() if item["serial"] == entry["serial"]))
                selected = entry["request"]
                try:
                    wait_for_groups(record, selected["in_groups"], selected["out_groups"], timeout=150)
                    registry = load_registry()
                    registry[entry["serial"]]["registered"] = True
                    registry[entry["serial"]]["username"] = selected["cn"]
                    save_registry(registry)
                    entry["state"] = "registered"
                    entry["expires_at"] = record["expires_at"]
                    entry.pop("error", None)
                except (RuntimeError, OSError) as exc:
                    entry["error"] = str(exc)[:300]
                save_batch_job(job_id, job)
        except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
            job["error"] = str(exc)[:300]
            save_batch_job(job_id, job)
    job["state"] = "complete" if all(entry["state"] == "registered" for entry in job["items"]) else "partial"
    save_batch_job(job_id, job)
    audit("issue_batch", [entry["serial"] for entry in job["items"] if "serial" in entry], job["state"])
    return job


def selected_records(items: object) -> list[dict]:
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError("Select between 1 and 100 certificates")
    records = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid certificate selection")
        record = checked_record(item.get("serial"), item.get("fingerprint"))
        if record["serial"] in {entry["serial"] for entry in records}:
            raise ValueError("Duplicate certificate selection")
        records.append(record)
    return records


def client_key(serial: str, registry: dict) -> tuple[Path, str] | None:
    metadata = registry.get(serial, {})
    identity = metadata.get("key_dir", "")
    legacy_rotation_dir = f"ca-rotation-alpha-{serial.lower()}"
    if identity and (not isinstance(identity, str) or not (
            re.fullmatch(r"[0-9a-f]{16}", identity) or identity == legacy_rotation_dir)):
        return None
    if identity:
        directory = PRIVATE / "clients" / identity
        if directory.is_symlink():
            return None
        key, password = directory / "key.pem", directory / "key.password"
    else:
        cert = x509.load_pem_x509_certificate(certificate_path(serial).read_bytes())
        names = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if not names or not COMMON_NAME.fullmatch(names[0].value):
            return None
        key = PRIVATE / f"{names[0].value}.key.pem"
        password = RUNTIME / "secrets" / "leaf_key_password"
    if not key.is_file() or not password.is_file():
        return None
    return key, password.read_text(encoding="ascii").strip()


def wait_for_cot_listener(timeout: int = 60) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((bind_ip(), 8089), timeout=2):
                return True
        except OSError:
            time.sleep(2)
    return False


def probe_8089(record: dict, registry: dict) -> str:
    key_info = client_key(record["serial"], registry)
    if not key_info:
        return "private-key-unavailable"
    key, password = key_info
    env = secret_env(TAK_PROBE_KEY_PASS=password)
    try:
        result = subprocess.run(
            [require_tool("openssl"), "s_client", "-brief", "-connect", f"{bind_ip()}:8089",
             "-servername", "takbox.local", "-cert", str(certificate_path(record["serial"])),
             "-key", str(key), "-pass", "env:TAK_PROBE_KEY_PASS", "-CAfile",
             str(PUBLIC / "root-ca.crt.pem"), "-verify_return_error"],
            cwd=PROJECT, env=env, input=b"\n", capture_output=True, timeout=12,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return "connection-unavailable"
    output = (result.stdout + result.stderr).decode("utf-8", "replace").lower()
    if "certificate revoked" in output or "alert number 44" in output:
        return "rejected-revoked"
    if "connection established" in output and result.returncode == 0:
        return "unexpectedly-accepted"
    return "unverified"


def revoke(items: object) -> dict:
    records = selected_records(items)
    pending = [record for record in records if not record["revoked"]]
    if not pending:
        raise ValueError("All selected certificates are already revoked")
    check_server_running()
    backup = ca_backup()
    openssl = require_tool("openssl")
    env = secret_env(TAK_INTERMEDIATE_PASS=(RUNTIME / "secrets" / "intermediate_ca_password")
                     .read_text(encoding="ascii").strip())
    results = []
    revoked = []
    for record in pending:
        serial = record["serial"]
        try:
            command([openssl, "ca", "-config", str(PRIVATE / "issuing-ca.cnf"),
                     "-revoke", str(certificate_path(serial)), "-crl_reason", "cessationOfOperation",
                     "-passin", "env:TAK_INTERMEDIATE_PASS"], env=env)
            revoked.append(serial)
            results.append({"serial": serial, "ca_revoked": True})
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
            results.append({"serial": serial, "ca_revoked": False, "error": str(exc)[:300]})
    published = restarted = False
    if revoked:
        try:
            command([require_tool("python"), str(PROJECT / "scripts" / "refresh_tak_crls.py")], timeout=90)
            published = True
            command([require_tool("docker"), "compose", "restart", "tak-server"], timeout=180)
            restarted = True
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
            results.append({"error": f"CRL/restart incomplete: {str(exc)[:300]}"})
    registry = load_registry()
    crl_serials = set()
    if published:
        crl = x509.load_pem_x509_crl((PUBLIC / "intermediate-ca.crl.pem").read_bytes())
        crl_serials = {format(item.serial_number, "X") for item in crl}
    for item in results:
        serial = item.get("serial")
        if serial:
            item["in_published_crl"] = serial in crl_serials
            item["validation_8089"] = "not-verified"
    if restarted and wait_for_cot_listener():
        with ThreadPoolExecutor(max_workers=8) as pool:
            checks = list(pool.map(lambda record: probe_8089(record, registry),
                                   [record for record in pending if record["serial"] in revoked]))
        checked = dict(zip(revoked, checks))
        for item in results:
            if item.get("serial") in checked:
                item["validation_8089"] = checked[item["serial"]]
    for serial in revoked:
        metadata = registry.get(serial)
        if metadata and metadata.get("package"):
            package = PACKAGES / metadata["package"]
            if package.is_file():
                archived = CONTROL / "retired-packages"
                archived.mkdir(parents=True, exist_ok=True)
                os.replace(package, archived / package.name)
            metadata["retired_package"] = metadata.pop("package")
    save_registry(registry)
    audit("revoke", revoked, "restarted" if restarted else "reload-incomplete")
    return {"results": results, "backup": backup, "crl_published": published,
            "tak_restarted": restarted,
            "validation_8443": "out-of-scope"}


def republish() -> dict:
    """Recover a CRL publication or restart that failed after CA revocation."""
    check_server_running()
    backup = ca_backup()
    command([require_tool("python"), str(PROJECT / "scripts" / "refresh_tak_crls.py")], timeout=90)
    command([require_tool("docker"), "compose", "restart", "tak-server"], timeout=180)
    revoked = [record for record in inventory() if record["revoked"]]
    crl = x509.load_pem_x509_crl((PUBLIC / "intermediate-ca.crl.pem").read_bytes())
    crl_serials = {format(item.serial_number, "X") for item in crl}
    checks = {}
    registry = load_registry()
    if revoked and wait_for_cot_listener():
        with ThreadPoolExecutor(max_workers=8) as pool:
            checks = dict(zip((item["serial"] for item in revoked),
                              pool.map(lambda record: probe_8089(record, registry), revoked)))
    results = [{"serial": record["serial"], "ca_revoked": True,
                "in_published_crl": record["serial"] in crl_serials,
                "validation_8089": checks.get(record["serial"], "not-verified")}
               for record in revoked]
    audit("republish", [record["serial"] for record in revoked], "restarted")
    return {"results": results, "backup": backup, "crl_published": True,
            "tak_restarted": True, "validation_8443": "out-of-scope"}


def rotation_status() -> dict:
    if not ROTATION_JOB.is_file():
        return {"state": "idle"}
    data = json.loads(ROTATION_JOB.read_text(encoding="utf-8"))
    if data.get("state") not in {"staging", "cutover", "renewing", "revoking", "complete", "failed", "interrupted"}:
        raise RuntimeError("Invalid CA replacement job state")
    return data


def save_rotation_status(data: dict) -> None:
    CONTROL.mkdir(parents=True, exist_ok=True)
    pending = ROTATION_JOB.with_suffix("." + uuid.uuid4().hex + ".pending")
    pending.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, ROTATION_JOB)


def start_ca_rotation(request: dict) -> dict:
    global ROTATION_THREAD
    with ROTATION_LOCK:
        if ROTATION_THREAD is not None and ROTATION_THREAD.is_alive():
            raise RuntimeError("A CA replacement is already running")
        current = rotation_status()
        if current["state"] not in {"idle", "complete"}:
            raise RuntimeError("Resolve the previous CA replacement before starting another")
        import ca_rotation_console as rotation
        expected = request.get("expected_ca_id")
        if not isinstance(expected, str) or expected != rotation.active_ca_summary()["id"]:
            raise RuntimeError("The issuing CA changed; refresh the page")
        selected = request.get("selected")
        prepared = rotation.prepare_selection(selected)
        check_server_running()
        job = {"id": uuid.uuid4().hex, "state": "staging",
               "message": "Preparing replacement CA", "started_at": datetime.now(timezone.utc).isoformat(),
               "old_ca_id": expected, "selected_count": len(prepared)}
        save_rotation_status(job)

        def run() -> None:
            def progress(state: str, message: str) -> None:
                job.update(state=state, message=message,
                           updated_at=datetime.now(timezone.utc).isoformat())
                save_rotation_status(job)
            try:
                result = rotation.rotate(selected, progress)
                job.update(state="complete", message="CA replacement completed", result=result)
            except Exception as exc:
                job.update(state="failed", message=str(exc)[:500])
                print(f"CA replacement failed: {type(exc).__name__}: {exc}", flush=True)
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_rotation_status(job)

        ROTATION_THREAD = Thread(target=run, name="tak-ca-replacement", daemon=False)
        ROTATION_THREAD.start()
        return {"job": job}


def execute(request: dict) -> dict:
    action = request.get("action")
    if action == "ca_rotate_status":
        return {"job": rotation_status()}
    if ROTATION_THREAD is not None and ROTATION_THREAD.is_alive():
        raise RuntimeError("CA replacement is running; wait for its result")
    if action == "ca_rotate_info":
        import ca_rotation_console as rotation
        return {"ca": rotation.active_ca_summary()}
    if action == "ca_rotate_start":
        return start_ca_rotation(request)
    if action == "snapshot":
        group_choices = {"local-test"}
        for metadata in load_registry().values():
            if isinstance(metadata, dict):
                group_choices.update(group for direction in ("in_groups", "out_groups")
                                     for group in metadata.get(direction, [])
                                     if isinstance(group, str) and GROUP.fullmatch(group))
        return {"certificates": inventory(), "archived_certificates": archived_inventory(),
                "group_choices": sorted(group_choices),
                "last_result": json.loads(LAST_RESULT.read_text(encoding="utf-8"))
                if LAST_RESULT.is_file() else None}
    if action == "status":
        record = checked_record(request.get("serial"), request.get("fingerprint"))
        return {"status": status(record)}
    if action == "groups":
        return {"status": set_groups(request.get("serial"), request.get("fingerprint"),
                                      request.get("in_groups"), request.get("out_groups"))}
    if action == "group_batch":
        return {"batch": set_group_batch(request.get("changes"))}
    if action == "issue":
        return issue(request)
    if action == "batch_issue":
        return {"batch": issue_batch(request.get("job_id"), request.get("items"))}
    if action == "batch_status":
        return {"batch": read_batch_job(request.get("job_id"))}
    if action == "validate_selection":
        return {"certificates": selected_records(request.get("selected"))}
    if action == "revoke":
        return revoke(request.get("selected"))
    if action == "republish":
        return republish()
    if action == "vx_prepare":
        return {"package": tak_vx_package_host.prepare(request.get("job_id"))}
    if action == "vx_status":
        return {"package": tak_vx_package_host.read_job(request.get("job_id"))}
    if action == "vx_replace":
        return {"package": tak_vx_package_host.replace(request.get("job_id"))}
    if action == "vx_restore":
        return {"package": tak_vx_package_host.restore(request.get("job_id"))}
    raise ValueError("Unsupported TAK certificate action")


def main() -> None:
    inbox, outbox = CONTROL / "inbox", CONTROL / "outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    previous_rotation = rotation_status()
    if previous_rotation["state"] in {"staging", "cutover", "renewing", "revoking"}:
        previous_rotation.update(state="interrupted", message="Host worker restarted during CA replacement; inspect runtime and snapshots before retrying")
        save_rotation_status(previous_rotation)
    heartbeat = CONTROL / "heartbeat"
    heartbeat_stop = Event()

    def keep_heartbeat() -> None:
        while not heartbeat_stop.wait(1):
            heartbeat.touch()

    heartbeat.touch()
    heartbeat_thread = Thread(target=keep_heartbeat, name="tak-certificate-heartbeat", daemon=True)
    heartbeat_thread.start()
    print("TAK certificate worker ready. Press Ctrl+C to stop.", flush=True)
    try:
        while True:
            for path in sorted(inbox.glob("*.json")):
                operation_id = path.stem
                if len(operation_id) != 32 or any(c not in "0123456789abcdef" for c in operation_id):
                    path.unlink(missing_ok=True)
                    continue
                payload = None
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if payload.get("id") != operation_id:
                        raise ValueError("Invalid request ID")
                    result = {"ok": True, **execute(payload)}
                    if payload.get("action") in {"issue", "groups", "group_batch", "revoke", "republish"}:
                        LAST_RESULT.write_text(json.dumps({"action": payload["action"],
                                                          "at": datetime.now(timezone.utc).isoformat(),
                                                          "result": result}, ensure_ascii=False), encoding="utf-8")
                except Exception as error:
                    print(f"TAK certificate operation failed: {type(error).__name__}: {error}", flush=True)
                    if isinstance(payload, dict) and payload.get("action") in {"issue", "groups", "group_batch", "revoke", "republish"}:
                        candidates = [payload.get("serial")]
                        selected = payload.get("selected")
                        if isinstance(selected, list):
                            candidates.extend(item.get("serial") for item in selected if isinstance(item, dict))
                        changes = payload.get("changes")
                        if isinstance(changes, list):
                            candidates.extend(item.get("serial") for item in changes if isinstance(item, dict))
                        serials = [value for value in candidates
                                   if isinstance(value, str) and SERIAL.fullmatch(value)]
                        audit(payload["action"], serials, f"failed:{type(error).__name__}")
                    result = {"ok": False, "error": str(error) if isinstance(error, (ValueError, RuntimeError))
                              else "TAK certificate operation failed; inspect the host worker"}
                pending = outbox / (operation_id + ".pending")
                pending.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
                os.replace(pending, outbox / (operation_id + ".json"))
                path.unlink(missing_ok=True)
            time.sleep(0.2)
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=2)
        heartbeat.unlink(missing_ok=True)


if __name__ == "__main__":
    from host_worker_lock import exclusive_worker

    try:
        with exclusive_worker(CONTROL):
            main()
    except KeyboardInterrupt:
        print("TAK certificate worker stopped.", flush=True)
