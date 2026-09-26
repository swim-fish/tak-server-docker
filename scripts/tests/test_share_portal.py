"""Acceptance checks for share quotas, expiry, and public download routes."""

from __future__ import annotations

import base64
import hashlib
import json
from html.parser import HTMLParser
import os
import sys
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import share_portal as portal
from certificate_validity import TAIPEI


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
            self.assertNotIn("data-group-board", response.data.decode())
            self.assertIn('href="/certificates/new"', response.data.decode())
            self.assertIn('id="view-list" aria-pressed="false"', response.data.decode())
            self.assertIn('class="certificate-list" role="list" data-view="cards"', response.data.decode())
            self.assertIn('data-cert-status="revoked"', response.data.decode())
            self.assertIn('data-cert-status="all"', response.data.decode())
            self.assertIn('data-cert-status="active" aria-pressed="true"', response.data.decode())
            self.assertIn('id="count-total">1</strong>', response.data.decode())
            self.assertIn('/static/bootstrap/bootstrap.min.css', response.data.decode())
            self.assertIn('class="modal fade" id="revoke-dialog"', response.data.decode())
            self.assertNotIn("撤銷範圍：", response.data.decode())
        with patch.object(admin, "cert_control", return_value={"group_choices": ["local-test", "team-alpha"]}):
            new_page = client.get("/certificates/new", headers=headers)
            self.assertEqual(new_page.status_code, 200)
            self.assertIn("data-group-board", new_page.data.decode())
            self.assertIn("簽發並註冊裝置憑證", new_page.data.decode())
            self.assertIn('aria-current="page" href="/certificates/new"', new_page.data.decode())
        recent = {"action": "revoke", "result": {"results": [
            {"serial": "1002", "ca_revoked": True, "validation_8089": "rejected-revoked"},
            {"serial": "1003", "ca_revoked": False, "error": "test failure"}]}}
        with patch.object(admin, "cert_control", return_value={"certificates": [record],
                                                             "last_result": recent}):
            page = client.get("/certificates", headers=headers).data.decode()
            self.assertIn("最近一次撤銷", page)
            self.assertIn("<li>tablet <code>1002</code></li>", page)
            self.assertNotIn("test failure", page)
            self.assertNotIn("已拒絕撤銷憑證", page)
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
            selected_expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).astimezone(
                TAIPEI).strftime("%Y-%m-%dT%H:%M")
            response = client.post("/certificates/issue", headers=headers,
                                   data={"csrf": admin.CSRF, "name": "Tablet 02", "cn": "tablet-02",
                                         "expires_at": selected_expiry,
                                         "in_group": "local-test", "out_group": "local-test"})
            self.assertEqual(response.status_code, 303)
            control.assert_called_once_with("issue", name="Tablet 02", cn="tablet-02",
                                            expires_at=selected_expiry,
                                            in_groups=["local-test"], out_groups=["local-test", "team-all"])
            control.reset_mock()
            invalid = client.post("/certificates/issue", headers=headers,
                                  data={"csrf": admin.CSRF, "expires_at": "2020-01-01T00:00"})
            self.assertEqual(invalid.status_code, 409)
            control.assert_not_called()

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

    def test_ca_replacement_page_keeps_individual_expiry_and_requires_two_confirmations(self) -> None:
        import share_admin_flask as admin

        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        client = admin.app.test_client()
        expiry = (datetime.now(timezone.utc) + timedelta(days=60)).replace(second=0, microsecond=0)
        taipei_expiry = expiry.astimezone(TAIPEI).strftime("%Y-%m-%dT%H:%M")
        record = {"serial": "1002", "fingerprint": "a" * 64, "name": "Tablet A", "cn": "tablet-a",
                  "expires_iso": expiry.isoformat(), "revoked": False, "expired": False,
                  "registered": True, "in_groups": ["team-alpha"], "out_groups": ["team-alpha"],
                  "package": None}

        def worker(action, **parameters):
            if action == "ca_rotate_status":
                return {"job": {"state": "idle"}}
            if action == "snapshot":
                return {"certificates": [record]}
            if action == "ca_rotate_info":
                return {"ca": {"id": "B" * 64, "serial": "1001", "expires_at": expiry.isoformat()}}
            if action == "ca_rotate_start":
                self.assertEqual(parameters["selected"], [{"serial": "1002", "fingerprint": "a" * 64,
                                                              "expires_at": taipei_expiry}])
                return {"job": {"state": "staging"}}
            raise AssertionError(action)

        with patch.object(admin, "cert_control", side_effect=worker):
            page = client.get("/certificates/ca", headers=headers)
            self.assertEqual(page.status_code, 200)
            self.assertIn('name="expiry_1002"', page.data.decode())
            self.assertIn('value="' + taipei_expiry + '"', page.data.decode())
            self.assertIn("從現在起 90 天", page.data.decode())
            self.assertIn('class="modal fade" id="ca-confirm-dialog"', page.data.decode())
            self.assertIn('id="confirm-ca-replacement" type="submit" disabled', page.data.decode())
            self.assertEqual(client.post("/certificates/ca", headers=headers,
                                         data={"csrf": admin.CSRF, "confirm_credentials": "yes"}).status_code, 400)
            result = client.post("/certificates/ca", headers=headers,
                                 data={"csrf": admin.CSRF, "confirm_credentials": "yes",
                                       "confirm_interruption": "yes", "expected_ca_id": "B" * 64,
                                       "certificate": "1002:" + "a" * 64, "expiry_1002": taipei_expiry})
            self.assertEqual(result.status_code, 303)

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

    def test_share_records_have_identifiable_labels(self) -> None:
        portal.create_share("icu", "", 10, 3, media_owner="squad:alpha",
                            media_path="live/alpha/1/", display_name="ICU-alpha-1")
        portal.create_share("icu", "", 10, 3, media_owner="squad:alpha",
                            media_path="live/command/camera/",
                            display_name="ICU-ADV-live/command/camera")
        portal.create_share("file", "atak:example.dpk", 10, 3,
                            display_name="tablet-1002")
        labels = {portal.share_label(row) for row in portal.list_shares()[0]}
        self.assertEqual(labels, {"ICU-alpha-1", "ICU-ADV-live/command/camera", "tablet-1002"})
        markup = portal.admin_page("test-csrf").decode("utf-8")
        self.assertIn("ICU-alpha-1", markup)
        self.assertIn("ICU-ADV-live/command/camera", markup)
        self.assertIn("tablet-1002", markup)
        self.assertNotIn("完成 0", markup)
        self.assertIn("id='share-qr-count'", markup)
        self.assertIn("data-qr-accepted='0' data-qr-max='3'", markup)

        import share_admin_flask as admin
        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        data = admin.app.test_client().get("/stats", headers={"Authorization": auth}).json
        self.assertEqual({item["display_name"] for item in data["shares"]}, labels)

    def test_shared_navbar_marks_one_current_page_and_breadcrumb_escapes(self) -> None:
        from console_ui import PAGES, breadcrumb, navbar

        for path, _ in PAGES:
            markup = navbar(path + "/result" if path != "/" else path)
            self.assertEqual(markup.count('aria-current="page"'), 1)
            for href, label in PAGES:
                self.assertIn(f'href="{href}">{label}</a>', markup)
        self.assertIn("&lt;script&gt;", breadcrumb([("用戶端憑證", "/certificates"),
                                                    ("<script>", None)]))

    def test_legacy_share_labels_use_available_metadata(self) -> None:
        portal.create_share("icu", "", 10, 1, media_owner="squad:bravo",
                            media_path="live/bravo/2/")
        portal.create_share("icu", "", 10, 1)
        with zipfile.ZipFile(portal.PACKAGE_DIR / "atak-field-tablet-100A.dpk", "w") as package:
            package.writestr("example.txt", "example-package")
        portal.create_share("file", "atak:atak-field-tablet-100A.dpk", 10, 1)
        labels = {portal.share_label(row) for row in portal.list_shares()[0]}
        self.assertEqual(labels, {"ICU-bravo-2", "ICU-預設", "field-tablet-100A"})

    def test_bootstrap_package_label_uses_matching_identity_metadata(self) -> None:
        package = portal.PACKAGE_DIR / "atak-local-test.dpk"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("example.txt", "bootstrap-package")
        identity = {
            "filename": package.name,
            "sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
            "cn": "test-tablet", "serial": "1002",
        }
        package.with_suffix(".identity.json").write_text(json.dumps(identity), encoding="utf-8")
        portal.create_share("file", "atak:atak-local-test.dpk", 10, 1)
        row = portal.list_shares()[0][0]
        self.assertEqual(portal.share_label(row), "test-tablet-1002")
        self.assertEqual(row["display_name"], "test-tablet-1002")
        identity["sha256"] = "0" * 64
        package.with_suffix(".identity.json").write_text(json.dumps(identity), encoding="utf-8")
        self.assertEqual(portal.share_label(row), "test-tablet-1002")
        with portal.connection() as db:
            db.execute("UPDATE shares SET display_name=NULL WHERE id=?", (row["id"],))
        row = portal.list_shares()[0][0]
        self.assertEqual(portal.share_label(row), "atak-local-test.dpk")

    def test_icu_advanced_path_only_enabled_in_advanced_mode(self) -> None:
        import share_admin_flask as admin

        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        client = admin.app.test_client()

        class IcuFields(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.section = {}
                self.input = {}

            def handle_starttag(self, tag, attrs) -> None:
                attributes = dict(attrs)
                if attributes.get("id") == "icu-advanced-path":
                    self.section = attributes
                elif attributes.get("id") == "icu-custom-path":
                    self.input = attributes

        for mode, is_advanced in (("", False), ("&mode=advanced", True)):
            response = client.get(f"/provision?flow=icu{mode}", headers=headers)
            self.assertEqual(response.status_code, 200)
            markup = response.data.decode("utf-8")
            fields = IcuFields()
            fields.feed(markup)
            self.assertEqual("hidden" in fields.section, not is_advanced)
            self.assertEqual("disabled" in fields.input, not is_advanced)
            self.assertEqual("required" in fields.input, is_advanced)
            self.assertIn("input-group icu-url-group", markup)
            self.assertIn("PATH 預覽", markup)
            self.assertIn("/static/icu_path.js", markup)

    def test_icu_squad_provision_accepts_selected_members(self) -> None:
        import share_admin_flask as admin

        operation_dir = self.root / "operations"
        operation_dir.mkdir()
        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        client = admin.app.test_client()
        values = {"csrf": admin.CSRF, "kind": "icu", "icu_mode": "standard", "squad": "alpha",
                  "person": ["1", "3"], "ttl": "20", "limit": "3"}
        configure = client.get("/provision?flow=icu", headers=headers)
        self.assertEqual(configure.status_code, 200)
        self.assertIn("ICU 小隊發布 · 設定", configure.data.decode())
        self.assertEqual(configure.data.count(b'name="person"'), 10)
        preview = client.post("/provision/preview", headers=headers, data=values)
        self.assertEqual(preview.status_code, 200)
        self.assertIn(b"live/alpha/1/VIDEO_1", preview.data)
        self.assertIn(b"live/alpha/3/VIDEO_1", preview.data)
        self.assertNotIn(b"live/alpha/2/VIDEO_1", preview.data)
        missing = client.post("/provision/preview", headers=headers, data={**values, "person": []})
        self.assertEqual(missing.status_code, 400)
        with patch.object(admin, "OPERATIONS_DIR", operation_dir), \
                patch.object(admin.media, "ensure_squad", return_value={
                    "user": "icu-alpha", "password": "test-squad-secret"}):
            execution = client.post("/provision/execute", headers=headers, data={**values,
                                    "operation_id": "e" * 32, "confirmation": "yes"})
            self.assertEqual(execution.status_code, 303)
            rows, _ = portal.list_shares()
            self.assertEqual({row["media_path"] for row in rows}, {"live/alpha/1/", "live/alpha/3/"})
            self.assertEqual(len({row["token"] for row in rows}), 2)
            result = client.get("/provision/result/" + "e" * 32, headers=headers)
            self.assertEqual(result.status_code, 200)
            self.assertIn(b"icu-batch-carousel", result.data)
            self.assertIn(b"ICU-alpha-1", result.data)
            self.assertIn(b"ICU-alpha-3", result.data)

    def test_source_folders_and_finished_row_layout(self) -> None:
        (portal.ICU_DIR / "initial.prefs").write_text("<preferences/>", encoding="utf-8")
        with zipfile.ZipFile(portal.PACKAGE_DIR / "atak.dpk", "w") as package:
            package.writestr("example.txt", "example")
        markup = portal.admin_page("test-csrf").decode("utf-8")
        choices = portal.import_choices()
        self.assertIn("runtime/packages/icu", [group for group, _ in choices])
        self.assertIn("runtime/packages/atak", [group for group, _ in choices])
        self.assertNotIn("runtime/share-inbox", markup)
        with self.assertRaises(ValueError):
            portal.create_share("file", "inbox:example.dpk", 10, 1)
        self.assertIn("開始引導式佈建", markup)
        self.assertIn("/provision", markup)
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

    def test_batch_certificate_preview_and_repeat_submission(self) -> None:
        import share_admin_flask as admin

        operation_dir = self.root / "operations"
        operation_dir.mkdir()
        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        client = admin.app.test_client()
        selected_expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).astimezone(
            TAIPEI).strftime("%Y-%m-%dT%H:%M")
        form = {"csrf": admin.CSRF, "name": ["Test One", "Test Two"],
                "cn": ["test-one", "test-two"], "in_groups": ["local-test", "team-a"],
                "out_groups": ["local-test", "team-b"], "expires_at": [selected_expiry, ""],
                "ttl": "20", "limit": "3"}
        preview = client.post("/provision/tak-new/preview", data=form, headers=headers)
        self.assertEqual(preview.status_code, 200)
        self.assertIn(b"test-one", preview.data)
        self.assertIn(b"test-two", preview.data)
        class HiddenValues(HTMLParser):
            value = None

            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if tag == "input" and attributes.get("name") == "values":
                    self.value = attributes.get("value")

        hidden = HiddenValues()
        hidden.feed(preview.data.decode("utf-8"))
        self.assertEqual(json.loads(hidden.value)["items"][1]["cn"], "test-two")
        self.assertEqual(json.loads(hidden.value)["items"][0]["expires_at"], selected_expiry)
        self.assertIn("team-all", json.loads(hidden.value)["items"][0]["out_groups"])
        self.assertNotEqual(json.loads(hidden.value)["items"][1]["expires_at"], selected_expiry)
        invalid = {**form, "expires_at": ["2020-01-01T00:00", ""]}
        self.assertEqual(client.post("/provision/tak-new/preview", data=invalid,
                                     headers=headers).status_code, 400)
        values = {
            "items": [{"name": "Test One", "cn": "test-one", "in_groups": ["local-test"],
                       "out_groups": ["local-test"]},
                      {"name": "Test Two", "cn": "test-two", "in_groups": ["team-a"],
                       "out_groups": ["team-b"]}], "ttl": 20, "limit": 3}
        entries = [{"request": item, "state": "registered", "serial": serial,
                    "package": f"atak-{item['cn']}-{serial}.dpk"}
                   for item, serial in zip(values["items"], ("100A", "100B"))]
        job_id = "a" * 32
        execution = {"csrf": admin.CSRF, "job_id": job_id, "confirmation": "yes",
                     "values": json.dumps(values)}
        with patch.object(admin, "OPERATIONS_DIR", operation_dir), \
                patch.object(admin, "cert_control", return_value={"batch": {
                    "state": "complete", "items": entries}}) as worker, \
                patch.object(portal, "create_share", side_effect=[101, 102]) as create:
            self.assertEqual(client.post("/provision/tak-new/execute", data=execution,
                                         headers=headers).status_code, 303)
            self.assertEqual(client.post("/provision/tak-new/execute", data=execution,
                                         headers=headers).status_code, 303)
            self.assertEqual(create.call_count, 2)
            self.assertEqual(worker.call_count, 1)
            receipt = admin.read_operation(job_id, "provision:tak-new")
            self.assertEqual(receipt["state"], "complete")
            self.assertEqual(len(receipt["results"]), 2)

    def test_new_certificate_form_uses_group_board(self) -> None:
        import share_admin_flask as admin

        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        with patch.object(admin, "cert_control", return_value={"group_choices": ["team-a"]}):
            response = admin.app.test_client().get("/provision?flow=tak-new", headers=headers)
        self.assertEqual(response.status_code, 200)
        markup = response.data.decode("utf-8")
        self.assertIn('data-group-field-mode="csv"', markup)
        self.assertIn('name="expires_at" type="datetime-local"', markup)
        self.assertIn('data-expiry-preset', markup)
        self.assertIn('<option value="168">7 天</option>', markup)
        self.assertIn('<option value="336">14 天</option>', markup)
        self.assertIn('<option value="672">28 天</option>', markup)
        self.assertIn('<option value="2160">90 天</option>', markup)
        self.assertIn('name="in_groups" value=""', markup)
        self.assertIn('name="out_groups" value="team-all"', markup)
        self.assertIn('data-certificate-squad', markup)
        self.assertIn('data-group="team-a"', markup)
        self.assertIn('data-lane="none"', markup)
        self.assertIn('data-lane="both"', markup)

    def test_icu_batch_creates_distinct_qr_shares(self) -> None:
        import share_admin_flask as admin
        import squad_groups

        operation_dir = self.root / "operations"
        operation_dir.mkdir()
        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        client = admin.app.test_client()
        values = {"csrf": admin.CSRF, "squad": "alpha", "start": "1", "count": "2",
                  "group": ["team-alpha"], "ttl": "20", "limit": "3"}
        with patch.object(squad_groups, "MAPPING_FILE", self.root / "squad-groups.json"):
            self.assertEqual(client.get("/provision/icu-batch", headers=headers).status_code, 200)
            preview = client.post("/provision/icu-batch/preview", headers=headers, data=values)
            self.assertEqual(preview.status_code, 200)
            self.assertIn(b"live/alpha/2/VIDEO_1", preview.data)
            with patch.object(admin, "OPERATIONS_DIR", operation_dir), \
                    patch.object(admin.media, "ensure_squad", return_value={
                        "user": "icu-alpha", "password": "test-publish-password"}), \
                    patch.object(admin, "cert_control", return_value={"batch": {"state": "complete", "results": [
                        {"person": person, "state": "ready", "uid": f"test-{person}"} for person in (1, 2)]}}):
                submitted = {**values, "operation_id": "a" * 32, "confirmation": "yes"}
                response = client.post("/provision/icu-batch/execute", headers=headers, data=submitted)
                self.assertEqual(response.status_code, 303)
                receipt = admin.read_operation("a" * 32, "provision:icu-batch")
                self.assertEqual(receipt["state"], "complete")
                rows, _ = portal.list_shares()
                self.assertEqual(len(rows), 2)
                self.assertEqual({row["batch_id"] for row in rows}, {"a" * 32})
                self.assertEqual(len({row["token"] for row in rows}), 2)
                result = client.get("/provision/icu-batch/result/" + "a" * 32, headers=headers)
                self.assertEqual(result.status_code, 200)
                self.assertIn(b"carousel-item", result.data)
                self.assertIn(b"live/alpha/1/VIDEO_1", result.data)
                self.assertIn(b"live/alpha/2/VIDEO_1", result.data)
                self.assertIn(b"team-alpha", result.data)

    def test_media_overview_shows_live_thumbnail_and_track_names(self) -> None:
        import share_admin_flask as admin

        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        path = {"name": "live/alpha/3/VIDEO_1", "tracks": ["H264", "KLV"]}
        viewer = {"desired": True, "sessions": 1, "local_base": "http://takbox.local:8889"}
        with patch.object(admin.media, "load", return_value={"publishers": {}}), \
                patch.object(admin.media, "active_paths", return_value=[path]), \
                patch.object(admin.media, "viewer_status", return_value=viewer):
            response = admin.app.test_client().get("/media", headers=headers)
        markup = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn('class="card media-viewer-card live"', markup)
        self.assertIn('class="media-stream-card"', markup)
        self.assertIn('data-thumbnail-url="/media/preview/live/alpha/3/VIDEO_1/', markup)
        self.assertIn("H264、KLV", markup)
        self.assertNotIn("H264、KLV、", markup)

    def test_icu_reshare_can_select_member_paths(self) -> None:
        import share_admin_flask as admin

        publisher = {"kind": "squad", "name": "Alpha", "user": "icu-alpha",
                     "password": "test-squad-secret", "enabled": True,
                     "paths": ["live/alpha/1/VIDEO_1", "live/alpha/2/VIDEO_1"]}
        operation_dir = self.root / "operations"
        operation_dir.mkdir()
        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        client = admin.app.test_client()
        base = {"csrf": admin.CSRF, "view": "icu", "action": "reshare",
                "confirmation": "yes", "publisher": ["squad:alpha"],
                "path_selection_present": "yes", "ttl": "20", "limit": "3"}
        with patch.object(admin, "OPERATIONS_DIR", operation_dir), \
                patch.object(admin.media, "load", return_value={"publishers": {"squad:alpha": publisher}}), \
                patch.object(admin.media, "active_paths", return_value=[]), \
                patch.object(admin.media, "viewer_status", return_value={"desired": True, "sessions": 0,
                                                                           "local_base": "http://takbox.local:8889"}):
            page = client.get("/media", headers=headers)
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"media-path-select-all", page.data)
            self.assertIn(b"media-path-select-none", page.data)
            self.assertEqual(page.data.count(b'name="reshare_path"'), 2)

            one = client.post("/media/update", headers=headers, data={**base, "operation_id": "b" * 32,
                              "reshare_path": ["squad:alpha|live/alpha/2/VIDEO_1"]})
            self.assertEqual(one.status_code, 303)
            shares, _ = portal.list_shares()
            self.assertEqual([row["media_path"] for row in shares], ["live/alpha/2/"])

            none = client.post("/media/update", headers=headers, data={**base, "operation_id": "c" * 32})
            self.assertEqual(none.status_code, 303)
            self.assertEqual(admin.read_operation("c" * 32, "media:update")["state"], "failed")
            self.assertEqual(len(portal.list_shares()[0]), 1)

            all_paths = client.post("/media/update", headers=headers, data={**base,
                                    "operation_id": "d" * 32, "reshare_path": [
                                        "squad:alpha|live/alpha/1/VIDEO_1",
                                        "squad:alpha|live/alpha/2/VIDEO_1"]})
            self.assertEqual(all_paths.status_code, 303)
            self.assertEqual(len(portal.list_shares()[0]), 3)

    def test_certificate_group_overview_classifies_each_permission(self) -> None:
        import share_admin_flask as admin

        records = [
            {"serial": "1001", "name": "Writer", "cn": "writer", "in_groups": ["team-a"],
             "out_groups": [], "revoked": False, "expired": False},
            {"serial": "1002", "name": "Reader", "cn": "reader", "in_groups": [],
             "out_groups": ["team-a"], "revoked": False, "expired": False},
            {"serial": "1003", "name": "Both", "cn": "both", "in_groups": ["team-a"],
             "out_groups": ["team-a"], "revoked": True, "expired": False},
            {"serial": "1004", "name": "Unknown", "cn": "unknown", "in_groups": [],
             "out_groups": [], "revoked": False, "expired": True},
        ]
        groups, unassigned = admin.certificate_group_index(records)
        self.assertEqual([item["serial"] for item in groups[0]["in"]], ["1001"])
        self.assertEqual([item["serial"] for item in groups[0]["out"]], ["1002"])
        self.assertEqual([item["serial"] for item in groups[0]["both"]], ["1003"])
        self.assertEqual([item["serial"] for item in unassigned], ["1004"])
        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        with patch.object(admin, "cert_control", return_value={"certificates": records}):
            response = admin.app.test_client().get("/certificates/groups", headers=headers)
        self.assertEqual(response.status_code, 200)
        markup = response.data.decode("utf-8")
        self.assertIn("依群組檢視憑證", markup)
        self.assertIn('id="group-records" type="application/json"', markup)
        self.assertIn('data-group-card="team-a"', markup)
        self.assertIn('data-lane="in"', markup)
        self.assertIn('data-lane="out"', markup)
        self.assertIn('data-lane="both"', markup)
        self.assertIn("未記錄群組", markup)
        self.assertIn('data-group-status="revoked"', markup)
        self.assertIn('data-group-status="all"', markup)
        self.assertIn('data-group-status="active" aria-pressed="true"', markup)
        self.assertIn('id="group-add-dialog"', markup)
        self.assertIn("搜尋尚未加入的使用中憑證", markup)

    def test_certificate_group_batch_requires_confirmation(self) -> None:
        import share_admin_flask as admin

        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        client = admin.app.test_client()
        change = {"serial": "1001", "fingerprint": "f" * 64,
                  "expected_in": ["local-test"], "expected_out": ["local-test"],
                  "in_groups": ["team-a"], "out_groups": ["team-a"]}
        form = {"csrf": admin.CSRF, "changes": json.dumps([change])}
        with patch.object(admin, "cert_control") as worker:
            self.assertEqual(client.post("/certificates/groups/batch", data=form,
                                         headers=headers).status_code, 400)
            worker.assert_not_called()
            form["confirmation"] = "yes"
            worker.return_value = {"batch": {"state": "complete", "results": []}}
            response = client.post("/certificates/groups/batch", data=form, headers=headers)
            self.assertEqual(response.status_code, 303)
            self.assertIn("/certificates/groups?result=complete", response.headers["Location"])
            worker.assert_called_once_with("group_batch", changes=[change])

    def test_device_path_uses_url_input_group(self) -> None:
        import share_admin_flask as admin

        auth = "Basic " + base64.b64encode(b"admin:test-admin-password-that-is-long-enough").decode()
        headers = {"Authorization": auth, "Host": "127.0.0.1:8766"}
        response = admin.app.test_client().get("/provision?flow=device", headers=headers)
        self.assertEqual(response.status_code, 200)
        markup = response.data.decode("utf-8")
        self.assertIn('id="device-url-base">rtsps://takbox.local:8322/', markup)
        self.assertIn('id="device-path" name="path"', markup)
        self.assertIn("/static/device_path.js", markup)


if __name__ == "__main__":
    unittest.main()
