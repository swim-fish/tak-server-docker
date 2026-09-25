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
    <entry key="disableLocalBroadcast" class="class java.lang.Boolean">true</entry>
    <entry key="stream_resolution" class="class java.lang.String">3</entry>
    <entry key="stream_frame_rate" class="class java.lang.String">15</entry>
    <entry key="stream_bit_rate" class="class java.lang.String">900</entry>
    <entry key="display_coord_alt" class="class java.lang.String">0</entry>
  </preference>
</preferences>
```

`videoServerPassword` 由 `runtime/secrets/mediamtx_publish_password` 讀入，圖中只是佔位文字；實際產出的 XML 含密碼，且不應加入 Git 或公開散布。QR 本身只含下載網址，不直接含密碼，但持有 QR 且能連到下載端點的裝置也能取得密碼。這些值是**發布**設定；觀看端仍須用 MediaMTX 的 `atak-viewer` 帳號與實際串流路徑。ICU 載入器將 XML 的 `entry` 寫入 ICU App 的 default `SharedPreferences`，不會寫入 ATAK App 的設定。

上方 XML 是舊共用帳號的格式範例。控制台引導式佈建產生的小隊 QR 使用該小隊帳號，例如 `icu-alpha`，並在 `videoServerPath` 寫入選定的初始路徑。MediaMTX 依帳號限制小隊前綴；同隊裝置匯入同一張仍可下載的 QR 後，可在 ICU 手動把 `live/alpha/1/` 改成 `live/alpha/2/`，不用更換帳密或再掃 QR。ICU 會把 `VIDEO_1` 附在路徑後方；控制台應看到 `live/alpha/2/VIDEO_1`。其他小隊路徑會被拒。QR 的時間／下載次數仍照分享設定計算；同時發布的裝置不得使用同一完整路徑。[實機與伺服器驗證](../validation/2026-09-25-icu-squad-path-scope.md)。

## 室內定位與影像設定

依照裝置上 ICU 7.5.1 APK 的 `broadcast_prefs`、`video_prefs`、`display_prefs` 資源，以及 ICU 自行匯出的 `local.prefs`，下表設定可用相同的 XML `entry` 格式寫入。新產生的 ICU QR（包含引導式佈建、小隊重新分享與手動產生器）預設套用右欄值；**已建立的分享是當時設定檔的快照，需重新產生 QR 才會套用**。

| 畫面項目 | XML key／型別 | 可用值與本專案預設 |
| --- | --- | --- |
| Disable Local Broadcasting | `disableLocalBroadcast`／Boolean | `true`＝勾選；預設勾選。室內 GPS 失效時，使用者觀察到未勾選會使發布中斷；此設定仍需在實機以 GPS 失效情境複測。 |
| Resolution（串流與 TS 錄影） | `stream_resolution`／String | `0` 最低、`1` 240p、`2` 480p、`3` 720p、`4` 裝置可用最高；預設 `3`。 |
| TS Frame Rate（串流與 TS 錄影） | `stream_frame_rate`／String | 可用影格率依相機而異；已匯出的裝置值為 `15`，本專案預設 `15` fps。 |
| Stream Bit Rate | `stream_bit_rate`／String | `400`、`700`、`900`、`2000`、`3000` kbps；預設 `900` kbps。 |
| Altitude Display | `display_coord_alt`／String | `0` m MSL、`1` m HAE、`2` ft MSL、`3` ft HAE；預設 `0`（公尺、平均海平面）。 |

### 實機設定畫面

下列圖片由使用者提供的 ICU 實機截圖**直接裁切設定區域**，未重繪或更動選項內容。點選圖片可開啟較大的版本。

<a href="../images/icu-disable-local-broadcasting.jpg"><img src="../images/icu-disable-local-broadcasting.jpg" alt="TAK ICU 廣播設定中已勾選 Disable Local Broadcasting" width="420"></a>

圖 1：使用者在室內 GPS 失效時觀察到，未勾選 **Disable Local Broadcasting** 可能使影像發布中斷；上圖是勾選後的畫面。這是使用者觀察，仍需以同一裝置重新匯入 QR 並在 GPS 失效情境下複測。

<a href="../images/icu-stream-quality-preferences.jpg"><img src="../images/icu-stream-quality-preferences.jpg" alt="TAK ICU 影像設定顯示 Resolution、TS Frame Rate 與 Stream Bit Rate" width="420"></a>

圖 2：串流畫質使用 `Resolution`、`TS Frame Rate` 和 `Stream Bit Rate`。下方的 `MP4 Resolution` 與 `MP4 Frame Rate` 是本機 MP4 錄影設定。畫面只顯示選項入口；**720p／15 fps／900 kbps 是新 QR 設定檔的值，並非這張截圖中可直接讀出的選取值**。

<a href="../images/icu-display-preferences.jpg"><img src="../images/icu-display-preferences.jpg" alt="TAK ICU 顯示設定顯示 Coordinate Display 與 Altitude Display" width="420"></a>

圖 3：`Altitude Display` 可選公尺或英尺；`Coordinate Display` 選的是座標格式。新 QR 指定 `m MSL`，保留裝置原有的座標格式。

`Coordinate Display` 使用另一個鍵 `display_coord_sys`，控制 DD、DM、DMS、UTM、MGRS 等**座標格式**，不是公制／英制選擇；產生器不覆蓋裝置的座標格式。畫面上的 `MP4 Resolution`（`resolution`）和 `MP4 Frame Rate`（`frame_rate`）只管 MP4 本機錄影，不能拿來調整 RTSPS 串流。`Broadcast Port`、UDP Address／TTL、RTSP Server IP／Port／Path／SSL 等也有偏好設定鍵，但部分欄位在 RTSP-Push 模式停用或與目前的 RTSPS 伺服器設定無關，因此 QR 只寫入本流程所需的項目。

手動產生器可用 `--stream-resolution`、`--stream-frame-rate`、`--stream-bit-rate` 與 `--altitude-display` 調整；`--allow-local-broadcast` 可取消預設勾選。影像品質與頻寬會一起變動，且 720p／指定影格率仍受手機相機能力限制。若 ICU 已在發布，重新掃描 QR 後應停止並重新啟動串流，再到 ICU 設定頁確認選項已變更。

### 頻寬估算

新 QR 預設 `900 kbps` 為影像目標位元率。單條串流持續發布一小時，單算影像約 `900 × 3600 ÷ 8 = 405 MB`；若先保留 20% 作為協定開銷及波動的規劃餘裕，約 **1.08 Mbps 上傳、486 MB／小時**。這是估算，並非實測；音訊、Wi-Fi 重傳與瞬間位元率變化可能增加流量。解析度及影格率會影響相同位元率下的畫質與編碼負擔，不能單靠「720p」推算固定頻寬。每多一位觀看者，MediaMTX 還需要額外的輸出頻寬；若不轉碼，可先以約一條相同位元率的串流估算。

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

在 `.env` 指定的 Windows 網路介面已啟用、`takbox.local` 可從裝置解析時，分別開兩個終端機執行：

```powershell
# 終端機 A：需要時才要求 UAC，僅開放設定介面的 TCP 8765。
.\scripts\Install-SharePortalFirewall.ps1

# 終端機 B：依 .env 綁定位址、只回應 GET/HEAD /download。
python .\scripts\serve_icu_profile.py `
  --profile runtime/packages/icu/initial.prefs --allow-http-password
```

防火牆腳本先確認 `.env` 的位址及介面，再建立只允許 `TAK_ALLOWED_SUBNET` 存取 `TAK_BIND_IP:8765/TCP` 的暫時規則；在其提高權限的視窗按 Ctrl+C 會移除本次規則。舊 Python 伺服器另行檢查來源子網，只提供 `/download`，按 Ctrl+C 停止。測試後停止伺服器與防火牆工作階段，並視需要刪除 `runtime/packages/icu/initial.prefs`。

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

每台裝置都要建立自己的 ADB reverse；同時連線多台時必須明確指定序號。開著 HTTP server 終端機，於另一個終端機確認 `adb -s $deviceSerial reverse --list`，也可從該裝置執行 `curl -I http://127.0.0.1:8765/initial.prefs` 驗證回應為 `200 OK`。以 Android 相機掃描電腦顯示的 `runtime/packages/icu/icu-setup.png`，選擇開啟 TAK ICU。成功後檢查 ICU 的 Server IP、Port、Stream Path、Use SSL?、Username；若密碼未保存，由使用者在 ICU 輸入現有發布密碼。啟動影像後，MediaMTX 應記錄 `live/qr-verify/<串流名稱>` 的 RTSPS 發布，再用讀取帳號驗證影像內容。測試後把 Stream Path 改回 `live/`，並執行 `adb -s $deviceSerial reverse --remove tcp:8765`；HTTP server 用 Ctrl+C 停止。

**驗收要同時看到 ICU 欄位改變、MediaMTX 發布紀錄及讀取端收到影像。** APK 在 HTTP 下載完成時先顯示 `Externally configured using the QR Code`，接著才解析 `initial.prefs`；單看提示訊息不足以證明每個欄位正確載入。

## DPK 邊界

ATAK DPK 可以交付 TAK 連線、憑證及 ATAK 自身偏好設定；ICU 是另一個 Android App，這版 APK 沒有宣告接收 DPK 檔案的 activity。把上述 `entry` 放進 ATAK `.pref`，不能據此認定會寫入 ICU 的 `SharedPreferences`。若要單一交付物，可在 DPK 中附上**供使用者另行掃描**的 ICU QR 圖片及說明，但仍需 ICU 的 `icu:` 入口完成第二步。
