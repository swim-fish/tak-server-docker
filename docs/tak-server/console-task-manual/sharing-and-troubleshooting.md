# 分享與疑難排解

[返回任務索引](../console-task-manual.md)

<a id="task-09"></a>

## 任務九　檢視與停止設定檔分享

1. 在「檔案分享」看頁首總開關及「分享中」連結；分享紀錄可切換每頁 10、20、30 筆與狀態篩選。
2. 要停止單筆，按「停止分享」；全部暫停則用總開關。分享中會顯示剩餘時間與下載次數。
3. 確認舊 QR 無法再下載。已下載到裝置的 DPK 或 `initial.prefs` 不會自動消失，身分停用須另行處理。

時間與次數可同時限制，先達到者即停止新下載；開啟 QR 本身不占下載次數。

![分享紀錄狀態篩選](../../images/console-task-09-shares.png)

圖 17：每頁筆數、狀態與下載用量；截圖顯示已結束的紀錄。

![分享下載總開關](../../images/console-task-09b-master-switch.png)

圖 18：總開關影響所有分享；停止單筆時請到該筆紀錄操作。

## 操作後核對與疑難排解

| 現象 | 先核對 | 下一步 |
| --- | --- | --- |
| 管理頁顯示 worker 無法取得資料 | Windows 已登入；`Manage-TakControlWorkers.ps1 -Action Status` | 用 `-Action Start` 啟動；再查 `runtime/tak-cert-control/worker.log` 或 `runtime/share-control/worker.log` |
| Android 掃 QR 只顯示下載通知 | 同熱點、mDNS、分享期限／次數、完整 `tak://` 或 `icu://` 連結 | 到 ATAK／ICU 核對真正匯入結果；同名 DPK 可先清除舊副本 |
| ATAK 已連線但看不到 Vx 套件 | Data Packages → Download 選對 TAK Server；8443 可達 | 查 TAK 套件是否只剩一筆、`tool=public` 與 `missionpackage`；不要改走一般 Vx QR |
| ICU 顯示外部設定但沒有影像 | Type、SSL、`takbox.local:8322`、Stream Path 和小隊帳密 | 啟動發布後查 MediaMTX 線上路徑；避免兩台使用相同 `VIDEO_1` 路徑 |
| ICU 在室內 GPS 失效後中斷 | 核對 Disable Local Broadcasting 是否勾選；使用者曾觀察到未勾選時停止發布 | 重新分享並匯入新版 ICU QR，再確認設定值及 MediaMTX 線上路徑；此情境仍待複測 |
| Vx 不再提示密碼但仍可登入 | 已註冊 Mumble 身分可能仍有效 | 到 Mumble 管理頁移除註冊身分，再用未註冊裝置驗證新密碼 |
| 公開影像在外網打不開 | 目前只有熱點入口 | 待 FQDN、HTTPS、NAT、ICE 與防火牆完成後另做外網驗收 |

[返回任務索引](../console-task-manual.md)
