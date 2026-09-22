# 後續計畫與驗收條件

以下尚未完成，不是現行啟動指令。已實作範圍見[架構](../architecture.md)，先前設計見[歷史資料](../archive/README.md)。

## 語音與任務部署

| 項目 | 完成條件 |
| --- | --- |
| 雙向 PTT／UDP | 兩台用戶端在各頻道雙向傳送；核對 UDP 路徑、延遲、斷線重連與 TCP fallback。 |
| VS1／VS2 按鍵 | 實體 PTT1／PTT2 對應正確，不誤送另一頻道。 |
| 任務重複部署 | 分別測同 UUID 重複下載、新 UUID 同名任務的覆寫／去重行為。 |
| 多裝置憑證 | 每台獨立簽發、授權、交付、撤銷，驗證不影響其他裝置。 |

## MediaMTX 與 UDP

Compose 尚無 MediaMTX。第一階段沿用原計畫的 RTSP 控制 TCP 8554、單播 RTP UDP 8000、RTCP UDP 8001，明確啟用 TCP／UDP transport。映像版本與設定鍵須在實作時依選定版本確認。

需要分別設定 publish／read 權限、Compose UDP 對應及主機防火牆，用另一台 LAN 裝置驗證發布與讀取。遇到 UDP 不可用時，另驗證 RTSP over TCP，不把 TCP 成功當成 UDP 通過。

本機 `rtsp://` 不需要 TLS 憑證，但缺少 TLS 保護，僅列入受信任 LAN／VPN 情境。日後改用 RTSPS 時，採獨立伺服器私鑰與完整鏈，另驗證 ATAK／攝影機／播放器相容性；安全媒體 transport 與通訊埠依選定版本再定案。不共用 TAK 伺服器私鑰。

## 公開 8446 與 Let's Encrypt

目前 bootstrap 移除 8446 connector，Compose 也未發布；尚無 Certbot 或公開憑證部署服務。未來先選定可驗證的公開 FQDN；`takbox.local` 僅供本機 mDNS 使用。

原設計採 DNS-01，將 DNS API 權限限制在必要 challenge 記錄。若採 HTTP-01，驗證必須可由外部連入 TCP 80；只開 8446 無法完成。驗證方式依 [Let's Encrypt 官方說明](https://letsencrypt.org/docs/challenge-types/)。

TAK 公開 connector 規劃使用獨立 keystore，保留既有私有 CA 與裝置簽發流程。公開伺服器憑證不取代 TAK 用戶端驗證或帳號授權。Connector 的登入模式及存取政策需在對外開放前另外確認。

驗收需涵蓋 staging 簽發、SAN／鏈／私鑰檢查、原子替換、服務重載、續期排程、失敗保留舊憑證及回復演練。現階段沒有可直接執行的 `public-cert-stage` 腳本或 Compose profile。

## Linux 與跨網段名稱解析

同一 Layer 2 網段可規劃 Linux host 的 Avahi 公告 `takbox.local`，發布實際 LAN IP，並允許必要的 UDP 5353 multicast；不公告 Docker bridge IP。保留相同 DNS SAN 時，仍須調整服務綁定與防火牆。

跨 VLAN／VPN 優先規劃 Router／內部 DNS、DHCP 下發 resolver 與路由規則，使用組織持有網域下的內部名稱。名稱變更後同步更新兩個伺服器的 SAN、TAK DPK 與 Vx Address。`.local` 不作為一般 unicast DNS zone；若保留它跨網段使用，須另外驗證 mDNS reflector 及存取邊界，見 [RFC 6762](https://www.rfc-editor.org/rfc/rfc6762.html)。

驗收應由實際 Android 網段完成解析、TLS、登入與語音測試。現有 Windows 排程、UAC 與防火牆腳本不能直接搬到 Linux 執行。

## 備份、PKI 與其他服務

- 建立一致的 PostgreSQL、Mumble、PKI／CA 資料庫及 secrets 備份／還原流程；現有 Mumble 管理操作備份不等於全系統備援。
- 補齊 CRL 定期更新、到期通知及保留既有 CA 的葉憑證輪替；目前依[憑證頁](../security/certificates.md)手動處理。
- TAK 5.7 資料庫遷移與 hardened 版本升級需先在隔離環境驗證回復流程。
- Federation Hub 需另外決定對等信任、路由與群組政策，尚未加入此 Compose。

- 將 Windows mDNS 的固定 Python 3.14 路徑改成可設定或可偵測，並測試乾淨 Windows 環境；目前須依建置頁安裝到指定位置。
