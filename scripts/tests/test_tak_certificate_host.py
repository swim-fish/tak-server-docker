"""Safety checks for the host-side TAK certificate controller."""

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from cryptography.hazmat.primitives.serialization import pkcs12
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tak_certificate_host as host


def certificate(serial: int, cn: str, expires: datetime) -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(serial).not_valid_before(expires - timedelta(days=10))
            .not_valid_after(expires)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
            .sign(key, hashes.SHA256()))
    return cert.public_bytes(serialization.Encoding.PEM)


class CertificateHostTests(unittest.TestCase):
    def test_commands_do_not_open_a_console_window(self):
        completed = subprocess.CompletedProcess(["docker"], 0, b"ok", b"")
        with patch.object(host.subprocess, "run", return_value=completed) as launch:
            self.assertEqual(host.command(["docker", "compose", "ps"]).stdout, b"ok")
        self.assertEqual(launch.call_args.kwargs["creationflags"],
                         getattr(host.subprocess, "CREATE_NO_WINDOW", 0))

    def test_api_status_checks_authentication_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            (runtime / "tak").mkdir()
            auth = runtime / "tak/UserAuthenticationFile.xml"
            auth.write_text('<UserAuthenticationFile xmlns="http://bbn.com/marti/xml/bindings">'
                            '<User identifier="device-01" fingerprint="0A:0B"/></UserAuthenticationFile>')
            record = {"cn": "device-01", "fingerprint": "0a0b"}
            with patch.object(host, "RUNTIME", runtime), \
                 patch.object(host.tak_api_client, "get_groups", return_value={
                     "username": "device-01", "groupList": ["shared"],
                     "groupListIN": ["publish"], "groupListOUT": ["observe"]}):
                result = host.status(record)
                self.assertEqual(result["in_groups"], ["publish", "shared"])
                self.assertEqual(result["out_groups"], ["observe", "shared"])
                record["fingerprint"] = "abcd"
                with self.assertRaisesRegex(RuntimeError, "fingerprint"):
                    host.status(record)

    def test_inventory_excludes_admin_and_keeps_expiry_separate_from_revocation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ca_db = root / "private/ca-db"
            public = root / "public"
            control = root / "control"
            packages = root / "packages"
            (ca_db / "newcerts").mkdir(parents=True)
            public.mkdir()
            control.mkdir()
            packages.mkdir()
            now = datetime(2026, 9, 23, 0, 0, tzinfo=timezone.utc)
            (ca_db / "newcerts/1001.pem").write_bytes(certificate(0x1001, "admin", now + timedelta(days=20)))
            (public / "admin.crt.pem").write_bytes((ca_db / "newcerts/1001.pem").read_bytes())
            (ca_db / "newcerts/1002.pem").write_bytes(certificate(0x1002, "tablet", now + timedelta(hours=12)))
            (ca_db / "newcerts/1003.pem").write_bytes(certificate(0x1003, "old-tablet", now - timedelta(days=1)))
            (ca_db / "index.txt").write_text(
                "V\t261013000000Z\t\t1001\tunknown\t/CN=admin\n"
                "V\t260923120000Z\t\t1002\tunknown\t/CN=tablet\n"
                "R\t260922000000Z\t260921000000Z\t1003\tunknown\t/CN=old-tablet\n")
            (control / "registry.json").write_text(json.dumps({"1002": {"name": "Field device"}}))
            with patch.multiple(host, CA_DB=ca_db, PUBLIC=public, CONTROL=control,
                                REGISTRY=control / "registry.json", PACKAGES=packages):
                rows = host.inventory(now)
                self.assertEqual([item["serial"] for item in rows], ["1003", "1002"])
                self.assertEqual(rows[1]["name"], "Field device")
                self.assertEqual(rows[1]["days_left"], "少於 1 天")
                self.assertTrue(rows[0]["expired"])
                self.assertTrue(rows[0]["revoked"])
                self.assertFalse(rows[1]["revoked"])
                with self.assertRaises(RuntimeError):
                    host.checked_record("1002", "0" * 64)

    def test_group_flags_map_in_and_out_groups(self):
        self.assertEqual(host.group_flags(["publish", "shared"], ["observe", "shared"]),
                         ["-g", "shared", "-ig", "publish", "-og", "observe"])

    def test_volume_registration_preserves_bind_mounted_file(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            (runtime / "tak").mkdir()
            auth = runtime / "tak/UserAuthenticationFile.xml"
            auth.write_text('<UserAuthenticationFile xmlns="http://bbn.com/marti/xml/bindings">'
                            '<User identifier="admin" role="ROLE_ADMIN" fingerprint="AA"/>'
                            '</UserAuthenticationFile>')
            inode = auth.stat().st_ino
            completed = subprocess.CompletedProcess(["docker"], 0, b"", b"")
            with patch.object(host, "RUNTIME", runtime), \
                 patch.object(host, "command", return_value=completed) as command, \
                 patch.object(host, "require_tool", return_value="docker"), \
                 patch.object(host, "wait_for_cot_listener", return_value=True), \
                 patch.object(host.tak_api_client, "get_groups", return_value={
                     "username": "device-01", "groupList": ["shared"],
                     "groupListIN": ["publish"], "groupListOUT": ["observe"]}) as groups_api:
                host.register_authentication({"cn": "device-01", "fingerprint": "0a" * 32},
                                             ["shared", "publish"], ["shared", "observe"])
                self.assertEqual(auth.stat().st_ino, inode)
                tree = ElementTree.parse(auth)
                user = host.authentication_user(tree, "device-01")
                self.assertEqual(user.get("fingerprint"), ":".join(["0A"] * 32))
                self.assertEqual([child.tag.rsplit("}", 1)[-1] for child in user],
                                 ["groupList", "groupListIN", "groupListOUT"])
                self.assertEqual(command.call_args.args[0][1:], ["compose", "restart", "tak-server"])
                groups_api.return_value = {"username": "device-01", "groupList": ["shared"],
                                           "groupListIN": [], "groupListOUT": []}
                host.register_authentication({"cn": "device-01", "fingerprint": "0a" * 32},
                                             ["shared"], ["shared"])
                self.assertEqual(len(list(host.authentication_user(ElementTree.parse(auth), "device-01"))), 1)
                with self.assertRaisesRegex(RuntimeError, "another certificate"):
                    host.register_authentication({"cn": "device-01", "fingerprint": "0b" * 32},
                                                 ["shared"], ["shared"])

    def test_invalid_group_and_empty_permissions_are_rejected(self):
        for value in (["anonymous", "anonymous"], ["../../admin"], ["name with space"]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                host.checked_group_list(value)
        with self.assertRaises(ValueError):
            host.group_flags([], [])

    def test_group_change_fails_closed_when_current_tak_state_is_unknown(self):
        record = {"serial": "1002", "fingerprint": "a" * 64}
        with patch.object(host, "checked_record", return_value=record), \
             patch.object(host, "load_registry", return_value={}), \
             patch.object(host, "status", side_effect=RuntimeError("TAK unavailable")), \
             patch.object(host.tak_api_client, "update_groups") as update:
            with self.assertRaisesRegex(RuntimeError, "TAK unavailable"):
                host.set_groups("1002", "a" * 64, ["local-test"], ["local-test"])
            update.assert_not_called()

    def test_issue_builds_device_specific_dpk_with_temporary_ca(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / "runtime"
            private = runtime / "pki/private"
            public = runtime / "pki/public"
            ca_db = private / "ca-db"
            control = runtime / "tak-cert-control"
            packages = runtime / "packages/atak"
            tak_certs = runtime / "tak/certs"
            secrets_dir = runtime / "secrets"
            for path in (ca_db / "newcerts", public, control, packages, tak_certs, secrets_dir):
                path.mkdir(parents=True, exist_ok=True)
            now = datetime.now(timezone.utc)
            root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            root_name = x509.Name([x509.NameAttribute(NameOID.COUNTRY_NAME, "TW"),
                                   x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TAK Local"),
                                   x509.NameAttribute(NameOID.COMMON_NAME, "Test Root")])
            root_cert = (x509.CertificateBuilder().subject_name(root_name).issuer_name(root_name)
                         .public_key(root_key.public_key()).serial_number(1)
                         .not_valid_before(now - timedelta(days=1))
                         .not_valid_after(now + timedelta(days=3650))
                         .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
                         .add_extension(x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()),
                                        critical=False).sign(root_key, hashes.SHA256()))
            issuing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            issuing_name = x509.Name([x509.NameAttribute(NameOID.COUNTRY_NAME, "TW"),
                                      x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TAK Local"),
                                      x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Client"),
                                      x509.NameAttribute(NameOID.COMMON_NAME, "Test Issuing")])
            issuing_cert = (x509.CertificateBuilder().subject_name(issuing_name).issuer_name(root_name)
                            .public_key(issuing_key.public_key()).serial_number(2)
                            .not_valid_before(now - timedelta(days=1))
                            .not_valid_after(now + timedelta(days=3000))
                            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                                                          key_encipherment=False, data_encipherment=False,
                                                          key_agreement=False, key_cert_sign=True,
                                                          crl_sign=True, encipher_only=False, decipher_only=False),
                                           critical=True)
                            .add_extension(x509.SubjectKeyIdentifier.from_public_key(issuing_key.public_key()),
                                           critical=False).sign(root_key, hashes.SHA256()))
            root_pem = root_cert.public_bytes(serialization.Encoding.PEM)
            issuing_pem = issuing_cert.public_bytes(serialization.Encoding.PEM)
            (public / "root-ca.crt.pem").write_bytes(root_pem)
            (public / "intermediate.crt.pem").write_bytes(issuing_pem)
            (public / "ca-chain.pem").write_bytes(issuing_pem + root_pem)
            (private / "intermediate.key.pem").write_bytes(issuing_key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.BestAvailableEncryption(b"temporary-test-password")))
            (secrets_dir / "intermediate_ca_password").write_text("temporary-test-password\n")
            (ca_db / "index.txt").write_text("")
            (ca_db / "index.txt.attr").write_text("unique_subject = no\n")
            (ca_db / "serial").write_text("1000\n")
            (ca_db / "crlnumber").write_text("1000\n")
            (private / "issuing-ca.cnf").write_text(f"""[ca]
default_ca = issuing_ca
[issuing_ca]
dir = {ca_db.as_posix()}
database = $dir/index.txt
new_certs_dir = $dir/newcerts
certificate = {(public / 'intermediate.crt.pem').as_posix()}
private_key = {(private / 'intermediate.key.pem').as_posix()}
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
""")
            paths = {"PROJECT": root, "RUNTIME": runtime, "PRIVATE": private, "PUBLIC": public,
                     "CA_DB": ca_db, "CONTROL": control, "REGISTRY": control / "registry.json",
                     "AUDIT": control / "audit.jsonl", "PACKAGES": packages, "TAK_CERTS": tak_certs}
            (runtime / "tak/UserAuthenticationFile.xml").write_text(
                '<UserAuthenticationFile xmlns="http://bbn.com/marti/xml/bindings"/>')
            def status(record):
                return {"username": "tablet-01", "in_groups": ["local-test"],
                        "out_groups": ["local-test"], "fingerprint": record["fingerprint"]}

            with patch.multiple(host, **paths), patch.object(host, "check_server_running"), \
                 patch.object(host, "register_authentication"), \
                 patch.object(host, "status", side_effect=status):
                result = host.issue({"name": "Field Tablet 01", "cn": "tablet-01",
                                     "in_groups": ["local-test"], "out_groups": ["local-test"]})
                rows = host.inventory()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["serial"], result["serial"])
            self.assertEqual(rows[0]["name"], "Field Tablet 01")
            self.assertTrue(rows[0]["registered"])
            package = packages / result["package"]
            with zipfile.ZipFile(package) as archive:
                self.assertEqual(set(archive.namelist()), {"MANIFEST/manifest.xml",
                                                           "config/servers.pref", "cert/caCert.p12",
                                                           "cert/clientCert.p12"})
                prefs = ElementTree.fromstring(archive.read("config/servers.pref"))
                self.assertEqual(prefs.find(".//entry[@key='connectString0']").text,
                                 "takbox.local:8089:ssl")
                password = prefs.find(".//entry[@key='clientPassword0']").text
                key, issued, chain = pkcs12.load_key_and_certificates(
                    archive.read("cert/clientCert.p12"), password.encode())
                self.assertIsNotNone(key)
                self.assertEqual(format(issued.serial_number, "X"), result["serial"])
                self.assertGreaterEqual(len(chain), 1)

            real_command = host.command
            refreshes = []

            def local_revoke_command(args, **kwargs):
                if len(args) > 1 and str(args[1]).endswith("refresh_tak_crls.py"):
                    refreshes.append(args)
                    real_command([host.require_tool("openssl"), "ca", "-gencrl", "-config",
                                  str(private / "issuing-ca.cnf"), "-out",
                                  str(public / "intermediate-ca.crl.pem"), "-passin",
                                  "env:TAK_INTERMEDIATE_PASS"],
                                 env=host.secret_env(TAK_INTERMEDIATE_PASS="temporary-test-password"))
                    return subprocess.CompletedProcess(args, 0, b"", b"")
                if "restart" in args and "tak-server" in args:
                    return subprocess.CompletedProcess(args, 0, b"", b"")
                return real_command(args, **kwargs)

            with patch.multiple(host, **paths), patch.object(host, "check_server_running"), \
                 patch.object(host, "wait_for_cot_listener", return_value=False), \
                 patch.object(host, "command", side_effect=local_revoke_command):
                revoked = host.revoke([{"serial": result["serial"],
                                       "fingerprint": rows[0]["fingerprint"]}])
                self.assertTrue(host.inventory()[0]["revoked"])
            self.assertEqual(len(refreshes), 1)
            self.assertTrue(revoked["results"][0]["ca_revoked"])
            self.assertTrue(revoked["results"][0]["in_published_crl"])
            self.assertEqual(revoked["results"][0]["validation_8089"], "not-verified")
            self.assertFalse(package.exists())
            self.assertTrue((control / "retired-packages" / package.name).is_file())


if __name__ == "__main__":
    unittest.main()
