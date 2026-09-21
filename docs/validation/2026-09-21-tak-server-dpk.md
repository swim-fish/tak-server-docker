# TAK Server 5.8 Hardened 與 ATAK Data Package 驗證紀錄

## 範圍

本紀錄涵蓋 2026-09-21 在 Windows 11、Docker Desktop／WSL2 與 Android 實機 `<ATAK_DEVICE_ID>` 完成的項目：

- 由 `takserver-docker-hardened-5.8-RELEASE-84.zip` 建置 TAK Server 與 PostgreSQL hardened image。
- 以 Docker Compose 啟動 TAK Server 5.8 與資料庫。
- 建立 Root CA、中繼簽發 CA、TAK server、admin 與 ATAK 裝置憑證。
- 啟用 TAK TLS CRL，驗證撤銷前後行為。
- 建立及持久化 TAK 憑證使用者與群組。
- 建立 ATAK 5.7 可手動匯入的 Data Package。
- 從 Android 實機驗證 mDNS、`8089/TCP` 與 Mumble `40000/TCP` 可達性。

Mumble 已加入 Compose 並完成伺服器端與實機網路前置驗證；詳見 `docs/validation/2026-09-21-mumble-server.md`。MediaMTX 與公開 `8446` 尚未啟用。

## 服務狀態

| 服務 | Image | 狀態 | 對外連接埠 |
| --- | --- | --- | --- |
| `tak-db` | `takserver-db-hardened:5.8-release-84` | healthy | 無 |
| `tak-server` | `takserver-hardened:5.8-release-84` | healthy | `192.168.137.1:8089/TCP`、`192.168.137.1:8443/TCP` |
| `mumble` | `mumblevoip/mumble-server:v1.5.915-1` | healthy | `192.168.137.1:40000/TCP+UDP` |

資料庫只加入 internal Docker network。Windows 防火牆規則將 `8089` 與 `8443` 限制在本機位址 `192.168.137.1` 與遠端子網路 `192.168.137.0/24`。

`tak-server` 健康檢查使用 `admin.p12` 做 mTLS，使用 Root CA 驗證 server certificate，並要求 `/Marti/api/missions` 回傳 HTTP 200。

`mumble` 健康檢查由容器內連到 `127.0.0.1:64738`，使用 Root CA 驗證 `takbox.local` 的 server certificate 與完整中繼 chain。

## 憑證鏈

```text
TAK Local Root CA
└─ TAK Local Issuing CA
   ├─ takbox.local server certificate
   ├─ admin client certificate
   ├─ <ATAK_DEVICE_ID> client certificate
   └─ Mumble server certificate
```

憑證建立與 truststore 內容必須對照 hardened 套件內的官方腳本：

- `vendor/takserver-docker-hardened-5.8-RELEASE-84/tak/certs/makeRootCa.sh`：建立 Root CA、`truststore-root.jks`／`.p12` 與 Root CA CRL。
- `vendor/takserver-docker-hardened-5.8-RELEASE-84/tak/certs/makeCert.sh`：`ca` 分支會把 Root CA 與新建立的中繼 CA 一併匯入該 CA 的 truststore。
- `vendor/takserver-docker-hardened-5.8-RELEASE-84/tak/certs/revokeCert.sh`：作為撤銷與 CRL 維護流程的參考。

本機實作依此得到下列規則：

- Root CA 私鑰不掛載到常駐 TAK 容器。
- 中繼 CA 為實際葉憑證簽發者。
- TAK server truststore 同時包含 Root CA 與中繼 CA；這與官方建立中繼 CA truststore 時同時匯入兩者的流程一致。
- ATAK 的 `caCert.p12` 同時包含 Root CA 與目前作用中的中繼 CA。這是依 `makeCert.sh ca` 的 truststore 結構修正後的必要配置。
- `clientCert.p12` 包含裝置私鑰及「裝置葉憑證 → 中繼 CA → Root CA」完整鏈。
- TAK server 與 Mumble 使用不同葉憑證及私鑰。
- TAK server certificate SAN 包含 `DNS:takbox.local` 與 `IP:192.168.137.1`。

## CRL 設定與驗證

`CoreConfig.xml` 的 `<security><tls>` 載入由實際葉憑證簽發者發布的 CRL：

```xml
<crl _name="TAK Local Issuing CA"
     crlFile="/opt/tak/certs/files/intermediate-ca.crl.pem"/>
```

另外設定 `<auth x509checkRevocation="true">`，供 TAK 的 Client Certificates 撤銷功能進行即時應用層檢查。

Root CA 與中繼 CA 都會產生 30 天有效的 CRL。TAK listener 只載入中繼 CA CRL，因為 TAK client leaf certificate 由中繼 CA 簽發；Root CA CRL 留作離線 PKI 管理，不載入 listener。若中繼 CA 本身遭撤銷或洩漏，處置方式是移除該中繼 CA 的 truststore 信任、輪替中繼 CA 及重新簽發葉憑證。

實測流程：

1. 由中繼 CA 簽發一次性 `crl-probe` client certificate。
2. 撤銷前，probe 可完成 `8089` 的 TLS 1.3 握手。
3. 以 `scripts/revoke_tak_certificate.py` 撤銷 probe，重新發布 CRL，並重新啟動 TAK Server。
4. OpenSSL 離線驗證回報 `certificate revoked`。
5. TAK Server 對 probe 回傳 TLS alert `certificate revoked`。
6. 正式 `<ATAK_DEVICE_ID>` client certificate 仍可完成 TLS 1.3 握手。
7. `admin.p12` 健康檢查仍取得 HTTP 200。

更新 CRL：

```powershell
python scripts\refresh_tak_crls.py
docker compose restart tak-server
```

撤銷指定的中繼 CA 葉憑證：

```powershell
python scripts\revoke_tak_certificate.py runtime\pki\public\example.crt.pem --reason keyCompromise
docker compose restart tak-server
```

CRL 必須在 `nextUpdate` 前更新。腳本執行時不會輸出 CA 密碼。

## 使用者與群組

`UserAuthenticationFile.xml` 已 bind mount 到 `/opt/tak/UserAuthenticationFile.xml`，因此重新啟動或重建 `tak-server` 容器不會遺失使用者設定。該檔案位於忽略版控的 `runtime/tak/`。

| 使用者 | 驗證方式 | 角色 | 群組 |
| --- | --- | --- | --- |
| `admin` | `admin.pem` fingerprint | `ROLE_ADMIN` | `__ANON__`，且管理員依預設可存取所有群組 |
| `<ATAK_DEVICE_ID>` | 裝置 client certificate fingerprint | `ROLE_ANONYMOUS` | `local-test` 讀寫 |

裝置使用者的 `ROLE_ANONYMOUS` 是 TAK file authenticator 的一般非管理角色；實際 CoT 範圍由 `local-test` 的 in/out group 控制。裝置未取得管理員權限。

查詢狀態：

```powershell
docker compose exec -T tak-server /bin/bash -lc `
  'cd /opt/tak && java -jar utils/UserManager.jar usermod -s admin'

docker compose exec -T tak-server /bin/bash -lc `
  'cd /opt/tak && java -jar utils/UserManager.jar usermod -s <ATAK_DEVICE_ID>'
```

新增一般憑證使用者時，先把公開憑證放入 `runtime/tak/certs/`，再執行：

```powershell
docker compose exec -T tak-server /bin/bash -lc `
  'cd /opt/tak && java -jar utils/UserManager.jar certmod -g local-test certs/files/client.pem'
```

不要對 ATAK 裝置憑證使用 `-A`。`-A` 只用於明確指定的管理員憑證。

## ATAK Data Package

輸出檔案：`runtime/packages/atak-local-test.dpk`

SHA-256：

```text
<LOCAL_DPK_SHA256>
```

封裝內容：

```text
atak-local-test.dpk
├─ MANIFEST/manifest.xml
├─ config/servers.pref
├─ cert/caCert.p12
└─ cert/clientCert.p12
```

已驗證：

- `MissionPackageManifest version="2"`。
- 兩個憑證項目的 `contentType` 為 `P12 Certificate`。
- `servers.pref` 的 `contentType` 為 `ATAK Preferences`。
- `connectString0=takbox.local:8089:ssl`。
- `enabled0=true`、`useAuth0=false`。
- `caLocation0=cert/caCert.p12`。
- `certificateLocation0=cert/clientCert.p12`。
- `caCert.p12` 有兩筆 `trustedCertEntry`：`tak-root` 與 `tak-issuing`。
- `clientCert.p12` 具有 SHA-256 MAC、AES-256-CBC 加密、三張憑證與一個加密 private key bag。

### ATAK 信任錯誤與修正

第一次匯入的 DPK 只有 Root CA。實機 logcat 顯示裝置 client certificate 與 Root CA 均成功載入，但 native Commo 對 `takbox.local:8089` 持續回報：

```text
Server cert verification failed: 20 - check truststore for this connection
```

TAK Server 在 TLS 握手時已送出「server 葉憑證 → 中繼 CA → Root CA」，OpenSSL 驗證亦為 `Verify return code: 0`，因此問題不在伺服器漏送 chain。將作用中的中繼 CA 加入 DPK 的 `caCert.p12` 後，truststore 結構與官方 `makeCert.sh ca` 一致。

修正使用 `scripts/rebuild_atak_data_package.py`，只重建 `caCert.p12`、Manifest 與 DPK；不輪替既有 server、admin 或裝置憑證。新套件在 ATAK 顯示名稱為 `ATAK Local TAK 5.8 v2`，仍使用 `takbox.local:8089:ssl`。

此 DPK 包含裝置私鑰與匯入所需密碼，只能交付給指定測試裝置，不得提交 Git 或透過公開管道分享。

## Android 實機前置驗證

ADB 識別到：

```text
<ATAK_DEVICE_ID>  device  model:<ANDROID_DEVICE_MODEL>
```

實機測試結果：

- `takbox.local` 解析為 `192.168.137.1`。
- ICMP 回應正常。
- `toybox nc -z -w 3 takbox.local 8089` 成功。

## 手動匯入步驟

1. 將 `runtime/packages/atak-local-test.dpk` 以受控方式傳到 `<ATAK_DEVICE_ID>`。
2. 在 ATAK 5.7 使用 Import Manager 手動匯入顯示名稱為 `ATAK Local TAK 5.8 v2` 的 DPK。
3. 確認沒有 PKCS#12、密碼、CA 或 manifest 錯誤。
4. 確認 `Local TAK Server 5.8` 連線顯示已連線。
5. 回報匯入時間與 ATAK 顯示的狀態，以便對照 TAK Server 與 ADB logcat。

修正版亦已透過 USB 複製到實機 `/sdcard/Download/atak-local-test-v2.dpk`，由使用者在 ATAK Import Manager 手動選取。

目前狀態：v2 DPK 已建立並完成離線結構驗證。實機重新匯入後，使用者已確認 ATAK Server 連線成功；原先的 native Commo 錯誤碼 20 已排除。

最終服務重啟後，`tak-server` 的 `8089/TCP` listener、mTLS healthcheck 與先前 Android subscription 紀錄均正常。本次 55 秒即時監看未觀察到新的持續 `8089` session，因此此紀錄只主張 ATAK app 已完成過連線驗證，不把該監看期間描述為持續在線。Vx／Mumble `40000` 則已有重新啟動後的 Android `ESTABLISHED`、`Authenticated` 與 `Primary` 頻道紀錄。

## 已知非阻斷訊息

TAK 5.8 hardened image 目前會輸出上游 Logback／Janino 條件式設定警告。API、messaging、健康檢查、TLS 與資料庫均正常運作，因此本次將其記錄為上游 image 的非阻斷訊息。
