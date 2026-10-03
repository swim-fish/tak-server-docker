# Sharing and troubleshooting

[Return to the task index](index.md)

<a id="task-09"></a>

## Task 9: Inspect and stop configuration sharing

Sharing records show the remaining time and download count. You can select 10, 20, or 30 entries per page and apply a status filter.

1. In 「檔案分享」, check the master switch and 「分享中」 links at the top.
2. To stop one share, select 「停止分享」 for that record.
3. To pause all shares, use the master switch.
4. Check that the old QR cannot download files.

Downloaded DPK files and `initial.prefs` do not disappear from devices. Deactivate identities separately.

Time and count limits can apply together. The first limit reached stops new downloads. Opening the QR itself does not count as a download.

![Sharing record status filter](../../images/console-task-09-shares.png)

Figure 17: Page size, status, and download usage. The screenshot shows ended records.

![Master download sharing switch](../../images/console-task-09b-master-switch.png)

Figure 18: The master switch affects all shares. To stop one share, use its record.

## Check results and troubleshoot

| Symptom | First check | Next action |
| --- | --- | --- |
| The management page cannot read worker data | Check that Windows is logged in. Run `Manage-TakControlWorkers.ps1 -Action Status`. | Start with `-Action Start`. Then read `runtime/tak-cert-control/worker.log` or `runtime/share-control/worker.log`. |
| Android only shows a download notification after a QR scan | Check the same hotspot, mDNS, sharing limits, and complete `tak://` or `icu://` link. | Check the actual import in ATAK/ICU. You can first delete an old DPK copy with the same name. |
| ATAK connects but cannot see the Vx package | Check the selected TAK Server in Data Packages → Download. Check access to 8443. | Check that only one TAK package remains. Check `tool=public` and `missionpackage`. Do not use a general Vx QR. |
| ICU shows external settings without video | Check Type, SSL, Stream Path, and squad credentials. Default RTSP uses `takbox.local:8554` with `Use SSL?` clear. RTSPS uses `takbox.local:8322` with SSL enabled. | After publication starts, check the MediaMTX online path. Prevent two devices from using the same `VIDEO_1` path. |
| ICU stops when indoor GPS fails | Check Disable Local Broadcasting. A user observed stopped publication with this checkbox clear. | Share and import a new ICU QR. Then check settings and the MediaMTX online path. This case still needs retesting. |
| Vx logs in without a password prompt | A registered Mumble identity may still be valid. | Delete the registered identity in Mumble management. Then test the new password with an unregistered device. |
| Public video does not open from the internet | The original acceptance scope here covers only the hotspot entry point. | After FQDN, HTTPS, NAT, ICE, and firewall work is complete, test internet access separately. |

[Return to the task index](index.md)
