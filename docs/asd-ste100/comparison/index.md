# TAK 控制台任務操作手冊：原文與中英文改寫對照

[原始手冊](../../tak-server/console-task-manual.md) · [繁中版](../zh-TW/index.md) · [English](../en/index.md)

原文欄保留來源內容。段落 ID 用於追蹤對照。獨立手冊依操作順序排列，必要時將風險說明移到步驟前。

## B001

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **TAK 控制台任務操作手冊** | **TAK 控制台任務操作手冊** | **TAK console task manual** |

## B002

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 本手冊供本機 TAK 5.8 測試環境的管理人員使用。依要完成的任務找入口、執行步驟與驗收結果；控制台頁面名稱及按鈕文字以目前版本為準。管理入口只供 Windows 主機使用，Android 只接收短效 QR 所指向的設定檔或 DPK。 | 本手冊供本機 TAK 5.8 測試環境的管理人員使用。依任務尋找入口、操作步驟與驗收結果。控制台頁面名稱及按鈕文字以目前版本為準。<br><br>管理入口只供 Windows 主機使用。Android 只接收短效 QR 所指向的設定檔或 DPK。 | This manual is for administrators of the local TAK 5.8 test environment. Find the entry point, procedure, and acceptance criteria for each task. Use the page names and button labels in the installed console.<br><br>The management entry point is for the Windows host only. Android receives configuration files or DPK files through short-lived QR links. |

## B003

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 現場交付與停用請先看圖片版[現場人員 Quick Start](../../tak-server/frontline-quick-start.md)；本手冊保留完整步驟及驗收資訊。 | 現場交付與停用請先看圖片版[現場人員 Quick Start](../../tak-server/frontline-quick-start.md)。本手冊提供完整步驟及驗收資訊。 | For field delivery and deactivation, first read the illustrated [frontline Quick Start](../../tak-server/frontline-quick-start.md). This manual gives the full procedures and acceptance criteria. |

## B004

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 控制台截圖取自 2026-09-25 至 26 日的本機環境，ICU 章另附實機設定畫面。部分舊圖以黃色框標出操作區；裝置名稱、憑證識別資料與註冊身分等資訊在需要時已遮蔽。線上數量與分享狀態會隨時間改變。 | 控制台截圖取自 2026-09-25 至 26 日的本機環境。ICU 章另附實機設定畫面。部分舊圖以黃色框標出操作區。裝置名稱、憑證識別資料與註冊身分等資訊在需要時已遮蔽。線上數量與分享狀態會隨時間改變。 | The console screenshots show the local environment on 2026-09-25 and 26. The ICU chapter also includes device settings. Yellow boxes identify controls in some older images. Device names, certificate identifiers, and registered identities are concealed where necessary. Online counts and sharing states change with time. |

## B005

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [目前 TAK 控制台的六個主導覽入口](../../images/console-current-navbar.png) | [目前 TAK 控制台的六個主導覽入口](../../images/console-current-navbar.png) | [Six main navigation entries in the TAK console](../../images/console-current-navbar.png) |

## B006

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 從圖中的六個主導覽入口找任務；「小隊與群組」用來設定 ICU 小隊與 TAK 群組的對應。下表連到各章的操作步驟與驗收項目。 | 從圖中的六個主導覽入口尋找任務。「小隊與群組」用來設定 ICU 小隊與 TAK 群組的對應。下表連到各章的操作步驟與驗收項目。 | Find the task through the six navigation entries in the image. The 「小隊與群組」 page maps ICU squads to TAK groups. The table below links to procedures and acceptance criteria. |

## B007

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **先開啟控制台** | **先開啟控制台** | **Open the console** |

## B008

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 啟動 Docker Desktop、Windows 熱點與 `takbox.local` 名稱解析，在專案根目錄執行 `docker compose up -d`。需要讓 Android 掃描下載 QR 時，另執行 `docker compose --profile sharing up -d share-public`，並保持分享防火牆的前景視窗開啟。<br>2. 執行 `.\scripts\Manage-TakControlWorkers.ps1 -Action Status`；憑證或 Mumble 管理程式未執行時，以 `-Action Start` 啟動。首次安裝才使用 `-Action Install`。<br>3. 在 Windows 瀏覽器開啟 `http://127.0.0.1:10066/`。以 `admin` 和本機 `runtime/secrets/share_admin_password` 登入。若 `.env` 已改 `SHARE_ADMIN_HOST_PORT`，使用實際通訊埠。<br>4. 先核對頁面 Navbar 可以開啟「檔案分享」、「引導式佈建」、「MediaMTX 管理」、「Mumble 管理」、「用戶端憑證」及「小隊與群組」。需要裝置掃 QR 時，再確認 Android 位於相同熱點、可解析 `takbox.local`。 | 1. 啟動 Docker Desktop。<br>2. 啟動 Windows 熱點。<br>3. 啟動 `takbox.local` 名稱解析。<br>4. 在專案根目錄執行 `docker compose up -d`。<br>5. 若需要讓 Android 掃描下載 QR，執行 `docker compose --profile sharing up -d share-public`。<br>6. 若需要讓 Android 掃描下載 QR，保持分享防火牆的前景視窗開啟。<br>7. 執行 `.\scripts\Manage-TakControlWorkers.ps1 -Action Status`。<br>8. 若憑證或 Mumble 管理程式未執行，以 `-Action Start` 啟動。首次安裝才使用 `-Action Install`。<br>9. 在 Windows 瀏覽器開啟 `http://127.0.0.1:10066/`。若 `.env` 已改 `SHARE_ADMIN_HOST_PORT`，使用實際通訊埠。<br>10. 以 `admin` 和本機 `runtime/secrets/share_admin_password` 登入。<br>11. 核對 Navbar 可以開啟「檔案分享」、「引導式佈建」、「MediaMTX 管理」、「Mumble 管理」、「用戶端憑證」及「小隊與群組」。<br>12. 若需要讓裝置掃 QR，確認 Android 位於相同熱點。<br>13. 若需要讓裝置掃 QR，確認 Android 可解析 `takbox.local`。 | 1. Start Docker Desktop.<br>2. Start the Windows hotspot.<br>3. Start name resolution for `takbox.local`.<br>4. Run `docker compose up -d` from the project root.<br>5. If Android must scan a download QR, run `docker compose --profile sharing up -d share-public`.<br>6. If Android must scan a download QR, keep the sharing firewall window open in the foreground.<br>7. Run `.\scripts\Manage-TakControlWorkers.ps1 -Action Status`.<br>8. If the certificate or Mumble worker is not running, start it with `-Action Start`. Use `-Action Install` only for initial installation.<br>9. Open `http://127.0.0.1:10066/` in a Windows browser. If `.env` changes `SHARE_ADMIN_HOST_PORT`, use that port.<br>10. Log in with `admin` and the local `runtime/secrets/share_admin_password`.<br>11. Check that Navbar opens 「檔案分享」, 「引導式佈建」, 「MediaMTX 管理」, 「Mumble 管理」, 「用戶端憑證」, and 「小隊與群組」.<br>12. If a device must scan a QR, check that Android uses the same hotspot.<br>13. If a device must scan a QR, check that Android can resolve `takbox.local`. |

## B009

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 管理頁使用 `127.0.0.1`，不可將它當成 Android 的下載網址。DPK 含裝置私鑰；ICU 設定含 MediaMTX 發布密碼。分享時設定期限與下載上限，完成後停止分享。詳細的啟動、防火牆及通訊埠調整見[分享服務](../../sharing/portal.md)與[憑證控制台](../../tak-server/certificate-console.md)。 | 管理頁使用 `127.0.0.1`。不可將這個位址當成 Android 的下載網址。<br><br>DPK 含裝置私鑰。ICU 設定含 MediaMTX 發布密碼。分享時須設定期限與下載上限。完成後須停止分享。啟動、防火牆及通訊埠調整方式見[分享服務](../../sharing/portal.md)與[憑證控制台](../../tak-server/certificate-console.md)。 | The management page uses `127.0.0.1`. Do not use this address as the Android download address.<br><br>DPK files contain device private keys. ICU settings contain the MediaMTX publisher password. Set the sharing expiry and download limit. Stop sharing after delivery. See [sharing service](../../sharing/portal.md) and [certificate console](../../tak-server/certificate-console.md) for startup, firewall, and port changes. |

## B010

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **依任務找頁面** | **依任務找頁面** | **Find a task** |

## B011

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| \| 你要完成的任務 \| 控制台入口 \| 完成時應看見 \|<br>\| --- \| --- \| --- \|<br>\| [交付既有 TAK 裝置憑證](../../tak-server/console-task-manual/certificates-and-groups.md#task-01) \| 引導式佈建 → TAK Server 連線，或用戶端憑證 → 詳細頁 \| 每張憑證有獨立短效 DPK QR；ATAK 連上 `takbox.local:8089:ssl` \|<br>\| [新增一台或一批 TAK 裝置](../../tak-server/console-task-manual/certificates-and-groups.md#task-02) \| 引導式佈建 → 新增 TAK 用戶端 \| 每台各有 CN、序號、群組、DPK 與 QR \|<br>\| [更改裝置 In／Out 權限](../../tak-server/console-task-manual/certificates-and-groups.md#task-03) \| 用戶端憑證 → 依群組檢視，或詳細頁 \| 儲存後從 TAK API 讀回相同群組 \|<br>\| [更新 Vx 四頻道任務](../../tak-server/console-task-manual/vx-and-mumble.md#task-04) \| 引導式佈建 → Vx 任務 \| TAK Server 只剩一筆 `ATAK Local Voice`；裝置下載後能加入四頻道 \|<br>\| [交付 ICU 設定](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-05) \| 引導式佈建 → ICU 影像發布 \| ICU 顯示外部設定，並在 MediaMTX 看見預期 `live/.../VIDEO_1` \|<br>\| [設定無人機或編碼器](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-06) \| 引導式佈建 → Advanced → 一般設備 \| 個別帳密及 RTSP／RTSPS 發布網址、QR \|<br>\| [檢視或關閉影像](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-07) \| MediaMTX 管理 → ICU／觀看工作階段 \| 串流清單、即時預覽、公開觀看開關及觀看工作階段符合預期 \|<br>\| [停用、重新啟用或輪替影像發布身分](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-08) \| MediaMTX 管理 → ICU／其他 \| 小隊或裝置身分狀態符合操作結果，舊連線依密碼選項處理 \|<br>\| [停止設定檔或 DPK 下載](../../tak-server/console-task-manual/sharing-and-troubleshooting.md#task-09) \| 檔案分享 → 分享紀錄 \| QR 無法再下載；目前有效連結消失 \|<br>\| [中斷語音或管理註冊身分](../../tak-server/console-task-manual/vx-and-mumble.md#task-10) \| Mumble 管理 \| 線上連線或註冊清單反映變更 \|<br>\| [撤銷 TAK 裝置憑證](../../tak-server/console-task-manual/certificates-and-groups.md#task-11) \| 用戶端憑證 → 憑證清冊 \| CRL 發布、TAK 重啟，舊憑證新連線遭拒 \|<br>\| [替換中繼 CA 並選擇重簽裝置](../../tak-server/console-task-manual/certificates-and-groups.md#task-ca-replace) \| 用戶端憑證 → CA 替換 \| 新 DPK 可登入 ATAK 與 Vx；8443 須以舊／新憑證建立新連線，逐次確認停權與可用性 \| | \| 你要完成的任務 \| 控制台入口 \| 完成時應看見 \|<br>\| --- \| --- \| --- \|<br>\| [交付既有 TAK 裝置憑證](../../tak-server/console-task-manual/certificates-and-groups.md#task-01) \| 引導式佈建 → TAK Server 連線，或用戶端憑證 → 詳細頁 \| 每張憑證有獨立短效 DPK QR；ATAK 連上 `takbox.local:8089:ssl` \|<br>\| [新增一台或一批 TAK 裝置](../../tak-server/console-task-manual/certificates-and-groups.md#task-02) \| 引導式佈建 → 新增 TAK 用戶端 \| 每台各有 CN、序號、群組、DPK 與 QR \|<br>\| [更改裝置 In／Out 權限](../../tak-server/console-task-manual/certificates-and-groups.md#task-03) \| 用戶端憑證 → 依群組檢視，或詳細頁 \| 儲存後從 TAK API 讀回相同群組 \|<br>\| [更新 Vx 四頻道任務](../../tak-server/console-task-manual/vx-and-mumble.md#task-04) \| 引導式佈建 → Vx 任務 \| TAK Server 只剩一筆 `ATAK Local Voice`；裝置下載後能加入四頻道 \|<br>\| [交付 ICU 設定](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-05) \| 引導式佈建 → ICU 影像發布 \| ICU 顯示外部設定，並在 MediaMTX 看見預期 `live/.../VIDEO_1` \|<br>\| [設定無人機或編碼器](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-06) \| `引導式佈建 → Advanced → 一般設備` \| 個別帳密及 RTSP／RTSPS 發布網址、QR \|<br>\| [檢視或關閉影像](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-07) \| MediaMTX 管理 → ICU／觀看工作階段 \| 串流清單、即時預覽、公開觀看開關及觀看工作階段符合預期 \|<br>\| [停用、重新啟用或輪替影像發布身分](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-08) \| MediaMTX 管理 → ICU／其他 \| 小隊或裝置身分狀態符合操作結果，舊連線依密碼選項處理 \|<br>\| [停止設定檔或 DPK 下載](../../tak-server/console-task-manual/sharing-and-troubleshooting.md#task-09) \| 檔案分享 → 分享紀錄 \| QR 無法再下載；目前有效連結消失 \|<br>\| [中斷語音或管理註冊身分](../../tak-server/console-task-manual/vx-and-mumble.md#task-10) \| Mumble 管理 \| 線上連線或註冊清單反映變更 \|<br>\| [撤銷 TAK 裝置憑證](../../tak-server/console-task-manual/certificates-and-groups.md#task-11) \| 用戶端憑證 → 憑證清冊 \| CRL 發布、TAK 重啟，舊憑證新連線遭拒 \|<br>\| [替換中繼 CA 並選擇重簽裝置](../../tak-server/console-task-manual/certificates-and-groups.md#task-ca-replace) \| 用戶端憑證 → CA 替換 \| 新 DPK 可登入 ATAK 與 Vx；8443 須以舊／新憑證建立新連線，逐次確認停權與可用性 \| | \| Task \| Console entry \| Acceptance criteria \|<br>\| --- \| --- \| --- \|<br>\| [Deliver an existing TAK certificate](../../tak-server/console-task-manual/certificates-and-groups.md#task-01) \| 引導式佈建 → TAK Server 連線, or 用戶端憑證 → 詳細頁 \| Each certificate has a separate short-lived DPK QR. ATAK connects to `takbox.local:8089:ssl`. \|<br>\| [Add TAK devices](../../tak-server/console-task-manual/certificates-and-groups.md#task-02) \| 引導式佈建 → 新增 TAK 用戶端 \| Each device has its own CN, serial number, groups, DPK, and QR. \|<br>\| [Change In/Out permissions](../../tak-server/console-task-manual/certificates-and-groups.md#task-03) \| 用戶端憑證 → 依群組檢視, or 詳細頁 \| The TAK API returns the saved groups. \|<br>\| [Update the four-channel Vx mission](../../tak-server/console-task-manual/vx-and-mumble.md#task-04) \| 引導式佈建 → Vx 任務 \| TAK Server has only one `ATAK Local Voice` package. The device can join all four channels after download. \|<br>\| [Deliver ICU settings](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-05) \| 引導式佈建 → ICU 影像發布 \| ICU shows external settings. MediaMTX shows the expected `live/.../VIDEO_1` path. \|<br>\| [Configure a drone or encoder](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-06) \| 引導式佈建 → Advanced → 一般設備 \| Each device has credentials, RTSP/RTSPS publisher URLs, and QR codes. \|<br>\| [View or close video](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-07) \| MediaMTX 管理 → ICU／觀看工作階段 \| Check the stream list, live preview, public viewing switch, and viewer sessions. \|<br>\| [Manage publisher identities](../../tak-server/console-task-manual/icu-and-mediamtx.md#task-08) \| MediaMTX 管理 → ICU／其他 \| Identity states match the operation. The password option determines the effect on old connections. \|<br>\| [Stop configuration or DPK downloads](../../tak-server/console-task-manual/sharing-and-troubleshooting.md#task-09) \| 檔案分享 → 分享紀錄 \| The QR cannot download files. Active links disappear. \|<br>\| [Disconnect voice or manage identities](../../tak-server/console-task-manual/vx-and-mumble.md#task-10) \| Mumble 管理 \| The online or registered identity list shows the change. \|<br>\| [Revoke a TAK certificate](../../tak-server/console-task-manual/certificates-and-groups.md#task-11) \| 用戶端憑證 → 憑證清冊 \| The CRL is published. TAK restarts. New connections with the old certificate fail. \|<br>\| [Replace the intermediate CA](../../tak-server/console-task-manual/certificates-and-groups.md#task-ca-replace) \| 用戶端憑證 → CA 替換 \| New DPK files allow ATAK and Vx login. Test new 8443 connections with old and new certificates after each replacement. \| |

## B012

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **驗收範圍** | **驗收範圍** | **Verification scope** |

## B013

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 本手冊以目前實作、既有瀏覽器及 Android 測試紀錄為依據。2026-09-26 另擷取新版群組操作、CA 警告及觀看工作階段頁；這些圖片只證明頁面顯示，不代表重新執行 CA 輪替或觀看連線。已實測的 ATAK、Vx、ICU、MediaMTX 及憑證撤銷結果，見[驗證索引](../../validation/README.md)。 | 本手冊以原始文件所述的實作、瀏覽器測試及 Android 測試紀錄為依據。2026-09-26 另擷取新版群組操作、CA 警告及觀看工作階段頁。這些圖片只證明頁面顯示，不代表重新執行 CA 輪替或觀看連線。ATAK、Vx、ICU、MediaMTX 及憑證撤銷的實測結果，見[驗證索引](../../validation/README.md)。 | This manual uses the implementation, browser tests, and Android tests described in the source documents. Additional screenshots from 2026-09-26 show group operations, CA warnings, and viewer sessions. These images show page content only. They do not prove a repeated CA replacement or viewer connection test. See the [validation index](../../validation/README.md) for ATAK, Vx, ICU, MediaMTX, and certificate revocation results. |
