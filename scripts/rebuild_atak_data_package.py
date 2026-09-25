#!/usr/bin/env python3
"""Rebuild the ATAK Data Package without rotating the existing local PKI."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from atak_package_identity import write_identity


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
PACKAGES = RUNTIME / "packages" / "atak"
PUBLIC = RUNTIME / "pki" / "public"
SECRETS = RUNTIME / "secrets"


def run(*args: str, env: dict[str, str]) -> None:
    subprocess.run(args, check=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="takbox.local")
    parser.add_argument("--client-name", default="atak-client")
    args = parser.parse_args()

    keytool = shutil.which("keytool")
    if not keytool:
        raise SystemExit("keytool must be available on PATH")

    store_password_file = SECRETS / "tak_store_password"
    client_store = PACKAGES / "clientCert.p12"
    root_cert = PUBLIC / "root-ca.crt.pem"
    issuing_cert = PUBLIC / "intermediate.crt.pem"
    required = (store_password_file, client_store, root_cert, issuing_cert)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Missing ATAK package inputs:\n" + "\n".join(missing))

    password = store_password_file.read_text(encoding="ascii").strip()
    env = os.environ.copy()
    env["TAK_STORE_PASS"] = password
    PACKAGES.mkdir(parents=True, exist_ok=True)

    ca_store = PACKAGES / "caCert.p12"
    temporary_ca_store = PACKAGES / "caCert.p12.new"
    temporary_ca_store.unlink(missing_ok=True)
    for alias, certificate in (("tak-root", root_cert), ("tak-issuing", issuing_cert)):
        run(
            keytool,
            "-importcert",
            "-noprompt",
            "-alias",
            alias,
            "-file",
            str(certificate),
            "-keystore",
            str(temporary_ca_store),
            "-storetype",
            "PKCS12",
            "-storepass:env",
            "TAK_STORE_PASS",
            env=env,
        )
    os.replace(temporary_ca_store, ca_store)

    prefs = f'''<?xml version="1.0" encoding="UTF-8"?>
<preferences>
  <preference version="1" name="cot_streams">
    <entry key="count" class="class java.lang.Integer">1</entry>
    <entry key="description0" class="class java.lang.String">Local TAK Server 5.8</entry>
    <entry key="connectString0" class="class java.lang.String">{escape(args.host)}:8089:ssl</entry>
    <entry key="enabled0" class="class java.lang.Boolean">true</entry>
    <entry key="useAuth0" class="class java.lang.Boolean">false</entry>
    <entry key="caLocation0" class="class java.lang.String">cert/caCert.p12</entry>
    <entry key="caPassword0" class="class java.lang.String">{password}</entry>
    <entry key="certificateLocation0" class="class java.lang.String">cert/clientCert.p12</entry>
    <entry key="clientPassword0" class="class java.lang.String">{password}</entry>
  </preference>
  <preference version="1" name="com.atakmap.app_preferences">
    <entry key="displayServerConnectionWidget" class="class java.lang.Boolean">true</entry>
  </preference>
</preferences>
'''
    manifest = f'''<?xml version="1.0" encoding="UTF-8"?>
<MissionPackageManifest version="2">
  <Configuration>
    <Parameter name="name" value="ATAK Local TAK 5.8 v2"/>
    <Parameter name="uid" value="{uuid.uuid4()}"/>
    <Parameter name="remarks" value="Device certificate and intermediate trust for {escape(args.client_name)}"/>
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

    package = PACKAGES / "atak-local-test.dpk"
    temporary_package = PACKAGES / "atak-local-test.dpk.new"
    with zipfile.ZipFile(temporary_package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("MANIFEST/manifest.xml", manifest)
        archive.writestr("config/servers.pref", prefs)
        archive.write(ca_store, "cert/caCert.p12")
        archive.write(client_store, "cert/clientCert.p12")
    os.replace(temporary_package, package)

    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    write_identity(package, PUBLIC / "atak-client.crt.pem")
    (PACKAGES / "atak-local-test.sha256").write_text(
        f"{digest}  {package.name}\n", encoding="ascii", newline="\n"
    )
    print(f"Created {package}")
    print(f"SHA-256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
