# 2026-09-25 中繼 CA 切換實測

本次在本機測試環境切換簽發中繼 CA，保留原 Root CA。A 裝置用於後續 ATAK 與 Vx 實機驗收；Android UI 由使用者操作。本頁只記錄已核對的結果，不將 TLS 握手等同實機登入。

## 切換與回復點

- 切換前以 `scripts/cutover_ca_rotation.py` 預檢候選 CA 指紋、A 裝置 DPK、管理員認證檔與 `CoreConfig.xml` 的 CRL 設定。
- `--apply` 建立含私鑰與密碼的忽略版控快照 `runtime/backups/ca-rotation-20260924T160501Z/`，封存舊中繼 CA 及清冊，再以 `docker compose down`、`up -d --no-build` 切換服務。快照只供本機回復，不得公開。
- 舊中繼 CA SHA-256 ID 為 `1716634DF8C600A2295CF78228152173A72813B93AE91E08D46E65B581E16E64`；新中繼 CA ID 為 `BD337A0FCC2CE7A8A78677B347582CBB46EEB5649D9C757738E91BAAFFD08B01`。
- 切換後 Root CRL 仍有 **0** 筆撤銷紀錄；沒有把隔離階段產生的舊 CA 撤銷 CRL 發布到服務。TAK 的 TLS 設定同時保留新、舊中繼 CRL 參照，以便過渡期測試。此階段不可宣稱舊憑證已停權。

## 伺服器端驗證

| 項目 | 實測結果 |
| --- | --- |
| Compose | `tak-server`、`tak-db`、`mumble`、`share-admin`、`share-public` 為 healthy；MediaMTX 與預覽、觀看容器為 running。 |
| TAK 8089 | 實際 TLS 伺服器憑證簽發者為 `TAK Local Issuing CA 20260924`，使用 Root CA 驗證成功。新 Alpha 憑證完成 TLS 1.3 交握。 |
| TAK 8443 | 新管理員憑證與新 Alpha 憑證分別呼叫 `/Marti/api/version`，均取得 HTTP 200。 |
| Mumble、MediaMTX | `takbox.local:40000` 與 `takbox.local:8322` 均以 Root CA 驗證成功，實際 TLS 伺服器憑證簽發者為新中繼 CA。 |
| A 裝置 DPK | 建立 `atak-alpha-ca-BD337A0FCC2C.dpk`，透過熱點 `takbox.local:10065` 產生 20 分鐘、最多 3 次下載的短效 QR。QR 圖留在 Git 忽略的 `runtime/validation/`。 |

使用者於 A 裝置匯入新 DPK 後，確認 ATAK 已連線，且 Vx 的 Primary、Alternate、Medical、Emergency 四個頻道均可加入。這是新鏈的實機登入驗收；同時也通過上述伺服器端 TLS 與 8443 API 檢查。

撤銷前另使用舊 Alpha `100C` 憑證進行對照：8089 可以完成 TLS 1.3 交握，但 8443 `/Marti/api/version` 回報 TLS `certificate_unknown`，即使附上舊中繼 CA 憑證鏈仍如此。舊憑證尚未位於 Root CRL；因此不能把這個 8443 拒絕結果歸因於 Root CA 撤銷。8089 只觀察到交握，尚未證明 CoT 應用層接受舊身分。

## 待實機與撤銷驗證

使用者在 A 裝置確認 Data Packages → Download 可看到 `ATAK Local Voice`。因此新憑證的 8443 應用入口也完成實機檢查。

`scripts/publish_root_ca_revocation.py` 再次建立快照 `runtime/backups/ca-rotation-20260924T161732Z/`，發布 Root CRL 並在 `security/tls` 增加 Root CRL 項目。部署後 Root CRL 只列出舊中繼 CA 序號 `29AB8D5019C04133D511C77DA9E0B721085D6E13`，下次更新時間為 2026-10-24 15:51:37 UTC。OpenSSL 以完整 CRL 鏈驗證新 Alpha 憑證為 `OK`，舊 Alpha 憑證在鏈深度 1 為 `certificate revoked`。

首次發布後，TAK 8089 **仍接受舊 Alpha 憑證的 TLS 1.2 交握**，新 Alpha 的 8089 與 8443 亦正常。檢查 `truststore-root.jks` 和 `fed-truststore.jks` 後，發現兩者仍以 `tak-issuing-old` 把已撤銷的舊中繼 CA 直接列為信任錨。這會讓憑證路徑在舊 CA 停止，不能只憑 Root CRL 已發布就宣稱 8089 停權。測試用舊身分亦曾把 CoT 寫入 TLS 連線，但裝置 log 未找到對應 UID，故不將其記為已完成的應用層路由。

接著執行 `scripts/drop_revoked_ca_trust_anchor.py`：快照 `runtime/backups/ca-rotation-20260924T162347Z/`，移除兩個 TAK truststore 的 `tak-issuing-old`，保留 Root 與新中繼 CA，重新啟動 TAK Server。讀回兩個 truststore 均確認舊項目不存在，Root 與新 CA 項目仍在。新 Alpha 於 8089 完成 TLS 1.2 交握，8443 `/Marti/api/version` 回應 200；舊 Alpha 的新 8089 握手遭 `TLSV1_ALERT_INTERNAL_ERROR` 拒絕，8443 仍為 `certificate_unknown`。8443 在撤銷前已拒絕舊 Alpha，故無法由前後比較將其拒絕單獨歸因於 Root CRL。使用者再於 A 裝置確認新 DPK 的 ATAK 連線與 Vx 四頻道均成功。舊 DPK 的有效分享已停止。

為避免 ATAK 對同名 DPK 的快取行為，另將舊 Alpha `100C` 與新 Alpha DPK 各複製一份，變更 Manifest UID 與顯示名稱，放到 A 裝置 Download；憑證與私鑰內容不變。使用者先移除目前的 TAK 連線設定，手動匯入舊 DPK，確認 **ATAK 無法連線**。同一階段 Vx 仍能以既有 Mumble 身分加入頻道；Mumble 伺服器紀錄顯示有已認證的連線。這是預期的驗證界線：TAK 用戶端憑證撤銷不會自動停用 Mumble 密碼或註冊身分。接著使用者手動匯入新 CA 回復 DPK，確認 **ATAK 連線與 Vx 四頻道全部恢復**。兩份測試 DPK 僅在 Git 忽略的 `runtime/validation/ca-rotation/` 與 A 裝置 Download 留存。

控制台的簽發表單另外簽出短效測試憑證 `ca-web-probe-20260925`（序號 `C5008119`）；主機清冊確認 `registered=True`，TAK API 讀回 `local-test` In + Out，詳細頁 HTTP 200。簽發過程會重啟 TAK Server，測試 HTTP 用戶端等待 120 秒後逾時，但簽發與註冊最終完成；因此此項僅能判定後端成功，瀏覽器端等待體驗仍需檢查。

控制台清冊現在同時讀取作用中 CA 與封存舊 CA 紀錄。Root CRL 與封存 CA 憑證核對後，8 筆舊用戶端憑證顯示「簽發 CA 已撤銷」，並禁止再次交付。管理頁 GET 回應 200，舊 Alpha 與新 Alpha 均出現在 HTML；完整瀏覽器互動仍待驗收。A 裝置完成回復後，舊與新 DPK 的短效分享均已停止。輪替按鈕尚未接上自動化流程，不能把本次手動腳本視為可重複的一鍵輪替功能。
