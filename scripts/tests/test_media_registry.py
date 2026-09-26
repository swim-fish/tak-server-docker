"""Check device reactivation without writing MediaMTX configuration."""

import copy
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import media_registry as media


class ReactivateDeviceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = {"version": 1, "publishers": {
            "device:test": {"kind": "device", "name": "Test drone", "user": "device-test",
                            "password": "old-secret", "enabled": False,
                            "paths": ["live/drone/test"]}}}

    def test_reuse_keeps_existing_password(self) -> None:
        with patch.object(media, "load", return_value=copy.deepcopy(self.registry)), patch.object(media, "apply") as apply:
            item = media.reactivate_device("device:test", False)
        self.assertTrue(item["enabled"])
        self.assertEqual(item["password"], "old-secret")
        self.assertEqual(apply.call_args.args[0]["publishers"]["device:test"]["password"], "old-secret")

    def test_rotate_changes_password(self) -> None:
        with patch.object(media, "load", return_value=copy.deepcopy(self.registry)), patch.object(media, "apply") as apply:
            item = media.reactivate_device("device:test", True)
        self.assertTrue(item["enabled"])
        self.assertNotEqual(item["password"], "old-secret")
        self.assertEqual(apply.call_args.args[0]["publishers"]["device:test"]["password"], item["password"])

    def test_path_collision_prevents_reactivation(self) -> None:
        self.registry["publishers"]["device:other"] = {
            **self.registry["publishers"]["device:test"], "enabled": True}
        with patch.object(media, "load", return_value=copy.deepcopy(self.registry)), patch.object(media, "apply") as apply:
            with self.assertRaisesRegex(ValueError, "assigned to another publisher"):
                media.reactivate_device("device:test", False)
        apply.assert_not_called()

    def test_enabled_device_cannot_reactivate(self) -> None:
        self.registry["publishers"]["device:test"]["enabled"] = True
        with patch.object(media, "load", return_value=copy.deepcopy(self.registry)), patch.object(media, "apply") as apply:
            with self.assertRaisesRegex(ValueError, "already enabled"):
                media.reactivate_device("device:test", True)
        apply.assert_not_called()

    def test_legacy_device_in_squad_namespace_cannot_reactivate(self) -> None:
        self.registry["publishers"]["device:test"]["paths"] = ["live/alpha/2"]
        with patch.object(media, "load", return_value=copy.deepcopy(self.registry)), patch.object(media, "apply") as apply:
            with self.assertRaisesRegex(ValueError, "reserved for an ICU squad"):
                media.reactivate_device("device:test", False)
        apply.assert_not_called()

    def test_squad_permission_accepts_only_its_own_subtree(self) -> None:
        item = {"kind": "squad", "paths": ["live/alpha/1/VIDEO_1"]}
        regex_path = next(path for path in media.permission_paths("squad:alpha", item)
                          if path.startswith("~"))
        pattern = re.compile(regex_path[1:])
        for path in ("live/alpha/2/VIDEO_1", "live/alpha/drone/camera-1/VIDEO_1"):
            self.assertIsNotNone(pattern.fullmatch(path))
        for path in ("live/bravo/2/VIDEO_1", "live/alpha/2/OTHER", "live/alphabeta/2/VIDEO_1"):
            self.assertIsNone(pattern.fullmatch(path))

    def test_squad_can_add_another_member_without_changing_account(self) -> None:
        self.registry["publishers"] = {"squad:alpha": {
            "kind": "squad", "name": "Alpha", "user": "icu-alpha", "password": "shared-secret",
            "enabled": True, "paths": ["live/alpha/1/VIDEO_1"]}}
        with patch.object(media, "load", return_value=copy.deepcopy(self.registry)), patch.object(media, "apply") as apply:
            item = media.ensure_squad("alpha", "live/alpha/2/VIDEO_1")
        self.assertEqual(item["user"], "icu-alpha")
        self.assertEqual(item["password"], "shared-secret")
        self.assertIn("live/alpha/2/VIDEO_1", item["paths"])
        apply.assert_called_once()

    def test_squad_stream_counts_follow_publishing_permissions(self) -> None:
        squad = {"kind": "squad", "paths": ["live/alpha/1/VIDEO_1"]}
        registry = {"publishers": {"squad:alpha": squad,
                                   "squad:bravo": {"kind": "squad", "paths": ["live/bravo/1/VIDEO_1"]},
                                   "device:drone": {"kind": "device", "paths": ["live/drone/camera"]}}}
        paths = [{"name": name, "ready": True} for name in (
            "live/alpha/1/VIDEO_1", "live/alpha/2/VIDEO_1", "live/bravo/1/VIDEO_1",
            "live/alpha/2/OTHER", "live/alphabeta/2/VIDEO_1", "live/drone/camera")]
        paths.append({"name": "live/alpha/3/VIDEO_1", "ready": False})
        self.assertEqual(media.squad_stream_counts(registry, paths),
                         {"squad:alpha": 2, "squad:bravo": 1})

    def test_other_publisher_cannot_claim_squad_namespace(self) -> None:
        with self.assertRaisesRegex(ValueError, "reserved for an ICU squad"):
            media.create_device("drone", "live/alpha/drone")
        with self.assertRaisesRegex(ValueError, "selected squad"):
            media.ensure_squad("alpha", "live/bravo/2/VIDEO_1")

    def test_public_viewer_sessions_exclude_publishers_and_private_query(self) -> None:
        response = {"itemCount": 3, "items": [
            {"id": "reader-1", "state": "read", "path": "live/alpha/1/VIDEO_1",
             "remoteAddr": "10.0.20.50:50000", "created": "2026-09-26T10:00:00Z",
             "peerConnectionEstablished": True, "outboundBytes": 2048,
             "query": "token=secret", "userAgent": "Browser"},
            {"id": "publisher-1", "state": "publish", "path": "live/test"}]}
        with patch.object(media, "api_request", return_value=response) as request:
            result = media.viewer_sessions()
        self.assertEqual(request.call_args.kwargs["base_url"], media.VIEWER_API_URL)
        self.assertEqual(result["shown"], 1)
        self.assertEqual(result["items"][0]["outbound_bytes"], 2048)
        self.assertNotIn("query", result["items"][0])


if __name__ == "__main__":
    unittest.main()
