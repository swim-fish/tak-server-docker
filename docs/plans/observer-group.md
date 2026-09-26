# TAK Server 觀察員群組計畫

> 狀態：設計草稿；尚未在本機 TAK Server 5.8 驗證 `In`／`Out` 分離的觀察員行為。本計畫不變更現有憑證或群組。既有 Alpha／Bravo CoT 隔離結果見[影像別名與 CoT 驗證紀錄](../../records/video-alias-sharing-validation.md)。

## 目標與範圍

讓隊員透過 TAK Server 將 CoT 資料提供給指定觀察員，而隊員不因觀察群組收到觀察員的資料。第一階段只處理 TAK Server 的 CoT 群組路由；Video Alias、Data Package、Mission、MediaMTX 觀看權限及區域網路廣播各有獨立存取路徑，不將 CoT 測試結果視為它們的授權證明。

本計畫的「觀察員不能寫入」先定義為**不能向觀察群組寫入**。若要求帳號完全不能向 TAK Server 發送任何資料，須另行驗證沒有 `In` 群組時的登入與 `__ANON__` 回退行為，並評估額外的伺服器端限制；不能只靠畫面上的 `Out` 群組推定全面唯讀。

## 群組配置

以 Alpha 為例，新增獨立的 `observe-alpha`。`team-alpha` 保留小隊原有的雙向溝通；`team-all` 是全體共用的具名群組，並非萬用字元。新憑證自動取得 `team-all` 的 `Out`，不因此取得 `In`。

| 身分 | `team-alpha` | `observe-alpha` | `team-all` |
| --- | --- | --- | --- |
| Alpha 隊員 | `In + Out` | 僅 `In` | 僅 `Out` |
| Alpha 觀察員 | 依需求決定是否僅 `Out` | 僅 `Out` | 僅 `Out` |
| 其他小隊 | 不加入 | 不加入 | 僅 `Out` |

觀察員不應取得 `observe-alpha` 的 `In`。若只要監看 Alpha，先不要賦予 `team-alpha` 的 `In`。若觀察員另有其他群組的 `In`，他仍可能向那些群組送出資料，須在清冊中明確顯示。

**資料流推論**：Alpha 隊員的 `In: observe-alpha` 與觀察員的 `Out: observe-alpha` 相交時，觀察員應收到隊員送往該群組的 CoT。隊員沒有該群組的 `Out`，不應因這個群組收到資料。這是待實機驗證的路由假設；一個連線擁有多個 `In` 群組時，可能將其所有 CoT 同時提供給多個群組，無法單靠群組設定挑選個別標記。

## 控制台規劃

1. 在小隊與 TAK 群組設定頁為每個小隊顯示對應的觀察群組，例如 `alpha → observe-alpha`。新增小隊時檢查名稱唯一性，避免與 `team-alpha`、`team-all` 或其他觀察群組重複。
2. 簽發隊員憑證時，清楚列出小隊群組 `In + Out`、觀察群組 `In`、`team-all` `Out` 的預設值；管理員可在簽發前檢查並調整。觀察員使用獨立憑證與身分，預設只有所選觀察群組及 `team-all` 的 `Out`。
3. 既有憑證不因變更小隊對應而自動修改。管理員先預覽受影響的憑證及權限差異，再批次套用；操作後從 TAK Server API 讀回每張憑證的實際 `In`／`Out` 群組。
4. 憑證詳細頁以明確標籤區分「隊員」與「觀察員」，並顯示所有其他 `In` 群組；介面不得把 `Out` 專用群組標成帳號全面唯讀。

## 驗證步驟

1. 在測試環境準備三張不同憑證：Alpha 隊員、Alpha 觀察員、Bravo 隊員。先查回各自的 `In`／`Out`，確認沒有非預期的 `__ANON__` 或共用 `In` 群組。
2. 以三條獨立的 TAK Server `8089` TLS 連線接收 CoT。Alpha 發送帶唯一 UID 的短效標記／位置事件，確認 Alpha 觀察員收到、Bravo 未收到；Alpha 隊員仍可透過 `team-alpha` 的既有權限互相看見。
3. 由觀察員嘗試發送唯一 UID 的 CoT，確認該事件沒有進入 `observe-alpha` 的接收端；同時檢查是否被導向 `__ANON__` 或其他群組。若可送入其他群組，紀錄為「觀察群組唯讀」，不可宣稱帳號全面唯讀。
4. 移除 Alpha 隊員的 `observe-alpha` `In` 後重送新 UID，確認觀察員不再收到；恢復原權限時也要查回群組清單。測試過程不撤銷憑證。
5. 讓 Android 裝置只保留一條 TAK Server 連線，避免舊 DPK／舊群組污染；必要時關閉區域網路廣播，區分 TAK Server 路由與同 Wi-Fi 封包。記錄伺服器 log、三端收到的 UID、時間與群組讀回結果。

## 驗收條件與限制

- Alpha 隊員的測試 CoT 到達觀察員，Bravo 不收到；撤掉觀察群組的 `In` 後，觀察員不再收到新事件。
- 觀察員送出的測試 CoT 不會以 `observe-alpha` 路由；若仍可能發送到其他群組，介面必須指出其權限範圍。
- `team-all` 只作為明確指派的 `Out` 群組；不得把觀察事件同時送入 `team-all`，除非管理員刻意選擇全體發布。
- CoT 群組隔離不等於 MediaMTX 影像讀取授權。Video Alias 清單若要提供觀察員，需另外測試 API 群組標記及 MediaMTX 讀取帳密／路徑規則。

## 參考

- [TAK Server 官方 User-Group Management 介面](https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/src/main/webapp/user-management/user_edit_groups.view.html)將使用者群組分成 In、Out、Both。
- [本機憑證與群組控制台歷史草稿](client-certificate-console-draft.md)記錄本專案採用的 `-ig`／`-og` 對應。實際資料流仍以上述雙向與反向測試為準。
