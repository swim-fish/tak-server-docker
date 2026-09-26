# MediaMTX 管理與 WebRTC 預覽

Windows 本機控制台把 MediaMTX 管理分為「ICU」(`http://127.0.0.1:10066/media`) 與「其他」(`http://127.0.0.1:10066/media/other`) 兩個子頁。兩頁共用線上 `live/` 串流、即時預覽及公開觀看開關；ICU 身分以卡片呈現，一般設備身分以表格呈現。頁面使用控制台既有的 Basic 驗證；MediaMTX Control API 只在 Compose 網路內開放。

![ICU 小隊卡片](../images/console-media-icu-cards.png)

![其他設備表格](../images/console-media-other-table.png)

## 即時影像

「目前發布的串流」以卡片顯示路徑、影像軌道與小型即時畫面；縮圖只在進入畫面附近時建立預覽連線，移出畫面後卸載。點「放大預覽」會在控制台內開啟同一串流，按「關閉預覽」會卸載放大播放器。公開觀看連結指向 `http://takbox.local:8889/live/<path>/`；路徑結尾的 `/` 是必要的，否則 MediaMTX 的頁面可能把最後一段路徑當成檔名。管理頁每 3 秒更新公開觀看工作階段數量，不會重整選取中的表單。

公開觀看預設開啟。控制台總開關關閉後，公開入口拒絕新的觀看請求，並透過內部 API 中斷既有公開 WebRTC 工作階段；管理頁預覽與 ICU 發布維持獨立。預覽由控制台代為向 `media-preview` 驗證，瀏覽器不需要連到 `127.0.0.1:8890` 或輸入第二組帳密。

若管理頁預覽收到 HTTP 401，先確認 `runtime/mediamtx/viewer-preview.yml` 的管理帳密是否仍與 `runtime/secrets/share_admin_password` 同步。這台本機環境可執行 `python scripts/provision_mediamtx.py --dns takbox.local` 重新產生設定，再執行 `docker compose up -d --force-recreate --no-deps media-preview` 載入新設定。請勿把密碼或產生的設定檔提交至 Git。

目前 `takbox.local` 與 `.env` 的 `TAK_BIND_IP` 只預期在同一個本機網路可達。**尚未開放網際網路觀看**；公開 FQDN、HTTPS 憑證、Router NAT、防火牆及 ICE 外部可達性仍須另行設定與實測。匿名觀看的 `live/` 路徑可預測，對外開放前應確認影像內容可以公開。

## 小隊 ICU QR

### 批次交付隊員 QR 與 TAK 影像別名

在「引導式佈建 → ICU 小隊批次交付」選擇小隊、起始隊員及人數（1–10），再選一個或多個 TAK 影像別名可見群組。頁面預設勾選該小隊對應的 `team-<小隊>`；`team-all` 是全體共用的具名群組，選用時仍須確認接收裝置憑證具有 `team-all` Out。預覽會列出每個完整路徑、所選群組，以及目前符合 Out 群組的有效憑證。確認後執行，結果頁可左右切換每位隊員的 ICU QR；分享紀錄開啟同小隊任一筆仍有效的 ICU QR 時，也能在彈窗切換同小隊的其他 QR。

每位隊員各有獨立的分享 token、期限與下載上限。ICU 掃描後取得同一小隊的發布帳密，但路徑不同，例如 `live/alpha/2/` 與 `live/alpha/3/`；ICU 會自行附加 `VIDEO_1`。TAK Video Alias 以固定 UID 發布，ATAK 的影像清單只向具所選群組 Out 權限的裝置顯示。重新執行相同隊員與群組會更新既有別名；更換群組時會短暫刪除並重建該別名，結果頁會顯示每位隊員的發布狀態。執行失敗可從同一結果頁接續，不必重新建立整批。

影像別名包含 MediaMTX 觀看帳密。**TAK 群組控制別名清單可見性，不會撤回已取得的播放網址或帳密**；停止 QR 分享也只會停止設定檔下載。需要停止既有觀看時，須另行輪替或停用觀看身分。新別名的群組可見性與播放仍須在 ATAK 實機驗證；目前已完成本機雙人批次及 API 唯一性檢查，詳見[執行計畫與待驗項目](../plans/icu-batch-video-alias.md)。

引導式佈建位於 `/provision`。「ICU 小隊發布」可選 Alpha 至 Hotel 小隊與 1–10 號隊員，預設全選；可單選、多選或用「全選隊員／全部不選」調整。每名隊員各有獨立的限時 QR，結果頁以 Carousel 切換；此流程只建立 ICU 發布設定，不建立 TAK Video Alias。需要同時建立群組可見的別名時，改用上節的「ICU 小隊批次交付」。Advanced ICU 模式可自訂單一個以 `live/` 開頭、`/` 結尾的 Stream Path；具名小隊的 Advanced 路徑必須保留自己的 `live/<小隊>/` 前綴。ICU 會在設定路徑後附加 `VIDEO_1`。每個小隊共用一組發布帳密；MediaMTX 只允許該帳密發布其小隊前綴下、以 `/VIDEO_1` 結尾的路徑，例如 Alpha 可用 `live/alpha/1/VIDEO_1` 或 `live/alpha/2/VIDEO_1`，不可發布 `live/bravo/2/VIDEO_1`。一般設備也不能占用小隊前綴。

同隊裝置可匯入**同一張尚未到期且未達下載上限的 QR**，再於 ICU 將 Stream Path 的小隊後段改為各自的識別值，例如從 `live/alpha/1/` 改成 `live/alpha/2/`；帳號、密碼、主機及通訊埠都不用更動。若 QR 已達下載限制，先在 ICU 子頁再次發布同隊 QR。兩台裝置不可同時使用相同的**完整**路徑，否則會互相搶占發布工作階段。Alpha／2 已由 Android ICU 實機改值、MediaMTX RTSPS 發布紀錄與控制台線上路徑確認；詳見[驗證紀錄](../validation/2026-09-25-icu-squad-path-scope.md)。

在 `/media` 勾選一個或多個**啟用中的 ICU 小隊**，展開各小隊的「QR 路徑」選擇要再次發布的路徑。路徑預設全部勾選；工具列的「全選／全部不選」只作用於目前選取的小隊，亦可逐條取消勾選。至少保留一條路徑，再設定 QR 分享時間與下載上限，按「再次發布 ICU QR」。此操作沿用現有小隊密碼，不停止原有 QR，也不踢除目前串流；每條選取的路徑會有獨立的限時、限次 QR。若要讓舊設定失效，使用「重設選取密碼」。結果頁有獨立網址；重新整理不會再次建立 QR 或重設密碼。分享紀錄的 QR 彈窗會將設定名稱放在 QR 上方，標題列以徽章顯示目前下載次數與上限，切換同小隊 QR 時會同步更新。作業異常時會顯示已完成項目，避免在未檢查狀態前重複執行。

QR 指向 `icu://download?url=...`，下載的 `initial.prefs` 含發布密碼。Android 必須連上 `.env` 所設定的允許網段、解析 `takbox.local` 並點開掃碼器顯示的**完整** `icu://` 連結。單憑「Externally configured」提示不足以判定影像已發布，仍應檢查 ICU 欄位及 MediaMTX 在線路徑。詳見 [ICU QR Code](icu-qrcode.md)。

## 一般設備與權限

Advanced → 一般設備可指定設備名稱及完整 `live/` 路徑，建立獨立的發布身分。路徑欄使用 RTSPS URL input group，前綴固定顯示 `rtsps://takbox.local:8322/`，輸入欄只填 Stream Path，並即時預覽完整發布 URL；正式建立後才產生設備專屬帳密。結果頁的 RTSP、RTSPS 網址與 QR 分開顯示；按「顯示連線資訊」才揭露內含帳密的網址，並可用各自的「複製網址」按鈕。一般設備 QR 不受 ICU 分享的時間／下載次數限制；停用身分或重設密碼才會讓舊網址失效。網址只在控制台與 QR 內顯示，不應貼入日誌或提交至 Git。RTSP 通訊埠為 `8554`，RTSPS 為 `8322`；RTSPS 裝置須信任 TAK CA 鏈與 `takbox.local` 伺服器名稱。

兩個子頁都有「啟用中／停用／顯示全部」篩選；切換時會取消隱藏項目的勾選。「其他」另提供名稱／帳號／路徑搜尋、每頁 10／20／30 筆及分頁。選取本頁只勾選目前顯示的設備。「停用選取身分」會拒絕新發布並嘗試中斷該帳號現有 RTSP 工作階段；「重設選取密碼」會輪替帳密，停止舊 QR，為小隊各路徑建立新 ICU QR。一般設備可重新顯示新發布網址與 QR。

在「其他」切換到「停用」，按設備列的「重新啟用」可開啟確認對話框。選「沿用舊密碼」會恢復原發布網址；選「產生新密碼」會讓原網址失效，須在結果頁取得新網址或 QR。兩種方式都保留設備帳號與 Stream Path；重新啟用會先檢查該路徑沒有被其他身分占用。2026-09-25 使用已停用的模擬無人機身分，實測沿用舊密碼後 RTSP 推流成功，隨後再次停用並確認原帳密推流被拒。產生新密碼的分支已通過程式測試，尚未以實際設備推流驗證。

![其他設備重新啟用對話框](../images/console-media-reactivate-dialog.png)

舊的 `atak-publisher` 共用帳號暫時保留供既有 ICU 遷移；改用小隊 QR 的裝置應逐步移轉，再決定停用舊帳號。

Android ICU 的 `live/alpha/1/VIDEO_1` RTSPS 串流已在 Chrome 中驗證 WebRTC 影像；MediaMTX 在獨立 viewer 內把 ICU 的 MPEG-TS 拆出 H.264 與 KLV。[2026-09-25 一般設備實測](../validation/2026-09-25-drone-synthetic-stream.md)另以 FFmpeg 模擬無人機，確認控制台產生的 RTSP／RTSPS 網址與 QR、RTSPS 憑證鏈、兩種協定的 TCP 發布與獨立讀取、WebRTC 預覽及停用後拒絕舊網址。尚待驗收實體無人機、音訊、Firefox、Android 瀏覽器、同隊多裝置同步發布與跨網段 UDP。
