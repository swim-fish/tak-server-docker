#!/usr/bin/env python3
"""Operate the optional OpenLDAP directory that supplies TAK Server groups.

Certificates still authenticate clients; the directory only decides groups
(`<auth default="ldap" x509groups="true">`). Subcommands, in rollout order:

  prepare  create secrets, the env file, and the LDAPS server certificate
  init     create the read-only bind account, tighten the ACL (run once the container is healthy)
  sync     copy users and groups of valid certificates from UserAuthenticationFile.xml
  enable   switch CoreConfig.xml to LDAP groups (stops and starts tak-server)
  disable  switch CoreConfig.xml back to file groups
  status   show mode, container health, and directory counts
  backup   export the directory with slapcat

Passwords are never printed and never passed on a host command line.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
SECRETS = RUNTIME / "secrets"
PRIVATE = RUNTIME / "pki" / "private"
PUBLIC = RUNTIME / "pki" / "public"
LDAP_CERTS = RUNTIME / "pki" / "ldap"
CORE_CONFIG = RUNTIME / "tak" / "CoreConfig.xml"
AUTH_FILE = RUNTIME / "tak" / "UserAuthenticationFile.xml"
CA_INDEX = PRIVATE / "ca-db" / "index.txt"
BACKUPS = RUNTIME / "backups" / "ldap"

BASE_DN = "dc=tak,dc=local"
ADMIN = "ldapadm"
BIND_DN = f"cn=takbind,{BASE_DN}"
SERVICE = "tak-ldap"
GROUP_PREFIX = "tak_"
CONFIG_NS = "http://bbn.com/marti/xml/config"
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
DIRECTIONS = {"groupList": "", "groupListIN": "_WRITE", "groupListOUT": "_READ"}
ADMIN_BIND = ('-x -D "cn=$LDAP_ADMIN,$LDAP_BASE_DN" -y <(printf %s "$LDAP_ADMIN_PASSWORD") '
              "-H ldapi:///")


# ---------- pure helpers (unit tested) ----------

def file_users(xml: bytes) -> dict[str, list[str]]:
    """Map each file user to the directory group names that express its file groups."""
    users: dict[str, list[str]] = {}
    for user in ElementTree.fromstring(xml):
        if not user.tag.endswith("}User"):
            continue
        groups = []
        for child in user:
            suffix = DIRECTIONS.get(child.tag.rsplit("}", 1)[-1])
            name = (child.text or "").strip()
            if suffix is not None and name and name != "__ANON__":
                groups.append(f"{GROUP_PREFIX}{name}{suffix}")
        users[user.get("identifier", "")] = sorted(set(groups))
    return users


def valid_common_names(index: str, now: datetime) -> set[str]:
    """Common names with at least one unrevoked, unexpired certificate in the CA database."""
    stamp = now.strftime("%y%m%d%H%M%SZ")
    names = set()
    for line in index.splitlines():
        fields = line.split("\t")
        match = re.search(r"/CN=([^/]+)", fields[-1]) if len(fields) >= 6 else None
        if match and fields[0] == "V" and fields[1] > stamp:
            names.add(match.group(1))
    return names


def directory_plan(users: dict[str, list[str]], valid: set[str] | None
                   ) -> tuple[dict[str, list[str]], list[str]]:
    """Return ({group: members}, skipped users). Group-less users stay file-managed."""
    groups: dict[str, list[str]] = {}
    skipped = []
    for name, memberships in sorted(users.items()):
        bad = [value for value in [name, *memberships] if not SAFE_NAME.fullmatch(value)]
        if bad or not memberships or (valid is not None and name not in valid):
            skipped.append(name)
            continue
        for group in memberships:
            groups.setdefault(group, []).append(name)
    return groups, skipped


def user_ldif(name: str) -> str:
    return (f"dn: uid={name},ou=People,{BASE_DN}\nobjectClass: inetOrgPerson\n"
            f"uid: {name}\ncn: {name}\nsn: {name}\n\n")


def group_ldif(group: str, members: list[str], exists: bool) -> str:
    lines = [f"member: uid={name},ou=People,{BASE_DN}" for name in members]
    dn = f"dn: cn={group},ou=Group,{BASE_DN}\n"
    if exists:
        return dn + "changetype: modify\nreplace: member\n" + "\n".join(lines) + "\n\n"
    return (dn + f"changetype: add\nobjectClass: groupOfNames\ncn: {group}\n"
            + "\n".join(lines) + "\n\n")


def set_auth(xml: bytes, ldap: dict[str, str] | None) -> bytes:
    """Return CoreConfig with <auth> in LDAP-group mode, or file mode when ldap is None."""
    ElementTree.register_namespace("", CONFIG_NS)
    root = ElementTree.fromstring(xml)
    auth = root.find(f"{{{CONFIG_NS}}}auth")
    if auth is None or auth.find(f"{{{CONFIG_NS}}}File") is None:
        raise RuntimeError("CoreConfig.xml has no <auth> element with a <File> backend")
    for child in auth.findall(f"{{{CONFIG_NS}}}ldap"):
        auth.remove(child)
    for name in ("default", "x509groups", "x509addAnonymous"):
        auth.attrib.pop(name, None)
    if ldap is not None:
        auth.set("default", "ldap")
        auth.set("x509groups", "true")
        auth.set("x509addAnonymous", "false")
        ElementTree.SubElement(auth, f"{{{CONFIG_NS}}}ldap", ldap)
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def ldap_attributes(store_password: str, bind_password: str, interval: int) -> dict[str, str]:
    return {
        "url": f"ldaps://{SERVICE}:636/", "style": "DS",
        "userstring": f"uid={{username}},ou=People,{BASE_DN}",
        "userBaseRDN": f"ou=People,{BASE_DN}", "groupBaseRDN": f"ou=Group,{BASE_DN}",
        "groupObjectClass": "groupOfNames", "userObjectClass": "inetOrgPerson",
        "groupprefix": f"cn={GROUP_PREFIX}", "groupNameExtractorRegex": "cn=(.*?)(?:,|$)",
        "updateinterval": str(interval),  # seconds, despite the guide saying milliseconds
        "ldapsTruststore": "JKS",
        "ldapsTruststoreFile": "/opt/tak/certs/files/truststore-root.jks",
        "ldapsTruststorePass": store_password,
        "serviceAccountDN": BIND_DN, "serviceAccountCredential": bind_password,
    }


def auth_mode(xml: bytes) -> str:
    auth = ElementTree.fromstring(xml).find(f"{{{CONFIG_NS}}}auth")
    return "ldap" if auth is not None and auth.get("default") == "ldap" else "file"


# ---------- host and container plumbing ----------

def write_private(path: Path, data: bytes) -> None:
    """Create or replace a credential-bearing file readable by its owner only (POSIX)."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags, 0o600), "wb") as handle:
        handle.write(data)
    os.chmod(path, 0o600)


def secret(name: str) -> str:
    value = (SECRETS / name).read_text(encoding="ascii").strip()
    if not value:
        raise RuntimeError(f"Empty secret file: {name}")
    return value


def run(*args: str, stdin: str | None = None, env: dict[str, str] | None = None,
        check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(args, cwd=PROJECT, input=stdin, env=env, capture_output=True,
                            text=True, encoding="utf-8", timeout=300)
    if check and result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} {' '.join(args[1:4])} failed: "
                           f"{result.stderr.strip()[-400:]}")
    return result


def compose(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return run("docker", "compose", "--profile", "ldap", *args, **kwargs)


def in_ldap(script: str, stdin: str = "", check: bool = True) -> subprocess.CompletedProcess:
    return compose("exec", "-T", SERVICE, "bash", "-c", script, stdin=stdin, check=check)


def service_state(service: str) -> str:
    out = compose("ps", "-a", "--format", "{{.State}} {{.Health}}", service).stdout.strip()
    return out or "absent"


# ---------- subcommands ----------

def prepare(_: argparse.Namespace) -> None:
    SECRETS.mkdir(parents=True, exist_ok=True)
    LDAP_CERTS.mkdir(parents=True, exist_ok=True)
    for name in ("ldap_admin_password", "ldap_bind_password"):
        path = SECRETS / name
        if not path.exists():
            write_private(path, secrets.token_urlsafe(24).encode("ascii"))
            print(f"created runtime/secrets/{name}")
    write_private(SECRETS / "tak-ldap.env", (
        f"LDAP_BASE_DN={BASE_DN}\nLDAP_ADMIN={ADMIN}\n"
        f"LDAP_ADMIN_PASSWORD={secret('ldap_admin_password')}\n").encode("ascii"))
    cert, key = LDAP_CERTS / "server.crt", LDAP_CERTS / "server.key"
    if cert.exists() and key.exists():
        print("LDAPS certificate already present; left unchanged")
    else:
        openssl = shutil.which("openssl")
        if not openssl:
            raise RuntimeError("openssl is unavailable")
        env = dict(os.environ, TAK_INTERMEDIATE_PASS=secret("intermediate_ca_password"))
        csr, ext = PRIVATE / "tak-ldap.csr.pem", PRIVATE / "tak-ldap.ext"
        ext.write_text("[leaf_ext]\nbasicConstraints=critical,CA:FALSE\n"
                       "keyUsage=critical,digitalSignature,keyEncipherment\n"
                       "extendedKeyUsage=serverAuth\nsubjectKeyIdentifier=hash\n"
                       "authorityKeyIdentifier=keyid,issuer\n"
                       f"subjectAltName=DNS:{SERVICE}\n",
                       encoding="ascii", newline="\n")
        # slapd cannot prompt for a passphrase, so this key is stored unencrypted under runtime/.
        run(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072",
            "-out", str(key))
        os.chmod(key, 0o600)
        run(openssl, "req", "-new", "-sha256", "-key", str(key),
            "-subj", f"/C=TW/O=TAK Local/OU=Local Test/CN={SERVICE}", "-out", str(csr))
        run(openssl, "ca", "-batch", "-config", str(PRIVATE / "issuing-ca.cnf"),
            "-extensions", "leaf_ext", "-extfile", str(ext), "-days", "730", "-notext",
            "-in", str(csr), "-out", str(cert), "-passin", "env:TAK_INTERMEDIATE_PASS", env=env)
        print("issued LDAPS certificate for", SERVICE)
    shutil.copy2(PUBLIC / "ca-chain.pem", LDAP_CERTS / "root-ca.pem")
    print("prepared; next: docker compose --profile ldap up -d --build tak-ldap")


def init(_: argparse.Namespace) -> None:
    bind_password = secret("ldap_bind_password")
    exists = in_ldap(f'ldapsearch -LLL {ADMIN_BIND} -b "{BIND_DN}" -s base dn',
                     check=False).returncode == 0
    if exists:
        ldif = (f"dn: {BIND_DN}\nchangetype: modify\nreplace: userPassword\n"
                f"userPassword: {bind_password}\n")
        in_ldap(f"ldapmodify {ADMIN_BIND}", stdin=ldif)
        print("bind account present; password re-applied")
    else:
        ldif = (f"dn: cn=service-ppolicy,{BASE_DN}\nobjectClass: top\nobjectClass: device\n"
                "objectClass: pwdPolicy\ncn: service-ppolicy\npwdAttribute: userPassword\n"
                "pwdMaxAge: 0\npwdMustChange: FALSE\npwdLockout: FALSE\n"
                "pwdAllowUserChange: FALSE\n\n"
                f"dn: {BIND_DN}\nobjectClass: organizationalRole\n"
                "objectClass: simpleSecurityObject\ncn: takbind\n"
                f"userPassword: {bind_password}\n"
                f"pwdPolicySubentry: cn=service-ppolicy,{BASE_DN}\n")
        in_ldap(f"ldapadd {ADMIN_BIND}", stdin=ldif)
        print("created read-only bind account and its non-expiring policy")
    config = "-Q -Y EXTERNAL -H ldapi:///"
    access = in_ldap(f'ldapsearch {config} -LLL -o ldif-wrap=no '
                     '-b "olcDatabase={1}mdb,cn=config" -s base olcAccess').stdout
    if "cn=takbind" in access:
        print("ACL already restricted")
    else:
        ldif = ("dn: olcDatabase={1}mdb,cn=config\nchangetype: modify\ndelete: olcAccess\n"
                "olcAccess: {1}\n-\nadd: olcAccess\n"
                f'olcAccess: {{1}}to * by self read by dn.base="cn={ADMIN},{BASE_DN}" write '
                f'by dn.base="{BIND_DN}" read by * none\n')
        in_ldap(f"ldapmodify {config}", stdin=ldif)
        print("ACL restricted: anonymous read removed")
    check_bind()


def check_bind() -> None:
    probe = ('LDAPTLS_CACERT=/etc/ldap/certs/root-ca.pem ldapsearch -x -LLL '
             f'-H ldaps://{SERVICE}:636 -D "{BIND_DN}" -y <(cat) -b "{BASE_DN}" -s base dn')
    in_ldap(probe, stdin=secret("ldap_bind_password"))
    anonymous = in_ldap(f'ldapsearch -x -LLL -H ldap://localhost -b "ou=People,{BASE_DN}" dn',
                        check=False)
    if "dn:" in anonymous.stdout:
        raise RuntimeError("Anonymous bind can still read ou=People")
    print("verified: bind account reads over LDAPS; anonymous read is refused")


def sync(args: argparse.Namespace) -> None:
    users = file_users(AUTH_FILE.read_bytes())
    valid = None if args.all_users else valid_common_names(
        CA_INDEX.read_text(encoding="utf-8"), datetime.now(timezone.utc))
    groups, skipped = directory_plan(users, valid)
    members = sorted({name for names in groups.values() for name in names})
    print(f"file users: {len(users)}; to directory: {len(members)} users, {len(groups)} groups; "
          f"left file-managed: {len(skipped)}")
    if args.dry_run:
        for group, names in sorted(groups.items()):
            print(f"  {group}: {len(names)} member(s)")
        return
    existing = in_ldap(f'ldapsearch -LLL -o ldif-wrap=no {ADMIN_BIND} -b "ou=Group,{BASE_DN}" '
                       '"(objectClass=groupOfNames)" cn').stdout
    present = set(re.findall(r"^cn: (.+)$", existing, flags=re.M))
    # -c with exit 68 means "already exists", which is expected on a re-run.
    added = in_ldap(f"ldapadd -c {ADMIN_BIND}", stdin="".join(map(user_ldif, members)),
                    check=False)
    if added.returncode not in (0, 68):
        raise RuntimeError(f"adding users failed: {added.stderr.strip()[-300:]}")
    in_ldap(f"ldapmodify {ADMIN_BIND}",
            stdin="".join(group_ldif(group, names, group in present)
                          for group, names in sorted(groups.items())))
    extra = sorted(present - set(groups))
    print(f"directory updated; groups only in the directory (left untouched): {len(extra)}")


def switch(args: argparse.Namespace, to_ldap: bool) -> None:
    current = CORE_CONFIG.read_bytes()
    if to_ldap:
        if not service_state(SERVICE).startswith("running healthy"):
            raise RuntimeError(f"{SERVICE} is not running and healthy")
        check_bind()
        ldap = ldap_attributes(secret("tak_store_password"), secret("ldap_bind_password"),
                               args.interval)
    else:
        ldap = None
    updated = set_auth(current, ldap)
    was_running = service_state("tak-server").startswith("running")
    if was_running:
        compose("stop", "tak-server")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_private(BACKUPS / f"CoreConfig.{stamp}.xml", current)
    # Write in place: CoreConfig.xml is a single-file bind mount.
    with CORE_CONFIG.open("r+b") as handle:
        handle.write(updated)
        handle.truncate()
    print(f"CoreConfig.xml auth mode: {auth_mode(updated)} (previous copy in runtime/backups/ldap)")
    if was_running:
        compose("start", "tak-server")
        print("tak-server restarted; confirm groups with GET /Marti/api/subscriptions/all")


def status(_: argparse.Namespace) -> None:
    print("auth mode:", auth_mode(CORE_CONFIG.read_bytes()))
    state = service_state(SERVICE)
    print(f"{SERVICE}:", state)
    if state.startswith("running"):
        for label, base in (("users", "ou=People"), ("groups", "ou=Group")):
            out = in_ldap(f'ldapsearch -LLL {ADMIN_BIND} -b "{base},{BASE_DN}" -s one dn').stdout
            print(f"directory {label}:", out.count("dn:"))
        check_bind()


def backup(_: argparse.Namespace) -> None:
    target = BACKUPS / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target.mkdir(mode=0o700, parents=True)
    for number, name in ((0, "config.ldif"), (1, "data.ldif")):
        out = in_ldap(f"slapcat -n {number}").stdout
        if "dn:" not in out:
            raise RuntimeError(f"slapcat -n {number} returned no entries")
        write_private(target / name, out.encode("utf-8"))
    print("directory exported to", target.relative_to(PROJECT).as_posix(),
          "(contains password hashes; keep it out of Git)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare").set_defaults(run=prepare)
    commands.add_parser("init").set_defaults(run=init)
    sync_parser = commands.add_parser("sync")
    sync_parser.add_argument("--dry-run", action="store_true")
    sync_parser.add_argument("--all-users", action="store_true",
                             help="include users without a valid certificate in the CA database")
    sync_parser.set_defaults(run=sync)
    enable = commands.add_parser("enable")
    enable.add_argument("--interval", type=int, default=60, help="group refresh in seconds")
    enable.set_defaults(run=lambda args: switch(args, True))
    commands.add_parser("disable").set_defaults(run=lambda args: switch(args, False))
    commands.add_parser("status").set_defaults(run=status)
    commands.add_parser("backup").set_defaults(run=backup)
    args = parser.parse_args(argv)
    try:
        args.run(args)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
