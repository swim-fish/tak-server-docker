# TAK Video Alias 分享與播放實測

測試日期：2026-09-25。環境為本機 TAK Server 5.8、MediaMTX 1.21.1、ATAK CIV 5.7.0.15；Android 播放端為 Alpha 平板。本紀錄只列連線結構，不包含影像讀取密碼、完整 XML 或含定位資訊的實機截圖。

## 上傳與讀回

ATAK 的 **Send Video Alias** 對應 `POST /Marti/vcm`，內容是 `<videoConnections><feed>…</feed></videoConnections>`；下載清單使用 `GET /Marti/vcm`。本機 ATAK 來源碼的 `PostVideoListOperation`、`GetVideoListOperation` 與 `VideoXMLHandler` 可核對請求格式。

原有 Video Alias 測試資料（實際別名為 `V1`，與 API 版本無關）由 ATAK 上傳後，TAK Server 的 `video_connections` 資料表新增一筆 `VIDEO` 類型紀錄，時間為臺灣時間 19:35:29。讀回欄位為 `rtsp`、`takbox.local:8554`、`/live/alpha/1/VIDEO_1`、`rtspReliable=1`。位址包含讀取帳號及密碼；此處不複製其值。

另建立 `Synthetic RTSP Video 20260925` 測試別名，指向 `rtsp`、`takbox.local:8554/test`，設定 `rtspReliable=1`。使用相同格式向 `POST /Marti/vcm` 上傳，回應 HTTP 200；隨後 `GET /Marti/vcm` 回應 HTTP 200，依 UID 找到一筆，欄位讀回一致。

## 模擬影片與 ATAK 播放

FFmpeg 在獨立 Docker 容器向 MediaMTX 的 `test` 路徑發布 640×360、15 fps 的移動測試圖案，位元率設定為 900 kbps。MediaMTX API 回報 `test` 路徑 ready；獨立讀取端使用 RTSP／TCP 成功解碼 30 個影格，並擷取到彩色測試圖案。

播放端 ATAK 從 TAK Server 下載 `Synthetic RTSP Video 20260925` 後，設定畫面顯示 `rtsp`、`takbox.local:8554/test`、已填的讀取帳密及已勾選的 Reliable P2P Connection。臺灣時間 20:10:11 的 ATAK log 記錄 `discovered track: FORMAT_VIDEO`；使用者確認畫面出現移動的彩色測試圖案。裝置上 20:10:54 與 20:11:04 的兩張系統截圖分別保存設定及播放結果；原圖含地圖位置資訊，沒有納入 Git。

驗證結果：**Video Alias 上傳 TAK Server、由 ATAK 下載、再透過 MediaMTX 播放模擬影片，完整通過。** 這個流程是伺服器影像清單的同步；不等於把同一份別名作為即時 CoT 推送給所有用戶端。19:35 之後的 CoT 路由歷史未找到 Video Alias 測試資料、RTSP 或 `ConnectionEntry` 的新通告。較早的 ICU 自動影像 CoT 則有 `VIDEO_1`、`rtsps`、8322 與 `ConnectionEntry`，屬另一條流程。

## Group 權限：清單隔離實測

TAK Server 的 `video_connections.groups` 記錄群組位元。Video Alias 測試資料只標記 `team-alpha`；管理員上傳的模擬別名標記 `__ANON__`、`local-test`、`team-alpha`、`team-bravo`。先前 Alpha 播放端能下載並播放模擬別名；由於該別名同時屬於全部群組，單靠該次播放無法判定清單是否隔離。

同日續測以有效 Alpha 憑證 `7A992BAF`，以及新簽發、有效期一天的 Bravo 測試憑證 `7A992BB0`，分別經 mTLS 呼叫同一個 `GET /Marti/vcm`。TAK 管理 API 確認 Bravo 只有 `team-bravo` In／Out 群組。先讀既有資料，Alpha 回 HTTP 200 且清單含 Video Alias 測試資料；Bravo 也回 HTTP 200，但清單為空。接著由 Bravo 身分使用 `POST /Marti/vcm` 上傳不含帳密的 `BRAVO-ONLY-VIDEO-ALIAS-PROBE-20260925`，回 HTTP 200。再次讀取：

| 憑證身分 | `GET /Marti/vcm` | 清單中的別名 |
| --- | --- | --- |
| Alpha，`team-alpha` | HTTP 200 | Video Alias 測試資料 |
| Bravo，`team-bravo` | HTTP 200 | `BRAVO-ONLY-VIDEO-ALIAS-PROBE-20260925` |

資料庫群組位元讀回也確認 Video Alias 測試資料僅屬 `team-alpha`、新測試別名僅屬 `team-bravo`。因此**本機 TAK Server 5.8 的 Video Alias 清單與上傳歸屬，已通過 Alpha／Bravo 雙向群組隔離測試**。這項結論限於 `/Marti/vcm` 的別名清單；知道 RTSP 網址及帳密後，跨群組用戶仍可能直接向 MediaMTX 讀取影像，下節另有實測。MediaMTX 對 RTSP 讀取另行驗證帳密與路徑權限，不能把 TAK 群組當成影像播放授權。

由於 Video Alias 的位址可包含讀取密碼，將別名分享到某群組也代表該群組能取得這組密碼；ATAK 畫面雖以 `XXHiddenXX` 或圓點遮蔽，不能視為密碼未交付。

## 跨群組播放與 CoT／DPK QR（續測）

以短暫的 FFmpeg 容器在 `live/alpha/1/VIDEO_1` 發布 640×360、15 fps 的合成 H.264 影像。從與 TAK Server 身分無關的獨立 Docker 網路，不帶 TAK 用戶端憑證、只使用 MediaMTX 的 `atak-viewer` 觀看帳密，以 RTSP／TCP 成功讀到 H.264 與正確解析度；同一路徑使用錯誤密碼時讀取失敗。這證明**知道 RTSP 路徑及有效觀看帳密者，即使沒有 Alpha 的 TAK 群組身分，仍可直接播放影像**。MediaMTX 不會從 RTSP 讀取請求取得 TAK 憑證群組。

另簽發一天效期、只含 `team-bravo` In／Out 群組的測試憑證 `7A992BB1`。用 Alpha、Bravo 兩條有效 TLS 連線接收 CoT，分別從同群組憑證送出短效 `b-i-v` 影像事件，內含 `__video/ConnectionEntry`，但不含觀看帳密。每一筆測試 UID 監看 8 秒：

| CoT 發送身分 | Alpha 接收 | Bravo 接收 |
| --- | --- | --- |
| Alpha | 有 | 無 |
| Bravo | 無 | 有 |

因此伺服器端對這種 Video CoT 也按群組路由；它與 `/Marti/vcm` Video Alias 清單是兩條不同途徑。另發送有效約 10 分鐘的新 Alpha CoT 後，使用者在 Alpha 平板 ATAK 看見 `ALPHA-COT-GROUP-PROBE`。該項目無法播放，符合這筆 CoT 不含觀看帳密的設定；CoT 傳遞成功不等於 RTSP 已獲授權。

另外依 ATAK 5.7.0.15 的 `ImportVideoAliasResolver` 與 `MissionPackageEventHandler2` 格式，建立含 `video/alpha-cross-group.xml` 的 DPK：Manifest 設 `onReceiveImport=true`，內容 `contentType=Video Alias`，XML 為 `<videoConnections><feed>`。別名 `ALPHA-DPK-CROSS-GROUP-20260925` 指向相同的 Alpha RTSP 路徑，開啟 `rtspReliable=1`，並包含已獲授權用於這次測試的 MediaMTX 觀看帳密。透過 `tak://com.atakmap.app/import?url=...` QR，在目前 Wi-Fi 建立 20 分鐘、最多 3 次下載的分享；分享紀錄顯示完成 1 次下載。第二支手機使用 Bravo 測試憑證登入後掃碼匯入，使用者確認看到了測試影像，MediaMTX 另記錄 RTSP／TCP 讀取。此時以同一張 Bravo 憑證讀取 `GET /Marti/vcm` 仍回 HTTP 200 **空清單**。因此 **DPK QR 可把 Alpha 影像的連線資訊直接交付給 Bravo 裝置，繞過 TAK Video Alias 清單的群組可見性限制**；實際播放仍取決於 DPK 交付的 MediaMTX 帳密與網路可達性。

測試 DPK 及分享快照含可重複使用的觀看密碼，測試期間只存於 Git 忽略的 `runtime/`，沒有加入版控。關閉 QR 分享不會讓已匯入 ATAK 的影像連線資訊消失；若要停止其 RTSP 播放，必須在 MediaMTX 停用或輪替觀看帳密。含密碼 DPK 完成一次下載與播放驗證後，QR 分享與先前不含密碼的試作 QR 均手動停止，兩份分享快照、工作區中的 DPK 與 QR 圖檔也已刪除；下載次數紀錄保留。

Bravo 手機的三張 20:51–20:54 實機截圖補強結果：影像清單有 `ALPHA-DPK-CROSS-GROUP-20260925` 及 `BRAVO-COT-GROUP-PROBE`，沒有 `ALPHA-COT-GROUP-PROBE`；連線畫面顯示 Alpha DPK 別名使用已遮蔽的 `atak-viewer` 帳密、`8554` 與 `?tcp`；播放畫面顯示彩色合成影像。使用者另確認 Alpha 平板看得到 `ALPHA-COT-GROUP-PROBE`，但因該 CoT 未帶帳密而無法觀看。Bravo 清單還有 `VIDEO_1`；此圖只能證明該裝置曾收到這個項目，不能單憑畫面判定它是 TAK Server 跨群組路由、ICU 自動通告，還是區域網路傳播。原始截圖含精確地圖位置與呼號，未加入 Git。

實測完成後停止合成影像容器。

## 測試資料清理

模擬發布容器已停止並移除。對測試別名嘗試 `DELETE /Marti/vcm/{uid}` 回 HTTP 500；因此在已授權可更動的本機測試資料庫中，只刪除 ID 2、名稱完全相符的測試別名。再次 `GET /Marti/vcm` 確認測試別名已消失、原有 Video Alias 測試資料仍在。此 HTTP 500 需另行診斷，不能將直接資料庫刪除當成正式管理流程。

續測的 Bravo 專屬別名未重試已知會回 HTTP 500 的刪除 API；在本機測試資料庫以 ID 3 與完整別名雙重條件刪除，回報刪除一筆。TAK 重啟並恢復健康後，Alpha 仍可從清單讀到 Video Alias 測試資料。

一般 Video Alias、CoT 與 DPK 功能測試只清理暫時別名、串流及分享。撤銷憑證僅用於 CA 輪替或明確以憑證撤銷為目標的測試，不作為例行清理步驟。

## 相同 UID 取代上傳（2026-09-26 續測）

在健康的本機 TAK Server 5.8，以管理員憑證對 `POST /Marti/vcm` 送出不含帳密的一次性測試別名；開始前資料庫只有既有的 Video Alias 測試資料。第一次上傳路徑 A 回 HTTP 200，新增一筆資料。第二次保持 `uid` 與 `alias` 不變，只把路徑改為 B，回 HTTP 200；資料庫仍是**同一筆 ID**，`GET /Marti/vcm` 也只讀回一筆，路徑已更新為 B。第三次保持 `alias` 不變、改用新的 `uid` 與路徑 C，回 HTTP 200，資料庫變成兩筆同名別名。因此**取代的鍵是穩定的 UID，名稱相同不足以取代**。

對新建測試別名呼叫 `DELETE /Marti/vcm/{uid}` 仍回 HTTP 500。兩筆一次性測試資料已用 ID、UID 與別名三重條件從本機測試資料庫清除；最後再次由 API 讀回，僅剩原本的 Video Alias 測試資料，TAK Server 維持 healthy。這次沒有撤銷任何憑證。舊版流程的刪除仍有問題；下節另外驗證 OpenAPI Video V2 的建立、更新與刪除。

## OpenAPI Video V2 端點（2026-09-26 續測）

`vendor/openapispec.json` 由使用者從官方下載；其 SHA-256 與官方 `5.8-RELEASE-66/openapispec.json` 相同。本機運行的 hardened 版本為 `5.8-RELEASE-84`，官方版本清單沒有相應的 84 規格。這份規格未列舊版 `/Marti/vcm`，但列出 `/Marti/api/video` 的 GET／POST 及 `/Marti/api/video/{uid}` 的 GET／PUT／DELETE。唯讀 GET 在本機 84 回傳原有 Video Alias 測試資料，證明 V2 清單也會顯示舊資料；但以 V2 GET 查詢舊版建立的單一 UID 回 404，V2 DELETE 該 UID 雖回 HTTP 200，舊資料仍存在。**不能用 V2 DELETE 的 200 回應當成舊版別名已刪除的證據。**

另以 `POST /Marti/api/video?group=team-alpha` 建立不含密碼的一次性 V2 JSON 別名，回 HTTP 200，資料寫入 `video_connections_v2`，群組位元與已知只屬 `team-alpha` 的 Video Alias 測試資料相同。對其 UID 用單筆 `VideoConnection` JSON 執行 PUT，回 HTTP 200；GET 及資料庫均讀到更新後的 feed URL，同一筆 ID 與群組位元保持不變。最後 V2 DELETE 回 HTTP 200，資料庫確認該 V2 UID 已移除。V2 POST 使用集合物件 `VideoCollections`，PUT 使用單筆 `VideoConnection`；若把集合物件送給 PUT，即使 HTTP 200 也不會更新預期的 feed。多群組參數與 ATAK 對 V2 別名的下載行為尚未驗證。

## 移除既有 Video Alias 測試資料（2026-09-26 續測）

先確認 Video Alias 測試資料的 UID 為 `9294badd-2289-4b3e-beea-f74243982276`，位於舊版 `video_connections`（ID 1），而 `video_connections_v2` 為空。V2 清單 `GET /Marti/api/video` 回 HTTP 200 且包含 Video Alias 測試資料；V2 單筆 `GET /Marti/api/video/{uid}` 回 404。依要求呼叫 V2 `DELETE /Marti/api/video/{uid}`，回 HTTP 200，但隨後 V2 清單仍包含 Video Alias 測試資料，資料庫中的舊版紀錄也仍存在。V2 DELETE 無法移除這筆舊版別名。

舊版刪除端點先前已實測回 HTTP 500，因此在已授權更動的本機測試資料庫，以 ID、UID、名稱三項條件確認唯一目標後移除 Video Alias 測試資料。刪除後，`GET /Marti/api/video` 與 `GET /Marti/vcm` 均回 HTTP 200 且不含 Video Alias 測試資料；兩個影像資料表均為空，TAK Server 保持 healthy。此次沒有撤銷憑證。

## Video V2 別名供 ATAK 實機檢查（2026-09-26）

以 `POST /Marti/api/video?group=team-alpha` 發布無帳密的測試別名 `API V2 Alpha Test 20260926`，UID 為 `4cfa097c-798d-4cd8-8219-92232fe7f048`。回 HTTP 200，資料只寫入 `video_connections_v2`；群組位元只有一個啟用位元。用戶端身分 `ca-test-alpha-rotated-20260924` 的管理 API 群組清單為 `team-alpha`。V2 單筆查詢、V2 清單與舊版 `GET /Marti/vcm` 均回 HTTP 200 且包含該別名。使用者已在序號 `7A992BAF` 的 Alpha 裝置 ATAK 看見此別名，完成 V2 發布到 ATAK 影像清單的實機驗證。串流網址是 `rtsp://takbox.local:8554/live/alpha/1/VIDEO_1`，沒有讀取帳密；此次沒有驗證影像播放。

舊版 `GET /Marti/vcm` 的回應是 `<videoConnections><feed>` XML，`alias`、feed UID、`protocol=rtsp`、`address=takbox.local`、`port=8554`、`path=/live/alpha/1/VIDEO_1` 與 `rtspReliable=1` 均以子元素提供，符合本機 ATAK `VideoXMLHandler.parseFeed` 的解析方式。實機清單顯示也已由使用者確認。

## Video V2 同 UID 改選群組（2026-09-26）

使用不含帳密的一次性別名，先以 `POST /Marti/api/video?group=team-alpha` 建立一筆，再對同 UID 呼叫 `PUT /Marti/api/video/{uid}?group=team-bravo`。PUT 回 HTTP 200，但資料庫群組位元不變。接著以同 UID 對 `team-bravo` 再 POST，回 HTTP 200，資料庫變成**兩筆**相同 UID、不同群組的紀錄，並未取代原群組。`DELETE /Marti/api/video/{uid}` 回 HTTP 200，兩筆均被移除。

另測相同 UID 與相同群組集合重複 POST：資料庫維持一筆，單筆 V2 GET 與舊版 `GET /Marti/vcm` 均讀到第二次提交的路徑。`group=team-alpha&group=team-bravo` 可建立一筆帶兩個群組位元的別名，對相同 UID 與相同群組集合重送也維持一筆並更新內容。將原 UID 先 DELETE，再以新群組 POST，可建立僅屬新群組的一筆紀錄。全部一次性探針已透過 V2 DELETE 清除，原有 `API V2 Alpha Test 20260926` 保留供 ATAK 實機檢查。

## 控制台 ICU 雙人批次（2026-09-26）

新增 Windows 管理 worker 封裝的受限 Video V2 操作，以及「引導式佈建 → ICU 小隊批次交付」。以 Alpha／2–3 實際建立兩個別名、兩份限時限次 ICU QR。TAK V2 清單讀回 `ICU Alpha 2`（UID `ed535320-5ab7-5dc7-8eef-2ccb7d29a8a0`）與 `ICU Alpha 3`（UID `7a185030-23bb-5959-acb0-9af073cc6090`），每個 UID 恰好一筆，指向對應的 `live/alpha/<隊員>/VIDEO_1`。兩份分享 token 不同；QR 結果頁產生兩個 Carousel 項目，分享紀錄以共同批次 ID 關聯。先前單人煙霧測試的 QR 已停止；雙人批次 QR 保留供實機驗收，會依期限或下載次數自行停止。

另將 Alpha／3 的目標群組從 `team-alpha` 改為 `team-all`，再改回 `team-alpha`；兩次 worker 操作均回完成，V2 清單都只讀回一筆該 UID。唯讀查詢 `video_connections_v2` 確認兩名隊員各有一筆紀錄，`groups` 都是長度 32768、只有第 32764 位為 1，與恢復後的 Alpha 群組位元一致。V2 清單本身不顯示足以獨立核對的群組位元；**尚未完成 ATAK 實機的群組可見性、ICU QR 匯入與串流播放**。沒有輸出任何 QR token、發布密碼、觀看密碼或私鑰，也沒有為清理作業撤銷憑證。

Playwright 使用本機 Chrome 與控制台 Basic 驗證開啟實際結果頁：初次發現 Jinja 將 `receipt.values` 誤當字典方法，造成小隊與路徑空白；改為鍵索引後，重新載入可見 `team-alpha`、`live/alpha/2/VIDEO_1`，按「下一位」切到 `live/alpha/3/VIDEO_1` 並更新為 `2／2`。手機寬度 390 px 可完整顯示 QR、倒數與前後切換按鈕；分享紀錄中的任一筆 QR 彈窗也顯示同批次 `2／2` 輪播。瀏覽器產生的含可用 QR 截圖僅供本機檢查，不納入版本控制。
