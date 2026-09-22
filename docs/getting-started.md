# 從零建置 TAK Server 與 Mumble

本教學從官方 5.8 Hardened ZIP 開始，完成三個容器啟動、ATAK 憑證連線與 Vx 加入語音頻道。適用版本與目前驗證範圍見[版本表](reference/versions-and-ports.md)及[驗證索引](validation/README.md)。

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

準備官方 `takserver-docker-hardened-5.8-RELEASE-84.zip`。啟用 Windows 行動熱點，讓主機持有 `192.168.137.1`，Android 連到此熱點。其他網段先依[網路調整說明](network/mdns.md#變更名稱或網段)修改設定，再簽發憑證。

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
python ./scripts/bootstrap_local.py --host takbox.local --ip 192.168.137.1 --client-name atak-client
```

腳本產生 Root CA、中繼 CA、獨立葉憑證、CRL、服務設定、密碼及 `runtime/packages/atak-local-test.dpk`，並執行憑證檢查。成功後應有 `runtime/tak/CoreConfig.xml` 及上述 DPK。

若腳本回報既有部署，先確認檔案來源再繼續。`--force` 會重建整套憑證與密碼，不能當成一般重試參數。詳細原理與更新方式見[憑證頁](security/certificates.md)。

## 3. 啟用名稱解析與防火牆

一般 PowerShell 執行 mDNS 安裝，依提示核准 UAC：

```powershell
./scripts/Install-WindowsMdns.ps1
./scripts/Test-WindowsMdns.ps1
```

名稱應解析到主機熱點 IP。TAK 防火牆腳本目前需要在**管理員 PowerShell** 執行：

```powershell
./scripts/Install-TakFirewall.ps1
```

另開一般 PowerShell，啟動 Mumble 防火牆工作階段並核准 UAC：

```powershell
./scripts/Install-MumbleFirewall.ps1
```

看到 `Mumble firewall active` 後保留兩個相關視窗，後續命令在另一個終端機執行。按 Ctrl+C 會清除該工作階段的規則。連線範圍與中斷限制見[防火牆頁](network/firewall.md)。

## 4. 建置並啟動服務

```powershell
docker compose build tak-db tak-server
docker compose up -d tak-db tak-server mumble
docker compose ps
docker compose logs --tail 100 tak-db tak-server mumble
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

應建立或找到 `Primary` 與 `Alternate`。最後確認 `docker compose ps` 的三項服務皆為 healthy。

## 6. 在 Android 匯入與連線

1. 將 `runtime/packages/atak-local-test.dpk` 透過受控方式交付指定裝置。
2. 在 ATAK 使用 Import → Local SD 匯入，確認 TAK 連線為 `takbox.local:8089:ssl`。細節見[ATAK 連線](atak/connection.md)。
3. 載入 Vx，依[Vx 手動設定](atak/vx-missions.md#手動建立第一個頻道)加入 `Primary`。Alias 可用 `P1`，Channel 不留空。
4. 需要密碼時，使用 `runtime/secrets/mumble_server_password`。已有註冊身分時可能直接登入。

第一次環境可先手動建立 Vx 頻道，再匯出原生任務作為後續 DPK 範本。已有 Vx-only 套件時，改走[TAK Server 下載流程](atak/vx-missions.md#從-tak-server-下載任務)；本次版本的一般 Local SD 匯入不會建立 Vx 任務。

## 7. 判斷是否完成

| 檢查 | 應觀察到的結果 |
| --- | --- |
| 容器 | `tak-db`、`tak-server`、`mumble` 皆 healthy |
| 名稱解析 | Android 能將 `takbox.local` 解析到主機 |
| ATAK | 指定 TAK 伺服器連線成功，沒有憑證信任錯誤 |
| Vx | 正確任務及頻道可見，Mumble 確認驗證成功並加入頻道 |
| 語音 | 有第二個用戶端時，另測雙向 PTT 與 UDP；未測就記錄為待驗 |

連線成功不代表音訊驗收完成。若只是暫停服務，可用 `docker compose stop`，之後以 `docker compose up -d` 啟動；資料 volume 會保留。重新開機後先確認熱點、mDNS 與防火牆，再啟動服務，見[重新開機流程](network/firewall.md#重新開機後)。
