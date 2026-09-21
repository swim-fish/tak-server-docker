# TAK Server 與 Mumble 本機整合驗證小計畫

## 1. 驗證目的

本計畫使用 Android 實機手動匯入 ATAK Data Package，驗證下列流程：

1. 以 Docker Compose 啟動本機 TAK Server 5.8 Hardened、PostgreSQL 與 Mumble。
2. ATAK `5.7.0.15` 能匯入符合 Mission Package version 2 規則的連線套件。
3. ATAK 使用套件內的用戶端憑證連上本機 TAK Server。
4. Vx 使用 ATAK 匯入的 TAK CA 信任由同一套 TAK PKI 簽發的 Mumble server certificate。
5. Vx 能登入 Mumble 並加入頻道；有第二個用戶端時，再驗證雙向 PTT 語音。

本輪只驗證 TAK 與 Mumble。mDNS 已作為固定測試名稱的前置條件完成；MediaMTX、`8446`、Certbot、公開 DNS 與 Federation 不納入本輪。

## 2. 固定測試條件

| 項目 | 測試值 |
| --- | --- |
| Android 裝置 | Samsung `<ANDROID_DEVICE_MODEL>`，序號 `<ATAK_DEVICE_ID>` |
| Android | `16`／API `36` |
| ATAK | `5.7.0.15` release |
| TAK Voice | `2.1.0 (20251122) - [5.6.0]` |
| TAK Server | `5.8-RELEASE-84` Hardened |
| Windows／Docker 主機 IP | `192.168.137.1` |
| TAK CoT TLS | `takbox.local:8089:ssl` |
| TAK 管理介面 | `https://takbox.local:8443`，只供管理驗證 |
| Mumble | `takbox.local:64400`，同時發布 TCP 與 UDP；診斷時可使用 `192.168.137.1` |

本輪 TAK 連線固定使用 `takbox.local`。Windows mDNS responder 已啟用，Android 實機可將名稱解析為 `192.168.137.1`；TAK 與 Mumble server certificate 的 SAN 同時包含 `DNS:takbox.local` 與 `IP:192.168.137.1`。

## 3. 憑證配置

本輪採用同一套 TAK PKI：

```text
TAK Root CA
└─ TAK Issuing Intermediate CA
   ├─ TAK Server leaf certificate
   ├─ ATAK device client certificate
   └─ Mumble server leaf certificate
```

必要條件：

- Root CA 只簽發中繼 CA，不直接簽發葉憑證。
- TAK 與 Mumble 使用不同的葉憑證及私鑰。
- Mumble 葉憑證必須具有 `CA:FALSE`、`serverAuth`、`DNS:takbox.local` 及 `IP:192.168.137.1` SAN。
- Mumble `server.crt` 依序包含葉憑證與 TAK 中繼 CA，不附加 Root CA。
- Mumble 容器只掛載 Mumble 葉憑證、完整中繼鏈及 Mumble 私鑰，不掛載任何 CA 私鑰。
- ATAK `caCert.p12` 同時包含 TAK Root CA 與作用中的 TAK 中繼 CA。此結構依 hardened 套件 `makeCert.sh ca` 同時匯入 Root CA 與中繼 CA 的流程建立，可避免 ATAK native Commo 錯誤碼 20。
- ATAK `clientCert.p12` 使用測試裝置專屬的用戶端葉憑證、私鑰及完整憑證鏈，不使用 admin 憑證。
- Mumble 設定 `certrequired=false`。Mumble 登入使用獨立的 server password；ATAK 的 `clientCert.p12` 不作為 Mumble 登入憑證。

### 3.1 信任來源隔離

為了證明 Vx 是經由 ATAK trust manager 信任 Mumble，本輪測試前確認：

- Android 使用者 CA store 沒有安裝 TAK Root CA。
- Mumble 使用 TAK 中繼 CA 簽發的新葉憑證，不使用目前由 `ATAK Local Voice CA` 簽發的測試憑證。
- 不關閉 TLS 驗證，也不接受或固定未受信任的臨時自簽憑證。

## 4. Data Package 內容

預定輸出一個裝置專屬 DPK：

```text
atak-local-test.dpk
├─ MANIFEST/
│  └─ manifest.xml
├─ cert/
│  ├─ caCert.p12
│  └─ clientCert.p12
└─ config/
   └─ servers.pref
```

`manifest.xml` 必須：

- 使用 `MissionPackageManifest version="2"`。
- 包含非空白且固定的 `name` 與唯一 `uid`。
- 列出上述三個封裝內容，不保留未列出的 orphan entry。
- 兩個 PKCS#12 項目使用精確的 `contentType="P12 Certificate"`。
- `servers.pref` 使用精確的 `contentType="ATAK Preferences"`。
- 設定 `onReceiveImport=true`、`onReceiveDelete=false`。

`servers.pref` 的 `cot_streams` 必須：

- `count=1`，索引從 `0` 開始。
- `connectString0=takbox.local:8089:ssl`。
- `enabled0=true`、`useAuth0=false`。
- `caLocation0=cert/caCert.p12`。
- `certificateLocation0=cert/clientCert.p12`。
- 使用實際 PKCS#12 密碼填入 `caPassword0` 與 `clientPassword0`。

DPK 含私密金鑰及密碼，只能透過受控方式交付給指定裝置；測試完成後依測試資料處理規則保存或銷毀。

## 5. 執行階段

### 階段 A：建立與檢查測試材料

1. 從 `takserver-docker-hardened-5.8-RELEASE-84.zip` 準備 TAK Server 與資料庫映像。
2. 建立 Root CA、中繼 CA、TAK server、裝置 client 與 Mumble server 憑證。
3. 使用 `openssl verify` 驗證 TAK 與 Mumble 葉憑證可追溯至 Root CA。
4. 使用 `openssl x509` 檢查 Mumble SAN、EKU、`CA:FALSE`、issuer 及有效期。
5. 使用 `keytool` 或 `openssl pkcs12` 實際開啟兩個 `.p12`，確認密碼及內容正確。
6. 建立 DPK，檢查 ZIP entry、`manifest.xml`、`servers.pref` 及路徑大小寫。
7. 對照 `vendor/takserver-docker-hardened-5.8-RELEASE-84/tak/certs/makeRootCa.sh` 與 `makeCert.sh`，確認 Root CA 建立方式及中繼 CA truststore 同時含 Root／中繼 CA。

通過條件：所有密碼都能開啟對應 PKCS#12；Mumble full chain、DPK 結構及 Manifest 都通過檢查。

### 階段 B：啟動本機服務

只啟動本輪需要的服務：

```powershell
docker compose up -d tak-db tak-server mumble
docker compose ps
```

啟動後檢查：

1. `tak-db` 為 healthy。
2. `tak-server` 為 healthy，且沒有 schema、keystore 或資料庫登入錯誤。
3. Windows 正在 `192.168.137.1` 發布 `8089/TCP`、`8443/TCP`、`64400/TCP` 與 `64400/UDP`。
4. `openssl s_client -connect 192.168.137.1:64400 -showcerts` 顯示 Mumble 葉憑證及 TAK 中繼 CA。
5. Mumble 日誌沒有私鑰、chain、密碼或資料庫初始化錯誤。
6. Windows Private profile 防火牆只允許測試子網路連入上述必要通訊埠。

通過條件：TAK、資料庫及 Mumble 持續運作，沒有 restart loop，兩個 TLS 服務都送出預期的憑證鏈。

### 階段 C：匯入前對照測試

在尚未匯入 DPK、且 Android 使用者 CA store 沒有 TAK Root CA 時，使用 Vx 嘗試連到：

```text
192.168.137.1:64400
```

預期結果是 Mumble TLS 不受信任。記錄操作時間與 Vx 顯示的錯誤文字；這是確認後續成功來源的對照，不修改 TLS 安全設定。

### 階段 D：使用者手動匯入 DPK

此階段由使用者在 ATAK 介面手動操作：

1. 開啟 ATAK 的匯入功能並選取 `atak-local-test.dpk`。
2. 完成匯入，記錄是否出現憑證、PKCS#12 密碼或 preference 錯誤。
3. 確認 ATAK 出現 Local TAK Server 連線。
4. 等候連線狀態完成；若 trust manager 尚未更新，完整關閉並重新啟動 ATAK 一次。
5. 回報匯入完成時間與畫面上的連線狀態，供伺服器日誌與 ADB logcat 對時。

匯入完成前，不以 ADB 自動點擊或替代使用者操作。

### 階段 E：驗證 TAK Server 連線

1. 確認 ATAK 已連到 `takbox.local:8089:ssl`。
2. 確認沒有 unknown CA、bad certificate、PKCS#12 或 client authentication 錯誤。
3. 從 TAK Server 日誌確認裝置用戶端憑證被接受。
4. 驗證裝置 CoT 出現在 TAK Server；若有第二個 TAK 用戶端，再驗證雙向 CoT／聊天。
5. 確認 `clientCert.p12` 沒有被誤用於 Mumble。

通過條件：ATAK 連線保持穩定，TAK Server 接受該裝置的專屬 client certificate。

### 階段 F：驗證 Vx／Mumble

在 Vx 的 Mumble 設定中輸入：

| 欄位 | 值 |
| --- | --- |
| Address | `192.168.137.1` |
| Port | `64400` |
| Password | Mumble ordinary client server password |
| P 主要 Channel | `Primary`，由 `scripts/provision_mumble_channel.py` 預先建立 |
| A 次要 Channel | `Alternate`，由 `scripts/provision_mumble_channel.py` 預先建立 |

接著：

1. 儲存設定並連線。
2. 確認不再出現 import certificate 或 unknown issuer 錯誤。
3. 確認 Mumble 日誌顯示使用者完成 TLS、驗證密碼並加入頻道。
4. 確認 Vx 顯示已連線的 Mumble 頻道。
5. 授予 TAK Voice 麥克風權限。
6. 使用第二台 ATAK 裝置或桌面 Mumble client 加入相同頻道，雙向各執行一次 PTT。
7. 確認 TCP 控制連線與 UDP 語音流量都通過，沒有只依賴 TCP fallback。

通過條件：Vx 在未安裝 Android TAK Root CA 的情況下信任 Mumble、完成登入及加入頻道；有第二個用戶端時可雙向傳送語音。

## 6. 問題判讀順序

| 症狀 | 優先檢查 |
| --- | --- |
| DPK 無法匯入 | ZIP 根目錄、`MANIFEST/manifest.xml`、version、`uid`、content type、entry 路徑 |
| PKCS#12 匯入錯誤 | `caPassword0`／`clientPassword0`、P12 完整性、私鑰與葉憑證是否配對 |
| TAK 連線憑證錯誤 | `connectString0`、TAK server IP SAN、CA chain、裝置 client EKU |
| 匯入後 Vx 仍顯示憑證錯誤 | Mumble 是否換成 TAK CA 簽發的葉憑證、IP SAN、full chain、ATAK trust manager 是否 refresh |
| Vx 顯示密碼錯誤 | 使用 ordinary client server password，不使用 SuperUser 或 PKCS#12 密碼 |
| 已登入但沒有聲音 | 麥克風權限、相同頻道、VS1／VS2 狀態、雙向 UDP、防火牆與 AP isolation |
| 使用 `.local` 時 unknown host | 檢查 Windows mDNS responder、防火牆、裝置 Wi-Fi 子網路與 `takbox.local` 是否解析為 `192.168.137.1` |

## 7. 驗收紀錄

執行時保存下列證據，但不保存明文密碼或私鑰內容：

- `docker compose ps`。
- TAK Server、PostgreSQL 與 Mumble 的相關日誌片段。
- TAK 與 Mumble server certificate 的 subject、issuer、SAN、EKU、serial 及有效期。
- DPK SHA-256、Manifest 驗證結果及套件 entry 清單。
- ATAK DPK 匯入結果與 TAK 連線狀態。
- 匯入前、匯入後的 Vx TLS 結果。
- Mumble 頻道加入結果。
- 雙向 PTT 結果，或明確註記因只有一個用戶端而尚未執行。

## 8. 本輪完成條件

本輪在以下條件全部成立時完成：

- DPK 符合 ATAK 5.7 Mission Package version 2 與 `cot_streams` 匯入規則。
- ATAK 使用 DPK 內的 client certificate 連上 TAK Server 5.8。
- Mumble 使用 TAK 中繼 CA 簽發、包含正確 IP SAN 的獨立 server certificate。
- Vx 透過 ATAK 匯入的 CA 完成 Mumble TLS 驗證。
- Vx 使用 Mumble password 登入並加入頻道。
- 第二個用戶端可用時，完成雙向 PTT；否則將語音驗證列為唯一未完成項目。
