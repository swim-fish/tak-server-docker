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
from xml.sax.saxutils import escape

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID, NameOID


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
TAIPEI = timezone(timedelta(hours=8), "Asia/Taipei")
GROUP = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
COMMON_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,62}\Z")
SERIAL = re.compile(r"[0-9A-F]{1,40}\Z")


def command(args: list[str], *, env: dict[str, str] | None = None,
            timeout: int = 90, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(args, cwd=PROJECT, env=env, input=input_bytes,
                            capture_output=True, timeout=timeout)
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
            "issuer": cert.issuer.rfc4514_string(), "cn": cn_value,
            "name": metadata.get("name", cn_value),
            "expires_at": expiry.astimezone(TAIPEI).strftime("%Y-%m-%d %H:%M:%S"),
            "expires_iso": expiry.isoformat(), "days_left": days_text,
            "expiring_soon": timedelta(0) < remaining <= timedelta(days=30),
            "expired": remaining.total_seconds() <= 0,
            "revoked": fields[0] == "R", "revoked_at": fields[2] if fields[0] == "R" else None,
            "package": package, "registered": metadata.get("registered"),
            "username": metadata.get("username"),
        })
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


def tak_certificate_file(serial: str) -> str:
    directory = TAK_CERTS / "clients"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{serial}.pem"
    shutil.copy2(certificate_path(serial), target)
    return f"certs/files/clients/{serial}.pem"


def user_manager(*args: str) -> str:
    result = command([require_tool("docker"), "compose", "exec", "-T", "-w", "/opt/tak",
                      "tak-server", "java", "-jar", "utils/UserManager.jar", *args], timeout=60)
    return (result.stdout + result.stderr).decode("utf-8", "replace")


def parse_status(output: str) -> dict:
    result = {"username": None, "role": None, "fingerprint": None,
              "in_groups": [], "out_groups": [], "recognized": False}
    group_mode = None
    for line in output.splitlines():
        text = line.strip()
        if text.startswith("Username:"):
            result["username"] = text.partition(":")[2].strip().strip("'")
            group_mode = None
        elif text.startswith("Role:"):
            result["role"] = text.partition(":")[2].strip()
            group_mode = None
        elif text.startswith("Fingerprint:"):
            result["fingerprint"] = text.partition(":")[2].strip().replace(":", "").lower()
            group_mode = None
        elif text.startswith("Groups ("):
            label = text.split("(", 1)[1].split(")", 1)[0].lower()
            group_mode = ("read" in label, "write" in label)
            result["recognized"] = True
        elif group_mode and text and GROUP.fullmatch(text):
            if group_mode[1]:
                result["in_groups"].append(text)
            if group_mode[0]:
                result["out_groups"].append(text)
    result["in_groups"].sort()
    result["out_groups"].sort()
    return result


def status(record: dict) -> dict:
    details = parse_status(user_manager("certmod", "-s", tak_certificate_file(record["serial"])))
    if not details["recognized"] or details["fingerprint"] != record["fingerprint"]:
        raise RuntimeError("TAK status could not be matched to this certificate")
    return details


def set_groups(serial: str, fingerprint: str, in_values: object, out_values: object) -> dict:
    record = checked_record(serial, fingerprint, active=True)
    in_groups = checked_group_list(in_values)
    out_groups = checked_group_list(out_values)
    flags = group_flags(in_groups, out_groups)
    previous_metadata = load_registry().get(serial, {})
    if previous_metadata.get("registered") is not False:
        previous = status(record)
        if previous["role"] == "ROLE_ADMIN":
            raise ValueError("Administrator certificates cannot be changed in this console")
    path = tak_certificate_file(serial)
    backup = ca_backup()
    user_manager("certmod", *flags, path)
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


def issue(request: dict) -> dict:
    name = request.get("name", "")
    cn = request.get("cn", "")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or any(ord(c) < 32 for c in name):
        raise ValueError("Device display name must contain 1–80 printable characters")
    if not isinstance(cn, str) or not COMMON_NAME.fullmatch(cn):
        raise ValueError("Certificate CN must use 2–63 ASCII letters, digits, dots, dashes or underscores")
    in_groups = checked_group_list(request.get("in_groups"))
    out_groups = checked_group_list(request.get("out_groups"))
    flags = group_flags(in_groups, out_groups)
    check_server_running()
    openssl = require_tool("openssl")
    keytool = require_tool("keytool")
    issuing_ca = x509.load_pem_x509_certificate((PUBLIC / "intermediate.crt.pem").read_bytes())
    if issuing_ca.not_valid_after_utc - datetime.now(timezone.utc) < timedelta(days=731):
        raise RuntimeError("Issuing CA expires too soon for a two-year client certificate")
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
             "-extensions", "client_ext", "-extfile", str(ext), "-days", "730", "-notext",
             "-in", str(csr), "-out", str(cert_file), "-passin", "env:TAK_INTERMEDIATE_PASS"],
            env=env)
    cert = x509.load_pem_x509_certificate(cert_file.read_bytes())
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
                        "package": None, "key_dir": identity, "registered": False,
                        "in_groups": in_groups, "out_groups": out_groups, "backup": backup}
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
    try:
        path = tak_certificate_file(serial)
        user_manager("certmod", *flags, path)
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
    if isinstance(identity, str) and re.fullmatch(r"[0-9a-f]{16}", identity):
        directory = PRIVATE / "clients" / identity
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
            with socket.create_connection(("192.168.137.1", 8089), timeout=2):
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
            [require_tool("openssl"), "s_client", "-brief", "-connect", "192.168.137.1:8089",
             "-servername", "takbox.local", "-cert", str(certificate_path(record["serial"])),
             "-key", str(key), "-pass", "env:TAK_PROBE_KEY_PASS", "-CAfile",
             str(PUBLIC / "root-ca.crt.pem"), "-verify_return_error"],
            cwd=PROJECT, env=env, input=b"\n", capture_output=True, timeout=12)
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


def execute(request: dict) -> dict:
    action = request.get("action")
    if action == "snapshot":
        group_choices = {"local-test"}
        for metadata in load_registry().values():
            if isinstance(metadata, dict):
                group_choices.update(group for direction in ("in_groups", "out_groups")
                                     for group in metadata.get(direction, [])
                                     if isinstance(group, str) and GROUP.fullmatch(group))
        return {"certificates": inventory(), "group_choices": sorted(group_choices),
                "last_result": json.loads(LAST_RESULT.read_text(encoding="utf-8"))
                if LAST_RESULT.is_file() else None}
    if action == "status":
        record = checked_record(request.get("serial"), request.get("fingerprint"))
        return {"status": status(record)}
    if action == "groups":
        return {"status": set_groups(request.get("serial"), request.get("fingerprint"),
                                      request.get("in_groups"), request.get("out_groups"))}
    if action == "issue":
        return issue(request)
    if action == "validate_selection":
        return {"certificates": selected_records(request.get("selected"))}
    if action == "revoke":
        return revoke(request.get("selected"))
    if action == "republish":
        return republish()
    raise ValueError("Unsupported TAK certificate action")


def main() -> None:
    inbox, outbox = CONTROL / "inbox", CONTROL / "outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    heartbeat = CONTROL / "heartbeat"
    print("TAK certificate worker ready. Press Ctrl+C to stop.", flush=True)
    try:
        while True:
            heartbeat.write_text(str(time.time()), encoding="ascii")
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
                    if payload.get("action") in {"issue", "groups", "revoke", "republish"}:
                        LAST_RESULT.write_text(json.dumps({"action": payload["action"],
                                                          "at": datetime.now(timezone.utc).isoformat(),
                                                          "result": result}, ensure_ascii=False), encoding="utf-8")
                except Exception as error:
                    print(f"TAK certificate operation failed: {type(error).__name__}: {error}", flush=True)
                    if isinstance(payload, dict) and payload.get("action") in {"issue", "groups", "revoke", "republish"}:
                        candidates = [payload.get("serial")]
                        selected = payload.get("selected")
                        if isinstance(selected, list):
                            candidates.extend(item.get("serial") for item in selected if isinstance(item, dict))
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
        heartbeat.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("TAK certificate worker stopped.", flush=True)
