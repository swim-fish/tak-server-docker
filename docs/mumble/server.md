# Mumble Server 與頻道

Mumble 使用獨立伺服器憑證，由 TAK 中繼 CA 簽發。本專案教學與目前服務的 SAN 只有 `DNS:takbox.local`，用戶端入口為 `takbox.local:40000`，TCP 與 UDP 都對應到容器 64738。固定名稱讓主機 IP 改變時仍可沿用憑證；名稱解析、Compose 綁定與防火牆須同步調整。完整版本、通訊埠見[參考表](../reference/versions-and-ports.md)。

## 啟動與檢查

需要已產生的 Mumble 憑證、三個相關 secret、Windows 熱點及[前景防火牆工作階段](../network/firewall.md#mumble-前景工作階段)。在另一個終端機執行：

```powershell
docker compose up -d mumble
docker compose ps mumble
docker compose logs --tail 80 mumble
```

成功時服務為 healthy。健康檢查會驗證伺服器鏈與主機名稱，但不等於已驗證 Mumble 登入、頻道權限或 UDP 語音。

若紀錄每約 30 秒出現來自 `127.0.0.1` 的短 TLS 連線，隨即顯示 `Connection closed`，這符合本機健康檢查行為。要判斷裝置斷線，需核對裝置來源、登入 session 與同時段 Vx 狀態。

### 使用 IP-only 憑證

Vx Address 可改用 `192.168.137.1`、Port `40000`，Mumble 葉憑證只需含相符的 `IP:192.168.137.1` SAN；DNS-only 與 IP-only 都已有[實測紀錄](../validation/2026-09-22-mumble-san.md)。bootstrap 至少要填 `--host`（或 `--dns`）或 `--ip`；只填 `--ip` 即產生 IP-only，兩者都填則產生 DNS＋IP。既有憑證輪替不要使用 `--force`。

選用 IP-only 時，健康檢查也應明確驗證 IP。可建立本機 `runtime/compose.mumble-ip.yaml`：

```yaml
services:
  mumble:
    healthcheck:
      test:
        - CMD-SHELL
        - >-
          printf '\n' |
          openssl s_client -connect 127.0.0.1:64738
          -CAfile /certs/root-ca.pem
          -verify_ip 192.168.137.1
          -verify_return_error >/dev/null 2>&1
```

```powershell
docker compose -f compose.yaml -f runtime/compose.mumble-ip.yaml up -d --no-deps --force-recreate mumble
```

`127.0.0.1:64738` 是容器內的探測位置，`-verify_ip` 則是憑證應包含的用戶端入口 IP。後續重新建立此服務時沿用同一 override。頻道工具使用 `--server-name 192.168.137.1`，使用者管理腳本使用 `-ServerName 192.168.137.1`，讓管理連線也依 IP SAN 驗證。切回 DNS 模式前，先換回含相符 DNS SAN 的憑證及 Vx Address，再採用原本 Compose 健康檢查。

## 建立 Voice 頻道

```powershell
python ./scripts/provision_mumble_channel.py
```

腳本使用 SuperUser，驗證 CA 與 `takbox.local` 後，初次建立持久化的 `Primary`（主要）、`Alternate`（次要）。目前四頻道 Vx DPK 另使用 `Medical`、`Emergency`；建立或核對全部頻道：

```powershell
python ./scripts/provision_mumble_channel.py Primary Alternate Medical Emergency --connect-host 192.168.137.1 --server-name takbox.local --port 40000
```

成功時應列出每個頻道的 ID。頻道已存在時回報既有 ID，不重複建立。DPK 必須使用本台伺服器的實際 ID，不能把本次的 `2`–`5` 當成所有部署的固定值。建立失敗時先檢查 TLS、SuperUser secret 與伺服器紀錄，再重跑；不要清空 volume。

Vx 的 Channel 不可留空；目前四頻道任務的使用方式見[Vx 任務](../atak/vx-missions.md)。

## 密碼與註冊身分

| secret | 用途 |
| --- | --- |
| `mumble_server_password` | 一般共用伺服器密碼，供 Vx 初次或未註冊身分連線使用。 |
| `mumble_superuser_password` | SuperUser 管理密碼，供頻道及使用者管理工具使用。 |
| `leaf_key_password` | 解密 Mumble 伺服器 TLS 私鑰，不是登入密碼。 |

檔案位於 `runtime/secrets/`。目前 `certrequired=false`；Vx 仍可能提供自行管理的用戶端憑證並註冊身分。[已註冊使用者](users.md)可能直接登入，所以沒有密碼提示不代表新密碼未生效。

## 更換一般伺服器密碼

先安排短暫中斷，將舊 secret 備份到受保護的位置。以本機編輯器或密碼管理工具，把 `runtime/secrets/mumble_server_password` 改成新的隨機單行值；不要把值放進命令列、版控或紀錄。套用：

```powershell
docker compose up -d --force-recreate mumble
docker compose ps mumble
```

這會中斷既有連線，保留原資料 volume、頻道、註冊身分與 TLS 憑證。更新後用未註冊測試身分確認舊密碼遭拒、新密碼可登入；已註冊 Vx 身分不能用來驗證共用密碼是否失效。

若要重現密碼提示，先看[取消註冊](users.md#互動式取消註冊)及[Vx 密碼行為](../atak/vx-missions.md#輸入密碼)。若變更有誤，還原備份 secret 後重建 Mumble；不要重建整套 PKI。

## 停止與資料保存

```powershell
docker compose stop mumble
```

再用 `docker compose up -d mumble` 啟動。`mumble-data` 保存註冊身分、頻道與 ACL；停止容器不會刪除它。前景防火牆需另按 Ctrl+C 清理。

依據：[Compose](../../compose.yaml)、[頻道工具](../../scripts/provision_mumble_channel.py)、[Mumble 實測](../validation/2026-09-21-mumble-server.md)。
