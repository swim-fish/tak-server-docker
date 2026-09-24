"""Checks for fixed-name Vx replacement and recovery boundaries."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tak_vx_package_host as vx


class VxPackageTests(unittest.TestCase):
    def test_metadata_uses_raw_tool_and_json_keyword_array(self) -> None:
        calls = []
        with patch.object(vx.tak_api_client, "package_request", side_effect=lambda *args: calls.append(args)):
            vx.set_public_metadata("a" * 64)
        self.assertEqual(calls[0][2], b"public")
        self.assertEqual(calls[1][2], b'["missionpackage"]')

    def test_failed_upload_restores_sha_verified_backup(self) -> None:
        with tempfile.TemporaryDirectory() as location, patch.object(vx, "JOBS", Path(location)):
            job_id = "a" * 32
            directory = vx.job_dir(job_id)
            directory.mkdir()
            old_bytes, new_bytes = b"old Vx package", b"new Vx package"
            old_hash = hashlib.sha256(old_bytes).hexdigest()
            new_hash = hashlib.sha256(new_bytes).hexdigest()
            (directory / "atak-local-vx.dpk").write_bytes(new_bytes)
            old = {"Name": vx.DISPLAY_NAME, "Hash": old_hash, "Tool": "public",
                   "Keywords": ["missionpackage"]}
            vx.save_job(job_id, {"job_id": job_id, "state": "prepared", "sha256": new_hash,
                                 "old": [old], "deleted": [], "uploaded": False})
            server = [old.copy()]

            def package_request(method, path, body=None, content_type=None):
                if method == "GET":
                    return old_bytes
                if method == "DELETE":
                    server.clear()
                    return b""
                if method == "PUT":
                    return b""
                raise AssertionError((method, path))

            def upload(path, filename="atak-local-vx.dpk"):
                if path.name == "atak-local-vx.dpk":
                    raise RuntimeError("simulated upload failure")
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), old_hash)
                server.append(old.copy())
                return old_hash

            with patch.object(vx, "exact_packages", side_effect=lambda: server.copy()), \
                    patch.object(vx.tak_api_client, "package_request", side_effect=package_request), \
                    patch.object(vx, "upload", side_effect=upload):
                with self.assertRaisesRegex(RuntimeError, "simulated upload failure"):
                    vx.replace(job_id)
                self.assertEqual(vx.read_job(job_id)["state"], "needs-recovery")
                self.assertEqual((directory / (old_hash + ".dpk")).read_bytes(), old_bytes)
                self.assertEqual(vx.restore(job_id)["state"], "restored")
                self.assertEqual(server[0]["Hash"], old_hash)


if __name__ == "__main__":
    unittest.main()
