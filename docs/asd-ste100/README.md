# TAK 控制台使用手冊：ASD-STE100 中英文對照

本目錄改寫 [TAK 控制台任務操作手冊](../tak-server/console-task-manual.md)及其四個分章，共 166 段。原始檔案維持不變。各章保留操作條件、風險、數值、指令、圖片與驗收限制。

| 章節 | 繁中改寫 | English | 原文／繁中／英文對照 |
| --- | --- | --- | --- |
| 開啟控制台與任務索引 | [繁中](zh-TW/index.md) | [English](en/index.md) | [三欄對照](comparison/index.md) |
| 憑證與群組 | [繁中](zh-TW/certificates-and-groups.md) | [English](en/certificates-and-groups.md) | [三欄對照](comparison/certificates-and-groups.md) |
| Vx 與 Mumble | [繁中](zh-TW/vx-and-mumble.md) | [English](en/vx-and-mumble.md) | [三欄對照](comparison/vx-and-mumble.md) |
| ICU 與 MediaMTX | [繁中](zh-TW/icu-and-mediamtx.md) | [English](en/icu-and-mediamtx.md) | [三欄對照](comparison/icu-and-mediamtx.md) |
| 分享與疑難排解 | [繁中](zh-TW/sharing-and-troubleshooting.md) | [English](en/sharing-and-troubleshooting.md) | [三欄對照](comparison/sharing-and-troubleshooting.md) |

## 使用範圍

英文版採用所指定 ASD-STE100 skill 的寫作原則。繁中版採用可適用的短句、條件分支、術語一致與操作順序原則。ASD-STE100 的英文詞彙規則不直接套用於中文。

這次工作未取得官方受控字典，也未執行正式認證。檢查成功只代表符合下述自動檢查條件。技術語意與操作安全仍須人工審閱。這次未操作 TAK、Android 或影音服務，也未重新執行原始手冊引用的實機測試。

原文的 ICU 疑難排解原本只列出 RTSPS 通訊埠。原文與改寫版都已依產生器與設定參考，分別寫出 RTSP `8554` 與 RTSPS `8322` 的 SSL 條件。證據見 [build_icu_qr.py](../../scripts/build_icu_qr.py)及 [ICU QR 設定](../mediamtx/icu-qrcode.md)。

## 重新產生與檢查

在專案根目錄執行下列命令。需要 Python 3.10 以上版本。

只檢查來源對應、產物一致性、技術識別字、數值、錨點、連結、Markdown 表格欄數與英文操作句長度。這個模式只輸出結果，不改寫 `checks/` 內的報告：

~~~powershell
python docs/asd-ste100/check_manual.py
~~~

修改 [manual-data.json](manual-data.json) 的 `zh` 或 `en` 欄位後，重新產生所有手冊及對照頁：

~~~powershell
python docs/asd-ste100/check_manual.py --write
~~~

`original` 欄位是原文快照，不供改寫。若來源手冊變更，檢查會失敗。更新來源快照時，須同時人工核對兩種語言。

執行完整檢查前，先把 `$steLinter` 設為 `asd-ste100` skill 內 `skills/asd-ste100/scripts/ste-lint.py` 的實際路徑。路徑依安裝方式與版本而不同：

~~~powershell
$steLinter = 'C:\path\to\asd-ste100\scripts\ste-lint.py'
python docs/asd-ste100/check_manual.py --ste-linter $steLinter --zhtw
~~~

同時指定 `--ste-linter` 與 `--zhtw` 時，才會更新 `checks/` 內的三份報告。報告一律以 LF 換行寫入。

若 `zhtw-mcp` 不在 PATH，透過 `--zhtw-command` 指定執行檔：

~~~powershell
python docs/asd-ste100/check_manual.py --ste-linter $steLinter --zhtw --zhtw-command 'C:\path\to\zhtw-mcp.exe'
~~~

檢查 script 使用標準函式庫，透過 MCP stdio 呼叫 `zhtw`。不會自動安裝工具。缺少指定工具或呼叫失敗時，程式會傳回非零結束碼。

## 檢查結果與限制

- [結構檢查](checks/structure.json)：五份來源、166 段與 15 份產物的對應，以及本目錄 Markdown 表格的欄數檢查。
- [英文結構檢查](checks/ste.json)：skill linter 的原始 finding 與各份英文 Markdown 的 SHA-256。
- [繁中檢查](checks/zhtw.json)：各繁中檔案的 SHA-256、規則集識別資料與 MCP 回應。回應不含已檢查的全文。
- [審閱紀錄](review.md)：改寫原則、保留項目與英文 advisory 的處理理由。
- [專案詞彙表](glossary.json)：需保留的產品用語、憑證術語與 UI 名稱。

繁中檢查採零錯誤、零警告門檻，保留資訊性提示。檢查範圍為繁中改寫版與本頁。對照頁的原文欄保留來源用語，不納入改寫版的用語門檻。程式碼區塊、指令、路徑與以程式碼格式標示的 UI 名稱不改寫。

英文操作句以 20 字為檢查門檻。這是近似計數：行內程式碼與完整 UI 標籤各算一個識別字。skill linter 另檢查敘述句長度及文法模式。數值與識別字檢查只能偵測遺失，無法證明條件、否定、順序與語意等價。

單獨執行結構檢查不會重新執行 STE 或繁中檢查。修改內容後，請執行完整檢查以更新語言報告。
