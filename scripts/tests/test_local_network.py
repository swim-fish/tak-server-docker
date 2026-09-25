"""Checks for the host address shared by Compose and management scripts."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import local_network


class LocalNetworkTests(unittest.TestCase):
    def test_dotenv_and_environment_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "TAK_BIND_IP=192.0.2.27\nTAK_ALLOWED_SUBNET=192.0.2.0/24\n",
                encoding="utf-8",
            )
            with patch.object(local_network, "PROJECT", root), patch.dict(
                os.environ, {"TAK_BIND_IP": "", "TAK_ALLOWED_SUBNET": ""}
            ):
                self.assertEqual(local_network.bind_ip(), "192.0.2.27")
                self.assertEqual(local_network.allowed_subnet(), "192.0.2.0/24")
            with patch.object(local_network, "PROJECT", root), patch.dict(
                os.environ, {"TAK_BIND_IP": "203.0.113.5", "TAK_ALLOWED_SUBNET": "203.0.113.0/24"}
            ):
                self.assertEqual(local_network.bind_ip(), "203.0.113.5")
                self.assertEqual(local_network.allowed_subnet(), "203.0.113.0/24")

    def test_rejects_subnet_without_bind_address(self) -> None:
        with patch.dict(os.environ, {"TAK_BIND_IP": "192.0.2.27", "TAK_ALLOWED_SUBNET": "198.51.100.0/24"}):
            with self.assertRaisesRegex(ValueError, "inside"):
                local_network.allowed_subnet()


if __name__ == "__main__":
    unittest.main()
