# 檔案分享與 Mumble 管理頁

公開下載使用 Docker Compose `sharing` profile；本機管理頁 `share-admin` 已列入預設服務，執行 `docker compose up -d` 時會啟動。兩者均由 Flask／Gunicorn 提供。公開容器只綁定 Windows 熱點的 `192.168.137.1:8765`；管理容器只綁定 Windows 本機的 `127.0.0.1:8766`。兩者不提供目錄瀏覽，並設為 Docker 自動重啟。

本機管理頁另有[用戶端憑證控制台](../tak-server/certificate-console.md)，可管理憑證、群組與專屬 DPK；其 Windows 管理程式與 Mumble 管理程式由登入後排程工作啟動。

## 啟動

先啟用熱點與 `takbox.local` mDNS，再於專案根目錄執行：

```powershell
python .\scripts\init_share_portal.py
.\scripts\Manage-TakControlWorkers.ps1 -Action Install
docker compose --profile sharing up -d --build share-admin share-public
.\scripts\Install-SharePortalFirewall.ps1
```

防火牆腳本會要求 UAC，只開放熱點網段的 TCP 8765；在該視窗按 Ctrl+C 會移除本次規則。管理頁不需對熱點開放防火牆通訊埠。於 Windows 主機瀏覽器開啟 `http://127.0.0.1:8766`，使用 `admin` 與 `runtime/secrets/share_admin_password` 的內容登入。密碼只在本機讀取，不要貼入聊天或文件。若本機 `.env` 將公開下載改到其他主機通訊埠，使用 `-Port <SHARE_PUBLIC_HOST_PORT>` 啟動防火牆腳本；管理頁網址則使用 `<SHARE_ADMIN_HOST_PORT>`。容器內仍維持 8765／8766。

## 分享規則

可建立兩種分享：

| 類型 | 來源與 QR 行為 |
| --- | --- |
| ICU 設定 | 可即時用目前 `mediamtx_publish_password` 產生 `initial.prefs`，或選 `runtime/packages/icu/` 內的 `.prefs`。QR 開啟 `icu://download?url=...`。 |
| ATAK DPK／ZIP | 從 `runtime/packages/atak/` 選檔，建立當下複製快照。QR 使用 `tak://com.atakmap.app/import?url=...` 交給 ATAK 下載及匯入；仍須由使用者確認。直接用瀏覽器下載則須自行在 ATAK 匯入。 |

新增分享的來源選單依 `runtime/packages/icu/`、`runtime/packages/atak/` 分組；ICU 即時產生另列一組。舊測試目錄 `runtime/share-inbox/` 不再顯示，也無法作為新增分享來源；需要保留的 DPK／ZIP 可手動移至 `runtime/packages/atak/`。手動產生的 ICU 設定檔與 QR 放在 `runtime/packages/icu/`，其產生器見 [ICU QR Code](../mediamtx/icu-qrcode.md)。分享頁產生的快照存於 Docker `share-files` volume，統計存於 `share-state` volume，兩者都可能含憑證或密碼。不要公開備份或使用 `docker compose down -v` 清除整套服務資料。

每筆分享至少設定停止時間或下載上限，也可兩項都填；先達到的條件即停止後續下載。QR 顯示與 HEAD 不計次；公開端接受一次檔案 GET 就使用一次名額。管理頁顯示已接受與完整送出的次數，可單筆停止或暫停全部分享。控制台開啟期間每 2 秒同步總開關、分享清單、下載次數、有效連結和來源檔案；切回分頁時立即同步。頁首顯示最後同步時間，連線失敗時顯示重試狀態。同步不清除正在填寫的停止條件或有效的來源選擇。總開關位於頁面上方；全部暫停時會顯示大型暫停符號與紅色狀態區塊。已結束的紀錄以灰底顯示，不再提供停止按鈕。分享網址是隨機高熵 token；停止分享或到期後，檔案快照仍留在 volume，需另外執行資料保留清理。

分享紀錄預設每頁 10 筆，可切換為 20 或 30 筆，並可隱藏已手動停止、到期或次數額滿的紀錄；總開關暫停中的分享仍會顯示。篩選後的頁數與筆數隨即時同步更新。「檢視 QR」與目前分享連結會在管理頁彈出 QR 視窗；視窗仍提供公開連結供複製或另開。QR 圖由已登入的管理站點提供，分享停止、到期或達下載上限後即無法再顯示。「分享中」的紀錄每秒更新剩餘時間，並於每次伺服器同步時校正；未設定停止時間時顯示「無時間限制」。

介面依寬度調整：手機使用單欄與卡片式紀錄，平板保留單欄但展開表單，桌機將分享狀態與新增分享並排，超寬螢幕限制內容最大寬度。Mumble 管理頁在桌機將線上連線與已註冊身分並排；公開 QR／下載頁保持易掃描的窄版面。

控制台與公開下載頁使用隨容器映像提供的 Bootstrap 5.3.8，不需從外部 CDN 載入。樣式檔、互動元件程式與 MIT 授權文字放在 `docker/share-portal/static/bootstrap/`；專案的色彩、卡片與響應式規則集中於 `docker/share-portal/static/console.css`。手機版的 Mumble 與分享紀錄改為緊湊資訊列；憑證清冊在手機版以卡片顯示重要狀態，完整指紋可進入憑證詳細頁查看。撤銷、刪除註冊身分、重設 Mumble 密碼及重啟確認使用 Bootstrap Modal，按鈕必須先勾選確認項目才可提交。

公開傳輸目前為 HTTP。ICU 設定含可重複使用的 MediaMTX 發布密碼，ATAK DPK 也可能含裝置私鑰；只在受控熱點短時間分享，設小額度並在完成後停止。掃碼裝置需與熱點位於相同可達網段，且能解析 `takbox.local`。若要跨網段或長期使用，需先部署經 ICU 實機驗證的 HTTPS 與存取控制。

ATAK QR 的下載 URL 會以原始 `.dpk`／`.zip` 檔名結尾，讓匯入器辨識格式。TAK 憑證 DPK 內含裝置私鑰，必須為每台裝置建立各自的短效分享。Vx-only DPK 不含 TAK 憑證，但本次 QR 實測只進入 ATAK 一般匯入流程，未建立 Mission；分享頁會辨識其 `onReceiveAction`，從來源清單排除並拒絕建立 QR 分享。Vx 設定應從 [TAK Server Data Packages](../atak/vx-missions.md#從-tak-server-下載任務) 下載。ICU QR 使用獨立的 `icu://download?url=...`；TAK 連線與 ICU 可各自建立及停止 QR 分享。

## Mumble 管理

管理頁的「Mumble 管理」提供搜尋、單筆／多選／全選／全部不選，且把線上連線與已註冊身分分開：

| 操作 | 效果 |
| --- | --- |
| 中斷線上連線 | 踢除所選 session；用戶端可以重新登入。 |
| 刪除註冊身分 | 先備份 Mumble SQLite，核對身分指紋，再取消註冊並中斷所選身分的連線。用戶端後續可能重新註冊。 |
| 重新啟動 Mumble | 只重建 `mumble` 容器，中斷目前連線；保留 volume 與憑證。 |
| 重設共用密碼並重新啟動 | 產生新密碼，寫入 `runtime/secrets/mumble_server_password`，備份舊值，再重建 `mumble` 容器。已註冊身分可能不再要求共用密碼。 |

這些操作由 Windows 主機程式執行，Flask 容器沒有 Docker socket。線上連線與取消註冊走 Mumble 原生協定；註冊清單及一致性備份由按需啟動、共用 `mumble-data` volume 的 `mumble-db-helper` 完成。只有重建 Mumble 仍由 Windows 程式呼叫 Compose。完成上方的排程工作安裝後，Mumble 管理程式會立即啟動，且在目前使用者登入 Windows 後自動啟動。檢查狀態：

```powershell
.\scripts\Manage-TakControlWorkers.ps1 -Action Status
```

如需前景診斷，先用 `-Action Stop` 停止排程，再執行 `python .\scripts\mumble_control_host.py`；按 Ctrl+C 只停止管理程式，不停止 Mumble 或分享服務。刪除註冊與重設密碼需在確認視窗勾選，確認按鈕才會啟用。操作前若有人在線，先通知相關使用者；此介面的中斷與重啟會立即影響連線。備份留在版控忽略的 `runtime/mumble-admin/` 與 `runtime/share-control/backups/`，程式紀錄在 `runtime/share-control/worker.log`，均不可公開。Vx 無法在 UI 指定任意 Mumble Username，詳見 [Mumble 使用者](../mumble/users.md)。

背景排程執行 Docker 查詢與 Mumble 重啟時使用 Windows 無主控台模式，開啟 Mumble 管理頁不會另外跳出命令視窗。

## 驗證與停止

```powershell
docker compose --profile sharing ps share-admin share-public
Invoke-WebRequest http://127.0.0.1:8766/healthz
Invoke-WebRequest http://192.168.137.1:8765/healthz
```

健康檢查只代表 Web 服務存活。要驗證 QR，先建立短效、單次分享，再從熱點裝置掃碼並核對實際 ICU 欄位或 ATAK 匯入結果。完成後停止測試分享與防火牆前景工作階段。若要停用兩個 Windows 管理程式，執行 `Manage-TakControlWorkers.ps1 -Action Stop`；若要關閉 Web 服務，執行 `docker compose --profile sharing stop share-admin share-public`。手動停止的容器不會被 `unless-stopped` 自動重新啟動。
