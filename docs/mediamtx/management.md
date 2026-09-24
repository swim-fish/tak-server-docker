# MediaMTX 管理與 WebRTC 預覽

Windows 本機控制台位於 `http://127.0.0.1:10066/media`。管理者可查看目前在線的 `live/` 串流、預覽影像、管理 ICU 小隊與一般設備發布身分。頁面使用控制台既有的 Basic 驗證；MediaMTX Control API 只在 Compose 網路內開放。

## 即時影像

在「目前發布的串流」選擇「即時預覽」，影像會載入控制台內的同來源預覽區。按「關閉預覽」會卸載 iframe，結束該預覽連線。公開觀看連結則指向 `http://takbox.local:8889/live/<path>/`；路徑結尾的 `/` 是必要的，否則 MediaMTX 的頁面可能把最後一段路徑當成檔名。管理頁每 3 秒更新公開觀看工作階段數量，不會重整選取中的表單。

公開觀看預設開啟。控制台總開關關閉後，公開入口拒絕新的觀看請求，並透過內部 API 中斷既有公開 WebRTC 工作階段；管理頁預覽與 ICU 發布維持獨立。預覽由控制台代為向 `media-preview` 驗證，瀏覽器不需要連到 `127.0.0.1:8890` 或輸入第二組帳密。

目前 `takbox.local` 與 `192.168.137.1` 只在本機熱點可達。**尚未開放網際網路觀看**；公開 FQDN、HTTPS 憑證、Router NAT、防火牆及 ICE 外部可達性仍須另行設定與實測。匿名觀看的 `live/` 路徑可預測，對外開放前應確認影像內容可以公開。

## 小隊 ICU QR

引導式佈建位於 `/provision`。標準模式可選 Alpha 至 Hotel 小隊及 1–10 人員代號，也可留空；Advanced ICU 模式可自訂以 `live/` 開頭、`/` 結尾的 Stream Path。ICU 會在設定路徑後附加 `VIDEO_1`。每個小隊共用一組發布帳密，但只被授權發布清單中指定的完整路徑；不同小隊使用不同帳密。

在 `/media` 勾選一個或多個**啟用中的 ICU 小隊**，設定 QR 分享時間與下載上限，選擇「再次發布 ICU QR」即可重新建立 QR。此操作沿用現有小隊密碼，不停止原有 QR，也不踢除目前串流；每個已配置路徑會有獨立的限時、限次 QR。若要讓舊設定失效，使用「重設選取密碼」。結果頁有獨立網址；重新整理不會再次建立 QR 或重設密碼。作業異常時會顯示已完成項目，避免在未檢查狀態前重複執行。

QR 指向 `icu://download?url=...`，下載的 `initial.prefs` 含發布密碼。Android 必須連上受控熱點、解析 `takbox.local` 並點開掃碼器顯示的**完整** `icu://` 連結。單憑「Externally configured」提示不足以判定影像已發布，仍應檢查 ICU 欄位及 MediaMTX 在線路徑。詳見 [ICU QR Code](icu-qrcode.md)。

## 一般設備與權限

Advanced → 一般設備可指定設備名稱及完整 `live/` 路徑，建立獨立的發布身分。路徑欄使用 RTSPS URL input group，前綴固定顯示 `rtsps://takbox.local:8322/`，輸入欄只填 Stream Path，並即時預覽完整發布 URL；正式建立後才產生設備專屬帳密。結果頁的 RTSP、RTSPS 網址與 QR 分開顯示；按「顯示連線資訊」才揭露內含帳密的網址。網址只在控制台與 QR 內顯示，不應貼入日誌或提交至 Git。RTSP 通訊埠為 `8554`，RTSPS 為 `8322`；RTSPS 裝置須信任 TAK CA 鏈與 `takbox.local` 伺服器名稱。

發布身分清單可用「啟用中／停用／顯示全部」按鈕篩選；切換時會取消隱藏項目的勾選。「停用選取身分」會拒絕新發布並嘗試中斷該帳號現有 RTSP 工作階段；「重設選取密碼」會輪替帳密，停止舊 QR，為小隊各路徑建立新 ICU QR。一般設備可重新顯示新發布網址與 QR。舊的 `atak-publisher` 共用帳號暫時保留供既有 ICU 遷移；改用小隊 QR 的裝置應逐步移轉，再決定停用舊帳號。

目前已用 Android ICU 的 `live/alpha/1/VIDEO_1` RTSPS 串流驗證 Chrome 中的 WebRTC 影像。MediaMTX 在獨立 viewer 內把 ICU 的 MPEG-TS 拆出 H.264 與 KLV；音訊、Firefox、Android 瀏覽器、同隊多裝置同步發布及一般設備 RTSP／RTSPS 推流仍待驗收。
