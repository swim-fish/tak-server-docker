"""Read-only checks for CA replacement selection and expiry changes."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ca_rotation_console as rotation


class CaRotationSelectionTests(unittest.TestCase):
    def test_selection_preserves_identity_and_allows_expiry_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cert = Path(directory) / "client.pem"
            cert.write_bytes(b"test certificate")
            now = datetime.now(timezone.utc)
            old_expiry = now + timedelta(days=14)
            requested = (now + timedelta(days=90)).astimezone(
                timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M")
            record = {"serial": "1002", "fingerprint": "a" * 64, "issuer_ca_id": "B" * 64,
                      "registered": True, "cn": "tablet-a", "name": "Alpha tablet",
                      "in_groups": ["team-alpha"], "out_groups": ["team-alpha"]}
            with patch.object(rotation.host, "checked_record", return_value=record), \
                    patch.object(rotation.host, "certificate_path", return_value=cert), \
                    patch.object(rotation, "ca_id", return_value="B" * 64), \
                    patch.object(rotation.x509, "load_pem_x509_certificate",
                                 return_value=SimpleNamespace(not_valid_after_utc=old_expiry)):
                result = rotation.prepare_selection([{"serial": "1002", "fingerprint": "a" * 64,
                                                       "expires_at": requested}])
            self.assertEqual(result, [{"old_serial": "1002", "cn": "tablet-a", "name": "Alpha tablet",
                                       "in_groups": ["team-alpha"], "out_groups": ["team-alpha"],
                                       "expires_at": requested}])

    def test_duplicate_selection_and_invalid_expiry_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "100"):
            rotation.prepare_selection([{}] * 101)
        with patch.object(rotation.host, "checked_record", return_value={"serial": "1002", "registered": True}):
            with self.assertRaisesRegex(ValueError, "expiry"):
                rotation.prepare_selection([{"serial": "1002", "fingerprint": "a" * 64,
                                             "expires_at": "not-a-date"}])


if __name__ == "__main__":
    unittest.main()
