# TAK Server 5.8 Hardened Docker Compose 建置計畫

## 1. 文件目的

本計畫說明如何使用下列官方套件，在 Windows 主機的 Docker Desktop／WSL2 環境建立本機 TAK 服務：

- `takserver-docker-hardened-5.8-RELEASE-84.zip`
- TAK Server 5.8 Hardened
- PostgreSQL 18／PostGIS
- MediaMTX
- ATAK Voice 使用的 Mumble Server

本文件保留整體架構與後續階段規劃。TAK Server、PostgreSQL、mDNS、Windows 防火牆、私有 PKI、CRL、使用者設定與 ATAK Data Package 已完成實作及本機驗證；Mumble 已加入 Compose 並完成伺服器端及實機網路前置驗證。執行證據見 `docs/validation/2026-09-21-tak-server-dpk.md` 與 `docs/validation/2026-09-21-mumble-server.md`。MediaMTX 與公開 `8446` 仍依本計畫後續執行。

## 2. 已確認的輸入與環境

### 2.1 TAK 套件

- 版本：`5.8-RELEASE-84`
- ZIP 完整性：通過 Python `ZipFile.testzip()` 檢查，共 200 個項目。
- TAK Server 核心：Java 17。
- 資料庫：PostgreSQL 18、PostGIS 3.6。
- TAK 容器執行使用者：UID `1001`、主要群組 GID `0`。
- 資料庫容器執行使用者：`postgres`、主要群組 GID `0`。
- TAK 與資料庫映像都內建 `HEALTHCHECK`。

### 2.2 本機工具

- Docker Engine CLI：`29.7.2`
- Docker Compose：`v5.4.0`
- WSL：`2.7.8.0`
- WSL Kernel：`6.18.33.1-1`

目前 Docker CLI 讀取 `<USER_HOME>\.docker\config.json` 時可能顯示 `Access is denied`。正式建置前須先確認檔案權限，避免 registry 登入或建置流程受影響。

## 3. 設計原則

1. 所有運行中的專案檔案與持久化資料放在 WSL 的 Linux 檔案系統，例如 `~/tak-server-docker`，不直接從 `/mnt/c` 或 OneDrive 掛載。
2. 官方 hardened Dockerfile 保留為上游輸入；必要修正以 wrapper、補充 Dockerfile 或受控設定檔實作，方便追蹤差異。
3. PostgreSQL 不發布到 Windows／LAN，只允許 TAK 容器透過私有 Docker 網路連線。
4. 憑證私鑰、資料庫密碼與服務密碼不提交到 Git，也不寫入 Compose 原始碼。
5. CA 私鑰不掛載到日常運行的 TAK 容器。
6. 對外連接埠綁定到指定的 Windows LAN IPv4，不使用未受限制的 `0.0.0.0`。
7. Federation Hub 暫不納入第一階段；單一 TAK Server 不需要 FedHub。
8. TAK hardened 的範圍只涵蓋 TAK 與 TAK 資料庫；MediaMTX、Mumble 另做映像版本固定、權限、憑證及網路限制。

## 4. 目標架構

```text
Windows 11
└─ Docker Desktop／WSL2 Linux containers
   ├─ tak-edge network
   │  ├─ tak-server      8089/TCP、8443/TCP（必要）
   │  ├─ mediamtx        8554/TCP（RTSP 控制與 TCP media）
   │  │                  8000/UDP（RTP）、8001/UDP（RTCP）
   │  └─ mumble          host 40000/TCP、40000/UDP → container 64738
   │
   └─ tak-backend network（internal）
      ├─ tak-server
      └─ tak-db          5432/TCP，只限容器網路
```

### 4.1 資料流

- ATAK／WinTAK 的 CoT、聊天、任務與資料同步連到 TAK Server。
- ATAK 視訊來源與觀看端直接連到 MediaMTX。
- ATAK Voice 的 Mumble channel 直接連到 Mumble Server。
- MediaMTX 與 Mumble 不以 TAK Server 的健康狀態作為啟動條件。
- TAK Server 只有在 PostgreSQL 完成初始化、schema upgrade 且健康檢查成功後才啟動。

## 5. 預定專案結構

```text
tak-server-docker/
├─ PLAN.md
├─ README.md                         # 實作階段新增
├─ compose.yaml                     # 實作階段新增
├─ compose.public.example.yaml      # 未來 8446／ACME／RTSPS 選用層
├─ compose.override.example.yaml    # LAN IP／選用功能範例
├─ .env.example                     # 非敏感參數
├─ .gitignore
├─ config/
│  ├─ tak/
│  │  ├─ CoreConfig.xml.template
│  │  └─ pg_hba.conf
│  ├─ mediamtx/
│  │  └─ mediamtx.yml
│  └─ mumble/
│     └─ mumble-server.ini
├─ docker/
│  ├─ tak-server-wrapper.Dockerfile
│  ├─ tak-db-wrapper.Dockerfile
│  └─ init/
├─ scripts/
│  ├─ Prepare-Upstream.ps1
│  ├─ Install-To-Wsl.ps1
│  ├─ bootstrap.sh
│  ├─ init-certs.sh
│  ├─ backup.sh
│  ├─ restore.sh
│  ├─ stage-public-certs.sh
│  └─ verify.sh
├─ secrets/                         # 忽略內容，只保留說明檔
├─ runtime/                         # 忽略，不提交 Git
└─ vendor/                          # 解壓後官方套件，忽略，不提交 Git
   └─ takserver-docker-hardened-5.8-RELEASE-84/
```

官方約 656 MB 的 ZIP 及解壓內容不提交到專案 Git。`Prepare-Upstream.ps1` 負責驗證指定 ZIP、確認版本為 `5.8-RELEASE-84`，再將它解壓到忽略的 `vendor/`。

## 6. Compose 服務規劃

### 6.1 `cert-init`

用途：只在第一次部署或簽發新憑證時執行。

- 以官方 `docker/Dockerfile.ca` 建置。
- 使用 Compose profile `init`，不隨一般 `docker compose up -d` 啟動。
- 從 `/run/secrets/` 讀取 CA 與憑證密碼，再由 wrapper 匯出給官方腳本。
- 使用固定的伺服器 DNS 名稱或 LAN IP 產生 server certificate SAN。
- TAK 私有憑證鏈強制使用「TAK 私有根 CA → 中繼簽發 CA → TAK server／client 葉憑證」。根 CA 不直接簽發任何 server／client 葉憑證，只負責簽發、輪替或撤銷中繼簽發 CA。
- 中繼簽發 CA 為必要元件。初始 server、admin、client 憑證及後續 enrollment 憑證都由中繼簽發 CA 簽發；未啟用線上 enrollment 時，中繼 CA 私鑰離線保存，只在受控簽發作業掛載。
- 官方腳本預設 server common name 為 `takserver`；實作時不可直接沿用，除非所有 ATAK 裝置都能以 `takserver` 解析該主機。
- 官方入口程式最後會 `sleep infinity`；wrapper 必須讓成功產生憑證後以狀態碼 `0` 結束，Compose 才能判定初始化完成。

### 6.2 `cert-stage`

用途：把 CA 產出的檔案分成「離線 CA 資料」與「TAK 運行所需資料」。

- 根 CA 私鑰與根憑證存到 `ca-private` volume 或受保護的離線 WSL 目錄；中繼簽發 CA 私鑰另存 `tak-signing-ca`，不混用儲存位置。
- 以明確 allowlist 複製下列運行檔案到 `tak-certs` volume：
  - `takserver.jks`
  - `truststore-root.jks`
  - `fed-truststore.jks`
  - `admin.pem`
  - `admin.p12`
  - `config-takserver.cfg`
  - 中繼簽發 CA 的公開憑證；實際上游檔名確認後加入 allowlist
  - 實際需要發給裝置的 client certificate／connection package
- 驗證 `takserver.jks` 的私鑰項目包含「葉憑證 → 中繼簽發 CA → 根 CA」完整憑證鏈。依官方 `makeCert.sh ca` 流程，TAK Server 的 `truststore-root.jks` 與 ATAK Data Package 的 `caCert.p12` 都同時信任部署允許的 Root CA 與作用中的中繼簽發 CA。
- 將 `intermediate-signing.jks` 或同等中繼簽發金鑰存入獨立的 `tak-signing-ca` volume，不與 `tak-certs` 或根 CA 私鑰混放。
- 只有啟用 `8446` certificate enrollment 且 `certificateSigning CA="TAKServer"` 時，TAK Server 才能唯讀掛載 `tak-signing-ca`；未啟用線上 enrollment 時，中繼 CA 私鑰不進入任何常駐容器。
- 不把 `ca-do-not-share.key` 或同等根 CA 私鑰掛載到 TAK Server。
- `cert-stage` 成功後結束，不作為常駐服務。

### 6.3 `tak-config-init`

用途：從 template 與 Compose secrets 建立 TAK 運行設定。

- 第一次執行時建立持久化的 `CoreConfig.xml`。
- 資料庫主機固定使用 Compose service name `tak-db`。
- 資料庫密碼從 secret 讀取並寫入權限受限的持久化設定檔。
- 不把資料庫密碼烘焙進 TAK 或資料庫映像。
- 後續若 Web UI 更新 `CoreConfig.xml`，保留變更，不在每次啟動時覆寫。
- 初始化腳本須具備 idempotent 行為：已有有效設定時只驗證，不重建。

### 6.4 `tak-db`

- 建置來源：官方 `docker/Dockerfile.hardened-takserver-db`，外加最小 wrapper。
- PostgreSQL 資料 volume：`tak-db-data:/var/lib/postgresql/data`。
- 掛載共用的 TAK runtime config，讓官方初始化腳本讀到相同資料庫密碼。
- 掛載收斂後的 `pg_hba.conf`。
- 不設定 `ports:`；只用 `expose: 5432` 表示容器網路用途。
- 只加入 `tak-backend`。
- 保留官方健康檢查，但在實作階段確認其檔案完整性基準不會因合法設定更新而誤報。
- 設定 `restart: unless-stopped`。
- 設定 log rotation，避免 Docker JSON log 無限制增長。

### 6.5 `tak-server`

- 建置來源：官方 `docker/Dockerfile.hardened-takserver`，外加最小 wrapper。
- 同時加入 `tak-backend` 與 `tak-edge`。
- 掛載：
  - `tak-certs`：`/opt/tak/certs/files`
  - `tak-runtime-config`：保存 `CoreConfig.xml`、`UserAuthenticationFile.xml` 等運行設定
  - `tak-logs`：`/opt/tak/logs`
- 不掛載完整 `/opt/tak`，避免 volume 遮蔽新映像中的 WAR、JAR 與升級內容。
- wrapper 在啟動前把持久化設定連結到 `/opt/tak` 的預期位置，然後執行官方入口程式。
- 提供 `ADMIN_CERT_NAME=admin`；以專案的 secret-aware healthcheck wrapper 取代映像內建的 healthcheck 命令。該 wrapper 在每次檢查時直接讀取 `/run/secrets/tak_cert_password`，不把密碼放進 Compose environment。
- `depends_on`：
  - `tak-config-init`: `service_completed_successfully`
  - `tak-db`: `service_healthy`
- 設定明確 Java heap，避免官方 `setenv.sh` 依整個 WSL VM 記憶體估算而超額配置。
- 設定 `stop_grace_period`，讓 Java 與資料庫連線有時間關閉。
- 保留官方健康檢查的 HTTPS API 與檔案完整性檢查邏輯，只替換密碼取得方式；完成實機測試後才調整 interval／start period。

### 6.6 `mediamtx`

- 映像固定到明確版本，驗證後再選擇是否固定 digest。
- 第一階段啟用 RTSP，明確設定 `rtspTransports: [tcp, udp]`，同時保留 TCP 與單播 UDP transport。
- 設定 `rtspAddress: :8554`、`rtpAddress: :8000`、`rtcpAddress: :8001`。發布 `8554/TCP` 作為 RTSP 控制連線及 TCP media transport；發布 `8000/UDP` 作為 RTP，並發布 `8001/UDP` 作為 RTCP。
- RTSP 選用 UDP 時，連線建立與協商仍經由 `8554/TCP`，音訊／視訊封包則使用 `8000/UDP` 與 `8001/UDP`。
- 不啟用 multicast，因此不發布 `8002/UDP` 與 `8003/UDP`。
- `udpMaxPayloadSize` 初始使用 MediaMTX 預設值 `1452`；只有在封包擷取或實測確認 MTU／分片問題後才調整。`udpReadBufferSize` 依實際丟包與主機資源量測後調整。
- Windows Docker Desktop 必須在 Compose 明確發布 UDP 通訊埠，並建立對應的 Windows Private profile 防火牆規則。以另一台 LAN 裝置實測 UDP publish／read；若特定網路路徑阻擋 UDP，客戶端可改用 RTSP over TCP。
- 設定 publish／read 使用者，不開放匿名發布。
- 第一階段的 `rtsp://` 不需要伺服器憑證，但 RTSP 帳密與媒體本身不具 TLS 保護，只適用於受信任 LAN 或 VPN。
- 若未來需要跨不受信任網路，改用 `rtsps://`：設定 `rtspEncryption: optional` 做相容性驗證，確認 ATAK／攝影機／播放器都支援後可改為 `strict`。MediaMTX 此時需要獨立的 PEM 私鑰與完整伺服器憑證鏈，設定 `rtspServerKey`、`rtspServerCert`，並發布 `8322/TCP`；單播 UDP secure transport 另使用 `8004/UDP`（SRTP）與 `8005/UDP`（SRTCP）。
- MediaMTX 不共用 TAK 私有金鑰；若使用公開 DNS 名稱，可使用該 MediaMTX 名稱專屬的 Let’s Encrypt 葉憑證。
- API、metrics、pprof 不發布到 LAN。
- 若未要求錄影，不建立錄影 volume。
- 第二階段視需求加入 WebRTC、HLS、RTSPS 或錄影；新增協定前再開相應連接埠。

### 6.7 `mumble`

- 以現有 `atak-voice` 設計為基礎，使用固定版本 `mumblevoip/mumble-server:v1.5.915-1`，正式定稿時再驗證是否需更新。
- Container 內使用標準 `64738/TCP+UDP`。因 Windows UDP excluded port range 涵蓋 `64738`，主機以 `192.168.137.1:40000/TCP+UDP` 對外映射。
- Mumble 需要 TLS 伺服器憑證；未設定時 Mumble 會自動建立自簽憑證，但正式部署使用明確管理的獨立憑證，避免用戶端首次信任提示、憑證變更警告及容器重建後識別改變。
- 設定 `sslCert`、`sslKey`；只有憑證鏈含中繼 CA 時才以 `sslCA` 提供中繼鏈，或將中繼憑證接在葉憑證之後形成 full chain。根 CA 不放入伺服器送出的 chain。
- 第一階段明確設定 `certrequired=false`，以 Mumble server password 與 channel ACL 管理登入。Vx 仍可能在 TLS handshake 提供它自行產生的 client certificate，但該憑證不作為 TAK 身分或 TAK PKI 用戶端憑證。
- Mumble 協定本身不強制使用 TAK PKI；`Mumble Server Installation Guide 1.0.0` 同時支援 TAK Server 產生的 server certificate 與符合條件的其他受信任憑證。本機整合測試已選定 TAK PKI。
- 由 TAK 中繼簽發 CA 簽發獨立的 Mumble server 葉憑證，讓 Vx 使用匯入 ATAK 的 truststore 驗證 Mumble。Mumble 不共用 TAK Server 葉憑證或私鑰。
- 簽發與 truststore 結構依 hardened 套件 `makeRootCa.sh` 與 `makeCert.sh ca` 流程調整：Root CA 只簽中繼 CA；中繼 CA 簽發 Mumble 葉憑證；ATAK truststore 同時包含 Root CA 與作用中的中繼 CA。
- 將 Mumble PEM full chain／加密 private key 交給 Mumble，並以 `sslPassPhrase` secret 解密。Mumble 不掛載 TAK CA keystore 或任何 CA private key。
- 使用公開 DNS 名稱時，優先使用 Mumble 名稱專屬的 Let’s Encrypt 憑證。此時憑證已由 Let’s Encrypt 中繼 CA 簽發。
- Mumble 常駐容器只唯讀掛載 server 私鑰、葉憑證及必要的公開 chain，不掛載任何 CA 私鑰。
- client password 與 SuperUser password 由 Compose secrets 提供。
- `mumble-data` volume 保存資料庫、channel 與 ACL。
- 以 `scripts/provision_mumble_channel.py` 經由 Mumble 原生 TLS 協定建立持久化子頻道；未指定名稱時建立 `Primary`（P 主要）與 `Alternate`（A 次要）。Vx 2.1.0 不使用根頻道 `Root` 作為語音頻道。
- 關閉 Bonjour、公開 server registration 與 ICE 管理介面，除非後續明確啟用。

### 6.8 `certbot` 與 `public-cert-stage`（未來選用 profile）

- 只在啟用公開 DNS 名稱及 `8446` Quick Connect／username-password／OAuth 時加入，例如 `tak.example.com`。Let’s Encrypt 憑證不簽發內部 `.local` 名稱；規劃以穩定的公開 FQDN 為準。
- 預設採 DNS-01 及 DNS provider API plugin，使用只允許修改 `_acme-challenge` 所需記錄的最小權限 token。這不需要將 `80/TCP` 長期開放到主機。
- 若採 HTTP-01，驗證期間必須讓網際網路以該 FQDN 連入 `80/TCP`；只開放 `8446/TCP` 無法完成 HTTP-01。由獨立 ACME webroot／proxy 回應 challenge，不讓 Certbot 改寫 TAK 設定。
- Certbot 的 ACME 帳號、renewal 設定與已簽發 PEM 存到 `acme-data` volume。Certbot 不掛載 Docker socket。
- `public-cert-stage` 驗證 FQDN、有效期、SAN、私鑰對應及完整 chain 後，將 `cert.pem`、`chain.pem`、`fullchain.pem`、`privkey.pem` 分送至各服務各自的憑證 volume。常駐容器只能唯讀掛載自己的憑證，不得讀取其他服務的私鑰。
- TAK `8446` 依 5.8 指南使用獨立 connector keystore。`public-cert-stage` 先以 `openssl pkcs12` 將 `privkey.pem`、`cert.pem`、`chain.pem` 組成 PKCS#12，再以 `keytool -importkeystore` 產生暫存 JKS，驗證後原子替換 `tak-public-8446.jks`。
- `8446` connector 規劃為 `<connector port="8446" clientAuth="false" _name="cert_https" keystore="JKS" keystoreFile="certs/public/tak-public-8446.jks" keystorePass="..."/>`。此公開憑證只配置在 connector 上，不取代共用 `<tls>` 的 `takserver.jks`。
- 更新成功後，才分別重新載入或重啟使用該憑證的服務。更新失敗時保留上一版可用憑證，並讓續期工作回報失敗。
- 續期由 Windows Task Scheduler 或 WSL 排程定期執行 `certbot renew`、`public-cert-stage`、憑證驗證與服務重載；先用 Let’s Encrypt staging 環境完成演練，避免正式環境 rate limit。

## 7. 網路與連接埠

### 7.1 第一階段發布

| 服務 | 連接埠 | 用途 | 規劃 |
| --- | --- | --- | --- |
| TAK | `8089/TCP` | ATAK／WinTAK TLS CoT | 綁定固定 LAN IP |
| TAK | `8443/TCP` | Admin UI／X.509 WebTAK | 綁定管理來源可達 IP，配合防火牆限制 |
| MediaMTX | `8554/TCP` | RTSP 控制連線及 TCP media transport | 綁定固定 LAN IP |
| MediaMTX | `8000/UDP` | RTSP 單播 UDP 的 RTP media | 綁定固定 LAN IP |
| MediaMTX | `8001/UDP` | RTSP 單播 UDP 的 RTCP control | 綁定固定 LAN IP |
| Mumble | `40000/TCP` | 控制與 TCP fallback；映射至 container `64738/TCP` | 綁定固定 LAN IP |
| Mumble | `40000/UDP` | 即時語音；映射至 container `64738/UDP` | 綁定固定 LAN IP |

### 7.2 預設不發布

| 連接埠 | 原因 |
| --- | --- |
| `5432/TCP` | PostgreSQL 只供 TAK 使用 |
| `8444/TCP` | 未確認需要對外提供此 connector |
| `8446/TCP` | 尚未啟用 username/password／OAuth／Quick Connect 流程 |
| `9000-9001/TCP` | 尚未啟用 federation |
| MediaMTX API／metrics／pprof | 僅供本機維運，第一階段不發布 |
| MediaMTX WebRTC／HLS／SRT／RTMP | 第一階段先完成 RTSP 驗證 |
| MediaMTX `8002-8003/UDP` | 第一階段不啟用 RTSP multicast |
| MediaMTX `8322/TCP`、`8004-8005/UDP` | 未啟用 RTSPS／SRTP／SRTCP；啟用前先驗證 ATAK 與影像來源相容性 |

### 7.3 未來公開 profile

| 連接埠 | 用途 | 前置條件 |
| --- | --- | --- |
| `8446/TCP` | TAK username/password、OAuth、certificate enrollment、Quick Connect | 公開 FQDN、Let’s Encrypt connector keystore、帳號與簽發政策完成 |
| `8089/TCP` | 遠端 ATAK TLS CoT | 只有遠端 ATAK 不走 VPN 時才需從邊界開放；仍使用 TAK 私有 PKI，不使用 Let’s Encrypt connector 憑證 |
| `80/TCP` | Certbot HTTP-01 challenge | 只有選用 HTTP-01 時需要；DNS-01 不需要 |
| `8322/TCP` | MediaMTX RTSPS | 只有確認客戶端支援並啟用 MediaMTX TLS 時發布 |
| `8004-8005/UDP` | MediaMTX SRTP／SRTCP | RTSPS 使用 secure UDP transport 時發布 |

### 7.4 Docker 網路

- `tak-backend` 使用明確 subnet，例如 `172.28.0.0/24`，並設 `internal: true`。
- 部署前檢查 subnet 是否與 WSL、VPN、公司 LAN 或其他 Docker network 衝突。
- `pg_hba.conf` 只允許 localhost 與 `tak-backend` subnet，不保留 ZIP 內的 `0.0.0.0/0 md5`。
- 上游腳本建立的是 MD5 格式的 PostgreSQL 密碼；第一版先維持相容並靠私有網路隔離。改為 SCRAM-SHA-256 需同步修改初始化腳本，列為後續強化項目。

## 8. 憑證與秘密資料

### 8.1 信任域與憑證鏈

| 信任域 | 憑證鏈 | 使用處 | 原則 |
| --- | --- | --- | --- |
| TAK 私有 PKI | TAK 私有根 CA → 必要的中繼簽發 CA → server／client 葉憑證 | `8089`、`8443`、admin／ATAK client certificate、Mumble server certificate、TAK certificate enrollment | 根 CA 不直接簽葉憑證；ATAK truststore 與 TAK `truststore-root.jks` 同時信任核准的 Root CA 與作用中的中繼 CA |
| Mumble local test | TAK 私有根 CA → TAK 中繼簽發 CA → Mumble server 葉憑證 | 只限 LAN／VPN 的第一階段測試 | 使用獨立葉憑證與私鑰；Mumble 只取得葉憑證、private key 與公開中繼 chain |
| 公開 Web PKI | ISRG Root → Let’s Encrypt intermediate → 各公開服務葉憑證 | 未來 `8446`、選用 MediaMTX RTSPS、公開名稱的 Mumble | 各服務使用各自葉憑證與私鑰；完整送出中繼鏈 |

- Let’s Encrypt、DigiCert 或其他公開 CA 不加入 TAK 的共用 `<tls>`、`truststore-root.jks` 或 ATAK truststore。
- `8446` 的公開憑證只負責在尚未安裝 TAK 私有 CA 前驗證 enrollment／Quick Connect 端點。完成 enrollment 後取得的 ATAK client certificate 仍由 TAK 私有 CA 或設定的企業 CA 簽發。
- 不在 TAK、MediaMTX、Mumble 間共用同一把私鑰。每個 DNS 名稱使用獨立葉憑證，可縮小單一金鑰外洩或輪替的影響範圍。
- 本機 Mumble 使用 TAK 整合模式：TAK 中繼 CA 只簽發一張具 `serverAuth` 且 SAN 受限於 Mumble 位址的 server 葉憑證，Mumble 不取得 TAK 中繼 CA 私鑰。
- TAK 中繼簽發 CA 設定 `basicConstraints CA:TRUE`、`pathLen:0` 及 `keyCertSign`／`cRLSign`；server／client 葉憑證一律為 `CA:FALSE`，並依用途限制 EKU。
- 根 CA 有效期最長、中繼 CA 次之、葉憑證最短。中繼 CA 輪替需保留重疊有效期，先部署新 chain 與 trust material，再停止舊中繼 CA 簽發。

### 8.2 憑證名稱

實作前必須確定 ATAK 裝置實際輸入的 server address：

- 若使用固定 LAN IP，server certificate SAN 必須包含該 IP。
- 若使用內部 DNS 名稱，所有裝置必須能解析該名稱，SAN 必須包含該 DNS 名稱。
- LAN IP 改變時，使用 IP SAN 的憑證也必須重新簽發。
- 未來公開服務分別規劃名稱，例如 `tak.example.com`、`media.example.com`、`voice.example.com`；實際名稱確認後才申請憑證及建立 DNS。

### 8.3 各服務是否需要憑證

| 服務 | 是否需要 | 規劃 |
| --- | --- | --- |
| TAK `8089`／`8443` | 必須 | 使用 TAK 私有 PKI；`8443` 預設要求 X.509 client certificate |
| TAK `8446` | 啟用時必須 | 使用獨立公開 CA server certificate，`clientAuth="false"`；client enrollment 由帳密／OAuth 控制 |
| Mumble | 必須 | local test 已使用「TAK Root CA → TAK 中繼 CA → Mumble server 葉憑證」；公開部署可改用 Let’s Encrypt chain |
| MediaMTX RTSP `8554` | 不需要 | 純 RTSP 沒有 TLS；限受信任 LAN／VPN，帳密不視為傳輸加密 |
| MediaMTX RTSPS `8322` | 必須 | 啟用 RTSPS／SRTP／SRTCP 時掛載獨立 PEM 憑證與私鑰 |

### 8.4 ATAK Voice 本機信任流程

實機基準為 Samsung `<ANDROID_DEVICE_MODEL>`、Android 16／API 36、ATAK `5.7.0.15` 與 TAK Voice `2.1.0 (20251122) - [5.6.0]`。2026-09-21 的 ADB 記錄已確認 ATAK 成功載入 `VoiceLifecycle` 與 `VoiceTool`，因此此組版本可進入 Vx 介面。

Vx 2.1.0 APK 的 Mumble server certificate 驗證順序如下：

1. Android 預設 `X509TrustManager`。
2. ATAK Trust Manager。
3. 直接讀取 Android `AndroidCAStore`，逐一嘗試 alias 含 `user` 的使用者 CA。

第三條 fallback 會檢查 server 葉憑證與 chain 尾端憑證的有效期、簽章與 issuer／subject 關係、連線位址對 `CN` 或 SAN 的精確比對，以及 server 葉憑證的 `serverAuth` EKU。它沒有取代完整 PKIX 驗證的所有檢查，因此憑證產生與部署仍以標準完整 chain 為準，不依賴 fallback 的寬鬆處理。

本機測試流程：

1. 以固定 LAN IP 或內部 DNS 名稱建立 Mumble server 葉憑證。Subject 的第一個 RDN 為 `CN=<Mumble host>`，SAN 必須包含 Voice 設定內輸入的相同 IP／DNS，並具 `serverAuth` EKU。
2. 由 TAK 中繼 CA 簽發獨立的 Mumble server 葉憑證；server 葉憑證設為 `CA:FALSE`，並具 `serverAuth` EKU。
3. Mumble 掛載加密的 server private key 與「server 葉憑證 → TAK 中繼 CA」full chain；TLS server 不送出 Root，且任何 CA 私鑰都不進容器。
4. ATAK Data Package 的 `caCert.p12` 同時匯入 TAK Root CA 與作用中的中繼 CA。此配置依 hardened 套件 `makeRootCa.sh` 與 `makeCert.sh ca` 的 truststore 流程建立。
5. 在 Voice 的 Mumble server 設定輸入 `takbox.local` 或 SAN 內的 `192.168.137.1`，通訊埠使用 Windows 對外映射的 `40000`。先以 `openssl s_client` 驗證 server certificate，再以兩台實際 ATAK 裝置測試登入與雙向 PTT。

Vx 的 Mumble client certificate 由外掛自行產生並保存在其內部 PKCS#12，使用 ATAK device UID 作為 `CN`，具 `clientAuth` EKU。它不是 TAK Server 發給裝置的 client certificate，也不需要由 TAK 根 CA 或中繼 CA 簽發。第一階段不以此自簽憑證建立身分授權，Mumble 使用 `certrequired=false`、server password 與 channel ACL。

Mumble 已在 `192.168.137.1:40000` 同時發布 TCP／UDP，實機 TCP 可達。完整 Vx TLS、密碼登入、channel 與雙向 PTT 仍須在重新匯入修正版 DPK 後驗證。正式驗收前由 Android 應用程式權限介面授予 TAK Voice 麥克風權限；`POST_NOTIFICATIONS` 與 `BLUETOOTH_CONNECT` 依通知及藍牙 PTT／耳機需求決定。

### 8.5 Secrets 清單

預計建立下列 secret 檔案，全部加入 `.gitignore`：

- `tak_ca_password`
- `tak_issuing_ca_password`
- `tak_cert_password`
- `tak_db_password`
- `mumble_server_password`
- `mumble_superuser_password`
- `mediamtx_publish_password`
- `mediamtx_read_password`
- `tak_public_keystore_password`
- 選用的 DNS provider API token

Compose secrets 在本機模式下是唯讀檔案掛載，應由 wrapper 從 `/run/secrets/<name>` 讀取。若官方腳本只接受環境變數，wrapper 只在呼叫該腳本的最小範圍內設定變數。

### 8.6 上游預設密碼

ZIP 的憑證腳本預設 `CAPASS=atakatak`。實作時必須用 secret 覆寫，不採用預設值。

## 9. 持久化與備份

### 9.1 預定 volumes

| Volume | 內容 | 備份優先級 |
| --- | --- | --- |
| `tak-db-data` | PostgreSQL 18 資料 | 最高 |
| `ca-private` | TAK 私有根 CA 私鑰與根憑證 | 最高，離線保護；不掛載至 TAK Server |
| `tak-signing-ca` | 必要的中繼簽發 CA keystore 與私鑰 | 最高；預設離線，只有線上 enrollment 時掛載至 TAK Server |
| `tak-certs` | TAK 運行用 keystore、truststore、client packages | 最高 |
| `tak-runtime-config` | CoreConfig、使用者驗證設定 | 最高 |
| `tak-logs` | TAK log | 依留存需求 |
| `mumble-data` | Mumble 使用者、channel、ACL | 高 |
| `acme-data` | Certbot account、renewal 設定與簽發結果 | 高；只在公開 profile 建立 |
| `tak-public-cert` | `8446` connector JKS | 高；只掛載至 TAK Server |
| `mumble-certs` | Mumble PEM 葉憑證、私鑰及中繼鏈 | 高；只掛載至 Mumble |
| `mediamtx-certs` | 選用 RTSPS 的 PEM 葉憑證、私鑰及中繼鏈 | 高；只在啟用 RTSPS 時建立並掛載至 MediaMTX |

### 9.2 備份方式

- PostgreSQL 採邏輯備份與 volume 冷備份兩種路徑。
- 邏輯備份使用 `pg_dump`，不採 README 中誤寫的 `psql --data-only` 指令。
- TAK 根 CA／中繼 CA 與各 runtime certificate 分開備份、分開控管存取權限；所有 CA 私鑰備份都必須加密並完成還原演練。
- ACME 帳號資料、renewal 設定及 DNS provider token 分開保護；DNS token 不放進一般備份。公開憑證可重新簽發，但私鑰與部署狀態仍納入受控備份與還原演練。
- Mumble 在停止服務後備份 volume。
- 所有備份都要做還原演練；只有產生檔案不算驗證成功。

## 10. 已發現的上游問題與處理原則

### 10.1 README 與 Dockerfile 的 registry 敘述不一致

README 表示建置需要 Iron Bank／Repo1 帳號，但這份 ZIP 的 Dockerfile 預設來源為公開 UBI 與 Eclipse Temurin，沒有直接使用 `registry1.dso.mil`。計畫將：

1. 記錄實際解析後的 base image 名稱與 digest。
2. 將「官方 hardened ZIP 建置」與「Iron Bank 發布映像」分開描述。
3. 未取得對應 Iron Bank image 與文件前，不宣稱部署符合 Iron Bank 認證。

### 10.2 憑證健康檢查缺少必要接線

TAK healthcheck 使用 `admin.p12`、`ADMIN_CERT_NAME` 與 `ADMIN_CERT_PASS`，README 只明列複製 `admin.pem`。計畫將 `admin.p12` 納入 `cert-stage` allowlist，並以 Compose 覆寫成 secret-aware healthcheck。原因是 Docker 執行 HEALTHCHECK 時不會取得入口程式在執行期間另外匯出的環境變數。

### 10.3 CA 初始化容器不會自行結束

官方 `generateClusterCertsIfNoneExist.sh` 最後執行 `sleep infinity`。計畫用專案 wrapper 讓初始化成功後結束，以支援 `service_completed_successfully`。

### 10.4 資料庫 README 的升級匯出命令不正確

README 將 `--data-only`、`--column-inserts`、`--disable-triggers` 放在 `psql` 命令；這些是 `pg_dump` 選項。若未來從 PostgreSQL 15 升級，另寫經驗證的 `pg_dump`／restore 流程，不直接複製 README 指令。

### 10.5 `pg_hba.conf` 範圍過大

ZIP 內含 `host all all 0.0.0.0/0 md5`。Compose 版本改為只允許私有 backend subnet，且不發布資料庫連接埠。

### 10.6 資料庫記憶體設定

上游 `postgresql.conf` 設定 `shared_buffers = 2560MB`。WSL／Docker Desktop 的記憶體上限必須容納 PostgreSQL、五個 TAK Java 程序、MediaMTX、Mumble 與 Windows 本身。實作前先完成資源預算，不直接採用過低的 Docker Desktop 預設值。

## 11. 實作階段

### 階段 A：專案骨架與上游準備

- 建立 `.gitignore`、`.env.example`、目錄骨架及說明文件。
- 建立 ZIP 驗證與解壓腳本。
- 建立 `.dockerignore`，排除 ZIP、runtime、backup 與不需要的文件，縮小 build context。
- 確認所有 shell script 為 LF 換行並保留執行權限。

### 階段 B：TAK 憑證與設定初始化

- 實作 `cert-init`、`cert-stage` 與 `tak-config-init`。
- 建立離線根 CA 及必要的中繼簽發 CA；根 CA 只簽發中繼 CA，中繼 CA 簽發所有 TAK server／admin／client 葉憑證。
- 使用選定的 LAN IP／DNS SAN 產生憑證。
- 以 `keytool -list -v`／`openssl` 驗證 TAK server、admin、client 的葉憑證、issuer、SAN、用途、到期日與「葉憑證 → 中繼 CA → 根 CA」完整私有憑證鏈。
- 確認 CA 私鑰未進入 TAK runtime volume。
- 驗證 `admin.p12` 可供內建 healthcheck 使用。

### 階段 C：TAK 與 PostgreSQL Compose

- 建立 hardened TAK、DB wrapper image。
- 限制 `pg_hba.conf`。
- 建立有名稱的 volumes 與 backend network。
- 完成 Compose 啟動順序與 restart policy。
- 驗證移除並重建容器後，資料庫、憑證及設定仍存在。

### 階段 D：MediaMTX 與 Mumble

- 加入 MediaMTX RTSP over TCP、單播 UDP 與帳密。
- 已整合 Mumble 設定、持久化 volume、secrets 與 TAK 中繼 CA 簽發的獨立 server certificate；host `40000/TCP+UDP` 映射至 container `64738`。
- 第一階段 MediaMTX 維持純 RTSP，記錄未加密限制；若要求 RTSPS，另以公開 profile 驗證 `8322/TCP`、`8004-8005/UDP` 與 ATAK 相容性。
- 所有發布連接埠綁定固定 LAN IP。
- 建立 Windows Private profile 的 TCP／UDP 防火牆規則草案；套用前另行檢查。

### 階段 E：驗收與備份

- 執行自動化靜態檢查與實際 ATAK 裝置測試。
- 驗證雙向 CoT、管理 UI、RTSP TCP／UDP publish/read、雙向 Mumble PTT。
- 驗證備份與還原。
- 記錄最終 image ID、base image digest、設定雜湊與開放連接埠。

### 階段 F：公開 `8446` 與 ACME（未來選用）

- 建立公開 FQDN、DNS 與邊界路由；先使用 Let’s Encrypt staging 測試 DNS-01 或 HTTP-01。
- 建立 `certbot`、`public-cert-stage`、`tak-public-8446.jks` 與原子輪替流程。
- 啟用 `8446` connector、File／LDAP authentication 或 OAuth，以及符合需求的 certificate signing policy。
- 只對外開放核准的連接埠。`8446` 只處理 enrollment／username-password／OAuth；若遠端 ATAK 不走 VPN，完成 enrollment 後仍需能到達 `8089/TCP` 才能交換 CoT。
- 驗證自動續期、失敗保留舊憑證、到期告警與服務重載。

## 12. 驗收條件

### 12.1 建置與設定

- `docker compose config --quiet` 成功。
- 所有映像可從乾淨 build cache 建置。
- Compose 設定輸出不含明文 secrets。
- `tak-db` 沒有 host port mapping。
- `docker inspect` 顯示預期的非 root 使用者與 healthcheck。

### 12.2 TAK

- `tak-db` 先變成 healthy，`tak-server` 才啟動。
- TAK 內建 healthcheck 成功。
- ATAK 以 TLS 連到 `8089`，可雙向交換位置與聊天。
- 使用 admin client certificate 登入 `8443`。
- 容器刪除並重建後，資料、設定與憑證仍存在。
- `takserver.jks` 送出的 server chain 可追溯到部署核准的 TAK 私有根 CA，SAN 與實際連線名稱相符；TAK truststore 不含公開 Web CA。
- 所有 TAK server、admin、client 葉憑證都由必要的中繼簽發 CA 簽發，沒有任何葉憑證由根 CA 直接簽發。
- 中繼簽發 CA 具備 `CA:TRUE`、`keyCertSign`／`cRLSign`，葉憑證具備 `CA:FALSE` 與符合用途的 EKU；以根 CA 驗證完整 chain 成功。

#### 未來 `8446` 公開 profile

- 未安裝 TAK 私有 CA 的支援客戶端可透過 `https://<public-fqdn>:8446` 驗證 Let’s Encrypt 完整憑證鏈。
- `8446` 送出的葉憑證 SAN 符合公開 FQDN，connector 使用 `clientAuth="false"`，且該 keystore 未被共用 `<tls>` 或 `8089` 使用。
- 經授權使用者可以完成 certificate enrollment；未授權、錯誤密碼或不符合簽發政策的 CSR 被拒絕。
- Let’s Encrypt staging 與 production 續期演練成功；新 JKS 驗證通過後才取代舊檔，TAK 重啟後仍可完成 enrollment。

### 12.3 MediaMTX

- 未授權使用者不可 publish。
- 經授權來源可分別以 RTSP over TCP 與 RTSP over UDP 發布串流。
- ATAK 或測試播放器可從另一台 LAN 裝置分別以 TCP 與 UDP 讀取串流。
- UDP 測試期間可觀察到 `8000/UDP` 的 RTP 與 `8001/UDP` 的 RTCP 流量，且持續播放時無不可接受的丟包、停格或延遲。
- 阻擋 `8000-8001/UDP` 的負向測試會失敗或切換至明確指定的 TCP transport；恢復防火牆規則後 UDP 可重新連線。
- 不需要的 API 與協定未對 LAN 開放。
- 第一階段確認 `8554` 為純 RTSP，文件與測試不誤認為已有 TLS。若啟用 RTSPS，使用 `openssl s_client` 及實際播放器驗證 `8322` 的 hostname、完整 chain、到期日，以及 TCP／secure UDP media。

### 12.4 Mumble

- ATAK `5.7.0.15` 可載入 TAK Voice `2.1.0` 的 `VoiceLifecycle`，裝置已授予 TAK Voice `RECORD_AUDIO`，啟動後不再出現 microphone foreground service 權限例外。
- 兩台實際 ATAK 裝置可加入同一 channel。
- TCP 連線成功。
- 雙向 UDP PTT 聲音正常。
- 一般使用者密碼與 SuperUser 密碼互不混用。
- Mumble 明確設定 `certrequired=false`；Vx 自行產生的 self-signed client certificate 不被誤認為 TAK PKI 身分憑證。
- 容器重建後 channel 與 ACL 仍存在。
- Mumble 送出設定的葉憑證與中繼 chain，hostname 與 ATAK Voice 使用的位址相符；容器重建不會改成另一張臨時自簽憑證。
- local test 的 Mumble server 葉憑證由 TAK 中繼 CA 簽發，連線位址、CN 與 SAN 相符，TLS server 送出葉憑證與中繼 CA，且不送出 Root。
- Mumble 容器內不存在任何 TAK CA 私鑰。

### 12.5 安全與維運

- CA 私鑰不在 TAK、MediaMTX 或 Mumble 常駐容器內。
- TAK Root CA 私鑰永不進入常駐容器；TAK 中繼簽發 CA 私鑰只有啟用 TAK 線上 enrollment 時才可由 TAK Server 讀取。
- Git working tree 未包含 secrets、client packages、私鑰、資料庫或 log。
- 第一階段 Windows 防火牆只允許指定 LAN subnet；未來公開 profile 使用獨立規則，只開放經核准的 `8446`、選用的 `8089` 與 ACME challenge 通訊埠。
- 備份能在隔離環境成功還原。

## 13. 實作前需由部署情境決定的項目

以下項目不阻擋專案骨架製作，但會影響最終設定：

1. Windows 主機的固定 LAN IPv4 或內部 DNS 名稱。
2. 允許連線的 Wi-Fi／LAN CIDR。
3. 未來 `8446` 使用的公開 FQDN、DNS provider、DNS-01 API 支援、Quick Connect／username-password／OAuth 流程，以及遠端 ATAK 透過 VPN 或公開 `8089` 連線。
4. MediaMTX 的串流來源、codec、是否錄影、來源與觀看端支援的 RTSP transport，以及 ATAK 實際使用的 URL 格式。
5. Mumble 未來是否只限 LAN、是否另設公開 DNS 名稱，以及預計使用者數量。
6. Docker Desktop／WSL 可配置的 CPU、記憶體與磁碟空間。
7. 是否已有既有 TAK 5.7 資料要遷移；本計畫目前按全新 PostgreSQL 18 部署設計。

## 14. 第一版不包含的項目

- Federation Hub 與跨站 federation。
- PostgreSQL 高可用或外部資料庫。
- 公網 NAT、DDNS、公開 CA 或 reverse proxy 的實際部署；本計畫只保留未來公開 profile 的設計與驗收條件。
- Kubernetes／Swarm。
- MediaMTX 錄影、WebRTC、HLS、SRT、RTMP。
- 自動更新映像。
- 宣稱 Iron Bank、DISA STIG、FIPS 或其他合規認證；這些需要獨立證據與驗證。

## 15. 參考依據

- `TAK_Server_Configuration_Guide_5.8.pdf`：Appendix B 的 TAK 私有 PKI、Appendix C 的 certificate enrollment，以及 Quick Connect 對 `8446` 公開憑證的限制。
- `Federation_Hub_Configuration_Guide_5.8.pdf`：keystore、truststore 與跨信任域 CA 管理方式；FedHub 本身仍不納入第一階段。
- `Mumble Server Installation Guide.pdf`（Voice 1.0.0）：支援 TAK Server certificate 與 self-signed certificate，並要求 trusted issuer、符合 Mumble host 的 CN／SAN、SSL server purpose 及有效 issuer chain。
- `User Guide.pdf`（Voice 2.1.0）：ATAK Voice 的 Mumble server／channel 設定與實機操作流程。
- [MediaMTX configuration reference](https://mediamtx.org/docs/references/configuration-file) 與 [RTSP-specific features](https://mediamtx.org/docs/features/rtsp-specific-features)：RTSP／RTSPS、RTP／RTCP、SRTP／SRTCP 與憑證參數。
- [Mumble server configuration](https://www.mumble.info/documentation/administration/config-file/)：`sslCert`、`sslKey`、`sslCA` 及自簽憑證行為。
- [Let’s Encrypt challenge types](https://letsencrypt.org/docs/challenge-types/) 與 [Certbot user guide](https://eff-certbot.readthedocs.io/en/stable/using.html)：HTTP-01、DNS-01 與續期流程。
