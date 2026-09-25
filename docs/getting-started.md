# 從零建置 TAK Server、Mumble 與 MediaMTX

本教學從官方 5.8 Hardened ZIP 開始，完成 TAK、資料庫、Mumble 與 MediaMTX 四個容器啟動、ATAK 憑證連線、Vx 語音與 ICU 影像連線。適用版本與目前驗證範圍見[版本表](reference/versions-and-ports.md)及[驗證索引](validation/README.md)。

希望由一支腳本完成首次建置與 Compose 啟動，可使用[首次建置腳本](scripts/first-time-setup.md)。以下保留逐步手動流程，方便檢查每項產物。

## 開始前

需要 Windows、Docker Desktop 的 Linux containers、Python 3.14、OpenSSL，以及包含 `keytool` 的 JDK 17。mDNS 安裝腳本目前固定使用 `C:/Python314/python.exe`，請先將 Python 3.14 安裝在該位置；只有 PATH 內的 Python 不足以滿足此腳本。第一次建置需下載基礎映像與套件。先在專案根目錄確認：

```powershell
docker version
docker compose version
python --version
Test-Path C:/Python314/python.exe
openssl version
keytool -help
```

準備官方 `takserver-docker-hardened-5.8-RELEASE-84.zip`。讓 Windows 主機與 Android 連到相同的 Wi-Fi 或行動熱點。在專案根目錄將 `.env.example` 複製為 `.env`，設定 `TAK_BIND_IP` 為主機目前的 IPv4 位址、`TAK_ALLOWED_SUBNET` 為裝置所在網段；Compose、mDNS 與防火牆腳本會讀取這兩個值。預設範例為 Windows 熱點 `192.168.137.1/24`。詳細步驟見[網路調整說明](network/mdns.md#變更名稱或網段)。

以下為全新部署。已有 `runtime/` 或資料庫時，請改讀[維運](tak-server/operations.md)，不要用 `bootstrap_local.py --force` 解決一般連線問題。

## 1. 解壓官方套件

將 `$zip` 換成實際檔案位置：

```powershell
$zip = 'C:/path/to/takserver-docker-hardened-5.8-RELEASE-84.zip'
New-Item -ItemType Directory -Path ./vendor -Force | Out-Null
Expand-Archive -LiteralPath $zip -DestinationPath ./vendor
Test-Path ./vendor/takserver-docker-hardened-5.8-RELEASE-84/tak/CoreConfig.example.xml
Test-Path ./vendor/takserver-docker-hardened-5.8-RELEASE-84/docker/Dockerfile.hardened-takserver
```

兩項應回傳 `True`。完整套件留在 `vendor/`；`runtime/tak/` 由下一步產生，不必複製整個官方 `tak/`。各檔案用途見[目錄參考](reference/runtime-layout.md)。

## 2. 產生憑證與 TAK 連線包

```powershell
python ./scripts/bootstrap_local.py --host takbox.local --client-name atak-client
```

腳本產生 Root CA、中繼 CA、獨立葉憑證、CRL、服務設定、密碼及 `runtime/packages/atak/atak-local-test.dpk`，並執行憑證檢查。成功後應有 `runtime/tak/CoreConfig.xml` 及上述 DPK。

腳本沒有預填 DNS 或 IP，必須至少指定 `--host`（別名 `--dns`）或 `--ip`；兩者都未指定、空白或格式錯誤時，會在產生或清除 runtime 前停止。上述教學明確選用 DNS，讓 IP 改變時可沿用名稱與憑證。

| 輸入選項 | TAK／Mumble SAN | 憑證 CN 與 DPK 連線位址 |
| --- | --- | --- |
| `--host takbox.local` | 只有 DNS | `takbox.local` |
| `--ip 192.168.137.1` | 只有 IP | `192.168.137.1` |
| `--host takbox.local --ip 192.168.137.1` | DNS＋IP | 優先使用 `takbox.local` |

這些參數不會修改 Compose、mDNS 或防火牆。使用 DNS 時，IP 變動後須同步更新名稱解析、服務綁定與防火牆。選用 IP-only 時，除了 Vx Address 與管理工具，TAK、Mumble 的健康檢查也要改用相符的 IP；TAK 的 curl 探測應使用 IP URL，移除原本的 `--resolve takbox.local:8443:127.0.0.1`。Mumble 範例見[IP-only 維運](mumble/server.md#使用-ip-only-憑證)。

若腳本回報既有部署，先確認檔案來源再繼續。`--force` 會重建整套憑證與密碼，不能當成一般重試參數。詳細原理與更新方式見[憑證頁](security/certificates.md)。

MediaMTX 另以同一中繼 CA 簽發專用葉憑證，並產生互不相同的發布／讀取密碼：

```powershell
python ./scripts/provision_mediamtx.py --dns takbox.local
```

若前一步選用 IP-only，改傳相符的 `--ip`。此腳本不重建 TAK 或 Mumble 憑證，詳細設定見[MediaMTX](mediamtx/server.md)。

## 3. 啟用名稱解析與防火牆

一般 PowerShell 開啟 mDNS 管理選單，選「安裝／修復並啟動」，依提示核准 UAC：

```powershell
./scripts/Manage-WindowsMdns.ps1
./scripts/Test-WindowsMdns.ps1
```

名稱應解析到 `.env` 的主機 IP。TAK 防火牆腳本會在一般 PowerShell 視需要請求 UAC：

```powershell
./scripts/Install-TakFirewall.ps1
```

另開一般 PowerShell，啟動 Mumble 防火牆工作階段並核准 UAC：

```powershell
./scripts/Install-MumbleFirewall.ps1
```

看到 `Mumble firewall active` 後保留兩個相關視窗，後續命令在另一個終端機執行。按 Ctrl+C 會清除該工作階段的規則。連線範圍與中斷限制見[防火牆頁](network/firewall.md)。

MediaMTX 防火牆腳本先確認熱點 IP，再依提示請求 UAC，建立 RTSP／RTSPS TCP 及媒體 UDP 的持久規則：

```powershell
./scripts/Install-MediaMtxFirewall.ps1
```

## 4. 建置並啟動服務

```powershell
docker compose build tak-db tak-server
docker compose up -d tak-db tak-server mumble mediamtx
docker compose ps
docker compose logs --tail 100 tak-db tak-server mumble mediamtx
```

首次資料庫初始化需要時間。確認服務未反覆重新啟動；若健康檢查持續失敗，依紀錄查[疑難排解](troubleshooting.md)，不要刪除 volume 重試。

## 5. 設定管理權限與頻道

TAK 啟動後，確認或重新套用管理憑證權限：

```powershell
docker compose exec -w /opt/tak tak-server java -jar utils/UserManager.jar certmod -A certs/files/admin.pem
```

裝置的群組設定依[新增一般 TAK 憑證使用者](tak-server/operations.md#新增一般憑證使用者)完成；不要給裝置憑證 `-A` 管理權限。

Mumble 啟動後建立預設頻道：

```powershell
python ./scripts/provision_mumble_channel.py
```

應建立或找到 `Primary`、`Alternate`、`Medical`、`Emergency`。確認 TAK、資料庫與 Mumble 健康，MediaMTX 容器維持 Up 並在紀錄中列出 RTSP／RTSPS listener；MediaMTX 未設定 Compose healthcheck。

## 6. 在 Android 匯入與連線

1. 將 `runtime/packages/atak/atak-local-test.dpk` 透過受控方式交付指定裝置。
2. 在 ATAK 使用 Import → Local SD 匯入，確認 TAK 連線為 `takbox.local:8089:ssl`。細節見[ATAK 連線](atak/connection.md)。
3. 載入 Vx，依[Vx 手動設定](atak/vx-missions.md#手動建立第一個頻道)加入 `Primary`。Alias 使用全名 `Primary`，Channel 不留空。
4. 需要密碼時，使用 `runtime/secrets/mumble_server_password`。已有註冊身分時可能直接登入。

第一次環境可先手動建立 Vx 頻道，再匯出原生任務作為後續 DPK 範本。已有 Vx-only 套件時，改走[TAK Server 下載流程](atak/vx-missions.md#從-tak-server-下載任務)；本次版本的一般 Local SD 與 ATAK QR 遠端匯入都不會建立 Vx 任務。TAK 憑證 DPK 可透過 ATAK QR 匯入，ICU 設定則使用自己的 QR；實機結果見[分離佈建驗證](validation/2026-09-23-qr-tak-vx-icu.md)。

需要 ICU 影像時，依[MediaMTX 的 TAK ICU 設定](mediamtx/server.md#tak-icu-設定與實測範圍)填入 `takbox.local:8322`、`live/`、發布帳密並勾選 `Use SSL?`。伺服器紀錄應出現 `is publishing to path 'live/...'`；觀看端另用讀取帳號。

## 7. 判斷是否完成

| 檢查 | 應觀察到的結果 |
| --- | --- |
| 容器 | `tak-db`、`tak-server`、`mumble` 皆 healthy；`mediamtx` 為 Up 且兩個 listener 已啟動 |
| 名稱解析 | Android 能將 `takbox.local` 解析到主機 |
| ATAK | 指定 TAK 伺服器連線成功，沒有憑證信任錯誤 |
| Vx | 正確任務及頻道可見，Mumble 確認驗證成功並加入頻道 |
| ICU／MediaMTX | ICU 經 RTSPS＋帳密發布，MediaMTX 紀錄出現實際 `live/` 路徑，讀取帳號可取得影像 |
| 語音 | 有第二個用戶端時，另測雙向 PTT 與 UDP；未測就記錄為待驗 |

連線成功不代表音訊驗收完成。若只是暫停服務，可用 `docker compose stop`，之後以 `docker compose up -d` 啟動；資料 volume 會保留。重新開機後先確認熱點、mDNS 與防火牆，再啟動服務，見[重新開機流程](network/firewall.md#重新開機後)。
