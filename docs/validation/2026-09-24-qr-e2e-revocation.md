# 2026-09-24 QR 佈建與憑證撤銷實機驗證

本次使用 Windows 熱點、TAK Server 5.8 Hardened、Mumble 1.5.915、MediaMTX 1.21.1，以及清除 ATAK 資料後的 Android 實機。Android UI 由使用者操作；主機只讀取 Android log、伺服器紀錄與使用者已儲存的系統截圖。原圖及 QR 測試檔留在 Git 忽略的 `runtime/validation/2026-09-24-qr-e2e/`，不公開裝置識別碼、呼號、定位或下載 token。

## 佈建順序與結果

| 步驟 | 觀察結果 |
| --- | --- |
| Compose 與 mDNS | TAK、資料庫、Mumble、MediaMTX、分享管理與公開下載服務啟動；`takbox.local` mDNS 回答熱點位址。 |
| 新憑證與 TAK DPK QR | 中繼 CA 簽發獨立用戶端憑證，加入 `local-test` 的 In／Out 群組；短效 QR 下載完成 1 次。使用者確認 `takbox.local:8089:ssl` 已連線。撤銷前，同一憑證可建立 8089 TLS 連線。 |
| Vx 四頻道 | TAK Server 既有 `ATAK Local Voice` 套件的 SHA-256、`tool=public`、`keywords=["missionpackage"]` 均與本機一致。修復 8443 可達性後，Android log 記錄查得 1 筆 Mission Package、`sharing.downloaded`、解析 1 筆 Protobuf Mission 並建立 `vx-local`；使用者確認 Primary、Alternate、Medical、Emergency 均能加入。這未驗證雙向 PTT 音訊。 |
| ICU QR | 獨立短效 `icu://download?url=...` QR 將 ICU 設為 `takbox.local:8322`、`live/`、RTSP-Push、SSL 開啟；使用者確認串流啟動，MediaMTX 記錄 `live/VIDEO_1` 經 RTSPS 發布且 1 軌 MPEG-TS 在線。 |

簽發後第一次註冊曾因 TAK 的 8089 監聽埠先於管理 API 就緒而被標為「註冊未驗證」。當時共用驗證檔與稍後的 API 都能讀到正確指紋及群組；控制台已改為在重啟後等待 API 讀回。使用同一張憑證重試群組註冊即成功，沒有簽發第二張。

## 8443 對 ATAK Data Packages 的影響

起初 Windows 的 `.env` 將 TAK HTTPS 對外映射到 `10043`，所以 8089 CoT 可連線，但 ATAK 的 `MissionPackageDownloader` 固定請求 `https://takbox.local:8443/Marti/sync/search?keywords=missionpackage`，Android log 顯示對 `192.168.137.1:8443` 連線逾時。這不是套件標籤或 In／Out 群組錯誤：以新憑證直接查詢相同伺服器 API 已可見套件。

重開機後 Windows 的 TCP 排除範圍已不含 8443，且沒有程式占用，因而把本機 `.env` 的 `TAK_HTTPS_HOST_PORT` 改回 `8443` 並重建 TAK 容器。TAK 健康後，ATAK 查詢加入 `tool=public`，回傳 1 筆套件並成功下載。未來若 8443 再被 Windows 保留，不能只改 Docker 對外通訊埠而期待 ATAK 的 Data Packages 功能正常；必須讓裝置可連到 `takbox.local:8443`。

## Vx 資料清除與密碼提示

使用者指出快速略過 Vx 的 Mumble 密碼提示時可能無法連線，曾從 **ATAK Settings → Tool Preferences → TAK Voice Preferences → DATA → Clear Database** 清除 Voice 資料庫。系統截圖中的按鈕說明為 `Clear the voice database`。清除後 `vx-local` 任務消失，須再次由 TAK Server 的 Data Packages → Download 取得。這次沒有驗證它是否清除加密的 Mumble 密碼快取，不能把它當成密碼重設流程。

## 撤銷與清理

只撤銷本次新簽發的測試憑證；原有裝置憑證未撤銷。控制台先停止其 DPK QR，再由中繼 CA 更新 CRL 並重啟 TAK。檢查顯示 CA 資料庫標記撤銷、發布的 CRL 包含該序號，舊 DPK 連結回應 HTTP `410`。TAK 健康後，使用撤銷憑證重新建立 8089 TLS 連線得到 `certificate revoked`；撤銷前相同測試可連線。

使用者在 ATAK 關閉再開啟連線後，畫面顯示 `IO error; reconnecting`。Android log 紀錄 8089 串流短暫進入 up，隨即 `SSL Read fatal error` 並將連線狀態設為 false。這個畫面錯誤文字本身不指明 CRL 原因，因此與伺服器的 `certificate revoked` 握手結果合併判讀。

另以本次憑證對 8443 重新請求套件清單，TLS 回覆 `certificate unknown`，而撤銷前同一憑證可取得 HTTP 200；管理憑證在撤銷後仍可讀取 API。這是本機版本的一次實測，控制台仍只自動標示 8089 的撤銷驗證結果。ICU 分享已停止；QR 快照與本機原始截圖仍留在忽略版控的測試資料中。
