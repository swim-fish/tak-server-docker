# 引導式佈建與分享計畫

> 狀態：部分實作。MediaMTX、批次憑證及 Vx 伺服器端替換見[引導式佈建驗證](../validation/2026-09-24-guided-provisioning.md)與[MediaMTX 管理](../mediamtx/management.md)；本頁保留完整設計及未完成的驗收條件。現行其他功能見[分享與管理頁](../sharing/portal.md)、[憑證控制台](../tak-server/certificate-console.md)及[Vx 任務](../atak/vx-missions.md)。

2026-09-24 已完成引導頁的既有 TAK 憑證多選分享、新憑證批次簽發、ICU 標準／Advanced QR、一般設備發布身分與網址、Vx 固定名稱伺服器端替換；MediaMTX 小隊／設備權限管理、QR 再次發布、控制台同來源預覽、熱點匿名 WebRTC、公開觀看開關及工作階段數量即時更新。Android ICU Alpha／1 發布與 Chrome 觀看已驗證。批次新 DPK 的 Android 匯入、替換後 Vx 套件在既有 Android 的更新行為，以及外網公開 DNS／HTTPS／ICE 尚未完成；請勿把下方驗收條件視為已通過。

## 目標與已驗證基礎

將控制台的「新增分享」改為獨立的引導式頁面，讓管理者先選 **TAK Server 連線**、**ICU 影像發布**或 **Vx 任務**，再依選項完成設定、預覽、執行及結果檢查。分享紀錄與停止分享控制保留在控制台首頁。手機採單欄逐步操作；寬螢幕可並排顯示設定摘要，但不得略過確認步驟。

目前已有單張與批次用戶端憑證簽發、DPK QR、ICU 設定檔 QR，以及 Vx-only DPK 的產生器與 TAK API 替換流程。實機已驗證 TAK QR 連線、ICU QR 經 RTSPS 發布，以及先前 Vx 套件從 TAK Server Data Packages 下載後建立四個頻道，見[端對端紀錄](../validation/2026-09-24-qr-e2e-revocation.md)。**本次替換後新套件的 Android 下載與已安裝任務更新行為尚未驗證。**

## 共用頁面流程

1. **選擇用途**：三張明確的入口卡片，分別標示結果是 QR 分享或 TAK Server 套件發布。
2. **填寫設定**：只顯示所選用途需要的欄位；保留返回上一步時的資料。
3. **預覽與確認**：顯示目的地、檔案／路徑、分享期限與下載上限，並指出會簽發憑證或替換伺服器套件的操作。
4. **執行與結果**：逐項顯示成功、待驗證及失敗；提供對應 QR、檔案 SHA-256 或恢復操作。重新整理頁面不得重複簽發或重複刪除。

沿用現有本機管理頁的身分驗證與 CSRF。管理頁不直接持有 CA 私鑰或 TAK 管理憑證；需要簽發或操作 TAK Server 的工作交給 Windows 管理 worker。長時間工作必須有作業 ID、進度與可重試狀態。

## TAK Server 連線：既有憑證與單筆／批次簽發

管理者可從清冊選一張或多張**有效、已註冊且有對應 DPK** 的既有憑證，各自建立分享；已撤銷、過期或註冊未驗證者不得產生可用 QR。另一入口可新增單筆或批次憑證，每筆填裝置顯示名稱、唯一 CN、In／Out 群組；批次可套用共同群組後再逐筆調整。預覽列出每筆的 CN、群組及預期產物。

每張新憑證都要有獨立私鑰、PKCS#12、DPK、序號及分享 token。現行批次流程先檢查 CN 重複、CA 有效期、群組與 TAK 健康狀態；逐筆記錄簽發及註冊狀態，合併寫入驗證檔並重啟一次，再由 API 逐筆讀回。若中途失敗，保留已成功項目的結果與未完成項目的原因；重試接續既有作業，不盲目重新簽發同一 CN。還需在 Android 驗證新批次 DPK 匯入與登入，並在隔離環境演練 CA 已簽發但 DPK 寫入中斷等部分失敗情境。

每筆 DPK 顯示獨立 QR、序號、有效期限、分享倒數與下載次數。沿用目前短效、限次的預設值，並允許管理者在確認頁調整。DPK 含用戶端私鑰與密碼；頁面不顯示其明文，分享連結仍須限制在目前受控的本機熱點使用範圍。撤銷憑證時繼續停止對應分享。

## ICU：標準模式與 Advanced → ICU QR Code

MediaMTX Advanced 入口先讓管理者選擇 **ICU QR Code** 或 **一般設備（無人機等）**。選 ICU 時可自訂 Stream Path，產生 ICU 專屬 `.prefs` 及 `icu://download?url=...` QR；一般設備則走後述發布網址／QR 流程。標準 ICU 與 Advanced → ICU 兩種路徑設定互斥，均固定使用目前的 MediaMTX 主機與 RTSPS 通訊埠。ICU 帳號與密碼依**小隊**分配，組內人員共用該小隊的發布身分；管理者可在確認頁查看**預期**發布 URL，但不顯示發布密碼。

### 標準模式

組別可留空，或從 **Alpha、Bravo、Charlie、Delta、Echo、Foxtrot、Golf、Hotel** 選一項；人員代號可留空，或選 `1` 至 `10`。組別寫入路徑時轉成小寫。`Charlie` 是本計畫採用的 NATO 拼法。

| 組別 | 人員代號 | 寫入 ICU 的 `videoServerPath` | 預期 MediaMTX 路徑 |
| --- | --- | --- | --- |
| 空 | 空 | `live/` | `live/VIDEO_1` |
| Alpha | 空 | `live/alpha/` | `live/alpha/VIDEO_1` |
| 空 | 1 | `live/1/` | `live/1/VIDEO_1` |
| Alpha | 1 | `live/alpha/1/` | `live/alpha/1/VIDEO_1` |

### Advanced → ICU QR Code

只自訂 **Stream Path**，不接受完整 RTSP(S) URL，也不修改主機、通訊埠、TLS 或帳密。輸入範例為 `live/command-post/camera-2/`；欄位不得留空，必須以 `live/` 開頭及 `/` 結尾。路徑片段僅允許 ASCII 字母、數字、`-`、`_`，不得包含空片段、`.`、`..`、查詢字串或片段識別符。`live/` 本身有效。頁面應即時顯示預期路徑 `live/command-post/camera-2/VIDEO_1`，切換模式時不把標準模式的值悄悄覆蓋到 Advanced 欄位。

上述 `VIDEO_1` 是目前 ICU 7.5.1 實機觀察到自行附加的串流名稱；尚無證據可用 QR 設定其尾端名稱。引導頁已用 [ICU 路徑產生器](../../scripts/icu_profiles.py) 驗證標準與 Advanced 路徑，即時建立對應的短效設定分享；一般設備另有完整 RTSPS URL 的 Path 預覽。兩台裝置使用同一路徑可能互相衝突；仍須以兩台 ICU 同時發布不同路徑並分別讀取驗收。路徑名稱僅用來辨識影像來源；共用發布帳密時，它不代表人員身分驗證。

### 小隊與 Advanced 設備的發布身分

**ICU 依小隊、一般 Advanced 設備依單台設備管理 username、password 與 `publish` 路徑權限。** Alpha 至 Hotel 各有一組小隊身分；未選組別的 ICU 歸入 `Default` 小隊，仍按前表產生 `live/` 或 `live/<人員代號>/` 路徑。小隊帳號可發布該小隊已分配的路徑，不給整個 `live/` 的無限制權限。無人機及其他一般設備各有獨立帳密，只能發布指定的完整路徑。ICU 在 Advanced 分支自訂路徑時，仍使用所選小隊帳密，只把經確認的新路徑明確加入該小隊的允許清單，不擴大成所有 `live/` 路徑。匿名 WebRTC read 與管理用 read 帳號另外處理。[MediaMTX internal authentication](https://mediamtx.org/docs/features/authentication)支援按使用者設定 `publish` 與 path 權限；此版本的路徑比對及更新後工作階段行為仍須實測。

控制台分列「ICU 小隊」與「Advanced 設備」，顯示名稱、權限路徑、啟用狀態、所屬人員／設備數及最後發布狀態。支援搜尋、單選／多選／全選後**批次停用**與**批次重設密碼**；確認畫面逐項列出受影響的帳號、路徑與正在發布的工作階段。小隊密碼重設會使該小隊所有 ICU 舊設定失效，不能只撤銷小隊中的單一裝置；單台設備需要獨立撤銷能力時，應改用 Advanced 設備身分。密碼不出現在清單或一般日誌。

新增設定時先檢查路徑是否已分配；停用或輪替一個小隊／設備的密碼，不得影響未選取者或匿名觀看。若要求立即停用，除拒絕新登入外，也須驗證並終止已選帳號的現有發布工作階段。ICU 標準模式兩欄皆空時仍依要求使用 `live/`，但多台設備採同一路徑會競爭 `live/VIDEO_1`；頁面必須顯示重複警示，實際多設備部署應選不同組別／人員或 Advanced 路徑。帳號不同本身無法避免路徑衝突。

### ICU 小隊密碼重設與重新交付

管理者可單選或多選小隊重設密碼，先預覽受影響的人員設定及目前分享。作業先準備新的小隊密碼與每位人員的 `initial.prefs`，再更新 MediaMTX 授權、停用舊 QR 分享並終止舊帳密的發布工作階段；每個階段記錄結果，失敗時保留可接續的作業 ID，避免再次按鈕造成第二次輪替。尚未取得新設定的裝置須重新掃描並載入，才能以新密碼發布。

重新交付時由管理者設定**有效時間與最多下載次數**，兩者可同時設定、先到者停止；每份人員設定各有自己的下載 token、QR、倒數與次數，預設沿用目前 20 分鐘／3 次。期限與次數限制的是檔案**下載**，不是小隊密碼的有效期限。已停用的舊分享應回應不可下載；重設後驗收一台舊設定拒絕登入、同隊兩台新設定可分別發布、其他小隊持續可用。

每位受影響人員只產生一個 ICU 專屬 `icu://download` QR，指向含新小隊密碼與該人員路徑的 `initial.prefs`；**ICU 更新流程不產生 DPK**。管理者可逐筆顯示、複製或停止 QR。重新掃描並點開完整 `icu://download?...` 連結後，才以 ICU 欄位變更及 MediaMTX 發布紀錄判定更新成功。舊 QR 停用後不能再下載設定；裝置先前已下載的舊設定不會自動消失，但其中的舊密碼應在輪替後失效。

## MediaMTX：網際網路匿名 WebRTC 觀看

新增瀏覽器 WebRTC 觀看入口，讓網際網路上的觀看者**不需輸入密碼**即可開啟已發布的 `live/` 串流。控制台的「公開觀看」總開關預設為**開啟**，狀態須持久化；狀態同時區分「設定為開啟」「公開入口已就緒」「目前有影像」。目前 Compose 僅將 MediaMTX 綁定 Windows 熱點 `192.168.137.1`，`takbox.local` 也不是網際網路可解析的名稱，因此加入開關本身不會讓外網連通。公開入口正式就緒前，頁面應清楚顯示缺少的網路條件，不得把設定狀態誤報為外網可觀看。

### 串流與存取邊界

- 保留目前 MediaMTX 的 ICU RTSPS 發布帳密、`atak-viewer` 讀取帳密及內部路徑。規劃獨立的 **公開 WebRTC viewer 服務**，只從現有 MediaMTX 以受控帳號讀取允許公開的 `live/` 串流，對外只提供匿名讀取；不得提供匿名發布、TAK 控制台或 MediaMTX Control API。控制台預覽另走未對外發布、須管理頁驗證的內部觀看入口，使總開關只影響公開 viewer。先以單一路徑驗證拉流方式，再擴至動態路徑。若採同一 MediaMTX 實例的替代設計，必須證明匿名授權僅作用於 WebRTC read，不會讓既有 RTSP／RTSPS 讀取或發布變成匿名。
- 公開網址使用可由網際網路解析的 FQDN 與受信任的 HTTPS 憑證；不能沿用 `takbox.local`。HTTPS 入口只轉送 WebRTC 觀看所需路由，拒絕 publish／WHIP 與 API 路由。WebRTC 訊號入口與 ICE 媒體連線分開檢查：設定可由外網到達的 `webrtcAdditionalHosts`，配置固定 UDP ICE 通訊埠及必要的 TCP fallback、Router NAT 與 Windows 防火牆規則；若所在地無可連入的公開位址，須先規劃可用的中繼方案。這些條件依 [MediaMTX WebRTC 連線說明](https://mediamtx.org/docs/features/webrtc-specific-features) 驗證。
- 匿名且可由網際網路觀看，表示知道或猜到 `live/alpha/1/VIDEO_1` 等路徑的人都可能看到影像；標準模式的組別與人員代號是可預測的，不能當成存取控制。公開分享頁不得列出 TAK 用戶端憑證、ICU 密碼或內部 API 資訊。

### 控制台與開關

控制台新增「MediaMTX 即時串流」頁：由僅限 Compose 內部的 [Control API `GET /v3/paths/list`](https://mediamtx.org/docs/features/control-api) 取得目前路徑、在線狀態、來源、軌道與觀看人數；只列出實際在線的 `live/` 來源。頁面以組別／人員或完整路徑搜尋，點一張串流卡片後才載入 WebRTC 預覽，避免一次播放全部影像。顯示觀看 URL、複製連結、連線狀態及解碼錯誤；多個串流與手機畫面須能操作。[MediaMTX 官方瀏覽器文件](https://mediamtx.org/docs/read/web-browsers)支援直接觀看頁與 iframe，但實際嵌入方式仍須以本機管理頁測試。

總開關預設開啟；關閉時必須停止新的匿名觀看請求，並終止既有的**公開 viewer** WebRTC 工作階段，再讀回確認，不能只隱藏控制台連結。控制台內部預覽與 ICU 發布仍可運作。作業從受保護的控制介面轉送到 viewer 的內部 API；API 不發布到主機或網際網路。MediaMTX 1.21.1 的 [Control API 規格](https://raw.githubusercontent.com/bluenviron/mediamtx/v1.21.1/api/openapi.yaml)提供路徑清單、WebRTC session 清單與踢除端點；切換後如何持久化及重啟恢復須以實際容器驗證。若 API 不可用或關閉後仍有公開工作階段，控制台要顯示操作失敗，不能只切換按鈕外觀。

### 先行可行性驗證

本機 ICU 實測在 MediaMTX 顯示單一 `MPEG-TS` 軌，見[影像驗證紀錄](../validation/2026-09-24-qr-e2e-revocation.md)。MediaMTX 1.21.1 提供 [`rtspDemuxMpegts`](https://mediamtx.org/docs/references/configuration-file) 將此類 RTSP 輸入拆成原生影像／音訊軌；先驗證它是否適用於本機 ICU 輸入，再在 Chrome、Firefox 及 Android 瀏覽器測試**同一條實際串流**的 WebRTC 影像與音訊。若拆軌後編碼仍不相容，再依 [WebRTC 編碼說明](https://mediamtx.org/docs/features/webrtc-specific-features)加入按需 FFmpeg 轉碼成相容的 H.264／Opus，核對 CPU、延遲與多路同時觀看容量。完成本機測試後，再從不在熱點內的外部網路測 HTTPS、ICE、畫面、聲音與開關前後行為。

## MediaMTX Advanced → 一般設備：發布網址與 QR

管理者在 Advanced 入口選「一般設備」後，為無人機、編碼器等設備產生向 MediaMTX **發布影像**的連線資訊；選「ICU QR Code」則回到前述 `.prefs` 下載流程。一般設備的 QR 編碼發布網址，不是 `icu://download`，也不是免密碼 WebRTC 觀看連結。管理者先指定設備名稱與獨立的 `live/` 路徑，例如 `live/alpha/1/drone-01`；一般設備直接使用完整路徑，不假設它會像 ICU 一樣自行附加 `VIDEO_1`。

| 本機目前啟用的發布協定 | Advanced 頁面格式 | 目前可達範圍 |
| --- | --- | --- |
| RTSP | `rtsp://<username>:<password>@<host>:8554/<stream-path>` | Windows 熱點；無 TLS，僅供受控網段測試。 |
| RTSPS | `rtsps://<username>:<password>@<host>:8322/<stream-path>` | Windows 熱點；需設備信任伺服器憑證鏈並選用相容的媒體傳輸。 |

TLS 版本的 scheme 必須是 **`rtsps://`**；不能將 `rtsp://` 與 `8322` 混用。[MediaMTX 官方 RTSP 文件](https://mediamtx.org/docs/features/rtsp-specific-features)列出 RTSPS `8322` 及 RTSP 的 TCP／UDP 媒體傳輸。頁面只列出**目前設定已啟用且可達**的協定；日後若另行開啟 SRT 或 WHIP，再依該協定實際格式增列，不能把 WebRTC 觀看網址當成發布網址。外網設備要發布時，須另有公開 FQDN、可由設備信任的 TLS 憑證、對應 Router／防火牆入口與實機連線驗證；目前的 `takbox.local` 私有 CA 與熱點綁定不足以提供通用外網網址。

Advanced 設備的結果頁只以**發布網址與 QR Code**呈現每種已啟用協定，不另輸出 Host、Port、Path、Username、Password 分欄表單。RTSP、RTSPS 各有獨立卡片、獨立 QR、放大操作與**各自的「複製網址」按鈕**；點選某張卡片只複製該協定的連結，不複製其他協定或合併文字。QR 須編碼同一張卡片的實際發布 URL。帳密若放在 URL／QR 中，任何取得該 QR、截圖或複製文字的人都可使用該發布身分。因此管理頁預設遮蔽完整 URL，管理者明確點選「顯示連線資訊」後才顯示含帳密網址與 QR，關閉視窗即清除頁面中的 QR 與明文；不得把完整 URL 寫進一般日誌、瀏覽器歷史連結或 Git。URL 的帳密欄位須正確百分比編碼。

對外設備佈建使用前述單台設備獨立發布身分與限定路徑，不能直接使用 ICU 小隊密碼。控制台顯示設備路徑是否在線、最後連線狀態及來源；同一路徑已有發布者時須提示衝突，並實測 MediaMTX 的覆蓋／拒絕策略。Advanced 設備密碼重設後重新產生該設備的網址與 QR，舊網址須失效。驗收依序涵蓋 RTSP／RTSPS 本機設備、網址與 QR、憑證信任、設備停用、密碼輪替，以及完成公開入口後的外網設備推流。

## Vx：固定名稱強制替換

管理者選擇經實機匯出驗證的 Vx 範本與頻道設定，預覽任務名稱、Mumble `takbox.local:40000`、頻道名稱與 ID。只產生 **Vx-only DPK**，不混入 TAK 裝置憑證或 Mumble 密碼；顯示檔案 SHA-256。伺服器顯示名稱固定為 `ATAK Local Voice`。Vx 套件的交付方式是 TAK Server Data Packages → Download；本機或 QR 匯入不會觸發已驗證的 `sharing.downloaded` 任務建立流程，因此此分支不提供誤導性的匯入 QR。

「強制替換」明確指 **TAK Server 套件清單中的固定名稱檔案**，執行順序如下：

1. 在本機產生新 DPK，驗證 manifest、Vx payload、頻道資訊及 SHA-256；檢查 TAK 管理 API 可用。
2. 以固定名稱精確查詢現有套件。將所有同名舊套件的檔案、hash 與必要 metadata 備份至版控忽略的 runtime，並確認備份可讀；不得依模糊名稱刪除其他套件。
3. 明確確認「強制替換」後，按查得的**確切 hash** 刪除同名舊套件，讀回確認清單中已無該名稱。這段期間 Data Packages 會暫時無檔可下載。
4. 上傳新 DPK，設定並讀回 `tool=public`、`keywords=["missionpackage"]`、固定名稱及 SHA-256；查詢結果必須恰好一筆。僅在全部檢查通過後標記作業完成。
5. 若刪除後上傳或驗證失敗，作業標記為需要恢復，提供從備份重新發布舊套件的操作並再次驗證清單。作業日誌須保存刪除與上傳的 hash，避免重新整理或重試時重複刪除。

現有[Vx 產生器](../../scripts/build_tak_vx_package.py)每次建立新的 Mission／Channel UUID。因此伺服器檔案只留一筆，**不代表已安裝於 Android 的 `vx-local` 會原地更新**。先以乾淨裝置驗證新檔下載與四頻道，再以已有舊任務的裝置測試同名新檔重複下載，記錄覆蓋、重複或失敗行為；在結果確定前，不把清除 Vx 資料庫列為自動更新步驟。

## 實作順序與驗收

| 階段 | 工作 | 完成條件 |
| --- | --- | --- |
| 1 | 新增引導頁與三種預覽；串接既有單筆 TAK 與 ICU 分享 | 手機及寬螢幕可完成流程；返回上一步、驗證錯誤與 QR 結果正確；既有分享紀錄仍可管理。 |
| 2 | TAK 既有憑證多選與新憑證批次簽發 | 每筆有獨立 DPK／QR；部分失敗可辨識且重試不重複簽發；群組及註冊狀態經 API 讀回。 |
| 3 | ICU 標準／Advanced → ICU QR 路徑及小隊發布身分 | 四種標準組合、合法／非法自訂路徑與 ICU QR 下載均通過；同隊兩台 ICU 使用同一組帳密、不同路徑同時發布；重設後舊設定失效、新設定可發布，其他小隊不受影響。 |
| 4 | Vx 管理 API、備份及強制替換 | 舊檔按確切 hash 清除，新檔為唯一同名結果；模擬上傳失敗後能從備份恢復；乾淨裝置可下載並加入四頻道。 |
| 5 | 已安裝 Vx 任務更新實測與文件 | 記錄同名新檔在既有裝置上的行為，據結果決定是否需穩定 UUID 或顯式移除舊任務；更新正式操作文件。 |
| 6 | WebRTC viewer、公開入口及控制台即時預覽 | 本機 ICU 真實影像可在指定瀏覽器觀看；公開觀看預設開啟且狀態可持久化；從外網免密碼觀看成功；關閉後新連線遭拒、既有公開工作階段結束，ICU 發布與內部預覽維持可用。 |
| 7 | MediaMTX 管理頁與 Advanced 設備發布 | Advanced 先選 ICU QR 或一般設備，結果與掃碼行為符合所選類型；ICU 小隊及獨立設備支援多選停用／重設；ICU 重設產生限時限次的新設定 QR，舊 QR 失效；一般設備依協定各自顯示正確 URL、QR 與複製按鈕，只能發布指定路徑且可單獨停用；RTSP、RTSPS、路徑衝突與外網推流依可達範圍完成驗證。 |

功能發布前再檢查管理頁及 runtime／Git 邊界：憑證私鑰、ICU 發布密碼、QR token、裝置識別碼與個人資訊不得寫入版控或一般操作日誌。
