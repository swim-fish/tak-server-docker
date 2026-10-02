# 2026-10-02 Windows Docker Desktop UDP RTSP 限制與 TCP-only 模式

## 結論

Windows 上的 Docker Desktop 轉送已發布的 UDP 通訊埠時，會改寫封包的來源位址與**來源通訊埠**。RTSP UDP 發布時，用戶端在 `SETUP` 宣告 `client_port`，MediaMTX 依「來源 IP＋宣告的通訊埠」辨識 RTP／RTCP；改寫後的封包無法對應到工作階段而被丟棄，約 10 秒後出現 `session timed out`。這與早期本機 ICU 純 RTSP「建立 session 後約 10 秒媒體逾時」的現象一致。

因此本機 Compose 的 MediaMTX 主節點改為 `rtspTransports: [tcp]`，移除 `8000-8001/UDP` 與 `8004-8005/UDP` 的主機映射與防火牆規則。要求 UDP 的用戶端收到 `461 Unsupported Transport`；會自動協商的用戶端改用 TCP interleaved。

## 測試環境

- Windows 11、Docker Desktop 29.8.1（WSL2），MediaMTX 1.21.1，`bluenviron/mediamtx:1.21.1-ffmpeg` 作為模擬發布端與讀取端。
- 啟動 `mediamtx`、`media-viewer`、`media-viewer-gateway`、`media-preview`、`share-admin`、`share-public`；未啟動 TAK 與資料庫。
- 「經主機」指 FFmpeg 容器在 Docker 預設 bridge，以 `takbox.local` 指向 `.env` 的 `TAK_BIND_IP`，走與 LAN 裝置相同的已發布通訊埠。
- 發布身分使用控制台 ICU QR 內的小隊帳密，路徑 `live/alpha/1/VIDEO_1`；讀取使用 `atak-viewer`、RTSP／TCP，與 ATAK Video Alias 的 Reliable 設定相同。

本紀錄不含帳密、實際綁定位址或裝置識別資訊。

## 對照結果

| 情境 | 發布 | 讀取 30 秒 | 結果 |
| --- | --- | --- | --- |
| 修改前，Compose 網路內直接連 `mediamtx` | RTSP／UDP | 433 影格 | 通過；MediaMTX 的 UDP 處理正常 |
| 修改前，經主機 | RTSP／UDP | 無軌道 | 失敗；10 秒後 `session timed out` |
| 修改前，經主機 | RTSP／TCP | 432 影格 | 通過 |
| 修改後，經主機 | RTSP／UDP（強制） | — | `SETUP` 回應 `461 Unsupported Transport`，符合預期 |
| 修改後，經主機 | RTSP，FFmpeg 自動協商 | 433 影格 | 通過；改用 TCP |
| 修改後，經主機 | RTSP／TCP | 433 影格 | 通過 |
| 修改後，`test_mediamtx_stream.py --include-udp` 與 `--via-host --include-udp` | RTSP／RTSPS TCP；RTSP UDP | — | TCP 發布／讀取通過，RTSP UDP 拒絕，兩種模式均 exit 0 |

## 封包證據

修改前經主機以 UDP 發布時，在 `mediamtx` 容器的網路命名空間擷取（只保留傳輸欄位）：

```text
RTSP SETUP  Transport: RTP/AVP/UDP;unicast;client_port=28836-28837;mode=record
RTP   <docker-gateway>:45644 -> mediamtx:8000   (宣告為 28836)
RTCP  <docker-gateway>:36927 -> mediamtx:8001   (宣告為 28837)
```

190 個 RTP／RTCP 封包有到達容器，但來源通訊埠與宣告值不同。TCP interleaved 的媒體在同一條 RTSP 連線內傳送，不需要比對來源通訊埠，因此不受影響。

## 界線

- 發布端是經 Windows 主機路徑的 Docker 容器，不是實體手機；Docker Desktop 對所有已發布通訊埠使用同一轉送機制，LAN 裝置預期有相同行為，但本次未以手機擷取封包。
- 尚未驗證 TAK ICU 7.5.1 收到 `461` 後是否自動改用 TCP；須以實機確認 MediaMTX 紀錄出現 `is publishing to path` 且持續超過 10 秒。
- FFmpeg 對 `rtsps://` 一律使用 TCP，無法用它測試 RTSPS 的 SRTP／UDP；RTSPS UDP 一併停用。
- 原生 Linux Docker 以 iptables DNAT 轉送外部連線，通常保留來源位址與通訊埠；雲端 VM 的 ICU UDP 發布成功屬於不同部署。Linux 遷移後可重新評估啟用 UDP。
