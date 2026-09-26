# TAK 裝置憑證與群組

[返回任務索引](../console-task-manual.md)

<a id="task-01"></a>

## 任務一　交付既有 TAK 裝置憑證

1. 在「引導式佈建 → TAK Server 連線」選擇有效且已註冊的憑證，核對 CN、CRL ID 與到期日。每台裝置使用自己的 DPK。
2. 設定分享期限與下載上限，按「預覽」後建立 QR。讓指定 Android 掃完整 `tak://` 連結並在 ATAK 確認匯入。
3. 確認 ATAK 已連上 `takbox.local:8089:ssl`；分享紀錄應顯示 `<CN>-<CRL ID>`。

同名舊 DPK 若阻止更新，先清除裝置上的舊下載副本。匯入提示或下載通知不能代替連線驗收。

![交付頁選取憑證與分享限制](../../images/console-task-01-existing-tak.png)

圖 1：選擇憑證，設定 QR 分享時間與下載上限。

![憑證清冊篩選與識別欄位](../../images/console-task-01b-inventory.png)

圖 2：回清冊用 CN 或 CRL ID 核對身分；識別資料已遮蔽。

<a id="task-02"></a>

## 任務二　新增 TAK 裝置並指定群組

1. 在「引導式佈建 → 新增 TAK 用戶端」為每台填顯示名稱與唯一 ASCII CN。到期日可用日曆，或選 1 小時、1 天、7 天、14 天、28 天、90 天。
2. 將群組移到 In／寫入、Out／讀取或 In + Out／讀寫；至少指定一種權限。批次可建 1 至 10 台，各有獨立私鑰與 DPK。
3. 按「預覽批次」核對 CN、效期、群組及 QR 限制，再確認簽發。結果頁逐台檢查註冊、序號與 QR；TAK 會重啟一次。

部分完成時先查既有結果，再以相同作業 ID 接續，避免重複簽發。同頁的 QR 下載期限和憑證效期是兩項設定。

![新增裝置與效期欄位](../../images/console-task-02-new-tak.png)

圖 3：逐台填 CN 與到期時間，再設定群組。

![四欄式群組清單](../../images/console-task-02b-group-lanes.png)

圖 4：未指派群組不授權讀寫；移到 In、Out 或 In + Out 才生效。

<a id="task-03"></a>

## 任務三　調整裝置的資料讀寫範圍

1. 開啟「用戶端憑證 → 依群組檢視」，預設篩選「使用中」。可勾選「隱藏空群組」縮短頁面；新增憑證時先取消勾選，才可拖到原本隱藏的空群組。
2. 可拖曳憑證，或按項目右側的「移動」開啟對話框。選「移動／調整權限」後指定目的群組與 In、Out 或 In + Out；選「從此群組移除」則只移除來源群組。也可拖到「未記錄群組」。
3. 核對待儲存變更並確認儲存；待儲存數歸零後，從 TAK API 讀回群組。調整既有群組不必重做 DPK。

驗證隔離時，要經 TAK Server 傳送新的 CoT；同一 Wi-Fi 的本機廣播無法證明群組規則。[雙裝置實測](../../validation/2026-09-24-ca-rotation-device-baseline.md)記錄 Alpha／Bravo 的結果。

![依群組檢視憑證](../../images/console-task-03-groups.png)

圖 5：目前的狀態篩選、隱藏空群組、三欄權限與單一「移動」按鈕。

![移動憑證並調整 In Out 權限的對話框](../../images/console-task-03-move-dialog.png)

圖 5a：「移動／調整權限」可選目的群組與權限；按「暫存移動」後仍須儲存群組變更。

![從目前群組移除憑證的對話框](../../images/console-task-03-remove-dialog.png)

圖 5b：切換「從此群組移除」後，只移除來源群組；圖中未送出變更。

![新增憑證到群組視窗](../../images/console-task-03b-add-group.png)

圖 6：搜尋尚未加入的使用中憑證，選擇加入權限；憑證識別資料已遮蔽。

<a id="task-11"></a>

## 任務十一　撤銷 TAK 裝置憑證

1. 在「用戶端憑證 → 憑證清冊」核對 CN、簽發 CA、CRL ID 與 SHA-256 指紋；不可只靠可能重複的名稱。
2. 選取有效憑證，按「撤銷選取的憑證」，再於確認視窗勾選。撤銷不可復原；控制台會停止關聯 QR、更新 CRL 並重啟 TAK。
3. 檢查 CRL 含該序號，並用舊 DPK 重新連線驗證 8089 拒絕；Android 可能只顯示 `IO Error`。

一般撤銷流程會自動更新 CRL 並重啟 TAK Server；若撤銷紀錄已寫入，但發布或重啟失敗，可選「重新發布 CRL 並重啟」。它會依目前 CA 資料庫重新產生 Root CA 與簽發中繼 CA 的 CRL，不會新增或還原撤銷紀錄，也不會撤銷中繼 CA。8443 須另測。中繼 CA 替換使用獨立子頁，並須檢查 TAK 信任憑證鏈資料庫（truststore）是否仍直接信任舊 CA；詳見[憑證使用手冊](../certificate-operator-guide.md)。

![憑證清冊選取狀態](../../images/console-task-11b-selected-certificate.png)

圖 21：先選憑證並核對識別欄位；識別資料已遮蔽。

![撤銷憑證確認視窗](../../images/console-task-11-revoke.png)

圖 22：再次確認影響範圍；截圖停在確認視窗，沒有送出撤銷。

<a id="task-ca-replace"></a>

## 任務十二　替換簽發中繼 CA 並重簽裝置

1. 到「用戶端憑證 → CA 替換」，核對目前 CA ID。先確認控制台與 Windows 憑證管理程式正常，並安排 TAK、Mumble、MediaMTX 的短暫中斷。
2. 勾選要重簽的使用中憑證。原到期日會自動帶入，可為每張憑證個別使用日曆調整，或選從現在起 7、14、28、90、730 天。未勾選的舊憑證會隨舊 CA 撤銷而失效，但不會產生新 DPK。
3. 核對 CN、群組與新到期日，開啟確認視窗並勾選兩項獨立確認後送出。TAK、Mumble 與 MediaMTX 會短暫中斷；同頁可檢視背景工作的階段與結果。
4. 到清冊確認舊憑證標示「簽發 CA 已撤銷」，逐一交付新 DPK。分別測試 ATAK 的 8089／8443 與 Vx 四頻道；Mumble 原有帳號另行管理。

8443 的受控測試已確認：實際載入 Root CRL 時，舊 CA 憑證的新連線會遭拒。現行設定已還原為只直接載入第一筆 CRL；每次 CA 替換後仍須以舊憑證重連 8443 確認遭拒，並以新憑證確認仍可使用。見[8443 測試紀錄](../../validation/2026-09-26-ca-rotation-8443-retest.md)。

![CA 替換頁的重簽選取與個別到期時間欄位](../../images/console-ca-rotation-1440.png)

圖 23：替換會使舊憑證失效，頁面以紅色警告標示；為選取的裝置指定新到期時間。識別資料已遮蔽。

![手機寬度的 CA 替換頁](../../images/console-ca-rotation-390.png)

圖 24：窄螢幕依序呈現高風險紅色警告、裝置卡片與操作按鈕；識別資料已遮蔽。

![CA 替換的雙重確認視窗](../../images/console-ca-rotation-confirm.png)

圖 25：兩項確認均勾選後，送出按鈕才可使用。此圖攝於送出前。

![CA 替換完成](../../images/console-ca-rotation-complete.png)

圖 26：本機測試已完成一張憑證重簽；CA ID 等識別資料已遮蔽。這次曾因 TAK API 啟動較慢而由原批次人工復原，詳見[驗證紀錄](../../validation/2026-09-25-wifi-env-ca-console.md)。

![舊 CA 憑證的撤銷狀態](../../images/console-ca-rotation-revoked.png)

圖 27：舊憑證在清冊顯示「簽發 CA 已撤銷」，不可再選取或交付。

若工作失敗，先依[憑證使用手冊](../certificate-operator-guide.md#撤銷ca-輪替與復原)檢查快照、Root CRL 與服務狀態，不要直接重試。Android 新 DPK 匯入、8443 套件與 Vx 四頻道仍須分別驗收。

[返回任務索引](../console-task-manual.md)
