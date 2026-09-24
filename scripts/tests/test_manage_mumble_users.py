"""Destructive-path guards tested without modifying a running server."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import manage_mumble_users as manager


def row(uid, fingerprint="original"):
    return {"id": uid, "name": f"Test User {uid}", "fingerprint": fingerprint}


class RemovalTests(unittest.TestCase):
    def setUp(self):
        self.current = {1: row(1), 2: row(2)}
        self.endpoint = {"container": "test-container", "host": "127.0.0.1", "port": 12345}
        self.snapshot = {"endpoint": self.endpoint, "users": list(self.current.values())}
        self.admin = Mock()
        self.admin.users = {12: {1: [12], 4: [2], 15: [b"test-hash"]}}
        self.admin.registered.return_value = {1: "Test User 1"}
        self.admin.disconnect.return_value = [12]
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.backup = Path(self.temp.name) / "backup.sqlite"

    def test_selection_rejects_empty_superuser_duplicates_and_stale_identity(self):
        for ids in ([], [0], [-1], [2, 2], [3]):
            with self.subTest(ids=ids), self.assertRaises((ValueError, RuntimeError)):
                manager.validate_selection(self.snapshot, self.current, ids)
        for changed in ({1: row(1)}, {1: row(1), 2: row(2, "replaced")}):
            with self.assertRaises(RuntimeError):
                manager.validate_selection(self.snapshot, changed, [2])

    def test_docker_queries_do_not_open_a_console_window(self):
        with patch.object(manager.subprocess, "run", return_value=Mock(returncode=0, stdout=b"ok")) as launch:
            self.assertEqual(manager.run("docker", "compose", "ps"), "ok")
        self.assertEqual(launch.call_args.kwargs["creationflags"],
                         getattr(manager.subprocess, "CREATE_NO_WINDOW", 0))

    def test_success_sends_only_selected_id_and_disconnects_only_selected_session(self):
        with patch.object(manager, "checked_users", side_effect=[self.current, self.current, {1: row(1)}]), \
             patch.object(manager, "backup_database", return_value=self.backup):
            result = manager.apply_selection(self.snapshot, self.endpoint, self.admin, [2])
        kind, payload = self.admin.send.call_args.args
        self.assertEqual(kind, 18)
        entries = manager.protocol.parse_protobuf(payload)[1]
        self.assertEqual([manager.protocol.parse_protobuf(v) for v in entries], [{1: [2]}])
        self.admin.disconnect.assert_called_once_with(self.admin.users)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["remaining_ids"], [1])

    def test_backup_failure_never_sends_removal(self):
        with patch.object(manager, "checked_users", return_value=self.current), \
             patch.object(manager, "backup_database", side_effect=RuntimeError("backup failed")):
            with self.assertRaises(RuntimeError):
                manager.apply_selection(self.snapshot, self.endpoint, self.admin, [2])
        self.admin.send.assert_not_called()

    def test_identity_change_during_backup_never_sends_removal(self):
        with patch.object(manager, "checked_users", side_effect=[self.current, {1: row(1), 2: row(2, "changed")}]), \
             patch.object(manager, "backup_database", return_value=self.backup):
            with self.assertRaises(RuntimeError):
                manager.apply_selection(self.snapshot, self.endpoint, self.admin, [2])
        self.admin.send.assert_not_called()

    def test_changed_container_never_touches_database(self):
        with patch.object(manager, "checked_users") as checked:
            with self.assertRaises(RuntimeError):
                manager.apply_selection(self.snapshot, {"container": "other"}, self.admin, [2])
        checked.assert_not_called()

    def test_partial_failure_is_recorded_and_does_not_kick(self):
        self.admin.registered.return_value = {1: "Test User 1", 2: "Test User 2"}
        with patch.object(manager, "checked_users", return_value=self.current), \
             patch.object(manager, "backup_database", return_value=self.backup):
            with self.assertRaises(RuntimeError):
                manager.apply_selection(self.snapshot, self.endpoint, self.admin, [2])
        journal = json.loads(self.backup.with_suffix(".operation.json").read_text())
        self.assertEqual(journal["status"], "incomplete-check-server-before-retry")
        self.admin.disconnect.assert_not_called()

    def test_fingerprint_detects_changed_certificate_without_exposing_secrets(self):
        account = [{"user_id": 1, "name": "Test", "pw": "private-password-hash"}]
        first = manager.fingerprints(account, [{"user_id": 1, "key": 3, "value": "cert-one"}])
        second = manager.fingerprints(account, [{"user_id": 1, "key": 3, "value": "cert-two"}])
        self.assertNotEqual(first[1]["fingerprint"], second[1]["fingerprint"])
        self.assertNotIn("private-password-hash", json.dumps(first))
        self.assertNotIn("cert-one", json.dumps(first))

    def test_disconnect_refuses_reused_session(self):
        admin = manager.Admin(self.endpoint, "example.test")
        admin.users = {12: {3: [b"Other"], 15: [b"other-hash"]}}
        admin.send = Mock()
        with self.assertRaises(RuntimeError):
            admin.disconnect({12: {3: [b"Original"], 15: [b"original-hash"]}})
        admin.send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
