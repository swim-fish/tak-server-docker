# 2026-09-25 憑證控制台瀏覽器驗證

以本機 Chrome 的 Playwright context，使用管理帳號的 HTTP Basic 認證實際開啟 `http://127.0.0.1:10066`。認證密碼從 Git 忽略的本機檔案讀取，未寫入命令、截圖或本頁。先檢查三種視窗寬度，再以專用的一小時測試憑證操作簽發與撤銷；測試 DPK 未分享或匯入 Android 裝置。

| 視窗寬度 | 清冊 | 預設檢視 | 詳細頁 | 群組頁 | 水平溢出 | JavaScript 錯誤 |
| --- | --- | --- | --- | --- | --- | --- |
| 1440 px | HTTP 200 | 清單 | HTTP 200 | HTTP 200 | 無 | 無 |
| 768 px | HTTP 200 | 卡片 | HTTP 200 | HTTP 200 | 無 | 無 |
| 390 px | HTTP 200 | 卡片 | HTTP 200 | HTTP 200 | 無 | 無 |

當時清冊共 11 筆，預設使用中顯示 3 筆。按「撤銷」顯示 8 筆，而且每筆都屬撤銷分類。搜尋 `ca-web-probe-20260925` 命中 1 筆；在撤銷篩選下顯示 0 筆，切回使用中後顯示 1 筆。三種寬度均可切換卡片與清單。群組頁預設的「使用中」按鈕 `aria-pressed=true`。詳細頁有群組權限區塊。未發現頁面 JavaScript 例外或文件寬度超出視窗。

另外在 1440 與 390 px 逐頁開啟五個主導覽頁面（檔案分享、引導式佈建、MediaMTX 管理、Mumble 管理、用戶端憑證）及憑證群組子頁。12 次載入均為 HTTP 200，主標題存在，無水平溢出或 JavaScript 例外。這是頁面載入檢查，不代表各頁的提交操作已重新驗證。原始結果存於 Git 忽略的 `runtime/validation/browser/console-pages.json`。

檢視過完整瀏覽器截圖後，選取兩張作為手冊圖：

- [清冊與篩選截圖](../images/certificate-console-inventory.png)：測試憑證 SHA-256 指紋經純影像遮蔽。
- [手機寬度群組頁截圖](../images/certificate-console-groups-mobile.png)：展示群組三種權限欄位。

### 瀏覽器簽發與撤銷

第一輪測試憑證 `browser-issue-revoke-20260925-muga4lve`（CRL ID `C500811A`）的簽發 POST 回報「TAK 註冊未驗證」。CA 已簽發並產生 DPK；稍後 TAK API 可以讀回 `local-test` 的 In／Out 群組。由憑證詳細頁重新儲存群組後，控制台確認已註冊。此輪再從清冊撤銷該憑證；CA 資料庫與已發布 CRL 均列為撤銷，TAK 恢復健康後，8089 新連線回報 `rejected-revoked`。首輪顯示，原本 90 秒的群組讀回窗口可能不足；這是依操作時間與後續成功讀回所作的推論，未取得原始內層例外。

長時間簽發／撤銷時，憑證 worker 原先只在作業開始前更新心跳。作業完成立刻跳轉到詳細頁或清冊，曾短暫出現 `Start the matching Windows management worker first`。已將心跳改為作業期間每秒更新，群組讀回等待上限調整為 150 秒，並單獨重啟 Windows 憑證 worker。作業進行中的排程工作狀態與心跳均顯示正常。

依要求執行 `docker compose down`、`docker compose up -d`，保留 volumes；TAK Server 健康後開始第二輪。Chrome 簽發 `browser-issue-revoke-20260925-mugb1g5r`（CRL ID `C500811B`），頁面直接跳到 `result=issued`，清冊顯示有效，TAK API 讀回已註冊及 `local-test` In／Out。隨後在確認視窗撤銷，頁面跳至 `result=revoked`，未再出現 worker 離線錯誤；清冊狀態為「憑證已撤銷」。後端結果顯示 CRL 已發布、TAK 已重啟、該序號在 CRL 中。剛重啟時自動 8089 探測為 `unverified`；待 TAK 健康後重測為 `rejected-revoked`。此測試未涵蓋 8443 的停權效果。

![同一張憑證的簽發與撤銷畫面](../images/certificate-browser-issue-revoke.png)

完整原始截圖及機器可讀的結果留在 Git 忽略的 `runtime/validation/browser/`，供本機核對；公開圖只保留狀態與 CRL ID，完整指紋已裁除。未把活動 QR、私鑰或密碼放入文件。
