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

## 部署內容

Windows 主機執行專案內的 mDNS responder，未從 Docker 容器直接發布 multicast。這可避免 Docker Desktop／WSL2 NAT 公告容器內部位址。

發布內容：

```text
takbox.local. A 192.168.137.1
ATAK Voice._mumble._tcp.local. SRV takbox.local.:64400
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
OK ATAK Voice._mumble._tcp.local. -> takbox.local. 192.168.137.1:64400
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
adb -s <ATAK_DEVICE_ID> shell toybox nc -z -w 3 takbox.local 64400
```

結束狀態碼為 `0`。

結果：通過。裝置可使用 mDNS 名稱連到 Windows 發布的 Mumble TCP 通訊埠。

### TLS 主機名稱

使用現有 Mumble 憑證及 `takbox.local` 驗證：

```text
subject=CN=192.168.137.1
issuer=CN=ATAK Local Voice CA
Verify return code: 62 (hostname mismatch)
```

結果：符合預期。mDNS 網路層已完成，但現有 Mumble 憑證沒有 `DNS:takbox.local` SAN，因此尚不可在 Vx 改用該名稱。

## 待辦事項

1. 由規劃中的 TAK 中繼 CA 重新簽發 Mumble server certificate。
2. TAK 與 Mumble server certificate 都加入：

   ```text
   DNS:takbox.local
   IP:192.168.137.1
   ```

3. 使用新憑證重新驗證 chain、`serverAuth`、SAN 及有效期。
4. 將 DPK 的 `connectString0` 改為 `takbox.local:8089:ssl`。
5. 將 Vx Mumble Address 改為 `takbox.local`，完成 TLS 與登入測試。
6. 在一般 Windows 使用者登入、重新啟動電腦及網路介面重連後，重跑 `scripts/Test-WindowsMdns.ps1`。

完成上述項目前，TAK 與 Vx 的核心驗證繼續使用 `192.168.137.1`。

## 維運與移除

檢查 responder：

```powershell
.\scripts\Test-WindowsMdns.ps1
```

完整移除排程工作、防火牆規則及 runtime：

```powershell
.\scripts\Uninstall-WindowsMdns.ps1 -RemoveRuntime
```

移除 mDNS 不會刪除 TAK、Mumble 或其憑證及資料。
