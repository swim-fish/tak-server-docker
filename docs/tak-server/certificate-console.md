# 用戶端憑證控制台

Windows 主機的 `http://127.0.0.1:8766/certificates` 提供用戶端憑證清冊、群組修改、逐筆簽發、DPK 交付及批次撤銷。CA 私鑰與 Docker 控制留在 Windows 管理程式；Flask 容器只透過 `runtime/tak-cert-control/` 佇列提交受限操作。

## 啟動

先完成 [TAK Server 啟動](operations.md#啟動檢視與停止)及[分享服務初始化](../sharing/portal.md#啟動)。主機需有 `python`、`openssl`、`keytool`、`docker`：

```powershell
python -m pip install -r .\scripts\requirements-tak-certificate-host.txt
python .\scripts\init_share_portal.py
.\scripts\Manage-TakControlWorkers.ps1 -Action Install
docker compose up -d --build share-admin
```

`Install` 為目前 Windows 使用者建立憑證與 Mumble 兩個登入後自動啟動的排程工作，安裝後立即啟動。執行工作需要該使用者登入 Windows；主機程式持續讀取本機佇列，不將 CA 私鑰或 Docker socket 掛入 Flask 容器。可用以下指令查狀態、重新啟動或移除兩個排程工作：

```powershell
.\scripts\Manage-TakControlWorkers.ps1 -Action Status
.\scripts\Manage-TakControlWorkers.ps1 -Action Start
.\scripts\Manage-TakControlWorkers.ps1 -Action Stop
.\scripts\Manage-TakControlWorkers.ps1 -Action Uninstall
```

主機程式紀錄分別位於 `runtime/tak-cert-control/worker.log` 與 `runtime/share-control/worker.log`。排程與手動前景執行共用單例鎖；已安裝排程時，不需再手動執行 `tak_certificate_host.py`。若要在前景診斷，先以 `-Action Stop` 停止排程，再執行 `python .\scripts\tak_certificate_host.py`；按 Ctrl+C 只停止該程式。

背景排程執行 Docker 或 OpenSSL 指令時使用 Windows 無主控台模式，開啟憑證清冊或詳細頁不會另外跳出命令視窗。

使用原有管理帳號 `admin` 與 `runtime/secrets/share_admin_password` 登入。只看清冊時可不啟動 TAK Server；群組讀回、簽發與撤銷需要 `tak-server` Compose 服務執行。若 Windows 熱點的 `192.168.137.1` 未啟用，TAK 與分享容器的對外通訊埠可能無法綁定。若 Windows 保留了 8443、8765 或 8766，可在 Git 忽略的本機 `.env` 設定 `TAK_HTTPS_HOST_PORT`、`SHARE_PUBLIC_HOST_PORT` 與 `SHARE_ADMIN_HOST_PORT`；這只改主機對外通訊埠，容器內的服務仍使用原通訊埠。管理頁網址與 QR 連結會使用設定的新通訊埠，既有裝置或防火牆規則也需配合更新。**ATAK Data Packages 下載器實測固定連 `takbox.local:8443`**；若只把 TAK HTTPS 映射改到替代主機通訊埠，8089 雖可登入，套件查詢仍會逾時。

需要熱點裝置存取替代通訊埠時，以 `Install-TakFirewall.ps1 -AdminPort <TAK_HTTPS_HOST_PORT>` 與 `Install-SharePortalFirewall.ps1 -Port <SHARE_PUBLIC_HOST_PORT>` 配合設定。`share-admin` 已設為 Docker 自動重啟；公開分享容器第一次仍需使用 `docker compose --profile sharing up -d share-public` 啟動，之後會自動重啟。Windows 登入後會自動啟動兩個管理程式；Docker Desktop 仍須啟動。

## 清冊與群組

清冊讀取 `runtime/pki/private/ca-db/index.txt` 及 `newcerts/`，只列出具 `clientAuth` 用途的憑證，排除 TAK Server 與管理員憑證。CA／CRL 的辨識鍵是簽發者加序號；SHA-256 指紋用來核對 TAK 註冊身分。顯示名稱及 CN 可以重複，不能當作唯一鍵。

到期日依憑證 `notAfter` 顯示為台灣時間；剩餘天數由實際時間差計算。少於 24 小時顯示「少於 1 天」，到期顯示「已過期」。清冊依到期日排序，可搜尋、篩選 30 天內到期項目，或選擇隱藏已撤銷憑證。統計列顯示目前顯示、隱藏及總筆數；搜尋或篩選時才顯示對應的符合筆數。「隱藏」是總筆數減去目前顯示筆數。寬度達 1100px 時預設清單，較窄時預設卡片；可手動切換，瀏覽器分別記住兩種寬度下的選擇與隱藏選項。兩種顯示方式共用搜尋、多選與撤銷操作。到期與撤銷分開顯示。

點入憑證後，群組分為未指派、In／寫入、Out／讀取、In + Out／讀寫四個清單。可拖曳群組到目的清單，或點選多個群組後用「移至清單」批次移動。新群組先加入未指派清單，再移至需要的權限；儲存時至少須有一個 In 或 Out 群組。寬螢幕將三個權限清單並排顯示，未指派清單位於上方。既有身分的儲存使用 TAK 5.8 `PUT /Marti/api/user-management/api/update-groups`，再以 `GET /Marti/api/user-management/api/get-groups-for-user/{username}` 讀回比對。Windows 管理程式使用 `admin.pem` 和加密管理私鑰連線，以 Root CA 驗證 TAK Server；同時從共用 `UserAuthenticationFile.xml` 核對 CN、指紋與角色。修改既有憑證的群組不用重做 DPK，也不用重啟 TAK。對無法讀回或指紋不符的既有身分，控制台拒絕修改；新簽發但註冊未完成的憑證可從同一頁重試。

## 新裝置憑證與 DPK

輸入裝置顯示名稱、ASCII 憑證 CN，以及 In／Out 群組後，主機程式用現有中繼 CA 與 `openssl ca` 資料庫簽發兩年效期的用戶端憑證。簽發前檢查中繼 CA 效期並備份 CA 資料庫。每筆裝置有獨立的加密私鑰、PKCS#12 密碼與 DPK，不覆寫 bootstrap 原有的 `clientCert.p12` 或 `atak-local-test.dpk`。

產出的 `atak-<CN>-<serial>.dpk` 位於 `runtime/packages/atak/`，包含 Root 與中繼 CA 信任庫、裝置憑證、私鑰及 `takbox.local:8089:ssl` 連線設定。PKCS#12 密碼依 ATAK 匯入格式寫在 DPK 的 `servers.pref`，因此整份 DPK 都是敏感資料。TAK 5.8 的已驗證 REST API 可管理群組，但沒有供此流程設定憑證指紋的介面；新簽發的 CN、SHA-256 指紋與群組會寫入 bind mount 的 `runtime/tak/UserAuthenticationFile.xml`，保留檔案 inode，再重啟 TAK 一次並由 API 讀回驗證。若簽發成功但註冊失敗，清冊保留該憑證並標示未驗證，可從群組頁重試。簽發是不可回復的 CA 紀錄，不能因後續步驟失敗就刪除 CA 資料庫列。

控制台不執行 `UserManager.jar`。它仍可用於首次授予 `admin` 權限及人工修復；這兩種手動操作列在 [TAK Server 操作](operations.md)。控制台只在新憑證註冊、CRL 發布或復原時重啟 TAK；群組 API 更新不重啟。

控制台不自動分享新 DPK。在憑證頁勾選確認後，才會用目前熱點 HTTP 建立 **20 分鐘、最多 3 次下載**的 QR 分享。此方式只適用受控熱點；跨網段或長期交付應先完成 HTTPS 與裝置端驗證。停止分享只會讓連結失效，不會清除已匯入裝置的憑證。

## 批次撤銷與驗證範圍

在清冊選取憑證並於確認視窗勾選後，控制台先停止關聯 QR 分享；主機程式逐筆以 `openssl ca -revoke` 更新中繼 CA 資料庫，整批只發布一次 CRL 並重啟一次 TAK Server。已撤銷憑證的 DPK 從分享來源移到 `runtime/tak-cert-control/retired-packages/`。已下載的副本仍可能存在，撤銷不可回復。

結果分別顯示 CA 撤銷、已發布 CRL 是否包含序號、TAK 重啟，以及使用原憑證新建 8089 TLS 連線的結果。只有收到 `certificate revoked` 警示才標成「8089 已拒絕撤銷憑證」；私鑰缺失、熱點不可達、逾時或其他錯誤都顯示未驗證。若顯示「意外接受憑證」，應檢查 TAK 的 CRL 載入。控制台**不自動驗證 8443**；其 connector 維持沒有 `crlFile`，不能僅從 8089 結果推定 8443 已停權。2026-09-24 另以同一張實機測試憑證手動驗證：撤銷前 8443 回 HTTP 200，撤銷後 TLS 回 `certificate unknown`，詳見[實測紀錄](../validation/2026-09-24-qr-e2e-revocation.md)。

若撤銷已寫入 CA 資料庫，但 CRL 發布或 TAK 重啟失敗，可使用清冊的「重新發布 CRL 並重啟」復原操作。此操作重新產生 CRL、重啟 TAK，並重新檢查已撤銷憑證的 8089 新連線；它不會恢復已撤銷憑證。

每次變更前的 CA 資料庫、CRL 及 `UserAuthenticationFile.xml` 備份位於 `runtime/tak-cert-control/backups/`；操作紀錄及最近結果位於同目錄。這些資料與 `runtime/pki/private/clients/` 的私鑰及密碼檔都不進 Git。備份檔不足以還原 PostgreSQL／Ignite 使用者狀態，仍須配合整套服務備份。

## 實機驗收與剩餘範圍

2026-09-24 已用新簽發的實機測試憑證確認短效 DPK QR 匯入、8089 登入、In／Out 群組 API 讀回，以及撤銷後 8089 新連線拒絕。第一次簽發在 TAK 重啟後過早讀取 API，被標為註冊未驗證；控制台已加上 API 就緒等待，並用同一張憑證重試成功。仍需另外驗證不同 In／Out 群組間的實際資料讀寫、更多裝置，以及控制台自動化的 8443 撤銷判讀。
