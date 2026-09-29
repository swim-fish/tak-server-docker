"""Keep repackaged ATAK login DPKs distinct without rotating credentials."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rebuild_atak_data_package as rebuild


class RebuildAtakDataPackageTests(unittest.TestCase):
    def test_rebuild_changes_manifest_uid_and_keeps_client_certificate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packages = root / "packages"
            public = root / "public"
            secrets = root / "secrets"
            for path in (packages, public, secrets):
                path.mkdir()
            (packages / "clientCert.p12").write_bytes(b"same client identity")
            (public / "root-ca.crt.pem").write_bytes(b"root CA")
            (public / "intermediate.crt.pem").write_bytes(b"intermediate CA")
            (secrets / "tak_store_password").write_text("test-password\n", encoding="ascii")

            def fake_run(*command: str, env: dict[str, str]) -> None:
                Path(command[command.index("-keystore") + 1]).write_bytes(b"same CA store")

            snapshots = []
            with patch.multiple(rebuild, PACKAGES=packages, PUBLIC=public, SECRETS=secrets), \
                 patch.object(rebuild, "run", side_effect=fake_run), \
                 patch.object(rebuild, "write_identity"), \
                 patch.object(rebuild.shutil, "which", return_value="keytool"), \
                 patch.object(sys, "argv", ["rebuild_atak_data_package.py"]), \
                 contextlib.redirect_stdout(io.StringIO()):
                for _ in range(2):
                    self.assertEqual(rebuild.main(), 0)
                    package = packages / "atak-local-test.dpk"
                    snapshots.append(package.read_bytes())

            uids = []
            for data in snapshots:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    manifest = ElementTree.fromstring(archive.read("MANIFEST/manifest.xml"))
                    uid = manifest.find("./Configuration/Parameter[@name='uid']")
                    self.assertIsNotNone(uid)
                    uids.append(uid.get("value"))
                    self.assertEqual(archive.read("cert/clientCert.p12"), b"same client identity")
            self.assertNotEqual(uids[0], uids[1])
            self.assertNotEqual(snapshots[0], snapshots[1])


if __name__ == "__main__":
    unittest.main()
