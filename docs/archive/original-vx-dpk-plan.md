# TAK Server 與 Vx Mumble 整合 DPK 計畫

> 歷史資料：保存至 2026-09-22 的原始計畫與研究歷程，內含未實作設計、舊值及已被後續實測修正的判斷。請勿直接照此部署；現行操作從[文件首頁](../README.md)開始，未完成項目見[後續計畫](../plans/roadmap.md)。

日期：2026-09-22。狀態：Vx-only DPK 經本機 TAK Server 下載已實測成功：觸發 sharing.downloaded、建立 vx-only-test 任務及 Mumble 頻道，輸入密碼後登入並加入 Primary。一般 Local SD 匯入仍不觸發 Vx 任務建立。後續雙頻道 vx-dual-test 亦已通過：同一台 Mumble Server 的 Primary／Alternate 可同時維持獨立 session。部署建議改為 TAK 憑證本機匯入＋Vx-only 伺服器下載兩階段；PTT 按鍵及雙向語音尚未驗收。詳見 [實機驗證紀錄](../validation/2026-09-22-tak-vx-dpk.md#tak-server-下載實測成功)。

## 1. 實機擷取結果

測試組合為 ATAK-CIV `5.7.0.15 (b75ee790)` 與 Vx `2.1.0 (20251122) - [5.6.0]`。透過 ADB 操作 Vx 的 Missions → 任務 `a` → Send Mission → Export，取得本機原生 ZIP；沒有傳送給聯絡人或 TAK Server。

| 項目 | 實際值 | 證據 |
| --- | --- | --- |
| Mission | `a` | 原生 JSON、Protobuf 與 Vx 畫面 |
| 畫面顯示 | `01-P1` | Vx channel selector |
| Alias | `P1` | JSON `channels[0].name`、Protobuf |
| Channel number | `1` | Protobuf；對應畫面前綴 `01-` |
| Address | `takbox.local` | JSON `host`、Protobuf connection |
| Port | `64400` | JSON `host`、Protobuf connection |
| Mumble channel name | `Primary` | JSON `subtitle`、Protobuf、畫面 |
| Mumble channel ID | `2` | JSON `serverChannelId`、Protobuf |
| TAK Server 設定檔 | `takbox.local:8089:ssl` | 裝置上既有 `servers.pref` |

`tak.box.local` 與 `takbox.local` 是不同名稱；此次實機擷取值為後者。`01-P1` 由頻道序號與 Alias 組成，不應整串寫入 Alias，否則可能重複顯示序號。

目前 Compose 對外提供 `40000/TCP+UDP`，但 Vx 任務仍保存 `64400`。規劃的新 DPK 應使用 `takbox.local:40000`。本次只匯出與檢查，未修改任務或伺服器通訊埠。

`servers.pref` 是裝置上的已匯入檔案，不等於直接讀取 ATAK 當下的私有連線資料庫。ATAK release 版的 `run-as` 回報 `package not debuggable`，因此本次沒有擷取私有 SharedPreferences 或資料庫。

### 原始證據位置

所有本機證據位於 Git 忽略的 `runtime/device-vx-2026-09-22/`：

| 檔案 | 用途 |
| --- | --- |
| `vx-mission-a-native.zip` | Vx 原生匯出包；保留原始 Manifest 與兩份任務資料 |
| `native-temp/` | `/sdcard/atak/tools/takvoice/temp/` 的 JSON 與 Protobuf 原件 |
| `verified-fields.json` | JSON／UI 對照 Protobuf 的欄位摘要 |
| `servers.pref` | 從 `/sdcard/atak/config/prefs/servers.pref` 擷取的既有 TAK 設定檔 |
| `vx-base.apk` | 從本次設備擷取的 Vx base APK，供版本與內附手冊核對 |
| `ui.xml`、`ui.png` | 本機操作證據，可能含呼號與地圖資訊，不提交版控 |

原生 ZIP SHA-256：`7af9dc2f000f24e8adffc56313e56185b2825cba00e9a056b5b0bd28e8850c33`。

原生包名稱帶有裝置呼號。日後產生器應使用中性名稱，例如 `ATAK Local TAK and Voice`，不得直接沿用原始呼號作為公開範例。

## 2. 原生格式及對既有研究的補充

### Manifest 必須保留 Vx 的 callback

實機匯出的 Manifest 為 version 2，Configuration 包含：

```xml
<Parameter name="onReceiveImport" value="true"/>
<Parameter name="onReceiveDelete" value="false"/>
<Parameter name="onReceiveAction"
           value="com.atakmap.android.gbr.multicastvoice.sharing.downloaded"/>
```

這個 action 使用 `multicastvoice` 舊命名空間；不可依目前外掛名稱自行改成 `gbr.vx`。

原生 Contents 有兩個 `ignore="false"` 的 Content，每個都有 `zipEntry` 與 Content 層級的 `uid`，沒有 `contentType`：

```text
MANIFEST/manifest.xml
<native-directory-1>/<mission-uuid>
<native-directory-2>/<mission-uuid>_proto
```

第一份無副檔名檔案是 JSON，相容舊版的 MissionDescription；第二份是 Protobuf。兩份都保留，並維持 Manifest、mission、channel、connection 的識別碼關聯。第一輪整合應保留原生 ZIP entry 路徑，不任意改成 `.json` 或猜測外掛 `contentType`。

### JSON 與 Protobuf 必須同步

此設備 JSON 的 Mumble channel 使用：

```json
{
  "name": "P1",
  "host": "takbox.local:64400",
  "serverChannelId": 2,
  "subtitle": "Primary",
  "isMumble": true,
  "port": -1
}
```

這是省略 UUID 等欄位的說明片段，不是完整可匯入檔案。Mumble 通訊埠位於 `host` 的 `:64400`；不能把此 legacy channel 的 `port=-1` 當成 Mumble 真正通訊埠。Mission 的 `missionPort=-1`、`missionDefaultProtocol=UDP` 也不能用來取代 Mumble connection 設定。

Protobuf 則把 `takbox.local` 與整數 `64400` 分開保存於 connection，channel 以 connection UUID 參照它。本次已確認此關聯相符，且 channel number 為 `1`、Alias 為 `P1`、Mumble channel name 為 `Primary`、ID 為 `2`。欄位語意由原生 JSON、UI 與 wire data 交叉對照取得，尚未完成自製序列化器的匯入測試。

修改主機或通訊埠時必須同步兩種表示。不能只改 JSON 就宣稱 Vx 2.1.0 會使用新值。

### Mumble 密碼不在原生任務包裡

本機 APK 的 `assets/User Guide.pdf` 第 4 頁明確說明：Mumble server password 不隨任務分享，接收端嘗試加入時會提示輸入。此次 JSON 與 Protobuf 也沒有包含伺服器密碼。

提示不是每次下載任務或輪替一般密碼都會出現。已有儲存密碼或可驗證的 Mumble 註冊身分時，可能直接登入；伺服器支援以已登錄的用戶端憑證驗證註冊身分，此時不再檢查一般 server password。2026-09-22 的密碼輪替測試已確認 Vx 仍以註冊 ID 連線，詳見 [驗證紀錄](../validation/2026-09-22-tak-vx-dpk.md#更換-mumble-密碼以重現提示畫面)。

APK 內另有 `voice_configuration_database.sqlite`，可辨識 `mission`、`mumble_channels`、`mumble_connections` 資料表定義。這比僅使用全域 `hostIP`／`hostPassword` 的公開範例更完整，也表示不能以寫入兩個偏好設定鍵值取代原生任務。

2026-09-22 後續分析已核對 APK 密碼管理類別 `atakplugin.vx.j60` 的實際讀寫程式：

```text
com.atakmap.android.gbr.vx.channels.mumble.security.MumblePasswordManagerPrefs
com.atakmap.android.gbr.vx.channels.mumble.security.serverPasswords
```

| 項目 | APK 確認結果 |
| --- | --- |
| 儲存檔名 | 上述 `MumblePasswordManagerPrefs` 完整名稱 |
| 儲存 API | `EncryptedSharedPreferences.create(...)`，使用 ATAK context |
| MasterKey | `AES256_GCM` |
| 偏好設定鍵加密 | `AES256_SIV` |
| 偏好設定值加密 | `AES256_GCM` |
| `serverPasswords` 內容 | Kotlin serialization 的 `Map<String, String>` JSON |
| Map 索引 | Mumble connection 的 `ipAddress` 字串；讀取時沒有串接通訊埠 |
| Map 值 | 一般 Mumble server password |

解密後的邏輯內容類似 `{"takbox.local":"<MUMBLE_SERVER_PASSWORD>"}`，但這不是可直接寫入 Android XML 的內容，也不是可用的 `.pref` 範本。`j60.h()` 透過加密 API 讀取並反序列化 JSON，`j60.l()` 則透過相同加密 API 寫入；`j60.g(host)` 與 `j60.n(host, password)` 分別取得及更新伺服器密碼。呼叫端 `y40.t()`／`y40.e()` 從 connection 的 `ipAddress` 欄位取 Map key，通訊埠另傳給連線建立函式。

同版本 ATAK SDK `PreferenceControl.loadSettings(Node, String, List)` 使用普通 `Context.getSharedPreferences(name, MODE_PRIVATE)` 與 `Editor.putString`。因此，把明碼 `serverPasswords` 放到一般 app preferences 會寫到不同儲存區；即使指定完整 `MumblePasswordManagerPrefs` 名稱，也不會套用 Vx 的鍵／值加密，Vx 的加密讀取不會因此取得該明碼值。

結論：**本版的一般 ATAK DPK／`.pref` 不能直接設定此 `serverPasswords` 鍵來完成自動登入。**JSON schema 正確不代表儲存方式相容。沒有把測試明碼寫入現用的加密儲存檔，也沒有宣稱完成密碼 DPK 匯入實測。本次結果來自設備 APK 與同版本 SDK 的靜態程式核對。

伺服器密碼與 `passwords.<host>` 是不同機制；後者的序列化型別為 `Map<Int, Pair<String, Long>>`，供頻道密碼與時間資訊使用，不應混用。

本機分析證據保存在同一 runtime 目錄的 `password-class-atakplugin_vx_j60.txt`、`password-callsites.txt` 與 `PreferenceControl.javap.txt`。AndroidX 官方 [EncryptedSharedPreferences 說明](https://developer.android.com/reference/androidx/security/crypto/EncryptedSharedPreferences) 亦指出它會加密儲存鍵和值。若未來需要自動化，必須先找到 Vx 支援的 provisioning 介面，或由受控、相容的 ATAK 外掛在裝置內呼叫正確加密 API；這屬於額外程式整合，不是純 DPK 格式調整。

## 3. 原始整合包設計（保留研究歷程）

原始目標為一份 DPK 設定 TAK 連線、信任庫及 Vx 任務；本機匯入實測未達成。2026-09-22 已驗證的可用方案為：TAK 設定／憑證本機匯入，Vx-only 任務包從 TAK Server 下載，首次登入 Mumble 手動輸入密碼。下列整合包格式保留供研究，不當作已通過的部署方式。

```text
atak-local-tak-vx.dpk
├── MANIFEST/manifest.xml
├── config/servers.pref
├── cert/caCert.p12
├── cert/clientCert.p12
├── <native-directory-1>/<mission-uuid>
└── <native-directory-2>/<mission-uuid>_proto
```

| 內容 | 打包方式 |
| --- | --- |
| TAK 連線 | 沿用 `cot_streams`，`connectString0=takbox.local:8089:ssl` |
| TAK CA | `caCert.p12` 同時含 Root CA 與中繼 CA |
| TAK client 身分 | 每台裝置專用 `clientCert.p12`，含私鑰及完整憑證鏈 |
| 憑證參照 | 沿用 `caLocation0`、`caPassword0`、`certificateLocation0`、`clientPassword0`，避免改成全域 default 憑證 |
| Vx 任務 | 保留 native JSON、Protobuf、Content uid 及 callback |
| Mumble 目標 | `takbox.local:40000`，Alias `P1`、channel `Primary` |
| Mumble 密碼 | 初版由使用者輸入一般 server password；來源為 `runtime/secrets/mumble_server_password` |

Manifest 中，`.pref` 用 `ATAK Preferences`，`.p12` 用 `P12 Certificate`；Vx 兩份 payload 保留原生無 `contentType` 的形式。整合時展開原生任務內容併入同一個 Manifest，不把任務 ZIP 再包成巢狀 ZIP。

Vx 仍須已安裝並啟用。DPK 不會安裝外掛，也不會替 Docker 建立 Mumble 頻道；`Primary`／`Alternate` 由現有 provisioner 建立。不同 Mumble 資料庫中的同名頻道可能有不同數值 ID，不能在所有部署中固定假設 `Primary=2`；打包前要取得該伺服器實際頻道資訊，或重新由 Vx 建立並匯出基準。

Mumble 使用同一中繼 CA 簽發的獨立 server certificate，DNS SAN 須包含 `takbox.local`。mDNS 只負責解析名稱。DPK 只分發 CA 公開憑證與該裝置的 TAK client 身分，不放入 CA 私鑰、Mumble server 私鑰或 SuperUser 密碼。

## 4. 實作與驗收順序

1. **建立可還原基準。**保留本次 `a` 原始匯出包。後續先在第二台同版本設備或新測試任務驗證，確認重複 UUID 的覆寫行為後才處理現用 `a`。
2. **修正基準任務的端點。**在後續已授權的實作階段，將 Vx 設為 `takbox.local:40000`，確認 `Primary` 可加入，再重新原生匯出。初版使用此匯出包，比自行編輯未知 Protobuf schema 更容易核對。
3. **單獨測試 Vx native ZIP。**使用預定的手動 DPK 匯入入口，檢查是否觸發 callback、任務是否出現、兩份 payload 是否被去重。若只解壓而沒有新增任務，先找出支援的原生載入方式；不得把匯入通知當成成功，也不直接要求使用者改匯入安全政策。
4. **新增組合打包器。**以 `scripts/rebuild_atak_data_package.py` 的憑證與 TAK 設定產物，加上已驗證 native ZIP 建立新的 `atak-local-tak-vx.dpk`。檢查 ZIP 路徑、重複 entry、Manifest 引用及 UUID 關係，拒絕路徑穿越。使用 XML serializer 正確處理密碼特殊字元。
5. **驗證 TAK 憑證及 Vx callback 的實際順序。**確認 `.pref` 被套用、CA／client 憑證匯入指定 TAK 連線，再檢查 Vx 任務是否可使用此信任鏈。Manifest 列出順序不等於已保證完成順序。
6. **首次連線驗收。**ATAK `8089` 實際連線成功；Vx 顯示 `a`、`01-P1`、`takbox.local:40000`、`Primary`；輸入一般 Mumble 密碼後驗證成功。應對照 Vx 畫面／logcat 與伺服器時間，避免把獨立 Mumla 的連線當成 Vx 驗證。
7. **重複匯入及重啟驗收。**確認不產生重複任務、不影響其他 TAK Server 憑證、更新既有端點的行為明確；相同 TAK 連線重匯入時也要確認憑證有更新。
8. **密碼處理。**已確認 `serverPasswords` 使用 EncryptedSharedPreferences，初版維持首次輸入密碼。若要完全自動登入，另立 Vx provisioning／裝置內整合方案；一般 ATAK 偏好設定匯出或明碼 `.pref` 不視為加密密碼的部署方式。不得以關閉 TLS 驗證代替。
9. **語音驗收。**使用第二個用戶端進行雙向 PTT 與 UDP 語音測試；TCP 登入和加入頻道成功不等同於音訊已通。

### 尚待討論／驗證的限制

- 初版匯入後手動輸入一次 Mumble 密碼，符合本版原生分享行為。`serverPasswords` 明碼 `.pref` 路徑已由程式核對排除；完全自動登入需要額外裝置內整合。
- `onReceiveAction` 已由原生包確認，但「本機手動匯入」與「網路收到資料包」的 callback 路徑仍須各自驗證。同版本 SDK 的 `ImportMissionPackageResolver`／`ExtractMissionPackageTask` 靜態檢查不足以保證所有入口都會通知 Vx。
- TAK `ImportCertSort` 的參考原始碼會比較匯入前後的串流；新增連線與重匯入既有連線的憑證行為要分別驗收。
- 若將同一 DPK 內其他 `.pref`／`.p12` 加入 native Manifest，Vx 是否只選擇自己的 payload 而忽略其他檔案，必須實機確認。
- 前一天 `40000` 的伺服器紀錄證明 Android Mumla 協定用戶端可連線；本次 Vx 匯出仍為 `64400`，所以那些紀錄不足以單獨證明目前 Vx 任務已完成通訊埠移轉。也無法僅憑本次快照判定昨天是否曾修改後又改回。

## 5. 依據與證據範圍

- 「研究Plugin」提供研究方向；本計畫的實際欄位與 callback 以本次設備匯出為準。
- Vx APK 隨附 `assets/User Guide.pdf`，第 3–5 頁：任務、分享與頻道設定；第 4 頁明確排除密碼分享。
- `atak_docs/docs/rst/atak-data-package.rst`：Manifest version 2、精確 `contentType`、偏好設定與憑證打包。
- `ATAK-CIV-5.7.0.15-SDK/main.jar`：同版本匯入類別的靜態檢查；本機分析輸出保留於上述 runtime 目錄。
- `atak-civ/atak/ATAK/app/src/main/java/` 的 `PreferenceControl`、`ImportCertSort`、`MissionPackageExtractor`、`MissionPackageReceiver`：參考原始碼的 SharedPreferences、憑證 finalize 與接收 callback 行為。此原始碼快照不當作手機 APK 的逐位元相同實作。

以上保留原始計畫與設計依據；目前實作及驗收結果以 [實機驗證紀錄](../validation/2026-09-22-tak-vx-dpk.md) 為準。
