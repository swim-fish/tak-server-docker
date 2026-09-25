"""Ensure network refresh leaves viewer authentication settings intact."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from update_viewer_network import update


class ViewerNetworkTests(unittest.TestCase):
    def test_changes_only_ice_host_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "viewer-public.yml"
            config.write_text(
                "authInternalUsers:\n  - user: tak-console\n    pass: keep-this-value\n"
                "webrtcAdditionalHosts: [takbox.local, 192.168.137.1]\npaths: {}\n",
                encoding="utf-8",
            )
            self.assertTrue(update(config, "10.0.20.27"))
            self.assertFalse(update(config, "10.0.20.27"))
            result = config.read_text(encoding="utf-8")
            self.assertIn("pass: keep-this-value", result)
            self.assertIn("webrtcAdditionalHosts: [takbox.local, 10.0.20.27]", result)


if __name__ == "__main__":
    unittest.main()
