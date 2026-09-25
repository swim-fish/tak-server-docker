# 2026-09-25 一般設備發布與收流驗證

## 範圍

在 Windows Docker Desktop 的 `tak-local` Compose 環境，從 TAK 控制台「引導式佈建 → MediaMTX Advanced → 一般設備」建立獨立發布身分，再用 FFmpeg 模擬無人機影像。這次沒有連接實體無人機。

- 測試名稱：`Drone RTSPS Validation`。
- 唯一路徑：`live/drone/validation-20260925`；一般設備不會附加 `VIDEO_1`。
- 發布入口：`rtsps://<帳號>:<密碼>@takbox.local:8322/live/drone/validation-20260925`，或受控熱點內的 `rtsp://<帳號>:<密碼>@takbox.local:8554/live/drone/validation-20260925`。
- 模擬來源：獨立 Docker bridge 上的 FFmpeg，經 Windows 已發布的 `192.168.137.1` 通訊埠連線；`takbox.local` 指向該位址。
- 接收端：另一個 FFmpeg 工作階段使用獨立 `atak-viewer` 讀取帳號；瀏覽器使用控制台 WebRTC 即時預覽。

發布網址與 QR 含測試密碼，因此版控文件及截圖保留佔位文字或遮蔽。測試身分在驗收後已停用。

## 實際操作與證據

1. 控制台的 URL input group 顯示 `rtsps://takbox.local:8322/` 前綴；填 `live/drone/validation-20260925` 後，預覽顯示完整路徑。確認後建立身分，結果頁預設隱藏連線資訊。
2. 按「顯示連線資訊」後，RTSP／RTSPS 各有專屬「複製網址」按鈕及 QR。向控制台端點讀回兩個網址，與身分帳號、密碼、通訊埠及指定路徑逐項比對一致；兩張 QR 均為有效 PNG。沒有把完整發布網址寫入版控。
3. RTSPS：FFmpeg 發布 1280×720、15 fps、目標 900 kbps 的 H.264 測試色條，強制 TCP 傳輸並驗證 TAK Root CA 與 `takbox.local` 主機名稱。MediaMTX 記錄 `is publishing to path 'live/drone/validation-20260925'`。另一端經 RTSPS 讀取並成功解碼 30 個影格。
4. 控制台「目前發布的串流」出現相同路徑；「即時預覽」顯示測試色條。`media-preview` 記錄 WebRTC 工作階段已建立，且從該路徑讀取一條 H.264 影像軌。
5. RTSP：同一身分經 `8554/TCP` 發布 640×360、10 fps、目標 600 kbps 的測試色條；另一端經 RTSP 讀取並成功解碼 30 個影格。此入口沒有 TLS，僅在受控本機網路測試。
6. 停止推流後，於控制台停用該身分。舊 RTSPS 網址再次發布的 FFmpeg 結束碼為 `8`；連線資訊與 QR 端點均回傳 HTTP `404`。控制台顯示「已停用」。
7. 新增「其他」子頁後，從停用表格開啟「重新啟用」對話框，選「沿用舊密碼」。重新啟用前後的密碼 SHA-256 相同；舊帳密經 `8554/TCP` 再次發布 320×180、10 fps 測試影像，FFmpeg 結束碼為 `0`。
8. 再次於控制台停用該身分。以相同帳密重試推流，FFmpeg 結束碼為 `8`。最終狀態為**已停用**。「產生新密碼」已由程式測試確認會更換密碼，但未進行實際推流驗收。

![一般設備發布 URL 預覽](../images/console-drone-01-url-preview.png)

圖 1：建立前核對主機、通訊埠及 Stream Path。

![已建立但尚未揭露連線資訊](../images/console-drone-04-created-hidden.png)

圖 2：建立完成後須主動展開，才會顯示含密碼的網址與 QR。

![RTSP 與 RTSPS 個別複製控制項](../images/console-drone-05-copy-links-redacted.png)

圖 3：截圖時已用瀏覽器樣式遮蔽網址與 QR；複製按鈕與協定分類保留原始介面。

![目前發布的測試路徑](../images/console-drone-03-stream-card.png)

圖 4：控制台列出指定路徑與即時預覽、熱點觀看入口。

![WebRTC 即時預覽測試色條](../images/console-drone-02-live-preview.png)

圖 5：瀏覽器實際收到 FFmpeg 模擬影像；不是實體無人機畫面。

![停用設備的重新啟用選項](../images/console-media-reactivate-dialog.png)

圖 6：對話框提供沿用舊密碼或產生新密碼；截圖於送出前擷取，沒有包含密碼。

## 驗收界線

這次確認本機 TCP 路徑、獨立發布身分、RTSPS 憑證驗證、RTSP／RTSPS 讀取與控制台 WebRTC 預覽。尚未測試實體無人機的編碼格式與韌體、UDP 傳輸、Android 或 Firefox 播放器，以及從網際網路連線。對外部署仍須處理公開 DNS、HTTPS、Router NAT、防火牆及 WebRTC ICE 可達性。
