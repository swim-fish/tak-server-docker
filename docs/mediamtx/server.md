# MediaMTX：RTSP、RTSPS 與 TAK ICU

本服務以 [MediaMTX v1.21.1](https://github.com/bluenviron/mediamtx/releases/tag/v1.21.1) 接收影像。Compose 啟用 RTSP `8554/TCP` 與 RTSPS `8322/TCP`，**只接受 TCP 傳輸**（`rtspTransports: [tcp]`），媒體以 TCP interleaved 在同一條連線傳送。發布路徑限於 `test` 與 `live/` 開頭；MediaMTX 管理 API 只在 Compose 網路內使用。另有獨立的 WebRTC viewer 與控制台預覽服務，見[MediaMTX 管理](management.md)。設定來源是[範本](../../config/mediamtx/mediamtx.yml.template)，實際含帳密設定保存在忽略版控的 `runtime/mediamtx/mediamtx.yml`。

來源到播放端的完整處理流程與逐段 TLS 說明見[本機影像處理與流向](video-flow.md)。

雲端 NetBird 部署的操作與權限另見 [NetBird 影音流程](../network/netbird-user-guide.md#3-publish-icu-and-view-in-atak)：所有發布仍需帳密，純 RTSP 觀看可在 peer／路徑授權後免帳密；RTSPS、RTMP、RTMPS 與 WebRTC 觀看保留驗證。下列 Compose 與早期本機實測不等同雲端設定。

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

現行發布身分依 ICU 小隊或一般裝置分配獨立帳密及完整路徑權限，由[管理頁](management.md)建立與輪替。舊的 `atak-publisher` 共用帳號暫時保留給既有裝置；`atak-viewer` 是 MediaMTX 上游讀取帳號。兩者密碼分別在 `runtime/secrets/mediamtx_publish_password` 和 `runtime/secrets/mediamtx_read_password`，初次執行簽發腳本時產生。只有手動維護舊 ICU 設定時才在本機終端機讀取共用發布密碼，**不要把輸出貼到聊天、截圖或版控**：

```powershell
Get-Content ./runtime/secrets/mediamtx_publish_password
```

> **Windows Docker Desktop UDP 限制：**Docker Desktop 轉送已發布的 UDP 通訊埠時會改寫來源通訊埠，MediaMTX 無法把 RTP／RTCP 對應到 `SETUP` 宣告的 `client_port`，UDP 發布約 10 秒後 `session timed out`。因此本機 Compose 限制為 TCP 模式，不映射 `8000-8001/UDP`、`8004-8005/UDP`；要求 UDP 的用戶端會收到 `461 Unsupported Transport`，支援自動協商者改用 TCP。原生 Linux Docker 遷移後可重新評估。封包證據見 [2026-10-02 紀錄](../validation/2026-10-02-windows-docker-udp-rtsp.md)。

純 RTSP 沒有 TLS，僅供受信任 LAN／VPN 測試；RTSPS 會使用伺服器 TLS 憑證。帳密是發布／讀取授權，不等於用戶端憑證登入。`rtspEncryption: optional` 讓兩種入口同時存在；未來若所有用戶端都完成 RTSPS 驗證，可另評估改為 `strict`。[MediaMTX RTSP 說明](https://mediamtx.org/docs/features/rtsp-specific-features)、[認證說明](https://mediamtx.org/docs/features/authentication)。

## TAK ICU 設定與實測範圍

若要透過 ICU 專屬 QR Code 佈建這些欄位，請見[ICU QR Code 格式與驗證](icu-qrcode.md)。

**ATAK 5.7.0.15 相容性限制：**ICU 7.5.1 啟用 `Use SSL?` 後，人物 CoT 的 Video 連結使用 `rtsps`。2026-09-30 雲端實測中，ICU 發布成功，實際連結以原帳密通過公開 TLS 驗證並取得 `DESCRIBE 200 OK`；ATAK 仍將 `rtsps` 解析為 `raw`，在人物 Video 顯示 `Failed to Connect`。增加觀看權限不會改變此版本的協定解析。完整觀察見[SSL 與 ATAK RTSPS 實測](../validation/2026-09-30-icu-ssl-atak-rtsps.md)。該日期未驗證取消 SSL 的替代方案；後續 NetBird 流程已確認 ICU 純 RTSP 發布及同隊 ATAK 人物 Video 可觀看，見 [2026-10-01 紀錄](../validation/2026-10-01-netbird-tak-media-voice.md)。

本機 TAK ICU 7.5.1 的 `Use SSL?` 設定會選擇 RTSPS。2026-09-23 實機以舊共用帳密成功送出 `live/VIDEO_1`，再由獨立讀取帳號經 RTSPS 讀取；2026-09-24 另以 Alpha 小隊 QR 成功發布 `live/alpha/1/VIDEO_1` 並在 Chrome 觀看。這不證明 ICU 內部是否嚴格檢查了憑證鏈。下表保留早期手動測試值；新裝置建議由控制台取得小隊 QR：

| ICU 欄位 | RTSPS 測試值 | RTSP 回退測試值 |
| --- | --- | --- |
| Server IP | `takbox.local` | `takbox.local` |
| Server Port | `8322` | `8554` |
| Stream Path | `live/` | `live/` |
| Username | `atak-publisher` | `atak-publisher` |
| Password | 發布密碼檔的內容 | 同左 |
| Use SSL? | 勾選 | 不勾選 |

`Server IP` 只填名稱，不加 `rtsps://` 或通訊埠；`Stream Path` 只填 `live/`，ICU 會自行接上串流識別名稱。路徑必須符合 `live/<名稱>`；`test` 僅供 FFmpeg 驗證。若使用 IP 連 RTSPS，憑證 SAN 必須有相符 `IP:` 項目，不能只靠 DNS SAN。

早期本機測試中，ICU 的純 RTSP（`8554`、不勾選 SSL）雖能建立 `live/VIDEO_1` session，卻在約 10 秒後因媒體逾時失敗。2026-10-02 已確認原因是 Windows Docker Desktop 改寫 UDP 來源通訊埠，見上方限制；本機改為 TCP-only 後，ICU QR 預設純 RTSP `8554`，**ICU 實機是否自動改用 TCP 仍待驗收**。後續雲端 NetBird RTSP 已通過上述驗證；移到其他部署時，仍須確認 ICU 的媒體傳輸及 Docker／Linux 網路路徑。

啟動後看 `docker compose logs -f mediamtx`：`is publishing to path 'live/...'` 才表示已送達伺服器。其他播放器使用 `atak-viewer` 讀取帳號與**實際發布路徑**。2026-09-25 實測發現，ATAK CIV 5.7.0.15 無法直接播放 ICU 自動通告的 RTSPS 來源；手動建立 `rtsp://takbox.local:8554/live/alpha/1/VIDEO_1` 影像來源，填入 `atak-viewer` 的獨立讀取密碼並勾選 **Reliable P2P Connection (consumes more resources)** 後，實機成功顯示 1280×720 影像。未勾選時，H.264 與 KLV 的 RTSP SETUP 傳輸方式不一致，MediaMTX 會關閉連線。純 RTSP 觀看沒有 TLS，只在受控區域網路或 VPN 使用；步驟與 log 見[ATAK 觀看實測](../validation/2026-09-25-atak-icu-viewer.md)。

## 伺服器端驗證

使用固定的官方 FFmpeg 測試映像，腳本不會顯示密碼：

```powershell
python ./scripts/test_mediamtx_stream.py --include-udp
python ./scripts/test_mediamtx_stream.py --via-host
```

第一個測試從 Compose 網路驗證 RTSP／RTSPS 的 TCP 發布、讀取，確認 RTSP UDP 被拒，並從 Windows 驗證 RTSPS 憑證鏈及 SAN。第二個從獨立 Docker bridge 測 Windows 已發布的 TCP 入口；可加 `--include-udp` 確認經主機的 UDP 同樣被拒。FFmpeg 對 `rtsps://` 一律使用 TCP，因此 UDP 拒絕只檢查純 RTSP。實際結果見[驗證紀錄](../validation/2026-09-23-mediamtx.md)。
