# 通訊埠與連線方向

本頁依 2026-09-26 的 `compose.yaml`、MediaMTX 設定及 Windows 防火牆腳本整理目前使用的通訊埠。實際的主機位址與允許網段由 `.env` 的 `TAK_BIND_IP`、`TAK_ALLOWED_SUBNET` 決定；換網路時應同步調整。表中「區域網路」表示 Docker 綁定該 Windows 位址，**不代表已向網際網路開放**。防火牆仍須依來源網段另外設定。

## 裝置連入 Windows 主機

| 主機通訊埠 | 協定 | 服務與用途 | Compose 容器端 | 範圍與注意事項 |
| --- | --- | --- | --- | --- |
| `8089` | TCP／TLS | ATAK 的 TAK CoT 連線，使用裝置憑證 | TAK Server `8089` | 區域網路；Windows TAK 防火牆規則限制來源網段 |
| `8443` | TCP／HTTPS | TAK API、ATAK Data Packages 下載 | TAK Server `8443` | 區域網路；部分 API 使用管理用戶端憑證。`.env` 可改主機映射，但 ATAK 的套件下載仍須驗證固定入口 |
| `40000` | TCP／TLS、UDP | Mumble 控制連線與語音媒體；Vx 使用 | Mumble `64738` TCP／UDP | 區域網路；防火牆使用前景工作階段，Ctrl+C 清除此工作階段的規則 |
| `8554` | TCP | MediaMTX RTSP 控制與 TCP 媒體 | MediaMTX `8554` | 區域網路；可用帳密發布或讀取，明文 RTSP 只在受控網路或 VPN 使用 |
| `8000`、`8001` | UDP | RTSP 的 RTP／RTCP 媒體 | MediaMTX 同號 | 區域網路；已映射，Docker Desktop 與裝置端 UDP 傳輸仍須另行驗收 |
| `8322` | TCP／TLS | MediaMTX RTSPS；ICU 影像發布的主要入口 | MediaMTX `8322` | 區域網路；憑證名稱及發布帳密均須正確 |
| `8004`、`8005` | UDP | RTSPS 的 SRTP／SRTCP 媒體 | MediaMTX 同號 | 區域網路；已映射，UDP 媒體仍須另行驗收 |
| `8889` | TCP／HTTP | 匿名 WebRTC 觀看頁與信令入口 | Viewer gateway `8889` | 區域網路；目前只驗證熱點觀看。若要網際網路觀看，還需網域、HTTPS、NAT 與 ICE 驗收 |
| `8189` | TCP、UDP | 公開 WebRTC 觀看的 ICE 媒體連線 | MediaMTX viewer `8189` | 區域網路；`8889` 可開頁面不代表 ICE 媒體一定可達 |
| `10065` | TCP／HTTP | 限時、限次的 DPK／ICU 設定下載與 QR 連結 | Share public `8765` | 區域網路；僅在 `sharing` profile 啟動；下載內容可能含私鑰或發布密碼，分享後應停止 |

以上區域網路入口均綁定 `.env` 的 `TAK_BIND_IP`。`8443`、`10065` 的主機通訊埠可由 `.env` 的 `TAK_HTTPS_HOST_PORT`、`SHARE_PUBLIC_HOST_PORT` 調整；其餘主機映射目前固定在 `compose.yaml`。ICU 實機已驗證 `8322/TCP` RTSPS 發布，不能據此推論 UDP 媒體已驗證。

## 只供 Windows 本機或容器使用

| 主機通訊埠 | 協定 | 用途 | 對外狀態 |
| --- | --- | --- | --- |
| `127.0.0.1:10066` | TCP／HTTP | TAK 控制台；容器端 `8766`，使用管理帳密 | 只綁 Windows loopback，不供 Android 直接管理 |
| `127.0.0.1:8890` | TCP／HTTP | 控制台即時預覽的本機 WebRTC 入口；容器端 `8889` | 只綁 Windows loopback |
| `127.0.0.1:8190` | TCP、UDP | 控制台即時預覽的 ICE 媒體 | 只綁 Windows loopback |
| 無主機映射 | TCP `5432` | PostgreSQL，僅供 Compose 的 `tak-backend` 網路使用 | 不對 Windows LAN 發布 |
| 無主機映射 | TCP `9997` | MediaMTX／viewer 管理 API，供 Compose 內部控制使用 | 不對 Windows LAN 發布 |

管理頁主機通訊埠可由 `.env` 的 `SHARE_ADMIN_HOST_PORT` 調整；無論數值為何仍只綁 `127.0.0.1`。公開觀看頁與控制台預覽是不同服務，`8889/8189` 與 `8890/8190` 不可互換。

## Windows 名稱解析與防火牆

`takbox.local` 由 Windows mDNS 在 `5353/UDP`、多點傳送位址 `224.0.0.251` 回答；這不是 Docker port mapping。mDNS 在本專案須手動啟動，並依 `.env` 公告當前 Windows 位址。

| 防火牆腳本 | 允許的主機通訊埠 | 工作階段 |
| --- | --- | --- |
| `Install-TakFirewall.ps1` | `8089/TCP`、`8443/TCP` | 持久規則；變更 `.env` 後重建 |
| `Install-MumbleFirewall.ps1` | `40000/TCP`、`40000/UDP` | 前景工作階段；Ctrl+C 移除本次規則 |
| `Install-MediaMtxFirewall.ps1` | `8554`、`8322`、`8189`、`8889/TCP`；`8000`、`8001`、`8004`、`8005`、`8189/UDP` | 持久規則；限制主機位址、介面與來源網段 |
| `Install-SharePortalFirewall.ps1` | `10065/TCP` | 下載期間的前景規則；管理頁 `10066` 不開給裝置 |
| `Manage-WindowsMdns.ps1` | `5353/UDP` | Windows mDNS 規則與服務，依實際介面設定 |

通訊埠映射、Windows 防火牆與名稱解析是三個不同設定。改動 `.env` 後，先核對 Windows 介面 IP，再更新 mDNS、防火牆及 Compose；最後由裝置實測名稱解析、TLS 與服務登入。

```powershell
docker compose ps
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 8089,8443,40000,8554,8322,8889,8189,10065,10066
Get-NetUDPEndpoint | Where-Object LocalPort -in 40000,8000,8001,8004,8005,8189,8190,5353
```

這些命令檢查主機映射及監聽狀態；連線是否可用仍須從實際裝置確認。`8446` Federation、RTMP 與 SRT 目前未啟用，也沒有將任何服務驗收為網際網路可用。完整規則與重新開機步驟見[Windows 防火牆](firewall.md)，版本及容器來源見[版本參考](../reference/versions-and-ports.md)。
