# Windows mDNS

本頁管理 Windows 主機的 `takbox.local` 公告。操作前啟用行動熱點，確認主機已持有 `192.168.137.1`，Android 已連上相同網段。不同位址請先看[變更名稱或網段](#變更名稱或網段)。

## 為什麼採用 mDNS

Vx 驗證 Mumble 伺服器時，必須同時通過 CA 信任鏈與 Address 對憑證 SAN 的比對。本機實測已確認：匯入 TAK 連線的 CA 信任鏈後，Vx 能驗證同一中繼 CA 簽發的 Mumble 葉憑證。詳細範圍見[憑證與信任鏈](../security/certificates.md)。

固定使用 `takbox.local`，可讓用戶端的 Address 與 `DNS:takbox.local` SAN 保持一致。直接輸入 IP 也可行，但必須有相符的 IP SAN。mDNS 負責解析名稱；CA 信任、憑證簽發與防火牆仍須各自設定。

Responder 在 Windows 主機執行，公告熱點 IP，避免發出 Docker bridge 位址。現行記錄為：

```text
takbox.local. A 192.168.137.1
ATAK Voice._mumble._tcp.local. SRV takbox.local.:40000
TAK CoT TLS._tak-cot._tcp.local. SRV takbox.local.:8089
```

Vx 手動輸入主機時主要使用 A record；SRV 記錄供服務探索與診斷，不能據此假設 Vx 自動採用公告通訊埠。

## 安裝與修復

先確認 Python 3.14 已安裝於 `C:/Python314/python.exe`；目前安裝腳本固定使用此路徑，沒有 Python 路徑參數。再於一般 PowerShell 執行，需要時核准 UAC：

```powershell
./scripts/Install-WindowsMdns.ps1
./scripts/Test-WindowsMdns.ps1
```

安裝腳本建立 `runtime/mdns/.venv`、安裝固定版本的相依套件並檢查 `zeroconf`／`ifaddr`，寫入 `config.json`，設定 UDP 5353 防火牆與 `TAK-mDNS-Responder` 排程工作，再啟動及查詢公告。排程觸發點是**使用者登入**；不能當成尚未登入時就會啟動的系統服務。

成功時測試應找到兩筆預期服務記錄。在 Android 可用已授權的 ADB 驗證：

```powershell
adb -s <ATAK_DEVICE_ID> shell ping -c 1 takbox.local
```

應先看到解析為主機 IP；ICMP 回應與否另受防火牆影響。名稱解析成功後，仍需由 ATAK／Vx 實際連線驗證。

若出現 `No module named 'ifaddr'`、排程不存在或 runtime 遺失，重新執行安裝，再測試。`Test-WindowsMdns.ps1` 只查詢，不負責修復。安裝失敗時檢視 `runtime/mdns/install-error.log`；執行狀態檢視 `runtime/mdns/responder.log`。分享紀錄前先移除本機識別資料。

## 變更名稱或網段

名稱可保持不變而重新公告 IP，但服務綁定與防火牆仍要同步修改：

1. 確認主機新 IP 已存在且介面連線正常。
2. 修改 `compose.yaml` 各服務的主機綁定位址；Mumble 的 TCP、UDP 對應應一致。
3. 以 `Install-WindowsMdns.ps1 -Address <HOST_IP> -Hostname <HOSTNAME> -RemoteSubnet <CIDR>` 重建公告。通訊埠有變更時一併傳入 `-MumblePort`／`-TakPort`。
4. 依[防火牆頁](firewall.md)更新服務規則與允許網段，再重建受影響的容器。
5. 若 DNS 名稱改變，重新簽發含新 SAN 的獨立伺服器憑證，更新 TAK DPK 與 Vx Address。只改 IP、用戶端仍以既有 DNS SAN 連線時，不必因 IP 改變而重簽 DNS 憑證；直接用新 IP 連線則需要新 IP SAN。

現有腳本沒有保留既有 PKI 的自動伺服器憑證輪替功能。已有部署時先規劃簽發及回復方式，不要用 `bootstrap_local.py --force` 代替輪替。

`.local` 用於本地鏈路的 mDNS；跨 VLAN／VPN 不應假設會直接解析。此範圍依據 [RFC 6762](https://www.rfc-editor.org/rfc/rfc6762.html)。Linux、Router 與一般 DNS 的遷移規劃見[後續計畫](../plans/roadmap.md#linux-與跨網段名稱解析)。

## 移除

一般 PowerShell 執行並核准 UAC：

```powershell
./scripts/Uninstall-WindowsMdns.ps1
```

這會停止並刪除排程與 mDNS 防火牆規則。確定不需保留專用環境及紀錄時，可加 `-RemoveRuntime`，只移除 `runtime/mdns/`，不處理 TAK／Mumble 容器或 PKI。自訂排程名稱時，安裝、測試、移除均須使用相同 `-TaskName`。

移除後不應再有該排程及規則；若仍能暫時解析，先考慮用戶端快取或其他 responder。需要恢復時重新安裝並查詢。

依據：[安裝](../../scripts/Install-WindowsMdns.ps1)、[查詢](../../scripts/Test-WindowsMdns.ps1)、[移除](../../scripts/Uninstall-WindowsMdns.ps1)、[實機紀錄](../validation/2026-09-21-windows-mdns.md)。
