# Using TAK, ICU, ATAK Video and Voice through NetBird

Updated: 2026-10-01 (Asia/Taipei). This guide applies to the separately deployed cloud Gateway. Local Compose installation remains documented in [getting started](../getting-started.md). The cloud routing, listeners, and policies are described in [NetBird architecture](netbird-routing.md).

All domains below are placeholders. Use the service names supplied by your administrator, not the example domains or a desktop peer hostname.

## 1. Connect and check your team

1. Connect NetBird to the administrator-provided public control endpoint. Complete local-account login and MFA as configured.
2. Ask the administrator to assign the user to `alpha`, `bravo`, `charlie`, or `admin` and verify propagation to this device's peer. User `auto_groups` and the connected peer's membership must both match the intended assignment.
3. Confirm NetBird is connected before opening TAK, media, or voice. A connected VPN does not by itself authorize every service.
4. Retain the supplied service hostnames. Exact private DNS sends TAK to its VPC host and media/voice/admin to the Gateway's NetBird address. DNS distribution and traffic permission are separate checks.

| Example service name | Use after VPN connection | Additional identity |
| --- | --- | --- |
| `tak.example.test` | TAK TLS `8089`, package/API HTTPS `8443` through the Gateway host route | Existing TAK client certificate |
| `media.example.test` | ICU publishing, ATAK RTSP viewing, authenticated browser viewer | Publishing credentials or protected-viewer login |
| `voice.example.test` | Mumble/Vx `40000/TCP+UDP` | Existing Mumble identity/password and channel ACLs |
| `admin.example.test` | Admin HTTPS `8443` for authorized admin peers | Existing service login |
| `netbird.example.test` | Public VPN bootstrap/login endpoint | NetBird local account and MFA |

Do not replace a service hostname with a NetBird desktop peer name or bare VPN address to bypass DNS/TLS errors. The hostname must match its certificate SAN. Existing public TAK access and the legacy public Mumble binding remain under their original rules; not every service has become VPN-only.

## 2. Connect ATAK to TAK

Import the device-specific TAK DPK using the [ATAK connection procedure](../atak/connection.md). Keep the supplied server hostname, CA trust, and client certificate. Connect NetBird first, then enable the TAK connection.

TAK uses one private host `/32` route with Gateway SNAT. TAK sees the Gateway's VPC source address while continuing to authenticate the device certificate. Do not use that shared source address as a user identity. Test package queries/downloads on `8443` separately from the CoT connection on `8089`; `8446` is a permitted policy entry whose service availability was not established.

A package link may be downloaded directly from its configured HTTPS delivery service outside the overlay. A successful download is not evidence that VPN service access works. Protect device DPKs, ICU profiles, signed URLs, and QR codes because they can contain credentials or bearer access.

## 3. Publish ICU and view in ATAK

Use the administrator-issued ICU QR/profile for this device. Import success only proves settings were loaded; actual publication must be checked separately.

For the tested ATAK person-marker Video flow, use the approved **plain RTSP** profile over NetBird: port `8554`, ICU `Use SSL?` disabled, and the assigned publishing username/password and exact path. Keep the approved profile's path and stream-name behavior; do not change to another member's or team's path.

| Operation | Current rule |
| --- | --- |
| RTSP publication | NetBird access plus publishing credentials and the assigned exact path |
| RTSPS/RTMP/RTMPS publication | NetBird access plus publishing credentials and the assigned exact path |
| Plain RTSP viewing in ATAK | No password when the peer and exact active path are authorized |
| RTSPS/RTMP/RTMPS viewing | Credentials remain required |
| Browser/WebRTC viewing | Approved peer plus viewer login/session grant |

Publication and viewing must reference the **same complete active stream path**. An illustrative password-free viewing URL is:

```text
rtsp://media.example.test:8554/ASSIGNED_COMPLETE_STREAM_PATH
```

`ASSIGNED_COMPLETE_STREAM_PATH` is a placeholder, not a deployed stream. Opening it cannot create a stream or grant permission. Keep credential-bearing publication URLs and raw CoT out of public screenshots, logs, and documentation.

1. Connect NetBird on the ICU device and viewer device.
2. Start ICU publication using the issued profile.
3. In ATAK, open the publisher's person-marker wheel and select `Video`. A stale or unavailable stream must be republished/refreshed before retesting.
4. If a manual RTSP entry is needed, use the actual approved path and the previously tested Reliable/TCP option. Viewing transport evidence must not be inferred from a connected TAK session.

The tested ATAK version could not play ICU's automatic `rtsps` person URL even when server publication/read authorization worked. NetBird does not add RTSPS playback support to ATAK. Plain RTSP has no protocol TLS; its NetBird tunnel transport is encrypted. Same-team ICU publication and password-free ATAK Video playback were accepted. Random-token rotation and atomic QR/URL/DPK reissue remain planned, rather than deployed by this guide.

Media isolation is enabled: own team plus assigned shared streams, with approved admin cross-team viewing. The admin isolation switch affects media read scope; it does not change publishing credentials, TAK groups, or Mumble channel ACLs. Cross-team phone denial and wider rollout remain separate acceptance gates.

## 4. Connect Mumble / ATAK Vx

Retain the issued Mumble hostname and port `40000`. Team voice policies allow `alpha`, `bravo`, `charlie`, and `admin` to Gateway TCP/UDP `40000`; service login and channel ACLs remain independent. The host forwards that port to container `64738`; clients use the host port, not the container port.

Vx requires an additional device-side interface check:

1. Connect NetBird, open Vx, and select the intended voice position/channel.
2. **Long-press `Network`.**
3. In `Available Network Interfaces`, select the active VPN entry, **`tun1 (VPN)` on the tested device**, and press `OK`.
4. Confirm the Network tile shows VPN. Check each active voice position if using both VS1 and VS2.
5. Reconnect voice once if needed, then verify login/channel status before testing PTT.

![Vx Network tile](../images/vx-netbird-network-button.png)

The [illustrated Vx guide](../atak/vx-missions.md#透過-netbird-選擇-vpn-介面) shows the Wi-Fi-to-VPN selector transition with cropped screenshots. VPN interface numbering can vary; do not assume every device uses `tun1`. NetBird being connected does not prove Vx selected its VPN interface.

The operator confirmed Vx connection after team-policy repair, an authorized Mumble-only restart, and VPN interface selection. The operator also reported successful Mumble connection over cellular/mobile data. Bidirectional PTT, audio quality, cellular media transport, and uninterrupted Wi-Fi/cellular switching have not been independently accepted by these reports. The earlier Cellular-interface filtering observation remains historical; no Vx APK fix was applied.

## 5. Troubleshoot in order

| Symptom | First check |
| --- | --- |
| Service name does not resolve privately | NetBird connection, intended DNS recipients and exact service hostname |
| TCP timeout | User auto-group, propagated peer membership, destination/port policy and listener |
| Vx still shows Wi-Fi or unavailable Network | Long-press Network and choose the active VPN entry |
| TLS hostname/issuer error | Correct service hostname, SAN, CA trust and device time; retain TLS verification |
| Vx reconnects end in TLS reset | Mumble logs for temporary `Global ban`, then login/channel errors |
| ICU imported but cannot publish | VPN media policy, exact assigned path, publishing credentials and listener/protocol |
| ATAK Video fails | Active stream, `rtsp` versus unsupported automatic `rtsps`, peer/path scope and transport |
| Login works but voice has no audio | Microphone permission, PTT assignment, channel ACLs, second client and actual UDP/TCP media |

Avoid rapid probe/reconnect loops. Mumble can temporarily auto-ban a source; keep protection enabled and allow expiry or use an authorized, backed-up Mumble-only recovery restart. Unauthenticated UDP status replies are disabled by `allowping=false`, so a silent status ping does not establish UDP media failure. Do not change passwords, rebuild PKI, or disable certificate checks solely because a VPN policy or Vx interface is wrong.

For dated evidence and limits, see [NetBird device acceptance](../validation/2026-10-01-netbird-tak-media-voice.md), [routing/policy details](netbird-routing.md), and [general troubleshooting](../troubleshooting.md).
