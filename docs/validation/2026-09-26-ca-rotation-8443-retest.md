# 2026-09-26 CA 輪替後的 8443 舊憑證重測

本次在既有 CA 輪替及舊 CA 撤銷完成後，對正在運作的 TAK Server 5.8 Hardened RELEASE-84 執行唯讀的 8443 版本查詢。未更改 CA、CRL、信任憑證鏈資料庫或服務設定，也未重新啟動容器。

## 測試條件

- 時間：2026-09-26 22:36（臺灣時間）。
- 端點：`10.0.20.27:8443`，TLS SNI 與 HTTP Host 均為 `takbox.local`；測試用戶端以本機 Root CA 驗證伺服器憑證。
- 每張憑證各建立一條新的 TLS 連線，查詢 `GET /Marti/api/version`。
- 舊 Alpha 用戶端憑證：序號 `100C`，CN `ca-test-alpha-20260924`，有效期至 2026-10-01 14:30 UTC；送出葉憑證及舊中繼 CA 的完整鏈。私鑰與密碼只從 Git 忽略的本機封存資料讀取，未輸出。
- 對照用現行管理員憑證：序號 `7A992BAC`，有效期至 2028-09-24 09:46:53 UTC。
- 本機 Root CRL 的 `nextUpdate` 為 2026-10-25 12:54:54 UTC，包含舊中繼 CA 序號 `29AB8D5019C04133D511C77DA9E0B721085D6E13`。

## 結果與界線

| 用戶端憑證 | 8443 新連線結果 |
| --- | --- |
| 舊 Alpha `100C` | TLS 回 `certificate_unknown`，未取得 HTTP 回應。 |
| 現行管理員 `7A992BAC` | `HTTP/1.1 200`。 |

因此，**目前 8443 會阻擋這張舊 CA 簽發的 Alpha 憑證，同時接受現行憑證**。舊 Alpha 尚未到期，而且已附完整舊憑證鏈，不能把本次拒絕簡單解釋為憑證到期或忘記附中繼 CA。

上述原始設定下的重測，不能證明拒絕的單一原因是 Root CRL：[輪替當天的前後紀錄](2026-09-25-ca-rotation-cutover.md)顯示，舊 Alpha 在 Root CRL 發布**之前**就已被 8443 回 `certificate_unknown`。此外，[本版 `crlFile` 程式路徑](2026-09-26-tak-crlfile-source-analysis.md)顯示預設 8443 connector 只直接取得全域 CRL 清單第一筆，即現行中繼 CA 的 CRL。以下另以暫時設定建立舊憑證可連線的基線，測試 Root CRL 實際載入 8443 後的效果。

## 同日受控 Root CRL 前後對照

為補足上述因果界線，另以本機測試環境暫時讓預設 8443 connector 的**第一筆**全域 `crlFile` 指向一個合併檔。合併檔依序含現行中繼 CA、前一代中繼 CA、最初中繼 CA 及 Root CA 的四份 CRL；兩階段的設定、前三份 CRL、信任憑證鏈資料庫、用戶端憑證及私鑰均相同，**只替換合併檔中的 Root CRL**。每階段重啟 TAK Server、等待 healthy，然後讓舊 Alpha 與現行管理員各自建立新的 8443 TLS 連線，查詢同一個版本端點。

| 階段 | Root CRL | 舊 Alpha `100C` | 現行管理員 `7A992BAC` |
| --- | --- | --- | --- |
| A | 2026-09-24 的撤銷前版本；無撤銷紀錄，仍在有效期內 | `HTTP/1.1 200` | `HTTP/1.1 200` |
| B | 現行版本；包含舊中繼 CA 序號 `29AB8D5019C04133D511C77DA9E0B721085D6E13` | TLS `certificate_unknown`，未取得 HTTP 回應 | `HTTP/1.1 200` |

測試前以本機備份腳本建立含憑證及密碼的 Git 忽略快照。完成後將 `CoreConfig.xml` 原始位元組寫回、重啟 TAK Server 並刪除暫存合併 CRL。`CoreConfig.xml` 及四份原始 CRL 均與快照 SHA-256 相符；容器回到 healthy 狀態。在**原始設定**下再測，舊 Alpha 仍回 `certificate_unknown`，現行管理員仍取得 HTTP 200。

此對照證明：**當 8443 的預設 connector 實際載入含各代中繼 CA 與 Root CA 的 CRL 合併檔時，Root CRL 中的舊 CA 撤銷紀錄可以使舊 Alpha 從可連線變成遭拒**。它不表示已把合併檔正式部署；目前原始設定仍讓 8443 直接取用全域第一筆現行中繼 CA CRL。現況下舊 Alpha 雖然遭拒，仍不能單憑該結果認定 Root CRL 已在原始 8443 設定中載入。後續若要把跨代 CA 停權列為 8443 的部署保證，須設計可更新的合併 CRL 或等效的多 CRL 設定，並重測新舊憑證及自動更新流程。
