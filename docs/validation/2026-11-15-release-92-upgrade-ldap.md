# 5.8-RELEASE-92 升級與 OpenLDAP 導入

日期：2026-11-15（時間為 UTC+8）。依[升級與 OpenLDAP 導入計畫](../plans/takserver-5.8-release-92-upgrade.md)在本機部署執行。

## 環境

| 項目 | 內容 |
| --- | --- |
| 主機 | Windows 11、Docker Desktop；TAK 的 `8089`、`8443` 只發布在 `127.0.0.1` |
| 升級前 | `takserver-hardened:5.8-release-84`、`takserver-db-hardened:5.8-release-84`，檔案驗證 |
| 升級後 | 兩個映像為 `5.8-release-92`，另加 `takserver-ldap:5.8-release-92` |
| 用戶端 | 模擬 CoT 用戶端（X509，連 `8089`）；Android 模擬機的 ATAK-CIV `5.7.0.15` |
| 測試憑證 | 三張 3 天效期的憑證，測試後已撤銷 |

## 結果摘要

| 項目 | 結果 |
| --- | --- |
| 升級到 RELEASE-92 | 通過。版本 API 回 `5.8-RELEASE-92-HEAD`，重建容器到 healthy 約 2 分鐘 |
| 資料庫 | 見下方限制：這次是在全新的資料庫上啟動，沒有驗證到既有資料的升級 |
| 升級後的檔案模式 | 通過。兩個不同群組的用戶端拿到檔案內的群組，互相收不到位置 |
| LDAP 服務 | 通過。`slapd` 以 `openldap` 執行，憑證唯讀掛載，服務帳號經 LDAPS 可讀，匿名讀取被拒 |
| 本專案 CA 簽發的 LDAPS 憑證 | 通過。TAK 以既有的 `truststore-root.jks` 驗證（先前只測過實驗用 CA） |
| 切換到 LDAP 群組 | 通過。群組名稱變成 `tak_<檔案群組>`，分流正確 |
| 模擬機 ATAK | 通過。連線、同群組可見、不同群組不可見 |
| 目錄內調動群組 | 通過。兩次異動分別在 4 秒內與約 55 秒生效，連線沒有重建 |
| 回復到檔案模式再啟用 | 通過。`disable` 後拿到檔案群組，`enable` 後回到目錄群組 |

## 升級

1. 備份：`pg_dump -Fc`（4.9 MB，66 個資料表）與三個設定檔，放在 `runtime/backups/upgrade-5.8-r92-<時間>/`。
2. 解壓新套件到 `vendor/`，三個檔案的版本字串改成 92，建置兩個映像。
3. `docker compose up -d tak-db tak-server`，約 2 分鐘後 healthy。

| 檢查 | 升級前 | 升級後 |
| --- | --- | --- |
| `/Marti/api/version` | `5.8-RELEASE-84-HEAD` | `5.8-RELEASE-92-HEAD` |
| `schema_version` 最大序號 | 101 | 101 |
| `CoreConfig.xml` | — | TAK 重排了格式、更新 `version` 屬性；`<auth>`、`<input>`、`<connector>` 不變 |
| API 與訊息服務的紀錄 | — | 啟動後沒有 error 或 exception |

**限制：**備份完成後、切換之前，Docker 的容器與 `tak-db-data`、`tak-logs` 兩個 volume 被另外清除。RELEASE-92 因此是在空的資料庫上初始化，不是對既有資料執行升級。兩個套件的 migration 內容雜湊相同，推論既有資料不需要轉換，但這一點沒有實測。備份仍保留在 `runtime/backups/`，沒有還原。

## 導入 OpenLDAP

依計畫的順序執行 `manage_tak_ldap.py` 的 `prepare`、`init`、`sync`、`backup`、`enable`。

| 步驟 | 觀察 |
| --- | --- |
| `prepare` | 產生兩個密碼與 env 檔；以中繼 CA 簽發 `CN=tak-ldap` 的憑證，`openssl verify` 通過 |
| 啟動容器 | 第一次啟動就 healthy，`636` 可用，不必再重啟 |
| `init` | 建立 `cn=takbind` 與不到期的政策；ACL 改成匿名不可讀；重複執行不會出錯 |
| `sync` | 99 筆檔案使用者中，憑證仍有效且有群組的 4 位寫入目錄（1 位既有使用者與 3 張測試憑證），共 4 個群組；重複執行結果相同 |
| `enable` | 停止 `tak-server`、備份並改寫 `<auth>`、重新啟動，約 2 分鐘後 healthy |

切換前後，同樣兩個模擬用戶端的群組：

| 模式 | `tk-sim` | `tk-simb` | 互相收到位置 |
| --- | --- | --- | --- |
| 檔案（RELEASE-92） | `tk-alpha` IN＋OUT | `tk-bravo` IN＋OUT | 否 |
| LDAP | `tak_tk-alpha` IN＋OUT | `tak_tk-bravo` IN＋OUT | 否 |

實作時修正的兩個問題：

- 容器內用 `ldaps://localhost:636` 驗證會失敗，因為 libldap 以反查到的容器主機名稱比對憑證。改用服務名稱 `tak-ldap`。
- 以 `ldapmodify` 新增群組時，條目要寫 `changetype: add`。

## Android 模擬機

ATAK-CIV `5.7.0.15`，以 `tk-emu` 的資料包連 `10.0.2.2:8089`。ATAK 的伺服器清單顯示伺服器版本 `5.8.92-RELEASE`。

| 步驟 | 預期 | 觀察 | 結果 |
| --- | --- | --- | --- |
| 匯入資料包並連線 | 連線成功，群組 `tak_tk-alpha` | 資料包放進匯入目錄後自動匯入，約 1.5 分鐘內連上；訂閱 API 顯示 `tak_tk-alpha` IN＋OUT | 通過 |
| 同群組可見 | `tk-sim` 收到模擬機的位置，`tk-simb` 收不到 | `tk-sim` 持續收到；`tk-simb` 沒有收到 | 通過 |
| 目錄內移到 `tak_tk-bravo` | 群組改變，連線不重建，可見性互換 | 4 秒內訂閱 API 顯示 `tak_tk-bravo`；來源通訊埠與訂閱識別碼不變；`tk-simb` 收到、`tk-sim` 收不到 | 通過 |
| 移回 `tak_tk-alpha` | 群組還原 | 約 55 秒後還原，連線沒有重建；`tk-sim` 再次收到 | 通過 |
| 移除連線 | 伺服器端的連線消失 | ATAK 端移除後，伺服器端的連線紀錄多留了約 9 分鐘，直到有資料要送給它才清掉 | 見下方 |

觀察到的其他現象：

- 兩次群組異動的生效時間差很多（4 秒與 55 秒），符合 `updateinterval="60"` 的輪詢週期：異動剛好落在輪詢前或後。
- ATAK 靜止時很少回報位置，約 3 分鐘一次。用戶端連線當下收到的那一筆是伺服器重送的最後位置，仍然依群組過濾。短時間的可見性測試要讓裝置移動，或把觀察時間拉長。
- 移除連線時模擬機的網路剛好重新取得位址，伺服器沒有收到斷線。這和 LDAP 無關，但提醒了訂閱 API 的清單可能包含已經離線的連線。
- ATAK 沒有當機，連線期間沒有 `8089` 的錯誤。

## 回復測試

| 動作 | 結果 |
| --- | --- |
| `manage_tak_ldap.py disable` | `<auth>` 只剩 `x509checkRevocation` 與 `<File>`；重啟後兩個用戶端拿到 `tk-alpha`、`tk-bravo` |
| `manage_tak_ldap.py enable` | `<auth>` 內只有一個 `<ldap>`；重啟後回到 `tak_tk-alpha`、`tak_tk-bravo` |

每次切換約 3 分鐘，其中大部分是 TAK 的啟動時間。

## 測試後的狀態

- TAK Server、資料庫與 LDAP 三個容器都是 RELEASE-92，healthy；TAK 在 LDAP 群組模式。
- 三張測試憑證已撤銷並發布 CRL，目錄內的測試帳號與群組已刪除。目錄內剩 1 位使用者、2 個群組。
- 模擬機上的測試連線與資料包已移除。模擬機的模擬 GPS 位置在測試中被改過，沒有還原。
- `5.8-release-84` 的兩個映像與 `vendor/` 內的舊套件仍保留，供回復使用。

## 沒有驗證的項目

- 既有資料庫的升級（見上方限制）。
- 實體手機，以及 `8443` 上依 LDAP 群組取得任務與檔案。這兩項在 RELEASE-84 上測過，見 [2026-11-14 的紀錄](2026-11-14-quarantine-ldap-devices.md)。
- 目錄斷線時退回檔案群組。RELEASE-84 上測過，這次沒有重測。
- 撤銷、隔離流程在 RELEASE-92 上的行為。
- Linux 主機上 `slapd` 讀取金鑰的權限，以及腳本設定的 `0600` 檔案權限。
- Mumble、MediaMTX 與分享入口這次沒有啟動，不在範圍內。
- 單元測試 113 個中有 1 個失敗（`test_share_portal` 的媒體總覽），升級前就存在，和這次變更無關。
