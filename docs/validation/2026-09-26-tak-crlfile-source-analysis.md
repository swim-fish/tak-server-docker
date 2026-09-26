# TAK 5.8 `crlFile` 程式路徑核對

本頁核對本機 `takserver-docker-hardened-5.8-RELEASE-84` 發行套件。`tak-server-sdk-5.8` 只有外掛範例，沒有 TAK Core 的 Java 原始碼；下列程式路徑依發行版 `takserver.war` 的 class bytecode 反組譯與隨附 `CoreConfig.xsd` 判讀，不將推論當成另一版本的保證。

## 兩個設定位置

| `CoreConfig.xml` 位置 | XSD | 發行版程式路徑 |
| --- | --- | --- |
| `security/tls/crl/@crlFile` | 每個 `crl` 項目必填 | `com.bbn.marti.service.SSLConfig.initTrust` 逐筆讀取 CRL，放入 TAK 共用 PKIX trust manager 的憑證資料集合；`tak.server.ServerConfiguration.containerFactory` 另取**第一筆**，設定預設 Tomcat connector 的 CRL 檔。 |
| `network/connector/@crlFile` | 選填 | `tak.server.ServerConfiguration.configureConnector` 在欄位非 `null` 時，對該 connector 同時呼叫 `SSLHostConfig.setRevocationEnabled(true)` 與 `setCertificateRevocationListFile(...)`。本版 `containerFactory` 從 connector 清單索引 1 開始呼叫此方法，建立額外的 connector。 |

上述 XSD 分別見[HTTP connector 定義](../../vendor/takserver-docker-hardened-5.8-RELEASE-84/tak/CoreConfig.xsd)與同檔的 `security/tls/crl` 定義。Tomcat 10.1.55 隨 WAR 打包的 `SSLUtilBase.getParameters` 會在 CRL 檔非空時加入該檔的憑證撤銷清單，並將 PKIX 撤銷檢查設為啟用；因此預設 connector 只透過全域第一筆 CRL 取得檔案，也可能實際拒絕已撤銷憑證。

## 本機 8443 的判讀

目前 `runtime/tak/CoreConfig.xml` 只有一個 `8443` HTTP connector：其 `network/connector/@crlFile` **未設定**，但 `security/tls/crl` 已設定作用中中繼 CA、舊中繼 CA 與 Root CA 等項目，第一筆是作用中中繼 CA 的 CRL。按上述 bytecode，這個唯一的預設 connector 會取得**第一筆全域 CRL**，不能因 connector 欄位為空就宣稱 8443 沒有 TLS 層撤銷檢查。[撤銷前後實測](2026-09-24-qr-e2e-revocation.md)亦確認同一張用戶端葉憑證在撤銷前可從 8443 取得 HTTP 200，撤銷後的新 TLS 請求遭拒；使用者再次確認撤銷後 8443 無法使用。

這不表示 8443 自動載入 `security/tls/crl` 的**全部**項目。這份發行版的 `ServerConfiguration` 只把第一筆交給預設 Tomcat connector；8089 使用的 `SSLConfig.initTrust` 則遍歷全域 CRL 清單。因此，不能用這次單張葉憑證的 8443 結果，宣稱 Root CRL 對舊中繼 CA 鏈已在 8443 生效。舊中繼 CA 撤銷仍須分別核對 8443 的新 TLS 連線、信任憑證鏈資料庫與實際載入的 CRL。

## 後續設定原則

- 單一 8443 connector 的現況有作用中中繼 CA 葉憑證撤銷的前後對照，無須為了重現此結果而盲目再加同一路徑的 connector `crlFile`。
- 若加入第二個 HTTP connector，應為該 connector 明確設定並測試 `crlFile`；不要假設預設 connector 的 customizer 會套用到額外 connector。
- 若要在 8443 驗證多個簽發 CA 的撤銷，須先確認其 TLS 實際使用的 CRL 檔內容與信任鏈，再逐條使用撤銷前後的測試憑證驗收。修改設定後需依 `CoreConfig.xsd` 驗證並重新啟動 TAK Server；本次分析沒有修改服務設定。
