"""Squad mapping validation and console route tests."""

import base64
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import squad_groups


class SquadGroupsTests(unittest.TestCase):
    def test_defaults_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
                squad_groups, "MAPPING_FILE", Path(directory) / "mapping.json"):
            mapping = squad_groups.load()
            self.assertEqual(mapping["alpha"], "team-alpha")
            self.assertIn("team-all", squad_groups.catalog([]))
            mapping["alpha"] = "team-field-a"
            squad_groups.save(mapping)
            self.assertEqual(squad_groups.load()["alpha"], "team-field-a")

    def test_rejects_duplicate_and_reserved_groups(self):
        mapping = squad_groups.defaults()
        mapping["alpha"] = "team-bravo"
        with self.assertRaises(ValueError):
            squad_groups.validate(mapping)
        mapping["alpha"] = "team-all"
        with self.assertRaises(ValueError):
            squad_groups.validate(mapping)

    def test_settings_route_requires_auth_and_csrf(self):
        import share_admin_flask as admin

        with tempfile.TemporaryDirectory() as directory, patch.object(
                squad_groups, "MAPPING_FILE", Path(directory) / "mapping.json"):
            client = admin.app.test_client()
            self.assertEqual(client.get("/settings/groups").status_code, 401)
            auth = "Basic " + base64.b64encode(
                b"admin:test-admin-password-that-is-long-enough").decode()
            headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
            page = client.get("/settings/groups", headers=headers)
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"team-all", page.data)
            mapping = squad_groups.defaults()
            mapping["alpha"] = "team-field-a"
            self.assertEqual(client.post("/settings/groups", headers=headers, data=mapping).status_code, 403)
            mapping["csrf"] = admin.CSRF
            self.assertEqual(client.post("/settings/groups", headers=headers, data=mapping).status_code, 303)
            self.assertEqual(squad_groups.load()["alpha"], "team-field-a")


if __name__ == "__main__":
    unittest.main()
