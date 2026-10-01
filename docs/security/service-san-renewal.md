# 不輪替 CA 的服務憑證 SAN 更新

公開版本已將實際部署位址改為保留的文件範例位址；範例不是目前可用的端點。

當主機綁定 IP 變更，且 TAK Server、Mumble 與 MediaMTX 需要接受直接以 IP 建立的 TLS 連線時，使用 `scripts/renew_service_san.py`。此腳本分別簽發三張葉憑證，SAN 同時包含 `DNS:takbox.local` 與目前 `TAK_BIND_IP` 對應的 `IP:` 項目。簽發時沿用各服務的私鑰，以及目前的簽發 CA；不更換 CA、用戶端憑證、密碼、信任憑證鏈資料庫或 ATAK Data Package。舊服務憑證仍記錄於 CA 資料庫且維持有效，可供部署回復。

執行前，確認目前的 CA 輪替工作已結束、Docker Desktop 可用，並在專案根目錄執行指令。請妥善保護未納入版控的 `runtime/pki/service-san-renewals/` 目錄：其中暫存的 TAK PKCS#12 與 JKS 檔案含有服務私鑰。

## 預備與部署

1. 在 `.env` 設定 `TAK_BIND_IP` 與 `TAK_ALLOWED_SUBNET`，確認該 IP 已指派給這台 Windows 主機，並先完成對應的 Compose、mDNS 與防火牆設定。
2. 執行 `stage` 預備憑證。此步驟會簽發三張新葉憑證，驗證各自的憑證鏈、DNS SAN、IP SAN、私鑰是否相符，以及暫存的 TAK keystore；不會取代目前部署的檔案：

   ```powershell
   python .\scripts\renew_service_san.py stage --dns takbox.local --ip 192.0.2.2
   ```

3. 將指令輸出的絕對路徑填入 `$stagePath`。停止三個服務、套用暫存憑證，再重建容器，讓 Docker 重新掛載更換後的憑證檔案：

   ```powershell
   $stagePath = 'C:\absolute\path\printed\by\stage'
   docker compose stop tak-server mumble mediamtx
   python .\scripts\renew_service_san.py apply $stagePath
   docker compose up -d --force-recreate --no-deps tak-server mumble mediamtx
   ```

只要三個服務中仍有任何一個正在執行，`apply` 就會拒絕套用。套用前，腳本會確認目前的部署檔案與簽發 CA 自預備階段以來都未變更，並將 11 個待替換檔案的已驗證備份存於 `$stagePath/backup/`；若替換失敗，會嘗試還原備份。

部署後，檢查 `docker compose ps --all`；完成身分驗證後，查詢管理介面的 `/readyz`，並實際建立連往 `192.0.2.2:8443`、`192.0.2.2:40000` 與 `192.0.2.2:8322` 的 TLS 連線。僅以 `takbox.local` 執行容器健康檢查，無法證明服務已提供新的 IP SAN。TAK HTTPS 需要既有管理員用戶端憑證，才能完成 TLS 連線。

## 回復先前部署的葉憑證

若部署後有服務無法正常運作，停止相同的三個服務，再還原暫存目錄中的備份。回復前，腳本會確認目前部署檔案仍與此次暫存版本相符。回復不會倒轉 CA 序號計數，也不會撤銷回復後未再使用的新葉憑證。

```powershell
$stagePath = 'C:\absolute\path\printed\by\stage'
docker compose stop tak-server mumble mediamtx
python .\scripts\renew_service_san.py rollback $stagePath
docker compose up -d --force-recreate --no-deps tak-server mumble mediamtx
```

Mumble 在 Windows 上使用獨立的防火牆前景工作階段。目標網路介面連線後，執行 `scripts/Install-MumbleFirewall.ps1`；區網用戶端需要語音連線期間，請保持提權視窗開啟。要移除本次工作階段建立的規則，請在原始 PowerShell 視窗按 `Ctrl+C`。
