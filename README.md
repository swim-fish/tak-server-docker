# TAK Server 5.8 Hardened 本機 Docker 環境

在 Windows Docker Desktop 執行 TAK Server、PostgreSQL、Mumble、MediaMTX 與本機控制台，供 ATAK 連線、Vx 語音及 ICU 影像發布使用。

- 第一次建置：[首次建置腳本](docs/scripts/first-time-setup.md)或[逐步手動流程](docs/getting-started.md)。
- 日常操作與問題查詢：[文件首頁](docs/README.md)。
- 現行部署範圍：[架構與驗證狀態](docs/architecture.md)。
- 尚待驗收：熱點外部的 MediaMTX UDP、公開 WebRTC 網際網路入口、公開 8446／ACME 與 Linux 遷移，見[後續計畫](docs/plans/roadmap.md)。

`vendor/`、`runtime/` 保存官方套件與本機部署資料，不提交 Git。TAK 憑證 DPK 含裝置私鑰；Vx-only 任務包不含登入密碼。

## Git LFS

文件截圖使用 Git LFS。安裝 Git LFS 後執行：

```powershell
git lfs install
git lfs pull
```

本專案目前驗證範圍是本機網路。Vx 雙頻道登入已通過，使用者另確認手機的雙頻道語音可用；雙向 PTT 按鍵對應、實際 UDP 路徑與音訊品質仍待記錄驗收。
