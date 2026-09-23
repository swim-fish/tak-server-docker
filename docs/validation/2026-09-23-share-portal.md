# 分享與 Mumble 管理頁驗證

日期：2026-09-23。Windows Docker Desktop、本機熱點 `192.168.137.1`、`takbox.local`。本紀錄區分程式測試、Compose 驗證與尚未執行的實機操作。

## 已完成

- `docker compose --profile sharing config --quiet` 通過；`share-admin` 綁定 `127.0.0.1:8766`、`share-public` 綁定 `192.168.137.1:8765`。管理容器沒有 Docker socket。
- 單元測試涵蓋時間／次數先到停止、並行下載名額不超額、QR／HEAD 不計次、完整下載後計數、ICU 密碼不出現在 QR、來源資料夾分組、Vx Mission 排除、停止紀錄灰階，以及 Mumble 選取指紋與密碼輪替失敗回復。最終 10 項通過。
- Compose 實際以無機密 ZIP 做一次公開 GET：HEAD 不計次；限額 1 的首次 GET 成功，第二次為 HTTP 410。手動停止與全部暫停／恢復也已測試。
- Flask 管理頁 GET 為 200，未帶授權被拒。Mumble 頁經 Windows 前景管理程式唯讀取得線上 session 與註冊身分；未勾選確認的刪除／重設 POST 為 400。
- Playwright 使用合成名稱及 token 檢查控制台：活躍連結置頂、已結束列灰階、QR／停止按鈕分欄；Mumble 刪除按鈕在未選取時停用，選取後才可開確認視窗，確認 checkbox 未勾時最終按鈕停用。
- 已將本機 `runtime/packages/` 內的 ATAK DPK、PKCS#12 與 checksum 移到 `runtime/packages/atak/`；ICU 設定與 QR 移到 `runtime/packages/icu/`。兩個目錄仍在 Git 忽略範圍。
- 已由使用者核准 UAC 啟動分享防火牆前景規則，核對為 `Wi-Fi 4`、主機 `192.168.137.1`、來源 `192.168.137.0/24`、TCP 8765。前景視窗按 Ctrl+C 後會移除該規則。
- Chrome 在本機表單 POST 送出 `Origin: null`、`Sec-Fetch-Site: same-origin`，原本的 Origin 白名單會回傳 403。管理服務現接受此組合且要求目標 Host 為 loopback；實際按下全部暫停／恢復均成功。以無副作用的 POST 確認跨站標記與錯誤 CSRF 仍回傳 403。
- 公開路由改由 Flask／Gunicorn 提供。最終測試映像內 10 項單元測試通過；容器實際提供 QR 頁與 PNG、HEAD 不計次、首次 GET 完成 `1 / 1` 下載，第二次 GET 回傳 410。新增 ATAK `tak://.../import` QR 與帶原始副檔名的下載路由；Vx Mission DPK 從來源清單排除並由後端拒絕分享。
- 瀏覽器檢查手機 390 px、平板 820 px、桌機 1440 px、超寬螢幕 2200 px：分享管理頁無橫向溢出；Mumble 管理頁手機採卡片、桌機採雙欄；公開 QR 頁在手機可完整顯示 QR 與下載入口。測試後已還原瀏覽器視窗寬度。
- 依介面檢查結果，移除先前測試用的 `runtime/share-inbox/` 來源選項；後端同步拒絕 `inbox:` 來源，既有檔案與已結束的測試紀錄保留。
- 控制台即時更新驗證：Chrome 開啟管理頁後未重整，加入無機密測試 ZIP，來源選單自動新增；另建立一筆限時 1 分鐘、最多 1 次下載的分享，2 秒內出現於有效連結與紀錄。停止後有效連結消失、紀錄改為「已手動停止」及灰階。刪除該測試紀錄與 ZIP 後，頁面也自動移除，測試快照已清除。
- 改用受 Basic 認證保護的 `/admin.js` 載入即時更新程式，CSP 允許同源腳本；瀏覽器顯示最後同步時間。整套 Python 單元測試 21 項通過，JavaScript 語法檢查通過。

## 限制

- 新分享頁的 TAK 憑證 QR、Vx QR 與 ICU QR 已由 Android 實機測試；TAK 與 ICU 成功，Vx QR 雖下載成功但不能建立 Mission，改由 TAK Server Download 成功。詳見[分離佈建驗證](2026-09-23-qr-tak-vx-icu.md)。
- Mumble 踢除、取消註冊、重設共用密碼及重新啟動的網頁端操作尚未對真實使用者執行；僅唯讀清單與無副作用的阻擋流程已驗證。
- 分享 HTTP 僅限受控熱點測試；尚無 HTTPS 或遠端管理支援。防火牆前景工作階段結束後，實機測試前須重新啟動規則。
