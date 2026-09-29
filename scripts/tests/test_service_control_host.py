"""Check allowlisted service control and Docker Compose status parsing."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import service_control_host as host


class ServiceControlHostTests(unittest.TestCase):
    def test_parse_ps_accepts_lines_and_array(self) -> None:
        rows = [{"Service": "mediamtx", "State": "running", "Health": ""},
                {"Service": "tak-db", "State": "running", "Health": "healthy"}]
        for output in ("\n".join(json.dumps(row) for row in rows), json.dumps(rows)):
            with self.subTest(output=output[0]):
                result = host.parse_ps(output)
                self.assertEqual(result["mediamtx"], {"state": "running", "health": "none"})
                self.assertEqual(result["tak-db"]["health"], "healthy")
                self.assertEqual(result["share-public"]["state"], "absent")

    def test_rejects_core_and_unknown_control_without_running_docker(self) -> None:
        with patch.object(host, "compose") as compose:
            for service in ("tak-db", "tak-server", "share-admin", "unknown"):
                with self.subTest(service=service), self.assertRaises(ValueError):
                    host.execute({"action": "control", "service": service, "verb": "stop"})
            with self.assertRaises(ValueError):
                host.execute({"action": "control", "service": "mediamtx", "verb": "down"})
            compose.assert_not_called()

    def test_cannot_start_an_absent_service(self) -> None:
        with patch.object(host, "snapshot", return_value={"services": host.parse_ps("")}), \
                patch.object(host, "compose") as compose:
            with self.assertRaisesRegex(RuntimeError, "not been deployed"):
                host.execute({"action": "control", "service": "mediamtx", "verb": "start"})
            compose.assert_not_called()

    def test_restart_confirms_state_and_records_action(self) -> None:
        before = {"services": {"mediamtx": {"state": "running", "health": "none"}}}
        after = {"services": {"mediamtx": {"state": "running", "health": "none"}}}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(host, "CONTROL", Path(directory)), \
                patch.object(host, "snapshot", side_effect=[before, after]), \
                patch.object(host, "compose", return_value="") as compose:
            result = host.execute({"action": "control", "service": "mediamtx", "verb": "restart"})
            compose.assert_called_once_with("restart", "mediamtx", timeout=120)
            self.assertEqual(result["operation"]["state"], "running")
            journal = (Path(directory) / "actions.jsonl").read_text(encoding="utf-8")
            self.assertEqual(json.loads(journal)["service"], "mediamtx")


if __name__ == "__main__":
    unittest.main()
