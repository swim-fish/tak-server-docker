# 分享與疑難排解：原文與中英文改寫對照

[原始手冊](../../tak-server/console-task-manual/sharing-and-troubleshooting.md) · [繁中版](../zh-TW/sharing-and-troubleshooting.md) · [English](../en/sharing-and-troubleshooting.md)

原文欄保留來源內容。段落 ID 用於追蹤對照。獨立手冊依操作順序排列，必要時將風險說明移到步驟前。

## B001

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **分享與疑難排解** | **分享與疑難排解** | **Sharing and troubleshooting** |

## B002

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [返回任務索引](../../tak-server/console-task-manual.md) | [返回任務索引](../../tak-server/console-task-manual.md) | [Return to the task index](../../tak-server/console-task-manual.md) |

## B003

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-09 | Anchor: task-09 | Anchor: task-09 |

## B004

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務九　檢視與停止設定檔分享** | **任務九　檢視與停止設定檔分享** | **Task 9: Inspect and stop configuration sharing** |

## B005

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 在「檔案分享」看頁首總開關及「分享中」連結；分享紀錄可切換每頁 10、20、30 筆與狀態篩選。<br>2. 要停止單筆，按「停止分享」；全部暫停則用總開關。分享中會顯示剩餘時間與下載次數。<br>3. 確認舊 QR 無法再下載。已下載到裝置的 DPK 或 `initial.prefs` 不會自動消失，身分停用須另行處理。 | 分享紀錄會顯示剩餘時間與下載次數。可切換每頁 10、20、30 筆，也可使用狀態篩選。<br><br>1. 在「檔案分享」核對頁首總開關及「分享中」連結。<br>2. 若要停止單筆分享，按該筆紀錄的「停止分享」。<br>3. 若要暫停全部分享，使用總開關。<br>4. 確認舊 QR 無法再下載。<br><br>已下載到裝置的 DPK 或 `initial.prefs` 不會自動消失。身分停用須另行處理。 | Sharing records show the remaining time and download count. You can select 10, 20, or 30 entries per page and apply a status filter.<br><br>1. In 「檔案分享」, check the master switch and 「分享中」 links at the top.<br>2. To stop one share, select 「停止分享」 for that record.<br>3. To pause all shares, use the master switch.<br>4. Check that the old QR cannot download files.<br><br>Downloaded DPK files and `initial.prefs` do not disappear from devices. Deactivate identities separately. |

## B006

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 時間與次數可同時限制，先達到者即停止新下載；開啟 QR 本身不占下載次數。 | 時間與次數可同時限制。任一限制先達上限，系統就會停止新下載。開啟 QR 本身不占下載次數。 | Time and count limits can apply together. The first limit reached stops new downloads. Opening the QR itself does not count as a download. |

## B007

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [分享紀錄狀態篩選](../../images/console-task-09-shares.png) | [分享紀錄狀態篩選](../../images/console-task-09-shares.png) | [Sharing record status filter](../../images/console-task-09-shares.png) |

## B008

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 17：每頁筆數、狀態與下載用量；截圖顯示已結束的紀錄。 | 圖 17：每頁筆數、狀態與下載用量。截圖顯示已結束的紀錄。 | Figure 17: Page size, status, and download usage. The screenshot shows ended records. |

## B009

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [分享下載總開關](../../images/console-task-09b-master-switch.png) | [分享下載總開關](../../images/console-task-09b-master-switch.png) | [Master download sharing switch](../../images/console-task-09b-master-switch.png) |

## B010

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 18：總開關影響所有分享；停止單筆時請到該筆紀錄操作。 | 圖 18：總開關影響所有分享。停止單筆時請到該筆紀錄操作。 | Figure 18: The master switch affects all shares. To stop one share, use its record. |

## B011

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **操作後核對與疑難排解** | **操作後核對與疑難排解** | **Check results and troubleshoot** |

## B012

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| \| 現象 \| 先核對 \| 下一步 \|<br>\| --- \| --- \| --- \|<br>\| 管理頁顯示 worker 無法取得資料 \| Windows 已登入；`Manage-TakControlWorkers.ps1 -Action Status` \| 用 `-Action Start` 啟動；再查 `runtime/tak-cert-control/worker.log` 或 `runtime/share-control/worker.log` \|<br>\| Android 掃 QR 只顯示下載通知 \| 同熱點、mDNS、分享期限／次數、完整 `tak://` 或 `icu://` 連結 \| 到 ATAK／ICU 核對真正匯入結果；同名 DPK 可先清除舊副本 \|<br>\| ATAK 已連線但看不到 Vx 套件 \| Data Packages → Download 選對 TAK Server；8443 可達 \| 查 TAK 套件是否只剩一筆、`tool=public` 與 `missionpackage`；不要改走一般 Vx QR \|<br>\| ICU 顯示外部設定但沒有影像 \| Type、SSL、Stream Path 和小隊帳密；預設 RTSP 用 `takbox.local:8554` 且 `Use SSL?` 不勾選，RTSPS 用 `takbox.local:8322` 並勾選 SSL \| 啟動發布後查 MediaMTX 線上路徑；避免兩台使用相同 `VIDEO_1` 路徑 \|<br>\| ICU 在室內 GPS 失效後中斷 \| 核對 Disable Local Broadcasting 是否勾選；使用者曾觀察到未勾選時停止發布 \| 重新分享並匯入新版 ICU QR，再確認設定值及 MediaMTX 線上路徑；此情境仍待複測 \|<br>\| Vx 不再提示密碼但仍可登入 \| 已註冊 Mumble 身分可能仍有效 \| 到 Mumble 管理頁移除註冊身分，再用未註冊裝置驗證新密碼 \|<br>\| 公開影像在外網打不開 \| 目前只有熱點入口 \| 待 FQDN、HTTPS、NAT、ICE 與防火牆完成後另做外網驗收 \| | \| 現象 \| 先核對 \| 下一步 \|<br>\| --- \| --- \| --- \|<br>\| 管理頁顯示 worker 無法取得資料 \| 確認 Windows 已登入。執行 `Manage-TakControlWorkers.ps1 -Action Status`。 \| 用 `-Action Start` 啟動。再查 `runtime/tak-cert-control/worker.log` 或 `runtime/share-control/worker.log`。 \|<br>\| Android 掃 QR 只顯示下載通知 \| 核對相同熱點、mDNS、分享期限與次數，以及完整 `tak://` 或 `icu://` 連結。 \| 到 ATAK／ICU 核對實際匯入結果。同名 DPK 可先清除舊副本。 \|<br>\| ATAK 已連線但看不到 Vx 套件 \| 在 Data Packages → Download 確認選對 TAK Server。確認 8443 可達。 \| 查 TAK 套件是否只剩一筆。核對 `tool=public` 與 `missionpackage`。不要改用一般 Vx QR。 \|<br>\| ICU 顯示外部設定但沒有影像 \| 核對 Type、SSL、Stream Path 和小隊帳密。預設 RTSP 使用 `takbox.local:8554`，且 `Use SSL?` 不勾選。若設定為 RTSPS，使用 `takbox.local:8322` 並啟用 SSL。 \| 啟動發布後，查 MediaMTX 線上路徑。避免兩台使用相同 `VIDEO_1` 路徑。 \|<br>\| ICU 在室內 GPS 失效後中斷 \| 核對 Disable Local Broadcasting 是否勾選。使用者曾觀察到未勾選時停止發布。 \| 重新分享並匯入新版 ICU QR。再確認設定值與 MediaMTX 線上路徑。此情境仍待複測。 \|<br>\| Vx 不再提示密碼但仍可登入 \| 已註冊 Mumble 身分可能仍有效。 \| 到 Mumble 管理頁移除註冊身分。再用未註冊裝置驗證新密碼。 \|<br>\| 公開影像在外網打不開 \| 本節原始驗收只涵蓋熱點入口。 \| 待 FQDN、HTTPS、NAT、ICE 與防火牆完成後，另做外網驗收。 \| | \| Symptom \| First check \| Next action \|<br>\| --- \| --- \| --- \|<br>\| The management page cannot read worker data \| Check that Windows is logged in. Run `Manage-TakControlWorkers.ps1 -Action Status`. \| Start with `-Action Start`. Then read `runtime/tak-cert-control/worker.log` or `runtime/share-control/worker.log`. \|<br>\| Android only shows a download notification after a QR scan \| Check the same hotspot, mDNS, sharing limits, and complete `tak://` or `icu://` link. \| Check the actual import in ATAK/ICU. You can first delete an old DPK copy with the same name. \|<br>\| ATAK connects but cannot see the Vx package \| Check the selected TAK Server in Data Packages → Download. Check access to 8443. \| Check that only one TAK package remains. Check `tool=public` and `missionpackage`. Do not use a general Vx QR. \|<br>\| ICU shows external settings without video \| Check Type, SSL, Stream Path, and squad credentials. Default RTSP uses `takbox.local:8554` with `Use SSL?` clear. RTSPS uses `takbox.local:8322` with SSL enabled. \| After publication starts, check the MediaMTX online path. Prevent two devices from using the same `VIDEO_1` path. \|<br>\| ICU stops when indoor GPS fails \| Check Disable Local Broadcasting. A user observed stopped publication with this checkbox clear. \| Share and import a new ICU QR. Then check settings and the MediaMTX online path. This case still needs retesting. \|<br>\| Vx logs in without a password prompt \| A registered Mumble identity may still be valid. \| Delete the registered identity in Mumble management. Then test the new password with an unregistered device. \|<br>\| Public video does not open from the internet \| The original acceptance scope here covers only the hotspot entry point. \| After FQDN, HTTPS, NAT, ICE, and firewall work is complete, test internet access separately. \| |

## B013

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [返回任務索引](../../tak-server/console-task-manual.md) | [返回任務索引](../../tak-server/console-task-manual.md) | [Return to the task index](../../tak-server/console-task-manual.md) |
