"""Verify CA replacement job persistence without changing live certificates."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ca_rotation_console as rotation
import tak_certificate_host as host


class CaRotationJobTests(unittest.TestCase):
    def test_background_job_finishes_and_records_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)
            with patch.object(host, "CONTROL", control), \
                    patch.object(host, "ROTATION_JOB", control / "ca-rotation-job.json"), \
                    patch.object(host, "ROTATION_THREAD", None), \
                    patch.object(rotation, "active_ca_summary", return_value={"id": "B" * 64}), \
                    patch.object(rotation, "prepare_selection", return_value=[]), \
                    patch.object(rotation, "rotate", return_value={"new_ca_id": "C" * 64}), \
                    patch.object(host, "check_server_running"):
                result = host.execute({"action": "ca_rotate_start", "expected_ca_id": "B" * 64,
                                       "selected": []})
                self.assertEqual(result["job"]["old_ca_id"], "B" * 64)
                host.ROTATION_THREAD.join(timeout=2)
                self.assertFalse(host.ROTATION_THREAD.is_alive())
                finished = host.execute({"action": "ca_rotate_status"})["job"]
                self.assertEqual(finished["state"], "complete")
                self.assertEqual(finished["result"]["new_ca_id"], "C" * 64)

    def test_failed_job_cannot_be_restarted_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)
            with patch.object(host, "CONTROL", control), \
                    patch.object(host, "ROTATION_JOB", control / "ca-rotation-job.json"), \
                    patch.object(host, "ROTATION_THREAD", None), \
                    patch.object(rotation, "active_ca_summary", return_value={"id": "B" * 64}), \
                    patch.object(rotation, "prepare_selection", return_value=[]), \
                    patch.object(rotation, "rotate", side_effect=RuntimeError("staged failure")), \
                    patch.object(host, "check_server_running"):
                host.execute({"action": "ca_rotate_start", "expected_ca_id": "B" * 64,
                              "selected": []})
                host.ROTATION_THREAD.join(timeout=2)
                self.assertEqual(host.rotation_status()["state"], "failed")
                with self.assertRaisesRegex(RuntimeError, "previous CA replacement"):
                    host.execute({"action": "ca_rotate_start", "expected_ca_id": "B" * 64,
                                  "selected": []})


if __name__ == "__main__":
    unittest.main()
