# OpenLDAP 導入計畫

> 狀態：規劃草稿（2026-11-14）；第 0 階段已完成，結果見[驗證紀錄](../validation/2026-11-14-openldap-phase0.md)。現行部署仍使用檔案驗證，`compose.yaml` 沒有 LDAP 服務。2026-11-13 的實驗結果見 [OpenLDAP 與 TAK Server 群組管理](../tak-server/openldap-groups.md)；本計畫說明要選哪一種接法，以及怎麼把 OpenLDAP 正式加進這個專案。

依據：官方套件 `takserver-ldap-5.8-RELEASE-92.zip`、`TAK_Server_Configuration_Guide_5.8.pdf` 第 9.3–9.7、10、12、16–19 節，`Federation_Hub_Configuration_Guide_5.8.pdf` 第 4、5 節，以及套件內的 `CoreConfig.xsd`、`CoreConfig.example.xml` 與 `takserver.war`（5.8-RELEASE-84）。標示「推論」的項目來自程式內的字串或 XSD 預設值，還沒有實測。官方套件的內容見第 3 節。

## 1. TAK Server 使用 LDAP 的四種方式

TAK Server 的 `<ldap>` 只有一個設定區塊，但用在哪條登入路徑由 `<auth>` 與 `<input>` 決定。四種方式可以並存。

| 方式 | 設定重點 | 身分驗證靠什麼 | LDAP 的角色 |
| --- | --- | --- | --- |
| A. 憑證＋LDAP 群組 | `<auth default="ldap" x509groups="true">`，`8089` 維持 `auth="x509"` | 用戶端憑證 | 依憑證 CN 查群組，需要服務帳號 |
| B. 憑證＋驗證訊息 | `<input protocol="tls" auth="ldap">` | 憑證加上 ATAK 送出的帳號密碼 | 驗證密碼並查群組 |
| C. 帳號密碼（OAuth） | 開啟 `8446`，由 TAK 發 JWT | LDAP 帳號密碼 | WebTAK 登入、憑證註冊（enrollment） |
| D. 檔案驗證（現況） | `<File location="UserAuthenticationFile.xml">` | 用戶端憑證 | 不使用 |

5.8 另外提供 **LDAP 管理介面**（Administrative > Manage LDAP Users，指南第 19 節）。它直接在目錄內建立使用者與群組、調整成員、鎖定帳號，並可用 CSV 批次匯入（需設 `bulkImportEnabled="true"`）。它不是第五種登入方式，而是 A、B、C 的管理工具。

### 優缺點

| 方式 | 優點 | 缺點與風險 |
| --- | --- | --- |
| A | 裝置端與 DPK 不必改；調動人員不必重發憑證；已在本專案實測 | CN 必須和目錄帳號一致；移出所有群組會落入 `__ANON__`，不等於停權；`CoreConfig.xml` 內有明文服務帳號密碼 |
| B | 多一道密碼，可在目錄端停用帳號 | 裝置要保存密碼；UDP 等無連線輸入不適用；要另開一個輸入埠並重做 DPK |
| C | 可用帳號密碼完成憑證註冊，不必人工發 DPK；WebTAK 可登入 | 本專案的 bootstrap 會移除 `8446`；要先處理公開憑證與網路入口；密碼政策變成必要 |
| D | 最單純，沒有外部相依 | 群組存在 TAK 的檔案內，人員調動要逐一修改；無法和其他系統共用帳號 |

### OpenLDAP 目錄的兩種配置

| 項目 | 2026-11-13 實驗的做法 | 5.8 預設值與管理介面的假設 |
| --- | --- | --- |
| 使用者 DN | `cn={username},ou=users,...` | 指南範例為 `uid={username},ou=People,...`；官方套件也用 `uid` |
| 群組類別 | `groupOfUniqueNames`／`uniqueMember`（osixia 的 memberOf 只支援這個） | `groupObjectClasses` 預設 `groupOfNames` |
| 群組來源 | 使用者條目的 `memberOf` | 相同；另有 `nestedGroupLookup`、`nestedGroupLookupUsingMemberOf` |
| 服務帳號 | 唯讀（`takread`） | 管理介面要能寫入，唯讀帳號不夠（推論） |
| 帳號鎖定 | 沒有 | 使用 `pwdAccountLockedTime`，官方套件有設定 ppolicy overlay |
| 傳輸 | 內部網路明文 `389` | `ldaps://` 加 `ldapsTruststore`、`ldapsTruststoreFile`、`ldapsTruststorePass` |

`style="DS"` 用於 OpenLDAP，`style="AD"` 用於 Active Directory。AD 以 `sAMAccountName` 比對帳號，並可用 `matchGroupInChain` 查巢狀群組；本專案不規劃 AD。

**文件出入（已實測）：**指南第 9.7.5 節與官方套件的 README 把 `updateinterval` 寫成毫秒（`60000`），實測單位是秒。設 `60` 時異動最慢約 2 分鐘生效。

## 2. 和聯邦（Federation）的關係

- 聯邦不使用 LDAP。指南第 12.1 節說明，各管理網域不必向對方透露內部結構，包含 LDAP／AD 的使用者資訊。兩台伺服器之間以互換的 CA 建立信任，另可選用權杖。
- 聯邦交換的是 **TAK 群組名稱**。Manage Federates 的 Manage Groups 與 Federated Group Mapping 用的就是 LDAP 群組轉出來的名稱，例如 `tak_ALPHA`。改用 LDAP 後群組名稱會帶 `tak_` 前綴，既有的聯邦群組設定要跟著改。
- Federation Hub 也不使用 LDAP。連線以 X.509 驗證，管理者列在 `authorized_users.yml`；管理介面可選用 Keycloak 的 OAuth 登入。若日後要讓 Hub 管理者用目錄帳號登入，路徑是 Keycloak 接 LDAP，而不是 Hub 直接接 LDAP。
- 本專案目前沒有啟用聯邦，也沒有部署 Federation Hub，見 [Federation Hub](../tak-server/federation-hub.md)。

## 3. 官方 LDAP 套件（`takserver-ldap-5.8-RELEASE-92`）

TAK 另外發布一個只有設定腳本的小套件，用來建出 5.8 管理介面所說的「支援的 LDAP 容器」。2026-11-14 已原樣建置並搭配 TAK Server 實測。

| 項目 | 套件的做法 |
| --- | --- |
| 基底 | `debian:bookworm-slim` 加 `slapd`、`slapd-contrib`、`ldap-utils`；建置後移除 apt、dpkg 與 perl |
| 目錄結構 | `ou=People`、`ou=Group`；使用者 `uid=<帳號>`；群組為 `groupOfNames`／`member` |
| Overlay | `memberof`（對象 `groupOfNames`）、`refint`、`ppolicy`、`auditlog` |
| TAK schema | 輔助類別 `takUser`，屬性 `takCallSign`、`takRole`、`takColor`，對應 `callsignAttribute` 等設定 |
| 密碼 | 預設雜湊 `{SHA512}`；政策為至少 12 字元、30 天到期、首次登入必須變更、5 次失敗鎖定 15 分鐘 |
| TLS | 掛載 `root-ca.pem`、`server.crt`、`server.key` 後啟用 `636`；另附自簽 CA 的產生腳本 |
| 範例設定 | `<auth default="ldap">`，`ldap://`、`uid={username},ou=People,...`，服務帳號直接用管理者 `ldapadm` |

這個套件證實了第 1 節標示為推論的三件事：使用者以 `uid` 為 DN、群組用 `groupOfNames`，以及帳號鎖定依賴 ppolicy。

直接照套件預設部署有下列問題，導入時要調整：

| 問題 | 說明 | 本專案的處理 |
| --- | --- | --- |
| 匿名可讀整個目錄 | ACL 第二條是 `by * read`，只有 `userPassword` 受保護 | 改成只允許服務帳號與本人讀取 |
| 服務帳號就是管理者 | 範例把 `ldapadm` 的密碼寫進 `CoreConfig.xml`，該帳號可寫入整個目錄 | 方式 A 另建唯讀的 `takbind`；管理介面需要寫入時再評估 |
| 通訊埠發布到主機 | `docker-compose.yml` 預設把 `389`、`636` 發布到所有介面 | 不發布，只接 `tak-backend` |
| 密碼走環境變數 | `LDAP_ADMIN_PASSWORD` 放在 env 檔，腳本以 `-w` 傳給指令 | env 檔放 `runtime/secrets/`，不進 Git |
| `slapd` 以 root 執行（已確認） | entrypoint 啟動時沒有指定 `-u openldap` | 以 Compose 的 `command` 補上參數，並實測 |
| 密碼政策套用到服務帳號 | 預設政策 30 天到期，`takbind` 也受影響 | 為服務帳號另設不到期的政策 |
| 稽核紀錄不在 volume | `/var/log/ldap/audit` 會隨容器重建消失，也不會輪替 | 另掛 volume，併入備份 |
| 密碼政策偏向帳號密碼登入 | 30 天到期與首次必須變更，對只用憑證的方式 A 沒有作用 | 方式 A 不設使用者密碼；方式 C 再調整政策 |

套件的範例把 `updateinterval` 寫成 `60000`，和指南一致，但實測單位是秒；本專案設 `60`。

## 4. 建議方向

1. **第一階段採方式 A。**它已經實測過，不改裝置端，也不需要 `8446`。保留 `<File>` 當成目錄外憑證的備援。
2. **目錄結構採官方套件的形式：**`ou=People`、`ou=Group`、`groupOfNames`／`member`、使用者 DN 為 `uid=<憑證 CN>`。這樣第二階段可以直接使用 5.8 的 LDAP 管理介面。
3. **映像用官方套件建置，不沿用 `osixia/openldap:1.5.0`，也不自己從頭寫。**套件放在 `vendor/`（不進 Git），做法比照 TAK Server 的映像；上表的調整放在本專案的 Compose 設定與一支初始化腳本。osixia 的 memberOf 只支援 `groupOfUniqueNames`，和上一點衝突。
4. **方式 B 不做。**它要裝置保存密碼，又要多開輸入埠，好處有限。
5. **方式 C 併入 `8446` 的計畫，**等[後續計畫](roadmap.md)的公開入口確定後再做。

## 5. 部署設計

### Compose 服務

```yaml
  tak-ldap:
    image: takserver-ldap:5.8-release-92
    build:
      context: ./vendor/takserver-ldap-5.8-RELEASE-92
      dockerfile: Dockerfile.takserver-ldap
    env_file:
      - ./runtime/secrets/tak-ldap.env
    volumes:
      - tak-ldap-config:/etc/ldap/slapd.d
      - tak-ldap-data:/var/lib/ldap
      - tak-ldap-audit:/var/log/ldap/audit
      - ./runtime/pki/ldap:/etc/ldap/certs:ro
    networks:
      tak-backend:
        ipv4_address: 172.28.0.4
    healthcheck:
      test: ["CMD", "ldapsearch", "-x", "-H", "ldap://localhost", "-b", "", "-s", "base", "(objectclass=*)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    command: ["-u", "openldap", "-g", "openldap"]
    security_opt:
      - no-new-privileges:true
    restart: unless-stopped
```

- 只接 `tak-backend`（`internal: true`），不發布任何通訊埠到主機。管理操作用 `docker exec` 或 TAK 的管理介面。
- `tak-server` 加上 `depends_on: tak-ldap: condition: service_healthy`。
- 新增具名 volume `tak-ldap-config`、`tak-ldap-data`、`tak-ldap-audit`，以及 `runtime/secrets/tak-ldap.env`（`LDAP_BASE_DN`、`LDAP_ADMIN`、`LDAP_ADMIN_PASSWORD`）。
- `command` 讓 `slapd` 以 `openldap` 使用者執行（已實測，bootstrap 與 `636` 都正常）。
- 套件的 entrypoint 會對憑證目錄執行 `chown`；唯讀掛載時這一步會失敗但不中斷。Windows Docker Desktop 上實測 `slapd` 讀得到金鑰；Linux 主機要讓金鑰對容器內的 UID 100 可讀。
- LDAP 設定錯誤（例如信任憑證庫不含正確的 CA）不會讓 TAK 啟動失敗，而是靜默退回檔案群組。啟用後要以訂閱 API 確認群組來自目錄。
- 備份與還原的做法已實測，注意事項見[補測 C2 與批次 D、E](../validation/2026-11-14-openldap-batch-cde.md)。

### 初始化腳本（`scripts/init_tak_ldap.py`）

套件的 bootstrap 完成後執行一次：

- 建立唯讀服務帳號 `cn=takbind`，密碼取自 `runtime/secrets/ldap_bind_password`。
- 把 ACL 第二條改成：本人可讀、`ldapadm` 可寫、`takbind` 可讀、其他人不可讀。
- 為 `takbind` 指定不到期的密碼政策。
- 用 `takbind` 透過 `ldaps://` 查詢確認。實測第一次啟動後 `636` 就可用，不必再重啟。

### TAK Server 設定

```xml
<auth default="ldap" x509groups="true" x509addAnonymous="false" x509checkRevocation="true">
  <File location="UserAuthenticationFile.xml" />
  <ldap url="ldaps://tak-ldap:636/" style="DS"
        userstring="uid={username},ou=People,dc=tak,dc=local"
        userBaseRDN="ou=People,dc=tak,dc=local"
        groupBaseRDN="ou=Group,dc=tak,dc=local"
        groupObjectClass="groupOfNames" userObjectClass="inetOrgPerson"
        groupprefix="cn=tak_" groupNameExtractorRegex="cn=(.*?)(?:,|$)"
        updateinterval="60"
        ldapsTruststore="JKS"
        ldapsTruststoreFile="/opt/tak/certs/files/truststore-root.jks"
        ldapsTruststorePass="<store-password>"
        serviceAccountDN="cn=takbind,dc=tak,dc=local"
        serviceAccountCredential="<bind-password>" />
</auth>
```

- 由 `scripts/bootstrap_local.py` 產生這段設定，並新增開關（例如 `.env` 的 `TAK_AUTH_BACKEND=file|ldap`，預設 `file`）。TAK 啟動時會改寫 `CoreConfig.xml`，修改時要用 XML 解析，不能整行取代。
- `ldaps://` 的伺服器憑證由現有的本機 PKI 簽發，SAN 含 `tak-ldap`，檔名依套件要求為 `root-ca.pem`、`server.crt`、`server.key`。
- 兩個密碼都會以明文留在 `runtime/tak/CoreConfig.xml`。這個檔案不進 Git，但紀錄與終端機輸出不可印出整段 `<ldap>`。

### 對現有工具的影響

| 項目 | 影響 | 處理方式 |
| --- | --- | --- |
| 憑證控制台的群組頁、`squad_groups.py` | 只讀寫檔案內的群組；CN 在目錄內的使用者，修改不會生效 | 第一階段在介面標示「LDAP 模式下群組由目錄管理」；第三階段改接目錄 |
| 簽發憑證流程 | 新憑證的 CN 在目錄內沒有帳號時，會退回檔案群組 | 簽發時同步建立目錄帳號並指派群組 |
| 檔案內的群組 | 目錄斷線時 TAK 退回檔案群組（已實測），使用者會依檔案內容重新分組 | 受 LDAP 管理的使用者，在檔案內登錄成只有自己的隔離群組 |
| 健康檢查 | 管理員憑證 `cn=admin` 查不到目錄帳號仍可使用（已實測） | 不變 |
| 備份 | 多了目錄資料 | 以 `slapcat` 匯出到 `runtime/backups/`，併入既有備份流程 |
| 撤銷 | CRL 流程不變 | LDAP 啟用期間的撤銷要補測 |

## 6. 停權與隔離

2026-11-14 的三份驗證紀錄（[撤銷、隔離與無群組](../validation/2026-11-14-revocation-quarantine-groupless.md)、[補測批次 A、B、C](../validation/2026-11-14-openldap-batch-abc.md)、[補測 C2 與批次 D、E](../validation/2026-11-14-openldap-batch-cde.md)）確認了下列事項，導入時要寫進操作流程：

- **LDAP 不能拒絕憑證連線。**方式 A 的連線由憑證鏈與 CRL 決定；LDAP 只在連線建立後決定群組。已撤銷的憑證在 TAK 重啟前仍會拿到 LDAP 群組。
- **撤銷要等 TAK 重啟才生效。**重啟前，既有連線與新連線都被接受；實測 40 分鐘內 TAK 不會自行重新載入 CRL。TAK 內建的 Client Certificates 撤銷不適用於外部 CA 簽發的憑證。
- **不能立刻重啟時用隔離群組減災。**把使用者移到只有他自己的群組，不需重啟：檔案模式 1 秒內、LDAP 模式 11–67 秒內生效，位置等事件隨即停止。
- **隔離不會停止任務變更通知。**他在隔離前訂閱的任務仍會推送變更通知，要另外刪除他的任務訂閱。檔案模式與 LDAP 模式都已在實體手機上確認。
- **重建輸入埠可以讓 `8089` 不重啟就重新載入 CRL。**經管理 API 刪除再重建 TLS 輸入埠後，已撤銷的憑證無法建立新的串流連線；既有連線不受影響。`8443` 不在此列，仍要等重啟。
- **目錄端鎖定帳號對憑證連線沒有作用。**它只擋得住帳號密碼登入（`8446` 與 `auth="ldap"` 輸入埠）。
- **LDAP 啟用且目錄正常時，隔離一定要改目錄。**只改檔案內的群組沒有作用；檔案內的修改是為了目錄斷線時不退回舊群組。目錄與檔案都改之後，實測目錄斷線期間仍然隔離。

操作順序（逐步說明見[隔離使用者](../tak-server/quarantine.md)）：

1. 檔案內的群組改成隔離群組（管理 API 或憑證控制台）。
2. 目錄內移到隔離群組，例如 `tak_QUAR_<名稱>`，並從其他 `tak_` 群組移除。
3. 以訂閱 API 確認群組已改變。
4. 刪除他在各任務的訂閱（`DELETE /Marti/api/missions/{name}/subscription?uid=<用戶端 UID>`）。
5. 視需要以 `DELETE /Marti/api/subscriptions/delete/{subscriptionUid}` 踢掉他的連線；ATAK 約 15 到 26 秒就自行重連，重連後仍在隔離群組。要讓他連不回來，把這一步移到步驟 7 之後（已實測）。
6. 撤銷憑證並發布 CRL。
7. 不能重啟時，重建 `8089` 的輸入埠（`DELETE /Marti/api/inputs/{name}` 後以原設定 `POST /Marti/api/inputs`），讓新的串流連線被拒絕。TAK 會改寫 `CoreConfig.xml` 內的輸入埠屬性。
8. 可以重啟時重啟 TAK；`8443` 要到這一步才會拒絕該憑證。

設計上的要求：

- 每位受 LDAP 管理的使用者，在檔案內平時就登錄成只有自己的隔離群組。這樣目錄斷線時不會混組，緊急隔離時也只需要改目錄。實測可行：斷線後 56 秒內各自退到自己的群組，恢復後 49 秒內回到目錄群組。代價是斷線期間整隊互相不可見。
- 不要留下「在目錄內、但檔案沒有登錄」的帳號。目錄斷線時，它的既有連線保留原本的 LDAP 群組，新連線卻落入 `__ANON__`。
- 不要用「移除所有群組」當成隔離。無群組的憑證會進入 `__ANON__`，和其他無群組的使用者互相可見（已實測）。
- 控制台要提供「隔離」操作，一次改好目錄與檔案兩邊，並讀回確認。這列入第 3 階段。

## 7. 分階段工作

| 階段 | 內容 | 完成條件 |
| --- | --- | --- |
| 0. 驗證假設（已完成） | 用官方套件建拋棄式容器，確認群組分配、唯讀 `takbind`、LDAPS、`updateinterval` 單位與目錄斷線行為 | [2026-11-14 驗證紀錄](../validation/2026-11-14-openldap-phase0.md) |
| 1. 服務與方式 A | 加入官方套件的 Compose 服務、初始化腳本、secrets、bootstrap 開關、備份與還原步驟 | 訂閱 API 顯示 LDAP 群組；切回 `file` 後行為與現在相同 |
| 2. LDAP 管理介面 | 試用 Manage LDAP Users，確認需要的 ACL、ppolicy 與 `adminGroup` | 能在介面建立使用者、調整群組、鎖定帳號；決定服務帳號要不要寫入權 |
| 3. 控制台整合 | 簽發憑證時同步建立目錄帳號；群組頁改讀目錄；提供一次改好目錄與檔案、並刪除任務訂閱的「隔離」操作 | 控制台顯示的群組與訂閱 API 一致；隔離後讀回為隔離群組 |
| 4. 帳號密碼登入 | 隨 `8446` 計畫評估方式 C 與憑證註冊 | 另立計畫 |

## 8. 尚待確認

各項的測試做法與通過條件見 [OpenLDAP 補測計畫](openldap-test-plan.md)。

- 要不要採用 LDAP 管理介面。已實測它需要可寫入的服務帳號（檢查方式是建立再刪除一筆測試使用者）；可寫入帳號的 ACL 限縮到 `ou=People` 與 `ou=Group` 後是否仍可用，還沒有測。
- 怎麼列出某位使用者訂閱的所有任務，以及任務變更通知帶了哪些內容。隔離流程需要逐一刪除他的任務訂閱。
- `8443` 有沒有不重啟就重新載入 CRL 的方式。`8089` 可以用重建輸入埠解決（已實測）；`8443` 沒有找到。
- `adminGroup` 的成員以帳號密碼登入就是 TAK 管理員。開啟 `8446` 前要決定用不用這個屬性，並調整套件預設的密碼政策（連續 5 次錯誤密碼會鎖定帳號 15 分鐘）。
- 裝置設定檔在 `__ANON__` 與隔離狀態下的範圍。
- 使用者條目在目錄內但沒有任何 `tak_` 群組時會落入 `__ANON__`（已實測）。要不要為這類帳號建立一個沒有其他成員的隔離群組，需要決定。
- 服務帳號給寫入權會讓 `CoreConfig.xml` 的明文密碼風險變高：實測對整個目錄樹有寫入權的帳號能讀取所有密碼雜湊、修改其他服務帳號與密碼政策。替代做法是管理介面不用、改由控制台以另一個帳號寫入目錄。
