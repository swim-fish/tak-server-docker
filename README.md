# TAK Server 5.8 Hardened 本機 Docker 環境

在 Windows Docker Desktop 執行 TAK Server、PostgreSQL 與 Mumble，供 ATAK 連線及 Vx 語音任務使用。

- 第一次建置：[從官方套件開始](docs/getting-started.md)。
- 日常操作與問題查詢：[文件首頁](docs/README.md)。
- 現行部署範圍：[架構與驗證狀態](docs/architecture.md)。
- 尚未實作：MediaMTX UDP、公開 8446／ACME 與 Linux 遷移，見[後續計畫](docs/plans/roadmap.md)。

`vendor/`、`runtime/` 保存官方套件與本機部署資料，不提交 Git。TAK 憑證 DPK 含裝置私鑰；Vx-only 任務包不含登入密碼。

## Git LFS

文件截圖使用 Git LFS。安裝 Git LFS 後執行：

```powershell
git lfs install
git lfs pull
```

本專案目前驗證範圍是本機網路。Vx 雙頻道登入已通過，雙向 PTT 與 UDP 音訊品質仍待驗收。
