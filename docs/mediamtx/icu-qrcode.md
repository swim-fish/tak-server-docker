# TAK ICU 7.5.1 的 QR Code 設定

此格式根據測試裝置上 `com.atakmap.takcam` 7.5.1 APK 的 `AndroidManifest.xml`、`ICUCamera` 與 `ICUPrefs` 程式，以及 ICU 自行匯出的 `local.prefs` 核對。裝置隨附的《ATAK TAK ICU User Guide》說明手動設定，但沒有列出這個 QR 佈建格式。下列格式的實機驗證狀態見[驗證紀錄](../validation/2026-09-23-icu-qrcode.md)。

## 入口與檔案格式

ICU 接受 Android `ACTION_VIEW` 的 `icu:` scheme。APK 中 `ICUCamera` 只在 URI host 為 `download` 時讀取 `url` 查詢參數，以 HTTP(S) GET 下載成 ICU 專屬資料夾的 `initial.prefs`，再解析為 ICU 自己的偏好設定。因此 QR Code 應編碼**整行 URI**，而不是直接把 XML 文字放在 QR Code：

```text
icu://download?url=<完整百分比編碼的 HTTP(S) 設定檔 URL>
```

目前建議由[引導式佈建](../plans/guided-provisioning.md)建立標準或 Advanced ICU 設定，再產生短效分享。以目前本機 `.env` 的主機映射為例，每筆 URL 是 `http://takbox.local:10065/d/<token>`，QR 內容形如：

```text
icu://download?url=http%3A%2F%2Ftakbox.local%3A10065%2Fd%2FTOKEN
```

`download` 是 `icu:` URI 的 **host**；HTTP 檔案路徑是 `/d/<token>`，由管理頁實際產生。不能寫成 `icu:///download`。下載回應須為 `200`；APK 以 `HttpURLConnection` 取得內容，未實作 DPK 解壓或其他路由。每台裝置須與 Windows 熱點連線，並能把 `takbox.local` 解析到熱點位址；這個流程不使用 USB 或 ADB reverse。

本機 ICU 匯出的 XML 是下列結構；布林值使用 `class java.lang.Boolean`，通訊埠是字串，不是整數：

```xml
<?xml version="1.0" encoding="utf-8"?>
<preferences>
  <preference version="1" name="ICU">
    <entry key="broadcast_destination_type" class="class java.lang.String">RTSP-Push (Video Management System)</entry>
    <entry key="videoServerIP" class="class java.lang.String">takbox.local</entry>
    <entry key="videoServerPort" class="class java.lang.String">8322</entry>
    <entry key="videoServerPath" class="class java.lang.String">live/</entry>
    <entry key="videoServerSSL" class="class java.lang.Boolean">true</entry>
    <entry key="videoServerUsername" class="class java.lang.String">atak-publisher</entry>
    <entry key="videoServerPassword" class="class java.lang.String">[由本機密碼檔產生]</entry>
  </preference>
</preferences>
```

`videoServerPassword` 由 `runtime/secrets/mediamtx_publish_password` 讀入，圖中只是佔位文字；實際產出的 XML 含密碼，且不應加入 Git 或公開散布。QR 本身只含下載網址，不直接含密碼，但持有 QR 且能連到下載端點的裝置也能取得密碼。這些值是**發布**設定；觀看端仍須用 MediaMTX 的 `atak-viewer` 帳號與實際串流路徑。ICU 載入器將 XML 的 `entry` 寫入 ICU App 的 default `SharedPreferences`，不會寫入 ATAK App 的設定。

## 產生 QR Code

手動產生器只接受 HTTP(S) URL，輸出目錄預設為版控忽略的 `runtime/packages/icu/`。密碼必須從本機檔案讀取，不能直接在命令列輸入。需要 `qrcode` 8.2 與 Pillow；以下在 `runtime/` 建立隔離的 Python 環境：

```powershell
python -m venv runtime/icu-qr/.venv
./runtime/icu-qr/.venv/Scripts/python.exe -m pip install "qrcode[pil]==8.2"
./runtime/icu-qr/.venv/Scripts/python.exe ./scripts/build_icu_qr.py `
  --host takbox.local `
  --port 8322 `
  --stream-path live/ `
  --username atak-publisher `
  --profile-url http://takbox.local:8765/download `
  --password-file runtime/secrets/mediamtx_publish_password `
  --allow-http-password
```

產物是 `initial.prefs`、`icu-setup-uri.txt` 與 `icu-setup.png`。前者含密碼；`runtime/` 被 `.gitignore` 排除。搬移前產生的舊 QR 仍指向 `/download`，只適用於下方舊單檔伺服器；使用分享管理頁時應掃描該頁新產生的 QR。由裝置上的系統相機或能開啟 `icu:` 自訂連結的掃碼程式開啟 QR。掃描後必須**點相機顯示的完整 `icu://download?...` 連結**；只從最近使用的 App 或桌面圖示開啟 ICU 不會觸發下載。ATAK 自身的 `tak:` QR 入口與 ICU 的 `icu:` 入口不同，不能互換。

## 手動單檔下載伺服器（舊測試方式）

分享管理頁已提供相同的 ICU 下載入口與限時／限次控制。只有重現舊測試時才使用本節；先執行 `docker compose --profile sharing stop share-public`，避免占用 TCP 8765。

在 Windows 熱點已啟用、`takbox.local` mDNS 可從裝置解析時，分別開兩個終端機執行：

```powershell
# 終端機 A：需要時才要求 UAC，僅開放熱點介面的 TCP 8765。
.\scripts\Install-SharePortalFirewall.ps1

# 終端機 B：只綁定熱點 IP、只回應 GET/HEAD /download。
python .\scripts\serve_icu_profile.py --bind 192.168.137.1 `
  --allow-subnet 192.168.137.0/24 `
  --profile runtime/packages/icu/initial.prefs --allow-http-password
```

防火牆腳本先確認熱點位址及介面，再建立只允許 `192.168.137.0/24` 存取 `192.168.137.1:8765/TCP` 的暫時規則；在其提高權限的視窗按 Ctrl+C 會移除本次規則。舊 Python 伺服器另行檢查來源子網，只提供 `/download`，按 Ctrl+C 停止。測試後停止伺服器與防火牆工作階段，並視需要刪除 `runtime/packages/icu/initial.prefs`。

**此方案的 HTTP 應用層沒有加密。** 它只適用於操作人員控制的短暫本機熱點測試，且每台能連到熱點的裝置都可能請求設定檔。正式多使用者佈建應改用 ICU 能信任的 HTTPS 網址；`.local` 的內部 CA 憑證是否受獨立 ICU App 信任，必須先在 Android 實機驗證，不能以 ATAK 內的 TAK Server 信任設定推定。

## 早期 USB／ADB reverse 驗證

早期測試使用 USB／ADB reverse，讓單一裝置的 `127.0.0.1:8765` 對應到電腦。此方式無法直接用於另一台沒有設定 reverse 的裝置；目前應優先使用上方的 `takbox.local` 方案。早期使用 `--stream-path live/qr-verify/` 產生可辨識的測試路徑；ICU 將再接上自己的串流名稱：

```powershell
./runtime/icu-qr/.venv/Scripts/python.exe ./scripts/build_icu_qr.py `
  --host takbox.local `
  --port 8322 `
  --stream-path live/qr-verify/ `
  --profile-url http://127.0.0.1:8765/initial.prefs
$deviceSerial = 'YOUR_DEVICE_SERIAL'
adb -s $deviceSerial reverse tcp:8765 tcp:8765
python -m http.server 8765 --bind 127.0.0.1 --directory runtime/packages/icu
```

每台裝置都要建立自己的 ADB reverse；同時連接多台時必須明確指定序號。開著 HTTP server 終端機，於另一個終端機確認 `adb -s $deviceSerial reverse --list`，也可從該裝置執行 `curl -I http://127.0.0.1:8765/initial.prefs` 驗證回應為 `200 OK`。以 Android 相機掃描電腦顯示的 `runtime/packages/icu/icu-setup.png`，選擇開啟 TAK ICU。成功後檢查 ICU 的 Server IP、Port、Stream Path、Use SSL?、Username；若密碼未保存，由使用者在 ICU 輸入現有發布密碼。啟動影像後，MediaMTX 應記錄 `live/qr-verify/<串流名稱>` 的 RTSPS 發布，再用讀取帳號驗證影像內容。測試後把 Stream Path 改回 `live/`，並執行 `adb -s $deviceSerial reverse --remove tcp:8765`；HTTP server 用 Ctrl+C 停止。

**驗收要同時看到 ICU 欄位改變、MediaMTX 發布紀錄及讀取端收到影像。** APK 在 HTTP 下載完成時先顯示 `Externally configured using the QR Code`，接著才解析 `initial.prefs`；單看提示訊息不足以證明每個欄位正確載入。

## DPK 邊界

ATAK DPK 可以交付 TAK 連線、憑證及 ATAK 自身偏好設定；ICU 是另一個 Android App，這版 APK 沒有宣告接收 DPK 檔案的 activity。把上述 `entry` 放進 ATAK `.pref`，不能據此認定會寫入 ICU 的 `SharedPreferences`。若要單一交付物，可在 DPK 中附上**供使用者另行掃描**的 ICU QR 圖片及說明，但仍需 ICU 的 `icu:` 入口完成第二步。
