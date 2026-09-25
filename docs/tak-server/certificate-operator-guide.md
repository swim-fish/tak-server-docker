# TAK 憑證控制台使用手冊

本手冊供本機測試環境的操作人員使用。控制台管理 TAK 裝置憑證、In／Out 群組、短效 DPK 分享與 CRL。TAK 憑證、Vx 的 Mumble 登入身分與 MediaMTX 發布身分各自驗證；停用其中一種，不會自動停用另外兩種。

![TAK 控制台頁面功能魚骨圖](../images/console-page-fishbone.png)

![憑證信任鏈與驗證邊界](../images/certificate-trust-chain.png)

## 開啟控制台

1. 啟動 Docker Desktop，在專案目錄執行 `docker compose up -d --build`。需要 QR 分享時，另執行 `docker compose --profile sharing up -d share-public`。
2. 登入 Windows 後，以 `.\scripts\Manage-TakControlWorkers.ps1 -Action Status` 檢查憑證與 Mumble 管理程式。若尚未安裝，執行 `-Action Install`；詳見[控制台啟動說明](certificate-console.md#啟動)。
3. 在 Windows 瀏覽器開啟 `http://127.0.0.1:10066/certificates`。使用帳號 `admin`，密碼只從本機 `runtime/secrets/share_admin_password` 讀取，不貼到聊天、截圖或 Git。若 `.env` 調整 `SHARE_ADMIN_HOST_PORT`，請使用實際映射通訊埠。

管理入口僅綁定 Windows 本機。供 Android 匯入的 QR 分享使用另一個公開入口；不要將管理網址交給裝置。

## 憑證清冊與詳細頁

清冊預設顯示「使用中」；點「逾期」、「撤銷」或「全部」切換狀態。搜尋可輸入裝置名稱、CN、憑證序號或指紋；「只看 30 天內到期」可與搜尋並用。統計列分別顯示目前顯示、隱藏、總計及符合搜尋的筆數。寬螢幕預設清單，窄螢幕預設卡片，也可手動切換。

![清冊篩選與狀態統計，測試憑證的 SHA-256 指紋已遮蔽](../images/certificate-console-inventory.png)

點「檢視群組與交付」開啟詳細頁。先核對 CN、`序號（CRL ID）`、簽發者、到期日、SHA-256 指紋及 TAK 讀回的群組。相同 CN 可能重複；操作時以**簽發 CA 身分加憑證序號**辨識憑證，以指紋核對 TAK 註冊身分。封存憑證標示「簽發 CA 已撤銷」或「已停用」，只供查閱；「憑證已撤銷」則是該葉憑證本身的狀態。

## 設定 In／Out 群組

「依群組檢視」將每個群組的憑證分成 **In／寫入**、**Out／讀取**、**In + Out／讀寫**。預設只看使用中憑證。可以拖曳憑證、使用「移動」、從群組移除，或在群組內按「新增憑證」搜尋後勾選。所有變更先保留在瀏覽器，按「儲存群組變更」並確認後才寫入 TAK；關閉頁面前應確認待儲存數量為零。詳細頁也可將群組拖曳到四個清單後儲存。

![手機寬度的群組檢視，展示 In、Out 與 In + Out](../images/certificate-console-groups-mobile.png)

驗收群組隔離時，要經 TAK Server 傳送 CoT；同一 Wi-Fi 的本機廣播不能證明伺服器群組規則。2026-09-24 的 Alpha／Bravo 測試中，兩台裝置各自傳送標記後，只有同群組端收到；完整紀錄見[群組實測](../validation/2026-09-24-ca-rotation-device-baseline.md)。

## 簽發裝置憑證與交付 DPK

1. 在「用戶端憑證 → 建立裝置憑證」填裝置顯示名稱及唯一的 ASCII CN，設定 In／Out 群組。
2. 可留空採預設效期，或在日曆指定到期日；快捷選單有 1 小時、1 天、7 天、14 天、28 天及 90 天。**憑證效期**與稍後的 **QR 分享效期**是兩件事。
3. 按「簽發並註冊裝置憑證」。此操作會產生專屬私鑰、PKCS#12 與 DPK，註冊後重啟 TAK。等待頁面及 TAK API 讀回；若頁面逾時，先回清冊核對 CN、序號、註冊狀態及群組，避免重複簽發。
4. 詳細頁確認裝置憑證有效、已註冊後，勾選確認建立短效 QR。預設分享 20 分鐘、最多 3 次下載；先到期或先達下載上限就停止。分享連結與 DPK 含裝置私鑰，僅在受控熱點交付。
5. 在對應 Android 裝置用系統相機點完整 `tak://` 連結，確認 ATAK 匯入及 `takbox.local:8089:ssl` 已連線。不同裝置要使用各自的 DPK。若重匯入同名 DPK 沒有更新，先清除 ATAK Data Packages 下載目錄中的舊副本，再確認伺服器清單；實機曾遇到重名套件快取。

批次建立 1 至 10 台裝置時使用「引導式佈建 → 新增 TAK 用戶端」，逐台設定 CN、期限與群組，先在預覽頁核對，再執行。每台有獨立 DPK 與 QR；整批只重啟 TAK 一次。參考[完整功能說明](certificate-console.md#新裝置憑證與-dpk)。

## 撤銷、CA 輪替與復原

清冊可多選有效憑證，按「撤銷選取的憑證」，在確認視窗勾選後才送出。控制台會停止關聯的 QR 分享、更新中繼 CA 的 CRL 並重啟 TAK。TAK Server 必須重新載入 CRL，才會套用憑證撤銷結果；一般撤銷流程已自動執行。撤銷不可回復；已下載的 DPK 不會從裝置自動消失，但新的 TAK 連線應遭拒絕。若撤銷紀錄已寫入，但 CRL 發布或重啟失敗，可用「重新發布 CRL 並重啟」。此操作依目前 CA 資料庫重新產生 Root CA 與簽發中繼 CA 的 CRL，不新增或恢復撤銷紀錄，也不會撤銷整個中繼 CA。重啟會暫時中斷既有 TAK 連線。

「用戶端憑證 → CA 替換」可選擇要重簽的使用中裝置。預設保留每張憑證的 CN、顯示名稱、In／Out 群組與原到期日；每張可用日曆調整，或選從現在起 7、14、28、90、730 天。效期須在送出後 5 分鐘至 730 天之間，且不能超過新中繼 CA 的期限。未勾選的裝置不取得新 DPK；已過期或單張已撤銷的憑證不可選。兩項獨立確認皆勾選後，控制台才會啟動背景工作。工作會建立本機快照、簽發新中繼 CA 與服務憑證、切換服務、重簽選取裝置、發布舊 CA 的 Root CRL，並移除 TAK 信任憑證鏈資料庫（truststore）對舊 CA 的直接信任。TAK、Mumble 與 MediaMTX 會在切換期間短暫中斷；控制台會顯示工作進度。若顯示失敗或中斷，先檢查本機快照與 CA 狀態，不要直接再按一次。

此背景流程的簽發準備、設定前置檢查與表單驗證已完成；**完整自動切換、Android ATAK 與 Vx 的實機驗收尚未完成**。在完成驗收前，操作人員應保留人工輪替程序作為參照。2026-09-25 的人工切換實測中，只發布 Root CRL 時，8089 仍接受舊憑證 TLS 交握；移除直接信任錨後，ATAK 舊 DPK 才無法重新連線。新 DPK 匯入後，ATAK 與 Vx 四頻道恢復。詳見[CA 輪替驗證紀錄](../validation/2026-09-25-ca-rotation-cutover.md)。

在 TAK 信任憑證鏈資料庫中，舊中繼 CA 若有獨立信任項目，就屬於「直接信任錨」。若仍保留，驗證路徑可能在舊 CA 結束。Root CRL 記錄中繼 CA 的撤銷；中繼 CA 的 CRL 記錄由該 CA 簽發的裝置憑證撤銷資訊。只撤銷單張裝置憑證時，不要刪除整個中繼 CA。這次移除的是 `tak-issuing-old`，Root 與新中繼 CA 均保留。

![只發布 Root CRL 與移除舊 CA 直接信任錨的實測對照](../images/ca-rotation-trust-anchor-comparison.png)

**Vx 邊界：**舊 TAK 裝置憑證失效後，Vx 仍曾以原本的 Mumble 密碼／註冊身分加入頻道。若要停用語音，須到「Mumble 管理」另行踢除工作階段、刪除註冊身分或重設密碼。不要把 TAK 的 CRL 當成 Mumble 帳號停權。

## 瀏覽器驗證範圍

2026-09-25 使用 Chrome／Playwright 在 1440、768、390 px 驗證清冊、搜尋、狀態篩選、卡片／清單切換、詳細頁與群組頁；結果與截圖見[瀏覽器驗證紀錄](../validation/2026-09-25-certificate-browser.md)。此輪只做唯讀互動；簽發、撤銷、群組儲存的後端結果依既有實測紀錄，不把畫面載入等同操作成功。
