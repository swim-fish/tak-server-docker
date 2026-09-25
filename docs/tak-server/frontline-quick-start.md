# 現場人員 Quick Start

本頁供已取得 TAK 控制台操作權限的現場人員使用。管理者在 Windows 控制台準備設定；裝置使用者在 Android 掃描對應的 QR。開始前，先確認裝置已連上現場網路，控制台及分享服務均可使用。

> **先認 QR 類型：**TAK 登入 QR 交給 ATAK 匯入；ICU QR 交給 TAK ICU 匯入；Vx 任務要在 ATAK 的 Data Packages 從 TAK Server 下載。三者不可互換。掃碼後請點相機顯示的**完整連結**，只看到下載通知不代表設定成功。

## 1. 建立 TAK 登入憑證並交付 QR

**控制台：**「引導式佈建 → 新增 TAK 用戶端」。每台裝置填不同的名稱與憑證 CN，選擇到期時間；可用日曆或快速選項。把需要的群組移到 **In／寫入**、**Out／讀取**或 **In + Out／讀寫**，再按「預覽批次」核對。

![裝置名稱、憑證 CN、到期時間與群組設定](../images/console-task-02-new-tak.png)

▲ 先填裝置名稱與憑證到期時間；群組位置決定資料讀寫範圍。

![四欄群組清單，包含未指派、In、Out 與 In 加 Out](../images/console-task-02b-group-lanes.png)

▲ 未指派的群組不會授權。選好後再預覽並簽發。

**交付：**設定 QR 可下載的時間與次數，為**每台裝置**顯示自己的 DPK QR。這兩項分享限制與憑證到期時間不同。讓指定裝置用相機掃描，點完整 `tak://` 連結並在 ATAK 確認匯入。

![選擇裝置憑證及設定 QR 分享時間與下載次數](../images/console-task-01-existing-tak.png)

▲ 顯示 QR 前，再核對選到的裝置及分享限制。**不要把同一張裝置憑證 QR 交給另一台裝置。**

**完成判定：**ATAK 的 TAK Server 連線顯示已連線；只有「下載開始」通知仍須繼續檢查。

## 2. 下載 Vx 任務，設定 VS1 與 VS2

在 ATAK 開啟 **Data Packages → Download → 現場 TAK Server**，下載 `ATAK Local Voice`。到 TAK Voice 的 Missions 找到 `vx-local`，確認有 `Primary`、`Alternate`、`Medical`、`Emergency`。

![控制台的 Vx 任務佈建入口](../images/console-task-04-vx.png)

▲ 管理者先確認伺服器上的 Vx 任務可供下載；裝置端要從 TAK Server 的 Data Packages 下載。

![TAK Voice 的四個可選頻道](../images/atak-vx-four-channel-pool.jpg)

▲ 在 VS1、VS2 分別選擇要使用的頻道，並各自測試加入。

**密碼提醒：**VS1 與 VS2 首次連線時，若各自跳出 `Enter Password for takbox.local`，**兩個提示都要輸入 Mumble 密碼**。若已記住密碼，可能不再出現提示。此處不是 ATAK 憑證或管理員密碼；不要快速略過提示。

![Vx 的 Mumble 密碼輸入視窗](../images/atak-vx-06-enter-mumble-password.jpg)

▲ VS1、VS2 都應確認已加入指定頻道，再測試通話。

## 3. 用 ICU QR 設定人員影像

**控制台：**「引導式佈建 → ICU 影像發布」，選小隊與人員代號，設定 QR 可下載的時間與次數，預覽後顯示 QR。不同裝置要使用不同的影像路徑；同隊共用 QR 時，使用者可在 ICU 改自己的末段代號。

![ICU 小隊、人員代號及 QR 分享限制](../images/console-task-05-icu.png)

▲ 一般人員使用「標準」模式，選小隊與人員代號。

**Android：**用系統相機掃 QR，點完整 `icu://download?...` 連結。ICU 顯示 `Externally configured using the QR Code` 後，核對伺服器、路徑與 SSL 設定，按開始發布。最後到「MediaMTX 管理」確認該人員的串流已上線。

![同一小隊改為 2 號路徑後，在控制台顯示上線](../images/console-icu-alpha-2-live-path.png)

▲ 以小隊與人員代號辨識影像。兩台裝置不可同時使用完全相同的路徑。

室內使用時，確認 ICU 的 **Disable Local Broadcasting** 已勾選；若未勾選且 GPS 中斷，曾觀察到發布停止。新 QR 預設為勾選。

![ICU 已勾選 Disable Local Broadcasting](../images/icu-disable-local-broadcasting.jpg)

▲ 這張實機畫面可作為勾選位置的參考。

## 4. 交付無人機或其他設備的發布網址

**控制台：**「引導式佈建 → Advanced → 一般設備」，填設備名稱與該設備專用的影像路徑。預覽後建立身分，在結果頁按「顯示連線資訊」，依設備能力複製 **RTSPS** 或 **RTSP** 的完整網址，或顯示相應 QR。

![一般設備名稱與發布路徑輸入畫面](../images/console-task-06-device.png)

▲ 每台設備指定自己的名稱與路徑；預覽時先核對網址末段。

![一般設備的 RTSP 與 RTSPS 網址複製按鈕及 QR 入口，實際密碼已遮蔽](../images/console-drone-05-copy-links-redacted.png)

▲ 網址內含該設備的帳號與密碼，只交給設備操作人員。此圖已遮蔽，不能直接拿來連線。

![設備發布後出現在目前串流清單](../images/console-drone-03-stream-card.png)

▲ 看到設備路徑上線後，再開啟即時預覽確認畫面。

## 5. 停用：選對要停止的項目

| 要做什麼 | 控制台入口 | 操作後仍要注意 |
| --- | --- | --- |
| 不讓 QR 繼續下載 | 檔案分享 → 分享紀錄 → 停止分享 | 已下載的設定不會從裝置消失。 |
| 不讓裝置再以舊 TAK 憑證登入 | 用戶端憑證 → 憑證清冊 → 撤銷選取的憑證 | 先核對裝置名稱與 CRL ID；撤銷後重新連線驗收。 |
| 停止 ICU 小隊發布 | MediaMTX 管理 → ICU → 停用小隊身分 | 小隊共用身分，會影響該小隊全部裝置。 |
| 停止一台無人機發布 | MediaMTX 管理 → 其他 → 停用該設備身分 | 該設備原發布網址不能再使用。 |
| 停止 Vx／Mumble 使用者 | Mumble 管理 → 中斷連線、移除註冊身分；需要時重設共用密碼 | **撤銷 TAK 憑證不會自動停用 Mumble。**變更密碼後，VS1、VS2 需各自重新連線。 |

![分享紀錄的狀態及停止分享入口](../images/console-task-09-shares.png)

▲ 只要停止下載，就在分享紀錄處理；這不是撤銷憑證。

![憑證清冊已選取的裝置憑證](../images/console-task-11b-selected-certificate.png)

▲ 撤銷前先核對選取的裝置；不要只看可能相同的顯示名稱。

![撤銷憑證的確認視窗](../images/console-task-11-revoke.png)

▲ 撤銷無法復原；確認視窗會要求再次勾選。

![MediaMTX 的 ICU 小隊管理卡片](../images/console-media-icu-cards.png)

▲ 影像發布身分在 MediaMTX 管理，不在憑證清冊。

![Mumble 線上連線與已註冊身分清單](../images/console-task-10-mumble.png)

▲ 踢除線上連線後，身分仍可能重新登入；需要阻止再次登入時，另處理註冊身分與共用密碼。

## 遇到問題時

- **TAK QR 已下載，卻未連線：**回 ATAK 檢查是否完成匯入；同名舊 DPK 可能需要先移除舊下載副本。
- **Vx 沒有任務：**確認是在 ATAK 的 Data Packages 從 TAK Server 下載；不要用一般檔案 QR 代替。
- **Vx 沒有密碼提示但仍能加入：**可能已有儲存密碼或註冊身分，請交由 Mumble 管理人員確認。
- **ICU 顯示已外部設定但沒有畫面：**確認已按開始發布，以及 MediaMTX 清單是否出現對應路徑。

需要詳細操作或疑難排解時，查閱[TAK 控制台任務操作手冊](console-task-manual.md)。
