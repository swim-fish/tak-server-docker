# Vx 任務與 Mumble 語音

[返回任務索引](index.md)

<a id="task-04"></a>

## 任務四　更新 Vx 四頻道任務

1. 在「引導式佈建 → Vx 任務佈建」產生套件。
2. 預覽套件。
3. 核對 SHA-256 與同名套件筆數。
4. 確認後執行「備份並強制替換」。
5. 核對結果只剩一筆 `ATAK Local Voice`。
6. 在 ATAK 的 Data Packages → Download，從 TAK Server 取得套件。
7. 到 TAK Voice 逐一加入 Primary、Alternate、Medical、Emergency。

Vx-only DPK 的一般下載 QR 無法直接建立 Mission。若誤用 `Clear Database`，任務會被移除，須重新下載。若替換失敗，使用工作備份復原。

![Vx 套件佈建入口](../../images/console-task-04-vx.png)

圖 7：產生套件後先預覽，再確認替換固定名稱的伺服器套件。

![ATAK Vx 四頻道清單](../../images/atak-vx-four-channel-pool.jpg)

圖 8：裝置下載後，TAK Voice 應顯示四個可加入的頻道。

<a id="task-10"></a>

## 任務十　管理 Vx 語音登入

依目的選擇下列操作。中斷連線、刪除註冊身分、重新啟動與重設密碼是不同操作。

### 中斷目前連線

1. 在「Mumble 管理 → 線上連線」選擇 session。
2. 按「中斷選取的連線」。

該身分仍可再次登入。

### 刪除已記住的身分

系統會先備份資料庫。有效的共用密碼仍可讓使用者重新註冊。

1. 到「已註冊身分」勾選要刪除的身分。
2. 確認刪除。

### 重新啟動或重設密碼

兩項操作都會中斷線上連線。

- 若要保留頻道與註冊資料，選「重新啟動 Mumble」。
- 若要變更本機 secret，選「重設共用密碼並重新啟動」。

核對線上清單與註冊清單。再驗證 Vx 重新登入的結果。TAK 憑證撤銷不等於 Mumble 停用。已註冊 Vx 身分在改密碼後仍可能直接登入。

![Mumble 線上與註冊清單](../../images/console-task-10-mumble.png)

圖 19：線上 session 和已註冊身分分開管理。截圖時沒有線上連線。

![Mumble 伺服器控制](../../images/console-task-10b-server-controls.png)

圖 20：重新啟動與重設密碼是不同操作，皆會中斷連線。

[返回任務索引](index.md)
