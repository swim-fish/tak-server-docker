# TAK 憑證信任設計報告

本報告供本機 TAK 5.8 測試環境的管理人員核對憑證信任鏈、撤銷邊界與中繼 CA 替換結果。結論是：撤銷舊中繼 CA 時，除了發布 Root CRL，還必須檢查 TAK 信任憑證鏈資料庫是否仍把舊中繼 CA 當成直接信任錨。2026-09-25 的實測中，移除該項目並重啟後，舊裝置憑證的新 8089 連線才遭拒絕。

本次文件更新日期為 2026-09-26。新增的控制台圖片用來說明現行介面，沒有重新執行 CA 替換。證據範圍包括 OpenSSL、TAK 8089、兩台 Android 的群組路由、A 裝置的舊／新 DPK 與 Vx，以及憑證控制台的瀏覽器操作；8443 與完整自動輪替仍須另行驗收。

## 信任鏈與服務分工

Root CA 簽發中繼 CA，中繼 CA 再簽發 TAK Server、Mumble、MediaMTX、管理員與裝置的獨立葉憑證。服務不共用私鑰；伺服器葉憑證的 SAN 要對應用戶端實際輸入的 DNS 名稱或 IP 位址。ATAK 的 TAK 連線 DPK 含裝置私鑰及信任資料，應以短效、限次 QR 交付。

![Root CA 中繼 CA 服務與裝置信任鏈](../images/certificate-trust-chain.png)

圖 1：Root、中繼 CA、獨立葉憑證與 ATAK／Vx 的信任邊界。

Vx 可利用 ATAK 個別 TAK Server 設定中的 CA 信任資料驗證 Mumble Server，但 Mumble 密碼與註冊身分是另一道登入機制。撤銷 TAK 裝置憑證不能視為已停用其 Mumble 身分。

![ATAK 與 Vx 語音登入的獨立驗證路徑](../images/tak-vx-authentication-boundary.png)

圖 2：TAK 憑證登入與 Mumble 語音登入需要分別停權與驗收。

## CRL 與直接信任錨

Root CRL 記錄中繼 CA 的撤銷；簽發中繼 CA 的 CRL 記錄其葉憑證的撤銷。兩層 CRL 有不同用途。平常只撤銷單張裝置葉憑證時，不應移除整個中繼 CA。

2026-09-25 的測試發現，只發布 Root CRL 後，8089 仍接受舊憑證的 TLS 交握。當 `truststore-root.jks` 與 `fed-truststore.jks` 不再直接信任 `tak-issuing-old`，並保留 Root 與新中繼 CA 後，舊憑證的新連線才遭拒絕。這是本次環境的觀察結果；若更換 TAK 版本或信任鏈組成，必須重新驗證。

![舊中繼 CA 留在信任鏈資料庫與移除後的對照](../images/ca-rotation-trust-anchor-comparison.png)

圖 3：Root CRL 已發布但舊 CA 仍為直接信任錨時，8089 的測試結果不同。

![中繼 CA 替換與裝置驗收時間軸](../images/ca-rotation-verification-timeline.png)

圖 4：從新 CA 上線、Root CRL 發布到裝置端重新登入的驗收順序。

目前 `CoreConfig.xml` 的 `security/tls/crl` 與用戶端憑證撤銷檢查用於 8089。8443 的 `network/connector` 尚未設定 `crlFile`，因此不能把 8089 的結果直接推論為 8443 已完成 TLS 層撤銷檢查。詳見[憑證與撤銷設定](../security/certificates.md)及[8443 驗證紀錄](../validation/2026-09-23-tak-crl-8443.md)。

## 實測結果與可見範圍

| 驗證項目 | 觀察結果 | 邊界 |
| --- | --- | --- |
| 舊 CA／舊 DPK | 移除直接信任錨後，舊憑證無法重新登入 ATAK | 驗證的是新的 8089 連線，不代表所有既有連線立即中止 |
| 新 CA／新 DPK | ATAK 可重新登入，Vx 的 Primary、Alternate、Medical、Emergency 四頻道可加入 | A 裝置的實機結果；其他版本應重測 |
| 短效裝置憑證 | Alpha 7 天與 Bravo 14 天憑證分別交付對應 DPK，ATAK 實機確認可連上 8089 | 已確認短效期憑證可用；未測試到期後的自動斷線行為 |
| 20 分鐘憑證到期 | 到期後的新 8089 TLS 連線收到 `certificate expired`；到期前建立的連線在不中斷的觀察期間，即使憑證過期仍能繼續收發資料 | 憑證到期不能當成即時中斷既有連線的措施；ATAK 畫面與手動重連結果另待確認。見[到期測試](../validation/2026-09-26-certificate-expiry-20m.md) |
| Mumble 既有身分 | 舊 TAK 憑證失效後，既有 Mumble 身分仍可登入 Vx | Mumble 身分須在 Mumble 管理頁另行處理 |
| 控制台憑證操作 | 重啟 Compose 後，瀏覽器簽發短效測試憑證、讀回群組並撤銷；CRL 包含該序號，新 8089 連線遭拒 | 該張瀏覽器測試憑證未匯入 Android |

![憑證清冊的篩選與識別資訊](../images/certificate-console-inventory.png)

圖 5：清冊用名稱、CN、CRL ID、狀態與到期資訊協助核對。圖中為 2026-09-25 的測試憑證，不能當成現行清冊。

![短效憑證的 ATAK 實機登入與獨立撤銷測試](../images/certificate-short-duration-verification.png)

圖 6：Alpha 7 天、Bravo 14 天憑證均經 ATAK 實機登入確認；下方撤銷流程使用另一張瀏覽器測試憑證，未對這兩張裝置憑證執行撤銷驗收。20 分鐘憑證另證實到期後新連線遭拒，而到期前建立的 TLS 連線只要不中斷，在觀察期間仍可繼續收發資料。這是[實測紀錄](../validation/2026-09-24-ca-rotation-device-baseline.md)的摘要圖，不是裝置截圖。

![不同驗證來源所能證明的範圍](../images/ca-rotation-evidence-layers.png)

圖 7：OpenSSL、TAK、Android 與瀏覽器的證據回答不同問題。

## 控制台操作與風險提示

「用戶端憑證 → CA 替換」可選擇要重簽的裝置，保留或調整其到期時間，並透過兩個確認核取方塊啟動替換。頁面已將舊憑證失效、服務憑證切換與既有連線中斷顯示為紅色高風險警告。圖片中的識別資料已遮蔽；擷取圖片時沒有再次執行替換。

![目前 CA 替換頁的紅色高風險警告與重簽欄位](../images/console-ca-rotation-1440.png)

圖 8：桌面版將警告置於重簽裝置清單上方。

![CA 替換頁的手機單欄排版](../images/console-ca-rotation-390.png)

圖 9：手機寬度仍可閱讀完整警告與重簽欄位。

控制台的「依群組檢視」可在不同 In／Out 清單間調整憑證，或從單一群組移除。它修改 TAK 群組授權，不能代替 CA／CRL 停權。所有變更先暫存，確認儲存後才寫入 TAK。

![依群組檢視的目前操作介面](../images/console-task-03-groups.png)

圖 10：群組頁的狀態篩選、隱藏空群組與每筆單一「移動」按鈕。

## 操作建議與後續驗收

1. 操作前核對本機備份、CA 指紋、舊／新 DPK 身分及 TAK 信任憑證鏈資料庫內容。
2. 切換時發布 Root CRL、移除舊中繼 CA 的直接信任項目並重啟 TAK；分別測試舊與新憑證的新連線。
3. 切換後逐台交付新 DPK，分開驗收 ATAK 與 Vx；如需停用語音，另處理 Mumble 註冊身分與密碼。
4. 8443 TLS 層 CRL 與完整自動輪替尚未在本輪文件更新中實測，應依[CA 輪替驗證紀錄](../validation/2026-09-25-ca-rotation-cutover.md)安排後續測試。

資料來源：[CA 輪替切換實測](../validation/2026-09-25-ca-rotation-cutover.md)、[瀏覽器簽發與撤銷](../validation/2026-09-25-certificate-browser.md)、[雙裝置群組基線](../validation/2026-09-24-ca-rotation-device-baseline.md)、[憑證操作說明](../tak-server/certificate-operator-guide.md)。
