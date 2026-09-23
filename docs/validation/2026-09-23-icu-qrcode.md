# 2026-09-23 TAK ICU QR Code 驗證

## 靜態證據

- 測試裝置的 `com.atakmap.takcam` 是 `7.5.1 (a02441d)`；`AndroidManifest.xml` 的 `ICUCamera` activity 接受 `ACTION_VIEW` 與 `icu:` scheme。
- `ICUCamera` 讀取 URI host `download` 與 `url` 查詢參數，下載到 ICU 私有外部資料夾的 `initial.prefs`。HTTP 狀態需為 `200`，下載後呼叫 `ICUPrefs` 載入器。
- `ICUPrefs` 讀取 `<preferences><preference name="ICU"><entry key="..." class="...">值</entry></preference></preferences>`，支援 String、Boolean、Float、Integer、Long 與 String Set，並略過 `bestDeviceUID`。
- 從裝置唯讀取得 ICU 自己輸出的 `local.prefs`，確認 `broadcast_destination_type`、`videoServerIP`、`videoServerPort`、`videoServerPath`、`videoServerSSL`、`videoServerUsername` 的值與型別；原始檔含發布密碼，僅存於版控忽略的 `runtime/analysis/`，未加入文件。
- 裝置隨附的《ATAK TAK ICU User Guide》確認 ICU 手動設定流程，但未提供此 QR 格式；QR 格式依 APK 程式確認。

## 產物與實機驗收

- [x] 產生無密碼 `initial.prefs`、`icu-setup-uri.txt`、`icu-setup.png`。XML parser 確認欄位型別、值與未包含 `videoServerPassword`；獨立 `zxing-cpp` QR decoder 讀回的 URI 與輸出檔完全相同。
- [x] `adb reverse tcp:8765 tcp:8765` 後，裝置向 `127.0.0.1:8765/initial.prefs` 發出 GET，電腦端 Python HTTP server 記錄 `200`；這只驗證下載路徑，尚未代表 ICU 已套用設定。
- [x] 首次掃描後只開啟 ICU，欄位未改、伺服器無新的 GET；再次由 Samsung 相機**點擊顯示的 `icu://download?...` 連結**後，畫面顯示 `Externally configured using the QR Code`。裝置 ICU 自行匯出的 `local.prefs` 已變成 `RTSP-Push (Video Management System)`、`takbox.local:8322`、`live/qr-verify/`、`videoServerSSL=true`、`atak-publisher`。下載後 `initial.prefs` 已由 ICU 刪除。這是欄位實際套用的證據，不只依賴提示訊息。
- [x] 使用者以既有發布密碼啟動 RTSPS，MediaMTX 記錄 `live/qr-verify/VIDEO_1` 可用並正在發布。
- [x] 獨立 `atak-viewer` 以 TAK Root CA 驗證 RTSPS，從 `live/qr-verify/VIDEO_1` 取得 3 秒影像。第一台裝置的 ADB reverse 與測試 HTTP server 已清除；ICU 路徑仍須由使用者改回 `live/`。

## 第二台裝置

- 第二台測試裝置也安裝 ICU 7.5.1。第一次掃碼未套用設定；其 `local.prefs` 只有 RTSP-Push 類型與 `videoServerSSL=false`，沒有 QR 內的主機、通訊埠或路徑。
- 測試 QR 的設定檔 URL 是 `http://127.0.0.1:8765/initial.prefs`。第一次只在第一台裝置建立 ADB reverse，第二台沒有此轉送，因此不能從自己的 `127.0.0.1` 讀到電腦檔案。
- 已對第二台建立專屬 ADB reverse；裝置內 `curl -I` 回應 `200 OK`。使用者再次掃碼後回報 `Externally configured` 提示與主機、通訊埠、路徑及 SSL 欄位都正確。當時尚未驗證第二台的實際發布影像。

## 不使用 ADB reverse 的 DNS 下載方案

- [x] 將 QR 的設定檔 URL 改為 `http://takbox.local:8765/download`；`icu://download?url=...` 仍為 ICU 啟動 URI。專用伺服器只回應 GET/HEAD `/download`，綁定 `192.168.137.1:8765`，並限制來源為熱點子網。
- [x] 從本機 `runtime/secrets/mediamtx_publish_password` 產生含 `videoServerPassword` 的 XML；離線 XML 檢查確認密碼與來源檔相同，獨立 QR decoder 確認圖片內容與 URI 檔相同。密碼值沒有寫入文件或命令輸出。
- [x] 第一台 Android 裝置沒有設定 ADB reverse。`takbox.local` 解析到 `192.168.137.1` 並可 ping；裝置直接對 `/download` 發送 HEAD，收到 `200 OK` 與 `Content-Length`，證明 DNS 和 TCP 路徑可達，且這項檢查沒有下載密碼內容。
- [x] 經使用者明確授權熱點內 HTTP 傳輸後，裝置直接對 `takbox.local` 的 `/download` 發送 GET；伺服器記錄 `200`，裝置端只統計回應長度而未顯示內容。這證明可從其他同網段裝置下載，尚不代表 ICU App 已套用設定。
- [x] 使用者第一次掃碼顯示 Fail。檢查時 TCP 8765 沒有 listener；前一次網路測試後已停止下載伺服器。重新啟動後，裝置直接對 `takbox.local:8765/download` 的 HEAD 收到 `200 OK`。
- [x] 使用者從第二台熱點裝置以系統相機點完整的 `icu://download?...` 連結；專用伺服器記錄 GET `/download` 回應 `200`。ICU 顯示 `Externally configured`，使用者確認欄位已更新。
- [x] 使用者直接啟動 ICU RTSPS，沒有重新輸入發布密碼。MediaMTX 記錄 `live/VIDEO_1` 正在發布，影像軌為 MPEG-TS。獨立 `atak-viewer` 以 TAK Root CA 驗證 RTSPS 並取得 2 秒影像。

目前本機熱點測試使用 HTTP，應用層沒有加密。含密碼的設定檔和 QR 皆位於版控忽略的 `runtime/icu-qr/`。完成掃碼與影像驗證後已停止下載伺服器，TCP 8765 沒有持續監聽；沒有成功建立新的 Windows 防火牆規則。若再次掃碼，需先短暫啟動下載伺服器。

靜態證據不等於實機匯入成功；上列動態項目完成後才能宣稱 QR 佈建通過。測試程序見[ICU QR Code 格式](../mediamtx/icu-qrcode.md)。
