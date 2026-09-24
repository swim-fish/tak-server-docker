# 2026-09-24 引導式佈建驗證

## TAK 批次憑證

Windows 管理 worker 以同一批次簽發兩張測試用戶端憑證，序號為 `100A`、`100B`。兩張各有獨立私鑰、PKCS#12 及 DPK；批次將兩個用戶端寫入 `UserAuthenticationFile.xml`，執行一次 TAK Server 重啟，再逐筆透過管理 API 讀回 `local-test` In／Out 群組。作業狀態為 `complete`。以同一作業 ID 與相同參數重送，約 0.1 秒返回既有結果，沒有重新簽發。控制台的批次預覽、重複送出不重建分享邏輯通過單元測試；Android 尚未匯入這兩張測試 DPK。

新簽發憑證與分享作業資料均位於 Git 忽略的 `runtime/`；本文件不包含 DPK、私鑰、密碼或 QR token。

## Vx 固定名稱替換

Windows 管理程式從已驗證的原生 Vx 匯出與四頻道清單產生 `vx-local` 的 Vx-only DPK，檢查 manifest、兩個 payload、JSON 頻道及 Protobuf Mission。新套件 SHA-256 為 `9a57a5f52c5a3411e1dc2620b0e5c135ffdf63126bf8ebad507313297f592467`。舊同名套件先由 TAK API 下載並核對 SHA-256 備份，再按確切 hash 刪除；上傳新包後，TAK Server 查詢只回傳唯一的 `ATAK Local Voice`，具備 `tool=public` 與 `keywords=["missionpackage"]`。

首次 metadata 寫入把 `tool` 值送成帶引號的 JSON 字串，TAK 5.8 回 HTTP 500，伺服器 API 日誌指出值不符允許的 regex。改為原始 `public` 字串後成功，`keywords` 仍使用 JSON 陣列。作業 journal 曾進入 `needs-recovery`，因新檔已上傳且 SHA-256 相符，重試只補齊 metadata 並讀回，最後狀態為 `complete`，沒有再次刪除或上傳。備份仍在 Git 忽略的 runtime 作業目錄。

這只驗證**伺服器端**固定名稱替換。Android 上新 DPK 的下載、四頻道登入，以及既有 `vx-local` 是否覆蓋或重複，仍待使用者操作與實機紀錄確認。

## 介面與程式檢查

`python -m unittest discover -s scripts/tests -p 'test_*.py' -q`：39 項通過，包含批次憑證預覽、相同確認表單重送不重建分享，以及模擬 Vx 新檔上傳失敗後，從 SHA-256 驗證備份恢復舊套件。`python -m compileall -q scripts`、`node --check docker/share-portal/static/new_certificate.js` 與 `git diff --check` 通過。Chrome 已開啟新增 TAK 用戶端引導頁，確認欄位、群組與分享限制可見；正在執行的控制台對新憑證雙筆預覽、Vx 四頻道預覽及 Vx 結果頁均回 HTTP 200。Vx 備份恢復目前只經模擬驗證；正式部署前仍應在隔離環境演練真實 TAK API 的失敗與恢復。
