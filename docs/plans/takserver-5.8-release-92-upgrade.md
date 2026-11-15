# TAK Server 5.8-RELEASE-92 升級與 OpenLDAP 導入計畫

> 狀態：2026-11-15 已在本機部署執行，結果見[驗證紀錄](../validation/2026-11-15-release-92-upgrade-ldap.md)。本頁保留計畫內容，供其他部署照做。

這次變更分兩段，各自可以單獨回復：

1. TAK Server 與資料庫映像由 `5.8-RELEASE-84` 升到 `5.8-RELEASE-92`。
2. 加入官方 LDAP 套件 `takserver-ldap-5.8-RELEASE-92`，TAK 群組改由目錄決定（[OpenLDAP 導入計畫](openldap.md)的方式 A）。連線仍以用戶端憑證驗證，裝置端與 DPK 不必改。

## 1. 兩個版本的差異

比對兩個官方套件解壓後的內容：

| 項目 | 結果 |
| --- | --- |
| `docker/` 內的 Dockerfile 與說明 | 相同 |
| `CoreConfig.example.xml` | 相同 |
| `SchemaManager.jar` 內的 migration | 112 個 SQL，內容雜湊相同；資料庫 schema 不變 |
| `takserver.war`、`takserver-pm.jar`、`takserver-retention.jar`、`UserManager.jar`、`ignite-extensions-*.jar` | 更新 |
| `certs/makeCert.sh`、`makeRootCa.sh` | 新增 `-legacy` 選項，產生 Android 12 以下可讀的 P12 |

本專案不使用套件的 `makeCert.sh`，憑證由 `scripts/` 內的流程簽發，所以 `-legacy` 沒有影響。升級只換應用程式，不需要改 `CoreConfig.xml`。

## 2. 升級 TAK Server

### 事前

| 步驟 | 做法 |
| --- | --- |
| 記錄基線 | `GET /Marti/api/version`、任務數、`CoreConfig.xml` 與 `UserAuthenticationFile.xml` 的雜湊值 |
| 備份資料庫 | `docker exec tak-local-tak-db-1 pg_dump -U postgres -d cot -Fc`，存到 `runtime/backups/upgrade-5.8-r92-<時間>/` |
| 備份設定 | 同一個目錄內放 `CoreConfig.xml`、`UserAuthenticationFile.xml`、`TAKIgniteConfig.xml` |
| 保留舊版 | `vendor/takserver-docker-hardened-5.8-RELEASE-84/` 與兩個 `5.8-release-84` 映像先不刪 |

### 切換

1. 把 `takserver-docker-hardened-5.8-RELEASE-92.zip` 解壓到 `vendor/`。
2. `compose.yaml`、`scripts/bootstrap_local.py`、`scripts/Initialize-LocalStack.ps1` 的版本字串改成 92。
3. `docker compose build tak-db tak-server`。
4. `docker compose up -d tak-db tak-server`。資料庫容器啟動時由 `docker/db-entrypoint.sh` 執行 `SchemaManager.jar upgrade`。
5. 等 `tak-server` 變成 healthy。

停機時間是重建兩個容器加上 TAK 啟動，本機實測約 2 分鐘。ATAK 會自行重連。

### 驗收

| 項目 | 通過條件 |
| --- | --- |
| 版本 | `/Marti/api/version` 回 `5.8-RELEASE-92-HEAD` |
| 資料庫 | `schema_version` 最大序號不變（101），沒有失敗的 migration |
| 設定 | `CoreConfig.xml` 的 `<auth>`、`<input>`、`<connector>` 與升級前相同（TAK 會重排格式並更新 `version` 屬性） |
| 連線 | 兩個不同群組的憑證連上 `8089`，訂閱 API 顯示檔案內的群組，互相收不到位置 |

### 回復

1. 三個檔案的版本字串改回 84，`docker compose up -d tak-db tak-server`。
2. schema 沒有變，資料庫不必還原。若資料損毀，以 `pg_restore --clean` 載入事前的備份。
3. 放回備份的 `CoreConfig.xml`。

## 3. 導入 OpenLDAP

設計依據與各種接法的比較見 [OpenLDAP 導入計畫](openldap.md)。這一段只列執行步驟，全部由 `scripts/manage_tak_ldap.py` 完成。

### 設計

| 項目 | 做法 |
| --- | --- |
| 服務 | `compose.yaml` 的 `tak-ldap`，屬於 `ldap` profile；沒有啟用 profile 的部署不受影響 |
| 網路 | 只接 `tak-backend`，不發布通訊埠 |
| 執行身分 | `command: ["-u", "openldap", "-g", "openldap"]`，`slapd` 不以 root 執行 |
| 傳輸 | `ldaps://tak-ldap:636/`；伺服器憑證由本專案的中繼 CA 簽發，TAK 用既有的 `truststore-root.jks` 驗證 |
| 服務帳號 | 唯讀的 `cn=takbind`，另設不到期的密碼政策；匿名讀取已關閉 |
| 群組對應 | 檔案內的 `groupList X` 對應 `tak_X`，`groupListIN X` 對應 `tak_X_WRITE`，`groupListOUT X` 對應 `tak_X_READ` |
| 同步範圍 | 只同步 CA 資料庫內仍有效、且檔案內有群組的使用者；沒有群組的（例如 `admin`）留在檔案管理 |
| 備援 | `<File>` 保留。目錄內找不到的 CN、目錄斷線時，都退回檔案內的群組 |

群組名稱會多出 `tak_` 前綴。既有任務、資料包若綁定舊的群組名稱，切換後要重新指定群組；啟用聯邦的部署也要同步修改群組對應。

### 步驟

```powershell
python scripts/manage_tak_ldap.py prepare          # 產生密碼、env 檔與 LDAPS 憑證
docker compose --profile ldap up -d --build tak-ldap
python scripts/manage_tak_ldap.py init             # 唯讀帳號、ACL、政策，並驗證
python scripts/manage_tak_ldap.py sync --dry-run   # 先看會建立哪些群組
python scripts/manage_tak_ldap.py sync
python scripts/manage_tak_ldap.py backup           # slapcat 匯出到 runtime/backups/ldap/
python scripts/manage_tak_ldap.py enable           # 改寫 <auth> 並重啟 tak-server
```

`enable` 會先確認 `tak-ldap` 是 healthy、服務帳號能經 LDAPS 讀取，再停止 `tak-server`、備份並改寫 `CoreConfig.xml`、重新啟動。兩個密碼會以明文寫進 `CoreConfig.xml`，紀錄與終端機輸出不可印出 `<ldap>` 元素。

### 驗收

| 項目 | 通過條件 |
| --- | --- |
| 目錄 | `manage_tak_ldap.py status` 顯示使用者與群組數量，服務帳號可讀、匿名不可讀 |
| 群組來源 | `GET /Marti/api/subscriptions/all` 內，連線的群組名稱帶 `tak_` 前綴 |
| 分流 | 同群組互相可見，不同群組不可見 |
| 異動 | 在目錄內把使用者移到另一個群組，2 分鐘內生效，連線不中斷 |
| Android | 模擬機的 ATAK 以憑證連線，結果與模擬用戶端一致 |

設定錯誤時 TAK 不會啟動失敗，而是靜默退回檔案群組，所以一定要用訂閱 API 確認群組名稱。

### 回復

```powershell
python scripts/manage_tak_ldap.py disable          # <auth> 改回只有 <File>，重啟 tak-server
docker compose --profile ldap stop tak-ldap
```

目錄資料留在具名 volume `tak-ldap-config`、`tak-ldap-data`、`tak-ldap-audit`。確定不再使用時才移除。

## 4. 這次沒有做的事

- 憑證控制台還不會寫入目錄。新簽發的憑證要再執行一次 `sync`，否則它會退回檔案群組。
- 控制台的群組頁仍只改檔案；CN 在目錄內的使用者，修改不會生效。隔離流程見[隔離使用者](../tak-server/quarantine.md)。
- 檔案內的群組沒有改成每人一個的備援群組；目錄斷線時使用者會退回檔案內的舊群組。
- LDAP 管理介面、`8446` 帳號密碼登入與憑證註冊，仍列在 [OpenLDAP 導入計畫](openldap.md)的第 2、4 階段。
- 實體手機這次沒有測；Linux 主機的金鑰權限也沒有測。
