# 官方套件、runtime 與密碼檔案

依據：[Compose 掛載設定](../../compose.yaml)與[bootstrap 產物](../../scripts/bootstrap_local.py)。建置順序見[從零建置](../getting-started.md)。

## 官方 ZIP 與 runtime/tak

使用[首次建置腳本](../scripts/first-time-setup.md)時，指定官方 ZIP 路徑即可；腳本會驗證後完整解壓到 `vendor/`，再由 bootstrap 產生 `runtime/tak/`。逐步手動建置時，請自行將 ZIP **完整解壓到 `vendor/`**。

各目錄的責任：

- `vendor/takserver-docker-hardened-5.8-RELEASE-84/tak/` 是 Docker build context 的一部分，包含 TAK Server WAR、JAR、schema、啟動腳本、資料庫工具及安全性套件。
- `docker/Dockerfile.hardened-takserver` 會把官方 `tak/` 複製到 image 的 `/opt/tak`。
- `runtime/tak/` 只保存這一套部署的設定、keystore、truststore、CRL 與管理憑證，再由 Compose bind mount 覆蓋 `/opt/tak` 的對應位置。
- `scripts/bootstrap_local.py` 只讀取官方 `tak/CoreConfig.example.xml` 當設定範本，其餘 `runtime/tak` 檔案由腳本產生。

`runtime/tak/` 產物：

```text
runtime/tak/
├─ CoreConfig.xml
├─ UserAuthenticationFile.xml
└─ certs/
   ├─ admin.p12
   ├─ admin.pem
   ├─ ca-chain.crl.pem
   ├─ fed-truststore.jks
   ├─ intermediate-ca.crl.pem
   ├─ intermediate-ca.pem
   ├─ root-ca.crl.pem
   ├─ root-ca.pem
   ├─ takserver.jks
   └─ truststore-root.jks
```

| 檔案 | 用途 |
| --- | --- |
| `CoreConfig.xml` | TAK Server 主設定。包含資料庫連線、TLS keystore/truststore、`x509checkRevocation="true"`，以及 8089 使用的中繼 CA CRL 路徑；8443 connector 目前未設定 `crlFile`。 |
| `UserAuthenticationFile.xml` | TAK Server 使用者驗證資料檔。初始內容為空的 `UserAuthenticationFile`。 |
| `takserver.jks` | TAK Server 的 server certificate 與私鑰。 |
| `truststore-root.jks` | TAK TLS 信任憑證鏈資料庫，包含 Root CA 與中繼 CA。 |
| `fed-truststore.jks` | Federation 信任憑證鏈資料庫；即使目前未開啟 Federation，仍先產生一致的信任鏈。 |
| `admin.p12` | 管理 API health check 與管理端使用的 client certificate。 |
| `admin.pem` | 管理憑證鏈，供 `UserManager.jar certmod -A` 授予管理權限。 |
| `root-ca.pem`、`intermediate-ca.pem` | TAK Server 信任鏈的公開 CA 憑證。 |
| `root-ca.crl.pem`、`intermediate-ca.crl.pem`、`ca-chain.crl.pem` | 憑證撤銷清單；TAK Server 會啟用 client certificate CRL 檢查。 |

## 本機資料目錄

`runtime/` 是本機部署狀態，已由 `.gitignore` 與 `.dockerignore` 排除。不得把它加入 Git、公開 release 或一般備份附件。

| 路徑 | 用途 | 機密性 |
| --- | --- | --- |
| `runtime/tak/` | bind mount 到 TAK Server 的設定、JKS、管理憑證、`UserAuthenticationFile.xml`、CA 與 CRL；新裝置註冊由 Windows 管理程式更新驗證檔並重啟 TAK。 | 高 |
| `runtime/pki/private/` | Root／中繼 CA 私鑰、葉私鑰、CSR、CA database、serial 與簽發設定。 | 最高 |
| `runtime/pki/private/clients/` | 控制台逐筆簽發的裝置私鑰、個別密碼、CSR 與 PKCS#12；每筆使用獨立目錄。 | 最高 |
| `runtime/pki/public/` | CA、TAK、ATAK、Mumble、MediaMTX 的公開憑證與 CRL。 | 低，但仍屬部署資料 |
| `runtime/pki/mumble-fullchain.pem` | Mumble server certificate 加中繼 CA；不包含 Root CA。 | 公開憑證鏈 |
| `runtime/pki/mumble-server.key.pem` | Mumble 加密私鑰，由 `leaf_key_password` 解密。 | 最高 |
| `runtime/pki/mediamtx-fullchain.pem` | MediaMTX 葉憑證加中繼 CA。 | 公開憑證鏈 |
| `runtime/pki/mediamtx-server.key.pem` | MediaMTX 專用未加密私鑰，容器唯讀掛載。 | 最高 |
| `runtime/mediamtx/mediamtx.yml` | 產生的 MediaMTX 設定，含發布／讀取帳密。 | 高 |
| `runtime/icu-qr/.venv/` | 手動產生 ICU QR 時使用的隔離 Python 環境。 | 本機工具 |
| `runtime/secrets/` | Docker Compose secrets 與 PKI／資料庫密碼，一個檔案一個值。 | 最高 |
| `runtime/packages/icu/` | 手動產生的 ICU `initial.prefs`、QR URI 與圖片；設定檔含 MediaMTX 發布密碼。 | 高 |
| `runtime/packages/atak/` | TAK／Vx DPK、ZIP 範本、PKCS#12 與 checksum；TAK 包含裝置私鑰及匯入密碼。 | 依套件內容判定 |
| `runtime/share-inbox/` | 舊測試目錄；分享服務不再讀取，現有檔案不會自動刪除。 | 依檔案內容判定 |
| `runtime/share-control/` | Windows Mumble 管理程式與 Flask 頁面的佇列、心跳、程式紀錄及密碼備份。 | 高 |
| `runtime/tak-cert-control/` | 用戶端憑證控制台的主機佇列、心跳、程式紀錄、簽發紀錄、CA 變更前備份、操作紀錄及撤銷後封存的 DPK。 | 最高 |
| `runtime/mdns/` | Windows mDNS virtual environment、產生的設定與本機 log。 | 本機狀態 |
| `runtime/mumble-admin/` | 註冊清單快照、資料庫備份與操作紀錄；資料庫含驗證資料。 | 最高 |
| `runtime/analysis/` | 本機除錯或逆向檢查產物，不是啟動服務的必要輸入。 | 依內容判定 |

PostgreSQL、TAK logs、Mumble database 與分享資料分別保存在 Docker named volume：`tak-db-data`、`tak-logs`、`mumble-data`、`share-state`、`share-files`，不在 `runtime/` 內。分享快照可能含 ICU 發布密碼或 ATAK 私鑰。

## 密碼檔案

| 檔案 | 用途 |
| --- | --- |
| `db_password` | TAK Server 連線 PostgreSQL 的密碼；值也寫入產生的 `CoreConfig.xml`。 |
| `root_ca_password` | 加密 Root CA 私鑰。 |
| `intermediate_ca_password` | 加密中繼 CA 私鑰。 |
| `leaf_key_password` | 加密 TAK／ATAK／Mumble 葉私鑰；Compose 也把它傳給 Mumble 解密 TLS 私鑰。 |
| `tak_store_password` | TAK JKS、PKCS#12、管理 health check 與 ATAK DPK 憑證匯入密碼。 |
| `mumble_server_password` | Mumble 一般用戶端共用密碼；填入 ATAK Vx 的 **Password** 欄位。 |
| `mumble_superuser_password` | Mumble `SuperUser` 管理密碼；`provision_mumble_channel.py` 用它建立頻道。不要填入 Vx。 |
| `mediamtx_publish_password` | TAK ICU 或其他影像來源的 `atak-publisher` 密碼。 |
| `mediamtx_read_password` | 播放端的 `atak-viewer` 密碼；與發布密碼不同。 |
| `share_admin_password` | 本機 Flask 管理頁的 `admin` 登入密碼；不提供給 Android。 |

需要在本機檢視 Vx 應輸入的 Mumble 密碼時執行：

```powershell
Get-Content .\runtime\secrets\mumble_server_password
```

此命令會把密碼顯示在目前終端機。不要把輸出貼入文件、issue、聊天、螢幕截圖或 shell transcript。這個密碼和 `mumble_superuser_password`、`tak_store_password`、ATAK client certificate 都不同。
