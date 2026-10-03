# TAK 裝置憑證與群組：原文與中英文改寫對照

[原始手冊](../../tak-server/console-task-manual/certificates-and-groups.md) · [繁中版](../zh-TW/certificates-and-groups.md) · [English](../en/certificates-and-groups.md)

原文欄保留來源內容。段落 ID 用於追蹤對照。獨立手冊依操作順序排列，必要時將風險說明移到步驟前。

## B001

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **TAK 裝置憑證與群組** | **TAK 裝置憑證與群組** | **TAK device certificates and groups** |

## B002

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [返回任務索引](../../tak-server/console-task-manual.md) | [返回任務索引](../../tak-server/console-task-manual.md) | [Return to the task index](../../tak-server/console-task-manual.md) |

## B003

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-01 | Anchor: task-01 | Anchor: task-01 |

## B004

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務一　交付既有 TAK 裝置憑證** | **任務一　交付既有 TAK 裝置憑證** | **Task 1: Deliver an existing TAK certificate** |

## B005

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 在「引導式佈建 → TAK Server 連線」選擇有效且已註冊的憑證，核對 CN、CRL ID 與到期日。每台裝置使用自己的 DPK。<br>2. 設定分享期限與下載上限，按「預覽」後建立 QR。讓指定 Android 掃完整 `tak://` 連結並在 ATAK 確認匯入。<br>3. 確認 ATAK 已連上 `takbox.local:8089:ssl`；分享紀錄應顯示 `<CN>-<CRL ID>`。 | 每台裝置須使用自己的 DPK。<br><br>1. 在「引導式佈建 → TAK Server 連線」選擇有效且已註冊的憑證。<br>2. 核對 CN、CRL ID 與到期日。<br>3. 設定分享期限與下載上限。<br>4. 按「預覽」。<br>5. 建立 QR。<br>6. 讓指定 Android 掃描完整 `tak://` 連結。<br>7. 在 ATAK 確認匯入。<br>8. 確認 ATAK 已連上 `takbox.local:8089:ssl`。<br>9. 核對分享紀錄顯示 `<CN>-<CRL ID>`。 | Each device must use its own DPK.<br><br>1. Select a valid, registered certificate in 「引導式佈建 → TAK Server 連線」.<br>2. Check the CN, CRL ID, and expiry date.<br>3. Set the sharing expiry and download limit.<br>4. Select 「預覽」.<br>5. Create the QR.<br>6. Let the assigned Android device scan the complete `tak://` link.<br>7. Check the import in ATAK.<br>8. Check that ATAK connects to `takbox.local:8089:ssl`.<br>9. Check that the sharing record shows `<CN>-<CRL ID>`. |

## B006

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 同名舊 DPK 若阻止更新，先清除裝置上的舊下載副本。匯入提示或下載通知不能代替連線驗收。 | 同名舊 DPK 若阻止更新，先清除裝置上的舊下載副本。匯入提示或下載通知不能代替連線驗收。 | If an old DPK with the same name prevents the update, first delete the old downloaded copy from the device. An import message or download notification does not prove a successful connection. |

## B007

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [交付頁選取憑證與分享限制](../../images/console-task-01-existing-tak.png) | [交付頁選取憑證與分享限制](../../images/console-task-01-existing-tak.png) | [Certificate selection and sharing limits](../../images/console-task-01-existing-tak.png) |

## B008

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 1：選擇憑證，設定 QR 分享時間與下載上限。 | 圖 1：選擇憑證，設定 QR 分享時間與下載上限。 | Figure 1: Select the certificate. Set the QR sharing duration and download limit. |

## B009

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [憑證清冊篩選與識別欄位](../../images/console-task-01b-inventory.png) | [憑證清冊篩選與識別欄位](../../images/console-task-01b-inventory.png) | [Certificate inventory filters and identifiers](../../images/console-task-01b-inventory.png) |

## B010

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 2：回清冊用 CN 或 CRL ID 核對身分；識別資料已遮蔽。 | 圖 2：回清冊用 CN 或 CRL ID 核對身分。識別資料已遮蔽。 | Figure 2: Use the CN or CRL ID to check the identity in the inventory. Identifiers are concealed. |

## B011

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-02 | Anchor: task-02 | Anchor: task-02 |

## B012

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務二　新增 TAK 裝置並指定群組** | **任務二　新增 TAK 裝置並指定群組** | **Task 2: Add TAK devices and assign groups** |

## B013

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 在「引導式佈建 → 新增 TAK 用戶端」為每台填顯示名稱與唯一 ASCII CN。到期日可用日曆，或選 1 小時、1 天、7 天、14 天、28 天、90 天。<br>2. 將群組移到 In／寫入、Out／讀取或 In + Out／讀寫；至少指定一種權限。批次可建 1 至 10 台，各有獨立私鑰與 DPK。<br>3. 按「預覽批次」核對 CN、效期、群組及 QR 限制，再確認簽發。結果頁逐台檢查註冊、序號與 QR；TAK 會重啟一次。 | 批次可建立 1 至 10 台裝置。每台裝置各有獨立私鑰與 DPK。確認簽發後，TAK 會重啟一次。<br><br>1. 在「引導式佈建 → 新增 TAK 用戶端」填入每台裝置的顯示名稱。<br>2. 為每台裝置填入唯一的 ASCII CN。<br>3. 用日曆設定到期日，或選擇 1 小時、1 天、7 天、14 天、28 天、90 天。<br>4. 將群組移到 In／寫入、Out／讀取或 In + Out／讀寫。至少須指定一種權限。<br>5. 按「預覽批次」。<br>6. 核對 CN、效期、群組及 QR 限制。<br>7. 確認簽發。<br>8. 在結果頁逐台檢查註冊狀態、序號與 QR。 | A batch can contain 1 to 10 devices. Each device has a separate private key and DPK. TAK restarts once after you confirm issuance. Expiry options are 1 hour, 1 day, 7 days, 14 days, 28 days, and 90 days.<br><br>1. Enter each device display name in 「引導式佈建 → 新增 TAK 用戶端」.<br>2. Enter a unique ASCII CN for each device.<br>3. Set the expiry with the calendar, or select a listed duration.<br>4. Move groups to In/write, Out/read, or In + Out/read and write. You must assign at least one permission.<br>5. Select 「預覽批次」.<br>6. Check the CN, validity period, groups, and QR limits.<br>7. Confirm issuance.<br>8. Check each device registration, serial number, and QR on the results page. |

## B014

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 部分完成時先查既有結果，再以相同作業 ID 接續，避免重複簽發。同頁的 QR 下載期限和憑證效期是兩項設定。 | 若批次只完成一部分，先查既有結果。再以相同工作 ID 接續，避免重複簽發。QR 下載期限與憑證效期是兩項獨立設定。 | If the batch completes only some devices, first check the existing results. Continue with the same job ID to prevent duplicate issuance. The QR download expiry and certificate validity period are separate settings. |

## B015

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [新增裝置與效期欄位](../../images/console-task-02-new-tak.png) | [新增裝置與效期欄位](../../images/console-task-02-new-tak.png) | [New device and expiry fields](../../images/console-task-02-new-tak.png) |

## B016

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 3：逐台填 CN 與到期時間，再設定群組。 | 圖 3：逐台填 CN 與到期時間，再設定群組。 | Figure 3: Enter each CN and expiry time. Then assign the groups. |

## B017

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [四欄式群組清單](../../images/console-task-02b-group-lanes.png) | [四欄式群組清單](../../images/console-task-02b-group-lanes.png) | [Four-column group list](../../images/console-task-02b-group-lanes.png) |

## B018

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 4：未指派群組不授權讀寫；移到 In、Out 或 In + Out 才生效。 | 圖 4：未指派群組不授權讀寫。移到 In、Out 或 In + Out 才生效。 | Figure 4: Unassigned groups give no read or write permission. Move a group to In, Out, or In + Out to assign permission. |

## B019

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-03 | Anchor: task-03 | Anchor: task-03 |

## B020

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務三　調整裝置的資料讀寫範圍** | **任務三　調整裝置的資料讀寫範圍** | **Task 3: Change device read and write permissions** |

## B021

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 開啟「用戶端憑證 → 依群組檢視」，預設篩選「使用中」。可勾選「隱藏空群組」縮短頁面；新增憑證時先取消勾選，才可拖到原本隱藏的空群組。<br>2. 可拖曳憑證，或按項目右側的「移動」開啟對話框。選「移動／調整權限」後指定目的群組與 In、Out 或 In + Out；選「從此群組移除」則只移除來源群組。也可拖到「未記錄群組」。<br>3. 核對待儲存變更並確認儲存；待儲存數歸零後，從 TAK API 讀回群組。調整既有群組不必重做 DPK。 | 1. 開啟「用戶端憑證 → 依群組檢視」。預設篩選為「使用中」。<br>2. 視需要勾選「隱藏空群組」。若新增憑證時要拖到空群組，先取消勾選。<br>3. 拖曳憑證，或按項目右側的「移動」開啟對話方塊。<br>4. 若要變更目的群組或權限，選「移動／調整權限」。<br>5. 若選擇「移動／調整權限」，指定目的群組與 In、Out 或 In + Out。<br>6. 若只要移除來源群組，選「從此群組移除」。也可拖到「未記錄群組」。<br>7. 核對待儲存變更。<br>8. 確認儲存。<br>9. 待儲存數歸零後，從 TAK API 讀回群組。<br><br>調整既有群組不必重做 DPK。 | 1. Open 「用戶端憑證 → 依群組檢視」. The default filter is 「使用中」.<br>2. Select 「隱藏空群組」 if necessary. Clear it before you drag a new certificate into an empty group.<br>3. Drag the certificate, or select 「移動」 beside the item to open the dialog.<br>4. To change the destination group or permissions, select 「移動／調整權限」.<br>5. If you select 「移動／調整權限」, specify the destination group and In, Out, or In + Out.<br>6. To remove only the source group, select 「從此群組移除」. You can also drag to 「未記錄群組」.<br>7. Check the pending changes.<br>8. Confirm the save.<br>9. When the pending count reaches zero, read the groups from the TAK API.<br><br>You do not need a new DPK after changes to existing groups. |

## B022

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 驗證隔離時，要經 TAK Server 傳送新的 CoT；同一 Wi-Fi 的本機廣播無法證明群組規則。[雙裝置實測](../../validation/2026-09-24-ca-rotation-device-baseline.md)記錄 Alpha／Bravo 的結果。 | 驗證隔離時，須經 TAK Server 傳送新的 CoT。同一 Wi-Fi 的本機廣播無法證明群組規則。[雙裝置實測](../../validation/2026-09-24-ca-rotation-device-baseline.md)記錄 Alpha／Bravo 的結果。 | To test isolation, send new CoT through TAK Server. Local broadcasts on the same Wi-Fi do not prove group isolation. The [two-device test](../../validation/2026-09-24-ca-rotation-device-baseline.md) records the Alpha/Bravo results. |

## B023

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [依群組檢視憑證](../../images/console-task-03-groups.png) | [依群組檢視憑證](../../images/console-task-03-groups.png) | [Certificates grouped by permissions](../../images/console-task-03-groups.png) |

## B024

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 5：目前的狀態篩選、隱藏空群組、三欄權限與單一「移動」按鈕。 | 圖 5：目前的狀態篩選、隱藏空群組、三欄權限與單一「移動」按鈕。 | Figure 5: Status filters, hidden empty groups, three permission columns, and the single 「移動」 button. |

## B025

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [移動憑證並調整 In Out 權限的對話框](../../images/console-task-03-move-dialog.png) | [移動憑證並調整 In Out 權限的對話方塊](../../images/console-task-03-move-dialog.png) | [Move certificate and change In/Out permissions](../../images/console-task-03-move-dialog.png) |

## B026

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 5a：「移動／調整權限」可選目的群組與權限；按「暫存移動」後仍須儲存群組變更。 | 圖 5a：「移動／調整權限」可選目的群組與權限。按「暫存移動」後仍須儲存群組變更。 | Figure 5a: 「移動／調整權限」 lets you select the destination and permissions. After 「暫存移動」, you must still save the group changes. |

## B027

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [從目前群組移除憑證的對話框](../../images/console-task-03-remove-dialog.png) | [從目前群組移除憑證的對話方塊](../../images/console-task-03-remove-dialog.png) | [Remove certificate from the current group](../../images/console-task-03-remove-dialog.png) |

## B028

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 5b：切換「從此群組移除」後，只移除來源群組；圖中未送出變更。 | 圖 5b：切換「從此群組移除」後，只移除來源群組。圖中未送出變更。 | Figure 5b: 「從此群組移除」 removes only the source group. No change was submitted in this image. |

## B029

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [新增憑證到群組視窗](../../images/console-task-03b-add-group.png) | [新增憑證到群組視窗](../../images/console-task-03b-add-group.png) | [Add a certificate to a group](../../images/console-task-03b-add-group.png) |

## B030

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 6：搜尋尚未加入的使用中憑證，選擇加入權限；憑證識別資料已遮蔽。 | 圖 6：搜尋尚未加入的使用中憑證，選擇加入權限。憑證識別資料已遮蔽。 | Figure 6: Find an active certificate that is not in the group. Select its permissions. Certificate identifiers are concealed. |

## B031

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-11 | Anchor: task-11 | Anchor: task-11 |

## B032

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務十一　撤銷 TAK 裝置憑證** | **任務十一　撤銷 TAK 裝置憑證** | **Task 11: Revoke a TAK device certificate** |

## B033

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 在「用戶端憑證 → 憑證清冊」核對 CN、簽發 CA、CRL ID 與 SHA-256 指紋；不可只靠可能重複的名稱。<br>2. 選取有效憑證，按「撤銷選取的憑證」，再於確認視窗勾選。撤銷不可復原；控制台會停止關聯 QR、更新 CRL 並重啟 TAK。<br>3. 檢查 CRL 含該序號，並用舊 DPK 重新連線驗證 8089 拒絕；Android 可能只顯示 `IO Error`。 | **注意：撤銷不可復原。** 控制台會停止關聯 QR、更新 CRL 並重啟 TAK。不可只靠可能重複的名稱識別憑證。<br><br>1. 在「用戶端憑證 → 憑證清冊」核對 CN、簽發 CA、CRL ID 與 SHA-256 指紋。<br>2. 選取有效憑證。<br>3. 按「撤銷選取的憑證」。<br>4. 在確認視窗勾選確認。<br>5. 檢查 CRL 含有該序號。<br>6. 用舊 DPK 重新連線，確認 8089 拒絕連線。Android 可能只顯示 `IO Error`。 | **CAUTION: You cannot reverse revocation.** The console stops related QR links, updates the CRL, and restarts TAK. Do not identify certificates only by names that can be duplicates.<br><br>1. Check the CN, issuing CA, CRL ID, and SHA-256 fingerprint in 「用戶端憑證 → 憑證清冊」.<br>2. Select the valid certificate.<br>3. Select 「撤銷選取的憑證」.<br>4. Select the confirmation checkbox in the dialog.<br>5. Check that the CRL contains the serial number.<br>6. Reconnect with the old DPK to check that 8089 rejects the connection. Android may show only `IO Error`. |

## B034

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 一般撤銷流程會自動更新 CRL 並重啟 TAK Server；若撤銷紀錄已寫入，但發布或重啟失敗，可選「重新發布 CRL 並重啟」。它會依目前 CA 資料庫重新產生 Root CA 與簽發中繼 CA 的 CRL，不會新增或還原撤銷紀錄，也不會撤銷中繼 CA。8443 須另測。中繼 CA 替換使用獨立子頁，並須檢查 TAK 信任憑證鏈資料庫（truststore）是否仍直接信任舊 CA；詳見[憑證使用手冊](../../tak-server/certificate-operator-guide.md)。 | 一般撤銷流程會自動更新 CRL 並重啟 TAK Server。若撤銷紀錄已寫入，但發布或重啟失敗，可選「重新發布 CRL 並重啟」。<br><br>這項操作會依目前 CA 資料庫重新產生 Root CA 與簽發中繼 CA 的 CRL。它不會新增或還原撤銷紀錄，也不會撤銷中繼 CA。<br><br>8443 須另測。中繼 CA 替換使用獨立子頁。替換時須檢查 TAK 信任憑證鏈資料庫（truststore）是否仍直接信任舊 CA。詳見[憑證使用手冊](../../tak-server/certificate-operator-guide.md)。 | The usual revocation procedure updates the CRL and restarts TAK Server automatically. If the revocation record exists but publication or restart fails, you can select 「重新發布 CRL 並重啟」.<br><br>This operation generates Root CA and issuing intermediate CA CRLs from the current CA database. It does not add or reverse revocation records. It does not revoke the intermediate CA.<br><br>Test 8443 separately. Intermediate CA replacement uses a separate subpage. Check whether the TAK truststore still directly trusts the old CA. See the [certificate operator guide](../../tak-server/certificate-operator-guide.md). |

## B035

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [憑證清冊選取狀態](../../images/console-task-11b-selected-certificate.png) | [憑證清冊選取狀態](../../images/console-task-11b-selected-certificate.png) | [Selected certificate in the inventory](../../images/console-task-11b-selected-certificate.png) |

## B036

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 21：先選憑證並核對識別欄位；識別資料已遮蔽。 | 圖 21：先選憑證並核對識別欄位。識別資料已遮蔽。 | Figure 21: Select the certificate first. Check the identifier fields. Identifiers are concealed. |

## B037

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [撤銷憑證確認視窗](../../images/console-task-11-revoke.png) | [撤銷憑證確認視窗](../../images/console-task-11-revoke.png) | [Certificate revocation dialog](../../images/console-task-11-revoke.png) |

## B038

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 22：再次確認影響範圍；截圖停在確認視窗，沒有送出撤銷。 | 圖 22：再次確認影響範圍。截圖停在確認視窗，沒有送出撤銷。 | Figure 22: Check the effect again. The screenshot shows the confirmation dialog before revocation submission. |

## B039

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-ca-replace | Anchor: task-ca-replace | Anchor: task-ca-replace |

## B040

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務十二　替換簽發中繼 CA 並重簽裝置** | **任務十二　替換簽發中繼 CA 並重簽裝置** | **Task 12: Replace the issuing intermediate CA and reissue certificates** |

## B041

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 到「用戶端憑證 → CA 替換」，核對目前 CA ID。先確認控制台與 Windows 憑證管理程式正常，並安排 TAK、Mumble、MediaMTX 的短暫中斷。<br>2. 勾選要重簽的使用中憑證。原到期日會自動帶入，可為每張憑證個別使用日曆調整，或選從現在起 7、14、28、90、730 天。未勾選的舊憑證會隨舊 CA 撤銷而失效，但不會產生新 DPK。<br>3. 核對 CN、群組與新到期日，開啟確認視窗並勾選兩項獨立確認後送出。TAK、Mumble 與 MediaMTX 會短暫中斷；同頁可檢視背景工作的階段與結果。<br>4. 到清冊確認舊憑證標示「簽發 CA 已撤銷」，逐一交付新 DPK。分別測試 ATAK 的 8089／8443 與 Vx 四頻道；Mumble 原有帳號另行管理。 | **注意：替換會短暫中斷 TAK、Mumble 與 MediaMTX。** 未勾選的舊憑證會隨舊 CA 撤銷而失效。系統不會為未勾選的憑證產生新 DPK。<br><br>1. 開啟「用戶端憑證 → CA 替換」。<br>2. 核對目前 CA ID。<br>3. 確認控制台與 Windows 憑證管理程式正常。<br>4. 安排 TAK、Mumble、MediaMTX 的短暫中斷。<br>5. 勾選要重簽的使用中憑證。系統會帶入原到期日。<br>6. 如需調整效期，為每張憑證使用日曆，或選從現在起 7、14、28、90、730 天。<br>7. 核對 CN、群組與新到期日。<br>8. 開啟確認視窗。<br>9. 勾選兩項獨立確認。<br>10. 送出工作。同頁可檢視背景工作的階段與結果。<br>11. 到清冊確認舊憑證標示「簽發 CA 已撤銷」。<br>12. 逐一交付新 DPK。<br>13. 分別測試 ATAK 的 8089／8443 與 Vx 四頻道。<br><br>Mumble 原有帳號須另行管理。 | **CAUTION: Replacement briefly interrupts TAK, Mumble, and MediaMTX.** Revocation of the old CA invalidates old certificates that you do not select. The system does not generate new DPK files for those certificates. Preset durations are 7, 14, 28, 90, and 730 days from now.<br><br>1. Open 「用戶端憑證 → CA 替換」.<br>2. Check the current CA ID.<br>3. Check that the console and Windows certificate worker operate correctly.<br>4. Schedule a brief interruption of TAK, Mumble, and MediaMTX.<br>5. Select the active certificates to reissue. The system copies their original expiry dates.<br>6. If necessary, change each expiry with the calendar, or select a preset duration.<br>7. Check the CN, groups, and new expiry dates.<br>8. Open the confirmation dialog.<br>9. Select both independent confirmation checkboxes.<br>10. Submit the job. The same page shows the background job stages and results.<br>11. Check that the inventory marks old certificates 「簽發 CA 已撤銷」.<br>12. Deliver each new DPK.<br>13. Test ATAK 8089/8443 and all four Vx channels separately.<br><br>Manage existing Mumble accounts separately. |

## B042

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 8443 的受控測試已確認：實際載入 Root CRL 時，舊 CA 憑證的新連線會遭拒。現行設定已還原為只直接載入第一筆 CRL；每次 CA 替換後仍須以舊憑證重連 8443 確認遭拒，並以新憑證確認仍可使用。見[8443 測試紀錄](../../validation/2026-09-26-ca-rotation-8443-retest.md)。 | 8443 的受控測試確認：實際載入 Root CRL 時，舊 CA 憑證的新連線會遭拒。原始文件所述設定已還原為只直接載入第一筆 CRL。<br><br>每次 CA 替換後，須以舊憑證重新連線 8443，確認連線遭拒。再以新憑證確認服務仍可使用。見[8443 測試紀錄](../../validation/2026-09-26-ca-rotation-8443-retest.md)。 | The controlled 8443 test confirmed rejection of new connections from old CA certificates when the server loaded the Root CRL. The configuration described in the source was restored to direct loading of only the first CRL.<br><br>After each CA replacement, reconnect to 8443 with an old certificate to check rejection. Then check access with a new certificate. See the [8443 test record](../../validation/2026-09-26-ca-rotation-8443-retest.md). |

## B043

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [CA 替換頁的重簽選取與個別到期時間欄位](../../images/console-ca-rotation-1440.png) | [CA 替換頁的重簽選取與個別到期時間欄位](../../images/console-ca-rotation-1440.png) | [CA replacement selection and expiry fields](../../images/console-ca-rotation-1440.png) |

## B044

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 23：替換會使舊憑證失效，頁面以紅色警告標示；為選取的裝置指定新到期時間。識別資料已遮蔽。 | 圖 23：替換會使舊憑證失效，頁面以紅色警告標示。為選取的裝置指定新到期時間。識別資料已遮蔽。 | Figure 23: Replacement invalidates old certificates. The page shows a red warning. Set a new expiry for selected devices. Identifiers are concealed. |

## B045

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [手機寬度的 CA 替換頁](../../images/console-ca-rotation-390.png) | [手機寬度的 CA 替換頁](../../images/console-ca-rotation-390.png) | [CA replacement at phone width](../../images/console-ca-rotation-390.png) |

## B046

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 24：窄螢幕依序呈現高風險紅色警告、裝置卡片與操作按鈕；識別資料已遮蔽。 | 圖 24：窄螢幕依序呈現高風險紅色警告、裝置卡片與操作按鈕。識別資料已遮蔽。 | Figure 24: The narrow layout shows the red risk warning, device cards, and controls in sequence. Identifiers are concealed. |

## B047

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [CA 替換的雙重確認視窗](../../images/console-ca-rotation-confirm.png) | [CA 替換的雙重確認視窗](../../images/console-ca-rotation-confirm.png) | [Two CA replacement confirmations](../../images/console-ca-rotation-confirm.png) |

## B048

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 25：兩項確認均勾選後，送出按鈕才可使用。此圖攝於送出前。 | 圖 25：兩項確認均勾選後，送出按鈕才可使用。此圖攝於送出前。 | Figure 25: Both checkboxes must be selected before submission is available. The image precedes submission. |

## B049

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [CA 替換完成](../../images/console-ca-rotation-complete.png) | [CA 替換完成](../../images/console-ca-rotation-complete.png) | [Completed CA replacement](../../images/console-ca-rotation-complete.png) |

## B050

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 26：本機測試已完成一張憑證重簽；CA ID 等識別資料已遮蔽。這次曾因 TAK API 啟動較慢而由原批次人工復原，詳見[驗證紀錄](../../validation/2026-09-25-wifi-env-ca-console.md)。 | 圖 26：本機測試已完成一張憑證重簽。CA ID 等識別資料已遮蔽。這次曾因 TAK API 啟動較慢而由原批次人工復原，詳見[驗證紀錄](../../validation/2026-09-25-wifi-env-ca-console.md)。 | Figure 26: The local test reissued one certificate. CA IDs and other identifiers are concealed. A slow TAK API startup required manual recovery through the original batch. See the [validation record](../../validation/2026-09-25-wifi-env-ca-console.md). |

## B051

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [舊 CA 憑證的撤銷狀態](../../images/console-ca-rotation-revoked.png) | [舊 CA 憑證的撤銷狀態](../../images/console-ca-rotation-revoked.png) | [Revoked certificates from the old CA](../../images/console-ca-rotation-revoked.png) |

## B052

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 27：舊憑證在清冊顯示「簽發 CA 已撤銷」，不可再選取或交付。 | 圖 27：舊憑證在清冊顯示「簽發 CA 已撤銷」，不可再選取或交付。 | Figure 27: The inventory marks old certificates 「簽發 CA 已撤銷」. You cannot select or deliver them. |

## B053

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 若工作失敗，先依[憑證使用手冊](../../tak-server/certificate-operator-guide.md#撤銷ca-輪替與復原)檢查快照、Root CRL 與服務狀態，不要直接重試。Android 新 DPK 匯入、8443 套件與 Vx 四頻道仍須分別驗收。 | 若工作失敗，不要直接重試。先依[憑證使用手冊](../../tak-server/certificate-operator-guide.md#撤銷ca-輪替與復原)檢查快照、Root CRL 與服務狀態。Android 新 DPK 匯入、8443 套件與 Vx 四頻道仍須分別驗收。 | If the job fails, do not retry immediately. First check snapshots, the Root CRL, and service states through the [certificate operator guide](../../tak-server/certificate-operator-guide.md#撤銷ca-輪替與復原). Test the new Android DPK import, 8443 packages, and all four Vx channels separately. |

## B054

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [返回任務索引](../../tak-server/console-task-manual.md) | [返回任務索引](../../tak-server/console-task-manual.md) | [Return to the task index](../../tak-server/console-task-manual.md) |
