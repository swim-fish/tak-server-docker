# 2026-09-29 監視器模式移植與四路播放驗證

## 環境與方法

- 本機 Windows Docker Desktop Compose 專案 `tak-local`，`takbox.local` 解析至 `192.168.88.2`。
- 將 `tak.shihyu.tw` 的監看牆互動移至 `share-admin`，畫面套用控制台 Bootstrap 5 樣式；播放走管理員驗證的 `/media/preview/`。
- 在獨立 Docker bridge 使用 FFmpeg，經 `rtsps://takbox.local:8322` 暫時發布四路 `live/monitor-test/1` 至 `live/monitor-test/4`、320×180／10 fps H.264 合成測試影像。發布端驗證本機 Root CA 與 `takbox.local` 主機名稱；測試後移除發布容器。
- 使用 Playwright Chromium 登入 `http://127.0.0.1:10066/media/wall`，確認預設四宮格、自動選取四路，並在全螢幕模式檢查各 iframe 的影片元素。

## 結果

1. `/media/wall/status` 回報四條上線路徑，頁面回應 HTTP 200 並載入 Bootstrap 5 樣式。
2. 全螢幕四宮格內四個影片元素均為 `readyState = 4`、`paused = false`、解碼尺寸 `320×180`，且 `currentTime > 0`。`media-preview` 記錄四個 WebRTC 工作階段建立、ICE 連線成功，並各自讀取一條 H.264 軌道。
3. 在 1280×720 瀏覽器視窗中切換至 12 與 16 格，兩者各有正確格數、最小格高 220px；頁面高度分別約 909px 與 1139px，以捲動保留影像高度。
4. ICU／其他頁的縮圖改以受管理員驗證的 JPEG 端點取得。對暫時發布的 `live/monitor-test/thumbnail` 擷取後，回應為 JPEG，檔頭 `FFD8`；兩頁的瀏覽器縮圖皆成功解碼為 480×270。測試來源關鍵影格間隔較長，最初 12 秒逾時曾使瀏覽器顯示替代文字；調整為 30 秒後重測成功。MediaMTX 記錄 RTSP 讀取工作階段於取得單一影格後關閉，API 查詢無殘留讀取工作階段。頁面不再包含縮圖 WebRTC iframe，點「放大預覽」仍可啟動即時畫面，關閉後回到靜態縮圖。

這次是四條合成影像的本機同時播放測試；12／16 格僅驗證版面，未測試 12／16 條串流同時解碼，也未測試實體 ICU 或外網觀看。
