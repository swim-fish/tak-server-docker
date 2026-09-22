# Vx DPK 格式與產生器

本頁供維護打包流程的人員使用。一般使用者請讀[Vx 任務操作](../atak/vx-missions.md)。格式來自裝置 Vx 2.1 原生匯出、APK／同版本 ATAK SDK 分析與[實機下載驗證](../validation/2026-09-22-tak-vx-dpk.md)，不是對所有 Vx 版本的通用格式承諾。

## 產生 Vx-only 套件

需要 Python 3、從 Vx 匯出的**單一 Mumble 頻道** ZIP，以及已確認的主機／頻道資料。原生 ZIP 含本機設定，放在 Git 忽略的 runtime；下列檔名為自行準備的輸入，不隨 repository 提供：

```powershell
python ./scripts/build_tak_vx_package.py --vx-only --vx-package ./runtime/packages/vx-native-single.zip --host takbox.local --port 40000 --mission-name vx-local --package-name "ATAK Local Voice" --output ./runtime/packages/atak-local-vx-only.dpk
```

產物為指定 DPK 及同名 `.sha256`。預設沿用範本的頻道 ID／名稱／Alias；若目標 Mumble 不同，應先核對 ID，再用下一節覆寫。

腳本會驗證 ZIP 路徑與大小、Manifest、JSON／Protobuf 一致性、UUID 關聯及輸出可讀性。不相容的範本應重新以支援版本匯出，不要移除檢查強行打包。成功產出仍須從 TAK Server 下載驗收。

## 一個 Mission 放入多個頻道

先以[頻道工具](../mumble/server.md#建立-primary-與-alternate)確認目前伺服器回報的 ID。下列僅為歷史測試 ID，必須改成自己的值，另存成 `runtime/packages/channels.json`：

```json
[
  {"number": 1, "alias": "P1", "mumble_channel_id": 2, "mumble_channel_name": "Primary"},
  {"number": 2, "alias": "A1", "mumble_channel_id": 3, "mumble_channel_name": "Alternate"}
]
```

```powershell
python ./scripts/build_tak_vx_package.py --vx-only --vx-package ./runtime/packages/vx-native-single.zip --channels-file ./runtime/packages/channels.json --host takbox.local --port 40000 --mission-name vx-dual --package-name "ATAK Local Voice Dual" --output ./runtime/packages/atak-local-vx-dual.dpk
```

頻道序號範圍為 1–99；不可重複序號或 Mumble ID。多個頻道參照同一 connection UUID，但 Vx 啟用 VS1／VS2 時仍可建立兩個獨立 Mumble session。套件不指定 PTT 按鍵或語音位置。

## Manifest 與 payload

原生 Manifest 為 version 2，保留：

```xml
<Parameter name="onReceiveImport" value="true"/>
<Parameter name="onReceiveDelete" value="false"/>
<Parameter name="onReceiveAction"
           value="com.atakmap.android.gbr.multicastvoice.sharing.downloaded"/>
```

Action 使用 `multicastvoice` 舊命名空間，不改成 `gbr.vx`。兩個 Content 為 `ignore="false"`，各有 `zipEntry` 與 Content 層級 `uid`，沒有 `contentType`。

```text
MANIFEST/manifest.xml
<native-directory-1>/<mission-uuid>
<native-directory-2>/<mission-uuid>_proto
```

第一份是 JSON，第二份是 Protobuf。產生器沿用原生 entry 結構、保留未知 Protobuf 欄位，同時更新 mission、channel、connection 及 Manifest 識別碼。

| 資料 | JSON | Protobuf |
| --- | --- | --- |
| Mumble 端點 | channel 的 `host="takbox.local:40000"` | connection 分開保存 hostname 與整數 port |
| 伺服器頻道 | `serverChannelId`、`subtitle` | channel 的 Mumble 資料 |
| 顯示 Alias | `name` | channel 名稱 |
| 連線關聯 | 同一任務下的 channel 資料 | channel 參照 connection UUID |

Legacy 的 `port=-1`、`missionPort=-1` 或 `missionDefaultProtocol=UDP` 不代表 Mumble 實際通訊埠。Vx 2.1 會處理有效的 Protobuf 任務；只改 JSON 不能保證新設定生效。

每次建置都產生新的套件、任務、頻道與 connection UUID，可能新增同名任務。這是產生新任務的工具，既有任務覆寫／去重仍待驗收。

## 為什麼 Local SD 匯入沒有任務

本次 ATAK Local SD 路徑只觀察到解壓及資料包處理，未觸發 Vx callback。TAK Server Download 路徑則會傳送 `onReceiveAction`，Vx 收到 Manifest 並建立任務。

Callback 需要 ATAK 傳入實際 Manifest 物件及本機內容資訊，不是只發出 action 字串就能替代。不同解析器讀到另一格式時的警告，必須與後續是否找到 Protobuf Mission 一起判讀。

## 密碼及整合包限制

原生任務不包含 Mumble 共用密碼。APK 的 `MumblePasswordManagerPrefs` 使用 AndroidX `EncryptedSharedPreferences`；`com.atakmap.android.gbr.vx.channels.mumble.security.serverPasswords` 是其加密儲存鍵，主機字串作為 Map 索引，不含通訊埠。

一般 ATAK `.pref` 使用普通 SharedPreferences，無法直接寫入相容的加密鍵值；因此本版不提供透過 DPK 預設此密碼的方法。相關靜態分析保留在[原始研究](../archive/original-vx-dpk-plan.md#mumble-密碼不在原生任務包裡)。

不加 `--vx-only` 時，工具會合併既有 TAK DPK 的 `servers.pref`、CA 與裝置 PKCS#12，產生實驗性整合包。這份包含裝置私鑰及匯入密碼，不當成共享任務上傳。整合包的一般 Local SD 匯入未通過 Vx 建立任務驗收；整合包從 Server Download 的完整流程尚未驗證。現行建議仍是 TAK 與 Vx 分兩階段交付。

依據：[產生器](../../scripts/build_tak_vx_package.py)、[ATAK 連線格式](../atak/connection.md)、[實測紀錄](../validation/2026-09-22-tak-vx-dpk.md)。
