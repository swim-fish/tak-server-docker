# TAK Server 維運

服務須已依[從零建置](../getting-started.md)完成，`runtime/tak/`、secrets 與資料 volume 應屬於同一套部署。以下命令在專案根目錄執行。

## 啟動、檢視與停止

```powershell
docker compose up -d tak-db tak-server
docker compose ps
docker compose logs --tail 100 tak-db tak-server
```

`tak-db`、`tak-server` 應維持執行並回復 healthy。TAK 健康檢查使用管理憑證呼叫本機 API；首次啟動或權限未設定時，先檢視紀錄及下一節。不要把 API 健康等同於 Android 已連線。

暫停用 `docker compose stop tak-server tak-db`，再次啟動用上述 `up -d`。只修改 TAK 設定／CRL 後，可用 `docker compose restart tak-server`。修改 Compose 環境、secret 或掛載來源時，需重建受影響容器，不能只依賴 restart。

`docker compose down -v` 會移除資料 volume，不適用一般重新啟動或疑難排解。

## 管理憑證

bootstrap 產生的 `admin.pem` 及 `admin.p12` 位於 TAK certs 掛載目錄。授予管理權限：

```powershell
docker compose exec -w /opt/tak tak-server java -jar utils/UserManager.jar certmod -A certs/files/admin.pem
docker compose exec -w /opt/tak tak-server java -jar utils/UserManager.jar usermod -s admin
```

應看到管理員角色；管理 API 健康檢查應成功。瀏覽器存取 `https://takbox.local:8443` 時，管理端需匯入管理員 PKCS#12 與必要信任鏈。管理私鑰只交付管理者，不放進一般裝置 DPK。

## 新增一般憑證使用者

bootstrap 只簽發一張裝置憑證，不會自動為所有裝置建立群組。以下將已簽發的裝置憑證加入 `local-test` 群組：

```powershell
Copy-Item -LiteralPath ./runtime/pki/public/atak-client.crt.pem -Destination ./runtime/tak/certs/client.pem
docker compose exec -w /opt/tak tak-server java -jar utils/UserManager.jar certmod -g local-test certs/files/client.pem
docker compose exec -w /opt/tak tak-server java -jar utils/UserManager.jar usermod -s atak-client
```

若 bootstrap 使用自訂 `--client-name`，最後一行換成實際憑證 CN；公開檔名仍為 `atak-client.crt.pem`。變更前先備份 `runtime/tak/UserAuthenticationFile.xml`。

預期一般裝置沒有 `ROLE_ADMIN`，並具有預期的讀寫群組。實測中的 `ROLE_ANONYMOUS` 是一般使用者角色名稱，不代表略過 TLS 用戶端憑證驗證。裝置彼此是否能看見資料，仍需檢查群組交集。

這段手動流程只授權既有憑證，不會簽發更多裝置憑證。多裝置可改用[用戶端憑證控制台](certificate-console.md)逐筆簽發、指派群組與產生專屬 DPK；正式實機驗收項目列於該頁。誤授權時先停止交付，依備份及 UserManager 的實際設定修正；不要把 `-A` 套用到一般裝置。

## 維護與備份範圍

備份需同時涵蓋 PKI 簽發狀態、密碼、TAK 設定與 Docker 資料 volume，詳見[目錄參考](../reference/runtime-layout.md)。本專案尚無完成還原演練的整套備份腳本；只複製 `runtime/` 不包含 PostgreSQL 與 Mumble 資料庫。

CRL 更新及撤銷依[憑證頁](../security/certificates.md)處理。資料庫升級、既有 5.7 遷移與新憑證鏈輪替，應安排獨立備份／還原驗收，不直接對現用 volume 執行 bootstrap。

依據：[Compose](../../compose.yaml)、[TAK 實測](../validation/2026-09-21-tak-server-dpk.md)。
