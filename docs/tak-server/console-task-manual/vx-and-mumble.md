# Vx 任務與 Mumble 語音

[返回任務索引](../console-task-manual.md)

<a id="task-04"></a>

## 任務四　更新 Vx 四頻道任務

1. 在「引導式佈建 → Vx 任務佈建」產生套件並預覽，核對 SHA-256 與同名套件筆數。
2. 確認後執行「備份並強制替換」；結果須只剩一筆 `ATAK Local Voice`。
3. ATAK 從 TAK Server 的 Data Packages → Download 取得套件，再到 TAK Voice 逐一加入 Primary、Alternate、Medical、Emergency。

Vx-only DPK 的一般下載 QR 無法直接建立 Mission。若誤用 `Clear Database`，任務會被移除，須重新下載；替換失敗時使用作業備份復原。

![Vx 套件佈建入口](../../images/console-task-04-vx.png)

圖 7：產生套件後先預覽，再確認替換固定名稱的伺服器套件。

![ATAK Vx 四頻道清單](../../images/atak-vx-four-channel-pool.jpg)

圖 8：裝置下載後，TAK Voice 應顯示四個可加入的頻道。

<a id="task-10"></a>

## 任務十　管理 Vx 語音登入

1. 在「Mumble 管理 → 線上連線」選 session 並按「中斷選取的連線」；該身分仍可再次登入。
2. 要移除已記住的身分，到「已註冊身分」勾選並確認刪除。系統會先備份資料庫；有效共用密碼仍可讓使用者重新註冊。
3. 「重新啟動 Mumble」保留頻道與註冊資料；「重設共用密碼並重新啟動」會改本機 secret。兩者都會中斷線上連線。

驗收線上／註冊清單及 Vx 重登。TAK 憑證撤銷不等於 Mumble 停用；已註冊 Vx 身分在改密碼後仍可能直接登入。

![Mumble 線上與註冊清單](../../images/console-task-10-mumble.png)

圖 19：線上 session 和已註冊身分分開管理；截圖時沒有線上連線。

![Mumble 伺服器控制](../../images/console-task-10b-server-controls.png)

圖 20：重新啟動與重設密碼是不同操作，皆會中斷連線。

[返回任務索引](../console-task-manual.md)
