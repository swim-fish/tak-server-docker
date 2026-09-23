# 版本、通訊埠與上游套件

以下是 2026-09-23 專案設定及實測版本。主機位址與通訊埠以 [compose.yaml](../../compose.yaml) 為準；改動時同步更新本頁及相關指令範例。

## 版本

| 元件 | 版本或依據 |
| --- | --- |
| 官方套件 | `takserver-docker-hardened-5.8-RELEASE-84.zip` |
| TAK／資料庫映像標籤 | `takserver-hardened:5.8-release-84`／`takserver-db-hardened:5.8-release-84` |
| TAK 執行環境 | Java 17；資料庫套件為 PostgreSQL 18／PostGIS 3.6 |
| Mumble 映像 | `mumblevoip/mumble-server:v1.5.915-1` |
| MediaMTX 映像 | `bluenviron/mediamtx:1.21.1`；測試使用 `1.21.1-ffmpeg` |
| Android 實測 | ATAK-CIV `5.7.0.15` release；Vx `2.1.0 (20251122) - [5.6.0]` |

Vx 標籤中的 `[5.6.0]` 是套件標示；與 ATAK 5.7 的可用性以本次實測為限，不保證其他版本組合。官方一般版、hardened 版或既有 5.7 資料庫間的升級，不在本次全新建置驗收範圍。

## 網路預設值

| 用途 | 主機端 | 容器端／說明 |
| --- | --- | --- |
| Windows 行動熱點 | `192.168.137.1`／`192.168.137.0/24` | 裝置需在允許子網路內 |
| 名稱 | `takbox.local` | mDNS 指向主機 LAN IP |
| TAK CoT TLS | `8089/TCP` | `8089/TCP` |
| TAK 管理 API | `8443/TCP` | `8443/TCP`，使用管理用戶端憑證 |
| Mumble | `40000/TCP`、`40000/UDP` | `64738/TCP`、`64738/UDP` |
| MediaMTX RTSP | `8554/TCP`、`8000-8001/UDP` | TCP 控制／媒體、UDP RTP／RTCP |
| MediaMTX RTSPS | `8322/TCP`、`8004-8005/UDP` | TLS 控制／TCP 媒體、UDP SRTP／SRTCP |
| 分享下載與 QR | `8765/TCP`，綁定熱點 IP | 僅在 `sharing` profile 啟動 |
| 分享與 Mumble 管理 | `127.0.0.1:8766/TCP` | 僅 Windows 主機可連；Mumble 操作需前景管理程式 |
| PostgreSQL | 不發布 | `5432/TCP`，限 `tak-backend` |
| mDNS | `5353/UDP` | Windows multicast，非 Compose port mapping |

`64400` 是歷史測試通訊埠。`40000` 避開 Windows 預設動態範圍 `49152–65535`，但仍須檢查實際占用及排除區間，不能保證所有主機都可使用。

`8446` 與 Federation 通訊埠仍未發布。MediaMTX 的 TCP 入口已由 Android 確認可達；UDP 對外媒體尚待實機驗收，見[MediaMTX 實測](../validation/2026-09-23-mediamtx.md)。

## 上游套件與本專案的差異

- 官方 `docker/Dockerfile.hardened-takserver` 與 `Dockerfile.hardened-takserver-db` 是建置來源；完整 `vendor/` 不提交版控。
- 本專案以 `bootstrap_local.py` 讀取官方 `tak/CoreConfig.example.xml` 產生部署設定，沒有實作原始計畫的 `cert-init`、`cert-stage`、`tak-config-init` 服務。
- `docker/db-entrypoint.sh` 處理資料庫啟動，`config/tak/pg_hba.conf` 限制資料庫存取；Compose 設定 Java heap 與自己的健康檢查。
- 憑證格式與 CA 信任鏈參考官方 `makeRootCa.sh`、`makeCert.sh`，詳見[憑證頁](../security/certificates.md)。

舊計畫記錄的工具版本、registry 問題及未採用的 wrapper 設計保存在[原始建置計畫](../archive/original-deployment-plan.md)，不是現行環境的必要條件。
