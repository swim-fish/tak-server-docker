# 文件首頁

第一次部署請讀[從零建置](getting-started.md)。以下依工作分類，指令預設在專案根目錄執行；一般 PowerShell 即可，需管理員權限的步驟會另外標示。

## 找到要做的工作

| 工作 | 文件 |
| --- | --- |
| 從官方 ZIP 建立服務並連上 ATAK／Vx | [從零建置](getting-started.md) |
| 理解目前有哪些服務、哪些項目已驗證 | [架構與驗證狀態](architecture.md) |
| 設定、測試或移除 Windows 名稱解析 | [mDNS](network/mdns.md) |
| 啟用熱點與防火牆、處理重新開機後的連線 | [防火牆](network/firewall.md) |
| 理解憑證鏈、SAN、TAK 信任庫與更新 CRL | [憑證與撤銷](security/certificates.md) |
| 管理 TAK 服務、管理員與裝置使用者 | [TAK Server 維運](tak-server/operations.md) |
| 用控制台管理用戶端憑證、群組、DPK 與撤銷 | [用戶端憑證控制台](tak-server/certificate-console.md) |
| 啟動 Mumble、建立頻道或更換密碼 | [Mumble Server](mumble/server.md) |
| 啟動 RTSP／RTSPS 影像服務、設定 TAK ICU | [MediaMTX](mediamtx/server.md) |
| 用 QR Code 佈建 TAK ICU 影像發布設定 | [ICU QR Code](mediamtx/icu-qrcode.md) |
| 查看即時影像、公開 WebRTC 開關及管理小隊／設備發布身分 | [MediaMTX 管理](mediamtx/management.md) |
| 分享 ICU 設定或 ATAK DPK／ZIP，管理 Mumble | [分享與管理頁](sharing/portal.md) |
| 單筆／批次簽發 TAK 憑證、替換 Vx 任務套件 | [引導式佈建計畫與現況](plans/guided-provisioning.md) |
| 查詢或取消 Mumble 註冊身分 | [Mumble 使用者](mumble/users.md) |
| 匯入 TAK 連線與裝置憑證 | [ATAK 連線](atak/connection.md) |
| 設定 Vx、下載任務或使用多頻道 | [Vx 任務與頻道](atak/vx-missions.md) |
| 排查無法連線、憑證或密碼提示 | [疑難排解](troubleshooting.md) |

## 查設定與格式

- [目錄、runtime 與 secrets](reference/runtime-layout.md)：哪些檔案來自官方套件、哪些由腳本產生。
- [版本、通訊埠與上游套件](reference/versions-and-ports.md)：現行預設值的主要參考頁。
- [Vx DPK 格式與產生器](reference/vx-package-format.md)：給維護打包流程的人員。

## 查證據與後續工作

[驗證索引](validation/README.md)區分實機結果、程式碼分析與待驗項目。[後續計畫](plans/roadmap.md)收錄尚未完成的功能；[引導式佈建與分享計畫](plans/guided-provisioning.md)記錄目前控制台流程與尚待驗收的項目。[歷史資料](archive/README.md)保留原始設計與過時畫面，不作為現行操作指引。

文件使用臺灣正體中文；CLI、檔名、設定鍵與 UI 名稱保留原文。部署範例使用 `takbox.local` 與 Windows 行動熱點；不同環境請依[變更網路設定](network/mdns.md#變更名稱或網段)同步調整。

## 用語與主要參考

| 用語 | 本專案使用方式 |
| --- | --- |
| 用戶端／伺服器 | 說明 client／server；產品及 UI 名稱保留原文。 |
| 通訊埠 | port；數值集中於版本與通訊埠頁，任務頁只保留必要範例。 |
| 檔案／資料夾 | file／directory；runtime 與 secrets 用途集中於目錄參考。 |
| 信任庫 | truststore；CA、SAN 與 CRL 規則集中於憑證頁。 |
| Mission／Channel／Alias | 保留 Vx UI 字樣，中文分別說明為任務／頻道／顯示別名。 |
| 註冊身分 | Mumble registered user；與 TAK 裝置憑證及一般共用密碼分開。 |
| 驗證通過 | 表示測試成功，不改成表示方法或途徑的「透過」。 |

程式碼決定現行參數，日期紀錄支持實測結論；歷史計畫與未驗項目不能推導成已完成的功能。
