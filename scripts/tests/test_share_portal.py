"""Acceptance checks for share quotas, expiry, and public download routes."""

from __future__ import annotations

import base64
import os
import sys
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

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

    def test_certificate_revocation_stops_every_matching_snapshot(self) -> None:
        first = self.share(ttl_minutes=10, max_downloads=3)
        second = self.share(ttl_minutes=10, max_downloads=3)
        self.assertEqual(portal.stop_file_shares("example.dpk"), 2)
        self.assertIsNone(portal.reserve_download(first["token"]))
        self.assertIsNone(portal.reserve_download(second["token"]))
        self.assertEqual(portal.stop_file_shares("example.dpk"), 0)

    def test_certificate_page_and_issue_post_require_admin_and_csrf(self) -> None:
        import share_admin_flask as admin

        record = {"serial": "1002", "fingerprint": "a" * 64, "issuer": "CN=Test CA",
                  "cn": "tablet", "name": "Field tablet", "expires_at": "2028-09-23 08:00:00",
                  "days_left": "730 天", "expiring_soon": False, "expired": False,
                  "revoked": False, "package": None, "registered": True}
        client = admin.app.test_client()
        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        self.assertEqual(client.get("/certificates").status_code, 401)
        with patch.object(admin, "cert_control", return_value={"certificates": [record], "last_result": None}):
            response = client.get("/certificates", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn("到期日（台灣時間）", response.data.decode())
            self.assertIn("Field tablet", response.data.decode())
            self.assertIn("style-src 'self' 'unsafe-inline'", response.headers["Content-Security-Policy"])
            self.assertIn("data-group-board", response.data.decode())
            self.assertIn('id="view-list" aria-pressed="false"', response.data.decode())
            self.assertIn('class="certificate-list" role="list" data-view="cards"', response.data.decode())
            self.assertIn('id="hide-revoked"', response.data.decode())
            self.assertIn('id="count-total">1</strong>', response.data.decode())
            self.assertIn('/static/bootstrap/bootstrap.min.css', response.data.decode())
            self.assertIn('class="modal fade" id="revoke-dialog"', response.data.decode())
        stylesheet = client.get("/static/group_assignment.css", headers=headers)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn(b".group-lanes", stylesheet.data)
        stylesheet.close()
        bootstrap_css = client.get("/static/bootstrap/bootstrap.min.css", headers=headers)
        self.assertEqual(bootstrap_css.status_code, 200)
        self.assertIn(b"v5.3.8", bootstrap_css.data[:500])
        bootstrap_css.close()
        theme_css = client.get("/static/console.css", headers=headers)
        self.assertEqual(theme_css.status_code, 200)
        self.assertIn(b".certificate-list", theme_css.data)
        theme_css.close()
        with patch.object(admin, "cert_control", side_effect=[
                {"certificates": [record], "last_result": None},
                {"status": {"username": "device-01", "in_groups": ["local-test"],
                            "out_groups": ["local-test"]}}]):
            detail = client.get("/certificates/1002", headers=headers)
            self.assertEqual(detail.status_code, 200)
            self.assertIn("群組權限", detail.data.decode())
        with patch.object(admin, "cert_control") as control:
            self.assertEqual(client.post("/certificates/issue", headers=headers,
                                         data={"csrf": "wrong"}).status_code, 403)
            control.assert_not_called()
            response = client.post("/certificates/issue", headers=headers,
                                   data={"csrf": admin.CSRF, "name": "Tablet 02", "cn": "tablet-02",
                                         "in_group": "local-test", "out_group": "local-test"})
            self.assertEqual(response.status_code, 303)
            control.assert_called_once_with("issue", name="Tablet 02", cn="tablet-02",
                                            in_groups=["local-test"], out_groups=["local-test"])

    def test_revoke_route_stops_package_shares_before_host_operation(self) -> None:
        import share_admin_flask as admin

        row = self.share(ttl_minutes=10, max_downloads=3)
        record = {"serial": "1002", "fingerprint": "a" * 64, "package": "example.dpk"}
        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        client = admin.app.test_client()

        def worker(action, **parameters):
            if action == "validate_selection":
                return {"certificates": [record]}
            if action == "revoke":
                self.assertIsNone(portal.reserve_download(row["token"]))
                return {"results": []}
            raise AssertionError(action)

        with patch.object(admin, "cert_control", side_effect=worker):
            response = client.post("/certificates/revoke", headers=headers,
                                   data={"csrf": admin.CSRF, "confirmation": "yes",
                                         "certificate": "1002:" + "a" * 64})
            self.assertEqual(response.status_code, 303)
        self.assertEqual(portal.share_status(portal.get_share(row["token"]), False), "已手動停止")

    def test_alternate_admin_port_and_crl_republish_confirmation(self) -> None:
        import share_admin_flask as admin

        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:10066",
                   "Origin": "http://127.0.0.1:10066"}
        client = admin.app.test_client()
        with patch.dict(os.environ, {"SHARE_ADMIN_HOST_PORT": "10066"}), \
                patch.object(admin, "cert_control") as worker:
            self.assertEqual(client.post("/certificates/republish", headers=headers,
                                         data={"csrf": admin.CSRF}).status_code, 400)
            worker.assert_not_called()
            self.assertEqual(client.post("/certificates/republish", headers=headers,
                                         data={"csrf": admin.CSRF,
                                               "confirmation": "yes"}).status_code, 303)
            worker.assert_called_once_with("republish")

    def test_public_qr_and_download_count(self) -> None:
        row = self.share(ttl_minutes=10, max_downloads=1)
        client = portal.app.test_client()
        self.assertEqual(client.get("/healthz").status_code, 200)
        self.assertIn(b"example.dpk", client.get(f"/q/{row['token']}").data)
        self.assertEqual(client.get(f"/qr.png/{row['token']}").data[:8], b"\x89PNG\r\n\x1a\n")
        public_css = client.get("/static/bootstrap/bootstrap.min.css")
        self.assertEqual(public_css.status_code, 200)
        self.assertIn("style-src 'self'", public_css.headers["Content-Security-Policy"])
        public_css.close()
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
                   "Host": f"127.0.0.1:{os.environ.get('SHARE_ADMIN_HOST_PORT', '8766')}"}
        response = client.post("/stop", data={"csrf": admin.CSRF, "id": row["id"]}, headers=headers)
        self.assertEqual(response.status_code, 303)
        self.assertIsNone(portal.reserve_download(row["token"]))
        self.assertEqual(client.post("/resume", data={"csrf": "wrong"}, headers=headers).status_code, 403)
        self.assertEqual(client.post("/resume", data={"csrf": admin.CSRF}, headers={
            **headers, "Sec-Fetch-Site": "cross-site"}).status_code, 403)
        with patch.object(admin, "control") as control:
            self.assertEqual(client.post("/mumble/restart", data={"csrf": admin.CSRF},
                                         headers=headers).status_code, 400)
            control.assert_not_called()

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
        self.assertEqual(after["shares"][0]["qr_image_url"], f"/qr.png/{row['token']}")
        self.assertEqual(after["shares"][0]["expires_at_epoch"], row["expires_at"])
        self.assertIsInstance(after["server_now"], int)
        self.assertEqual(after["shares"][0]["status"], "分享中")
        self.assertFalse(after["shares"][0]["inactive"])
        self.assertEqual(client.get(f"/qr.png/{row['token']}").status_code, 401)
        self.assertEqual(client.get(f"/qr.png/{row['token']}", headers=auth).data[:8],
                         b"\x89PNG\r\n\x1a\n")
        self.assertEqual(portal.get_share(row["token"])["accepted"], 0)
        portal.set_paused(True)
        paused = client.get("/stats", headers=auth).json["shares"][0]
        self.assertEqual(paused["status"], "全部暫停")
        self.assertFalse(paused["inactive"])
        self.assertEqual(client.get(f"/qr.png/{row['token']}", headers=auth).status_code, 410)
        self.assertIn("已暫停", client.get("/", headers=auth).data.decode())
        portal.set_paused(False)
        portal.update_status(row["id"])
        stopped = client.get("/stats", headers=auth).json["shares"][0]
        self.assertEqual(stopped["status"], "已手動停止")
        self.assertTrue(stopped["inactive"])
        self.assertEqual(client.get(f"/qr.png/{row['token']}", headers=auth).status_code, 410)

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
        self.assertIn("id='share-qr-dialog'", active_markup)
        self.assertIn("/static/bootstrap/bootstrap.bundle.min.js", active_markup)
        self.assertIn(f"data-qr-image='/qr.png/{row['token']}'", active_markup)
        self.assertIn("class='share-countdown'", active_markup)
        self.assertIn("剩餘", active_markup)
        self.assertIn(f"data-expiry='{row['expires_at']}'", active_markup)
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
