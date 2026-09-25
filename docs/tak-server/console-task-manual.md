# TAK 控制台任務操作手冊

本手冊供本機 TAK 5.8 測試環境的管理人員使用。依要完成的任務找入口、執行步驟與驗收結果；控制台頁面名稱及按鈕文字以目前版本為準。管理入口只供 Windows 主機使用，Android 只接收短效 QR 所指向的設定檔或 DPK。

控制台截圖取自 2026-09-25 的本機環境，ICU 章另附實機設定畫面。黃色框標出操作區；裝置名稱、憑證識別資料與註冊身分等資訊已遮蔽。線上數量與分享狀態會隨時間改變。

![TAK 控制台功能與頁面入口](../images/console-page-fishbone.png)

從圖中的五個頁面入口找任務；下表連到各章的操作步驟與驗收項目。

## 先開啟控制台

1. 啟動 Docker Desktop、Windows 熱點與 `takbox.local` 名稱解析，在專案根目錄執行 `docker compose up -d`。需要讓 Android 掃描下載 QR 時，另執行 `docker compose --profile sharing up -d share-public`，並保持分享防火牆的前景視窗開啟。
2. 執行 `.\scripts\Manage-TakControlWorkers.ps1 -Action Status`；憑證或 Mumble 管理程式未執行時，以 `-Action Start` 啟動。首次安裝才使用 `-Action Install`。
3. 在 Windows 瀏覽器開啟 `http://127.0.0.1:10066/`。以 `admin` 和本機 `runtime/secrets/share_admin_password` 登入。若 `.env` 已改 `SHARE_ADMIN_HOST_PORT`，使用實際通訊埠。
4. 先核對頁面 Navbar 可以開啟「檔案分享」、「引導式佈建」、「MediaMTX 管理」、「Mumble 管理」及「用戶端憑證」。需要裝置掃 QR 時，再確認 Android 位於相同熱點、可解析 `takbox.local`。

管理頁使用 `127.0.0.1`，不可將它當成 Android 的下載網址。DPK 含裝置私鑰；ICU 設定含 MediaMTX 發布密碼。分享時設定期限與下載上限，完成後停止分享。詳細的啟動、防火牆及通訊埠調整見[分享服務](../sharing/portal.md)與[憑證控制台](certificate-console.md)。

## 依任務找頁面

| 你要完成的任務 | 控制台入口 | 完成時應看見 |
| --- | --- | --- |
| [交付既有 TAK 裝置憑證](console-task-manual/certificates-and-groups.md#task-01) | 引導式佈建 → TAK Server 連線，或用戶端憑證 → 詳細頁 | 每張憑證有獨立短效 DPK QR；ATAK 連上 `takbox.local:8089:ssl` |
| [新增一台或一批 TAK 裝置](console-task-manual/certificates-and-groups.md#task-02) | 引導式佈建 → 新增 TAK 用戶端 | 每台各有 CN、序號、群組、DPK 與 QR |
| [更改裝置 In／Out 權限](console-task-manual/certificates-and-groups.md#task-03) | 用戶端憑證 → 依群組檢視，或詳細頁 | 儲存後從 TAK API 讀回相同群組 |
| [更新 Vx 四頻道任務](console-task-manual/vx-and-mumble.md#task-04) | 引導式佈建 → Vx 任務 | TAK Server 只剩一筆 `ATAK Local Voice`；裝置下載後能加入四頻道 |
| [交付 ICU 設定](console-task-manual/icu-and-mediamtx.md#task-05) | 引導式佈建 → ICU 影像發布 | ICU 顯示外部設定，並在 MediaMTX 看見預期 `live/.../VIDEO_1` |
| [設定無人機或編碼器](console-task-manual/icu-and-mediamtx.md#task-06) | 引導式佈建 → Advanced → 一般設備 | 個別帳密及 RTSP／RTSPS 發布網址、QR |
| [檢視或關閉影像](console-task-manual/icu-and-mediamtx.md#task-07) | MediaMTX 管理 | 串流清單、即時預覽及公開觀看狀態符合預期 |
| [停用、重新啟用或輪替影像發布身分](console-task-manual/icu-and-mediamtx.md#task-08) | MediaMTX 管理 → ICU／其他 | 小隊或設備身分狀態符合操作結果，舊連線依密碼選項處理 |
| [停止設定檔或 DPK 下載](console-task-manual/sharing-and-troubleshooting.md#task-09) | 檔案分享 → 分享紀錄 | QR 無法再下載；目前有效連結消失 |
| [中斷語音或管理註冊身分](console-task-manual/vx-and-mumble.md#task-10) | Mumble 管理 | 線上連線或註冊清單反映變更 |
| [撤銷 TAK 裝置憑證](console-task-manual/certificates-and-groups.md#task-11) | 用戶端憑證 → 憑證清冊 | CRL 發布、TAK 重啟，舊憑證新連線遭拒 |
| [替換中繼 CA 並選擇重簽裝置](console-task-manual/certificates-and-groups.md#task-ca-replace) | 用戶端憑證 → CA 替換 | 本機輪替及舊鏈拒絕已驗；Android 新 DPK、8443 與 Vx 另驗 |

## 驗收範圍

本手冊以目前實作、既有瀏覽器及 Android 測試紀錄為依據。2026-09-25 在桌機與手機檢查六個管理頁是否載入，並測試憑證頁的搜尋、篩選與群組檢視；該輪沒有重新提交每一種管理操作。已實測的 ATAK、Vx、ICU、MediaMTX 及憑證撤銷結果，見[驗證索引](../validation/README.md)。
