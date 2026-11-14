# 2026-11-14 OpenLDAP 導入第 0 階段：官方 LDAP 套件與 TAK Server

## 結論

1. 官方套件 `takserver-ldap-5.8-RELEASE-92` 建出的容器可以直接搭配 TAK Server `5.8-RELEASE-84`：使用者 DN 為 `uid=<憑證 CN>`、群組為 `groupOfNames`，TAK 從 `memberOf` 取得群組。
2. 收緊 ACL 後，唯讀服務帳號 `cn=takbind` 足以讓 TAK 依憑證 CN 查群組；匿名存取被拒絕。
3. `ldaps://` 加上 `ldapsTruststore="JKS"`、`ldapsTruststoreFile`、`ldapsTruststorePass` 可用。套件說啟用 LDAPS 要再重啟一次容器，實測第一次啟動後 `636` 就能連。
4. `updateinterval` 的單位是**秒**。設定指南第 9.7.5 節與套件 README 的 `60000`（毫秒）不正確。
5. 目錄無法連線時，TAK 不會拒絕憑證使用者，而是**退回 `UserAuthenticationFile.xml` 的群組**。原本由 LDAP 分開的使用者，會依檔案內的群組重新分組。
6. 套件的 `slapd` 以 root 執行，預設 ACL 允許匿名讀取整個目錄，密碼政策會讓服務帳號的密碼在 30 天後到期。這三項在正式導入前要處理。

本紀錄包含同一天的兩輪實驗：先用模擬用戶端，再加入 Android 模擬機上的 ATAK。實驗容器、映像、信任憑證庫與測試憑證都已移除或撤銷，`runtime/tak/CoreConfig.xml` 已還原（SHA-256 與修改前相同），`compose.yaml` 沒有變更。

## 測試環境

- Windows 11、Docker Desktop（WSL2），TAK Server `5.8-RELEASE-84`（hardened）。
- LDAP 容器：以官方套件的 `Dockerfile.takserver-ldap` 原樣建置（`debian:bookworm-slim`、OpenLDAP 2.5.13），服務名稱 `p0-ldap`，只接 `tak-backend`，不發布通訊埠。以另一個 Compose override 檔啟動，放在儲存庫之外。
- LDAPS 憑證：實驗用的自簽 CA 與伺服器憑證（SAN 為 `p0-ldap`），CA 匯入一個實驗用 JKS，暫時放在 `runtime/tak/certs/`。
- 測試憑證：以憑證工作佇列的 `batch_issue` 簽發三張一日效期憑證 `p0-alpha`、`p0-bravo`、`p0-nodir`，三者在檔案內都屬於 `p0-file`（IN＋OUT）。
- 模擬用戶端：Python TLS CoT 用戶端，每 2 秒送一筆 SA 事件。實驗當天主機沒有 `.env` 的 `TAK_BIND_IP` 位址，`8089`／`8443` 沒有發布到主機，所以用戶端改在 `tak-edge` 網路內的容器執行，直接連 `tak-server:8089`。
- 群組讀取：在 `tak-server` 容器內以管理員憑證呼叫 `GET /Marti/api/subscriptions/all`，每 3 秒輪詢一次。

本紀錄不含密碼、實際位址或裝置識別資訊。

## 目錄內容與調整

套件 bootstrap 完成後，另外做了三件事：

1. 建立 `cn=takbind,dc=tak,dc=local`（`organizationalRole`＋`simpleSecurityObject`）。
2. 把 ACL 第二條從 `by self read / by ldapadm write / by * read` 改成 `by self read / by ldapadm write / by takbind read / by * none`。
3. 載入測試資料：

| 條目 | 內容 |
| --- | --- |
| `uid=p0-alpha,ou=People` | `inetOrgPerson`＋`takUser`；成員：`tak_ALPHA` |
| `uid=p0-bravo,ou=People` | `inetOrgPerson`＋`takUser`；成員：`tak_BRAVO`、`tak_CP_READ` |
| `p0-nodir` | 不在目錄內 |

| 檢查 | 結果 |
| --- | --- |
| 調整前匿名查詢 base DN | 讀得到 4 筆條目 |
| 調整後匿名查詢 | `No such object (32)` |
| `takbind` 經 `ldaps://p0-ldap:636`（驗證 CA）讀 `memberOf` | 讀得到；讀不到 `userPassword` |
| `slapd` 行程的 UID | 0（root） |
| 預設密碼政策 | `pwdMaxAge` 30 天、`pwdMustChange: TRUE`；`takbind` 條目有 `pwdChangedTime`，會套用到期 |

## TAK Server 設定

```xml
<auth default="ldap" x509groups="true" x509addAnonymous="false" x509checkRevocation="true">
  <File location="UserAuthenticationFile.xml"/>
  <ldap url="ldaps://p0-ldap:636/" style="DS"
        userstring="uid={username},ou=People,dc=tak,dc=local"
        userBaseRDN="ou=People,dc=tak,dc=local" groupBaseRDN="ou=Group,dc=tak,dc=local"
        groupObjectClass="groupOfNames" userObjectClass="inetOrgPerson"
        groupprefix="cn=tak_" groupNameExtractorRegex="cn=(.*?)(?:,|$)"
        updateinterval="60"
        ldapsTruststore="JKS" ldapsTruststoreFile="/opt/tak/certs/files/<truststore>.jks"
        ldapsTruststorePass="<store-password>"
        serviceAccountDN="cn=takbind,dc=tak,dc=local" serviceAccountCredential="<bind-password>"/>
</auth>
```

以 `docker compose restart tak-server` 套用，約 70 秒後回到 healthy。

## 結果

### 群組分配

| 憑證 CN | TAK 分配的群組 | 判定 |
| --- | --- | --- |
| `p0-alpha` | `tak_ALPHA` IN＋OUT | 通過 |
| `p0-bravo` | `tak_BRAVO` IN＋OUT、`tak_CP` OUT | 通過；`_READ` 後綴轉成只讀 |
| `p0-nodir` | `p0-file` IN＋OUT | 通過；不在目錄內時使用檔案群組 |

`p0-alpha` 與 `p0-bravo` 沒有共同群組時，彼此收不到對方的事件。

### `updateinterval` 的單位

連線期間在目錄內增減 `p0-alpha` 的群組成員，記錄既有連線的群組何時改變：

| `updateinterval` | 各次異動到生效的時間 |
| --- | --- |
| `60` | 35、45、40 秒；模擬機一次 106 秒 |
| `20` | 23、13、9 秒 |

延遲隨設定值縮短，量級是秒而不是毫秒。同一天的模擬機測試（`60`）有一次花了 106 秒，所以生效時間的上限大約是設定值的兩倍。`takserver.war` 內對應的方法名稱是 `setUpdateIntervalSeconds`。若照文件設成 `60000`，既有連線要等約 16.7 小時才更新。

### 目錄斷線與恢復（`updateinterval="60"`）

| 時間點 | 既有連線 `p0-alpha` | 新連線 `p0-bravo` |
| --- | --- | --- |
| 停止 LDAP 容器前 | `tak_ALPHA`、`tak_BRAVO`、`tak_JOINT1` | — |
| 停止後 15 秒建立新連線 | 仍是 LDAP 群組 | 立刻得到 `p0-file` |
| 停止後約 45 秒 | 改成 `p0-file` | `p0-file` |
| 重新啟動 LDAP 容器後約 40 秒 | 回到 LDAP 群組 | — |

斷線期間三個用戶端都在 `p0-file`，彼此看得到對方的事件。連線沒有中斷，也不需要重啟 TAK。

### LDAP 管理介面的 API（唯讀查詢）

| 端點 | 回應 |
| --- | --- |
| `/Marti/api/ldap-user-management/isLdapTakComplient` | `false` |
| `/Marti/api/util/isLdapAdmin` | `false` |
| `/Marti/api/ldap-user-management/isBulkImportEnabled` | `false` |
| `/Marti/api/ldap-user-management/users` | 列出兩位使用者與其群組；`callSign` 為 `null` |
| `/Marti/api/ldap-user-management/groups` | 列出四個群組與成員 |

服務帳號唯讀時，API 可以讀取使用者與群組，但相容性檢查回 `false`。推測原因是檢查包含寫入測試；沒有用可寫入的帳號對照。`callSign` 為 `null` 是因為沒有設定 `callsignAttribute`。

## Android 模擬機上的 ATAK

第二輪用同一套設定重建實驗環境，加入 Android 模擬機（Android 16、ATAK 5.7.0.15 SDK 版）。

- 另簽發三張一日效期憑證：`p0-emu`（模擬機）、`p0-sima`、`p0-simb`（模擬用戶端）。三者在檔案內各自登錄成只有自己的隔離群組 `p0-iso-<名稱>`。
- 目錄內：`p0-emu` 與 `p0-sima` 屬於 `tak_ALPHA`，`p0-simb` 屬於 `tak_BRAVO`。
- 以 `TAK_BIND_IP=127.0.0.1` 重建 `tak-server` 容器，模擬機經主機 loopback 連 `8089`。連線套件由 ATAK Manager 的部署程式碼推送並匯入。

| 步驟 | TAK 分配給模擬機的群組 | 模擬機 Contacts | 模擬用戶端 |
| --- | --- | --- | --- |
| 匯入套件並連線 | `tak_ALPHA` IN＋OUT | 只有 SIM-Alpha | Alpha 收到模擬機，Bravo 沒有 |
| 目錄內把 `p0-emu` 從 `tak_ALPHA` 移到 `tak_BRAVO` | 106 秒後變成 `tak_BRAVO` | 出現 SIM-Bravo；SIM-Alpha 轉為灰色（逾時） | 新連線的 Alpha 收不到模擬機，Bravo 收到 |
| 停止 LDAP 容器 | 10 秒後變成 `p0-iso-emu` | 連線維持；既有聯絡人尚未逾時 | 兩個模擬用戶端約 20–40 秒後各自退到隔離群組 |
| 重新啟動 LDAP 容器 | 8 秒後回到 `tak_BRAVO` | — | 約 20 秒後回到 LDAP 群組 |
| 撤銷三張憑證（TAK 重新啟動） | 沒有訂閱 | ATAK 顯示未連線，反覆重試 | — |

調動過程沒有重發憑證、沒有重啟 TAK，模擬機上也沒有任何操作。同一天以另一組憑證重跑一次：調動 38 秒生效，模擬機的 ATAK 紀錄在整個過程中沒有任何斷線或重連；目錄斷線後 18–62 秒退到隔離群組，恢復後 8–31 秒換回。目錄斷線期間 Contacts 清單沒有立刻變化，因為 ATAK 要等對方的事件逾時才更新；判定以 TAK 的訂閱群組為準。

撤銷後模擬機的 ATAK 記錄 `set connected: false`，訂閱清單沒有 `p0-` 使用者。這補上了第一輪沒有驗證的「撤銷後 `8089` 拒絕連線」。

## 對導入計畫的影響

- 第一階段可以採用官方套件、`takbind` 唯讀帳號與 LDAPS，設定值如上。
- `updateinterval` 設 `60`，不要照文件設 `60000`。目錄異動最慢約 2 分鐘生效。
- 檔案內的群組是目錄斷線時的實際後備。受 LDAP 管理的使用者在檔案內要登錄成只有自己的隔離群組，否則斷線時會依舊的檔案群組混在一起。模擬機測試已確認隔離群組有效。
- `takbind` 要排除在 30 天到期的密碼政策之外，否則一個月後 TAK 會查不到群組並退回檔案群組。
- `slapd` 以 root 執行的問題要在第一階段補上 `-u openldap -g openldap` 並實測。
- 要使用 LDAP 管理介面，服務帳號大概需要寫入權；這留到第二階段。

## 未測試

- 使用者在目錄內、但不在檔案內時，目錄斷線後的群組（依 11-13 的紀錄推測會是 `__ANON__`）。
- 信任憑證庫內沒有正確 CA 時 TAK 的行為。
- 以本專案 PKI 簽發的 LDAP 伺服器憑證；本次用的是實驗用自簽 CA。
- 帳號密碼登入、`8446`、憑證註冊、管理介面的寫入功能、ppolicy 鎖定。
- 實體 Android 裝置。本次有模擬用戶端與 Android 模擬機上的 ATAK。

後續的撤銷時機、隔離群組與無群組憑證測試見[另一份紀錄](2026-11-14-revocation-quarantine-groupless.md)。

依據：[OpenLDAP 導入計畫](../plans/openldap.md)、[OpenLDAP 與 TAK Server 群組管理](../tak-server/openldap-groups.md)。
