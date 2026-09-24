"""Safety checks for the host-side Mumble management worker."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mumble_control_host as worker


class MumbleControlHostTests(unittest.TestCase):
    def test_recreate_does_not_open_a_console_window(self) -> None:
        with patch.object(worker.subprocess, "run", return_value=Mock(returncode=0)) as launch:
            worker.recreate_mumble()
        self.assertEqual(launch.call_args.kwargs["creationflags"],
                         getattr(worker.subprocess, "CREATE_NO_WINDOW", 0))

    def test_selection_rejects_stale_or_duplicate_identity(self) -> None:
        current = {3: {"id": 3, "fingerprint": "a" * 64}}
        self.assertEqual(worker.checked_selection([{"id": 3, "fingerprint": "a" * 64}], current), [3])
        with self.assertRaises(RuntimeError):
            worker.checked_selection([{"id": 3, "fingerprint": "b" * 64}], current)
        with self.assertRaises(ValueError):
            worker.checked_selection([{"id": 3, "fingerprint": "a" * 64}] * 2, current)

    def test_password_reset_backs_up_and_does_not_return_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret = root / "mumble_server_password"
            secret.write_text("old-secret\n", encoding="utf-8")
            with patch.object(worker, "CONTROL", root), patch.object(worker, "PASSWORD", secret), \
                 patch.object(worker, "recreate_mumble") as recreate:
                result = worker.reset_password()
            recreate.assert_called_once()
            self.assertNotEqual(secret.read_text(encoding="utf-8"), "old-secret\n")
            self.assertEqual((root / "backups" / result["backup"]).read_text(encoding="utf-8"),
                             "old-secret\n")
            self.assertNotIn("old-secret", str(result))
            self.assertNotIn(secret.read_text(encoding="utf-8").strip(), str(result))

    def test_failed_recreate_restores_previous_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret = root / "mumble_server_password"
            secret.write_text("old-secret\n", encoding="utf-8")
            with patch.object(worker, "CONTROL", root), patch.object(worker, "PASSWORD", secret), \
                 patch.object(worker, "recreate_mumble", side_effect=RuntimeError("Docker unavailable")):
                with self.assertRaises(RuntimeError):
                    worker.reset_password()
            self.assertEqual(secret.read_text(encoding="utf-8"), "old-secret\n")


if __name__ == "__main__":
    unittest.main()
