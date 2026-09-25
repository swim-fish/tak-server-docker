# 首次建置腳本

`scripts/Initialize-LocalStack.ps1` 將官方 TAK Server 5.8 Hardened ZIP 轉成這個專案可啟動的本機部署。它只適用**全新**的 Windows 主機部署；已有 `runtime/`、Compose 容器或 `tak-local` volume 時會停止，不會重建 CA 或刪除資料。

## 準備資料

必須準備官方 `takserver-docker-hardened-5.8-RELEASE-84.zip`，或事先將它完整解壓至 `vendor/takserver-docker-hardened-5.8-RELEASE-84/`。不需另行複製 WAR、JAR、`makeCert.sh` 或設定檔到 `runtime/tak/`；腳本會使用官方 ZIP 的 Docker build context，並以 `bootstrap_local.py` 產生本機設定。

主機先安裝並確認 Docker Desktop（Linux containers）、Python、OpenSSL、JDK 17 的 `keytool`。Python 必須能匯入 `cryptography`；Windows mDNS 安裝另要求 `C:\Python314\python.exe`。若缺少主機 Python 相依套件，可先執行：

```powershell
python -m pip install -r .\scripts\requirements-tak-certificate-host.txt
```

先開啟 Wi-Fi 或 Windows 行動熱點，確認主機和裝置位於相同網段。將 `.env.example` 複製為 `.env`，設定 `TAK_BIND_IP` 為主機 IPv4 位址、`TAK_ALLOWED_SUBNET` 為允許裝置連線的 CIDR；首次建置腳本、Compose、mDNS 和防火牆共用這些設定。預設範例為 `192.168.137.1`／`192.168.137.0/24`。DNS 目前固定為 `takbox.local`；若更改 DNS 或通訊埠，仍須同步檢查憑證 SAN、DPK、mDNS 與服務設定。

## 執行

在專案根目錄先做不修改資料的前置檢查，再執行首次建置：

```powershell
.\scripts\Initialize-LocalStack.ps1 `
  -ZipPath 'D:\Downloads\takserver-docker-hardened-5.8-RELEASE-84.zip' `
  -CheckOnly

.\scripts\Initialize-LocalStack.ps1 `
  -ZipPath 'D:\Downloads\takserver-docker-hardened-5.8-RELEASE-84.zip'
```

請替換為 ZIP 的實際位置。如果官方套件已完整解壓在 `vendor/`，可省略 `-ZipPath`；未解壓又未指定時，腳本會在正式執行時詢問位置。若已知可信的官方 SHA-256，也可與 `-ZipPath` 同時指定 `-ExpectedZipSha256 <64 位十六進位值>`，在解壓前核對。`-ClientName` 可變更最初 ATAK DPK 的憑證 CN，預設為 `atak-client`。

腳本依序：

1. 檢查工具、`.env` 指定的主機 IP、既有 `runtime/`、Compose 容器與 volume；檢查 ZIP 內容與必要檔案。
2. 將 ZIP 解壓至暫存目錄，確認內容後移入 `vendor/`。不覆寫既有官方套件。
3. 執行 `bootstrap_local.py`，建立 Root／中繼 CA、CRL、TAK／ATAK／Mumble 憑證、密碼、`runtime/tak/` 與初始 DPK。
4. 執行 `provision_mediamtx.py`，建立 MediaMTX 憑證、帳密、觀看與管理設定，再用 `docker compose config --quiet` 檢查 Compose 輸入。
5. 安裝並啟動 mDNS；依 Windows UAC 提示建立 TAK、MediaMTX 與 Mumble 熱點防火牆規則。**Mumble 會開啟可互動的前景視窗，使用期間須保持開啟；按 Ctrl+C 會清除該工作階段規則。**
6. 執行 `docker compose up -d --build`，授予 TAK 管理憑證權限、重啟 TAK 並等待健康檢查，建立 Mumble 的 `Primary`、`Alternate`、`Medical`、`Emergency` 頻道，安裝並啟動兩個 Windows 管理程式。

`-SkipNetworkSetup` 只供熱點名稱解析與防火牆已由其他方式設定時使用；它略過 mDNS 和防火牆變更，但仍要求熱點 IP 已存在。使用此選項後，Android 是否可連線須自行驗證。

## 結果與驗收

成功後，檢查：

```powershell
docker compose ps
.\scripts\Manage-TakControlWorkers.ps1 -Action Status
.\scripts\Test-WindowsMdns.ps1
```

TAK Server、PostgreSQL、Mumble 應為 healthy，MediaMTX 應為 Up；控制台管理程式應顯示回應中。初始 ATAK 登入包位於 `runtime/packages/atak/atak-local-test.dpk`，**含裝置私鑰和匯入密碼**，僅交付指定裝置。`runtime/secrets/`、`runtime/pki/private/` 及整份 `runtime/` 都不得加入 Git。想從 Android 掃 QR 下載時，另啟動 `docker compose --profile sharing up -d share-public`，並依[分享服務說明](../sharing/portal.md)設定暫時防火牆規則。

若中途失敗，先查看錯誤與 `docker compose logs`，保留已產生的 `runtime/` 供檢查。腳本不支援在部分成功的狀態下自動重跑，也不會替使用者清除容器、volume、憑證或防火牆規則。資料庫與憑證恢復見[維運說明](../tak-server/operations.md)；逐步手動建置仍可參考[從零建置](../getting-started.md)。
