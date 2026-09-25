# 2026-09-24 中繼 CA 輪替前置驗證

本次只做讀取、隔離 Root CA 資料庫試驗及本機快照；**沒有撤銷作用中的中繼 CA，也沒有重啟或切換服務**。完整步驟見[輪替計畫](../plans/ca-rotation.md)。

| 項目 | 結果 |
| --- | --- |
| Root CA | 目前憑證有效至 2036-09-18 15:54:07（臺灣時間）；預設簽發期限 3650 天。 |
| 作用中中繼 CA | 目前憑證有效至 2031-09-20 15:54:08（臺灣時間）；SHA-256 指紋 `1716634DF8C600A2295CF78228152173A72813B93AE91E08D46E65B581E16E64`；序號 `29AB8D5019C04133D511C77DA9E0B721085D6E13`。 |
| Root CA 資料庫 | `index.txt` 為空，`newcerts` 亦無檔案；不能依目前 Root DB 直接把作用中中繼 CA 標為已撤銷。中繼 CA 公開憑證可由 Root 驗證。 |
| 作用中簽發 CA 資料庫 | 共 12 筆葉憑證紀錄：9 筆有效、3 筆已撤銷。這是 CA DB 狀態，不代表每筆連線目前均可用。 |
| 隔離撤銷試驗 | 複製 Root DB 到 `runtime/validation/ca-rotation-root-crl-trial/`，使用原 Root 憑證與私鑰，但只對**副本**執行 `openssl ca -revoke`。OpenSSL 成功補登舊中繼 CA 並產出 Root CRL。該 CRL 含舊中繼 CA 序號；以 `openssl verify -crl_check` 驗證舊中繼 CA 得到 `error 23: certificate revoked`。 |
| 舊葉憑證鏈試驗 | 將隔離 Root CRL 與現有中繼 CRL 合併，以 `openssl verify -crl_check_all` 檢查舊 ATAK 用戶端憑證，於鏈深度 1 得到 `error 23: certificate revoked`。此為離線 OpenSSL 結果，**不是** TAK／Vx 實機驗收。 |
| 本機快照 | `python scripts/prepare_ca_rotation.py` 建立 `runtime/backups/ca-rotation-20260924T140905Z/`；184 個檔案的 SHA-256 全數吻合，包含 Root DB 與控制台 registry。目錄由 Git 忽略，含私鑰、密碼及 DPK，不可公開。 |
| Compose 基線 | 補用有權限的 shell 讀取 Docker 狀態：`tak-server`、`tak-db`、`mumble`、`share-admin`、`share-public` 均為 running／healthy；`mediamtx`、`media-preview`、`media-viewer`、`media-viewer-gateway` 為 running（未設定健康檢查）。 |

讀取 Docker Compose 狀態的第一次嘗試受到 shell 的 Docker pipe 權限限制；之後使用有權限的 shell 取得上述基線。後續實機驗收依[輪替計畫](../plans/ca-rotation.md#分開驗收atak-與-vx)分別記錄 ATAK 與 Vx 登入。操作畫面可截圖，但需去識別後才加入文件。

## 隔離新中繼 CA

23:27（臺灣時間）首次執行 `scripts/stage_ca_rotation.py`，以已核對的舊 CA 指紋為前置條件，在 Git 忽略的 `runtime/ca-rotation-stage/` 建立新中繼 CA、獨立簽發資料庫及未發布的 Root CRL。離線 OpenSSL 驗證中，新 CA 為 `OK`，舊 CA 為 `certificate revoked`。但首次候選的葉憑證序號會與舊 CA 清冊重複，因此**廢棄首次候選，不用於切換**。

23:51 重新產生候選，簽發序號起點避開舊 CA 已用的範圍。選定候選的 CA 指紋為 `BD337A0FCC2CE7A8A78677B347582CBB46EEB5649D9C757738E91BAAFFD08B01`；新服務與 Alpha／Bravo 用戶端憑證序號依序為 `C5008113` 至 `C5008118`。新 Root CRL 的離線驗證接受新 CA、拒絕舊 CA。隔離目錄已產出 TAK Server、管理員、Mumble、MediaMTX 憑證，以及兩份新 DPK；服務憑證鏈、四個 PKCS#12 與三個 JKS 均通過讀取驗證。作用中的 Root 資料庫、CA、服務憑證與部署 CRL 都沒有切換。這只驗證候選材料，尚不能代表 TAK、Vx 或其他服務已拒絕舊鏈。
