# Vx 任務、頻道與密碼

先完成[ATAK 連線及 CA 匯入](connection.md)，載入 Vx，確認 Mumble 已有 `Primary`、`Alternate`、`Medical`、`Emergency` 頻道。本頁適用已實測的 Vx 2.1；版本及限制見[驗證索引](../validation/README.md)。

## 手動建立第一個頻道

在 TAK Voice 選擇或建立 Mission，新增 Mumble 頻道，填入：

| 欄位 | 本機預設 |
| --- | --- |
| Address | `takbox.local` |
| Port | `40000` |
| Channel | 選伺服器的 `Primary`，不可留空。 |
| Alias | `Primary`，只控制顯示名稱。 |

完成後選取該頻道，確認顯示 `takbox.local - Primary`，並以伺服器登入／加入頻道紀錄交叉核對。選擇頻道與開始麥克風傳送是不同動作。

手動設定的舊版實機截圖見[歷史畫面](../archive/vx-manual-setup.md)，其中舊通訊埠不可照抄。需要供其他部署重用時，可將**單一 Mumble 頻道**任務透過 Missions → 該任務 → Send Mission → Export 匯出，作為[產生器](../reference/vx-package-format.md)範本。

## 從 TAK Server 下載任務

建議分兩階段：TAK 憑證 DPK 可經 Local SD 或經實機驗證的 ATAK QR 匯入；Vx-only DPK 必須經 TAK Server 下載。已實測的一般 Local SD 匯入會解壓縮 Vx 檔案，但不觸發建立任務的 callback；重新安裝 ATAK、先載入 Vx 後也相同。

控制台的 **引導式佈建 → Vx 任務** 現可從已驗證的本機 Vx 範本產生四頻道 Vx-only DPK，預覽 SHA-256、Mumble 位址與頻道，並將 TAK Server 上所有顯示名稱**完全等於** `ATAK Local Voice` 的舊套件先按 SHA-256 備份，再按確切 hash 刪除。新套件上傳後會讀回檢查唯一同名結果、`tool=public` 與 `missionpackage` 標籤。若刪除後失敗，結果頁提供從本機備份恢復的操作；不會刪除其他名稱的套件。TAK 的一般 metadata API 寫入 `tool` 時使用原始 `public` 字串；帶 JSON 引號的字串在本機 TAK 5.8 會回 HTTP 500。Vx 部署與後續 Android 驗證見[引導式佈建驗證](../validation/2026-09-24-guided-provisioning.md)。

2026-09-23 另以 ATAK `tak://com.atakmap.app/import?url=...` QR 下載現行四頻道 Vx-only DPK。裝置收到檔案並由 Import Manager 處理，但 TAK Voice 未新增 `vx-local`；該 QR 路徑仍不能當成下列 TAK Server Download 的替代。TAK 連線憑證 DPK 的 QR 匯入則已連線成功，兩種 DPK 必須分開判定。

1. 管理者先[產生 Vx-only DPK](../reference/vx-package-format.md#產生-vx-only-套件)，確認不含裝置私鑰或密碼。
2. 管理者將套件上傳到 TAK Server；可先加入 ATAK 的 Data Packages 清單，再選 Send → Select Server → 本機 TAK Server。傳送目標是自己的伺服器，不選 Contact。也可使用伺服器 `/Marti/sync/upload` API。上傳後確認檔案 SHA-256、`tool=public` 及 `keywords=["missionpackage"]`；缺少關鍵字時，ATAK 的 public 清單可能顯示 `No results available`。本機 Import 只完成檔案處理，不以 Mission 是否出現判定成敗。
3. 點 Download → 同一台 TAK Server，選對套件名稱，下載並確認完成。
4. 開啟 TAK Voice → Missions，確認目標任務出現，開啟並選擇預期頻道。需要時輸入密碼。

ATAK 的 Data Packages 下載器會查詢 `https://takbox.local:8443/Marti/sync/search?keywords=missionpackage`。`8089` 顯示已連線仍不足以證明此查詢可達；若畫面在 Querying 後退出或清單為空，先查 Android log 是否為 8443 逾時，並確認 Docker 對外映射及熱點防火牆。2026-09-24 實測中，把 HTTPS 主機通訊埠從 `10043` 恢復到 `8443` 後，原本已有正確 `missionpackage` 標籤的套件才出現在清單，見[當日紀錄](../validation/2026-09-24-qr-e2e-revocation.md)。

成功條件是任務、Channel Pool 與連線資料均正確；真正登入還需看到 Mumble 驗證成功及加入目標頻道。下載本身不會證明麥克風已啟動。

若任務未出現，先確認走的是 Server Download，並檢查紀錄是否收到 `sharing.downloaded` 及處理 Protobuf Mission。不要先重設整個 ATAK；比對名稱／套件 SHA-256 與[格式參考](../reference/vx-package-format.md)。重建套件會產生新 UUID，可能新增同名任務；既有同 UUID 的覆寫規則尚未驗收。

## 輸入密碼

Vx 在嘗試連線時可能顯示 **Enter Password for takbox.local**。此時使用 `runtime/secrets/mumble_server_password`；不可填 SuperUser 或 PKCS#12 密碼。

![Vx Mumble 密碼對話框，密碼欄空白](../images/atak-vx-06-enter-mumble-password.jpg)

圖為 2026-09-22 實機對話框裁切，只保留主機名稱與空白密碼欄。已儲存密碼時可能直接登入；已註冊身分通過驗證時，也可能不再檢查共用密碼。

Vx 的加密密碼快取以主機字串索引，不含通訊埠。刪除 Mission 不等於清除密碼；一般 `.pref` 也不能直接建立此加密快取。更換伺服器密碼後仍登入，先看[註冊身分](../mumble/users.md)，不要據此判定輪替失敗。

實機曾在快速略過密碼提示後無法連線。ATAK **Settings → Tool Preferences → TAK Voice Preferences → DATA → Clear Database** 可清除 Voice 資料庫，但也會移除 `vx-local`，之後必須再從 TAK Server 的 Data Packages 下載。尚未驗證此操作是否清除加密密碼快取；不要把它視為只重設 Mumble 密碼的按鈕。

## 多頻道與 PTT

一個 Mission 可放多個頻道，從 Channel Pool 快速切換；不必為每個頻道另建一個 Mission。現行 `atak-local-vx.dpk` 有 `Primary`、`Alternate`、`Medical`、`Emergency` 四個頻道。四頻道包已由 TAK Server Download 實機建立任務，且逐一加入 Mumble 對應頻道；舊雙頻道包另已確認兩個獨立 session 可同時加入 Primary／Alternate。

![實機 Vx vx-local Channel Pool 的四個頻道](../images/atak-vx-four-channel-pool.jpg)

2026-09-23 的四頻道包已由 TAK Server Download 建立任務，使用者逐一加入四個頻道，Mumble 伺服器也有對應的移動紀錄。截圖只保留頻道清單，不包含原畫面的地圖與定位資料；詳見[當日驗證](../validation/2026-09-23-qr-tak-vx-icu.md)。

- VS1、VS2 是兩個可選頻道的語音位置。
- PTT1、PTT2 的實體按鍵指派由 Vx 設定，DPK 產生器不代為設定。
- 多個 Channel Pool 項目不等於增加同時使用的語音位置。
- Channel Linking 涉及音訊轉送，本部署未自動啟用。

下載現行四頻道包後，先在 VS1 分別選取 `Primary`、`Alternate`、`Medical`、`Emergency`，再測 VS1=`Primary`、VS2=`Alternate` 同時連線。PTT 按鍵與雙向 UDP 語音需要第二個用戶端另行驗收；現有登入證據不能代替音訊測試。

依據：[Vx 下載與雙連線實測](../validation/2026-09-22-tak-vx-dpk.md)、[DPK 格式](../reference/vx-package-format.md)。
