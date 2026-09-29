"""Exercise channel provisioner connection and trust-source options."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import local_network
import provision_mumble_channel as provision


def channel_state(name: str, channel_id: int) -> tuple[int, bytes]:
    return (
        provision.MESSAGE_CHANNEL_STATE,
        provision.protobuf_varint(1, channel_id)
        + provision.protobuf_string(3, name),
    )


class ProvisionMumbleChannelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.default_ca = root / "default-ca.pem"
        self.custom_ca = root / "custom-ca.pem"
        self.default_password = root / "default-password"
        self.custom_password = root / "custom-password"
        for ca in (self.default_ca, self.custom_ca):
            ca.write_text("test CA", encoding="utf-8")
        self.default_password.write_text("default-secret\n", encoding="utf-8")
        self.custom_password.write_text("custom-secret\n", encoding="utf-8")

    def run_provisioner(self, arguments: list[str]) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
        connection = MagicMock()
        wrapped = MagicMock()
        wrapped.__enter__.return_value = connection
        context = MagicMock()
        context.wrap_socket.return_value = wrapped
        raw = MagicMock()
        raw.__enter__.return_value = raw
        with patch.object(sys, "argv", ["provision_mumble_channel.py", *arguments]), \
             patch.object(provision, "ROOT_CA", self.default_ca), \
             patch.object(provision, "SUPERUSER_PASSWORD", self.default_password), \
             patch.object(provision.ssl, "create_default_context", return_value=context) as create_context, \
             patch.object(provision.socket, "create_connection", return_value=raw) as create_connection, \
             patch.object(provision, "read_message", side_effect=[
                 channel_state("Primary", 2),
                 channel_state("Alternate", 3),
                 (provision.MESSAGE_SERVER_SYNC, b""),
             ]), \
             patch.object(provision, "send_message") as send_message:
            self.assertEqual(provision.main(), 0)
        self.assertEqual(send_message.call_count, 2)
        return create_context, create_connection, context, send_message

    def test_defaults_use_bind_ip_project_ca_and_password(self) -> None:
        with patch.object(local_network, "bind_ip", return_value="192.168.88.2") as bind_ip:
            create_context, create_connection, context, send_message = self.run_provisioner([])
        bind_ip.assert_called_once_with()
        create_context.assert_called_once_with(cafile=str(self.default_ca))
        create_connection.assert_called_once_with(("192.168.88.2", 40000), timeout=5)
        self.assertEqual(context.wrap_socket.call_args.kwargs["server_hostname"], "takbox.local")
        self.assertIn(provision.protobuf_string(2, "default-secret"), send_message.call_args_list[1].args[2])

    def test_explicit_host_and_custom_files_do_not_read_bind_ip(self) -> None:
        with patch.object(local_network, "bind_ip", side_effect=AssertionError("unexpected .env lookup")):
            create_context, create_connection, context, send_message = self.run_provisioner([
                "--connect-host", "192.168.88.2",
                "--server-name", "192.168.88.2",
                "--port", "40001",
                "--root-ca", str(self.custom_ca),
                "--password-file", str(self.custom_password),
            ])
        create_context.assert_called_once_with(cafile=str(self.custom_ca))
        create_connection.assert_called_once_with(("192.168.88.2", 40001), timeout=5)
        self.assertEqual(context.wrap_socket.call_args.kwargs["server_hostname"], "192.168.88.2")
        self.assertIn(provision.protobuf_string(2, "custom-secret"), send_message.call_args_list[1].args[2])

    def test_system_ca_does_not_require_local_ca_file(self) -> None:
        missing_ca = Path(self.directory.name) / "missing-ca.pem"
        with patch.object(local_network, "bind_ip", side_effect=AssertionError("unexpected .env lookup")):
            create_context, _, _, _ = self.run_provisioner([
                "--connect-host", "192.168.88.2",
                "--root-ca", str(missing_ca),
                "--system-ca",
            ])
        create_context.assert_called_once_with(cafile=None)

    def test_custom_ca_must_exist_without_system_ca(self) -> None:
        missing_ca = Path(self.directory.name) / "missing-ca.pem"
        with patch.object(sys, "argv", [
                 "provision_mumble_channel.py", "--connect-host", "192.168.88.2",
                 "--root-ca", str(missing_ca),
             ]), \
             patch.object(provision, "SUPERUSER_PASSWORD", self.default_password), \
             patch.object(provision.socket, "create_connection") as connect:
            with self.assertRaisesRegex(SystemExit, "Missing Mumble CA"):
                provision.main()
        connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
