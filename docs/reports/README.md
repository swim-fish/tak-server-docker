# 報告來源與 Word 輸出

[憑證信任設計報告](tak-certificate-trust-design-report.md)與[控制台任務操作手冊](../tak-server/console-task-manual.md)的 Markdown 是可編輯來源。操作手冊另依功能分成四章；`scripts/build_docs_reports.py` 會依索引及各章順序合成 Word 文件，並從 Markdown 參照的圖片嵌入截圖。

在專案根目錄執行下列指令；Python 環境需要 `python-docx` 與 `Pillow`：

```powershell
python scripts/build_docs_reports.py --check
python scripts/build_docs_reports.py
```

輸出為本目錄的 `tak-certificate-trust-design-report.docx` 與 `tak-console-task-manual.docx`。修改內容、圖片或圖說後，先更新 Markdown，再重新產生 Word。發佈前應逐頁檢查 Word 版面與截圖中的識別資料；目前的 CA 替換與觀看工作階段截圖只說明介面狀態，不表示重新進行該項實測。
