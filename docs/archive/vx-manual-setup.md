# Vx 手動設定的歷史畫面

> 本組截圖保留通訊埠移轉前的介面與操作順序。畫面中的 `64400` 已由 `40000` 取代；現行操作請讀[Vx 任務與頻道](../atak/vx-missions.md)。實測版本為 ATAK 5.7.0.15／Vx 2.1.0。

先在 Vx 新增 Mumble channel。

![在 Vx 選擇 Mumble channel 類型](../images/atak-vx-01-select-mumble.jpg)

輸入：

| 欄位 | 值 |
| --- | --- |
| Address | `takbox.local` |
| Port | `40000` |
| Password | `runtime/secrets/mumble_server_password` 的內容 |

![設定 Mumble server 位址、通訊埠與密碼](../images/atak-vx-02-configure-mumble-server.jpg)

> 此截圖拍攝於通訊埠移轉前，畫面中的 `64400` 是歷史值；目前請依上表輸入 `40000`。

選取由 provisioner 建立的 `Primary` 頻道。Channel 不可留空，也不要只使用 Mumble 的 `Root`。

![選取 Primary 頻道](../images/atak-vx-03-select-server-channel.jpg)

設定最多 10 個字元的 alias，例如 `P1`。

![設定頻道 alias](../images/atak-vx-04-set-channel-alias.jpg)

儲存後，Channel Pool 會顯示 server 與實際 Mumble 頻道。

![已儲存的 Vx Mumble channel](../images/atak-vx-05-saved-channel-profile.jpg)
