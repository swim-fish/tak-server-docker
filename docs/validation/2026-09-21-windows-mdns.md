# Windows mDNS 驗證紀錄

## 紀錄資訊

| 項目 | 值 |
| --- | --- |
| 驗證日期 | `2026-09-21` |
| Windows 主機名稱 | `<WINDOWS_HOST>` |
| Windows mDNS 介面 | `192.168.137.1` |
| 發布名稱 | `takbox.local` |
| Android 裝置 | Samsung `<ANDROID_DEVICE_MODEL>`，序號 `<ATAK_DEVICE_ID>` |
| Android | `16`／API `36` |
| Python | `3.14.7` |
| python-zeroconf | `0.151.3` |
| ifaddr | `0.2.0` |

## 部署內容

Windows 主機執行專案內的 mDNS responder，未從 Docker 容器直接發布 multicast。這可避免 Docker Desktop／WSL2 NAT 公告容器內部位址。

發布內容：

```text
takbox.local. A 192.168.137.1
ATAK Voice._mumble._tcp.local. SRV takbox.local.:40000
TAK CoT TLS._tak-cot._tcp.local. SRV takbox.local.:8089
```

安裝結果：

- 建立 `TAK-mDNS-Responder` 使用者登入排程工作。
- Responder 綁定 `192.168.137.1:5353/UDP`。
- Python virtual environment 位於 `runtime/mdns/.venv`。
- 實際設定位於 `runtime/mdns/config.json`。
- Responder 記錄位於 `runtime/mdns/responder.log`。
- `runtime/` 已加入 `.gitignore`，不提交執行環境與本機狀態。

## 防火牆範圍

建立下列規則：

| 規則 | 方向 | 本機範圍 | 遠端範圍 |
| --- | --- | --- | --- |
| `TAK-mDNS-Responder-In` | Inbound UDP | `192.168.137.1:5353` | `192.168.137.0/24` |
| `TAK-mDNS-Responder-Out` | Outbound UDP | `192.168.137.1:5353` | `192.168.137.0/24`、`224.0.0.251` |

兩條規則都限制為專案 virtual environment 的 `python.exe`，套用 Domain、Private 與 Public profile。未開放其他本機介面或遠端子網路。

## 驗證結果

### DNS-SD 記錄

使用專案 `mdns/query.py` 查詢 responder：

```text
OK ATAK Voice._mumble._tcp.local. -> takbox.local. 192.168.137.1:40000
OK TAK CoT TLS._tak-cot._tcp.local. -> takbox.local. 192.168.137.1:8089
```

結果：通過。

### Android mDNS 解析

從實機執行：

```powershell
adb -s <ATAK_DEVICE_ID> shell ping -c 2 -W 3 takbox.local
```

結果：

```text
PING takbox.local (192.168.137.1)
2 packets transmitted, 2 received, 0% packet loss
```

結果：通過。Android 已把 `takbox.local` 解析為 `192.168.137.1`。

### Android 至 Mumble TCP

從實機執行：

```powershell
adb -s <ATAK_DEVICE_ID> shell toybox nc -z -w 3 takbox.local 40000
```

通訊埠移轉後的預期結束狀態碼為 `0`。Android 裝置未連接 ADB，因此未直接執行此命令；但 Mumble 已在 `40000` 記錄 Android `Mumla 3.7.3` client 完成驗證並加入具名頻道。Windows host、Docker port publish、TLS 與實際 client TCP 路徑均已通過。

### TLS 主機名稱

使用 TAK Root CA、Mumble 憑證及 `takbox.local` 驗證：

```text
TLS version: TLSv1.3
subject: C=TW, O=TAK Local, OU=Local Test, CN=takbox.local
issuer: CN=TAK Local Issuing CA
SAN: DNS:takbox.local, IP:192.168.137.1
```

結果：通過。憑證 chain 由 TAK Root CA 驗證成功，且 `takbox.local` 符合 DNS SAN。

## 待辦事項

1. 在 Android 實機重跑 `toybox nc -z -w 3 takbox.local 40000`，補齊直接的 mDNS／TCP 診斷紀錄。
2. 確認 Mumble 日誌或 Vx diagnostics 顯示 UDP transport。
3. 使用第二個語音用戶端完成雙向 PTT 驗證。

## 維運與移除

檢查 responder：

```powershell
.\scripts\Test-WindowsMdns.ps1
```

若測試出現 `ModuleNotFoundError: ifaddr`、`No module named pip` 或 mDNS Python environment 不完整，代表 `runtime/mdns/.venv` 不完整。重新執行下列安裝腳本並核准 Windows UAC；腳本會重建損壞的 virtual environment、重新安裝固定版本相依套件、執行 `pip check`，並重新建立排程工作：

```powershell
.\scripts\Install-WindowsMdns.ps1
.\scripts\Test-WindowsMdns.ps1
```

完整移除排程工作、防火牆規則及 runtime：

```powershell
.\scripts\Uninstall-WindowsMdns.ps1 -RemoveRuntime
```

解除安裝腳本可從一般 PowerShell 執行，並在需要時顯示 Windows UAC；提高權限後仍會保留 `-RemoveRuntime`。移除 mDNS 不會刪除 TAK、Mumble 或其憑證及資料。
