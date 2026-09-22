# 疑難排解

先記錄操作時間、套件名稱與症狀，再依「網路 → TLS → 使用者 → 頻道／音訊」查詢。不要先重建 PKI、清空 volume 或重設 ATAK，避免失去原始問題與身分資料。

## 依症狀查詢

| 症狀 | 先確認 | 接續處理 |
| --- | --- | --- |
| 重開機後全部不通 | 熱點 IP、Docker engine、mDNS 排程、前景防火牆 | [重新開機流程](network/firewall.md#重新開機後) |
| mDNS 缺 `ifaddr` 或找不到排程 | 安裝是否成功、專用 venv 是否完整 | [重新安裝與測試](network/mdns.md#安裝與修復) |
| `unknown host` | Android 是否解析到主機 IP、是否跨 VLAN／VPN | [mDNS 範圍](network/mdns.md) |
| IP 可連，名稱不可連 | A record 與名稱拼字、VPN／resolver | 先修解析，再核對 DNS SAN |
| `unknown issuer`／`import certificate` | CA 信任庫是否含 Root 及中繼 CA、裝置時間 | [信任鏈](security/certificates.md)、[重打包](atak/connection.md#修正信任包而不重建-pki) |
| `hostname mismatch`／IP mismatch | Vx Address 是否與葉憑證 SAN 相同 | 修正 Address 或重簽正確 SAN，不關閉 TLS 驗證 |
| TAK 健康檢查失敗 | 資料庫、管理憑證權限、CRL 有效期、紀錄 | [TAK 維運](tak-server/operations.md) |
| Mumble 每 30 秒本機 TLS 連上又關閉 | 來源是否 `127.0.0.1`、是否吻合 healthcheck | [健康檢查說明](mumble/server.md#啟動與檢查) |
| Vx 無法加入頻道 | Channel 是否空白、ID 是否存在、ACL 是否允許 | [頻道建立](mumble/server.md#建立-primary-與-alternate) |
| Vx DPK 匯入後無 Mission | 是否走 Local SD 而非 Server Download | [正確下載流程](atak/vx-missions.md#從-tak-server-下載任務) |
| Vx 沒有密碼提示 | 是否已有密碼快取或註冊身分 | [密碼行為](atak/vx-missions.md#輸入密碼) |
| 換密碼後仍能登入 | 註冊身分可能略過共用密碼檢查 | [註冊管理](mumble/users.md) |
| 取消註冊後使用者又出現 | 是否重新通過驗證並自行註冊 | 取消註冊不是永久封鎖 |
| 頻道已連線但沒有聲音 | 麥克風權限、VS1／VS2、PTT 指派、UDP 與另一用戶端 | 按[音訊驗收](validation/README.md#待完成的實機驗收)另測 |

## 最小診斷命令

```powershell
docker compose ps
docker compose logs --tail 100 tak-db tak-server mumble
./scripts/Test-WindowsMdns.ps1
Test-NetConnection -ComputerName takbox.local -Port 8089
Test-NetConnection -ComputerName takbox.local -Port 40000
```

TCP 測試只代表主機可以建立 TCP 連線，不驗證 Android 路徑、TLS、密碼或 UDP。若主機通但 Android 不通，轉查來源網段、防火牆工作階段與裝置網路。

紀錄可能包含呼號、裝置 ID、網路位址及套件資訊。保留原始證據於受控 runtime，對外只提供去識別的相關片段；不要附整份 logcat、DPK、secrets 或資料庫。

## 通訊埠占用與排除範圍

Docker 回報 bind 失敗時，先查主機占用及 Windows 排除範圍：

```powershell
Get-NetTCPConnection -LocalPort 40000 -ErrorAction SilentlyContinue
Get-NetUDPEndpoint -LocalPort 40000 -ErrorAction SilentlyContinue
netsh interface ipv4 show excludedportrange protocol=tcp
netsh interface ipv4 show excludedportrange protocol=udp
```

40000 位於預設動態範圍之外，仍可能被其他服務占用。需要改通訊埠時，同步調整 Compose 的 TCP／UDP、Mumble 防火牆、mDNS SRV 與 Vx 任務，見[網路變更](network/mdns.md#變更名稱或網段)。通訊埠不屬於 SAN，單純改 port 不要求重簽憑證。
