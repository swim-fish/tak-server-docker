# NetBird TAK, Media and Voice Acceptance

Date: 2026-10-01 (Asia/Taipei). This record summarizes the separately deployed cloud Gateway and device observations. It contains no actual deployment/client addresses, user identities, device identifiers, raw CoT, credentials, or location information.

## Results and evidence boundaries

| Check | Result | Limit |
| --- | --- | --- |
| Routing/DNS configuration | One TAK host `/32` through Gateway masquerade/SNAT; exact private service DNS | No full-VPC/default Internet route; original public TAK rules retained |
| TAK transport | Gateway/private TAK TCP `8089` and `8443` reached in the pilot | TCP reachability alone does not establish certificate/application acceptance; `8446` probe was unreachable |
| ICU over NetBird | Actual publication accepted after Gateway/media correction | Publication and QR import are distinct checks |
| Same-team ATAK Video | Operator confirmed person-marker RTSP playback without viewing credentials | Only an eligible peer and active permitted path; protected protocols retain read credentials |
| RTSP/RTSPS server boundary | RTSP DESCRIBE/SETUP/PLAY and media receipt; anonymous RTSPS rejected, authenticated RTSPS accepted | Does not add RTSPS playback to the tested ATAK version |
| Voice user/peer group | User auto-group and actual connected phone peer both matched the intended team | Correct membership alone did not grant the missing voice policy |
| Team voice policy | Added TCP and UDP `40000` from the four service groups to Gateway; exact readback and existing policies/memberships preserved | Network ingress does not replace Mumble authentication/channel ACLs |
| Vx Wi-Fi-to-VPN interface selection | Screenshots show `wlan0 (WIFI)` changing to `tun1 (VPN)` via long-press Network | Interface numbering can vary; no APK modification or separate Cellular-filter fix |
| Mumble recovery | Authorized Mumble-only restart after temporary auto-ban; settings/image retained and TLS hostname/chain verified | Auto-ban protection remains enabled; restart alone does not establish correct Vx settings |
| Vx device connection | Operator confirmed successful connection; two established phone sessions persisted during a 15-second observation with authentication and no new global bans | Successful state followed policy repair, restart and device selection; individual effects were not isolated |
| Cellular/mobile-data Mumble connection | Operator subsequently confirmed connection | No separate packet capture, bidirectional PTT or audio-quality acceptance for this report |

## Device-side Vx operation

Long-press `Network`, choose the active VPN interface (`tun1 (VPN)` on this device), then press `OK`. Confirm the Network tile reflects VPN before reconnecting. See the [cropped screenshot procedure](../atak/vx-missions.md#透過-netbird-選擇-vpn-介面).

The cellular connection report supports this NetBird operating workflow. The [2026-09-30 Cellular-interface diagnosis](2026-09-30-vx-cellular-interface-selection.md) remains a dated observation of the earlier interface-filtering behavior; this run did not modify the APK or repeat every original reproduction case.

## Remaining acceptance

- Bidirectional PTT, microphone release behavior, audio quality and actual UDP/TCP voice media.
- Wi-Fi/cellular transition continuity and longer-duration reconnect/load behavior.
- Cross-team phone denial, approved shared media access and broader peer enrollment.
- Full team-specific Mumble channel ACL rollout, independent of the media isolation setting.
- Random-token path rotation and coordinated QR/URL/DPK reissue/revocation.

## Evidence handling

Private runtime holds original diagnostic logs and full screenshots. Public images are direct crops of the Network tile or interface dialogs, with maps, GPS/callsigns, service identities and surrounding views removed. The cropped pixels were compared to the original rectangles, and output PNGs were checked for absence of EXIF/GPS/text metadata. These crops document UI selection, not a complete network trace or audio test.

[User workflow](../network/netbird-user-guide.md) · [Current cloud architecture](../network/netbird-routing.md)
