# Vx 任務與 Mumble 語音：原文與中英文改寫對照

[原始手冊](../../tak-server/console-task-manual/vx-and-mumble.md) · [繁中版](../zh-TW/vx-and-mumble.md) · [English](../en/vx-and-mumble.md)

原文欄保留來源內容。段落 ID 用於追蹤對照。獨立手冊依操作順序排列，必要時將風險說明移到步驟前。

## B001

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **Vx 任務與 Mumble 語音** | **Vx 任務與 Mumble 語音** | **Vx missions and Mumble voice** |

## B002

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [返回任務索引](../../tak-server/console-task-manual.md) | [返回任務索引](../../tak-server/console-task-manual.md) | [Return to the task index](../../tak-server/console-task-manual.md) |

## B003

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-04 | Anchor: task-04 | Anchor: task-04 |

## B004

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務四　更新 Vx 四頻道任務** | **任務四　更新 Vx 四頻道任務** | **Task 4: Update the four-channel Vx mission** |

## B005

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 在「引導式佈建 → Vx 任務佈建」產生套件並預覽，核對 SHA-256 與同名套件筆數。<br>2. 確認後執行「備份並強制替換」；結果須只剩一筆 `ATAK Local Voice`。<br>3. ATAK 從 TAK Server 的 Data Packages → Download 取得套件，再到 TAK Voice 逐一加入 Primary、Alternate、Medical、Emergency。 | 1. 在「引導式佈建 → Vx 任務佈建」產生套件。<br>2. 預覽套件。<br>3. 核對 SHA-256 與同名套件筆數。<br>4. 確認後執行「備份並強制替換」。<br>5. 核對結果只剩一筆 `ATAK Local Voice`。<br>6. 在 ATAK 的 Data Packages → Download，從 TAK Server 取得套件。<br>7. 到 TAK Voice 逐一加入 Primary、Alternate、Medical、Emergency。 | 1. Generate the package in 「引導式佈建 → Vx 任務佈建」.<br>2. Preview the package.<br>3. Check the SHA-256 and the number of packages with the same name.<br>4. After confirmation, select 「備份並強制替換」.<br>5. Check that only one `ATAK Local Voice` package remains.<br>6. In ATAK, download the package from TAK Server through Data Packages → Download.<br>7. In TAK Voice, join Primary, Alternate, Medical, and Emergency individually. |

## B006

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Vx-only DPK 的一般下載 QR 無法直接建立 Mission。若誤用 `Clear Database`，任務會被移除，須重新下載；替換失敗時使用作業備份復原。 | Vx-only DPK 的一般下載 QR 無法直接建立 Mission。若誤用 `Clear Database`，任務會被移除，須重新下載。若替換失敗，使用工作備份復原。 | A general download QR for a Vx-only DPK cannot directly create a Mission. If you accidentally use `Clear Database`, it removes the mission. Download the mission again. If replacement fails, restore from the job backup. |

## B007

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [Vx 套件佈建入口](../../images/console-task-04-vx.png) | [Vx 套件佈建入口](../../images/console-task-04-vx.png) | [Vx package provisioning entry](../../images/console-task-04-vx.png) |

## B008

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 7：產生套件後先預覽，再確認替換固定名稱的伺服器套件。 | 圖 7：產生套件後先預覽，再確認替換固定名稱的伺服器套件。 | Figure 7: Preview the generated package first. Then confirm replacement of the server package with the fixed name. |

## B009

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [ATAK Vx 四頻道清單](../../images/atak-vx-four-channel-pool.jpg) | [ATAK Vx 四頻道清單](../../images/atak-vx-four-channel-pool.jpg) | [Four ATAK Vx channels](../../images/atak-vx-four-channel-pool.jpg) |

## B010

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 8：裝置下載後，TAK Voice 應顯示四個可加入的頻道。 | 圖 8：裝置下載後，TAK Voice 應顯示四個可加入的頻道。 | Figure 8: After download, TAK Voice should show four channels that the device can join. |

## B011

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| Anchor: task-10 | Anchor: task-10 | Anchor: task-10 |

## B012

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| **任務十　管理 Vx 語音登入** | **任務十　管理 Vx 語音登入** | **Task 10: Manage Vx voice login** |

## B013

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 1. 在「Mumble 管理 → 線上連線」選 session 並按「中斷選取的連線」；該身分仍可再次登入。<br>2. 要移除已記住的身分，到「已註冊身分」勾選並確認刪除。系統會先備份資料庫；有效共用密碼仍可讓使用者重新註冊。<br>3. 「重新啟動 Mumble」保留頻道與註冊資料；「重設共用密碼並重新啟動」會改本機 secret。兩者都會中斷線上連線。 | 依目的選擇下列操作。中斷連線、刪除註冊身分、重新啟動與重設密碼是不同操作。<br><br>**中斷目前連線**<br><br>1. 在「Mumble 管理 → 線上連線」選擇 session。<br>2. 按「中斷選取的連線」。<br><br>該身分仍可再次登入。<br><br>**刪除已記住的身分**<br><br>系統會先備份資料庫。有效的共用密碼仍可讓使用者重新註冊。<br><br>1. 到「已註冊身分」勾選要刪除的身分。<br>2. 確認刪除。<br><br>**重新啟動或重設密碼**<br><br>兩項操作都會中斷線上連線。<br><br>- 若要保留頻道與註冊資料，選「重新啟動 Mumble」。<br>- 若要變更本機 secret，選「重設共用密碼並重新啟動」。 | Select the operation for your purpose. Disconnection, identity deletion, restart, and password reset are separate operations.<br><br>**Disconnect a current connection**<br><br>1. Select the session in 「Mumble 管理 → 線上連線」.<br>2. Select 「中斷選取的連線」.<br><br>The identity can log in again.<br><br>**Delete a remembered identity**<br><br>The system first backs up the database. A valid shared password still lets the user register again.<br><br>1. Select the identity in 「已註冊身分」.<br>2. Confirm deletion.<br><br>**Restart or reset the password**<br><br>Both operations disconnect online sessions.<br><br>- To keep channels and registration data, select 「重新啟動 Mumble」.<br>- To change the local secret, select 「重設共用密碼並重新啟動」. |

## B014

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 驗收線上／註冊清單及 Vx 重登。TAK 憑證撤銷不等於 Mumble 停用；已註冊 Vx 身分在改密碼後仍可能直接登入。 | 核對線上清單與註冊清單。再驗證 Vx 重新登入的結果。TAK 憑證撤銷不等於 Mumble 停用。已註冊 Vx 身分在改密碼後仍可能直接登入。 | Check the online and registered identity lists. Then test Vx login again. TAK certificate revocation does not deactivate Mumble. A registered Vx identity may still log in directly after a password change. |

## B015

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [Mumble 線上與註冊清單](../../images/console-task-10-mumble.png) | [Mumble 線上與註冊清單](../../images/console-task-10-mumble.png) | [Mumble online and registered identities](../../images/console-task-10-mumble.png) |

## B016

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 19：線上 session 和已註冊身分分開管理；截圖時沒有線上連線。 | 圖 19：線上 session 和已註冊身分分開管理。截圖時沒有線上連線。 | Figure 19: Manage online sessions and registered identities separately. No connections were online in this screenshot. |

## B017

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [Mumble 伺服器控制](../../images/console-task-10b-server-controls.png) | [Mumble 伺服器控制](../../images/console-task-10b-server-controls.png) | [Mumble server controls](../../images/console-task-10b-server-controls.png) |

## B018

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| 圖 20：重新啟動與重設密碼是不同操作，皆會中斷連線。 | 圖 20：重新啟動與重設密碼是不同操作，皆會中斷連線。 | Figure 20: Restart and password reset are separate operations. Both disconnect sessions. |

## B019

| 原文 | 繁中改寫 | English STE draft |
| --- | --- | --- |
| [返回任務索引](../../tak-server/console-task-manual.md) | [返回任務索引](../../tak-server/console-task-manual.md) | [Return to the task index](../../tak-server/console-task-manual.md) |
