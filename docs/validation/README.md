# 驗證索引

本區保存特定日期、版本與環境的證據，不等於每次啟動都重新驗證。日常操作以[文件首頁](../README.md)所列說明為準；目前版本／通訊埠以[參考表](../reference/versions-and-ports.md)為準。

## 已有證據

| 項目 | 結果與界線 | 紀錄 |
| --- | --- | --- |
| Windows mDNS | 主機與 Android 名稱解析曾通過；仍需在每個部署網段確認 | [2026-09-21](2026-09-21-windows-mdns.md) |
| TAK 與 DPK | 裝置憑證連線、群組與 CRL 撤銷測試 | [2026-09-21](2026-09-21-tak-server-dpk.md) |
| TAK 8443／8089 CRL | 歷史測試曾同時設定兩個 `crlFile`；目前 8443 未設 connector 欄位，但全域第一筆 CRL 仍進入預設 connector，且單張葉憑證撤銷後 8443 新連線遭拒 | [歷史測試](2026-09-23-tak-crl-8443.md)／[前後對照](2026-09-24-qr-e2e-revocation.md)／[程式路徑](2026-09-26-tak-crlfile-source-analysis.md) |
| 用戶端憑證控制台早期測試 | 臨時 CA 完成簽發／撤銷、群組讀回與 Flask 測試；當時尚未執行實機驗收，後續結果見 2026-09-24 紀錄 | [2026-09-23](2026-09-23-client-certificate-console.md) |
| Mumble TLS／頻道 | 服務與頻道可用；早期 40000 測試不可單獨證明 Vx 任務端點已更新 | [2026-09-21](2026-09-21-mumble-server.md) |
| Vx Local SD | 清除設定及重新安裝後仍未建立任務，撤回早期成功判斷 | [2026-09-22](2026-09-22-tak-vx-dpk.md#清除既有設定後重測) |
| Vx Server Download | Vx-only 任務、首次密碼提示、登入及加入頻道成功 | [下載實測](2026-09-22-tak-vx-dpk.md#tak-server-下載實測成功) |
| Vx 雙頻道 | 早期紀錄只證明兩條 session；使用者後續確認手機的雙頻道語音可用，尚未保存 UDP 與雙向按鍵紀錄 | [早期雙頻道結果](2026-09-22-tak-vx-dpk.md#雙頻道實測結果) |
| TAK／Vx／ICU 分離佈建 | TAK 憑證 QR 成功；Vx QR 一般匯入不建立 Mission，改由 TAK Server Download 建立四頻道並逐一加入；ICU QR 發布 RTSPS 成功 | [2026-09-23](2026-09-23-qr-tak-vx-icu.md) |
| 全新憑證 QR 與撤銷 | 清除 ATAK 資料後重新匯入、Vx 四頻道、ICU RTSPS、CRL 撤銷及實機重連；發現 ATAK Data Packages 需要 8443 可達 | [2026-09-24](2026-09-24-qr-e2e-revocation.md) |
| 中繼 CA 輪替前置驗證 | Root DB 缺少中繼 CA 紀錄；隔離副本補登／撤銷與 OpenSSL 鏈驗證通過，本機快照完成；尚未切換服務 | [2026-09-24](2026-09-24-ca-rotation-preflight.md) |
| CA 輪替前實機與群組基線 | 兩張短效憑證分組簽發並在兩台 Android 連線；同網段標記互見尚需排除本機傳播；群組移除與還原通過 | [2026-09-24](2026-09-24-ca-rotation-device-baseline.md) |
| 中繼 CA 切換與 Root CRL | 新鏈的 A 裝置 ATAK、Vx、8443 套件查詢通過；發布 Root CRL 後仍須移除舊 CA 直接信任錨，8089 才拒絕舊 Alpha TLS 握手 | [2026-09-25](2026-09-25-ca-rotation-cutover.md) |
| 20 分鐘裝置憑證到期 | 到期後 8089 新連線遭拒，既有連線仍可收發；使用者確認 ATAK 直到下次重新連線才無法使用 | [2026-09-26](2026-09-26-certificate-expiry-20m.md) |
| CA 輪替後 8443 舊憑證重測 | 原設定拒絕舊 Alpha；受控測試在第一筆 CRL 載入四份合併檔後，只替換 Root CRL，使舊 Alpha 從 HTTP 200 變成 TLS 遭拒。原設定已還原，不宣稱其已載入 Root CRL | [2026-09-26](2026-09-26-ca-rotation-8443-retest.md) |
| `.env` Wi-Fi 位址與 CA 控制台替換 | Wi-Fi 綁定、Android mDNS／TCP、控制台 CA 替換及 Root CRL 通過；批次 API 就緒逾時後人工復原，Android 新 DPK 驗收另記；防火牆 UAC 首次取消 | [2026-09-25](2026-09-25-wifi-env-ca-console.md) |
| 憑證控制台瀏覽器 | Chrome 在桌面、平板、手機寬度的清冊、篩選、詳細頁及群組頁通過唯讀互動驗證；附去識別截圖 | [2026-09-25](2026-09-25-certificate-browser.md) |
| 引導式批次憑證與 Vx 替換 | 兩張測試憑證合併註冊並由 API 讀回；伺服器固定名稱 Vx 套件替換及 metadata 讀回通過，Android 新套件待驗 | [2026-09-24](2026-09-24-guided-provisioning.md) |
| Mumble 單一類型 SAN | DNS-only／IP-only 搭配相符 Vx Address，P1／A1 均成功；不包含不相符 SAN 拒絕測試 | [SAN 實測](2026-09-22-mumble-san.md) |
| MediaMTX／TAK ICU | RTSP、RTSPS TCP 與 Compose 內 UDP 串流通過；ICU 7.5.1 經 RTSPS＋帳密實際發布，獨立讀取成功；跨 bridge UDP 待驗 | [2026-09-23](2026-09-23-mediamtx.md) |
| ATAK 觀看 ICU 影像 | ATAK 5.7.0.15 的自動 RTSPS 通告無法直接播放；手動 RTSP 加讀取帳密及 Reliable／TCP 後，實機顯示 1280×720 影像 | [2026-09-25](2026-09-25-atak-icu-viewer.md) |
| 一般設備發布網址與收流 | 控制台建立獨立身分；FFmpeg 模擬無人機經熱點入口以 RTSP／RTSPS TCP 發布，獨立讀取端各解碼 30 個影格；WebRTC 預覽顯示影像，停用後舊網址遭拒。實體無人機與外網未驗收 | [2026-09-25](2026-09-25-drone-synthetic-stream.md) |
| ICU 同隊共用 QR 與路徑隔離 | 同一 Alpha QR 匯入後，Android 手動改為 `live/alpha/2/` 並成功發布；Alpha 帳密對 Bravo 與非 ICU 路徑遭拒 | [2026-09-25](2026-09-25-icu-squad-path-scope.md) |
| TAK ICU QR Code | 依 ICU 7.5.1 APK 與原生 `local.prefs` 確認格式；`takbox.local` 含密碼 QR 已由第二台熱點裝置掃碼套用，ICU 無提示發布 RTSPS，獨立讀取端取得影像 | [2026-09-23](2026-09-23-icu-qrcode.md) |
| 分享與 Mumble 管理頁 | Compose 健康、限時／限次與單次下載、Flask 管理頁與 Mumble 唯讀清單通過；真實使用者刪除與密碼輪替未執行 | [2026-09-23](2026-09-23-share-portal.md) |
| 密碼輪替與註冊 | 已註冊 Vx 仍可登入；取消註冊後重現密碼提示 | [密碼測試](2026-09-22-tak-vx-dpk.md#更換-mumble-密碼以重現提示畫面) |
| 公開儲存庫衛生 | 本機內容稽核通過；最終發布檢查待文件提交後重跑 | [2026-09-22](2026-09-22-public-repo-hygiene.md) |
| 文件重整 | 分類、來源、連結、圖片及語言驗收 | [2026-09-22](2026-09-22-docs-refactor.md) |

## 工具測試的範圍

Mumble 前景防火牆既有測試涵蓋介面未啟用、建立失敗清理、Ctrl+C／pipeline 中斷及保留其他規則等情境；不代表所有 Windows 強制關閉方式都能清理。

互動式取消註冊工具已有選取及後端保護檢查，曾唯讀列出實機註冊及驗證備份。先前一次性實機取消註冊已成功；新版互動工具的破壞性端到端操作未因此自動列為通過。操作限制見[Mumble 使用者](../mumble/users.md)。

測試程式：[防火牆](../../scripts/tests/Test-MumbleFirewallSession.ps1)、[使用者管理](../../scripts/tests/test_manage_mumble_users.py)。腳本實際名稱及可用參數以 repository 為準。

## 待完成的實機驗收

需要第二個用戶端。先準備兩個可辨識的測試身分，並記錄伺服器頻道。開始前確認雙方都能登入，並依序記錄：

1. Primary 雙向按住 PTT 傳送／接收，確認放開後停止。
2. Alternate 重複測試，確認沒有送到另一個未選頻道。
3. VS1／VS2 與 PTT1／PTT2 指派符合預期。
4. 核對 UDP 媒體是否實際通過；受阻時另測 TCP fallback，不把登入成功當成 UDP 通過。
5. 測斷線重連、短暫切換網路與延遲／丟包；保留去識別的結果。
6. 完成同 UUID 任務重複下載、新 UUID 同名任務與既有密碼快取的測試。

整合 TAK＋Vx 包的 Server Download、Linux、MediaMTX 跨網路 UDP、ATAK 自動 RTSPS 通告替代方式、公開 8446／ACME 及資料庫升級尚未驗收，見[後續計畫](../plans/roadmap.md)。
