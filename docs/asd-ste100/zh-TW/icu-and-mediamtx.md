# ICU 與 MediaMTX 影像

[返回任務索引](index.md)

<a id="task-05"></a>

## 任務五　替人員建立 ICU 影像發布 QR

`initial.prefs` 含發布密碼。同一小隊共用發布密碼。新 QR 預設為 720p、15 fps、900 kbps、高度公尺 MSL，並勾選 Disable Local Broadcasting。

1. 在「引導式佈建 → ICU 小隊發布」選擇小隊。
2. 從 1–10 號隊員中單選、多選或全選。預設勾選全部隊員，每名所選隊員各有一張 QR。
3. 若要自訂單一路徑，選 Advanced。具名小隊的 Stream Path 必須位於 `live/<小隊>/` 下，並以 `/` 結尾。ICU 會在末端加上 `VIDEO_1`。
4. 設定 QR 時間與下載上限。
5. 預覽各隊員路徑。
6. 執行工作。
7. 在結果頁左右切換 QR。
8. 分別交付完整 `icu://download?url=...` 連結。
9. 在 ICU 核對外部設定、RTSP-Push 與 `takbox.local:8554`。
10. 確認 `Use SSL?` 未勾選。
11. 啟動串流。
12. 在 MediaMTX 核對線上路徑。

**同隊可使用同一張 QR。** 匯入後，各裝置可在 ICU 把小隊後段改成自己的路徑。例如，將 `live/alpha/1/` 改為 `live/alpha/2/`，帳密維持不變。不同裝置應使用不同完整路徑。

QR 下載的 `initial.prefs` 含密碼。匯入提示不能證明影像已發布。已建立的 QR 是設定檔快照。變更預設值後，須重新分享。

若還要把影像別名發布到 TAK 群組，使用下列批次流程。

TAK 群組只限制別名清單的可見性。已取得觀看帳密的裝置，不會因群組變更而自動失去播放權限。若改選群組，系統會先移除舊別名再重建。影像清單可能短暫消失。

1. 選「引導式佈建 → ICU 小隊批次交付」。
2. 選擇小隊、起始隊員與人數。
3. 選擇 TAK 影像別名的可見群組。
4. 在預覽核對每名隊員的 `live/<小隊>/<隊員>/VIDEO_1` 與可讀憑證。
5. 執行工作。
6. 讓每台裝置掃描自己的 QR。
7. 在 ATAK 影像清單核對相應的 `ICU <小隊> <隊員>` 別名。

詳見[批次操作與限制](../../mediamtx/management.md#批次交付隊員-qr-與-tak-影像別名)。

![ICU 標準模式選項](../../images/console-task-05-icu.png)

圖 9：依小隊與人員代號產生標準路徑及短效 QR。

![ICU Advanced 路徑預覽](../../images/console-task-05b-advanced-path.png)

圖 10：Advanced 只改 Stream Path。預覽會顯示 ICU 自動附加的 `VIDEO_1`。

![同一張 Alpha QR 改成 2 號路徑後上線](../../images/console-icu-alpha-2-live-path.png)

圖 10a：Android ICU 匯入原 Alpha QR 後，使用者手動改成 `live/alpha/2/` 並成功發布。控制台顯示完整路徑 `live/alpha/2/VIDEO_1`。此圖只顯示路徑，沒有擷取實際影像。

### 裝置端核對畫面

下列圖片由使用者提供的實機截圖裁切，保留原始設定內容。圖 A 顯示已勾選的狀態。圖 B、C 只顯示設定入口。**不能單靠截圖證明裝置已套用 900 kbps 或公尺 MSL。**

掃描新 QR 後，須在 ICU 開啟選項核對設定。再以 MediaMTX 的線上路徑驗證發布。設定鍵與可用值見 [ICU QR 設定](../../mediamtx/icu-qrcode.md#室內定位與影像設定)。

![ICU 已勾選 Disable Local Broadcasting](../../images/icu-disable-local-broadcasting.jpg)

圖 A：室內 GPS 失效時，使用者觀察到未勾選這項設定可能使影像發布中斷。新 QR 預設勾選，仍需實機複測。

![ICU 串流解析度、影格率與位元率設定入口](../../images/icu-stream-quality-preferences.jpg)

圖 B：串流畫質看 Resolution、TS Frame Rate、Stream Bit Rate。MP4 錄影使用另一組設定。

![ICU 座標格式與高度顯示設定入口](../../images/icu-display-preferences.jpg)

圖 C：Altitude Display 控制公尺或英尺。Coordinate Display 控制座標格式。

<a id="task-06"></a>

## 任務六　讓無人機或編碼器發布影像

**注意：發布網址與 QR 含帳密。不要貼進日誌或 Git。** 一般裝置的 QR 沒有 ICU 分享下載期限。停用身分或重設密碼才會讓舊連線資訊失效。一般裝置不會自動附加 `VIDEO_1`。

1. 在「`引導式佈建 → Advanced → 一般設備`」填入裝置名稱。
2. 填入唯一的 `live/` 完整路徑。URL input group 會顯示 RTSPS 預覽。
3. 核對預覽。
4. 建立裝置身分。
5. 在結果頁按「顯示連線資訊」。RTSP 與 RTSPS 各有完整網址、「複製網址」按鈕及 QR。
6. 優先用 RTSPS 發布。
7. 使用 RTSPS 時，驗證 TAK CA 憑證鏈與 `takbox.local`。僅支援 RTSP 的裝置可在受控熱點使用 `8554`。
8. 在 MediaMTX 確認完整路徑上線。
9. 用另一個讀取端驗證影像。

每台裝置有獨立帳密與指定路徑。RTSPS 網址格式為 `rtsps://<帳號>:<密碼>@takbox.local:8322/<Stream Path>`。RTSP 使用 `rtsp://` 與 `8554`。

![一般裝置 URL input group](../../images/console-task-06-device.png)

圖 11：先核對裝置名稱與完整 Stream Path。

![一般裝置發布預覽頁](../../images/console-task-06b-preview.png)

圖 12：預覽確認路徑及 TLS 條件。截圖未建立帳號。

### 本機模擬無人機實測

2026-09-25 在控制台建立 `Drone RTSPS Validation`，路徑為 `live/drone/validation-20260925`。測試使用獨立 Docker bridge 上的 FFmpeg 模擬無人機。FFmpeg 經 Windows 熱點位址向 `takbox.local:8322` 發布 H.264 影像。

獨立讀取帳號從相同路徑解碼 30 個影格。控制台 WebRTC 預覽也顯示測試色條。RTSP `8554/TCP` 另以相同身分發布，並讀取 30 個影格。

測試後已停用身分，舊網址無法再發布。這次測試不代表實體無人機或外網驗收。詳見[驗證紀錄](../../validation/2026-09-25-drone-synthetic-stream.md)。

![一般裝置實測的發布 URL 預覽](../../images/console-drone-01-url-preview.png)

圖 12a：建立前的 URL 預覽只有主機、通訊埠與路徑。帳密在建立後才產生。

![一般裝置 RTSP 與 RTSPS 複製按鈕](../../images/console-drone-05-copy-links-redacted.png)

圖 12b：建立後展開連線資訊，可分別複製 RTSP／RTSPS 網址或掃 QR。截圖中的網址與 QR 已遮蔽，不能用來連線。

![模擬無人機串流卡片](../../images/console-drone-03-stream-card.png)

圖 12c：發布後先核對 `live/drone/validation-20260925` 是否出現在「目前發布的串流」。

![模擬無人機影像在控制台播放](../../images/console-drone-02-live-preview.png)

圖 12d：控制台預覽收到 FFmpeg 測試色條。播放成功還需以獨立讀取端確認影像可解碼。

<a id="task-07"></a>

## 任務七　檢視影像與控制觀看

先看下方流向圖，再依播放端選擇連線。ICU QR 預設以 RTSP `8554` 發布，且 `Use SSL?` 不勾選。這與 ATAK Video Alias 支援的協定一致。無人機與一般裝置可用 RTSPS。在受控區域網路內，也可使用無 TLS 的 RTSP。

ATAK 的已驗證路徑是直接向 MediaMTX 以 RTSP／TCP 讀取。瀏覽器則由獨立 viewer／preview 容器按需讀取，再提供 WebRTC。逐段協定、加密與實測限制見[本機影像處理與流向](../../mediamtx/video-flow.md)。

### 在管理頁預覽

1. 在「MediaMTX 管理」選擇線上串流。
2. 按「即時預覽」。
3. 看完後按「關閉預覽」。

### 在熱點裝置觀看

1. 使用 `http://takbox.local:8889/live/<path>/` 觀看。須保留末尾斜線。

### 控制公開 WebRTC 觀看

「公開 WebRTC 觀看」開關控制新觀看與現有公開工作階段。這個開關不停止 ICU 推流。管理頁即時預覽不列入公開觀看工作階段。

1. 依需求設定「公開 WebRTC 觀看」開關。
2. 切到「觀看工作階段」子頁。
3. 核對公開觀看的數量、路徑、來源位址與連線狀態。

此頁每 5 秒更新。可搜尋工作階段，或按「立即更新」。

### 在 ATAK CIV 5.7.0.15 觀看 ICU 影像

ICU 自動分享的 RTSPS 來源，不能直接用這版 ATAK 內建播放器開啟。RTSP 只限受控區域網路或 VPN。

1. 確認發布端仍持續發布。
2. 在 ATAK 手動建立 RTSP 來源。
3. 填入 `takbox.local:8554`、實際 `live/.../VIDEO_1` 路徑及 `atak-viewer` 讀取帳密。
4. 勾選 **Reliable P2P Connection (consumes more resources)**，讓 RTSP 使用 TCP。

見[實機紀錄](../../validation/2026-09-25-atak-icu-viewer.md)。

本節引用的原始驗收只涵蓋熱點觀看。網際網路仍需 FQDN、HTTPS、NAT 與 ICE 驗收。圖 13 截圖時沒有線上串流。

![WebRTC 觀看狀態控制](../../images/console-task-07-viewer.png)

圖 13：管理頁顯示公開觀看開關、工作階段數與串流清單。

![ICU、無人機、MediaMTX、ATAK、WebRTC 與縮圖的影像流向](../../images/console-task-07b-viewing-flow.png)

圖 14：來源推流、MediaMTX 接收、ATAK 直接讀取、瀏覽器 WebRTC 與單影格縮圖分屬不同處理路徑。`Use SSL?` 代表 ICU 的 RTSPS／TLS。WebRTC 的 HTTP 信令與加密媒體也分開標示。

![MediaMTX 公開觀看工作階段頁](../../images/console-media-viewer-sessions.png)

圖 14a：2026-09-26 截圖時沒有公開觀看工作階段。這是空清單的頁面檢查，未驗證實際播放。來源位址若經 NAT 或代理，不一定是觀看裝置的原始 IP。

<a id="task-08"></a>

## 任務八　停用或輪替 MediaMTX 發布身分

### 選取發布身分

1. 開啟「MediaMTX 管理」。
2. 若要管理小隊，切到「ICU」。若要管理一般裝置，切到「其他」。
3. 搜尋身分。
4. 依需求切換「啟用中／停用／顯示全部」。
5. 勾選要修改的身分。

兩頁共用線上串流與觀看開關。在「ICU」，「啟用」表示身分允許登入。「串流中」徽章與路徑數表示 MediaMTX 目前有可用發布串流。展開「QR 路徑」可逐條核對。

在「其他」，可設定每頁 10／20／30 筆，並使用上一頁或下一頁。

### 依目的執行操作

再次發布 QR 不會更改原密碼。重設小隊密碼後，整個小隊須重新掃 QR。一般裝置須重新取得專屬發布網址。

1. 若要再次發布 ICU QR，展開小隊卡片的 QR 路徑。預設全選。
2. 若要再次發布 ICU QR，逐條勾選或使用「全選／全部不選」。至少須選一條。
3. 依目的選「再次發布 ICU QR」、「停用選取身分」或「重設選取密碼」。
4. 勾選頁面確認。
5. 送出工作。
6. 若已重設小隊密碼，讓整個小隊重新掃 QR。
7. 若已重設一般裝置密碼，重新取得專屬發布網址。
8. 若已重設密碼，核對原發布連線已中斷。

再次發布 QR 不會更改原密碼。小隊共用帳密。要單獨停用一台裝置，應使用一般裝置身分。

![MediaMTX 發布身分清單](../../images/console-task-08-publishers.png)

圖 15：搜尋與篩選發布身分。

![選取身分後的管理按鈕](../../images/console-task-08b-selected-publisher.png)

圖 16：選取後才可再次發布、停用或重設。截圖未送出變更。

![ICU 子頁的小隊卡片](../../images/console-media-icu-cards.png)

圖 17：ICU 子頁保留小隊卡片與「再次發布 ICU QR」。

![其他子頁的裝置表格](../../images/console-media-other-table.png)

圖 18：「其他」子頁提供狀態篩選、搜尋、每頁筆數及裝置列的重新啟用入口。

### 重新啟用已停用的裝置

沿用舊密碼時，原網址會恢復可用。產生新密碼後，原網址失效。

1. 切到「其他」→「停用」。
2. 找到裝置。
3. 按「重新啟用」。
4. 在對話方塊選「沿用舊密碼」或「產生新密碼」。
5. 勾選確認。
6. 送出工作。
7. 在結果頁按「顯示連線資訊」。
8. 分別複製 RTSP／RTSPS 新網址，或使用 QR。
9. 核對指定路徑可以推流。

![重新啟用裝置的密碼選項](../../images/console-media-reactivate-dialog.png)

圖 19：預設選取「產生新密碼」，也可明確改成「沿用舊密碼」。測試身分曾沿用舊密碼重新啟用並成功推流，驗證後已再次停用。產生新密碼尚未完成實際推流驗收。

[返回任務索引](index.md)
