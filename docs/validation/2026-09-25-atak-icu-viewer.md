# ATAK 觀看 TAK ICU 影像實測（2026-09-25）

## 測試對象

- 發布端：TAK ICU 7.5.1，以 RTSPS 發布 `live/alpha/1/VIDEO_1`。MediaMTX 將內容拆為 H.264 與 KLV 兩條軌道。
- 觀看端：Alpha 平板，ATAK CIV 5.7.0.15，與 MediaMTX 位於同一區域網路。
- 觀看身分：MediaMTX 的 `atak-viewer` 讀取帳號；密碼與發布端的小隊帳密分開。本紀錄不包含實際帳密。

## 排查與結果

1. ATAK 從 ICU 的影像通告開啟 `rtsps://takbox.local:8322/live/alpha/1/VIDEO_1` 時，log 顯示 `using raw for: rtsps`，`ConnectionEntry` 變成 `protocol=raw`。播放器只記錄 `connect to takbox.local`，立即在 `MediaProcessor.createFromFileNative` 拋出 `MediaException`；MediaMTX 沒收到對應的讀取請求。相同裝置到 8322 與 8554 的 TCP 連線測試均成功。ATAK 5.7.0.15 SDK 的 `ConnectionEntryBase.Protocol` 列舉有 `RTSP`，沒有 `RTSPS`。
2. 第一次手動 RTSP 嘗試時，發布端已停止，MediaMTX 回報 `no stream is available on path 'live/alpha/1/VIDEO_1'`。這次不能判定播放器或帳密是否可用。
3. ICU 再次發布後，ATAK 的 RTSP 讀取已通過驗證並取得路徑。未勾選「Reliable／TCP」時，MediaMTX 記錄 `is reading ... with UDP, 2 tracks (H264, KLV)`，隨後回報 `can't setup medias with different transports`；ATAK 拋出 `MediaProcessor.createFromRtspNative` 例外。
4. 在 ATAK 手動建立的 RTSP 影像來源勾選 **Reliable P2P Connection (consumes more resources)** 後，log 出現 `rtsp reliable communications requested`。MediaMTX 記錄以 TCP 讀取同一路徑的 H.264 與 KLV；ATAK 辨識兩條軌道並建立 1280×720 畫面。使用者提供的最後兩張實機截圖另確認格式清單有 `rtsp`、沒有 `rtsps`，且來源填入 `takbox.local:8554/live/alpha/1/VIDEO_1`、`atak-viewer`、遮蔽的密碼與已勾選的 Reliable P2P Connection。實機畫面也確認影像持續顯示。原始截圖含地圖與定位資訊，僅供當次核對，沒有加入版控。

## 可重現設定

保持 ICU 以 RTSPS 發布；在 ATAK 的影像來源手動設定 **RTSP**、主機 `takbox.local`、通訊埠 `8554`、完整路徑 `live/alpha/1/VIDEO_1`、讀取帳號 `atak-viewer` 及其獨立密碼，並勾選 **Reliable P2P Connection (consumes more resources)**，讓 RTSP 走 TCP。先確認 ICU 持續發布，再開啟 ATAK 影像。

ICU 自動通告的 RTSPS 來源在這版 ATAK 無法直接播放；上述 RTSP 觀看走未加密連線，僅限受控區域網路或 VPN。其他 ATAK 版本、外網、RTSP UDP 與自動通告改寫均未驗收。

## 自動通告與手動來源的欄位差異

| ATAK 影像項目 | 自動收到的 `VIDEO_1` | 手動建立的 Video Alias 測試資料（實際別名為 `V1`） |
| --- | --- | --- |
| 通告／選擇的協定 | 解析 log 顯示 `rtsps`；ATAK 5.7.0.15 轉成 `raw` | `rtsp` |
| 主機、通訊埠、路徑 | `takbox.local`、`8322`、`live/alpha/1/VIDEO_1` | `takbox.local`、`8554`、`live/alpha/1/VIDEO_1` |
| 讀取身分 | 觀看端記錄沒有 `atak-viewer` | `atak-viewer` 與獨立讀取密碼 |
| Reliable P2P Connection | 自動項目沒有啟用紀錄 | 已勾選，RTSP 改走 TCP |
| 播放器實際得到的連線 | `raw` 只產生 `takbox.local`，隨即失敗 | 完整 RTSP 來源及 `?tcp`，成功播放 |

ATAK 的格式選單列出 `raw`，但沒有 `rtsps`。`raw` 是未知協定的備援解析結果，不能視為 RTSPS 播放選項。上述通告欄位是由 `using raw for: rtsps`、`ConnectionEntry` 與播放器 log 還原；**未直接擷取 ICU 發出的原始 CoT XML**。自動的 `VIDEO_1` 會持續隨通告更新，本次成功的是獨立手動建立的 Video Alias 測試資料，沒有證明修改 `VIDEO_1` 後可持久保留設定。
