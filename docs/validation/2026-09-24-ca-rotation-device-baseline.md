# 2026-09-24 CA 輪替前實機與群組基線

本紀錄是輪替前的測試。作用中的中繼 CA 尚未切換或撤銷；本次僅重新啟動 Compose、簽發測試用戶端憑證，並驗證群組操作。

## 服務與裝置

- Compose 以 `down`、`up -d --no-build` 重啟，TAK Server、資料庫、Mumble、控制台及分享服務恢復執行。Windows mDNS 重新啟動後，`takbox.local` 回應熱點主機位址，CoT TLS 與 Mumble 服務紀錄可查。
- 原有 bootstrap DPK 重新產生後，由第一台 Android 匯入，使用者確認 ATAK 已連線。分享管理頁對該 DPK 的有效快照顯示 `<CN>-<CRL ID>`；另一筆已停止的舊紀錄因快照不存在，保留原檔名，避免誤標。
- 控制台批次簽發兩張短效憑證：Alpha `100C` 為 7 天、`team-alpha` In + Out；Bravo `100D` 為 14 天、`team-bravo` In + Out。第一次註冊後，TAK API 尚未在 20 秒內就緒，作業顯示部分完成；以相同作業 ID 接續後讀回群組、建立各自 QR，作業完成，沒有重複簽發。
- 使用者確認兩台 Android 分別匯入對應 DPK，且 ATAK 均可連上 `takbox.local:8089:ssl`。舊 TAK 連線設定可能仍留在裝置上，因此尚未將此結果當作「僅使用新憑證」的證明；已另產生短效 QR，等待清除舊連線後重匯入。

### Bravo 重匯入紀錄

Bravo 裝置 於 23:14 掃描同名 DPK 的 QR：下載成功，裝置端檔案 SHA-256 與主機一致，ATAK 判定 Manifest 有效；但紀錄接著顯示 `Overwriting existing file without prompting user`、`already in FileInfo db`，沒有新的套件解壓縮或 `takbox.local` 連線設定。通用 `ImportReceiver` 的 `no Importer found` 訊息本身不足以判定 DPK 損壞。使用者確認畫面只有開始下載，伺服器清單沒有新連線。

將同一份憑證與偏好設定封裝成新檔名並換新的 Manifest UID 後，23:24:18 出現 `ExtractMissionPackageTask`，23:24:19 `takbox.local:8089:ssl` 連線成功，8443 的版本與用戶端端點 API 均回應 200。重試包只用於本機短效分享；未重新簽發憑證。使用者另表示曾移除 `atak/tools/datapackage/` 中的舊 DPK；這與檔名、Manifest UID 同時變動，因此不能單獨證明 ATAK 是依哪一項判斷重複，也不能排除刪檔促成重新匯入。原始紀錄只足以證明同名下載曾停留在檔案覆寫階段，重試則確實完成套件安裝。

## 群組觀察與限制

TAK 5.8 管理 API 對兩張新憑證分別回應 `team-alpha`、`team-bravo`，沒有 `__ANON__`。本機 `UserAuthenticationFile.xml` 的 `__ANON__` 只列在管理員身分。TAK Server SDK 的 `README.md`「Message Groups and Addresses」將 `__ANON__` 說明為 plugin 訊息未指定群組時使用的特殊群組；不應把它直接解讀成這兩張用戶端憑證共用的群組。首次同一 Wi-Fi 網段測試中，兩台互相看得到標記；同網段 ATAK 本機 CoT 傳播及舊連線設定都可能影響此結果，**不能據此宣稱 TAK Server 群組隔離失效或成功**。需清除舊連線後，在接收端暫停 TAK Server 連線但維持 Wi-Fi，再送新標記確認是否存在本機傳播；之後以排除本機傳播的網路路徑重測群組路由。

23:34 曾在 Alpha 地圖建立測試 point，Bravo 保持同一 Wi-Fi、關閉 TAK 連線時看不到。使用者指出 point 必須執行「分享／傳送」才會送出；此次尚未分享，因此**離線看不到不能作為本機傳播或群組隔離的證據**。下一輪須記錄實際分享目的地，並使用全新名稱的 point 測試。

Bravo 重新連線後，使用者在 Contacts 的 Group 檢視中無法互相看到對方；改從相同 Teams 檢視則可以傳送。Alpha 於 23:39:47 的 ATAK 紀錄明確顯示 `Sending CoT to contact ... using tcp endpoint <peer-hotspot-IP>:4242`，即同熱點的裝置對裝置 TCP 傳送。此成功傳送繞過 TAK Server 群組路由，不能據此宣稱跨群組的伺服器路由成功或隔離失敗。隨後改以明確指向 `takbox.local:8089` 的 CoT 測試伺服器群組分流。

### TAK Server 群組分流實測

兩台 ATAK 均連線 `takbox.local:8089:ssl`，並保持不同的 `team-alpha`／`team-bravo` In + Out 群組。測試程式使用各自既有的測試憑證，以驗證伺服器名稱的 TLS 連線直接向 Windows 熱點位址的 `8089` 送入唯一 UID 的 CoT；沒有使用 ATAK Contacts 的點對點傳送。

| 發送身分 | Alpha ATAK | Bravo ATAK | 裝置紀錄 |
| --- | --- | --- | --- |
| Alpha 憑證 `100C` | 有 | 無 | Alpha `ContactStore` 於 23:42:28 加入該 UID；Bravo 未記錄該 UID，使用者畫面確認。 |
| Bravo 憑證 `100D` | 無 | 有 | Bravo `ContactStore` 於 23:43:54 加入該 UID；Alpha 未記錄該 UID，使用者畫面確認。 |

這證明**本次兩個已註冊群組的伺服器媒介 CoT 分流**符合預期。測試事件短時間後由 ATAK 標記 stale；驗收依收到當下的紀錄與使用者畫面判定。相同 Teams 的本機 TCP 4242 直連仍可越過 TAK Server 的群組分流，因此同網段部署若要求全面隔離，還須處理裝置間連線或網路隔離；不能只靠 TAK In／Out 群組。

## 群組移除

先以非實機測試憑證直接呼叫 TAK 管理 API，清空其 In／Out 群組，再恢復原 `local-test` In + Out，兩次讀回均吻合。控制台隨後加入「從此群組移除」按鈕及「未記錄群組」拖放目標；對同一張測試憑證，實際在瀏覽器暫存移除、確認儲存、從 TAK API 讀回空群組，再透過控制台加回 `local-test` 並讀回確認。Alpha、Bravo 的群組在此測試中未更動。新增簽發仍需至少指定一個群組；已註冊憑證允許移除最後一個群組。

原始 QR 與畫面截圖保存在 Git 忽略的 `runtime/validation/ca-rotation/`，含可用連結或裝置資訊，不直接加入公開文件。後續仍需分別驗收 ATAK、Vx 與撤銷後重新登入。
