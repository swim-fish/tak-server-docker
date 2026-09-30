# Vx 行動網路介面判斷問題

2026-09-30 實測與 APK bytecode 分析確認：Vx 2.1.0 在只有行動網路、存在兩個 Cellular 介面項目時，會將兩者全部移出可用清單。Mumble 已登入，Vx 卻顯示 `Auto - Unavailable`，並將 PTT 設為錯誤狀態。

本次行動網路已成功連到 Mumble 的 `40000` 通訊埠，且有加密 UDP ping 往返。這份結果不能推廣成所有 4G／5G 都無法使用 Vx，也不能把登入或 ping 成功當作雙向語音驗收。接上可上網的 Wi-Fi 後，介面顯示與 PTT 錯誤狀態已恢復；雙向音訊仍未測試。

## 適用版本與症狀

| 項目 | 本次環境 |
| --- | --- |
| Android | 16，API 36 |
| ATAK | `5.7.0.15 (b75ee790)` |
| Vx | `2.1.0 (20251122) - [5.6.0]` |
| Mumble 入口 | TCP／UDP `40000`；省略實際主機名稱 |
| APK SHA-256 | `512193d0d9f4463607a84fe036ecd0834cd186c6b4969f28b00b210a1c1ed45d` |

問題發生時，Android 預設行動網路已通過網際網路連線驗證，IPv4 介面包含 `rmnet_data0` 與 `rmnet_data2`。Vx 的 Network 選單卻只剩帶錯誤圖示的 `Auto`，沒有可選的 Cellular 項目。兩個行動網路介面可能來自不同網路連線情境；本次未確認其形成原因，不能據此判定為雙 SIM 問題。

版本與 APK hash 用來限定本次分析的對象。混淆後的 class／method 名稱可能隨版本改變，不能直接套用到其他 APK。

## 行動網路與 Wi-Fi 對照

下列時間均為 2026-09-30，時區 `Asia/Taipei`（UTC+08:00）。

| 檢查 | 僅行動網路 | 接上 Wi-Fi 後 |
| --- | --- | --- |
| 介面／路由 | IPv4 介面含 `rmnet_data0`、`rmnet_data2`，未見 Wi-Fi 路由 | 路由使用 `rmnet_data2`、`wlan0` |
| Vx Network 顯示 | `Auto - Unavailable` | `Auto` |
| Mumble 工作階段 | 09:03:35、09:07:46 有連線成功紀錄；伺服器確認驗證及加入頻道 | 09:20:10.206、09:20:10.373 各有一條連線成功紀錄 |
| PTT 錯誤狀態 | `true` | `false` |
| 雙向語音 | 未測試 | 未測試 |

Wi-Fi 切換後的去識別紀錄保留以下訊息，省略行程 ID、物件識別值及用戶端身分：

```text
09:20:09.707  Gained network interface default
09:20:10.206  Connection successful, joining new channel
09:20:10.207  PTT Error state: false
09:20:10.373  Connection successful, joining new channel
09:20:10.379  PTT Error state: false
```

手機紀錄與伺服器紀錄均確認行動網路工作階段已通過 Mumble 驗證並加入頻道；另有加密 UDP ping 往返。主機端以公開 CA 信任套件驗證服務憑證鏈與 hostname 也通過。這些證據支持介面判斷問題，未發現需要更換通訊埠、密碼或服務憑證的依據。

## 介面篩選如何造成錯誤

在 `Latakplugin/vx/o80;->n()V` 中，Vx 先計算類型為 `WIFI` 或 `CELL` 的介面項目數。數量達到 2，就透過 `n80` predicate 移除所有 `CELL` 項目；這個條件沒有要求存在 Wi-Fi。

以下為 bytecode 邏輯摘要，並非上游原始碼：

```text
if count(entries where type is WIFI or CELL) >= 2:
    remove all entries where type is CELL

Auto.available = any remaining non-DEFAULT entry is available
```

因此，兩個 `CELL` 項目就足以觸發移除。沒有 Wi-Fi 時，清單只剩無可用實體介面支持的 `Auto`。UI 隨後將 PTT 標成錯誤，即使底層 Mumble 已登入。

| bytecode 位置 | 判讀 |
| --- | --- |
| `o80.n()`，offset `0x0060`、`0x0062` | 比較 `WIFI`／`CELL` 項目數是否至少為 2 |
| `o80.n()`，offset `0x0074` | 呼叫 Kotlin `removeAll`，使用 `n80` predicate |
| `n80.invoke` → `o80.c(a80)` → `o80.o(a80)` | predicate 判斷介面類型是否為 `CELL` |
| `o80.n()` 後半段 | 依剩餘非 `DEFAULT` 項目的可用狀態更新 `Auto` |
| `gs0.Z(t6,v6)`，offset `0x00aa`、`0x00ee` | 介面不可用時呼叫 `x7.p1(true)`，並附加 ` - Unavailable` |

這條程式路徑與實測相符：只有兩個 Cellular 項目時出錯；接上 Wi-Fi 後有可用介面留在清單，畫面與 PTT 錯誤狀態恢復。

## 重現與後續驗收

重現時需使用同一版本 Vx，保留既有 Mumble 設定，並使用可正常上網的行動網路：

1. 關閉 Wi-Fi，確認 Android 有至少兩個 IPv4 Cellular 介面項目。
2. 開啟 Vx 頻道，記錄 Network 顯示、選單選項及 PTT 錯誤狀態。
3. 核對手機與伺服器紀錄是否已登入及加入頻道，分開判讀登入失敗與介面不可用。
4. 接上可上網的 Wi-Fi，以相同 Mumble 設定再次觀察 Network 與 PTT 狀態。

本次未清除 ATAK 資料、修改 Vx 設定或變更伺服器設定，也未按下 PTT 傳送語音。原始 logcat、UI dump、路由與反組譯檔案留在受控診斷資料夾；本頁只收錄去識別結果。

暫時可改用 Wi-Fi；本次實測已解除介面與 PTT 錯誤。修正行動網路支援需由 Vx 維護者調整篩選條件：多個 Cellular 項目不能單獨觸發全部移除；若要優先使用 Wi-Fi，應確認 Wi-Fi 可用，並保留行動網路作為備援。本次沒有修改 APK，也未驗證其他 Vx 版本是否已修正。

維護者修正後應覆蓋下列情境。表中的結果是驗收要求，尚未在修正版上執行：

| 情境 | 修正版應符合的行為 |
| --- | --- |
| 單一 Cellular，無 Wi-Fi | 保留可用 Cellular 項目 |
| 多個 Cellular，無 Wi-Fi | 至少保留可用的行動網路選項，`Auto` 不因項目數量而失效 |
| 可用 Wi-Fi 與 Cellular 並存 | 可以選用 Wi-Fi；保留行動網路備援 |
| Wi-Fi 不可用，但 Cellular 可上網 | 使用可用 Cellular，不將 `Auto` 判為不可用 |
| 從 Wi-Fi 切回行動網路 | 重新判斷介面並恢復可用狀態 |

介面狀態修正後，仍須以第二個用戶端完成[雙向音訊驗收](README.md#待完成的實機驗收)，確認 PTT 傳送／接收、頻道隔離及實際媒體傳輸。
