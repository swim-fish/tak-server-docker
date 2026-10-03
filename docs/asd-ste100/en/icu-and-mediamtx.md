# ICU and MediaMTX video

[Return to the task index](index.md)

<a id="task-05"></a>

## Task 5: Create ICU publisher QR codes for personnel

The `initial.prefs` file contains the publisher password. Members of one squad share this password. New QR defaults are 720p, 15 fps, 900 kbps, and altitude in meters MSL. Disable Local Broadcasting is selected by default.

1. Select the squad in 「引導式佈建 → ICU 小隊發布」.
2. Select one, several, or all members numbered 1–10. All members are selected by default. Each selected member gets a QR.
3. To specify a single custom path, select Advanced. A named squad Stream Path must stay under `live/<小隊>/` and end with `/`. ICU adds `VIDEO_1`.
4. Set the QR duration and download limit.
5. Preview each member path.
6. Run the job.
7. Switch between QR codes on the results page.
8. Deliver each complete `icu://download?url=...` link.
9. In ICU, check external settings, RTSP-Push, and `takbox.local:8554`.
10. Check that `Use SSL?` is clear.
11. Start the stream.
12. Check the online path in MediaMTX.

**Squad members can use the same QR.** After import, each device can change the path suffix in ICU. For example, change `live/alpha/1/` to `live/alpha/2/` without changes to credentials. Different devices should use different complete paths.

The downloaded `initial.prefs` contains a password. An import message does not prove video publication. An existing QR is a configuration snapshot. Share a new QR after default settings change.

Use the following batch procedure if you also need to publish video aliases to TAK groups.

TAK groups control only alias list visibility. Devices with viewer credentials do not automatically lose playback permission after group changes. If you select different groups, the system deletes and recreates old aliases. The video list may disappear briefly.

1. Select 「引導式佈建 → ICU 小隊批次交付」.
2. Select the squad, first member, and member count.
3. Select the groups that can see the TAK video aliases.
4. In the preview, check each `live/<小隊>/<隊員>/VIDEO_1` path and the certificates with read permission.
5. Run the job.
6. Let each device scan its own QR.
7. Check the corresponding `ICU <小隊> <隊員>` alias in the ATAK video list.

See [batch operations and limits](../../mediamtx/management.md#批次交付隊員-qr-與-tak-影像別名).

![ICU standard mode options](../../images/console-task-05-icu.png)

Figure 9: Generate standard paths and short-lived QR codes from squad and member identifiers.

![ICU Advanced path preview](../../images/console-task-05b-advanced-path.png)

Figure 10: Advanced changes only Stream Path. The preview shows the `VIDEO_1` suffix that ICU adds.

![Alpha QR changed to member 2 and online](../../images/console-icu-alpha-2-live-path.png)

Figure 10a: After import of the original Alpha QR, the user changed the Android ICU path to `live/alpha/2/`. Publication succeeded. The console shows `live/alpha/2/VIDEO_1`. The image shows the path only, without video capture.

### Check settings on the device

These crops come from device screenshots supplied by the user. They retain the original settings. Figure A shows a selected checkbox. Figures B and C show only the settings entries. **These screenshots do not prove that 900 kbps or meters MSL are applied.**

After a new QR scan, open the ICU options to check the settings. Then check publication through the MediaMTX online path. See [ICU QR settings](../../mediamtx/icu-qrcode.md#室內定位與影像設定) for keys and available values.

![ICU Disable Local Broadcasting selected](../../images/icu-disable-local-broadcasting.jpg)

Figure A: A user observed that a clear checkbox may interrupt video publication when indoor GPS fails. New QR codes select it by default. Device retesting is still necessary.

![ICU stream resolution, frame rate, and bit rate entries](../../images/icu-stream-quality-preferences.jpg)

Figure B: Resolution, TS Frame Rate, and Stream Bit Rate control stream quality. MP4 recording uses separate settings.

![ICU coordinate and altitude display entries](../../images/icu-display-preferences.jpg)

Figure C: Altitude Display selects meters or feet. Coordinate Display selects the coordinate format.

<a id="task-06"></a>

## Task 6: Publish video from a drone or encoder

**CAUTION: Publisher URLs and QR codes contain credentials. Do not paste them into logs or Git.** General device QR codes do not have the ICU sharing expiry. Only identity deactivation or password reset invalidates the old connection details. General devices do not automatically add `VIDEO_1`.

1. Enter the device name in 「引導式佈建 → Advanced → 一般設備」.
2. Enter a unique complete `live/` path. The URL input group shows an RTSPS preview.
3. Check the preview.
4. Create the device identity.
5. Select 「顯示連線資訊」 on the results page. RTSP and RTSPS each have a complete URL, 「複製網址」 button, and QR.
6. Prefer RTSPS for publication.
7. With RTSPS, verify the TAK CA chain and `takbox.local`. RTSP-only devices can use `8554` on a controlled hotspot.
8. Check that the complete path is online in MediaMTX.
9. Test the video with a separate reader.

Each device has separate credentials and an assigned path. The RTSPS format is `rtsps://<帳號>:<密碼>@takbox.local:8322/<Stream Path>`. RTSP uses `rtsp://` and `8554`.

![General device URL input group](../../images/console-task-06-device.png)

Figure 11: First check the device name and complete Stream Path.

![General device publisher preview](../../images/console-task-06b-preview.png)

Figure 12: Check the path and TLS conditions in the preview. The screenshot precedes account creation.

### Local simulated drone test

On 2026-09-25, the console created `Drone RTSPS Validation` with path `live/drone/validation-20260925`. FFmpeg on a separate Docker bridge simulated a drone. It published H.264 through the Windows hotspot address to `takbox.local:8322`.

A separate reader account decoded 30 frames from the same path. The console WebRTC preview also showed test color bars. A separate RTSP `8554/TCP` test published with the same identity and read 30 frames.

The identity was deactivated after testing. The old URL could no longer publish. This test does not establish acceptance for a physical drone or internet access. See the [validation record](../../validation/2026-09-25-drone-synthetic-stream.md).

![General device publisher URL preview](../../images/console-drone-01-url-preview.png)

Figure 12a: Before creation, the URL preview contains only the host, port, and path. Credentials become available after creation.

![General device RTSP and RTSPS copy controls](../../images/console-drone-05-copy-links-redacted.png)

Figure 12b: After creation, expand the connection details to copy RTSP/RTSPS URLs or scan QR codes. Concealed URLs and QR codes in the screenshot cannot connect.

![Simulated drone stream card](../../images/console-drone-03-stream-card.png)

Figure 12c: After publication, check for `live/drone/validation-20260925` in 「目前發布的串流」.

![Simulated drone video in the console](../../images/console-drone-02-live-preview.png)

Figure 12d: The console preview received FFmpeg color bars. A separate reader must still confirm successful video decoding.

<a id="task-07"></a>

## Task 7: View video and control viewing

First read the flow diagram below. Then select the connection for the playback device. ICU QR defaults use RTSP `8554` with `Use SSL?` clear. This matches the protocol supported by ATAK Video Alias. Drones and general devices can use RTSPS. They can also use RTSP without TLS on a controlled LAN.

The verified ATAK path reads directly from MediaMTX through RTSP/TCP. For browsers, separate viewer/preview containers read on demand and supply WebRTC. See [local video flow](../../mediamtx/video-flow.md) for protocols, encryption, and test limits.

### Preview in the management page

1. Select an online stream in 「MediaMTX 管理」.
2. Select 「即時預覽」.
3. When finished, select 「關閉預覽」.

### View from a hotspot device

1. Open `http://takbox.local:8889/live/<path>/`. Keep the final slash.

### Control public WebRTC viewing

The 「公開 WebRTC 觀看」 switch controls new viewing and existing public sessions. It does not stop ICU publication. Public session counts exclude management previews.

1. Set 「公開 WebRTC 觀看」 as required.
2. Open the 「觀看工作階段」 subpage.
3. Check the public viewer count, paths, source addresses, and connection states.

The page updates every 5 seconds. You can search sessions or select 「立即更新」.

### View ICU video in ATAK CIV 5.7.0.15

This ATAK built-in player cannot directly open the RTSPS source that ICU shares automatically. Use RTSP only on a controlled LAN or VPN.

1. Check that the publisher continues to publish.
2. Manually create an RTSP source in ATAK.
3. Enter `takbox.local:8554`, the actual `live/.../VIDEO_1` path, and the `atak-viewer` credentials.
4. Select **Reliable P2P Connection (consumes more resources)** to use RTSP over TCP.

See the [device test record](../../validation/2026-09-25-atak-icu-viewer.md).

The original acceptance test cited here covers hotspot viewing only. Internet access still needs FQDN, HTTPS, NAT, and ICE acceptance tests. No streams were online in Figure 13.

![WebRTC viewing controls](../../images/console-task-07-viewer.png)

Figure 13: The management page shows the public viewing switch, session count, and stream list.

![ICU, drone, MediaMTX, ATAK, WebRTC, and thumbnail flows](../../images/console-task-07b-viewing-flow.png)

Figure 14: Publication, MediaMTX reception, direct ATAK reading, browser WebRTC, and single-frame thumbnails use different paths. `Use SSL?` means ICU RTSPS/TLS. The diagram separates WebRTC HTTP signaling from encrypted media.

![Public MediaMTX viewer sessions](../../images/console-media-viewer-sessions.png)

Figure 14a: No public viewer sessions existed in the 2026-09-26 screenshot. This empty-list page check did not test playback. After NAT or a proxy, the source address may differ from the device IP.

<a id="task-08"></a>

## Task 8: Deactivate publisher identities or change their passwords

### Select publisher identities

1. Open 「MediaMTX 管理」.
2. For squads, select 「ICU」. For general devices, select 「其他」.
3. Search for the identity.
4. Set 「啟用中／停用／顯示全部」 as required.
5. Select the identities to change.

Both pages share the online streams and viewing switch. On 「ICU」, 「啟用」 means the identity can log in. The 「串流中」 badge and path count indicate available publisher streams in MediaMTX. Expand 「QR 路徑」 to check individual paths.

On 「其他」, select 10/20/30 entries per page. Use the previous and next page controls.

### Select the operation

Reissuing QR codes does not change the password. After a squad password reset, every squad member must scan a QR again. General devices must obtain their own publisher URLs again.

1. To reissue ICU QR codes, expand the squad card QR paths. All paths are selected by default.
2. To reissue ICU QR codes, select individual paths or use 「全選／全部不選」. You must select at least one path.
3. Select 「再次發布 ICU QR」, 「停用選取身分」, or 「重設選取密碼」 for the required operation.
4. Select the page confirmation checkbox.
5. Submit the job.
6. After a squad password reset, let all squad members scan the QR again.
7. After a general device password reset, obtain its assigned publisher URL again.
8. After a password reset, check that the original publisher connection is disconnected.

Reissuing QR codes does not change the original password. Squad members share credentials. To deactivate one device separately, you should use a general device identity.

![MediaMTX publisher identities](../../images/console-task-08-publishers.png)

Figure 15: Search and filter publisher identities.

![Controls for selected identities](../../images/console-task-08b-selected-publisher.png)

Figure 16: Select identities before reissuing, deactivating, or resetting. The screenshot precedes submission.

![Squad cards on the ICU subpage](../../images/console-media-icu-cards.png)

Figure 17: The ICU subpage keeps squad cards and 「再次發布 ICU QR」.

![Device table on the other subpage](../../images/console-media-other-table.png)

Figure 18: The 「其他」 subpage has status filters, search, page size, and reactivation controls in device rows.

### Reactivate a device

With the old password, the original URL becomes usable again. A new password invalidates the original URL.

1. Select 「其他」 → 「停用」.
2. Find the device.
3. Select 「重新啟用」.
4. Select 「沿用舊密碼」 or 「產生新密碼」 in the dialog.
5. Select the confirmation checkbox.
6. Submit the job.
7. Select 「顯示連線資訊」 on the results page.
8. Copy the RTSP/RTSPS URLs separately, or use the QR.
9. Check that the assigned path accepts publication.

![Password options for device reactivation](../../images/console-media-reactivate-dialog.png)

Figure 19: The default is 「產生新密碼」. You can explicitly select 「沿用舊密碼」. A test identity successfully published after reactivation with its old password. The identity was deactivated again after verification. Publication with a new password still needs a test.

[Return to the task index](index.md)
