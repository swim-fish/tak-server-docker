"""Verify managed Video V2 alias replacement without a live TAK Server."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tak_video_alias_host as host


class FakeVideoAPI:
    def __init__(self):
        self.rows = []
        self.calls = []
        self.fail_group = None

    def request(self, method, uid=None, *, groups=None, payload=None):
        self.calls.append((method, uid, groups))
        if method == "GET":
            return {"videoConnections": [copy.deepcopy(row) for row, _ in self.rows]}
        if method == "DELETE":
            self.rows = [(row, owned) for row, owned in self.rows if row["uuid"] != uid]
            return None
        if self.fail_group and self.fail_group in groups:
            raise RuntimeError("Injected TAK POST failure")
        for incoming in payload["videoConnections"]:
            self.rows = [(row, owned) for row, owned in self.rows
                         if row["uuid"] != incoming["uuid"] or owned != tuple(groups)]
            self.rows.append((copy.deepcopy(incoming), tuple(groups)))
        return None


class VideoAliasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        password = root / "viewer-password"
        password.write_text("private-test-viewer-secret", encoding="ascii")
        self.fake = FakeVideoAPI()
        self.patches = [patch.object(host, "CONTROL", root),
                        patch.object(host, "REGISTRY", root / "aliases.json"),
                        patch.object(host, "READ_PASSWORD", password),
                        patch.object(host.tak_api_client, "video_request", self.fake.request)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_same_groups_update_and_changed_groups_replace(self):
        first = host.publish_batch("alpha", [1], ["team-alpha"])
        self.assertEqual(first["state"], "complete")
        self.assertEqual(len(self.fake.rows), 1)
        self.assertEqual(host.publish_batch("alpha", [1], ["team-alpha"])["state"], "complete")
        self.assertEqual(len(self.fake.rows), 1)
        changed = host.publish_batch("alpha", [1], ["team-all", "team-bravo"])
        self.assertEqual(changed["state"], "complete")
        self.assertEqual(len(self.fake.rows), 1)
        self.assertEqual(self.fake.rows[0][1], ("team-all", "team-bravo"))
        self.assertIn(("DELETE", host.alias_uid("alpha", 1), None), self.fake.calls)
        self.assertNotIn("private-test-viewer-secret", host.REGISTRY.read_text(encoding="utf-8"))

    def test_failed_group_change_restores_previous_alias(self):
        host.publish_batch("alpha", [1], ["team-alpha"])
        self.fake.fail_group = "team-bravo"
        result = host.publish_batch("alpha", [1], ["team-bravo"])
        self.assertEqual(result["state"], "partial")
        self.assertEqual(len(self.fake.rows), 1)
        self.assertEqual(self.fake.rows[0][1], ("team-alpha",))
        self.assertEqual(json.loads(host.REGISTRY.read_text())["aliases"][host.alias_uid("alpha", 1)]["groups"],
                         ["team-alpha"])

    def test_unmanaged_existing_uid_is_preserved(self):
        self.fake.rows.append((host.payload("alpha", 1)["videoConnections"][0], ("team-alpha",)))
        result = host.publish_batch("alpha", [1], ["team-all"])
        self.assertEqual(result["state"], "partial")
        self.assertEqual(len(self.fake.rows), 1)
        self.assertFalse(any(method == "DELETE" for method, _, _ in self.fake.calls))


if __name__ == "__main__":
    unittest.main()
