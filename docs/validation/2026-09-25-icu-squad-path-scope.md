# 2026-09-25 ICU 同隊共用 QR 與路徑隔離

## 驗證目標

讓同隊裝置匯入相同 ICU QR，然後各自修改小隊後段的 Stream Path。Alpha 帳號只可發布 `live/alpha/…/VIDEO_1`；其他小隊與非 ICU 尾段仍須遭拒。

## 實際結果

1. 修改前，Alpha 登錄檔只有 `live/alpha/1/VIDEO_1`。以既有 `icu-alpha` 帳密模擬發布 `live/alpha/2/VIDEO_1`，FFmpeg 結束碼為 `8`，MediaMTX 記錄 `failed to authenticate`。
2. 將 MediaMTX 的 Alpha 發布權限改為以 `live/alpha/` 為界、以 `/VIDEO_1` 結尾的正規表示式，重新載入設定。登錄檔仍只有原本的 Alpha／1 QR 初始路徑，未簽發第二組帳密。
3. 相同帳密模擬發布 `live/alpha/2/VIDEO_1`，FFmpeg 結束碼為 `0`。嘗試 `live/bravo/2/VIDEO_1` 及 `live/alpha/2/OTHER`，兩者結束碼皆為 `8`。
4. 使用者在 Android ICU 匯入原 Alpha QR 後，手動將 Stream Path 改為 `live/alpha/2/`，回報串流成功啟動。MediaMTX 記錄 RTSPS 發布到 `live/alpha/2/VIDEO_1`，並顯示 H.264、KLV 兩條軌道；控制台列出該線上路徑。

![Android ICU 更改後的 Alpha／2 線上路徑](../images/console-icu-alpha-2-live-path.png)

圖 1：控制台實際列出的路徑。為避免收錄現場影像，截圖只包含串流卡片，沒有開啟即時預覽。

## 邊界與操作提醒

- 授權以完整小隊名稱為界，`alpha` 不會比對 `alphabeta` 或 `bravo`。小隊後段可使用英文字母、數字、底線、連字號組成的多層路徑；ICU 固定附加 `VIDEO_1`。
- `default` 非具名小隊，維持原有逐一路徑授權。一般設備的獨立帳號不能占用具名小隊前綴。
- 同隊共用 QR 等同共用密碼；停用或重設整個小隊會影響該隊所有裝置。不同裝置應使用不同完整路徑，以免互相搶占發布工作階段。
- 這次實機確認 Alpha／2 可發布；未逐一用 Android 測試其他小隊或多台裝置同時發布。伺服器端已測試 Alpha 帳號無法發布 Bravo 路徑。
