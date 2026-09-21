# TAK Server 5.8 Hardened 本機 Docker 環境

本專案在 Windows Docker Desktop 上執行 TAK Server 5.8 Hardened、PostgreSQL 與 Mumble，並產生供 ATAK 匯入的 Data Package。

請從下列文件開始：

- [從零開始建置與啟動](docs/SETUP_FROM_SCRATCH.md)
- [Windows mDNS 設定](MDNS.md)
- [本機整合驗證計畫](LOCAL_VALIDATION_PLAN.md)

`vendor/` 與 `runtime/` 都是本機產物，不應提交 Git。`vendor/` 保存官方 hardened 套件；`runtime/` 保存私鑰、密碼、憑證、Data Package 與執行階段設定。

## Git LFS

`docs/images/*.jpg` 透過 Git LFS 管理。第一次 clone 本專案前先安裝 Git LFS，然後執行：

```powershell
git lfs install
git lfs pull
```
