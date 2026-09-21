# Mumble 本機伺服器驗證紀錄

## 範圍

本紀錄涵蓋 2026-09-21 在 Windows 11、Docker Desktop／WSL2 與 Android 實機 `<ATAK_DEVICE_ID>` 完成的 Mumble 伺服器端驗證。改用 `40000` 後，Android Mumla client 已重新通過 TLS、密碼驗證與具名子頻道加入。雙向 PTT 與 UDP 語音仍需第二個用戶端驗證。

## Compose 設定

| 項目 | 值 |
| --- | --- |
| Image | `mumblevoip/mumble-server:v1.5.915-1` |
| Container port | `64738/TCP`、`64738/UDP` |
| Windows host port | `192.168.137.1:40000/TCP`、`192.168.137.1:40000/UDP` |
| Container process | UID/GID `10000:10000` |
| Client authentication | `certrequired=false`，使用一般 server password |
| Persistent data | `mumble-data:/data` |

Windows 預設 UDP dynamic port range 是 `49152–65535`。HNS／WinNAT 的 UDP excluded port range 曾先後涵蓋 `64738` 與 `64400`，而且重新啟動後區間會移動。因此標準 Mumble container port 維持 `64738`，Windows 對外改用動態範圍之外的 `40000`。`scripts/Install-MumbleFirewall.ps1` 只允許本機位址 `192.168.137.1` 與遠端子網路 `192.168.137.0/24` 的 `40000/TCP+UDP`。

一般 server password、SuperUser password 與 TLS private key passphrase 都由 Compose secrets 掛載，不寫入 Compose 或日誌。Vx 一般登入密碼位於忽略版控的 `runtime/secrets/mumble_server_password`；不得使用 SuperUser 或 PKCS#12 密碼代替。

## 憑證鏈

```text
TAK Local Root CA
└─ TAK Local Issuing CA
   └─ takbox.local Mumble server certificate
```

憑證流程參考 hardened 套件的：

- `vendor/takserver-docker-hardened-5.8-RELEASE-84/tak/certs/makeRootCa.sh`
- `vendor/takserver-docker-hardened-5.8-RELEASE-84/tak/certs/makeCert.sh`

Mumble 使用由 TAK 中繼 CA 簽發的獨立 server certificate。`runtime/pki/mumble-fullchain.pem` 依序包含 Mumble 葉憑證與 TAK 中繼 CA；不附加 Root CA。`runtime/pki/mumble-server.key.pem` 是加密的 Mumble 專用 private key。Mumble 容器不掛載 Root CA 或中繼 CA private key。

已驗證：

- Subject `CN=takbox.local`。
- Issuer `CN=TAK Local Issuing CA`。
- SAN 包含 `DNS:takbox.local` 與 `IP:192.168.137.1`。
- EKU 包含 `serverAuth`。
- Mumble 日誌顯示載入一張 intermediate certificate。
- 從 Windows 連到 `192.168.137.1:40000`，以 Root CA 驗證 `takbox.local`，結果為 `Verify return code: 0 (ok)`。

ATAK Voice 自行建立的 self-signed Mumble client certificate 只用於 Vx 的 Mumble client 身分。它不是 TAK 裝置 client certificate，也不需要由 TAK 中繼 CA 簽發。本機 Mumble 明確設定 `certrequired=false`，登入由 Mumble server password 與 channel ACL 控制。

## 執行結果

`docker compose ps mumble` 顯示：

```text
tak-local-mumble-1  mumblevoip/mumble-server:v1.5.915-1  Up (healthy)
192.168.137.1:40000->64738/tcp
192.168.137.1:40000->64738/udp
```

容器主程序：

```text
1  10000  10000  mumble-server  /usr/bin/mumble-server -fg -ini /data/mumble_server_config.ini
```

Windows host 已完成 `40000/TCP+UDP` 綁定、Docker port publish、Mumble healthcheck、mDNS SRV 與 TLS hostname 驗證。Android 裝置未連接 ADB，因此未重跑 `toybox nc -z -w 3 takbox.local 40000`；但重新啟動後，Mumble 已記錄 Android `Mumla 3.7.3` client 完成 `Authenticated`，並進入 `Primary`、`Alternate` 與 `TAK`，證明新通訊埠的實際 client TCP、TLS、密碼與頻道流程可用。UDP 語音路徑仍須以雙向 PTT 實測。

### Vx 首次登入結果

Vx 在通訊埠移轉前曾使用錯誤的一般 server password，Mumble 日誌明確回報 `Invalid server password`。改用 `runtime/secrets/mumble_server_password` 的內容後，Mumble 在 2026-09-21 17:10:40（Asia/Taipei）記錄 ATAK Vx client 完成 `Authenticated`。改用 `40000` 並重新啟動後，日誌於 20:47:37 再次記錄 Android `Mumla 3.7.3` client 完成 `Authenticated`，隨後成功切換至 `Primary`、`Alternate` 與 `TAK`。最終重啟後，20:52:18 又有 Android client 完成驗證，20:53:27 進入 `Primary`；Windows 同時顯示 Android 熱點用戶端到 `40000/TCP` 的連線為 `ESTABLISHED`。

Mumble 初始資料庫只有預設頻道：

```text
channel_id  parent_id  name
0                      Root
```

Vx 嘗試加入尚未存在的 `魷魚` 與 `aaa` 時，日誌顯示 `channelId=-1`；輸入 `Root` 也仍得到 `channelId=-1`，確認 Vx `2.1.0` 不把 Mumble 根頻道當成可加入的語音頻道。這不是 TLS、憑證、網路或 ACL 拒絕。

已使用 `scripts/provision_mumble_channel.py` 經由 Mumble 原生 TLS／Protobuf 管理連線，以 SuperUser secret 建立持久化子頻道。最初用 `TAK` 完成 Vx 相容性驗證：

```text
channel_id  parent_id  name  inheritacl
0                      Root
1           0          TAK   1
```

Mumble 記錄 `Added channel TAK[1:0] under Root[0:-1]`；現有 Vx 連線亦立即收到 `CHANNEL_STATE`，並記錄 `Valid channel: id=1, name=TAK`。腳本不直接修改 SQLite，也不輸出 SuperUser 密碼。

腳本現已調整為初次執行且未指定名稱時建立兩個英文預設頻道：

| Vx 用途 | Mumble 頻道名稱 |
| --- | --- |
| P 主要頻道 | `Primary` |
| A 次要頻道 | `Alternate` |

預設建立指令：

```powershell
python scripts\provision_mumble_channel.py
```

目前測試資料庫的結果為：

```text
channel_id  parent_id  name       inheritacl
0                      Root
1           0          TAK        1
2           0          Primary    1
3           0          Alternate  1
```

`TAK` 是前一階段的相容性測試頻道；全新 Mumble volume 在執行預設建立指令後使用 `Primary` 與 `Alternate`。重複執行會辨識既有頻道，不建立重複項目。若需額外自訂頻道，可在命令列依序指定：

```powershell
python scripts\provision_mumble_channel.py Operations Training
```

使用者在 Vx 輸入 `TAK` 後，Mumble 記錄該 ATAK Vx client 已移入 `TAK[1:0]`。Vx 後續持續回報：

```text
UDP Pings received steadily, continuing to use UDP
Received UDP packet of type: PING
```

以上 Vx UDP 紀錄來自通訊埠移轉前的驗證。`40000/TCP+UDP` 的 Windows 與 Docker server 端驗證完成後，仍須由 Vx 重新連線，確認 Mumble crypt state 與雙向 UDP ping。尚未有第二個語音用戶端，所以不把 UDP ping 成功等同於雙向 PTT 音訊驗收。

Vx 2.1.0 的頻道欄位必須填入伺服器上已存在的非 Root 具名子頻道。空白、未建立的名稱及 `Root` 都無法加入。

## Vx 後續驗證

在 ATAK 重新匯入修正版 `runtime/packages/atak-local-test.dpk` 後，Vx 使用：

| 欄位 | 值 |
| --- | --- |
| Address | `takbox.local`，也可用 SAN 內的 `192.168.137.1` |
| Port | `40000` |
| Password | `runtime/secrets/mumble_server_password` 的內容 |
| P 主要 Channel | `Primary` |
| A 次要 Channel | `Alternate` |

通過條件：

1. Vx 選擇已建立的 `Primary` 或 `Alternate` 後可維持在對應的非 Root channel ID。
2. Mumble 日誌顯示使用者加入選定頻道，Vx 不再顯示無法加入頻道。
3. 第二個用戶端可用時，雙向 PTT 都能通過 UDP 傳送語音。
4. 容器重新建立後，SQLite、channel 與 ACL 仍由 `mumble-data` 保留。
