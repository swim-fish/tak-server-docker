"""Pure-logic checks for the LDAP rollout helper: group mapping, user selection, CoreConfig edits."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import manage_tak_ldap as ldap  # noqa: E402

AUTH = b"""<?xml version="1.0"?>
<UserAuthenticationFile xmlns="http://bbn.com/marti/xml/bindings">
  <User identifier="alice" fingerprint="x"><groupList>alpha</groupList>
    <groupListOUT>all</groupListOUT><groupListIN>cp</groupListIN></User>
  <User identifier="bob" fingerprint="x"><groupList>alpha</groupList></User>
  <User identifier="admin" fingerprint="x" role="ROLE_ADMIN"/>
  <User identifier="anon" fingerprint="x"><groupList>__ANON__</groupList></User>
  <User identifier="bad name" fingerprint="x"><groupList>alpha</groupList></User>
</UserAuthenticationFile>"""

CORE = b"""<?xml version="1.0"?>
<Configuration xmlns="http://bbn.com/marti/xml/config">
  <network><input _name="stdssl" protocol="tls" port="8089"/></network>
  <auth x509checkRevocation="true"><File location="UserAuthenticationFile.xml"/></auth>
  <repository enable="true"/>
</Configuration>"""


class LdapHelperTests(unittest.TestCase):
    def test_file_groups_map_to_prefixed_directional_groups(self) -> None:
        users = ldap.file_users(AUTH)
        self.assertEqual(users["alice"], ["tak_all_READ", "tak_alpha", "tak_cp_WRITE"])
        self.assertEqual(users["admin"], [])
        self.assertEqual(users["anon"], [])

    def test_plan_skips_groupless_unsafe_and_invalid_users(self) -> None:
        groups, skipped = ldap.directory_plan(ldap.file_users(AUTH), {"alice", "bad name"})
        self.assertEqual(groups, {"tak_all_READ": ["alice"], "tak_alpha": ["alice"],
                                  "tak_cp_WRITE": ["alice"]})
        self.assertEqual(sorted(skipped), ["admin", "anon", "bad name", "bob"])
        groups, _ = ldap.directory_plan(ldap.file_users(AUTH), None)
        self.assertEqual(groups["tak_alpha"], ["alice", "bob"])

    def test_valid_common_names_ignore_revoked_and_expired(self) -> None:
        index = ("V\t991231000000Z\t\t01\tunknown\t/C=TW/O=T/CN=live\n"
                 "R\t991231000000Z\t260101000000Z\t02\tunknown\t/C=TW/O=T/CN=revoked\n"
                 "V\t200101000000Z\t\t03\tunknown\t/C=TW/O=T/CN=expired\n")
        now = datetime(2026, 11, 15, tzinfo=timezone.utc)
        self.assertEqual(ldap.valid_common_names(index, now), {"live"})

    def test_group_ldif_adds_or_replaces_members(self) -> None:
        self.assertIn("changetype: add\nobjectClass: groupOfNames",
                      ldap.group_ldif("tak_a", ["u1"], False))
        self.assertIn("changetype: modify\nreplace: member\nmember: uid=u1,ou=People,",
                      ldap.group_ldif("tak_a", ["u1"], True))

    def test_enable_then_disable_restores_file_mode(self) -> None:
        enabled = ldap.set_auth(CORE, ldap.ldap_attributes("store", "bind", 60))
        self.assertEqual(ldap.auth_mode(enabled), "ldap")
        auth = ElementTree.fromstring(enabled).find(f"{{{ldap.CONFIG_NS}}}auth")
        self.assertEqual(auth.get("x509groups"), "true")
        self.assertEqual(auth.get("x509checkRevocation"), "true")
        element = auth.find(f"{{{ldap.CONFIG_NS}}}ldap")
        self.assertEqual(element.get("url"), "ldaps://tak-ldap:636/")
        self.assertEqual(element.get("updateinterval"), "60")
        self.assertIsNotNone(auth.find(f"{{{ldap.CONFIG_NS}}}File"))
        # Enabling twice must not duplicate the element.
        again = ldap.set_auth(enabled, ldap.ldap_attributes("store", "bind", 30))
        self.assertEqual(again.count(b"<ldap "), 1)
        disabled = ldap.set_auth(again, None)
        self.assertEqual(ldap.auth_mode(disabled), "file")
        auth = ElementTree.fromstring(disabled).find(f"{{{ldap.CONFIG_NS}}}auth")
        self.assertEqual(auth.attrib, {"x509checkRevocation": "true"})
        self.assertNotIn(b"bind", disabled)

    def test_set_auth_rejects_config_without_file_backend(self) -> None:
        broken = CORE.replace(b'<File location="UserAuthenticationFile.xml"/>', b"")
        with self.assertRaisesRegex(RuntimeError, "File"):
            ldap.set_auth(broken, None)


if __name__ == "__main__":
    unittest.main()
