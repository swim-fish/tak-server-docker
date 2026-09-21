# 從零開始建置 TAK Server 5.8 Hardened 與 Mumble

## 1. 目標與預設網路

本手冊從官方 `takserver-docker-hardened-5.8-RELEASE-84.zip` 開始，在 Windows Docker Desktop 建立下列本機服務：

| 服務 | ATAK／管理端使用的位址 | 容器內通訊埠 |
| --- | --- | --- |
| TAK CoT TLS | `takbox.local:8089` | `8089/TCP` |
| TAK 管理介面 | `https://takbox.local:8443` | `8443/TCP` |
| Mumble | `takbox.local:64400` | `64738/TCP`、`64738/UDP` |

目前 `compose.yaml` 將主機通訊埠綁定到 `192.168.137.1`，預期 ATAK 裝置位於 `192.168.137.0/24`。若主機介面不同，必須同步修改：

- `compose.yaml` 的 `ports`。
- `scripts/bootstrap_local.py` 的 `--ip` 參數。
- `scripts/Install-TakFirewall.ps1` 與 `scripts/Install-MumbleFirewall.ps1` 的參數。
- Windows mDNS 設定；詳見 [Windows mDNS 設定](../MDNS.md)。

## 2. 前置需求

在 Windows PowerShell 確認下列工具可用：

```powershell
docker version
docker compose version
python --version
openssl version
keytool -help
```

需要的軟體如下：

- Docker Desktop，使用 Linux containers。
- Python 3。
- OpenSSL。
- Java JDK 17 或其他包含 `keytool` 的相容 JDK。
- 官方 `takserver-docker-hardened-5.8-RELEASE-84.zip`。

Docker build 會下載 `eclipse-temurin:17.0.19_10-jdk-ubi10-minimal`、Red Hat UBI 10.2 與套件相依項目，因此第一次建置需要網路連線。若官方套件內的 repository 要求驗證，依套件的 `docker/README_hardened_docker.md` 完成 registry 登入。

## 3. 解壓官方 hardened 套件

先切換到本專案根目錄，再執行：

```powershell
$zip = 'C:\path\to\takserver-docker-hardened-5.8-RELEASE-84.zip'
New-Item -ItemType Directory -Path .\vendor -Force | Out-Null
Expand-Archive -LiteralPath $zip -DestinationPath .\vendor
Test-Path .\vendor\takserver-docker-hardened-5.8-RELEASE-84\tak\CoreConfig.example.xml
Test-Path .\vendor\takserver-docker-hardened-5.8-RELEASE-84\docker\Dockerfile.hardened-takserver
```

兩個 `Test-Path` 都應回傳 `True`。

### 3.1 ZIP 與 `runtime/tak` 的關係

請將 ZIP **完整解壓到 `vendor/`**。不要把 ZIP 內的整個 `tak/` 複製到 `runtime/tak/`。

原因如下：

- `vendor/takserver-docker-hardened-5.8-RELEASE-84/tak/` 是 Docker build context 的一部分，包含 TAK Server WAR、JAR、schema、啟動腳本、資料庫工具及安全性套件。
- `docker/Dockerfile.hardened-takserver` 會把官方 `tak/` 複製到 image 的 `/opt/tak`。
- `runtime/tak/` 只保存這一套部署的設定、keystore、truststore、CRL 與管理憑證，再由 Compose bind mount 覆蓋 `/opt/tak` 的對應位置。
- `scripts/bootstrap_local.py` 只讀取官方 `tak/CoreConfig.example.xml` 當設定範本，其餘 `runtime/tak` 檔案由腳本產生。

因此，官方 ZIP 需要完整保留在 `vendor/`；需要出現在 `runtime/tak/` 的內容如下：

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
| `CoreConfig.xml` | TAK Server 主設定。包含資料庫連線、TLS keystore/truststore、`x509checkRevocation="true"` 與中繼 CA CRL 路徑。 |
| `UserAuthenticationFile.xml` | TAK Server 使用者驗證資料檔。初始內容為空的 `UserAuthenticationFile`。 |
| `takserver.jks` | TAK Server 的 server certificate 與私鑰。 |
| `truststore-root.jks` | TAK TLS 信任庫，包含 Root CA 與中繼 CA。 |
| `fed-truststore.jks` | Federation 信任庫；即使目前未開啟 Federation，仍先產生一致的信任鏈。 |
| `admin.p12` | 管理 API health check 與管理端使用的 client certificate。 |
| `admin.pem` | 管理憑證鏈，供 `UserManager.jar certmod -A` 授予管理權限。 |
| `root-ca.pem`、`intermediate-ca.pem` | TAK Server 信任鏈的公開 CA 憑證。 |
| `root-ca.crl.pem`、`intermediate-ca.crl.pem`、`ca-chain.crl.pem` | 憑證撤銷清單；TAK Server 會啟用 client certificate CRL 檢查。 |

## 4. 產生 PKI、密碼、TAK 設定與 ATAK Data Package

執行：

```powershell
python .\scripts\bootstrap_local.py `
  --host takbox.local `
  --ip 192.168.137.1 `
  --client-name atak-client
```

腳本依照官方 `makeRootCa.sh` 與 `makeCert.sh` 的信任鏈原則，建立：

```text
TAK Local Root CA
└─ TAK Local Issuing CA
   ├─ TAK Server certificate
   ├─ admin client certificate
   ├─ ATAK client certificate
   └─ Mumble server certificate
```

Root CA 只簽發中繼 CA；TAK、ATAK、管理端與 Mumble 各自使用不同葉憑證。TAK 與 Mumble server certificate 的 SAN 同時包含 `DNS:takbox.local` 與 `IP:192.168.137.1`。

本機架構選擇共用 CA 階層來整合 Vx 與 Mumble。ATAK 匯入 Data Package 後，Vx 可以利用套件內的 TAK Root CA 與中繼 CA 驗證 Mumble server certificate；Mumble 不使用 TAK Server 的葉憑證或 private key，而是使用同一個中繼 CA 簽發的獨立葉憑證。

Vx 除了驗證 CA chain，也會比對連線 Address 與 Mumble 憑證 SAN。使用 `takbox.local` 可避免本機 IP 變動時頻繁重簽憑證；Windows mDNS responder 負責讓 Android 在同一網段把這個名稱解析到 Docker host。mDNS 只提供名稱解析，完整設計理由與 Linux／Router 遷移方式請見 [Windows mDNS 設定](../MDNS.md#為什麼這個架構需要-mdns)。

CA 信任、Mumble TLS、SAN 與 mDNS 的完整關係請見 [ATAK Vx 驗證 Mumble Server 憑證流程圖](../MDNS.md#atak-vx-驗證-mumble-server-憑證流程圖)。

腳本也會：

1. 產生 Root CA 與中繼 CA 的 CRL，並在 `CoreConfig.xml` 啟用撤銷檢查。
2. 建立 `runtime/tak` 的 JKS、PKCS#12、PEM 與設定檔。
3. 建立 Mumble TLS full chain 與加密私鑰。
4. 產生所有本機密碼檔，包括 Mumble 一般 server password 與 SuperUser password。
5. 產生 `runtime/packages/atak-local-test.dpk` 及其 SHA-256 檔案。
6. 使用 OpenSSL 與 `keytool` 驗證憑證鏈、CRL、SAN、keystore 及 PKCS#12。

已有部署時，腳本會拒絕覆寫。只有確定要輪替所有 CA、憑證、密碼與 ATAK Data Package 時才使用 `--force`：

```powershell
python .\scripts\bootstrap_local.py --host takbox.local --ip 192.168.137.1 --client-name atak-client --force
```

這會使先前匯入 ATAK 的 Data Package 與既有憑證失效，需要重新匯入新套件。

## 5. `runtime` 目錄用途

`runtime/` 是本機部署狀態，已由 `.gitignore` 與 `.dockerignore` 排除。不得把它加入 Git、公開 release 或一般備份附件。

| 路徑 | 用途 | 機密性 |
| --- | --- | --- |
| `runtime/tak/` | bind mount 到 TAK Server 的設定、JKS、管理憑證、CA 與 CRL。 | 高 |
| `runtime/pki/private/` | Root／中繼 CA 私鑰、葉私鑰、CSR、CA database、serial 與簽發設定。 | 最高 |
| `runtime/pki/public/` | CA、TAK、ATAK、Mumble 的公開憑證與 CRL。 | 低，但仍屬部署資料 |
| `runtime/pki/mumble-fullchain.pem` | Mumble server certificate 加中繼 CA；不包含 Root CA。 | 公開憑證鏈 |
| `runtime/pki/mumble-server.key.pem` | Mumble 加密私鑰，由 `leaf_key_password` 解密。 | 最高 |
| `runtime/secrets/` | Docker Compose secrets 與 PKI／資料庫密碼，一個檔案一個值。 | 最高 |
| `runtime/packages/` | ATAK DPK、CA/client PKCS#12 與 checksum。DPK 內含裝置私鑰及匯入密碼。 | 最高 |
| `runtime/mdns/` | Windows mDNS virtual environment、產生的設定與本機 log。 | 本機狀態 |
| `runtime/analysis/` | 本機除錯或逆向檢查產物，不是啟動服務的必要輸入。 | 依內容判定 |

PostgreSQL、TAK logs 與 Mumble database 分別保存在 Docker named volume：`tak-db-data`、`tak-logs`、`mumble-data`，不在 `runtime/` 內。

### 5.1 `runtime/secrets` 檔案

| 檔案 | 用途 |
| --- | --- |
| `db_password` | TAK Server 連線 PostgreSQL 的密碼；值也寫入產生的 `CoreConfig.xml`。 |
| `root_ca_password` | 加密 Root CA 私鑰。 |
| `intermediate_ca_password` | 加密中繼 CA 私鑰。 |
| `leaf_key_password` | 加密 TAK／ATAK／Mumble 葉私鑰；Compose 也把它傳給 Mumble 解密 TLS 私鑰。 |
| `tak_store_password` | TAK JKS、PKCS#12、管理 health check 與 ATAK DPK 憑證匯入密碼。 |
| `mumble_server_password` | Mumble 一般用戶端共用密碼；填入 ATAK Vx 的 **Password** 欄位。 |
| `mumble_superuser_password` | Mumble `SuperUser` 管理密碼；`provision_mumble_channel.py` 用它建立頻道。不要填入 Vx。 |

需要在本機查看 Vx 應輸入的 Mumble 密碼時執行：

```powershell
Get-Content .\runtime\secrets\mumble_server_password
```

此命令會把密碼顯示在目前終端機。不要把輸出貼入文件、issue、聊天、螢幕截圖或 shell transcript。這個密碼和 `mumble_superuser_password`、`tak_store_password`、ATAK client certificate 都不同。

## 6. 建置與啟動容器

先建置兩個官方 hardened image：

```powershell
docker compose build tak-db tak-server
```

Compose 使用下列標籤：

```text
takserver-db-hardened:5.8-release-84
takserver-hardened:5.8-release-84
```

啟動服務：

```powershell
docker compose up -d tak-db tak-server mumble
docker compose ps
```

第一次初始化 PostgreSQL 與 TAK Server 需要較長時間。等待三個服務都通過 health check：

```powershell
docker compose ps --format json
docker compose logs --tail 100 tak-db tak-server mumble
```

日誌若需分享，先移除內部位址、憑證 subject、裝置名稱與其他識別資訊。

## 7. 啟用 TAK 管理憑證

Hardened 啟動腳本會嘗試啟用 `admin.pem`。服務開始後可執行下列命令確認或重新套用：

```powershell
docker compose exec -w /opt/tak tak-server `
  java -jar utils/UserManager.jar certmod -A certs/files/admin.pem
```

管理介面使用 `runtime/tak/certs/admin.p12`，密碼是 `runtime/secrets/tak_store_password`。`admin.p12` 只供管理，不應放入 ATAK 裝置的 Data Package；裝置套件使用獨立的 `clientCert.p12`。

## 8. 建立 Mumble 預設頻道

Vx 需要選取實際存在且名稱非空白的頻道。Mumble ready 後執行：

```powershell
python .\scripts\provision_mumble_channel.py
```

腳本使用 `mumble_superuser_password` 登入，第一次執行會建立：

- `Primary`：P 主要頻道。
- `Alternate`：A 次要頻道。

再次執行是安全的；已存在的頻道會保留。

## 9. Windows 防火牆與 mDNS

以系統管理員身分開啟 PowerShell，執行：

```powershell
.\scripts\Install-TakFirewall.ps1
.\scripts\Install-MumbleFirewall.ps1
.\scripts\Install-WindowsMdns.ps1
.\scripts\Test-WindowsMdns.ps1
```

防火牆只允許 `192.168.137.0/24` 存取 TAK 的 `8089/TCP`、`8443/TCP` 及 Mumble 的 `64400/TCP`、`64400/UDP`。Mumble 的 TCP 用於 TLS 控制連線，UDP 用於低延遲語音。

Android 裝置應能把 `takbox.local` 解析為 `192.168.137.1`。`.local` 僅適合同一個 link；跨 VLAN、VPN 或公開服務請改用一般 DNS。

後續移植到 Linux 時，同一 Layer 2 網段可由 Linux host 使用 Avahi 發布 `takbox.local`。跨 VLAN、VPN 或由 Router 管理的部署應建立一般 DNS 名稱，調整 DHCP／DNS、路由與防火牆規則，並重新簽發含新 DNS SAN 的 TAK 與 Mumble server certificate；不要在一般 DNS 中建立 `.local` zone。

## 10. 匯入 ATAK Data Package

將下列檔案透過受控方式傳到指定 ATAK 裝置，並在 ATAK 內手動匯入：

```text
runtime/packages/atak-local-test.dpk
```

套件包含：

```text
MANIFEST/manifest.xml
cert/caCert.p12
cert/clientCert.p12
config/servers.pref
```

匯入後，ATAK 應使用 `takbox.local:8089:ssl` 與裝置專用 client certificate 連線。若重新執行 bootstrap `--force`，必須重新匯入新的 DPK。

## 11. ATAK Vx 設定 Mumble

先在 Vx 新增 Mumble channel。

![在 Vx 選擇 Mumble channel 類型](images/atak-vx-01-select-mumble.jpg)

輸入：

| 欄位 | 值 |
| --- | --- |
| Address | `takbox.local` |
| Port | `64400` |
| Password | `runtime/secrets/mumble_server_password` 的內容 |

![設定 Mumble server 位址、通訊埠與密碼](images/atak-vx-02-configure-mumble-server.jpg)

選取由 provisioner 建立的 `Primary` 頻道。Channel 不可留空，也不要只使用 Mumble 的 `Root`。

![選取 Primary 頻道](images/atak-vx-03-select-server-channel.jpg)

設定最多 10 個字元的 alias，例如 `P1`。

![設定頻道 alias](images/atak-vx-04-set-channel-alias.jpg)

儲存後，Channel Pool 會顯示 server 與實際 Mumble 頻道。

![已儲存的 Vx Mumble channel](images/atak-vx-05-saved-channel-profile.jpg)

Mumble 使用 TAK 中繼 CA 簽發的獨立 server certificate。Vx 透過 ATAK Data Package 內的 CA chain 驗證它，並確認畫面輸入的 `takbox.local` 符合憑證的 DNS SAN；Mumble 登入本身仍使用 `mumble_server_password`，不會使用 ATAK 的 client certificate。

## 12. 基本驗證

```powershell
docker compose ps
docker compose logs --tail 100 tak-server
docker compose logs --tail 100 mumble
```

檢查重點：

1. `tak-db`、`tak-server`、`mumble` 都是 healthy，沒有 restart loop。
2. ATAK 能連到 `takbox.local:8089:ssl`。
3. Vx 不再出現 certificate import 或 unknown issuer 錯誤。
4. Vx 能使用一般 Mumble server password 登入並加入 `Primary` 或 `Alternate`。
5. 使用第二個用戶端進行 PTT，確認 `64400/UDP` 有語音流量。

更完整的驗收與問題判讀請見 [本機整合驗證計畫](../LOCAL_VALIDATION_PLAN.md)。

## 13. 停止與重新啟動

停止容器但保留資料：

```powershell
docker compose down
```

重新啟動：

```powershell
docker compose up -d
```

不要加上 `--volumes`，除非確定要刪除 PostgreSQL、TAK logs 與 Mumble database。PKI 與 Data Package 在 `runtime/`，即使刪除 named volumes 也不會自動輪替。
