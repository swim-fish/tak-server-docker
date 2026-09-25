# TAK 控制台任務操作手冊

本手冊供本機 TAK 5.8 測試環境的管理人員使用。依要完成的任務找入口、執行步驟與驗收結果；控制台頁面名稱及按鈕文字以目前版本為準。管理入口只供 Windows 主機使用，Android 只接收短效 QR 所指向的設定檔或 DPK。

以下操作截圖取自 2026-09-25 的本機控制台，另有一張影像流向圖。黃色框標示相關操作區；裝置名稱、憑證識別資料與註冊身分等資訊已遮蔽。畫面中的線上數量與分享狀態會隨時間改變。

![TAK 控制台功能與頁面入口](../images/console-page-fishbone.png)

## 先開啟控制台

1. 啟動 Docker Desktop、Windows 熱點與 `takbox.local` 名稱解析，在專案根目錄執行 `docker compose up -d`。需要讓 Android 掃描下載 QR 時，另執行 `docker compose --profile sharing up -d share-public`，並保持分享防火牆的前景視窗開啟。
2. 執行 `.\scripts\Manage-TakControlWorkers.ps1 -Action Status`；憑證或 Mumble 管理程式未執行時，以 `-Action Start` 啟動。首次安裝才使用 `-Action Install`。
3. 在 Windows 瀏覽器開啟 `http://127.0.0.1:10066/`。以 `admin` 和本機 `runtime/secrets/share_admin_password` 登入。若 `.env` 已改 `SHARE_ADMIN_HOST_PORT`，使用實際通訊埠。
4. 先核對頁面 Navbar 可以開啟「檔案分享」、「引導式佈建」、「MediaMTX 管理」、「Mumble 管理」及「用戶端憑證」。需要裝置掃 QR 時，再確認 Android 位於相同熱點、可解析 `takbox.local`。

管理頁使用 `127.0.0.1`，不可將它當成 Android 的下載網址。DPK 含裝置私鑰；ICU 設定含 MediaMTX 發布密碼。分享時設定期限與下載上限，完成後停止分享。詳細的啟動、防火牆及通訊埠調整見[分享服務](../sharing/portal.md)與[憑證控制台](certificate-console.md)。

## 依任務找頁面

| 你要完成的任務 | 控制台入口 | 完成時應看見 |
| --- | --- | --- |
| 交付既有 TAK 裝置憑證 | 引導式佈建 → TAK Server 連線，或用戶端憑證 → 詳細頁 | 每張憑證有獨立短效 DPK QR；ATAK 連上 `takbox.local:8089:ssl` |
| 新增一台或一批 TAK 裝置 | 引導式佈建 → 新增 TAK 用戶端 | 每台各有 CN、序號、群組、DPK 與 QR |
| 更改裝置 In／Out 權限 | 用戶端憑證 → 依群組檢視，或詳細頁 | 儲存後從 TAK API 讀回相同群組 |
| 更新 Vx 四頻道任務 | 引導式佈建 → Vx 任務 | TAK Server 只剩一筆 `ATAK Local Voice`；裝置下載後能加入四頻道 |
| 交付 ICU 設定 | 引導式佈建 → ICU 影像發布 | ICU 顯示外部設定，並在 MediaMTX 看見預期 `live/.../VIDEO_1` |
| 設定無人機或編碼器 | 引導式佈建 → Advanced → 一般設備 | 個別帳密及 RTSP／RTSPS 發布網址、QR |
| 檢視或關閉影像 | MediaMTX 管理 | 串流清單、即時預覽及公開觀看狀態符合預期 |
| 停用影像發布身分 | MediaMTX 管理 → 發布身分 | 所選身分停用或密碼更新，舊連線受影響 |
| 停止設定檔或 DPK 下載 | 檔案分享 → 分享紀錄 | QR 無法再下載；目前有效連結消失 |
| 中斷語音或管理註冊身分 | Mumble 管理 | 線上連線或註冊清單反映變更 |
| 撤銷 TAK 裝置憑證 | 用戶端憑證 → 憑證清冊 | CRL 發布、TAK 重啟，舊憑證新連線遭拒 |

## 任務一　交付既有 TAK 裝置憑證

1. 在「引導式佈建 → TAK Server 連線」選擇有效且已註冊的憑證，核對 CN、CRL ID 與到期日。每台裝置使用自己的 DPK。
2. 設定分享期限與下載上限，按「預覽」後建立 QR。讓指定 Android 掃完整 `tak://` 連結並在 ATAK 確認匯入。
3. 確認 ATAK 已連上 `takbox.local:8089:ssl`；分享紀錄應顯示 `<CN>-<CRL ID>`。

同名舊 DPK 若阻止更新，先清除裝置上的舊下載副本。匯入提示或下載通知不能代替連線驗收。

![交付頁選取憑證與分享限制](../images/console-task-01-existing-tak.png)

圖 1：選擇憑證，設定 QR 分享時間與下載上限。

![憑證清冊篩選與識別欄位](../images/console-task-01b-inventory.png)

圖 2：回清冊用 CN 或 CRL ID 核對身分；識別資料已遮蔽。

## 任務二　新增 TAK 裝置並指定群組

1. 在「引導式佈建 → 新增 TAK 用戶端」為每台填顯示名稱與唯一 ASCII CN。到期日可用日曆，或選 1 小時、1 天、7 天、14 天、28 天、90 天。
2. 將群組移到 In／寫入、Out／讀取或 In + Out／讀寫；至少指定一種權限。批次可建 1 至 10 台，各有獨立私鑰與 DPK。
3. 按「預覽批次」核對 CN、效期、群組及 QR 限制，再確認簽發。結果頁逐台檢查註冊、序號與 QR；TAK 會重啟一次。

部分完成時先查既有結果，再以相同作業 ID 接續，避免重複簽發。同頁的 QR 下載期限和憑證效期是兩項設定。

![新增裝置與效期欄位](../images/console-task-02-new-tak.png)

圖 3：逐台填 CN 與到期時間，再設定群組。

![四欄式群組清單](../images/console-task-02b-group-lanes.png)

圖 4：未指派群組不授權讀寫；移到 In、Out 或 In + Out 才生效。

## 任務三　調整裝置的資料讀寫範圍

1. 開啟「用戶端憑證 → 依群組檢視」，預設篩選「使用中」。可拖曳憑證、按「移動」，或在群組中按「新增憑證」。
2. 選擇 In、Out 或 In + Out。要移除權限，可按「從此群組移除」或拖到「未記錄群組」。
3. 核對待儲存變更並確認儲存；待儲存數歸零後，從 TAK API 讀回群組。調整既有群組不必重做 DPK。

驗證隔離時，要經 TAK Server 傳送新的 CoT；同一 Wi-Fi 的本機廣播無法證明群組規則。[雙裝置實測](../validation/2026-09-24-ca-rotation-device-baseline.md)記錄 Alpha／Bravo 的結果。

![依群組檢視憑證](../images/console-task-03-groups.png)

圖 5：狀態篩選、各群組權限及「儲存群組變更」。

![新增憑證到群組視窗](../images/console-task-03b-add-group.png)

圖 6：搜尋尚未加入的使用中憑證，選擇加入權限；憑證識別資料已遮蔽。

## 任務四　更新 Vx 四頻道任務

1. 在「引導式佈建 → Vx 任務佈建」產生套件並預覽，核對 SHA-256 與同名套件筆數。
2. 確認後執行「備份並強制替換」；結果須只剩一筆 `ATAK Local Voice`。
3. ATAK 從 TAK Server 的 Data Packages → Download 取得套件，再到 TAK Voice 逐一加入 Primary、Alternate、Medical、Emergency。

Vx-only DPK 的一般下載 QR 無法直接建立 Mission。若誤用 `Clear Database`，任務會被移除，須重新下載；替換失敗時使用作業備份復原。

![Vx 套件佈建入口](../images/console-task-04-vx.png)

圖 7：產生套件後先預覽，再確認替換固定名稱的伺服器套件。

![ATAK Vx 四頻道清單](../images/atak-vx-four-channel-pool.jpg)

圖 8：裝置下載後，TAK Voice 應顯示四個可加入的頻道。

## 任務五　替人員建立 ICU 影像發布 QR

1. 在「引導式佈建 → ICU 影像發布」選 Alpha 至 Hotel 小隊及 1–10 人員代號；兩者留空則用 `live/`。
2. 自訂時選 Advanced，只填以 `live/` 開頭、以 `/` 結尾的 Stream Path。ICU 會在末端加上 `VIDEO_1`。
3. 設定 QR 時間與下載上限，預覽後交付完整 `icu://download?url=...`。ICU 應顯示外部設定、RTSP-Push、`takbox.local:8322` 與 SSL；啟動後再查 MediaMTX 線上路徑。

同一小隊共用發布密碼。QR 下載的 `initial.prefs` 含密碼；只看到匯入提示尚未證明影像已發布。

![ICU 標準模式選項](../images/console-task-05-icu.png)

圖 9：依小隊與人員代號產生標準路徑及短效 QR。

![ICU Advanced 路徑預覽](../images/console-task-05b-advanced-path.png)

圖 10：Advanced 只改 Stream Path；預覽會顯示 ICU 自動附加的 `VIDEO_1`。

## 任務六　讓一般設備發布影像

1. 在「引導式佈建 → Advanced → 一般設備」填設備名稱與唯一的 `live/` 完整路徑；URL input group 會顯示 RTSPS 預覽。
2. 預覽後建立設備身分。結果頁可個別複製 RTSP／RTSPS 網址或顯示 QR；每台設備有獨立帳密與指定路徑。
3. 優先用 RTSPS 發布並驗證 TAK CA 鏈與 `takbox.local`；只有 RTSP 的設備可在受控熱點使用 `8554`。最後確認 MediaMTX 出現路徑。

發布網址可能含帳密，不要貼進截圖、日誌或 Git。一般設備不會自動附加 `VIDEO_1`。

![一般設備 URL input group](../images/console-task-06-device.png)

圖 11：先核對設備名稱與完整 Stream Path。

![一般設備發布預覽頁](../images/console-task-06b-preview.png)

圖 12：預覽確認路徑及 TLS 條件；截圖未建立帳號。

## 任務七　檢視影像與控制觀看

1. 在「MediaMTX 管理」選線上串流，按「即時預覽」；看完按「關閉預覽」。
2. 熱點裝置使用 `http://takbox.local:8889/live/<path>/` 觀看，末尾斜線需保留。
3. 以「公開 WebRTC 觀看」開關控制新觀看與現有公開工作階段；此開關不停止 ICU 推流。

目前只驗證熱點觀看；網際網路仍需 FQDN、HTTPS、NAT 與 ICE 驗收。截圖時沒有線上串流。

![WebRTC 觀看狀態控制](../images/console-task-07-viewer.png)

圖 13：管理頁顯示公開觀看開關、工作階段數與串流清單。

![MediaMTX 推流與觀看流向](../images/console-task-07b-viewing-flow.png)

圖 14：推流與觀看分屬不同路徑；控制台預覽僅供 Windows 本機使用。

## 任務八　停用或輪替 MediaMTX 發布身分

1. 在「MediaMTX 管理 → 發布身分」搜尋並勾選小隊或設備，可用啟用狀態篩選。
2. 按目的選「再次發布 ICU QR」、「停用選取身分」或「重設選取密碼」，勾選頁面確認後送出。
3. 重設小隊密碼後，整個小隊須重新掃 QR；一般設備則重新取得專屬發布網址。核對原發布連線已中斷。

再次發布 QR 不會更改原密碼。小隊共用帳密；要單獨停用一台設備，應使用一般設備身分。

![MediaMTX 發布身分清單](../images/console-task-08-publishers.png)

圖 15：搜尋與篩選發布身分。

![選取身分後的管理按鈕](../images/console-task-08b-selected-publisher.png)

圖 16：選取後才可再次發布、停用或重設；截圖未送出變更。

## 任務九　檢視與停止設定檔分享

1. 在「檔案分享」看頁首總開關及「分享中」連結；分享紀錄可切換每頁 10、20、30 筆與狀態篩選。
2. 要停止單筆，按「停止分享」；全部暫停則用總開關。分享中會顯示剩餘時間與下載次數。
3. 確認舊 QR 無法再下載。已下載到裝置的 DPK 或 `initial.prefs` 不會自動消失，身分停用須另行處理。

時間與次數可同時限制，先達到者即停止新下載；開啟 QR 本身不占下載次數。

![分享紀錄狀態篩選](../images/console-task-09-shares.png)

圖 17：每頁筆數、狀態與下載用量；截圖顯示已結束的紀錄。

![分享下載總開關](../images/console-task-09b-master-switch.png)

圖 18：總開關影響所有分享；停止單筆時請到該筆紀錄操作。

## 任務十　管理 Vx 語音登入

1. 在「Mumble 管理 → 線上連線」選 session 並按「中斷選取的連線」；該身分仍可再次登入。
2. 要移除已記住的身分，到「已註冊身分」勾選並確認刪除。系統會先備份資料庫；有效共用密碼仍可讓使用者重新註冊。
3. 「重新啟動 Mumble」保留頻道與註冊資料；「重設共用密碼並重新啟動」會改本機 secret。兩者都會中斷線上連線。

驗收線上／註冊清單及 Vx 重登。TAK 憑證撤銷不等於 Mumble 停用；已註冊 Vx 身分在改密碼後仍可能直接登入。

![Mumble 線上與註冊清單](../images/console-task-10-mumble.png)

圖 19：線上 session 和已註冊身分分開管理；截圖時沒有線上連線。

![Mumble 伺服器控制](../images/console-task-10b-server-controls.png)

圖 20：重新啟動與重設密碼是不同操作，皆會中斷連線。

## 任務十一　撤銷 TAK 裝置憑證

1. 在「用戶端憑證 → 憑證清冊」核對 CN、簽發 CA、CRL ID 與 SHA-256 指紋；不可只靠可能重複的名稱。
2. 選取有效憑證，按「撤銷選取的憑證」，再於確認視窗勾選。撤銷不可復原；控制台會停止關聯 QR、更新 CRL 並重啟 TAK。
3. 檢查 CRL 含該序號，並用舊 DPK 重新連線驗證 8089 拒絕；Android 可能只顯示 `IO Error`。

若 CRL 發布或重啟失敗，可「重新發布 CRL 並重啟」，但憑證仍維持撤銷。8443 須另測。中繼 CA 輪替目前須執行人工腳本，並檢查 TAK 信任憑證鏈資料庫（truststore）是否仍直接信任舊 CA；詳見[憑證使用手冊](certificate-operator-guide.md)。

![憑證清冊選取狀態](../images/console-task-11b-selected-certificate.png)

圖 21：先選憑證並核對識別欄位；識別資料已遮蔽。

![撤銷憑證確認視窗](../images/console-task-11-revoke.png)

圖 22：再次確認影響範圍；截圖停在確認視窗，沒有送出撤銷。

## 操作後核對與疑難排解

| 現象 | 先核對 | 下一步 |
| --- | --- | --- |
| 管理頁顯示 worker 無法取得資料 | Windows 已登入；`Manage-TakControlWorkers.ps1 -Action Status` | 用 `-Action Start` 啟動；再查 `runtime/tak-cert-control/worker.log` 或 `runtime/share-control/worker.log` |
| Android 掃 QR 只顯示下載通知 | 同熱點、mDNS、分享期限／次數、完整 `tak://` 或 `icu://` 連結 | 到 ATAK／ICU 核對真正匯入結果；同名 DPK 可先清除舊副本 |
| ATAK 已連線但看不到 Vx 套件 | Data Packages → Download 選對 TAK Server；8443 可達 | 查 TAK 套件是否只剩一筆、`tool=public` 與 `missionpackage`；不要改走一般 Vx QR |
| ICU 顯示外部設定但沒有影像 | Type、SSL、`takbox.local:8322`、Stream Path 和小隊帳密 | 啟動發布後查 MediaMTX 線上路徑；避免兩台使用相同 `VIDEO_1` 路徑 |
| Vx 不再提示密碼但仍可登入 | 已註冊 Mumble 身分可能仍有效 | 到 Mumble 管理頁移除註冊身分，再用未註冊裝置驗證新密碼 |
| 公開影像在外網打不開 | 目前只有熱點入口 | 待 FQDN、HTTPS、NAT、ICE 與防火牆完成後另做外網驗收 |

**驗收界線：**本手冊以目前實作、既有瀏覽器及 Android 測試紀錄為依據。2026-09-25 在桌機與手機檢查六個管理頁是否載入，並測試憑證頁的搜尋、篩選與群組檢視；該輪沒有重新提交每一種管理操作。已實測的 ATAK、Vx、ICU、MediaMTX 及憑證撤銷結果，見[驗證索引](../validation/README.md)。
