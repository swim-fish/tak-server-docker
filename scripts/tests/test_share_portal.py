"""Acceptance checks for share quotas, expiry, and public download routes."""

from __future__ import annotations

import base64
import sys
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import share_portal as portal


class SharePortalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.originals = {name: getattr(portal, name) for name in
                          ("STATE_DIR", "FILE_DIR", "DB_PATH", "PACKAGE_DIR", "ICU_DIR",
                           "PUBLISH_PASSWORD_FILE", "ADMIN_PASSWORD_FILE")}
        self.addCleanup(self.restore)
        portal.STATE_DIR = self.root / "state"
        portal.FILE_DIR = self.root / "files"
        portal.DB_PATH = portal.STATE_DIR / "shares.sqlite3"
        portal.PACKAGE_DIR = self.root / "packages"
        portal.ICU_DIR = self.root / "icu"
        portal.PUBLISH_PASSWORD_FILE = self.root / "publish-password"
        portal.ADMIN_PASSWORD_FILE = self.root / "admin-password"
        portal.PACKAGE_DIR.mkdir()
        portal.ICU_DIR.mkdir()
        with zipfile.ZipFile(portal.PACKAGE_DIR / "example.dpk", "w") as package:
            package.writestr("example.txt", "example-package")
        portal.PUBLISH_PASSWORD_FILE.write_text("test-publish-secret\n", encoding="utf-8")
        portal.ADMIN_PASSWORD_FILE.write_text("test-admin-password-that-is-long-enough\n", encoding="utf-8")
        portal.initialize()

    def restore(self) -> None:
        for name, value in self.originals.items():
            setattr(portal, name, value)

    def share(self, **kwargs):
        portal.create_share("file", "atak:example.dpk", **kwargs)
        return portal.list_shares()[0][0]

    def test_first_of_time_or_count_stops_new_downloads(self) -> None:
        row = self.share(ttl_minutes=10, max_downloads=2)
        self.assertIsNotNone(portal.reserve_download(row["token"]))
        self.assertIsNotNone(portal.reserve_download(row["token"]))
        self.assertIsNone(portal.reserve_download(row["token"]))
        self.assertEqual(portal.share_status(portal.get_share(row["token"]), False), "次數額滿")

        second = self.share(ttl_minutes=10, max_downloads=5)
        with portal.connection() as db:
            db.execute("UPDATE shares SET expires_at=1 WHERE id=?", (second["id"],))
        self.assertIsNone(portal.reserve_download(second["token"]))
        self.assertEqual(portal.share_status(portal.get_share(second["token"]), False), "時間到期")

    def test_parallel_reservations_never_exceed_limit(self) -> None:
        row = self.share(ttl_minutes=10, max_downloads=3)
        with ThreadPoolExecutor(max_workers=12) as workers:
            reservations = list(workers.map(portal.reserve_download, [row["token"]] * 12))
        self.assertEqual(sum(item is not None for item in reservations), 3)
        self.assertEqual(portal.get_share(row["token"])["accepted"], 3)

    def test_public_qr_and_download_count(self) -> None:
        row = self.share(ttl_minutes=10, max_downloads=1)
        client = portal.app.test_client()
        self.assertEqual(client.get("/healthz").status_code, 200)
        self.assertIn(b"example.dpk", client.get(f"/q/{row['token']}").data)
        self.assertEqual(client.get(f"/qr.png/{row['token']}").data[:8], b"\x89PNG\r\n\x1a\n")
        qr = urlparse(portal.qr_value(row))
        self.assertEqual((qr.scheme, qr.netloc, qr.path),
                         ("tak", "com.atakmap.app", "/import"))
        download_url = parse_qs(qr.query)["url"][0]
        self.assertTrue(download_url.endswith(f"/d/{row['token']}/example.dpk"))
        self.assertEqual(client.head(urlparse(download_url).path).status_code, 200)
        self.assertEqual(client.get(f"/d/{row['token']}/wrong.dpk").status_code, 404)
        self.assertEqual(portal.get_share(row["token"])["accepted"], 0)
        response = client.get(urlparse(download_url).path, buffered=True)
        self.assertEqual(response.data, (portal.PACKAGE_DIR / "example.dpk").read_bytes())
        self.assertEqual(client.get(urlparse(download_url).path).status_code, 410)
        self.assertEqual(portal.get_share(row["token"])["completed"], 1)

    def test_admin_auth_csrf_stop_and_pause(self) -> None:
        import share_admin_flask as admin

        row = self.share(ttl_minutes=10, max_downloads=3)
        client = admin.app.test_client()
        self.assertEqual(client.get("/").status_code, 401)
        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        self.assertIn(b"TAK", client.get("/", headers={"Authorization": auth}).data)
        headers = {"Authorization": auth, "Origin": "null", "Sec-Fetch-Site": "same-origin",
                   "Host": "127.0.0.1:8766"}
        response = client.post("/stop", data={"csrf": admin.CSRF, "id": row["id"]}, headers=headers)
        self.assertEqual(response.status_code, 303)
        self.assertIsNone(portal.reserve_download(row["token"]))
        self.assertEqual(client.post("/resume", data={"csrf": "wrong"}, headers=headers).status_code, 403)
        self.assertEqual(client.post("/resume", data={"csrf": admin.CSRF}, headers={
            **headers, "Sec-Fetch-Site": "cross-site"}).status_code, 403)

    def test_admin_live_state_includes_new_shares_and_sources(self) -> None:
        import share_admin_flask as admin

        client = admin.app.test_client()
        auth = {"Authorization": "Basic " + base64.b64encode(
            b"admin:test-admin-password-that-is-long-enough").decode()}
        self.assertEqual(client.get("/admin.js").status_code, 401)
        script = client.get("/admin.js", headers=auth)
        self.assertEqual(script.status_code, 200)
        self.assertIn(b"setInterval(refresh, 2000)", script.data)
        script.close()
        before = client.get("/stats", headers=auth).json
        self.assertEqual(before["shares"], [])
        self.assertIn("atak:example.dpk", str(before["sources"]))
        row = self.share(ttl_minutes=10, max_downloads=2)
        after = client.get("/stats", headers=auth).json
        self.assertEqual(len(after["shares"]), 1)
        self.assertEqual(after["shares"][0]["id"], row["id"])
        self.assertEqual(after["shares"][0]["filename"], "example.dpk")
        self.assertTrue(after["shares"][0]["qr_url"].endswith(f"/q/{row['token']}"))
        self.assertEqual(after["shares"][0]["status"], "分享中")
        portal.update_status(row["id"])
        self.assertEqual(client.get("/stats", headers=auth).json["shares"][0]["status"],
                         "已手動停止")

    def test_icu_profile_uses_secret_without_putting_it_in_qr(self) -> None:
        portal.create_share("icu", "", 10, 2)
        row = portal.list_shares()[0][0]
        profile = (portal.FILE_DIR / row["stored_name"]).read_text(encoding="utf-8")
        self.assertIn("test-publish-secret", profile)
        qr = portal.qr_value(row)
        self.assertTrue(qr.startswith("icu://download?url="))
        self.assertNotIn("test-publish-secret", qr)

    def test_source_folders_and_finished_row_layout(self) -> None:
        (portal.ICU_DIR / "initial.prefs").write_text("<preferences/>", encoding="utf-8")
        with zipfile.ZipFile(portal.PACKAGE_DIR / "atak.dpk", "w") as package:
            package.writestr("example.txt", "example")
        markup = portal.admin_page("test-csrf").decode("utf-8")
        self.assertIn("runtime/packages/icu", markup)
        self.assertIn("runtime/packages/atak", markup)
        self.assertNotIn("runtime/share-inbox", markup)
        with self.assertRaises(ValueError):
            portal.create_share("file", "inbox:example.dpk", 10, 1)
        self.assertIn("value='icu:initial.prefs'", markup)
        self.assertIn("value='atak:atak.dpk'", markup)
        self.assertIn("<th>查看</th><th>控制</th>", markup)
        self.assertIn("目前分享中的連結", markup)
        portal.create_share("icu", "icu:initial.prefs", 10, 1)
        row = portal.list_shares()[0][0]
        self.assertEqual((portal.FILE_DIR / row["stored_name"]).read_text(encoding="utf-8"),
                         "<preferences/>")
        active_markup = portal.admin_page("test-csrf").decode("utf-8")
        self.assertIn(f"<li id='active-{row['id']}'", active_markup)
        self.assertIn(f"/q/{row['token']}", active_markup)
        portal.update_status(row["id"])
        markup = portal.admin_page("test-csrf").decode("utf-8")
        self.assertIn(f"<tr id='row-{row['id']}' class='inactive'>", markup)
        self.assertIn("已結束", markup)
        self.assertIn("status-muted", markup)
        self.assertNotIn(f"<li id='active-{row['id']}'", markup)

    def test_vx_mission_package_requires_tak_server_download(self) -> None:
        with zipfile.ZipFile(portal.PACKAGE_DIR / "voice.dpk", "w") as package:
            package.writestr("MANIFEST/manifest.xml",
                             b'<Parameter name="onReceiveAction" value="' +
                             portal.VX_DOWNLOAD_ACTION + b'"/>')
        choices = portal.import_choices()
        self.assertNotIn("atak:voice.dpk", str(choices))
        with self.assertRaisesRegex(ValueError, "TAK Server Data Packages"):
            portal.create_share("file", "atak:voice.dpk", 10, 1)


if __name__ == "__main__":
    unittest.main()
