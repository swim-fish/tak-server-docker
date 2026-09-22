# 2026-09-22 文件重整驗收

範圍為 README 與 docs 的結構、內容及引用。使用 `refactor-technical-docs` 整理任務與證據，採 Sepia professional refactor 修訂文字，再以 `zhtw-mcp` 檢查臺灣用語。本次不變更 Compose、腳本、PKI、服務或 Android 狀態。

## 檔案遷移與責任

| 舊位置／內容 | 新位置 | 主要責任 |
| --- | --- | --- |
| 根目錄 README | [README](../../README.md) | 專案入口及首次建置連結 |
| `PLAN.md` 的現行部分 | [架構](../architecture.md)、[版本與通訊埠](../reference/versions-and-ports.md) | 現行部署與版本範圍 |
| `PLAN.md` 的未完成設計 | [後續計畫](../plans/roadmap.md) | 待實作／待驗收及完成條件 |
| `PLAN.md`、`LOCAL_VALIDATION_PLAN.md`、Vx 原始計畫 | [歷史索引](../archive/README.md) | 原始設計、衝突與研究過程 |
| `MDNS.md` | [mDNS](../network/mdns.md)、[憑證](../security/certificates.md) | 名稱解析、SAN、CA 圖解 |
| `SETUP_FROM_SCRATCH.md` 第 1–4、6–7、10、12–13 節 | [首次建置](../getting-started.md)、[TAK 維運](../tak-server/operations.md)、[ATAK 連線](../atak/connection.md) | 建置、授權、匯入、啟停 |
| 原建置頁第 3.1、5 節 | [runtime 參考](../reference/runtime-layout.md) | 官方 ZIP、掛載檔案、secrets |
| 原建置頁第 8、8.1 節 | [Mumble Server](../mumble/server.md)、[使用者](../mumble/users.md) | 頻道、密碼、註冊管理 |
| 原建置頁第 9 節 | [防火牆](../network/firewall.md)、[mDNS](../network/mdns.md) | 熱點、UAC、前景規則與清理 |
| 原建置頁第 11 節、Vx DPK 研究的現行結論 | [Vx 操作](../atak/vx-missions.md)、[DPK 格式](../reference/vx-package-format.md) | 兩階段交付、callback、雙頻道 |
| 舊畫面與日期紀錄 | [歷史畫面](../archive/vx-manual-setup.md)、[驗證索引](README.md) | 保留當時畫面與結果，不冒充現行驗收 |

根目錄專案 Markdown 收斂為 README，內部連結同步遷移。未建立舊路徑的重複操作頁；既有外部書籤需要改指向新索引，原始版本仍可由 Git 歷史查閱。

## 主要事實及證據

| 主張 | 狀態 | 主要來源／處理 |
| --- | --- | --- |
| 現行只有 TAK、DB、Mumble 三個 Compose 服務 | confirmed | `compose.yaml`；移除現行說明中不存在的初始化服務 |
| 預設 Mumble 主機通訊埠 40000 | volatile | Compose、腳本與版本頁；64400 僅保留歷史說明 |
| mDNS 安裝／移除自行請求 UAC | confirmed | PowerShell 腳本；修正舊管理員起始步驟 |
| TAK 防火牆仍需管理員 PowerShell | confirmed | `Install-TakFirewall.ps1` |
| CA 信任與 SAN 分別驗證 | confirmed | bootstrap、Vx／TAK 實測；圖解與憑證頁統一解釋 |
| 一般 Local SD 能建立 Vx 任務 | conflict，已處理 | 撤回早期說法；採用清除設定後結果及 Server Download 成功路徑 |
| 註冊身分可能不檢查共用密碼 | confirmed | Mumble 固定版本原始碼及密碼輪替實測 |
| 雙頻道登入代表雙向音訊成功 | unknown，不採用 | 保留登入結果，PTT／UDP 明確列為待驗 |
| 全 WSL 儲存、Certbot／MediaMTX 初始化服務 | historical／planned | 移至歷史與後續計畫，不提供為現行啟動命令 |

## 結構與內容驗收

本輪文件驗收完成，未留下未處理的 Critical／High 文件問題：

| 檢查 | 結果 |
| --- | --- |
| 文件範圍 | 根目錄 README 加 docs 共 28 份 Markdown。 |
| 本機連結／錨點 | 28 份全部有效；以 repository 為解析根目錄，排除 runtime／vendor 掃描。 |
| 圖片 | 7 個引用、6 張 JPG；替代文字、目標檔案與中繼資料檢查無問題。 |
| PowerShell 範例 | 37 組通過語法解析；佔位符先替換成範例值，只解析而不執行。 |
| 命令參數 | 腳本路徑存在；Python CLI 參數與 argparse 定義一致。 |
| 原始碼核對 | 修正不存在的初始化服務、UAC 說明及 mDNS 固定 Python 3.14 路徑。 |
| 機密資料 | 未命中本機 8 份 secret 值、私鑰標記、已知使用者路徑或裝置序號；不是全 Git 歷史稽核。 |
| 文字與差異 | 無控制字元；Git whitespace 檢查有效範圍無問題。 |
| zhtw／Sepia | 完整語言掃描後人工複核，修正現行用語及冗長句；不以風格分數推論作者或文字來源。 |

zhtw 完整掃描曾回報 1 個 error，位於歷史建置計畫第 13 節標題的「項目」；這裡表示待決定事項，不是 project，故保留並判定為誤報。其餘提示分為歷史措辭、正確技術語意及 Markdown 解析誤報，已人工檢視。現行操作頁沒有殘留的語言 error。

連結及圖片檢查沿用 skill 的工具；命令解析、來源比對與本機 secret 比對報告保存在 Git 忽略的 `runtime/docs-refactor-2026-09-22/`。

語言檢查保留語意正確的「驗證通過」「項目」「語音頻道」，以及描述步驟的「程序」。工具將部分詞片段或 Markdown 連結標點視為問題，依上下文人工排除。歷史原始計畫的措辭保留，沒有改寫當時技術結論。

六張 JPG 保持原檔及 LFS 管理。前五張為歷史 UI；含舊 port 的圖已明確標示。密碼提示圖為空白欄位的原圖裁切。人工檢視未見明文密碼、呼號、裝置序號或個人座標；部分歷史圖片仍有一般地圖背景。沒有新增原始截圖或 logcat。

## 人工審查量表

| 面向 | 分數（0–3） | 證據或限制 |
| --- | --- | --- |
| 任務入口 | 3 | 文件首頁依工作提供直達連結。 |
| 前置條件 | 3 | 建置、網路、憑證與工具頁先列需求。 |
| 心智模型 | 3 | 架構與憑證圖解分清信任、名稱與身分。 |
| 操作可執行性 | 2 | 參數及語法依程式碼核對；本輪沒有清空重建環境。 |
| 回饋與成功條件 | 3 | 健康、解析、登入、任務及音訊分開判斷。 |
| 例外與復原 | 2 | 各頁有安全重試方向；整套備份還原工具仍待實作。 |
| 證據與正確性 | 3 | 衝突、版本界線與未驗項目均有註記及來源。 |
| 內容分層 | 3 | 教學、任務、概念、參考、歷史分開。 |
| 可維護性 | 3 | 精確規則有主要參考頁，其他頁僅摘要及連結。 |
| 視覺與無障礙 | 2 | 圖片有替代文字；舊 UI 已隔離，未重拍現行全套畫面。 |
| 術語與語言 | 3 | 有共用用語表、zhtw 檢查及人工語意複核。 |
| 版本與時效 | 3 | 版本表有日期，證據保留原測試日期。 |

本輪為文件驗收。既有 TAK／Vx 登入結果沿用日期紀錄；雙向 PTT、UDP、Linux、MediaMTX、公開 8446／ACME 與整合包 Server Download 均未因此新增為通過。
