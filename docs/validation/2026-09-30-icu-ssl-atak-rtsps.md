# 2026-09-30 ICU 啟用 SSL 後，ATAK 人物 Video 無法觀看

同日後續已完成[非 SSL RTSP 限定 IP 無帳密觀看](2026-09-30-icu-rtsp-ip-reader.md)，使用者確認 ATAK 可觀看。下文保留先前 SSL 測試當時的觀察與未驗證範圍；RTSPS 的相容性結論未因此改變。

## 結論與適用版本

TAK ICU 7.5.1 勾選 `Use SSL?` 後，以 RTSPS 發布影像，並在人物 CoT 的 `event/detail/__video/@url` 帶入 `rtsps://` 連結。**本次實測的 ATAK CIV 5.7.0.15 不支援直接播放這個 RTSPS 來源**：點選人物轉盤上的 Video 後顯示 `Failed to Connect`，紀錄顯示網址被解析為 `raw`，隨即發生播放器例外。

ICU 的 SSL 發布在本次雲端測試中成功；失敗發生於 ATAK 解析自動通告的觀看連結。其他 ATAK 版本、其他播放器及改寫後的連結不在本次結論範圍內。

## 測試對象與資料處理

- 發布端：TAK ICU 7.5.1，`Use SSL?` 啟用，RTSPS `8322/TCP`。
- 觀看端：ATAK CIV 5.7.0.15，從人物轉盤的 Video 按鈕開啟 ICU 自動通告來源。
- 雲端收流端：GCP 上的 MediaMTX 1.21.1，使用內部帳密授權。
- 日期與時間：2026-09-30，Asia/Taipei（UTC+08:00）。

本紀錄省略實際帳密、網域、IP、呼號、裝置識別碼、人物 UID、座標及本機使用者目錄。含敏感資料的原始 CoT、完整網址及 logcat 保留於 Git 忽略的受控 `runtime/`，不附於文件。

## 實際觀察

| 檢查 | 觀察結果 | 能證明的範圍 |
| --- | --- | --- |
| TAK Server 快取的人物 CoT | 實際讀回 `event/detail/__video/@url`；協定為 `rtsps`，通訊埠為 `8322`，URI userinfo 同時含帳號與密碼 | 人物 Video 的來源是 ICU 自動通告的發布連結；不是由偏好設定重組，也不是伺服器管理的 Video Alias |
| 雲端授權調整 | Alpha、Bravo、Charlie 共 30 個 ICU 帳號保留原帳密及原路徑的 `publish`，新增同一路徑的 `read` | 同一組帳密可發布及讀取自己的串流；不授予其他成員或跨小隊讀取權限 |
| 授權後、尚無串流時 | 30 個原帳密對各自路徑的 RTSPS `DESCRIBE` 均回應 `404`；錯誤密碼、跨小隊路徑、同隊其他成員路徑各 3 次均回應 `401` | 自己路徑的讀取授權通過，但當時無串流；不能把 `404` 當成畫面播放成功 |
| ATAK 實際開啟 | 13:55:27、13:55:30、13:55:56、13:56:24 的四次嘗試均出現 `protocol=raw`，隨後為 `MediaException` 與 `MediaProcessor.createFromFileNative`；另持續出現 `using raw for: rtsps` | 此版本將 RTSPS 當成 `raw` 處理，人物 Video 無法直接播放 |
| 隨後查詢雲端狀態 | MediaMTX 有 1 條 ready 串流，與先前匯出的 ICU 人物 Video 路徑相符；30 個帳號的發布及讀取權限仍在 | 這次串流已上線，權限設定仍生效 |
| 實際 ICU 網址的公開端點檢查 | 使用匯出網址中的原帳密傳送 RTSPS `DESCRIBE`，驗證公開 TLS 憑證與主機名稱後收到 `200 OK` | 公開入口可達、TLS 驗證及讀取授權成功，串流描述可取得；本次沒有以此測試解碼影像或驗證 ATAK 畫面 |

以下是去識別化的網址結構，佔位文字不能用於連線：

```text
rtsps://<username>:<password>@<media-host>:8322/live/<team>/<member>/VIDEO_1
```

因此，人物轉盤出現 Video 按鈕只表示 ATAK 收到影像連結，不代表內建播放器支援該協定。增加 `read` 權限後，伺服器端授權已通過，但 ATAK 仍因 RTSPS 解析失敗而無法觀看。

## 操作上的影響與未驗證項目

- 使用 ICU 的 SSL 發布設定時，須另外驗證 ATAK 的觀看來源相容性；不能將 ICU 發布成功視為 ATAK 人物 Video 播放成功。
- [2026-09-25 本機測試](2026-09-25-atak-icu-viewer.md)曾保留 ICU RTSPS 發布，另在 ATAK 手動建立 RTSP 來源並勾選 Reliable／TCP，成功觀看。該結果僅適用受控區域網路或 VPN，沒有證明本次雲端人物連結已修復。
- 本次未將 ICU 關閉 SSL 後重測。早期 ICU 純 RTSP 曾因媒體逾時失敗，不能將「取消 `Use SSL?`」列為已驗證的解法。
- 雲端管理的 RTMPS Video Aliases 與人物 CoT 的 RTSPS 連結是不同來源；本次未透過 RTMPS Alias 驗證這條真實 ICU 串流，也未改寫人物 CoT。
- 其他 ATAK 版本、同時多串流、多觀看端及長時間播放尚未驗收。

相關說明：[MediaMTX／ICU 設定](../mediamtx/server.md)、[ICU QR 格式](../mediamtx/icu-qrcode.md)、[疑難排解](../troubleshooting.md)。
