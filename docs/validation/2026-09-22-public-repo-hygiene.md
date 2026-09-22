# 2026-09-22 公開儲存庫衛生稽核

- 目標：`master` 的 `b1b50acedf02412065d997aad7d4ba186af5bfc6`，以及本輪尚未提交的文件變更。
- 範圍：本機 Remediate 稽核；分別檢查 working tree、staged、HEAD tree，並補查 HEAD 可追溯的全部 5 次提交。
- 內容結果：**PASS（限上述本機範圍）**，未發現已確認的敏感資料曝露。
- 提交前的正式發布檢查：**BLOCKED**。當時文件尚未提交，工作目錄與 index 不一致；提交後須對新的明確 commit 重跑，本紀錄保留提交前狀態。

## 採用政策

依 `audit-public-repo-hygiene` 檢查敏感資料、metadata、二進位檔與歷史。採用專案既有規則：`runtime/`、`vendor/`、secrets、裝置憑證包、私鑰及診斷產物不進版控；`docs/images/*.jpg` 使用 Git LFS。

沒有額外套用「所有一般 metadata 都阻擋發布」的規則。Git 維護者身分與檔案中的私人識別資料分開審查；公開作者資料本身不列為曝露。範例主機名稱、熱點網段及測試頻道是本專案的操作範例，不是秘密值。

## 發現與處理

| 等級 | 類別 | 去識別位置 | 處理 |
| --- | --- | --- | --- |
| VERIFIED | 個資／憑證模式及本機密碼比對 | 工作目錄、index、HEAD 及可追溯歷史 | 未命中已知本機識別字串、私鑰內容或目前 8 份 secret 值。 |
| VERIFIED | 圖片複核 | `docs/images/` 的 6 張 JPG | 已檢視畫面、metadata 及 LFS 物件；解除原始掃描的人工複核警告。 |
| BLOCKER（發布流程） | 尚未固定最終版本 | 工作目錄與 index | 文件提交後，對新的明確 commit 重跑發布檢查。此項不是秘密資料發現。 |

沒有已確認的曝露需要刪除或替換，因此本輪未修改圖片、程式或 Git 歷史。新增本紀錄並在驗證索引加入入口，保留稽核依據。

## 已驗證範圍

### 工作目錄與暫存區

- 初次完整清冊有 60 個現有非忽略檔案，包含尚未追蹤的新說明文件。
- staged 掃描無候選問題；另將 index blob 與本機 secret 值比對。
- 工作目錄文字使用同一套模式掃描，補查已知本機識別字串；不只檢查 staged diff。
- `runtime/` 與 `vendor/` 的本機產物按副檔名盤點，並確認不在目前 index；未將它們加入發布輸入。

### 歷史與 metadata

- 掃描 HEAD 可追溯的 5 次提交及 64 個不同 Git blob。
- 內容 patch 與 commit message、作者／提交者、ref 名稱分開檢查。
- 4 個本機 refs 的名稱及可用 tag metadata 已檢查。未把不屬於 HEAD 祖先的其他目標宣稱為通過。
- 沒有發現需執行歷史清理或密碼輪替的已確認曝露；未改寫、刪除或推送任何 ref。

### Git LFS、圖片與產物

- 5 個歷史 tree 的圖片都是有效 LFS pointer，具 attribute 規則。
- 可追溯歷史共有 6 個不同 JPG 內容版本，均與已檢視的工作目錄圖片相同；本機 LFS 物件存在且 SHA-256 相符，`git lfs fsck` 成功。
- 圖片沒有 EXIF、GPS、XMP、作者或裝置 metadata；JPEG 編碼資訊不視為個資。
- 畫面未見明文密碼、呼號、裝置序號或個人座標。舊設定圖有遮罩密碼欄及一般地圖背景；新密碼提示圖是空白欄位。舊通訊埠已由歷史說明標示。
- 目前 tree 與可追溯內容沒有非 LFS 原始二進位檔，也沒有受控的 DPK、APK、JAR、ZIP、私鑰或資料庫產物。

## 檢查證據與限制

本機去識別結果保留在 Git 忽略的 `runtime/hygiene-audit-2026-09-22/`，包含 staged／tree／publish JSON、工作目錄補充掃描、歷史與 index 比對及圖片 SHA-256／metadata 清冊。`metadata-reviewed` acknowledgement 對應已完成的六張圖片檢視，不是略過檢查。

本次未查遠端 GitHub Release notes、assets、CI artifacts 或遠端 LFS 物件可下載性；未指定任何 release asset，因此沒有對發布檔案大小或下載 SHA-256 作保證。忽略目錄中的原始套件、logcat 與憑證包只確認隔離狀態，未把它們當成可公開附件驗收。

未掃描 reflog、不可達物件、stash 內容或 HEAD 以外分支的獨有歷史。模式掃描與目前 secret 的比對不能證明不存在未知或已輪替的秘密值，不能據此宣稱整個儲存庫可立即公開。

## 外部或破壞性操作

本輪沒有需要執行的密碼輪替、歷史改寫、force-push 或 release 替換。若未來發現已發布的秘密，應另行確認撤銷／輪替及歷史清理範圍；只刪除現行文字不足以消除歷史曝露。
