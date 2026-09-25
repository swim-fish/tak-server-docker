# TAK ICU 7.5.1 設定檔與偏好設定盤點

盤點日期：2026-09-25。來源為本機測試 APK `runtime/analysis/takcam.apk`（套件 `com.atakmap.takcam`）、其編譯後的 `res/xml` 設定畫面，以及 ICU 自行匯出的 `runtime/analysis/icu-local-after-qr.prefs`。匯出檔含發布密碼；**本紀錄只列鍵名、型別與公開的選項值，不複製帳號、密碼、IP 或整份匯出檔**。

## 設定檔位置與用途

| 位置 | 用途 |
| --- | --- |
| `runtime/analysis/takcam.apk` | 裝置上的 ICU 7.5.1 APK；`res/xml` 是設定畫面定義，不是可直接匯入的 XML。 |
| APK `res/3Q.xml`／`xml/prefs` | 主設定頁、相機選擇及各子頁入口。 |
| APK `res/UT.xml`／`xml/broadcast_prefs` | 廣播、UDP、RTSP 與 RTSP-Push 設定。 |
| APK `res/aD.xml`／`xml/video_prefs` | 串流、TS／MP4 錄影及上傳設定。 |
| APK `res/lf.xml`／`xml/control_prefs` | 操作控制設定。 |
| APK `res/lq.xml`／`xml/display_prefs` | 座標、高度與方位角顯示。 |
| APK `res/8W.xml`／`xml/remote_connect_prefs` | 遠端控制畫面及其顯示選項。 |
| APK `res/zz.xml`／`xml/provider_paths` | Android FileProvider 可分享路徑的系統設定；不是 ICU 使用者偏好設定。 |
| `runtime/analysis/icu-local.prefs`、`icu-local-after-qr.prefs` | ICU 匯出的完整本機偏好設定快照，供核對 XML `entry` 的型別；含機密值，不納入 Git。 |
| `runtime/analysis/icu-second-before.prefs`、`icu-second-after-qr.prefs` | 第二台裝置匯入前後的比較快照；含機密值，不納入 Git。 |
| `runtime/packages/icu/initial.prefs` | 舊版手動 QR 流程的下載設定檔；此檔建立於 2026-09-23，**不會因產生器更新而自動更新**。 |
| 控制台建立的每筆 ICU 分享檔案 | 建立分享時由 `scripts/build_icu_qr.py` 產生的 `initial.prefs` 快照，存於 Docker 分享資料卷；重新分享才會採用新版預設值。 |

ICU QR 使用 `icu://download?url=...` 下載 `initial.prefs`。檔案結構為 `<preferences><preference name="ICU"><entry key="..." class="...">值</entry></preference></preferences>`。已從匯出檔核對的布林值型別是 `class java.lang.Boolean`；畫面中的選單與文字欄位通常是 `class java.lang.String`。下表「已匯出」表示該鍵實際出現在上述 `icu-local-after-qr.prefs`，**不是**每個候選鍵都已實機驗證可透過 QR 改變。

## 相機與廣播

| 設定畫面／用途 | 偏好設定鍵 | 已匯出 | 已知選項或備註 |
| --- | --- | :---: | --- |
| Camera | `selectedCamera` | 是 | 裝置相機清單由執行時產生。 |
| Camera Orientation | `cameraOrientation` | 是 | `0`、`1`、`2`、`3` 對應 0°、90°、180°、270°。 |
| Destination Type | `broadcast_destination_type` | 是 | 本專案使用 `RTSP-Push (Video Management System)`。 |
| Delivery Method | `selectedDelivery` | 是 | 匯出值為 `UDP`；RTSP-Push 模式下畫面停用。 |
| Broadcast Alias | `alias` | 否 | 需另行驗證匯入效果。 |
| Broadcast Buffer | `broadcastBuffer` | 否 | 秒；畫面說明 `0` 為停用。 |
| Disable Local Broadcasting | `disableLocalBroadcast` | 是 | Boolean；新 QR 預設 `true`（勾選）。 |
| Broadcast Port | `port` | 否 | RTSP-Push 模式下畫面停用。 |
| Server Port | `serverPort` | 否 | 裝置遠端控制伺服器通訊埠。 |
| Use Last Octet | `lastOctet` | 是 | Boolean；UDP 區塊。 |
| Broadcast Address | `ipAddress` | 否 | UDP 區塊。 |
| Broadcast TTL | `broadcastTTL` | 否 | UDP 區塊。 |
| RTSP Address | `rtspAddress` | 否 | 非目前 RTSP-Push 連線欄位。 |
| Focal Distance | `focal_distance` | 否 | 串流附加設定；未驗證匯入效果。 |
| Connection Timeout | `connTimeout` | 否 | 串流附加設定；未驗證匯入效果。 |
| Multicast SA Address | `mcSaAddr` | 否 | Multicast 區塊。 |
| Multicast SA Port | `mcSaPort` | 否 | Multicast 區塊。 |
| Server IP／DNS | `videoServerIP` | 是 | RTSP-Push 目標；新 QR 使用 `takbox.local`。 |
| Server Port | `videoServerPort` | 是 | RTSP-Push 目標；新 QR 使用 `8322`。 |
| Stream Path | `videoServerPath` | 是 | 新 QR 依小隊／人員或 Advanced Path 產生。 |
| Username | `videoServerUsername` | 是 | 敏感資料，不記實際值。 |
| Password | `videoServerPassword` | 是 | 機密資料，不記實際值。 |
| Use SSL | `videoServerSSL` | 是 | Boolean；RTSPS 設為 `true`。 |

## 影像、錄影與上傳

| 設定畫面／用途 | 偏好設定鍵 | 已匯出 | 已知選項或備註 |
| --- | --- | :---: | --- |
| Recording Media Type | `recording_type` | 是 | MP4 或 TS；控制本機錄影格式。 |
| Storage Location | `storage_location` | 是 | APK 選項值 `0`、`1`。 |
| Resolution | `stream_resolution` | 是 | 串流／TS：`0` 最低、`1` 240p、`2` 480p、`3` 720p、`4` 裝置最高；新 QR 預設 `3`。 |
| TS Frame Rate | `stream_frame_rate` | 是 | 相機支援值由裝置產生；匯出值與新 QR 預設皆為 `15` fps。 |
| Stream Bit Rate | `stream_bit_rate` | 是 | `400`、`700`、`900`、`2000`、`3000` kbps；新 QR 預設 `900`。 |
| MP4 Resolution | `resolution` | 是 | **只管 MP4 錄影**，不調整 RTSPS 串流。 |
| MP4 Frame Rate | `frame_rate` | 是 | **只管 MP4 錄影**，不調整 RTSPS 串流。 |
| Record MP4 with audio | `record_with_audio` | 是 | Boolean。 |
| Automatic Upload | `auto_video_upload` | 否 | 快照／錄影檔案自動上傳；與即時 RTSPS 發布不同。 |
| Video Upload URL | `video_upload_url` | 否 | 自動上傳目的地；未驗證匯入效果。 |

`upload_video` 是「Upload Image/Video」動作入口，不是持續保存的畫質選項。

## 控制與顯示

| 設定畫面／用途 | 偏好設定鍵 | 已匯出 | 已知選項或備註 |
| --- | --- | :---: | --- |
| Toggle Action Bar | `toggleActionBar` | 是 | 選項值 `0`、`1`、`2`。 |
| Always Show Action Bar | `alwaysShowActionBar` | 是 | Boolean。 |
| Control Brightness | `controlBrightness` | 是 | Boolean。 |
| Quit On Back | `icuControlQuitOnBack` | 是 | Boolean。 |
| Ask To Quit | `icuControlAskToQuit` | 是 | Boolean。 |
| Coordinate Display | `display_coord_sys` | 否 | `0` DD、`1` DM、`2` DMS、`3` UTM、`4` MGRS、`5` 地址；**這是座標格式，不是公制切換**。 |
| Altitude Display | `display_coord_alt` | 否 | `0` m MSL、`1` m HAE、`2` ft MSL、`3` ft HAE；新 QR 寫入 `0`。 |
| Azimuth Display | `display_azimuth` | 否 | Boolean。 |
| Remote Display Location | `rc_display_location` | 否 | Boolean；遠端控制頁。 |
| Remote Display Azimuth | `rc_display_azimuth` | 否 | Boolean；遠端控制頁。 |

APK 遠端控制頁的 `rc_start_record`、`rc_stop_record`、`rc_set_resolution`、`rc_set_framerate` 是動作入口；主設定頁的 `broadcastPrefs`、`videoPrefs`、`displayPrefs`、`controlPrefs`、`help`、`about` 也是導覽／動作入口。以下鍵只代表設定畫面的分類或子頁入口，不應直接當成可匯入的值：`pref_camera_setting`、`application_Settings`、`udp_delivery`、`rtsp_delivery`、`stream_preferences`、`multicast_prefs`、`video_man_system_prefs`、`videoTsPrefs`、`videoMp4Prefs`、`videoFtpPrefs`。匯出檔另有 `acra.lastVersionNr`（Integer），屬 App 內部版本資訊，不應放進佈建設定檔。

## 目前產生器實際寫入的鍵

`scripts/build_icu_qr.py` 目前寫入：`broadcast_destination_type`、`videoServerIP`、`videoServerPort`、`videoServerPath`、`videoServerSSL`、`videoServerUsername`、`disableLocalBroadcast`、`stream_resolution`、`stream_frame_rate`、`stream_bit_rate`、`display_coord_alt`，以及提供密碼時的 `videoServerPassword`。這些值供新的引導式佈建、重新分享與手動產生器共用。其他候選鍵尚未加入 QR，避免覆蓋裝置原本設定或誤把畫面動作當成偏好設定。

重現盤點可用 Android SDK `aapt2 dump resources runtime/analysis/takcam.apk` 查資源名稱與選項陣列，再用 `aapt dump xmltree runtime/analysis/takcam.apk res/UT.xml` 等指令檢查畫面鍵。檢查匯出檔時只列 `entry` 的 `key` 與 `class`；不要輸出 `videoServerPassword` 或整份檔案。
