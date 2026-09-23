# MediaMTX：RTSP、RTSPS 與 TAK ICU

本服務以 [MediaMTX v1.21.1](https://github.com/bluenviron/mediamtx/releases/tag/v1.21.1) 接收影像。Compose 同時啟用 RTSP `8554/TCP`、RTSPS `8322/TCP`，以及對應的 RTP／RTCP `8000-8001/UDP`、SRTP／SRTCP `8004-8005/UDP`。只開放 `test` 與 `live/` 開頭的串流路徑；其他協定與管理 API 不啟用。設定來源是[範本](../../config/mediamtx/mediamtx.yml.template)，實際含帳密設定保存在忽略版控的 `runtime/mediamtx/mediamtx.yml`。

## 簽發憑證與啟動

先完成[TAK PKI bootstrap](../getting-started.md#2-產生憑證與-tak-連線包)。現有部署**不要**用 `bootstrap_local.py --force` 取得 MediaMTX 憑證；執行獨立簽發腳本即可：

```powershell
python ./scripts/provision_mediamtx.py --dns takbox.local
docker compose up -d --no-deps mediamtx
docker compose ps mediamtx
docker compose logs --tail 40 mediamtx
```

腳本要求至少一項 `--dns`／`--ip`，以實際用戶端輸入值建立 SAN。再次執行會驗證既有憑證並重建設定，不重簽憑證或更換現有密碼。憑證檔案不完整或 SAN 不相符時會停止，需先調查；不可直接重建整套 TAK PKI。

MediaMTX 使用 TAK Root → 中繼簽發 CA 簽出的**獨立葉憑證及私鑰**。`runtime/pki/mediamtx-fullchain.pem` 由葉憑證與中繼 CA 組成；MediaMTX 專用私鑰未加密，因容器啟動需要直接讀取，僅存於忽略版控的 `runtime/pki/` 並唯讀掛載。不要把私鑰、實際設定或 `runtime/secrets/` 加入 Git。TAK ICU 是否信任 ATAK 匯入的 CA，仍須實機確認；同一 CA 簽發本身不保證所有 App 都採用該信任設定。

需要從熱點裝置連入時，在一般 PowerShell 執行[MediaMTX 防火牆腳本](../../scripts/Install-MediaMtxFirewall.ps1)並核准 UAC。它只允許指定主機位址、介面及網段進入上述通訊埠：

```powershell
./scripts/Install-MediaMtxFirewall.ps1
```

## 發布及讀取權限

帳號固定為 `atak-publisher` 和 `atak-viewer`。前者只有 `publish` 權限，後者只有 `read` 權限；密碼分別在 `runtime/secrets/mediamtx_publish_password` 和 `runtime/secrets/mediamtx_read_password`。初次執行簽發腳本時才產生密碼。需要手動輸入 ICU 時，在本機終端機讀取發布密碼，**不要把輸出貼到聊天、截圖或版控**：

```powershell
Get-Content ./runtime/secrets/mediamtx_publish_password
```

純 RTSP 沒有 TLS，僅供受信任 LAN／VPN 測試；RTSPS 會使用伺服器 TLS 憑證。帳密是發布／讀取授權，不等於用戶端憑證登入。`rtspEncryption: optional` 讓兩種入口同時存在；未來若所有用戶端都完成 RTSPS 驗證，可另評估改為 `strict`。[MediaMTX RTSP 說明](https://mediamtx.org/docs/features/rtsp-specific-features)、[認證說明](https://mediamtx.org/docs/features/authentication)。

## TAK ICU 設定與實測範圍

若要透過 ICU 專屬 QR Code 佈建這些欄位，請見[ICU QR Code 格式與驗證](icu-qrcode.md)。

本機 TAK ICU 7.5.1 的 `Use SSL?` 設定會選擇 RTSPS。2026-09-23 實機已使用 RTSPS 與發布帳密成功送出 `live/VIDEO_1`，再由獨立讀取帳號經 RTSPS 讀取；這不證明 ICU 內部是否嚴格檢查了憑證鏈。設定如下：

| ICU 欄位 | RTSPS 測試值 | RTSP 回退測試值 |
| --- | --- | --- |
| Server IP | `takbox.local` | `takbox.local` |
| Server Port | `8322` | `8554` |
| Stream Path | `live/` | `live/` |
| Username | `atak-publisher` | `atak-publisher` |
| Password | 發布密碼檔的內容 | 同左 |
| Use SSL? | 勾選 | 不勾選 |

`Server IP` 只填名稱，不加 `rtsps://` 或通訊埠；`Stream Path` 只填 `live/`，ICU 會自行接上串流識別名稱。路徑必須符合 `live/<名稱>`；`test` 僅供 FFmpeg 驗證。若使用 IP 連 RTSPS，憑證 SAN 必須有相符 `IP:` 項目，不能只靠 DNS SAN。

目前這台 ICU 的純 RTSP（`8554`、不勾選 SSL）雖能建立 `live/VIDEO_1` session，卻在約 10 秒後因媒體逾時失敗。故上表右欄是診斷用設定，**不是已驗證可用的 ICU 回退路徑**。本機使用 RTSPS over TCP；若未來透過 VPN 使用 RTSP，須重新確認 ICU 的媒體傳輸及 Docker／Linux 網路路徑，不能只改連線位址。

啟動後看 `docker compose logs -f mediamtx`：`is publishing to path 'live/...'` 才表示已送達伺服器。要在 ATAK 或其他播放器觀看，另使用 `atak-viewer` 帳號與**實際發布路徑**；ATAK 內建播放器的 RTSPS 相容性仍須另測。第三方 [OpenTAK ICU 的說明](https://docs.opentakserver.io/opentak_icu/index.html)曾指出原廠 TAK ICU 對「RTSPS＋帳密」有相容性疑慮，但本次安裝的 7.5.1 已完成這項組合的發布與讀取驗證。

## 伺服器端驗證

使用固定的官方 FFmpeg 測試映像，腳本不會顯示密碼：

```powershell
python ./scripts/test_mediamtx_stream.py --include-udp
python ./scripts/test_mediamtx_stream.py --via-host
```

第一個測試從 Compose 網路驗證 RTSP／RTSPS 的 TCP 與 UDP 發布、讀取，並從 Windows 驗證 RTSPS 憑證鏈及 SAN。第二個從獨立 Docker bridge 測 Windows 已發布的 TCP 入口。Docker Desktop 的 UDP NAT 可能使跨 bridge 的 RTP／SRTP 接收失敗，這不能用內部網路測試結果代替 Android 端的 UDP 驗收。實際結果見[驗證紀錄](../validation/2026-09-23-mediamtx.md)。
