# 分享與疑難排解

[返回任務索引](index.md)

<a id="task-09"></a>

## 任務九　檢視與停止設定檔分享

分享紀錄會顯示剩餘時間與下載次數。可切換每頁 10、20、30 筆，也可使用狀態篩選。

1. 在「檔案分享」核對頁首總開關及「分享中」連結。
2. 若要停止單筆分享，按該筆紀錄的「停止分享」。
3. 若要暫停全部分享，使用總開關。
4. 確認舊 QR 無法再下載。

已下載到裝置的 DPK 或 `initial.prefs` 不會自動消失。身分停用須另行處理。

時間與次數可同時限制。任一限制先達上限，系統就會停止新下載。開啟 QR 本身不占下載次數。

![分享紀錄狀態篩選](../../images/console-task-09-shares.png)

圖 17：每頁筆數、狀態與下載用量。截圖顯示已結束的紀錄。

![分享下載總開關](../../images/console-task-09b-master-switch.png)

圖 18：總開關影響所有分享。停止單筆時請到該筆紀錄操作。

## 操作後核對與疑難排解

| 現象 | 先核對 | 下一步 |
| --- | --- | --- |
| 管理頁顯示 worker 無法取得資料 | 確認 Windows 已登入。執行 `Manage-TakControlWorkers.ps1 -Action Status`。 | 用 `-Action Start` 啟動。再查 `runtime/tak-cert-control/worker.log` 或 `runtime/share-control/worker.log`。 |
| Android 掃 QR 只顯示下載通知 | 核對相同熱點、mDNS、分享期限與次數，以及完整 `tak://` 或 `icu://` 連結。 | 到 ATAK／ICU 核對實際匯入結果。同名 DPK 可先清除舊副本。 |
| ATAK 已連線但看不到 Vx 套件 | 在 Data Packages → Download 確認選對 TAK Server。確認 8443 可達。 | 查 TAK 套件是否只剩一筆。核對 `tool=public` 與 `missionpackage`。不要改用一般 Vx QR。 |
| ICU 顯示外部設定但沒有影像 | 核對 Type、SSL、Stream Path 和小隊帳密。預設 RTSP 使用 `takbox.local:8554`，且 `Use SSL?` 不勾選。若設定為 RTSPS，使用 `takbox.local:8322` 並啟用 SSL。 | 啟動發布後，查 MediaMTX 線上路徑。避免兩台使用相同 `VIDEO_1` 路徑。 |
| ICU 在室內 GPS 失效後中斷 | 核對 Disable Local Broadcasting 是否勾選。使用者曾觀察到未勾選時停止發布。 | 重新分享並匯入新版 ICU QR。再確認設定值與 MediaMTX 線上路徑。此情境仍待複測。 |
| Vx 不再提示密碼但仍可登入 | 已註冊 Mumble 身分可能仍有效。 | 到 Mumble 管理頁移除註冊身分。再用未註冊裝置驗證新密碼。 |
| 公開影像在外網打不開 | 本節原始驗收只涵蓋熱點入口。 | 待 FQDN、HTTPS、NAT、ICE 與防火牆完成後，另做外網驗收。 |

[返回任務索引](index.md)
