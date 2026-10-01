# 2026-09-30 ICU 非 SSL RTSP 與 ATAK 限定 IP 無帳密觀看

## 實機結果

TAK ICU 7.5.1 以指定測試裝置的原帳密發布到 RTSP `8554/TCP`，關閉 `Use SSL?`，沿用 `live/<team>/<member>/VIDEO_1`。ATAK CIV 5.7.0.15 的人物 Video 連結已改為 `rtsp`，因此不再落入早先 RTSPS 的 `raw` 解析問題。

但第一次 RTSP 嘗試仍失敗：實際 CoT 的 `__video/@url` 含帳密，子項 `ConnectionEntry` 沒有帳密，也沒有 `rtspReliable`；ATAK 紀錄中的播放器位址缺少帳密，並在 `MediaProcessor.createFromRtspNative` 發生例外。

依使用者要求，雲端 MediaMTX 新增**只允許指定單一對外 IPv4、不帶帳密讀取指定測試裝置的完整路徑**的例外後，使用者重新發布，並確認 **ATAK 可以觀看影像**。

## 設定與驗證範圍

| 項目 | 設定或觀察 |
| --- | --- |
| ICU 發布 | RTSP、通訊埠 `8554`、SSL 關閉；仍須原帳密 |
| 人物 Video | `rtsp://<media-host>:8554/live/<team>/<member>/VIDEO_1`；ATAK 的 `ConnectionEntry` 可不帶帳密 |
| 防火牆 | 僅允許操作人員指定 IPv4 `/32` 的 TCP `8554`、UDP `8000–8001`；舊的全來源 RTSP 規則仍停用 |
| MediaMTX 讀取例外 | `user: any`、空密碼、`ips` 限定同一 `/32`；唯一權限為 `read`，唯一完整路徑為 `live/<team>/<member>/VIDEO_1` |
| 串流尚未上線時 | 允許來源無帳密 `DESCRIBE` 回應 `404`，表示授權通過但沒有串流 |
| 存取邊界 | 無帳密讀取其他成員、其他小隊及 `ANNOUNCE` 發布，各回應 `401`；VM loopback 無帳密讀取也回應 `401` |
| 重新發布後 | 允許來源無帳密 `DESCRIBE`、兩條 TCP `SETUP` 與 `PLAY` 均回應 `200`；獨立讀取端收到 H.264、KLV 兩條軌道的 RTP，未保存媒體內容 |
| ATAK 實機 | MediaMTX 顯示符合允許來源的 UDP 觀看工作階段；使用者確認畫面可觀看 |

此例外只放寬指定 IP 對指定路徑的讀取，沒有開放無帳密發布。MediaMTX 的內部 `read` 授權會套用到其讀取協定；不是只在 RTSP 加一個免登入選項。既有帳密與其他身分權限均保留。

## 與先前 SSL 測試的關係

[同日先前的 SSL 測試](2026-09-30-icu-ssl-atak-rtsps.md)確認 ATAK 5.7.0.15 無法直接播放 ICU 的 `rtsps` 人物連結。這次成功的是雲端 RTSP 加上限定 IP 的無帳密讀取，並不表示 RTSPS 已獲此版本播放器支援。

先前 Windows／Docker Desktop 的 ICU 純 RTSP 曾因媒體逾時失敗；此次雲端 MediaMTX 開啟 TCP／UDP RTSP 傳輸並映射 RTP／RTCP，實際接受 ICU 的 UDP 發布。兩者是不同部署，不能互相取代驗證結果。

本次確認指定測試裝置的單一路串流及該 ATAK 觀看端可用，未驗證多裝置、長時間或行動網路 IP 變動後的觀看。行動網路對外 IP 改變時，須更新防火牆與 MediaMTX 的 `ips`。完整重新佈建會移除這項測試例外，需另行明確套用。

測試來源的實際對外 IP 列為私人資訊；文件僅以「指定來源 IPv4 `/32`」描述，不記錄實際位址。網域、帳密、人物 UID、呼號、裝置識別碼及本機使用者目錄亦未記入本文件。完整設定與原始紀錄僅保存在受控且由 Git 忽略的 `runtime/`。
