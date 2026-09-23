# Mumble 使用者與註冊身分

本頁適用於現行 Mumble 映像與實測 Vx 版本，見[版本表](../reference/versions-and-ports.md)。操作前先確認 [Mumble 服務](server.md)可達，且管理密碼檔存在。

## Vx 如何取得身分

裝置 APK 的 `h50.Q0()` 以 ATAK 呼號及 Vx 管理的 UUID 組成 `呼號---UUID`；`h50.s1()` 將它放入 Mumble Authenticate。呼號中的空白會經轉換，使用者不能把頻道 Alias 當成登入帳號。

登入成功後，`sq0.r()` 會在尚無註冊 ID 時送出自行註冊要求。伺服器允許時，建立註冊身分並綁定用戶端憑證。Vx 也有自行產生及保存用戶端憑證的程式；這與匯入 TAK CA 來信任 Mumble 伺服器是不同流程。

本次檢查的 Vx UI 與 DPK 都沒有 Username 欄位，無法任意指定 Mumble 帳號。改 ATAK 呼號不等於更換已註冊的憑證；預先建立一般 `user01` 帳號，也不會自動讓 Vx 使用它。

依據為本機 APK 的登入及註冊呼叫路徑；實測曾觀察到同一裝置的兩個註冊身分，各自加入 Primary／Alternate。不要把一個 Mumble ID 當成一位自然人的永久識別。

## 新增與驗證的區別

Mumble 支援由管理員註冊已連線使用者、允許用戶端自行註冊，或透過管理 API 預建帳號。本專案未啟用 ICE 管理介面；現有腳本提供查詢與取消註冊，未提供離線新增帳號命令。

一般 `serverpassword` 用於未識別為註冊使用者的連線。註冊身分驗證成功後，不再檢查這個共用密碼。更換伺服器密碼不會撤銷既有註冊資格；新用戶端和既有註冊用戶端應分開測試。原生協定的註冊與驗證邏輯見 [Mumble v1.5.915](https://github.com/mumble-voip/mumble/blob/v1.5.915/src/murmur/Messages.cpp)。

## 互動式取消註冊

若使用本機 Flask 管理頁，可依[分享與管理頁](../sharing/portal.md#mumble-管理)操作線上連線中斷、註冊身分刪除、搜尋與多選。管理頁把兩種操作分開；下方命令列腳本仍可獨立使用。

在專案目錄開啟一般 PowerShell／Windows Terminal，執行：

```powershell
.\scripts\Remove-MumbleUsers.ps1
```

需要 Python、Docker CLI、可存取 Docker Desktop 的帳號，以及正在執行的 `mumble` 服務。不必預先以系統管理員身分開啟終端機。腳本沿用 `runtime/secrets/mumble_superuser_password` 與 Root CA，驗證 TLS 憑證及 `takbox.local`；TCP 位址和通訊埠從本機 Compose 容器的實際對應取得。已變更憑證 DNS 名稱時，使用 `-ServerName <DNS_NAME>`。

| 按鍵 | 功能 |
| --- | --- |
| `↑`／`↓` | 移動游標，清單較長時自動換頁。 |
| 空白鍵 | 選取／取消目前使用者，可多選。 |
| `A` | 全選；永遠排除 `SuperUser`。 |
| `N` | 全部不選。 |
| Enter | 檢視選取清單；尚未執行取消註冊。 |
| `Q`／Esc／Ctrl+C | 在選取畫面取消操作。 |

清單顯示註冊 ID、名稱與目前連線數。檢查選取結果後，必須輸入大寫 `DELETE` 才會執行。沒有選取使用者或輸入其他文字時，不會取消任何註冊。只檢視清單時可執行：

```powershell
.\scripts\Remove-MumbleUsers.ps1 -ListOnly
```

取消註冊流程：

1. 核對目前容器、註冊名稱及驗證資料的指紋，避免操作到選取後已變更的身分。
2. 使用 SQLite 一致性備份保留完整 Mumble 資料庫，並驗證 `integrity_check`；失敗時停止操作。
3. 備份後再次核對選取身分，透過 Mumble 原生管理協定取消指定註冊。
4. 中斷所選使用者仍存在且身分相符的連線，不加入封鎖清單；核對取消結果及其他註冊身分。

備份、清單快照與操作紀錄存放在 Git 忽略的 `runtime/mumble-admin/`。資料庫備份含驗證資料，不能提交版控或公開分享。失敗時先檢視腳本回報的 `.operation.json`，確認是否已部分完成，再重新列出使用者；不要直接重跑舊選取。取消多個註冊與中斷連線不是單一原子交易。

這個操作取消 Mumble 註冊身分，保留頻道、伺服器憑證、CA 與 ATAK／Vx 設定。Vx 已儲存的密碼不會被清除；一般 server password 輪替後，取消註冊可用於重現密碼提示。使用者重新通過驗證後仍可能再次註冊，因此這不是永久停權或封鎖功能。若需還原完整資料庫，應先停止 Mumble，於維護時段處理；還原也會回復備份之後的其他資料變動。

## 成功判斷與復原

腳本應回報移除的 ID、中斷連線數、備份及紀錄路徑。再執行 `-ListOnly`，確認目標已移除。若用戶端重連後 ID 又出現，先查是否重新通過驗證並自行註冊；取消註冊沒有禁止新註冊的效果。

若需復原，保留 `.sqlite` 與 `.operation.json`，先停止操作並安排停機還原。不要把完整資料庫備份覆蓋到仍在執行的 Mumble，也不要在錯誤狀態下連續重試刪除。

依據：[互動腳本](../../scripts/Remove-MumbleUsers.ps1)、[管理程式](../../scripts/manage_mumble_users.py)、[取消註冊與密碼提示實測](../validation/2026-09-22-tak-vx-dpk.md#取消-vx-註冊身分以測試重新驗證)。
