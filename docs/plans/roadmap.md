# 後續計畫與驗收條件

以下尚未完成，不是現行啟動指令。已實作範圍見[架構](../architecture.md)，先前設計見[歷史資料](../archive/README.md)。

## 引導式佈建與分享

引導頁、批次憑證簽發、Vx 伺服器端固定名稱替換、ICU 組別／人員與 Advanced 自訂路徑、小隊／設備發布身分、熱點匿名 WebRTC、控制台預覽與開關已有本機實作，見[驗證紀錄](../validation/2026-09-24-guided-provisioning.md)及[MediaMTX 管理](../mediamtx/management.md)。仍需新憑證 DPK 的 Android 匯入、替換後 Vx 的實機更新行為、外網公開 DNS／HTTPS／ICE、跨瀏覽器與多裝置驗收。操作順序、失敗恢復及完整驗收見[引導式佈建與分享計畫](guided-provisioning.md)。

## 語音與任務部署

使用者已確認手機的 Vx 雙頻道語音可用；此回報未附雙向按鍵、UDP 封包及延遲紀錄。下表保留需要分別驗收的範圍。

| 項目 | 完成條件 |
| --- | --- |
| 雙向 PTT／UDP | 已有手機雙頻道語音成功回報；仍需記錄兩台用戶端在各頻道的雙向傳送、UDP 路徑、延遲、斷線重連與 TCP fallback。 |
| VS1／VS2 按鍵 | 實體 PTT1／PTT2 對應正確，不誤送另一頻道。 |
| 任務重複部署 | 分別測同 UUID 重複下載、新 UUID 同名任務的覆寫／去重行為。 |
| 多裝置憑證 | 每台獨立簽發、授權、交付、撤銷，驗證不影響其他裝置。 |

## MediaMTX 後續驗收

MediaMTX RTSP／RTSPS、publish／read 權限、獨立中繼 CA 簽發憑證及 Compose TCP／UDP 對應已實作，見[MediaMTX 操作](../mediamtx/server.md)及[實測紀錄](../validation/2026-09-23-mediamtx.md)。TAK ICU 7.5.1 已經由 RTSPS＋帳密發布實機影像，FFmpeg 獨立讀取成功。

仍須由實際 LAN 裝置測 UDP RTP／RTCP 與 SRTP／SRTCP 的發布及讀取。獨立 Docker bridge 經 Windows 發布通訊埠的 UDP 讀取未成功；需分辨 Docker Desktop NAT 與用戶端回程路徑，不把 Compose 內 UDP 成功當成外部 UDP 通過。ATAK 5.7.0.15 已用手動 RTSP 來源、讀取帳密及 Reliable／TCP 成功觀看 ICU 影像；ICU 自動通告的 RTSPS 來源被辨識為 RAW，後續須規劃相容的影像通告方式。ICU 對不受信任憑證的拒絕行為仍未驗收。

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
