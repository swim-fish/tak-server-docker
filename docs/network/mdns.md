# Windows mDNS

本頁管理 Windows 主機的 `takbox.local` 公告。操作前確認 `.env` 的 `TAK_BIND_IP` 是主機目前的 Wi-Fi 或行動熱點 IPv4 位址，`TAK_ALLOWED_SUBNET` 涵蓋裝置所在網段，且 Android 已連上該網路。預設範例使用 `192.168.137.1/24`；本機目前的 Wi-Fi 設定以 Git 忽略的 `.env` 為準。

## 為什麼採用 mDNS

部署 Vx 與 Mumble 時，應提供受信任的 CA 鏈及與 Address 相符的 SAN。本機實測已確認：匯入 TAK 連線的 CA 信任鏈後，Vx 能驗證同一中繼 CA 簽發的 Mumble 葉憑證。詳細範圍見[憑證與信任鏈](../security/certificates.md)。

固定使用 `takbox.local`，可讓用戶端的 Address 與 `DNS:takbox.local` SAN 保持一致。直接輸入 IP 也可行，但必須有相符的 IP SAN。mDNS 負責解析名稱；CA 信任、憑證簽發與防火牆仍須各自設定。

DNS-only 與 IP-only 憑證均已通過 Vx P1／A1 登入及加入頻道測試，SAN 可依 Address 擇一。直接以 IP 連線的 Mumble 不需要 mDNS；本專案預設採用 mDNS，是為了固定名稱並降低主機 IP 改變時的憑證更新需求。TAK 若仍使用 `takbox.local`，仍須保留名稱解析。詳見[實測紀錄](../validation/2026-09-22-mumble-san.md)。

Responder 在 Windows 主機執行，公告 `.env` 的 `TAK_BIND_IP`，避免發出 Docker bridge 位址。例如預設熱點設定為：

```text
takbox.local. A 192.168.137.1
ATAK Voice._mumble._tcp.local. SRV takbox.local.:40000
TAK CoT TLS._tak-cot._tcp.local. SRV takbox.local.:8089
```

Vx 手動輸入主機時主要使用 A record；SRV 記錄供服務探索與診斷，不能據此假設 Vx 自動採用公告通訊埠。

## 安裝與修復

先確認 Python 3.14 已安裝於 `C:/Python314/python.exe`；目前管理腳本固定使用此路徑，沒有 Python 路徑參數。再於一般 PowerShell 開啟互動式選單，選擇「安裝／修復並啟動」，需要時核准 UAC：

```powershell
./scripts/Manage-WindowsMdns.ps1
./scripts/Test-WindowsMdns.ps1
```

管理腳本的安裝／修復選項讀取 `.env`，建立 `runtime/mdns/.venv`、安裝固定版本的相依套件並檢查 `zeroconf`／`ifaddr`，寫入 `config.json`，設定 UDP 5353 防火牆與 `TAK-mDNS-Responder` 排程工作，再啟動及查詢公告。排程工作**沒有自動觸發器**；重新開機或登入後不會自行啟動。網路介面啟用後可從選單選「啟動公告」，或執行 `./scripts/Manage-WindowsMdns.ps1 -Action Start`。選「停止公告」只會停止 responder，保留設定與防火牆規則。

成功時測試應找到兩筆預期服務記錄。在 Android 可用已授權的 ADB 驗證：

```powershell
adb -s <ATAK_DEVICE_ID> shell ping -c 1 takbox.local
```

應先看到解析為主機 IP；ICMP 回應與否另受防火牆影響。名稱解析成功後，仍需由 ATAK／Vx 實際連線驗證。

若出現 `No module named 'ifaddr'`、排程不存在或 runtime 遺失，重新選「安裝／修復並啟動」，再測試。`Test-WindowsMdns.ps1` 只查詢，不負責修復。安裝失敗時檢視 `runtime/mdns/install-error.log`；執行狀態檢視 `runtime/mdns/responder.log`。分享紀錄前先移除本機識別資料。

## 變更名稱或網段

名稱可保持不變而重新公告 IP，但服務綁定與防火牆仍要同步修改：

1. 確認主機新 IP 已存在且介面連線正常。
2. 在 `.env` 設定 `TAK_BIND_IP=<HOST_IP>` 與 `TAK_ALLOWED_SUBNET=<CIDR>`；這兩個值供 Compose、mDNS 和防火牆腳本共用。
3. 執行 `Manage-WindowsMdns.ps1 -Action Install` 重建公告及 mDNS 防火牆規則。名稱或通訊埠有變更時可傳入 `-Hostname`、`-MumblePort`／`-TakPort`。
4. 執行 `python .\scripts\update_viewer_network.py` 更新既有 MediaMTX WebRTC ICE 候選位址；此工具不會重簽憑證或變更觀看帳密。首次建置時 `provision_mediamtx.py` 已讀取 `.env`，可略過此步。
5. 依[防火牆頁](firewall.md)更新服務規則，執行 `docker compose --profile sharing up -d` 重建受影響的容器，並執行 `docker compose restart media-viewer` 載入新的 ICE 位址。
5. 若 DNS 名稱改變，重新簽發含新 SAN 的獨立伺服器憑證，更新 TAK DPK 與 Vx Address。只改 IP、用戶端仍以既有 DNS SAN 連線時，不必因 IP 改變而重簽 DNS 憑證；直接用新 IP 連線則需要新 IP SAN。

現有腳本沒有保留既有 PKI 的自動伺服器憑證輪替功能。已有部署時先規劃簽發及回復方式，不要用 `bootstrap_local.py --force` 代替輪替。

`.local` 用於本地鏈路的 mDNS；跨 VLAN／VPN 不應假設會直接解析。此範圍依據 [RFC 6762](https://www.rfc-editor.org/rfc/rfc6762.html)。Linux、Router 與一般 DNS 的遷移規劃見[後續計畫](../plans/roadmap.md#linux-與跨網段名稱解析)。

## 移除

一般 PowerShell 在管理選單選「移除設定與防火牆規則」，或執行下列指令，並核准 UAC：

```powershell
./scripts/Manage-WindowsMdns.ps1 -Action Uninstall
```

這會停止並刪除排程與 mDNS 防火牆規則。確定不需保留專用環境及紀錄時，可加 `-RemoveRuntime`，只移除 `runtime/mdns/`，不處理 TAK／Mumble 容器或 PKI。互動式選單會另外詢問是否移除 runtime。自訂排程名稱時，安裝、啟動、測試、移除均須使用相同 `-TaskName`。

移除後不應再有該排程及規則；若仍能暫時解析，先考慮用戶端快取或其他 responder。需要恢復時重新安裝並查詢。

依據：[管理腳本](../../scripts/Manage-WindowsMdns.ps1)、[查詢](../../scripts/Test-WindowsMdns.ps1)、[實機紀錄](../validation/2026-09-21-windows-mdns.md)。
