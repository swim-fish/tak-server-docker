"""Safety checks for the service-only SAN renewal workflow."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import renew_service_san as renewal  # noqa: E402


class ServiceSanRenewalTests(unittest.TestCase):
    def test_apply_requires_all_three_services_stopped(self) -> None:
        rows = [{"Service": name, "State": "exited"}
                for name in ("tak-server", "mumble", "mediamtx")]
        for output in ("\n".join(json.dumps(row) for row in rows), json.dumps(rows)):
            with self.subTest(output=output[:1]), \
                    patch.object(renewal, "tool", return_value="docker"), \
                    patch.object(renewal, "command", return_value=output):
                renewal.require_services_stopped()

    def test_apply_rejects_running_or_missing_service(self) -> None:
        for rows in (
            [{"Service": "tak-server", "State": "running"},
             {"Service": "mumble", "State": "exited"},
             {"Service": "mediamtx", "State": "exited"}],
            [{"Service": "tak-server", "State": "exited"},
             {"Service": "mumble", "State": "exited"}],
        ):
            with self.subTest(rows=rows), \
                    patch.object(renewal, "tool", return_value="docker"), \
                    patch.object(renewal, "command", return_value=json.dumps(rows)):
                with self.assertRaisesRegex(RuntimeError, "Stop "):
                    renewal.require_services_stopped()


if __name__ == "__main__":
    unittest.main()
