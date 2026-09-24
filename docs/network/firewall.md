# Windows 防火牆與熱點

預設只允許熱點網段 `192.168.137.0/24` 存取主機 `192.168.137.1`。通訊埠清單以[版本與通訊埠](../reference/versions-and-ports.md)為準。

## 先確認介面

先啟用 Windows 行動熱點，再執行：

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -eq '192.168.137.1'
Get-NetIPInterface -AddressFamily IPv4 | Where-Object ConnectionState -eq 'Connected'
```

目標 IP 應為 `Preferred`，對應介面應為 `Connected`。此 IP 是 Android 使用的熱點 gateway，檢查重點是主機介面已啟用，不是上游網際網路 gateway 能否 ping。

## TAK 規則

`Install-TakFirewall.ps1` 目前不會自行請求 UAC，請在**管理員 PowerShell** 執行：

```powershell
./scripts/Install-TakFirewall.ps1
```

腳本建立持久的 `TAK-Local-CoT-8089` 與 `TAK-Local-Admin-8443` TCP 規則。重新執行會替換同名規則；變更網段時傳入 `-LocalAddress <HOST_IP> -RemoteAddress <CIDR>`。這些規則重開機後仍在，不需要每次重建。

需要取消時，在管理員 PowerShell 精確移除這兩個 DisplayName：

```powershell
Get-NetFirewallRule -DisplayName 'TAK-Local-CoT-8089','TAK-Local-Admin-8443' | Remove-NetFirewallRule
```

若移除錯誤，依原參數重新執行安裝即可恢復。

## Mumble 前景工作階段

在一般 PowerShell 執行，腳本會先檢查目標介面，再請求 UAC：

```powershell
./scripts/Install-MumbleFirewall.ps1
```

看到 `Mumble firewall active` 才代表規則建立成功。規則僅允許指定介面、IP、網段的 TCP／UDP 40000；每次執行使用獨立的規則名稱。自訂方式：

```powershell
./scripts/Install-MumbleFirewall.ps1 -LocalAddress <HOST_IP> -RemoteAddress <CIDR> -Port <HOST_PORT>
```

保留原始與提權後的視窗，後續 Docker 命令在另一個終端機執行。在原始視窗按 Ctrl+C，腳本通知提權工作階段停止並移除**本次建立的規則**；介面失效時也會結束。容器及 mDNS 繼續執行。

出現 `Existing Mumble firewall rules will be preserved` 表示另有既存規則。Ctrl+C 不會移除它們，因此不能由工作階段結束推論 Mumble 已完全阻擋。也不要用萬用字元刪除其他仍在使用的工作階段規則。

強制終止提權程序、直接關閉視窗或斷電，可能跳過清理。發生時以管理員權限列出 `TAK-Local-Mumble-*`，核對工作階段 ID，只移除已失效的那組：

```powershell
Get-NetFirewallRule -Name 'TAK-Local-Mumble-*' | Select-Object Name,DisplayName,Enabled
```

正常 Ctrl+C 後應看不到該組 `TAK-Local-Mumble-Session-<id>-...`；其他既存規則應保留。若仍有殘留，先確認對應工作階段已停止，再依完整 `Name` 處理。

## MediaMTX 規則

在一般 PowerShell 啟動，腳本先檢查目標 IP，再請求 UAC。它建立持久的 `TAK-Local-MediaMTX-TCP`（8554、8322）與 `TAK-Local-MediaMTX-UDP`（8000、8001、8004、8005）規則，限制主機位址、熱點介面及來源網段：

```powershell
./scripts/Install-MediaMtxFirewall.ps1
```

自訂主機與來源網段時傳 `-LocalAddress <HOST_IP> -RemoteAddress <CIDR>`，並同步調整 Compose port bind、名稱解析及憑證 SAN。重新執行會替換同名規則；移除時須在管理員 PowerShell 核對並精確移除這兩個 Name。規則允許封包進入，不保證 Docker Desktop UDP NAT 或用戶端回程可用；以實際串流驗證。

## 重新開機後

分享入口需要時使用 `./scripts/Install-SharePortalFirewall.ps1 -Port 10065`，只開放目前熱點下載通訊埠；管理頁 `127.0.0.1:10066` 不對裝置開放。若 `.env` 改變映射，防火牆 `-Port` 也須同步調整。詳見[分享與管理頁](../sharing/portal.md)。

1. 啟動 Docker Desktop，等待 Linux engine 可用。
2. 啟用熱點並確認主機 IP／網段。
3. 執行 `./scripts/Manage-WindowsMdns.ps1 -Action Start` 手動啟動 mDNS，再執行 `Test-WindowsMdns.ps1`；缺少排程或相依套件時依 [mDNS 頁](mdns.md)選「安裝／修復並啟動」。mDNS 不會隨重新開機自動啟動。
4. TAK／MediaMTX 持久規則若仍在且參數相同，可繼續沿用；Mumble 前景規則需要重新啟動工作階段。
5. 執行 `docker compose up -d`，確認服務 healthy，再由 Android 測試連線。

防火牆成功不代表名稱解析、TLS 或頻道登入成功，完整檢查見[疑難排解](../troubleshooting.md)。

依據：[TAK 腳本](../../scripts/Install-TakFirewall.ps1)、[Mumble 腳本](../../scripts/Install-MumbleFirewall.ps1)。前景清理的既有測試範圍見[驗證索引](../validation/README.md)。
