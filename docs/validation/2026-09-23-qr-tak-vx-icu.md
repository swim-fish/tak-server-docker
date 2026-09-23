# 2026-09-23 TAK、Vx 與 ICU 分離佈建驗證

測試環境：Android 16、ATAK 5.7.0.15、Vx 2.1.0、TAK ICU 7.5.1；TAK Server 5.8 Hardened、Mumble 1.5.915、MediaMTX 1.21.1。Android 畫面由使用者操作，主機只讀取裝置及容器紀錄。裝置識別碼、呼號、分享 token、憑證及密碼不記入此文件。

## 三條入口的結果

| 設定 | 交付方式 | 實測結果 |
| --- | --- | --- |
| TAK Server 連線與 CA／裝置憑證 | 短效 ATAK `tak://com.atakmap.app/import?url=...` QR 指向憑證 DPK | 分享紀錄完整下載 1 次；使用者確認連線成功，ATAK `CotStreamListener` 顯示 `takbox.local:8089:ssl` 已連線。 |
| Vx 四頻道 Mission | 同樣的 ATAK QR 指向 Vx-only DPK | 完整下載 2 次，`ImportFileDownloader` 將檔案交給一般 DPK 匯入器；TAK Voice 未新增 `vx-local`。未觀察到 `sharing.downloaded`。 |
| Vx 四頻道 Mission | TAK Server Data Packages → Download | 成功。裝置收到 `sharing.downloaded`、解析 Protobuf Mission，使用者確認 `vx-local` 與四頻道。 |
| TAK ICU 發布設定 | `icu://download?url=...` QR 指向 `initial.prefs` | 完整下載 2 次；使用者確認 ICU 設定及啟動成功，MediaMTX 收到 RTSPS 發布至 `live/VIDEO_1`。 |

三張測試 QR 由本機分享頁產生，20 分鐘或 3 次下載先到者停止。TAK 憑證 DPK 經使用者明確授權，僅於本機 Windows 熱點的 HTTP 分享；測試完成後三筆分享均手動停止，對應的檔案快照與 QR 圖也已移除。分享資料庫保留不含檔案內容的下載計數；裝置原始截圖位於 Git 忽略的 `runtime/`，只將裁切圖放入文件。

## Vx 伺服器下載細節

現行套件：`runtime/packages/atak/atak-local-vx.dpk`，1,698 bytes，SHA-256 `f467b11790443436e2a90176646a7990004e382f4f2bd0151d3b49c63e75b0d1`。此 Vx-only 套件沒有 TAK 憑證、裝置私鑰或 Mumble 密碼。

管理者透過 `/Marti/sync/upload` 上傳，伺服器回傳相同 SHA-256。上傳後須同時設定 `tool=public` 與 `keywords=["missionpackage"]`：起初缺少後者時，ATAK 的 public Data Packages 查詢顯示 `No results available`；補齊後查詢列出唯一的 **ATAK Local Voice**。這是本次不可見的直接原因，不是群組權限問題。

伺服器的兩份舊測試包 **ATAK Local Voice Dual Test**、**ATAK Local Voice Only Test** 已按確切 hash 由 `/Marti/api/files/{hash}` 刪除；刪除前確認 `runtime/packages/atak-archive/` 有相同 SHA-256 的本機備份。最後 `/Marti/api/sync/search` 只列出新包，`tool=public`、`keywords=["missionpackage"]`。

裝置下載紀錄：

```text
MissionPackageDownloader: Queried: 1 Mission Packages
MissionPackageDownloader: Sending OnReceiveParams intent: com.atakmap.android.gbr.multicastvoice.sharing.downloaded
MissionSharingManager: Received intent: action=com.atakmap.android.gbr.multicastvoice.sharing.downloaded
MissionSharingManager: MissionPackageManifest found. Mission name: ATAK Local Voice
MissionSharingManager: Found protobuf missions. Count: 1
MissionSharingManager: Processing Proto Mission: name=vx-local
```

Protobuf／legacy JSON 解析器會交叉嘗試兩份 payload，個別解析警告之後仍有明確的 Protobuf Mission 成功紀錄。Mumble 伺服器另外記錄此裝置通過登入，逐一加入 `Primary[2]`、`Alternate[3]`、`Medical[4]`、`Emergency[5]`。這驗證頻道選取與伺服器加入；雙向 PTT 音訊未在本次測試。

![實機 Vx vx-local Channel Pool 顯示四個頻道，Primary 位於 VS1、Medical 位於 VS2](../images/atak-vx-four-channel-pool.jpg)

圖片取自使用者於裝置截取的實際 ATAK 畫面，以程式只裁切 Channel Pool。原圖的地圖、呼號與定位資訊未放入文件；裁切圖亦未保留原圖 EXIF。另一張同時段截圖顯示相同 Channel Pool，未重複收錄。

## 操作結論

TAK 憑證 DPK 與 ICU 設定可以各自用專屬 QR 佈建。Vx 的 `sharing.downloaded` 只在本次 TAK Server Data Packages → Download 路徑觸發；一般 ATAK 遠端 QR 匯入雖能取得同一份 Vx DPK，仍未建立 Mission。分享頁因此不再列出帶該 Vx action 的 DPK 作為 QR 來源。

相關文件：[TAK 連線](../atak/connection.md)、[Vx Mission](../atak/vx-missions.md)、[ICU QR](../mediamtx/icu-qrcode.md)、[分享頁](../sharing/portal.md)。
