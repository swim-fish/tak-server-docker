# ICU 與 MediaMTX 影像：原文與中英文改寫對照

[原始手冊](../../tak-server/console-task-manual/icu-and-mediamtx.md) · [繁中版](../zh-TW/icu-and-mediamtx.md) · [English](../en/icu-and-mediamtx.md)

原文欄保留來源內容。段落 ID 用於追蹤對照。獨立手冊依操作順序排列，必要時將風險說明移到步驟前。

## B001

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **ICU 與 MediaMTX 影像** | **ICU 與 MediaMTX 影像** | **ICU and MediaMTX video** |

## B002

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [返回任務索引](../../tak-server/console-task-manual.md) | [返回任務索引](../../tak-server/console-task-manual.md) | [Return to the task index](../../tak-server/console-task-manual.md) |

## B003

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-05 | Anchor: task-05 | Anchor: task-05 |

## B004

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務五　替人員建立 ICU 影像發布 QR** | **任務五　替人員建立 ICU 影像發布 QR** | **Task 5: Create ICU publisher QR codes for personnel** |

## B005

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 在「引導式佈建 → ICU 小隊發布」選小隊，再從 1–10 號隊員中單選、多選或全選；預設勾選全部隊員。每名所選隊員各有一張 QR。<br>2. 自訂單一路徑時選 Advanced，具名小隊的 Stream Path 必須留在 `live/<小隊>/` 下並以 `/` 結尾。ICU 會在末端加上 `VIDEO_1`。<br>3. 設定 QR 時間與下載上限，預覽各隊員路徑後執行；結果頁左右切換 QR，分別交付完整 `icu://download?url=...`。<br>4. 在 ICU 核對外部設定、RTSP-Push、`takbox.local:8554` 且 `Use SSL?` 不勾選，再啟動串流並查 MediaMTX 線上路徑。新 QR 預設 720p、15 fps、900 kbps、高度公尺 MSL，且勾選 Disable Local Broadcasting。 | `initial.prefs` 含發布密碼。同一小隊共用發布密碼。新 QR 預設為 720p、15 fps、900 kbps、高度公尺 MSL，並勾選 Disable Local Broadcasting。<br><br>1. 在「引導式佈建 → ICU 小隊發布」選擇小隊。<br>2. 從 1–10 號隊員中單選、多選或全選。預設勾選全部隊員，每名所選隊員各有一張 QR。<br>3. 若要自訂單一路徑，選 Advanced。具名小隊的 Stream Path 必須位於 `live/<小隊>/` 下，並以 `/` 結尾。ICU 會在末端加上 `VIDEO_1`。<br>4. 設定 QR 時間與下載上限。<br>5. 預覽各隊員路徑。<br>6. 執行工作。<br>7. 在結果頁左右切換 QR。<br>8. 分別交付完整 `icu://download?url=...` 連結。<br>9. 在 ICU 核對外部設定、RTSP-Push 與 `takbox.local:8554`。<br>10. 確認 `Use SSL?` 未勾選。<br>11. 啟動串流。<br>12. 在 MediaMTX 核對線上路徑。 | The `initial.prefs` file contains the publisher password. Members of one squad share this password. New QR defaults are 720p, 15 fps, 900 kbps, and altitude in meters MSL. Disable Local Broadcasting is selected by default.<br><br>1. Select the squad in 「引導式佈建 → ICU 小隊發布」.<br>2. Select one, several, or all members numbered 1–10. All members are selected by default. Each selected member gets a QR.<br>3. To specify a single custom path, select Advanced. A named squad Stream Path must stay under `live/<小隊>/` and end with `/`. ICU adds `VIDEO_1`.<br>4. Set the QR duration and download limit.<br>5. Preview each member path.<br>6. Run the job.<br>7. Switch between QR codes on the results page.<br>8. Deliver each complete `icu://download?url=...` link.<br>9. In ICU, check external settings, RTSP-Push, and `takbox.local:8554`.<br>10. Check that `Use SSL?` is clear.<br>11. Start the stream.<br>12. Check the online path in MediaMTX. |

## B006

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 同一小隊共用發布密碼。**同隊可使用同一張 QR**；匯入後各裝置可在 ICU 把小隊後段改成自己的路徑，例如 `live/alpha/1/` 改為 `live/alpha/2/`，帳密維持不變。不同裝置應使用不同完整路徑。QR 下載的 `initial.prefs` 含密碼；只看到匯入提示尚未證明影像已發布。已建立的 QR 是設定檔快照，變更預設值後須重新分享。 | **同隊可使用同一張 QR。** 匯入後，各裝置可在 ICU 把小隊後段改成自己的路徑。例如，將 `live/alpha/1/` 改為 `live/alpha/2/`，帳密維持不變。不同裝置應使用不同完整路徑。<br><br>QR 下載的 `initial.prefs` 含密碼。匯入提示不能證明影像已發布。已建立的 QR 是設定檔快照。變更預設值後，須重新分享。 | **Squad members can use the same QR.** After import, each device can change the path suffix in ICU. For example, change `live/alpha/1/` to `live/alpha/2/` without changes to credentials. Different devices should use different complete paths.<br><br>The downloaded `initial.prefs` contains a password. An import message does not prove video publication. An existing QR is a configuration snapshot. Share a new QR after default settings change. |

## B007

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 若還要把影像別名發布到 TAK 群組，改選「引導式佈建 → ICU 小隊批次交付」：選小隊、起始隊員與人數，再選 TAK 影像別名的可見群組。預覽核對每名隊員的 `live/<小隊>/<隊員>/VIDEO_1` 與可讀憑證後執行。交付時讓每台裝置掃自己的 QR，並在 ATAK 影像清單核對相應的 `ICU <小隊> <隊員>` 別名。若改選群組，舊別名會先移除再重建，影像清單可能短暫消失。TAK 群組只限制別名清單可見性；已取得觀看帳密的裝置不會因群組變更自動失去播放權限。詳見[批次操作與限制](../../mediamtx/management.md#批次交付隊員-qr-與-tak-影像別名)。 | 若還要把影像別名發布到 TAK 群組，使用下列批次流程。<br><br>TAK 群組只限制別名清單的可見性。已取得觀看帳密的裝置，不會因群組變更而自動失去播放權限。若改選群組，系統會先移除舊別名再重建。影像清單可能短暫消失。<br><br>1. 選「引導式佈建 → ICU 小隊批次交付」。<br>2. 選擇小隊、起始隊員與人數。<br>3. 選擇 TAK 影像別名的可見群組。<br>4. 在預覽核對每名隊員的 `live/<小隊>/<隊員>/VIDEO_1` 與可讀憑證。<br>5. 執行工作。<br>6. 讓每台裝置掃描自己的 QR。<br>7. 在 ATAK 影像清單核對相應的 `ICU <小隊> <隊員>` 別名。<br><br>詳見[批次操作與限制](../../mediamtx/management.md#批次交付隊員-qr-與-tak-影像別名)。 | Use the following batch procedure if you also need to publish video aliases to TAK groups.<br><br>TAK groups control only alias list visibility. Devices with viewer credentials do not automatically lose playback permission after group changes. If you select different groups, the system deletes and recreates old aliases. The video list may disappear briefly.<br><br>1. Select 「引導式佈建 → ICU 小隊批次交付」.<br>2. Select the squad, first member, and member count.<br>3. Select the groups that can see the TAK video aliases.<br>4. In the preview, check each `live/<小隊>/<隊員>/VIDEO_1` path and the certificates with read permission.<br>5. Run the job.<br>6. Let each device scan its own QR.<br>7. Check the corresponding `ICU <小隊> <隊員>` alias in the ATAK video list.<br><br>See [batch operations and limits](../../mediamtx/management.md#批次交付隊員-qr-與-tak-影像別名). |

## B008

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [ICU 標準模式選項](../../images/console-task-05-icu.png) | [ICU 標準模式選項](../../images/console-task-05-icu.png) | [ICU standard mode options](../../images/console-task-05-icu.png) |

## B009

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 9：依小隊與人員代號產生標準路徑及短效 QR。 | 圖 9：依小隊與人員代號產生標準路徑及短效 QR。 | Figure 9: Generate standard paths and short-lived QR codes from squad and member identifiers. |

## B010

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [ICU Advanced 路徑預覽](../../images/console-task-05b-advanced-path.png) | [ICU Advanced 路徑預覽](../../images/console-task-05b-advanced-path.png) | [ICU Advanced path preview](../../images/console-task-05b-advanced-path.png) |

## B011

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 10：Advanced 只改 Stream Path；預覽會顯示 ICU 自動附加的 `VIDEO_1`。 | 圖 10：Advanced 只改 Stream Path。預覽會顯示 ICU 自動附加的 `VIDEO_1`。 | Figure 10: Advanced changes only Stream Path. The preview shows the `VIDEO_1` suffix that ICU adds. |

## B012

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [同一張 Alpha QR 改成 2 號路徑後上線](../../images/console-icu-alpha-2-live-path.png) | [同一張 Alpha QR 改成 2 號路徑後上線](../../images/console-icu-alpha-2-live-path.png) | [Alpha QR changed to member 2 and online](../../images/console-icu-alpha-2-live-path.png) |

## B013

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 10a：Android ICU 匯入原 Alpha QR 後，使用者手動改成 `live/alpha/2/` 並成功發布；控制台顯示完整路徑 `live/alpha/2/VIDEO_1`。此圖只顯示路徑，沒有擷取實際影像。 | 圖 10a：Android ICU 匯入原 Alpha QR 後，使用者手動改成 `live/alpha/2/` 並成功發布。控制台顯示完整路徑 `live/alpha/2/VIDEO_1`。此圖只顯示路徑，沒有擷取實際影像。 | Figure 10a: After import of the original Alpha QR, the user changed the Android ICU path to `live/alpha/2/`. Publication succeeded. The console shows `live/alpha/2/VIDEO_1`. The image shows the path only, without video capture. |

## B014

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **裝置端核對畫面** | **裝置端核對畫面** | **Check settings on the device** |

## B015

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 下列圖片由使用者提供的實機截圖裁切，保留原始設定內容。圖 A 顯示已勾選的狀態；圖 B、C 只顯示設定入口，**不能單靠截圖證明裝置已套用 900 kbps 或公尺 MSL**。掃描新 QR 後，須在 ICU 開啟選項核對，並以 MediaMTX 的線上路徑驗證發布。設定鍵與可用值見 [ICU QR 設定](../../mediamtx/icu-qrcode.md#室內定位與影像設定)。 | 下列圖片由使用者提供的實機截圖裁切，保留原始設定內容。圖 A 顯示已勾選的狀態。圖 B、C 只顯示設定入口。**不能單靠截圖證明裝置已套用 900 kbps 或公尺 MSL。**<br><br>掃描新 QR 後，須在 ICU 開啟選項核對設定。再以 MediaMTX 的線上路徑驗證發布。設定鍵與可用值見 [ICU QR 設定](../../mediamtx/icu-qrcode.md#室內定位與影像設定)。 | These crops come from device screenshots supplied by the user. They retain the original settings. Figure A shows a selected checkbox. Figures B and C show only the settings entries. **These screenshots do not prove that 900 kbps or meters MSL are applied.**<br><br>After a new QR scan, open the ICU options to check the settings. Then check publication through the MediaMTX online path. See [ICU QR settings](../../mediamtx/icu-qrcode.md#室內定位與影像設定) for keys and available values. |

## B016

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [ICU 已勾選 Disable Local Broadcasting](../../images/icu-disable-local-broadcasting.jpg) | [ICU 已勾選 Disable Local Broadcasting](../../images/icu-disable-local-broadcasting.jpg) | [ICU Disable Local Broadcasting selected](../../images/icu-disable-local-broadcasting.jpg) |

## B017

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 A：室內 GPS 失效時，使用者觀察到未勾選這項設定可能使影像發布中斷；新 QR 預設勾選，仍需實機複測。 | 圖 A：室內 GPS 失效時，使用者觀察到未勾選這項設定可能使影像發布中斷。新 QR 預設勾選，仍需實機複測。 | Figure A: A user observed that a clear checkbox may interrupt video publication when indoor GPS fails. New QR codes select it by default. Device retesting is still necessary. |

## B018

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [ICU 串流解析度、影格率與位元率設定入口](../../images/icu-stream-quality-preferences.jpg) | [ICU 串流解析度、影格率與位元率設定入口](../../images/icu-stream-quality-preferences.jpg) | [ICU stream resolution, frame rate, and bit rate entries](../../images/icu-stream-quality-preferences.jpg) |

## B019

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 B：串流畫質看 Resolution、TS Frame Rate、Stream Bit Rate；MP4 錄影使用另一組設定。 | 圖 B：串流畫質看 Resolution、TS Frame Rate、Stream Bit Rate。MP4 錄影使用另一組設定。 | Figure B: Resolution, TS Frame Rate, and Stream Bit Rate control stream quality. MP4 recording uses separate settings. |

## B020

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [ICU 座標格式與高度顯示設定入口](../../images/icu-display-preferences.jpg) | [ICU 座標格式與高度顯示設定入口](../../images/icu-display-preferences.jpg) | [ICU coordinate and altitude display entries](../../images/icu-display-preferences.jpg) |

## B021

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 C：Altitude Display 控制公尺或英尺；Coordinate Display 控制座標格式。 | 圖 C：Altitude Display 控制公尺或英尺。Coordinate Display 控制座標格式。 | Figure C: Altitude Display selects meters or feet. Coordinate Display selects the coordinate format. |

## B022

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-06 | Anchor: task-06 | Anchor: task-06 |

## B023

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務六　讓無人機或編碼器發布影像** | **任務六　讓無人機或編碼器發布影像** | **Task 6: Publish video from a drone or encoder** |

## B024

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 在「引導式佈建 → Advanced → 一般設備」填設備名稱與唯一的 `live/` 完整路徑；URL input group 會顯示 RTSPS 預覽。<br>2. 預覽後建立設備身分。結果頁按「顯示連線資訊」，RTSP 與 RTSPS 各有一組完整網址、「複製網址」按鈕及 QR；每台裝置有獨立帳密與指定路徑。網址格式為 `rtsps://<帳號>:<密碼>@takbox.local:8322/<Stream Path>`，RTSP 使用 `rtsp://` 與 `8554`。<br>3. 優先用 RTSPS 發布並驗證 TAK CA 憑證鏈與 `takbox.local`；僅支援 RTSP 的裝置可在受控熱點使用 `8554`。最後在 MediaMTX 確認完整路徑上線，再用另一個讀取端驗證影像。 | 1. 在「`引導式佈建 → Advanced → 一般設備`」填入裝置名稱。<br>2. 填入唯一的 `live/` 完整路徑。URL input group 會顯示 RTSPS 預覽。<br>3. 核對預覽。<br>4. 建立裝置身分。<br>5. 在結果頁按「顯示連線資訊」。RTSP 與 RTSPS 各有完整網址、「複製網址」按鈕及 QR。<br>6. 優先用 RTSPS 發布。<br>7. 使用 RTSPS 時，驗證 TAK CA 憑證鏈與 `takbox.local`。僅支援 RTSP 的裝置可在受控熱點使用 `8554`。<br>8. 在 MediaMTX 確認完整路徑上線。<br>9. 用另一個讀取端驗證影像。<br><br>每台裝置有獨立帳密與指定路徑。RTSPS 網址格式為 `rtsps://<帳號>:<密碼>@takbox.local:8322/<Stream Path>`。RTSP 使用 `rtsp://` 與 `8554`。 | 1. Enter the device name in 「引導式佈建 → Advanced → 一般設備」.<br>2. Enter a unique complete `live/` path. The URL input group shows an RTSPS preview.<br>3. Check the preview.<br>4. Create the device identity.<br>5. Select 「顯示連線資訊」 on the results page. RTSP and RTSPS each have a complete URL, 「複製網址」 button, and QR.<br>6. Prefer RTSPS for publication.<br>7. With RTSPS, verify the TAK CA chain and `takbox.local`. RTSP-only devices can use `8554` on a controlled hotspot.<br>8. Check that the complete path is online in MediaMTX.<br>9. Test the video with a separate reader.<br><br>Each device has separate credentials and an assigned path. The RTSPS format is `rtsps://<帳號>:<密碼>@takbox.local:8322/<Stream Path>`. RTSP uses `rtsp://` and `8554`. |

## B025

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 發布網址與 QR 含帳密，不要貼進日誌或 Git。一般裝置使用的 QR 沒有 ICU 分享下載期限；停用身分或重設密碼才會讓舊連線資訊失效。一般設備不會自動附加 `VIDEO_1`。 | **注意：發布網址與 QR 含帳密。不要貼進日誌或 Git。** 一般裝置的 QR 沒有 ICU 分享下載期限。停用身分或重設密碼才會讓舊連線資訊失效。一般裝置不會自動附加 `VIDEO_1`。 | **CAUTION: Publisher URLs and QR codes contain credentials. Do not paste them into logs or Git.** General device QR codes do not have the ICU sharing expiry. Only identity deactivation or password reset invalidates the old connection details. General devices do not automatically add `VIDEO_1`. |

## B026

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [一般設備 URL input group](../../images/console-task-06-device.png) | [一般裝置 URL input group](../../images/console-task-06-device.png) | [General device URL input group](../../images/console-task-06-device.png) |

## B027

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 11：先核對設備名稱與完整 Stream Path。 | 圖 11：先核對裝置名稱與完整 Stream Path。 | Figure 11: First check the device name and complete Stream Path. |

## B028

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [一般設備發布預覽頁](../../images/console-task-06b-preview.png) | [一般裝置發布預覽頁](../../images/console-task-06b-preview.png) | [General device publisher preview](../../images/console-task-06b-preview.png) |

## B029

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 12：預覽確認路徑及 TLS 條件；截圖未建立帳號。 | 圖 12：預覽確認路徑及 TLS 條件。截圖未建立帳號。 | Figure 12: Check the path and TLS conditions in the preview. The screenshot precedes account creation. |

## B030

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **本機模擬無人機實測** | **本機模擬無人機實測** | **Local simulated drone test** |

## B031

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 2026-09-25 在控制台建立 `Drone RTSPS Validation`，路徑為 `live/drone/validation-20260925`。使用獨立 Docker bridge 上的 FFmpeg 模擬無人機，經 Windows 熱點位址向 `takbox.local:8322` 發布 H.264 影像；獨立讀取帳號從相同路徑解碼 30 個影格，控制台 WebRTC 預覽也顯示測試色條。RTSP `8554/TCP` 另以相同身分發布、讀取 30 個影格。測試後已停用身分，舊網址無法再發布；這不是實體無人機或外網驗收。詳見[驗證紀錄](../../validation/2026-09-25-drone-synthetic-stream.md)。 | 2026-09-25 在控制台建立 `Drone RTSPS Validation`，路徑為 `live/drone/validation-20260925`。測試使用獨立 Docker bridge 上的 FFmpeg 模擬無人機。FFmpeg 經 Windows 熱點位址向 `takbox.local:8322` 發布 H.264 影像。<br><br>獨立讀取帳號從相同路徑解碼 30 個影格。控制台 WebRTC 預覽也顯示測試色條。RTSP `8554/TCP` 另以相同身分發布，並讀取 30 個影格。<br><br>測試後已停用身分，舊網址無法再發布。這次測試不代表實體無人機或外網驗收。詳見[驗證紀錄](../../validation/2026-09-25-drone-synthetic-stream.md)。 | On 2026-09-25, the console created `Drone RTSPS Validation` with path `live/drone/validation-20260925`. FFmpeg on a separate Docker bridge simulated a drone. It published H.264 through the Windows hotspot address to `takbox.local:8322`.<br><br>A separate reader account decoded 30 frames from the same path. The console WebRTC preview also showed test color bars. A separate RTSP `8554/TCP` test published with the same identity and read 30 frames.<br><br>The identity was deactivated after testing. The old URL could no longer publish. This test does not establish acceptance for a physical drone or internet access. See the [validation record](../../validation/2026-09-25-drone-synthetic-stream.md). |

## B032

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [一般設備實測的發布 URL 預覽](../../images/console-drone-01-url-preview.png) | [一般裝置實測的發布 URL 預覽](../../images/console-drone-01-url-preview.png) | [General device publisher URL preview](../../images/console-drone-01-url-preview.png) |

## B033

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 12a：建立前的 URL 預覽只有主機、通訊埠與路徑；帳密在建立後才產生。 | 圖 12a：建立前的 URL 預覽只有主機、通訊埠與路徑。帳密在建立後才產生。 | Figure 12a: Before creation, the URL preview contains only the host, port, and path. Credentials become available after creation. |

## B034

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [一般設備 RTSP 與 RTSPS 複製按鈕](../../images/console-drone-05-copy-links-redacted.png) | [一般裝置 RTSP 與 RTSPS 複製按鈕](../../images/console-drone-05-copy-links-redacted.png) | [General device RTSP and RTSPS copy controls](../../images/console-drone-05-copy-links-redacted.png) |

## B035

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 12b：建立後展開連線資訊，可分別複製 RTSP／RTSPS 網址或掃 QR。截圖中的網址與 QR 已遮蔽，不能用來連線。 | 圖 12b：建立後展開連線資訊，可分別複製 RTSP／RTSPS 網址或掃 QR。截圖中的網址與 QR 已遮蔽，不能用來連線。 | Figure 12b: After creation, expand the connection details to copy RTSP/RTSPS URLs or scan QR codes. Concealed URLs and QR codes in the screenshot cannot connect. |

## B036

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [模擬無人機串流卡片](../../images/console-drone-03-stream-card.png) | [模擬無人機串流卡片](../../images/console-drone-03-stream-card.png) | [Simulated drone stream card](../../images/console-drone-03-stream-card.png) |

## B037

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 12c：發布後先核對 `live/drone/validation-20260925` 是否出現在「目前發布的串流」。 | 圖 12c：發布後先核對 `live/drone/validation-20260925` 是否出現在「目前發布的串流」。 | Figure 12c: After publication, check for `live/drone/validation-20260925` in 「目前發布的串流」. |

## B038

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [模擬無人機影像在控制台播放](../../images/console-drone-02-live-preview.png) | [模擬無人機影像在控制台播放](../../images/console-drone-02-live-preview.png) | [Simulated drone video in the console](../../images/console-drone-02-live-preview.png) |

## B039

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 12d：控制台預覽收到 FFmpeg 測試色條；播放成功還需以獨立讀取端確認影像可解碼。 | 圖 12d：控制台預覽收到 FFmpeg 測試色條。播放成功還需以獨立讀取端確認影像可解碼。 | Figure 12d: The console preview received FFmpeg color bars. A separate reader must still confirm successful video decoding. |

## B040

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-07 | Anchor: task-07 | Anchor: task-07 |

## B041

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務七　檢視影像與控制觀看** | **任務七　檢視影像與控制觀看** | **Task 7: View video and control viewing** |

## B042

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 先看下方流向圖，再依播放端選擇連線：ICU QR 預設以 RTSP `8554`（`Use SSL?` 不勾選）發布，與 ATAK Video Alias 支援的協定一致；無人機／一般設備可用 RTSPS，受控區域網路內也可用無 TLS 的 RTSP。ATAK 的已驗證路徑是直接向 MediaMTX 以 RTSP／TCP 讀取；瀏覽器則由獨立 viewer／preview 容器按需讀取後提供 WebRTC。逐段協定、加密與實測限制見[本機影像處理與流向](../../mediamtx/video-flow.md)。 | 先看下方流向圖，再依播放端選擇連線。ICU QR 預設以 RTSP `8554` 發布，且 `Use SSL?` 不勾選。這與 ATAK Video Alias 支援的協定一致。無人機與一般裝置可用 RTSPS。在受控區域網路內，也可使用無 TLS 的 RTSP。<br><br>ATAK 的已驗證路徑是直接向 MediaMTX 以 RTSP／TCP 讀取。瀏覽器則由獨立 viewer／preview 容器按需讀取，再提供 WebRTC。逐段協定、加密與實測限制見[本機影像處理與流向](../../mediamtx/video-flow.md)。 | First read the flow diagram below. Then select the connection for the playback device. ICU QR defaults use RTSP `8554` with `Use SSL?` clear. This matches the protocol supported by ATAK Video Alias. Drones and general devices can use RTSPS. They can also use RTSP without TLS on a controlled LAN.<br><br>The verified ATAK path reads directly from MediaMTX through RTSP/TCP. For browsers, separate viewer/preview containers read on demand and supply WebRTC. See [local video flow](../../mediamtx/video-flow.md) for protocols, encryption, and test limits. |

## B043

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 在「MediaMTX 管理」選線上串流，按「即時預覽」；看完按「關閉預覽」。<br>2. 熱點裝置使用 `http://takbox.local:8889/live/<path>/` 觀看，末尾斜線需保留。<br>3. 以「公開 WebRTC 觀看」開關控制新觀看與現有公開工作階段；此開關不停止 ICU 推流。切到「觀看工作階段」子頁，核對公開觀看的數量、路徑、來源位址與連線狀態；管理頁即時預覽不列入。此頁每 5 秒更新，可搜尋或按「立即更新」。<br>4. 若在 ATAK CIV 5.7.0.15 觀看 ICU 影像，先確認發布端仍持續發布；在 ATAK 手動建立 RTSP 來源，使用 `takbox.local:8554`、實際 `live/.../VIDEO_1` 路徑及 `atak-viewer` 讀取帳密，並勾選 **Reliable P2P Connection (consumes more resources)**，讓 RTSP 走 TCP。ICU 自動分享的 RTSPS 來源不能直接用這版 ATAK 內建播放器開啟。RTSP 只限受控區域網路或 VPN；見[實機紀錄](../../validation/2026-09-25-atak-icu-viewer.md)。 | **在管理頁預覽**<br><br>1. 在「MediaMTX 管理」選擇線上串流。<br>2. 按「即時預覽」。<br>3. 看完後按「關閉預覽」。<br><br>**在熱點裝置觀看**<br><br>1. 使用 `http://takbox.local:8889/live/<path>/` 觀看。須保留末尾斜線。<br><br>**控制公開 WebRTC 觀看**<br><br>「公開 WebRTC 觀看」開關控制新觀看與現有公開工作階段。這個開關不停止 ICU 推流。管理頁即時預覽不列入公開觀看工作階段。<br><br>1. 依需求設定「公開 WebRTC 觀看」開關。<br>2. 切到「觀看工作階段」子頁。<br>3. 核對公開觀看的數量、路徑、來源位址與連線狀態。<br><br>此頁每 5 秒更新。可搜尋工作階段，或按「立即更新」。<br><br>**在 ATAK CIV 5.7.0.15 觀看 ICU 影像**<br><br>ICU 自動分享的 RTSPS 來源，不能直接用這版 ATAK 內建播放器開啟。RTSP 只限受控區域網路或 VPN。<br><br>1. 確認發布端仍持續發布。<br>2. 在 ATAK 手動建立 RTSP 來源。<br>3. 填入 `takbox.local:8554`、實際 `live/.../VIDEO_1` 路徑及 `atak-viewer` 讀取帳密。<br>4. 勾選 **Reliable P2P Connection (consumes more resources)**，讓 RTSP 使用 TCP。<br><br>見[實機紀錄](../../validation/2026-09-25-atak-icu-viewer.md)。 | **Preview in the management page**<br><br>1. Select an online stream in 「MediaMTX 管理」.<br>2. Select 「即時預覽」.<br>3. When finished, select 「關閉預覽」.<br><br>**View from a hotspot device**<br><br>1. Open `http://takbox.local:8889/live/<path>/`. Keep the final slash.<br><br>**Control public WebRTC viewing**<br><br>The 「公開 WebRTC 觀看」 switch controls new viewing and existing public sessions. It does not stop ICU publication. Public session counts exclude management previews.<br><br>1. Set 「公開 WebRTC 觀看」 as required.<br>2. Open the 「觀看工作階段」 subpage.<br>3. Check the public viewer count, paths, source addresses, and connection states.<br><br>The page updates every 5 seconds. You can search sessions or select 「立即更新」.<br><br>**View ICU video in ATAK CIV 5.7.0.15**<br><br>This ATAK built-in player cannot directly open the RTSPS source that ICU shares automatically. Use RTSP only on a controlled LAN or VPN.<br><br>1. Check that the publisher continues to publish.<br>2. Manually create an RTSP source in ATAK.<br>3. Enter `takbox.local:8554`, the actual `live/.../VIDEO_1` path, and the `atak-viewer` credentials.<br>4. Select **Reliable P2P Connection (consumes more resources)** to use RTSP over TCP.<br><br>See the [device test record](../../validation/2026-09-25-atak-icu-viewer.md). |

## B044

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 目前只驗證熱點觀看；網際網路仍需 FQDN、HTTPS、NAT 與 ICE 驗收。下方圖 13 截圖時沒有線上串流。 | 本節引用的原始驗收只涵蓋熱點觀看。網際網路仍需 FQDN、HTTPS、NAT 與 ICE 驗收。圖 13 截圖時沒有線上串流。 | The original acceptance test cited here covers hotspot viewing only. Internet access still needs FQDN, HTTPS, NAT, and ICE acceptance tests. No streams were online in Figure 13. |

## B045

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [WebRTC 觀看狀態控制](../../images/console-task-07-viewer.png) | [WebRTC 觀看狀態控制](../../images/console-task-07-viewer.png) | [WebRTC viewing controls](../../images/console-task-07-viewer.png) |

## B046

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 13：管理頁顯示公開觀看開關、工作階段數與串流清單。 | 圖 13：管理頁顯示公開觀看開關、工作階段數與串流清單。 | Figure 13: The management page shows the public viewing switch, session count, and stream list. |

## B047

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [ICU、無人機、MediaMTX、ATAK、WebRTC 與縮圖的影像流向](../../images/console-task-07b-viewing-flow.png) | [ICU、無人機、MediaMTX、ATAK、WebRTC 與縮圖的影像流向](../../images/console-task-07b-viewing-flow.png) | [ICU, drone, MediaMTX, ATAK, WebRTC, and thumbnail flows](../../images/console-task-07b-viewing-flow.png) |

## B048

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 14：來源推流、MediaMTX 接收、ATAK 直接讀取、瀏覽器 WebRTC 與單影格縮圖分屬不同處理路徑。`Use SSL?` 代表 ICU 的 RTSPS／TLS；WebRTC 的 HTTP 信令與加密媒體也分開標示。 | 圖 14：來源推流、MediaMTX 接收、ATAK 直接讀取、瀏覽器 WebRTC 與單影格縮圖分屬不同處理路徑。`Use SSL?` 代表 ICU 的 RTSPS／TLS。WebRTC 的 HTTP 信令與加密媒體也分開標示。 | Figure 14: Publication, MediaMTX reception, direct ATAK reading, browser WebRTC, and single-frame thumbnails use different paths. `Use SSL?` means ICU RTSPS/TLS. The diagram separates WebRTC HTTP signaling from encrypted media. |

## B049

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [MediaMTX 公開觀看工作階段頁](../../images/console-media-viewer-sessions.png) | [MediaMTX 公開觀看工作階段頁](../../images/console-media-viewer-sessions.png) | [Public MediaMTX viewer sessions](../../images/console-media-viewer-sessions.png) |

## B050

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 14a：2026-09-26 截圖時沒有公開觀看工作階段；這是空清單的頁面檢查，未驗證實際播放。來源位址若經 NAT 或代理，不一定是觀看裝置的原始 IP。 | 圖 14a：2026-09-26 截圖時沒有公開觀看工作階段。這是空清單的頁面檢查，未驗證實際播放。來源位址若經 NAT 或代理，不一定是觀看裝置的原始 IP。 | Figure 14a: No public viewer sessions existed in the 2026-09-26 screenshot. This empty-list page check did not test playback. After NAT or a proxy, the source address may differ from the device IP. |

## B051

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-08 | Anchor: task-08 | Anchor: task-08 |

## B052

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務八　停用或輪替 MediaMTX 發布身分** | **任務八　停用或輪替 MediaMTX 發布身分** | **Task 8: Deactivate publisher identities or change their passwords** |

## B053

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 開啟「MediaMTX 管理」。切到「ICU」管理小隊卡片；切到「其他」管理一般設備表格。兩頁的線上串流與觀看開關共用。<br>2. 搜尋並切換「啟用中／停用／顯示全部」。在「ICU」，「啟用」表示身分允許登入；「串流中」徽章與路徑數表示 MediaMTX 目前有可用發布串流，展開「QR 路徑」可逐條核對。在「其他」可設定每頁 10／20／30 筆，並使用上一頁／下一頁。勾選要修改的身分。<br>3. 再次發布時展開小隊卡片的 QR 路徑，預設全選，也能逐條勾選或使用「全選／全部不選」；至少選一條。接著依目的選「再次發布 ICU QR」、「停用選取身分」或「重設選取密碼」，勾選頁面確認後送出。<br>4. 重設小隊密碼後，整個小隊須重新掃 QR；一般設備則重新取得專屬發布網址。核對原發布連線已中斷。 | **選取發布身分**<br><br>1. 開啟「MediaMTX 管理」。<br>2. 若要管理小隊，切到「ICU」。若要管理一般裝置，切到「其他」。<br>3. 搜尋身分。<br>4. 依需求切換「啟用中／停用／顯示全部」。<br>5. 勾選要修改的身分。<br><br>兩頁共用線上串流與觀看開關。在「ICU」，「啟用」表示身分允許登入。「串流中」徽章與路徑數表示 MediaMTX 目前有可用發布串流。展開「QR 路徑」可逐條核對。<br><br>在「其他」，可設定每頁 10／20／30 筆，並使用上一頁或下一頁。<br><br>**依目的執行操作**<br><br>再次發布 QR 不會更改原密碼。重設小隊密碼後，整個小隊須重新掃 QR。一般裝置須重新取得專屬發布網址。<br><br>1. 若要再次發布 ICU QR，展開小隊卡片的 QR 路徑。預設全選。<br>2. 若要再次發布 ICU QR，逐條勾選或使用「全選／全部不選」。至少須選一條。<br>3. 依目的選「再次發布 ICU QR」、「停用選取身分」或「重設選取密碼」。<br>4. 勾選頁面確認。<br>5. 送出工作。<br>6. 若已重設小隊密碼，讓整個小隊重新掃 QR。<br>7. 若已重設一般裝置密碼，重新取得專屬發布網址。<br>8. 若已重設密碼，核對原發布連線已中斷。 | **Select publisher identities**<br><br>1. Open 「MediaMTX 管理」.<br>2. For squads, select 「ICU」. For general devices, select 「其他」.<br>3. Search for the identity.<br>4. Set 「啟用中／停用／顯示全部」 as required.<br>5. Select the identities to change.<br><br>Both pages share the online streams and viewing switch. On 「ICU」, 「啟用」 means the identity can log in. The 「串流中」 badge and path count indicate available publisher streams in MediaMTX. Expand 「QR 路徑」 to check individual paths.<br><br>On 「其他」, select 10/20/30 entries per page. Use the previous and next page controls.<br><br>**Select the operation**<br><br>Reissuing QR codes does not change the password. After a squad password reset, every squad member must scan a QR again. General devices must obtain their own publisher URLs again.<br><br>1. To reissue ICU QR codes, expand the squad card QR paths. All paths are selected by default.<br>2. To reissue ICU QR codes, select individual paths or use 「全選／全部不選」. You must select at least one path.<br>3. Select 「再次發布 ICU QR」, 「停用選取身分」, or 「重設選取密碼」 for the required operation.<br>4. Select the page confirmation checkbox.<br>5. Submit the job.<br>6. After a squad password reset, let all squad members scan the QR again.<br>7. After a general device password reset, obtain its assigned publisher URL again.<br>8. After a password reset, check that the original publisher connection is disconnected. |

## B054

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 再次發布 QR 不會更改原密碼。小隊共用帳密；要單獨停用一台裝置，應使用一般設備身分。 | 再次發布 QR 不會更改原密碼。小隊共用帳密。要單獨停用一台裝置，應使用一般裝置身分。 | Reissuing QR codes does not change the original password. Squad members share credentials. To deactivate one device separately, you should use a general device identity. |

## B055

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [MediaMTX 發布身分清單](../../images/console-task-08-publishers.png) | [MediaMTX 發布身分清單](../../images/console-task-08-publishers.png) | [MediaMTX publisher identities](../../images/console-task-08-publishers.png) |

## B056

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 15：搜尋與篩選發布身分。 | 圖 15：搜尋與篩選發布身分。 | Figure 15: Search and filter publisher identities. |

## B057

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [選取身分後的管理按鈕](../../images/console-task-08b-selected-publisher.png) | [選取身分後的管理按鈕](../../images/console-task-08b-selected-publisher.png) | [Controls for selected identities](../../images/console-task-08b-selected-publisher.png) |

## B058

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 16：選取後才可再次發布、停用或重設；截圖未送出變更。 | 圖 16：選取後才可再次發布、停用或重設。截圖未送出變更。 | Figure 16: Select identities before reissuing, deactivating, or resetting. The screenshot precedes submission. |

## B059

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [ICU 子頁的小隊卡片](../../images/console-media-icu-cards.png) | [ICU 子頁的小隊卡片](../../images/console-media-icu-cards.png) | [Squad cards on the ICU subpage](../../images/console-media-icu-cards.png) |

## B060

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 17：ICU 子頁保留小隊卡片與「再次發布 ICU QR」。 | 圖 17：ICU 子頁保留小隊卡片與「再次發布 ICU QR」。 | Figure 17: The ICU subpage keeps squad cards and 「再次發布 ICU QR」. |

## B061

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [其他子頁的設備表格](../../images/console-media-other-table.png) | [其他子頁的裝置表格](../../images/console-media-other-table.png) | [Device table on the other subpage](../../images/console-media-other-table.png) |

## B062

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 18：「其他」子頁提供狀態篩選、搜尋、每頁筆數及設備列的重新啟用入口。 | 圖 18：「其他」子頁提供狀態篩選、搜尋、每頁筆數及裝置列的重新啟用入口。 | Figure 18: The 「其他」 subpage has status filters, search, page size, and reactivation controls in device rows. |

## B063

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **重新啟用已停用的裝置** | **重新啟用已停用的裝置** | **Reactivate a device** |

## B064

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 切到「其他」→「停用」，找到設備後按「重新啟用」。<br>2. 在對話框選「沿用舊密碼」或「產生新密碼」，勾選確認再送出。沿用時原網址恢復可用；產生新密碼後，原網址失效。<br>3. 結果頁按「顯示連線資訊」，分別複製 RTSP／RTSPS 新網址或使用 QR。核對指定路徑可以推流。 | 沿用舊密碼時，原網址會恢復可用。產生新密碼後，原網址失效。<br><br>1. 切到「其他」→「停用」。<br>2. 找到裝置。<br>3. 按「重新啟用」。<br>4. 在對話方塊選「沿用舊密碼」或「產生新密碼」。<br>5. 勾選確認。<br>6. 送出工作。<br>7. 在結果頁按「顯示連線資訊」。<br>8. 分別複製 RTSP／RTSPS 新網址，或使用 QR。<br>9. 核對指定路徑可以推流。 | With the old password, the original URL becomes usable again. A new password invalidates the original URL.<br><br>1. Select 「其他」 → 「停用」.<br>2. Find the device.<br>3. Select 「重新啟用」.<br>4. Select 「沿用舊密碼」 or 「產生新密碼」 in the dialog.<br>5. Select the confirmation checkbox.<br>6. Submit the job.<br>7. Select 「顯示連線資訊」 on the results page.<br>8. Copy the RTSP/RTSPS URLs separately, or use the QR.<br>9. Check that the assigned path accepts publication. |

## B065

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [重新啟用設備的密碼選項](../../images/console-media-reactivate-dialog.png) | [重新啟用裝置的密碼選項](../../images/console-media-reactivate-dialog.png) | [Password options for device reactivation](../../images/console-media-reactivate-dialog.png) |

## B066

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 19：預設選取「產生新密碼」，也可明確改成「沿用舊密碼」。測試身分曾沿用舊密碼重新啟用並成功推流，驗證後已再次停用；產生新密碼尚未完成實際推流驗收。 | 圖 19：預設選取「產生新密碼」，也可明確改成「沿用舊密碼」。測試身分曾沿用舊密碼重新啟用並成功推流，驗證後已再次停用。產生新密碼尚未完成實際推流驗收。 | Figure 19: The default is 「產生新密碼」. You can explicitly select 「沿用舊密碼」. A test identity successfully published after reactivation with its old password. The identity was deactivated again after verification. Publication with a new password still needs a test. |

## B067

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [返回任務索引](../../tak-server/console-task-manual.md) | [返回任務索引](../../tak-server/console-task-manual.md) | [Return to the task index](../../tak-server/console-task-manual.md) |
