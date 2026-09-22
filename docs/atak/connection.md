# ATAK 連線與憑證 DPK

本頁處理 TAK 連線、CA 與裝置憑證。Vx 任務另外依[Vx 頁](vx-missions.md)從已連線的 TAK Server 下載。

## 匯入前

確認 TAK Server 已啟動、裝置在同一網路、`takbox.local` 可解析，且管理者已授予該裝置適當[群組](../tak-server/operations.md#新增一般憑證使用者)。每份裝置憑證 DPK 含私鑰與 PKCS#12 匯入密碼，只交付指定裝置，不上傳為共享任務包。

bootstrap 產物為 `runtime/packages/atak-local-test.dpk`，內容：

| 路徑 | 用途 |
| --- | --- |
| `MANIFEST/manifest.xml` | 宣告匯入項目及類型。 |
| `config/servers.pref` | 指定 TAK 連線、CA 及用戶端憑證位置／匯入密碼。 |
| `cert/caCert.p12` | Root CA 與中繼 CA 的公開信任資料。 |
| `cert/clientCert.p12` | 指定裝置私鑰及憑證鏈。 |

## 匯入與確認

1. 以受控方式把 DPK 放到裝置可選取的位置。
2. 在 ATAK 選 Import → Local SD，選擇該 DPK 並完成匯入。
3. 在 TAK Server 設定確認 `takbox.local:8089:ssl`。
4. 確認指定 TAK 伺服器連線成功，沒有憑證信任錯誤；必要時比對伺服器同時段紀錄。

成功代表 TAK 憑證連線可用，不代表 Vx 任務已建立。若失敗，先檢查名稱解析、憑證有效期及信任鏈，再看[疑難排解](../troubleshooting.md)。

## 設定是個別伺服器還是全域

本專案產生的 `servers.pref` 使用 `cot_streams` 的第 0 筆連線：

| 鍵 | 範圍 |
| --- | --- |
| `connectString0` | 這筆連線的 host、port、TLS 模式。 |
| `caLocation0`、`caPassword0` | 這筆連線的 CA 檔案及匯入密碼。 |
| `certificateLocation0`、`clientPassword0` | 這筆連線的用戶端憑證檔案及匯入密碼。 |

這些是附索引的個別 TAK Server 設定，不是設定 default 全域憑證。本次 Vx 實測能使用 ATAK 匯入的信任資料，但不能據此擴大為 Android 系統全域信任；詳細驗證條件見[憑證頁](../security/certificates.md#vx-驗證-mumble-的範圍)。

重匯入可能影響既有連線設定，先備份或記錄目標連線；不要假設把多份第 0 筆設定直接合併，就能得到多伺服器部署。此情境尚未驗收。

## 修正信任包而不重建 PKI

若既有 `caCert.p12` 缺少中繼 CA，而原始 CA、裝置 PKCS#12 及密碼仍正確，可重新打包：

```powershell
python ./scripts/rebuild_atak_data_package.py --host takbox.local --client-name atak-client
```

此工具重建信任庫與 DPK，沿用既有用戶端憑證；`--client-name` 不會簽發新身分。重新交付並匯入後再確認 TAK 連線。若是憑證到期、撤銷、私鑰遺失或 SAN 不符，重打包不能修復，應先處理 PKI。

Manifest 的實際 `contentType` 使用 `ATAK Preferences` 及 `P12 Certificate`；不要把說明文字或無空白別名當作格式值。來源：[bootstrap](../../scripts/bootstrap_local.py)、[重打包工具](../../scripts/rebuild_atak_data_package.py)、[實測紀錄](../validation/2026-09-21-tak-server-dpk.md)。
