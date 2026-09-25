# 2026-09-25 憑證控制台瀏覽器驗證

以本機 Chrome 的 Playwright context，使用管理帳號的 HTTP Basic 認證實際開啟 `http://127.0.0.1:10066`。認證密碼從 Git 忽略的本機檔案讀取，未寫入命令、截圖或本頁。測試只執行 GET 與前端篩選、搜尋、顯示模式切換；未送出任何簽發、撤銷或群組異動。

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

完整原始截圖及機器可讀的 `results.json` 留在 Git 忽略的 `runtime/validation/browser/`，供本機核對；未把活動 QR、私鑰、密碼或完整指紋放入文件。此輪未驗證提交操作後的瀏覽器等待體驗；先前測試憑證簽發的 HTTP 用戶端曾在 TAK 重啟期間等待 120 秒逾時，儘管後端簽發與註冊完成，仍需單獨追蹤。
