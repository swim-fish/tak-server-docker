# Mumble DNS-only 與 IP-only SAN 實測

日期：2026-09-22。版本：ATAK-CIV `5.7.0.15` release、Vx `2.1.0 (20251122) - [5.6.0]`、Mumble `v1.5.915-1`。

## 結果

| Mumble 葉憑證 SAN | Vx Address／Port | 實機結果 |
| --- | --- | --- |
| 只有 `DNS:takbox.local` | `takbox.local`／`40000` | 使用者確認 P1、A1 均成功 |
| 只有 `IP:192.168.137.1` | `192.168.137.1`／`40000` | 使用者確認 P1、A1 均成功；伺服器記錄兩次新登入及加入 Primary／Alternate |

因此，本次版本與信任設定下，Mumble SAN 可依 Vx Address 選擇 DNS 或 IP，不必兩者同時存在。要提供兩種入口時才同時加入。部署規則集中於[憑證頁](../security/certificates.md)。

## 方法與證據

1. 每次簽發前，備份原本 Mumble 葉憑證、完整鏈、私鑰、CSR、extension 設定及中繼 CA 資料庫。
2. 沿用既有 Mumble 私鑰與 CSR，以同一中繼 CA 簽發新葉憑證；只改 SAN，保留 `CN=takbox.local`、`CA:FALSE` 及 `serverAuth`。
3. 以 OpenSSL 驗證信任鏈、用途及本輪 DNS 或 IP。DNS-only 憑證另執行 IP 驗證，確認遭拒。
4. 更新葉憑證加中繼 CA 的 fullchain，重新建立 Mumble 容器。從實際 TLS 連線讀取 SAN，確認只有指定類型，並比對服務憑證與主機檔案指紋相同。
5. DNS 輪次確認 mDNS 回應；IP 輪次的容器健康檢查改用 `-verify_ip 192.168.137.1`。兩輪服務健康檢查均通過。
6. 使用者手動設定 Vx Address，重新加入 P1／A1 並回報結果；另擷取 Android 與 Mumble 日誌。成功判定依使用者回報及伺服器新 session 紀錄，不把本機 TLS 健康檢查當成 Vx 登入證據。

本輪沒有重建 CA、變更共用密碼或取消 Mumble 註冊身分，也沒有重新匯入 TAK DPK。

## APK 分析與驗收界線

APK 的 Mumble 信任管理器有 Android、TAK 與自訂憑證 fallback 分支。自訂名稱檢查接受 SAN type 2（DNS）或 type 7（IP）中任一與設定 host 相符的項目，以不分大小寫的字串比對處理；不要求兩種類型同時存在。此分支也有 CN fallback。

本輪沒有隔離實際採用的 trust-manager 分支。DNS 輪次的 CN 與 Address 相同；IP 輪次的 CN 仍是 `takbox.local`，Address 則是 IP。結果證明上述配置可用，不能推論所有分支都一定執行相同的 SAN 檢查，也未驗證「SAN 不符時 Vx 必然拒絕」。部署應使用相符 SAN，不依賴 CN fallback。

P1／A1 成功涵蓋登入與加入頻道，未驗收雙向 PTT、UDP 音訊傳輸或長時間連線品質。

## 測試後狀態與回復

IP 輪次結束時 Mumble 使用 IP-only 憑證，Vx 以 `192.168.137.1:40000` 完成驗證。其後依使用者要求，已還原原先通過測試的 DNS-only Mumble 憑證，重新建立容器並採用原本的 DNS 健康檢查；Vx Address 已改回 `takbox.local`、Port `40000`，使用者確認 P1、A1 均成功。回復後的 TLS、DNS 健康檢查、mDNS 與實際憑證指紋比對均通過。TAK 既有憑證與設定未修改。

bootstrap 後續改為不預填 DNS／IP，強制至少指定 `--host`（或 `--dns`）、`--ip` 其中一項，依輸入產生 DNS-only、IP-only 或 DNS＋IP；本專案教學明確指定 DNS。目前服務的 DNS-only 憑證不受此 CLI 調整影響。IP 輪次使用的健康檢查 override `runtime/device-vx-2026-09-22/compose.ip-only.yaml` 保留作為測試產物，目前服務不使用它。選用 IP 模式的操作範例見[Mumble 維運](../mumble/server.md#使用-ip-only-憑證)。

舊憑證及簽發前資料庫備份留在 `runtime/backups/`。回復服務憑證時，還原相符的葉憑證、fullchain、金鑰及 extension 設定，重建容器並核對實際 TLS 憑證；不要回退 CA 資料庫，以免重用已簽發的 serial。

原始 APK 分析、日誌及 TLS 驗證結果留在 Git 忽略的 `runtime/device-vx-2026-09-22/`。公開文件只保存去識別的結論，不加入原始日誌、裝置識別、私鑰或密碼。
