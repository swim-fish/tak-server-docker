#!/usr/bin/env python3
"""Generate local TAK PKI, runtime configuration, and an ATAK Data Package."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import os
import re
import secrets
import shutil
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


PROJECT = Path(__file__).resolve().parents[1]
UPSTREAM = PROJECT / "vendor" / "takserver-docker-hardened-5.8-RELEASE-84"
RUNTIME = PROJECT / "runtime"
SECRETS = RUNTIME / "secrets"
PRIVATE = RUNTIME / "pki" / "private"
PUBLIC = RUNTIME / "pki" / "public"
CA_DB = PRIVATE / "ca-db"
ROOT_CA_DB = PRIVATE / "root-ca-db"
TAK_CERTS = RUNTIME / "tak" / "certs"
PACKAGES = RUNTIME / "packages"


def run(*args: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(args[:2]), "...")
    subprocess.run(args, check=True, env=env)


def write_secret(path: Path, value: str) -> None:
    path.write_text(value, encoding="ascii", newline="\n")


def concat(output: Path, *inputs: Path) -> None:
    with output.open("wb") as target:
        for source in inputs:
            target.write(source.read_bytes())
            if not source.read_bytes().endswith(b"\n"):
                target.write(b"\n")


def make_leaf(
    openssl: str,
    env: dict[str, str],
    name: str,
    common_name: str,
    eku: str,
    san: str | None = None,
) -> tuple[Path, Path]:
    key = PRIVATE / f"{name}.key.pem"
    csr = PRIVATE / f"{name}.csr.pem"
    cert = PUBLIC / f"{name}.crt.pem"
    ext = PRIVATE / f"{name}.ext"
    lines = [
        "basicConstraints=critical,CA:FALSE",
        "keyUsage=critical,digitalSignature,keyEncipherment",
        f"extendedKeyUsage={eku}",
        "subjectKeyIdentifier=hash",
        "authorityKeyIdentifier=keyid,issuer",
    ]
    if san:
        lines.append(f"subjectAltName={san}")
    ext.write_text("[leaf_ext]\n" + "\n".join(lines) + "\n", encoding="ascii", newline="\n")
    run(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-aes-256-cbc", "-pass", "env:TAK_LEAF_PASS", "-out", str(key), env=env)
    run(openssl, "req", "-new", "-sha256", "-key", str(key), "-passin", "env:TAK_LEAF_PASS", "-subj", f"/C=TW/O=TAK Local/OU=Local Test/CN={common_name}", "-out", str(csr), env=env)
    run(openssl, "ca", "-batch", "-config", str(PRIVATE / "issuing-ca.cnf"), "-extensions", "leaf_ext", "-extfile", str(ext), "-days", "730", "-notext", "-in", str(csr), "-out", str(cert), "-passin", "env:TAK_INTERMEDIATE_PASS", env=env)
    return key, cert


def export_p12(openssl: str, env: dict[str, str], name: str, key: Path, cert: Path, output: Path) -> None:
    run(openssl, "pkcs12", "-export", "-name", name, "-inkey", str(key), "-passin", "env:TAK_LEAF_PASS", "-in", str(cert), "-certfile", str(PUBLIC / "ca-chain.pem"), "-out", str(output), "-passout", "env:TAK_STORE_PASS", env=env)


def dns_name(value: str) -> str:
    value = value.strip()
    labels = value.split(".")
    if len(value) > 253 or not all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label) for label in labels):
        raise argparse.ArgumentTypeError("Enter a DNS name without a scheme, port, or trailing dot")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return value
    raise argparse.ArgumentTypeError("Use --ip for an IP address")


def ip_literal(value: str) -> str:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Enter a valid IP address without a port") from error


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", "--dns", type=dns_name, help="DNS SAN and preferred connection name; specify this and/or --ip")
    parser.add_argument("--ip", type=ip_literal, help="IP SAN and connection address when DNS is omitted")
    parser.add_argument("--client-name", default="atak-client")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not args.host and not args.ip:
        parser.error("Specify at least one of --host/--dns or --ip")
    args.server_name = args.host or args.ip
    args.server_san = ",".join(
        value for value in (f"DNS:{args.host}" if args.host else None, f"IP:{args.ip}" if args.ip else None) if value
    )
    return args


def main() -> int:
    args = parse_args()

    openssl = shutil.which("openssl")
    keytool = shutil.which("keytool")
    if not openssl or not keytool:
        raise SystemExit("openssl and keytool must be available on PATH")
    source_config = UPSTREAM / "tak" / "CoreConfig.example.xml"
    if not source_config.exists():
        raise SystemExit(f"Missing extracted upstream package: {source_config}")
    if (RUNTIME / "tak" / "CoreConfig.xml").exists() and not args.force:
        raise SystemExit("Runtime deployment already exists; use --force only when intentionally rotating all local credentials")
    if args.force:
        runtime_root = RUNTIME.resolve()
        for generated in (RUNTIME / "pki", RUNTIME / "tak", RUNTIME / "packages", RUNTIME / "secrets"):
            target = generated.resolve()
            if target.parent != runtime_root:
                raise SystemExit(f"Refusing to remove unexpected path: {target}")
            shutil.rmtree(target, ignore_errors=True)

    for directory in (
        SECRETS,
        PRIVATE,
        PUBLIC,
        TAK_CERTS,
        PACKAGES,
        RUNTIME / "tak",
        CA_DB / "newcerts",
        ROOT_CA_DB / "newcerts",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    values = {
        "TAK_ROOT_PASS": secrets.token_urlsafe(32),
        "TAK_INTERMEDIATE_PASS": secrets.token_urlsafe(32),
        "TAK_LEAF_PASS": secrets.token_urlsafe(32),
        "TAK_STORE_PASS": secrets.token_urlsafe(24),
        "TAK_DB_PASS": secrets.token_urlsafe(24),
        "MUMBLE_SERVER_PASS": secrets.token_urlsafe(24),
        "MUMBLE_SUPERUSER_PASS": secrets.token_urlsafe(24),
    }
    env = os.environ.copy()
    env.update(values)
    write_secret(SECRETS / "tak_store_password", values["TAK_STORE_PASS"])
    write_secret(SECRETS / "db_password", values["TAK_DB_PASS"])
    write_secret(SECRETS / "root_ca_password", values["TAK_ROOT_PASS"])
    write_secret(SECRETS / "intermediate_ca_password", values["TAK_INTERMEDIATE_PASS"])
    write_secret(SECRETS / "leaf_key_password", values["TAK_LEAF_PASS"])
    write_secret(SECRETS / "mumble_server_password", values["MUMBLE_SERVER_PASS"])
    write_secret(SECRETS / "mumble_superuser_password", values["MUMBLE_SUPERUSER_PASS"])

    root_key = PRIVATE / "root-ca.key.pem"
    root_cert = PUBLIC / "root-ca.crt.pem"
    run(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:4096", "-aes-256-cbc", "-pass", "env:TAK_ROOT_PASS", "-out", str(root_key), env=env)
    run(openssl, "req", "-new", "-x509", "-sha256", "-days", "3650", "-key", str(root_key), "-passin", "env:TAK_ROOT_PASS", "-subj", "/C=TW/O=TAK Local/OU=Offline Root/CN=TAK Local Root CA", "-addext", "basicConstraints=critical,CA:TRUE,pathlen:1", "-addext", "keyUsage=critical,keyCertSign,cRLSign", "-addext", "subjectKeyIdentifier=hash", "-out", str(root_cert), env=env)

    (ROOT_CA_DB / "index.txt").write_text("", encoding="ascii")
    (ROOT_CA_DB / "index.txt.attr").write_text("unique_subject = no\n", encoding="ascii", newline="\n")
    (ROOT_CA_DB / "serial").write_text("1000\n", encoding="ascii", newline="\n")
    (ROOT_CA_DB / "crlnumber").write_text("1000\n", encoding="ascii", newline="\n")
    root_ca_config = PRIVATE / "root-ca.cnf"
    root_ca_config.write_text(f'''[ca]
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

    intermediate_key = PRIVATE / "intermediate.key.pem"
    intermediate_csr = PRIVATE / "intermediate.csr.pem"
    intermediate_cert = PUBLIC / "intermediate.crt.pem"
    intermediate_ext = PRIVATE / "intermediate.ext"
    intermediate_ext.write_text("[v3_intermediate_ca]\nbasicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\n", encoding="ascii", newline="\n")
    run(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:4096", "-aes-256-cbc", "-pass", "env:TAK_INTERMEDIATE_PASS", "-out", str(intermediate_key), env=env)
    run(openssl, "req", "-new", "-sha256", "-key", str(intermediate_key), "-passin", "env:TAK_INTERMEDIATE_PASS", "-subj", "/C=TW/O=TAK Local/OU=Issuing CA/CN=TAK Local Issuing CA", "-out", str(intermediate_csr), env=env)
    run(openssl, "ca", "-batch", "-config", str(root_ca_config), "-extensions", "v3_intermediate_ca", "-extfile", str(intermediate_ext), "-days", "1825", "-notext", "-in", str(intermediate_csr), "-out", str(intermediate_cert), "-passin", "env:TAK_ROOT_PASS", env=env)
    concat(PUBLIC / "ca-chain.pem", intermediate_cert, root_cert)

    (CA_DB / "index.txt").write_text("", encoding="ascii")
    (CA_DB / "index.txt.attr").write_text("unique_subject = no\n", encoding="ascii", newline="\n")
    (CA_DB / "serial").write_text("1000\n", encoding="ascii", newline="\n")
    (CA_DB / "crlnumber").write_text("1000\n", encoding="ascii", newline="\n")
    ca_config = PRIVATE / "issuing-ca.cnf"
    ca_config.write_text(f'''[ca]
default_ca = issuing_ca

[issuing_ca]
dir = {CA_DB.as_posix()}
database = $dir/index.txt
new_certs_dir = $dir/newcerts
certificate = {intermediate_cert.as_posix()}
private_key = {intermediate_key.as_posix()}
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
''', encoding="ascii", newline="\n")

    server_key, server_cert = make_leaf(openssl, env, "takserver", args.server_name, "serverAuth,clientAuth", args.server_san)
    admin_key, admin_cert = make_leaf(openssl, env, "admin", "admin", "clientAuth")
    client_key, client_cert = make_leaf(openssl, env, "atak-client", args.client_name, "clientAuth")
    mumble_key, mumble_cert = make_leaf(openssl, env, "mumble", args.server_name, "serverAuth", args.server_san)

    root_crl = PUBLIC / "root-ca.crl.pem"
    crl = PUBLIC / "intermediate-ca.crl.pem"
    crl_bundle = PUBLIC / "ca-chain.crl.pem"
    run(openssl, "ca", "-gencrl", "-config", str(root_ca_config), "-out", str(root_crl), "-passin", "env:TAK_ROOT_PASS", env=env)
    run(openssl, "ca", "-gencrl", "-config", str(ca_config), "-out", str(crl), "-passin", "env:TAK_INTERMEDIATE_PASS", env=env)
    concat(crl_bundle, crl, root_crl)

    server_p12 = PRIVATE / "takserver.p12"
    export_p12(openssl, env, "takserver", server_key, server_cert, server_p12)
    run(keytool, "-importkeystore", "-noprompt", "-srckeystore", str(server_p12), "-srcstoretype", "PKCS12", "-srcstorepass:env", "TAK_STORE_PASS", "-destkeystore", str(TAK_CERTS / "takserver.jks"), "-deststoretype", "JKS", "-deststorepass:env", "TAK_STORE_PASS", "-destkeypass:env", "TAK_STORE_PASS", env=env)

    for alias, storetype, output in (("tak-root", "JKS", TAK_CERTS / "truststore-root.jks"), ("tak-root", "JKS", TAK_CERTS / "fed-truststore.jks"), ("tak-root", "PKCS12", PACKAGES / "caCert.p12")):
        run(keytool, "-importcert", "-noprompt", "-alias", alias, "-file", str(root_cert), "-keystore", str(output), "-storetype", storetype, "-storepass:env", "TAK_STORE_PASS", env=env)
    for storetype, output in (
        ("JKS", TAK_CERTS / "truststore-root.jks"),
        ("JKS", TAK_CERTS / "fed-truststore.jks"),
        ("PKCS12", PACKAGES / "caCert.p12"),
    ):
        run(keytool, "-importcert", "-noprompt", "-alias", "tak-issuing", "-file", str(intermediate_cert), "-keystore", str(output), "-storetype", storetype, "-storepass:env", "TAK_STORE_PASS", env=env)

    export_p12(openssl, env, "admin", admin_key, admin_cert, TAK_CERTS / "admin.p12")
    export_p12(openssl, env, args.client_name, client_key, client_cert, PACKAGES / "clientCert.p12")
    concat(TAK_CERTS / "admin.pem", admin_cert, intermediate_cert, root_cert)
    shutil.copy2(root_cert, TAK_CERTS / "root-ca.pem")
    shutil.copy2(intermediate_cert, TAK_CERTS / "intermediate-ca.pem")
    shutil.copy2(root_crl, TAK_CERTS / "root-ca.crl.pem")
    shutil.copy2(crl, TAK_CERTS / "intermediate-ca.crl.pem")
    shutil.copy2(crl_bundle, TAK_CERTS / "ca-chain.crl.pem")
    concat(RUNTIME / "pki" / "mumble-fullchain.pem", mumble_cert, intermediate_cert)
    shutil.copy2(mumble_key, RUNTIME / "pki" / "mumble-server.key.pem")

    run(openssl, "pkcs12", "-export", "-name", "tak-issuing-ca", "-inkey", str(intermediate_key), "-passin", "env:TAK_INTERMEDIATE_PASS", "-in", str(intermediate_cert), "-certfile", str(root_cert), "-out", str(PRIVATE / "intermediate-signing.p12"), "-passout", "env:TAK_STORE_PASS", env=env)

    config = source_config.read_text(encoding="utf-8")
    config = config.replace("jdbc:postgresql://tak-database:5432/cot", "jdbc:postgresql://tak-db:5432/cot")
    config = config.replace("<auth>", '<auth x509checkRevocation="true">', 1)
    database_password_attribute = 'password="' + values["TAK_DB_PASS"] + '"'
    config = config.replace('password=""', database_password_attribute, 1)
    config = config.replace('keystorePass="atakatak"', f'keystorePass="{values["TAK_STORE_PASS"]}"')
    config = config.replace('truststorePass="atakatak"', f'truststorePass="{values["TAK_STORE_PASS"]}"')
    config = config.replace('<!-- <crl _name="TAKServer CA" crlFile="certs/files/ca.crl"/>  -->', '<crl _name="TAK Local Issuing CA" crlFile="/opt/tak/certs/files/intermediate-ca.crl.pem"/>')
    config = re.sub(r'^\s*<connector port="8444".*?\r?\n', '', config, flags=re.MULTILINE)
    config = re.sub(r'^\s*<connector port="8446".*?\r?\n', '', config, flags=re.MULTILINE)
    (RUNTIME / "tak" / "CoreConfig.xml").write_text(config, encoding="utf-8", newline="\n")
    (RUNTIME / "tak" / "UserAuthenticationFile.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<UserAuthenticationFile xmlns="http://bbn.com/marti/xml/bindings"/>\n',
        encoding="utf-8",
        newline="\n",
    )

    prefs = f'''<?xml version="1.0" encoding="UTF-8"?>
<preferences>
  <preference version="1" name="cot_streams">
    <entry key="count" class="class java.lang.Integer">1</entry>
    <entry key="description0" class="class java.lang.String">Local TAK Server 5.8</entry>
    <entry key="connectString0" class="class java.lang.String">{escape(args.server_name)}:8089:ssl</entry>
    <entry key="enabled0" class="class java.lang.Boolean">true</entry>
    <entry key="useAuth0" class="class java.lang.Boolean">false</entry>
    <entry key="caLocation0" class="class java.lang.String">cert/caCert.p12</entry>
    <entry key="caPassword0" class="class java.lang.String">{values["TAK_STORE_PASS"]}</entry>
    <entry key="certificateLocation0" class="class java.lang.String">cert/clientCert.p12</entry>
    <entry key="clientPassword0" class="class java.lang.String">{values["TAK_STORE_PASS"]}</entry>
  </preference>
  <preference version="1" name="com.atakmap.app_preferences">
    <entry key="displayServerConnectionWidget" class="class java.lang.Boolean">true</entry>
  </preference>
</preferences>
'''
    uid = str(uuid.uuid4())
    manifest = f'''<?xml version="1.0" encoding="UTF-8"?>
<MissionPackageManifest version="2">
  <Configuration>
    <Parameter name="name" value="ATAK Local TAK 5.8"/>
    <Parameter name="uid" value="{uid}"/>
    <Parameter name="remarks" value="Device certificate for {escape(args.client_name)}"/>
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
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("MANIFEST/manifest.xml", manifest)
        archive.writestr("config/servers.pref", prefs)
        archive.write(PACKAGES / "caCert.p12", "cert/caCert.p12")
        archive.write(PACKAGES / "clientCert.p12", "cert/clientCert.p12")

    for cert in (intermediate_cert, server_cert, admin_cert, client_cert, mumble_cert):
        run(openssl, "verify", "-CAfile", str(root_cert), "-untrusted", str(intermediate_cert), str(cert), env=env)
    for cert in (server_cert, admin_cert, client_cert, mumble_cert):
        run(openssl, "verify", "-crl_check_all", "-CRLfile", str(crl_bundle), "-CAfile", str(root_cert), "-untrusted", str(intermediate_cert), str(cert), env=env)
    run(openssl, "crl", "-in", str(root_crl), "-noout", "-issuer", "-lastupdate", "-nextupdate")
    run(openssl, "crl", "-in", str(crl), "-noout", "-issuer", "-lastupdate", "-nextupdate")
    for cert in (server_cert, mumble_cert):
        if args.host:
            run(openssl, "verify", "-CAfile", str(root_cert), "-untrusted", str(intermediate_cert), "-purpose", "sslserver", "-verify_hostname", args.host, str(cert), env=env)
        if args.ip:
            run(openssl, "verify", "-CAfile", str(root_cert), "-untrusted", str(intermediate_cert), "-purpose", "sslserver", "-verify_ip", args.ip, str(cert), env=env)
    run(keytool, "-list", "-keystore", str(TAK_CERTS / "takserver.jks"), "-storepass:env", "TAK_STORE_PASS", env=env)
    run(openssl, "pkcs12", "-in", str(PACKAGES / "clientCert.p12"), "-passin", "env:TAK_STORE_PASS", "-noout", "-info", env=env)

    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (PACKAGES / "atak-local-test.sha256").write_text(f"{digest}  {package.name}\n", encoding="ascii", newline="\n")
    print(f"Created {package}")
    print(f"SHA-256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
