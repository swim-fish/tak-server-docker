# TAK console task manual

This manual is for administrators of the local TAK 5.8 test environment. Find the entry point, procedure, and acceptance criteria for each task. Use the page names and button labels in the installed console.

The management entry point is for the Windows host only. Android receives configuration files or DPK files through short-lived QR links.

For field delivery and deactivation, first read the illustrated [frontline Quick Start](../../tak-server/frontline-quick-start.md). This manual gives the full procedures and acceptance criteria.

The console screenshots show the local environment on 2026-09-25 and 26. The ICU chapter also includes device settings. Yellow boxes identify controls in some older images. Device names, certificate identifiers, and registered identities are concealed where necessary. Online counts and sharing states change with time.

![Six main navigation entries in the TAK console](../../images/console-current-navbar.png)

Find the task through the six navigation entries in the image. The 「小隊與群組」 page maps ICU squads to TAK groups. The table below links to procedures and acceptance criteria.

## Open the console

The management page uses `127.0.0.1`. Do not use this address as the Android download address.

DPK files contain device private keys. ICU settings contain the MediaMTX publisher password. Set the sharing expiry and download limit. Stop sharing after delivery. See [sharing service](../../sharing/portal.md) and [certificate console](../../tak-server/certificate-console.md) for startup, firewall, and port changes.

1. Start Docker Desktop.
2. Start the Windows hotspot.
3. Start name resolution for `takbox.local`.
4. Run `docker compose up -d` from the project root.
5. If Android must scan a download QR, run `docker compose --profile sharing up -d share-public`.
6. If Android must scan a download QR, keep the sharing firewall window open in the foreground.
7. Run `.\scripts\Manage-TakControlWorkers.ps1 -Action Status`.
8. If the certificate or Mumble worker is not running, start it with `-Action Start`. Use `-Action Install` only for initial installation.
9. Open `http://127.0.0.1:10066/` in a Windows browser. If `.env` changes `SHARE_ADMIN_HOST_PORT`, use that port.
10. Log in with `admin` and the local `runtime/secrets/share_admin_password`.
11. Check that Navbar opens 「檔案分享」, 「引導式佈建」, 「MediaMTX 管理」, 「Mumble 管理」, 「用戶端憑證」, and 「小隊與群組」.
12. If a device must scan a QR, check that Android uses the same hotspot.
13. If a device must scan a QR, check that Android can resolve `takbox.local`.

## Find a task

| Task | Console entry | Acceptance criteria |
| --- | --- | --- |
| [Deliver an existing TAK certificate](certificates-and-groups.md#task-01) | 引導式佈建 → TAK Server 連線, or 用戶端憑證 → 詳細頁 | Each certificate has a separate short-lived DPK QR. ATAK connects to `takbox.local:8089:ssl`. |
| [Add TAK devices](certificates-and-groups.md#task-02) | 引導式佈建 → 新增 TAK 用戶端 | Each device has its own CN, serial number, groups, DPK, and QR. |
| [Change In/Out permissions](certificates-and-groups.md#task-03) | 用戶端憑證 → 依群組檢視, or 詳細頁 | The TAK API returns the saved groups. |
| [Update the four-channel Vx mission](vx-and-mumble.md#task-04) | 引導式佈建 → Vx 任務 | TAK Server has only one `ATAK Local Voice` package. The device can join all four channels after download. |
| [Deliver ICU settings](icu-and-mediamtx.md#task-05) | 引導式佈建 → ICU 影像發布 | ICU shows external settings. MediaMTX shows the expected `live/.../VIDEO_1` path. |
| [Configure a drone or encoder](icu-and-mediamtx.md#task-06) | 引導式佈建 → Advanced → 一般設備 | Each device has credentials, RTSP/RTSPS publisher URLs, and QR codes. |
| [View or close video](icu-and-mediamtx.md#task-07) | MediaMTX 管理 → ICU／觀看工作階段 | Check the stream list, live preview, public viewing switch, and viewer sessions. |
| [Manage publisher identities](icu-and-mediamtx.md#task-08) | MediaMTX 管理 → ICU／其他 | Identity states match the operation. The password option determines the effect on old connections. |
| [Stop configuration or DPK downloads](sharing-and-troubleshooting.md#task-09) | 檔案分享 → 分享紀錄 | The QR cannot download files. Active links disappear. |
| [Disconnect voice or manage identities](vx-and-mumble.md#task-10) | Mumble 管理 | The online or registered identity list shows the change. |
| [Revoke a TAK certificate](certificates-and-groups.md#task-11) | 用戶端憑證 → 憑證清冊 | The CRL is published. TAK restarts. New connections with the old certificate fail. |
| [Replace the intermediate CA](certificates-and-groups.md#task-ca-replace) | 用戶端憑證 → CA 替換 | New DPK files allow ATAK and Vx login. Test new 8443 connections with old and new certificates after each replacement. |

## Verification scope

This manual uses the implementation, browser tests, and Android tests described in the source documents. Additional screenshots from 2026-09-26 show group operations, CA warnings, and viewer sessions. These images show page content only. They do not prove a repeated CA replacement or viewer connection test. See the [validation index](../../validation/README.md) for ATAK, Vx, ICU, MediaMTX, and certificate revocation results.
