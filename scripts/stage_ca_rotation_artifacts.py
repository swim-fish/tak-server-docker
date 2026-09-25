#!/usr/bin/env python3
"""Prepare replacement service certificates and device DPKs without deploying them."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from local_network import bind_ip


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
STAGES = RUNTIME / "ca-rotation-stage"
PUBLIC = RUNTIME / "pki" / "public"
SECRETS = RUNTIME / "secrets"


def run(*args: str, env: dict[str, str]) -> None:
    result = subprocess.run(args, cwd=PROJECT, env=env, capture_output=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()[-500:]
        raise RuntimeError(f"{Path(args[0]).name} failed: {detail}")


def concat(output: Path, *sources: Path) -> None:
    output.write_bytes(b"".join(source.read_bytes().rstrip(b"\n") + b"\n" for source in sources))


def issue_leaf(stage: Path, name: str, cn: str, eku: str, san: str | None,
               *, encrypted: bool, env: dict[str, str]) -> tuple[Path, Path]:
    private = stage / "artifacts" / "private"
    public = stage / "artifacts" / "public"
    key, csr, cert = private / f"{name}.key.pem", private / f"{name}.csr.pem", public / f"{name}.crt.pem"
    ext = private / f"{name}.ext"
    lines = ["[leaf_ext]", "basicConstraints=critical,CA:FALSE",
             "keyUsage=critical,digitalSignature,keyEncipherment", f"extendedKeyUsage={eku}",
             "subjectKeyIdentifier=hash", "authorityKeyIdentifier=keyid,issuer"]
    if san:
        lines.append(f"subjectAltName={san}")
    ext.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    openssl = shutil.which("openssl")
    if not openssl:
        raise RuntimeError("openssl is unavailable")
    key_args = [openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072"]
    if encrypted:
        key_args += ["-aes-256-cbc", "-pass", "env:TAK_NEW_LEAF_PASS"]
    run(*key_args, "-out", str(key), env=env)
    req_args = [openssl, "req", "-new", "-sha256", "-key", str(key)]
    if encrypted:
        req_args += ["-passin", "env:TAK_NEW_LEAF_PASS"]
    run(*req_args, "-subj", f"/C=TW/O=TAK Local/OU=Local Test/CN={cn}", "-out", str(csr), env=env)
    run(openssl, "ca", "-batch", "-config", str(stage / "issuing-ca.cnf"),
        "-extensions", "leaf_ext", "-extfile", str(ext), "-days", "730", "-notext",
        "-in", str(csr), "-out", str(cert), "-passin", "env:TAK_NEW_INTERMEDIATE_PASS", env=env)
    run(openssl, "verify", "-CAfile", str(PUBLIC / "root-ca.crt.pem"),
        "-untrusted", str(stage / "intermediate.crt.pem"), str(cert), env=env)
    if "serverAuth" in eku:
        run(openssl, "verify", "-purpose", "sslserver", "-verify_hostname", "takbox.local",
            "-CAfile", str(PUBLIC / "root-ca.crt.pem"),
            "-untrusted", str(stage / "intermediate.crt.pem"), str(cert), env=env)
    return key, cert


def export_p12(name: str, key: Path, cert: Path, output: Path,
               *, env: dict[str, str]) -> None:
    openssl = shutil.which("openssl")
    if not openssl:
        raise RuntimeError("openssl is unavailable")
    run(openssl, "pkcs12", "-export", "-name", name,
        "-inkey", str(key), "-passin", "env:TAK_NEW_LEAF_PASS", "-in", str(cert),
        "-certfile", str(output.parents[1] / "ca-chain.pem"),
        "-out", str(output), "-passout", "env:TAK_STORE_PASS", env=env)


def truststore(output: Path, storetype: str, *, stage: Path, env: dict[str, str]) -> None:
    keytool = shutil.which("keytool")
    if not keytool:
        raise RuntimeError("keytool is unavailable")
    for alias, cert in (("tak-root", PUBLIC / "root-ca.crt.pem"),
                        ("tak-issuing-old", PUBLIC / "intermediate.crt.pem"),
                        ("tak-issuing", stage / "intermediate.crt.pem")):
        run(keytool, "-importcert", "-noprompt", "-alias", alias, "-file", str(cert),
            "-keystore", str(output), "-storetype", storetype,
            "-storepass:env", "TAK_STORE_PASS", env=env)


def device_package(output: Path, cn: str, cert: Path, key: Path, ca_store: Path,
                   *, env: dict[str, str]) -> dict:
    store = output.with_suffix(".p12")
    export_p12(cn, key, cert, store, env=env)
    password = env["TAK_STORE_PASS"]
    prefs = f'''<?xml version="1.0" encoding="UTF-8"?>
<preferences><preference version="1" name="cot_streams">
<entry key="count" class="class java.lang.Integer">1</entry>
<entry key="description0" class="class java.lang.String">Local TAK Server 5.8</entry>
<entry key="connectString0" class="class java.lang.String">takbox.local:8089:ssl</entry>
<entry key="enabled0" class="class java.lang.Boolean">true</entry>
<entry key="useAuth0" class="class java.lang.Boolean">false</entry>
<entry key="caLocation0" class="class java.lang.String">cert/caCert.p12</entry>
<entry key="caPassword0" class="class java.lang.String">{escape(password)}</entry>
<entry key="certificateLocation0" class="class java.lang.String">cert/clientCert.p12</entry>
<entry key="clientPassword0" class="class java.lang.String">{escape(password)}</entry>
</preference><preference version="1" name="com.atakmap.app_preferences">
<entry key="displayServerConnectionWidget" class="class java.lang.Boolean">true</entry>
</preference></preferences>
'''
    manifest = f'''<?xml version="1.0" encoding="UTF-8"?>
<MissionPackageManifest version="2"><Configuration>
<Parameter name="name" value="ATAK Local TAK 5.8 {escape(cn)}"/>
<Parameter name="uid" value="{uuid.uuid4()}"/>
<Parameter name="remarks" value="Replacement CA test certificate"/>
<Parameter name="onReceiveImport" value="true"/>
<Parameter name="onReceiveDelete" value="false"/>
</Configuration><Contents>
<Content zipEntry="cert/caCert.p12"><Parameter name="contentType" value="P12 Certificate"/></Content>
<Content zipEntry="cert/clientCert.p12"><Parameter name="contentType" value="P12 Certificate"/></Content>
<Content zipEntry="config/servers.pref"><Parameter name="contentType" value="ATAK Preferences"/></Content>
</Contents></MissionPackageManifest>
'''
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("MANIFEST/manifest.xml", manifest)
        archive.writestr("config/servers.pref", prefs)
        archive.write(ca_store, "cert/caCert.p12")
        archive.write(store, "cert/clientCert.p12")
    leaf = x509.load_pem_x509_certificate(cert.read_bytes())
    return {"cn": cn, "serial": format(leaf.serial_number, "X"),
            "fingerprint": leaf.fingerprint(hashes.SHA256()).hex().upper(),
            "package": output.name}


def prepare(stage: Path, *, include_test_devices: bool = True) -> None:
    stage = stage.resolve(strict=True)
    if stage.parent != STAGES.resolve(strict=True) or not stage.name.startswith("issuing-"):
        raise ValueError("Stage must be a direct child of runtime/ca-rotation-stage")
    if (stage / "old-ca-id.txt").read_text(encoding="ascii").strip().upper() != x509.load_pem_x509_certificate(
            (PUBLIC / "intermediate.crt.pem").read_bytes()).fingerprint(hashes.SHA256()).hex().upper():
        raise RuntimeError("Active CA changed after stage creation")
    artifacts = stage / "artifacts"
    artifacts.mkdir(exist_ok=False)
    for name in ("private", "public", "tak-certs", "packages"):
        (artifacts / name).mkdir()
    leaf_password = secrets.token_urlsafe(36)
    (artifacts / "private" / "leaf.password").write_text(leaf_password + "\n", encoding="ascii")
    env = os.environ.copy()
    env["TAK_NEW_INTERMEDIATE_PASS"] = (stage / "intermediate.password").read_text(encoding="ascii").strip()
    env["TAK_NEW_LEAF_PASS"] = leaf_password
    env["TAK_STORE_PASS"] = (SECRETS / "tak_store_password").read_text(encoding="ascii").strip()
    concat(artifacts / "ca-chain.pem", stage / "intermediate.crt.pem", PUBLIC / "root-ca.crt.pem")
    names = [("takserver", "takbox.local", "serverAuth,clientAuth", f"DNS:takbox.local,IP:{bind_ip()}", True),
             ("admin", "admin", "clientAuth", None, True),
             ("mumble", "takbox.local", "serverAuth", "DNS:takbox.local", True),
             ("mediamtx", "takbox.local", "serverAuth", "DNS:takbox.local", False)]
    if include_test_devices:
        names.extend((("alpha", "ca-test-alpha-rotated-20260924", "clientAuth", None, True),
                      ("bravo", "ca-test-bravo-rotated-20260924", "clientAuth", None, True)))
    issued = {}
    for name, cn, eku, san, encrypted in names:
        issued[name] = issue_leaf(stage, name, cn, eku, san, encrypted=encrypted, env=env)
    private, public, tak = artifacts / "private", artifacts / "public", artifacts / "tak-certs"
    export_p12("takserver", *issued["takserver"], private / "takserver.p12", env=env)
    keytool = shutil.which("keytool")
    if not keytool:
        raise RuntimeError("keytool is unavailable")
    run(keytool, "-importkeystore", "-noprompt", "-srckeystore", str(private / "takserver.p12"),
        "-srcstoretype", "PKCS12", "-srcstorepass:env", "TAK_STORE_PASS",
        "-destkeystore", str(tak / "takserver.jks"), "-deststoretype", "JKS",
        "-deststorepass:env", "TAK_STORE_PASS", "-destkeypass:env", "TAK_STORE_PASS", env=env)
    truststore(tak / "truststore-root.jks", "JKS", stage=stage, env=env)
    truststore(tak / "fed-truststore.jks", "JKS", stage=stage, env=env)
    truststore(artifacts / "packages" / "caCert.p12", "PKCS12", stage=stage, env=env)
    export_p12("admin", *issued["admin"], tak / "admin.p12", env=env)
    concat(tak / "admin.pem", issued["admin"][1], stage / "intermediate.crt.pem", PUBLIC / "root-ca.crt.pem")
    concat(artifacts / "mumble-fullchain.pem", issued["mumble"][1], stage / "intermediate.crt.pem")
    concat(artifacts / "mediamtx-fullchain.pem", issued["mediamtx"][1], stage / "intermediate.crt.pem")
    metadata = {"new_ca_id": (stage / "ca-id.txt").read_text(encoding="ascii").strip(), "devices": {}}
    if include_test_devices:
        for name in ("alpha", "bravo"):
            cn = next(item[1] for item in names if item[0] == name)
            package = artifacts / "packages" / f"atak-{name}-rotated.dpk"
            metadata["devices"][name] = device_package(package, cn, issued[name][1], issued[name][0],
                                                        artifacts / "packages" / "caCert.p12", env=env)
    (artifacts / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Replacement service certificates and {len(metadata['devices'])} DPKs staged in {artifacts.relative_to(PROJECT)}")
    print("Active services, certificates, CA database and deployed CRLs are unchanged.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    args = parser.parse_args()
    prepare(args.stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
