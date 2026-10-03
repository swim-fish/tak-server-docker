# TAK device certificates and groups

[Return to the task index](index.md)

<a id="task-01"></a>

## Task 1: Deliver an existing TAK certificate

Each device must use its own DPK.

1. Select a valid, registered certificate in 「引導式佈建 → TAK Server 連線」.
2. Check the CN, CRL ID, and expiry date.
3. Set the sharing expiry and download limit.
4. Select 「預覽」.
5. Create the QR.
6. Let the assigned Android device scan the complete `tak://` link.
7. Check the import in ATAK.
8. Check that ATAK connects to `takbox.local:8089:ssl`.
9. Check that the sharing record shows `<CN>-<CRL ID>`.

If an old DPK with the same name prevents the update, first delete the old downloaded copy from the device. An import message or download notification does not prove a successful connection.

![Certificate selection and sharing limits](../../images/console-task-01-existing-tak.png)

Figure 1: Select the certificate. Set the QR sharing duration and download limit.

![Certificate inventory filters and identifiers](../../images/console-task-01b-inventory.png)

Figure 2: Use the CN or CRL ID to check the identity in the inventory. Identifiers are concealed.

<a id="task-02"></a>

## Task 2: Add TAK devices and assign groups

A batch can contain 1 to 10 devices. Each device has a separate private key and DPK. TAK restarts once after you confirm issuance. Expiry options are 1 hour, 1 day, 7 days, 14 days, 28 days, and 90 days.

1. Enter each device display name in 「引導式佈建 → 新增 TAK 用戶端」.
2. Enter a unique ASCII CN for each device.
3. Set the expiry with the calendar, or select a listed duration.
4. Move groups to In/write, Out/read, or In + Out/read and write. You must assign at least one permission.
5. Select 「預覽批次」.
6. Check the CN, validity period, groups, and QR limits.
7. Confirm issuance.
8. Check each device registration, serial number, and QR on the results page.

If the batch completes only some devices, first check the existing results. Continue with the same job ID to prevent duplicate issuance. The QR download expiry and certificate validity period are separate settings.

![New device and expiry fields](../../images/console-task-02-new-tak.png)

Figure 3: Enter each CN and expiry time. Then assign the groups.

![Four-column group list](../../images/console-task-02b-group-lanes.png)

Figure 4: Unassigned groups give no read or write permission. Move a group to In, Out, or In + Out to assign permission.

<a id="task-03"></a>

## Task 3: Change device read and write permissions

1. Open 「用戶端憑證 → 依群組檢視」. The default filter is 「使用中」.
2. Select 「隱藏空群組」 if necessary. Clear it before you drag a new certificate into an empty group.
3. Drag the certificate, or select 「移動」 beside the item to open the dialog.
4. To change the destination group or permissions, select 「移動／調整權限」.
5. If you select 「移動／調整權限」, specify the destination group and In, Out, or In + Out.
6. To remove only the source group, select 「從此群組移除」. You can also drag to 「未記錄群組」.
7. Check the pending changes.
8. Confirm the save.
9. When the pending count reaches zero, read the groups from the TAK API.

You do not need a new DPK after changes to existing groups.

To test isolation, send new CoT through TAK Server. Local broadcasts on the same Wi-Fi do not prove group isolation. The [two-device test](../../validation/2026-09-24-ca-rotation-device-baseline.md) records the Alpha/Bravo results.

![Certificates grouped by permissions](../../images/console-task-03-groups.png)

Figure 5: Status filters, hidden empty groups, three permission columns, and the single 「移動」 button.

![Move certificate and change In/Out permissions](../../images/console-task-03-move-dialog.png)

Figure 5a: 「移動／調整權限」 lets you select the destination and permissions. After 「暫存移動」, you must still save the group changes.

![Remove certificate from the current group](../../images/console-task-03-remove-dialog.png)

Figure 5b: 「從此群組移除」 removes only the source group. No change was submitted in this image.

![Add a certificate to a group](../../images/console-task-03b-add-group.png)

Figure 6: Find an active certificate that is not in the group. Select its permissions. Certificate identifiers are concealed.

<a id="task-11"></a>

## Task 11: Revoke a TAK device certificate

**CAUTION: You cannot reverse revocation.** The console stops related QR links, updates the CRL, and restarts TAK. Do not identify certificates only by names that can be duplicates.

1. Check the CN, issuing CA, CRL ID, and SHA-256 fingerprint in 「用戶端憑證 → 憑證清冊」.
2. Select the valid certificate.
3. Select 「撤銷選取的憑證」.
4. Select the confirmation checkbox in the dialog.
5. Check that the CRL contains the serial number.
6. Reconnect with the old DPK to check that 8089 rejects the connection. Android may show only `IO Error`.

The usual revocation procedure updates the CRL and restarts TAK Server automatically. If the revocation record exists but publication or restart fails, you can select 「重新發布 CRL 並重啟」.

This operation generates Root CA and issuing intermediate CA CRLs from the current CA database. It does not add or reverse revocation records. It does not revoke the intermediate CA.

Test 8443 separately. Intermediate CA replacement uses a separate subpage. Check whether the TAK truststore still directly trusts the old CA. See the [certificate operator guide](../../tak-server/certificate-operator-guide.md).

![Selected certificate in the inventory](../../images/console-task-11b-selected-certificate.png)

Figure 21: Select the certificate first. Check the identifier fields. Identifiers are concealed.

![Certificate revocation dialog](../../images/console-task-11-revoke.png)

Figure 22: Check the effect again. The screenshot shows the confirmation dialog before revocation submission.

<a id="task-ca-replace"></a>

## Task 12: Replace the issuing intermediate CA and reissue certificates

**CAUTION: Replacement briefly interrupts TAK, Mumble, and MediaMTX.** Revocation of the old CA invalidates old certificates that you do not select. The system does not generate new DPK files for those certificates. Preset durations are 7, 14, 28, 90, and 730 days from now.

1. Open 「用戶端憑證 → CA 替換」.
2. Check the current CA ID.
3. Check that the console and Windows certificate worker operate correctly.
4. Schedule a brief interruption of TAK, Mumble, and MediaMTX.
5. Select the active certificates to reissue. The system copies their original expiry dates.
6. If necessary, change each expiry with the calendar, or select a preset duration.
7. Check the CN, groups, and new expiry dates.
8. Open the confirmation dialog.
9. Select both independent confirmation checkboxes.
10. Submit the job. The same page shows the background job stages and results.
11. Check that the inventory marks old certificates 「簽發 CA 已撤銷」.
12. Deliver each new DPK.
13. Test ATAK 8089/8443 and all four Vx channels separately.

Manage existing Mumble accounts separately.

The controlled 8443 test confirmed rejection of new connections from old CA certificates when the server loaded the Root CRL. The configuration described in the source was restored to direct loading of only the first CRL.

After each CA replacement, reconnect to 8443 with an old certificate to check rejection. Then check access with a new certificate. See the [8443 test record](../../validation/2026-09-26-ca-rotation-8443-retest.md).

![CA replacement selection and expiry fields](../../images/console-ca-rotation-1440.png)

Figure 23: Replacement invalidates old certificates. The page shows a red warning. Set a new expiry for selected devices. Identifiers are concealed.

![CA replacement at phone width](../../images/console-ca-rotation-390.png)

Figure 24: The narrow layout shows the red risk warning, device cards, and controls in sequence. Identifiers are concealed.

![Two CA replacement confirmations](../../images/console-ca-rotation-confirm.png)

Figure 25: Both checkboxes must be selected before submission is available. The image precedes submission.

![Completed CA replacement](../../images/console-ca-rotation-complete.png)

Figure 26: The local test reissued one certificate. CA IDs and other identifiers are concealed. A slow TAK API startup required manual recovery through the original batch. See the [validation record](../../validation/2026-09-25-wifi-env-ca-console.md).

![Revoked certificates from the old CA](../../images/console-ca-rotation-revoked.png)

Figure 27: The inventory marks old certificates 「簽發 CA 已撤銷」. You cannot select or deliver them.

If the job fails, do not retry immediately. First check snapshots, the Root CRL, and service states through the [certificate operator guide](../../tak-server/certificate-operator-guide.md#撤銷ca-輪替與復原). Test the new Android DPK import, 8443 packages, and all four Vx channels separately.

[Return to the task index](index.md)
