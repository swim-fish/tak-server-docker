# Vx missions and Mumble voice

[Return to the task index](index.md)

<a id="task-04"></a>

## Task 4: Update the four-channel Vx mission

1. Generate the package in 「引導式佈建 → Vx 任務佈建」.
2. Preview the package.
3. Check the SHA-256 and the number of packages with the same name.
4. After confirmation, select 「備份並強制替換」.
5. Check that only one `ATAK Local Voice` package remains.
6. In ATAK, download the package from TAK Server through Data Packages → Download.
7. In TAK Voice, join Primary, Alternate, Medical, and Emergency individually.

A general download QR for a Vx-only DPK cannot directly create a Mission. If you accidentally use `Clear Database`, it removes the mission. Download the mission again. If replacement fails, restore from the job backup.

![Vx package provisioning entry](../../images/console-task-04-vx.png)

Figure 7: Preview the generated package first. Then confirm replacement of the server package with the fixed name.

![Four ATAK Vx channels](../../images/atak-vx-four-channel-pool.jpg)

Figure 8: After download, TAK Voice should show four channels that the device can join.

<a id="task-10"></a>

## Task 10: Manage Vx voice login

Select the operation for your purpose. Disconnection, identity deletion, restart, and password reset are separate operations.

### Disconnect a current connection

1. Select the session in 「Mumble 管理 → 線上連線」.
2. Select 「中斷選取的連線」.

The identity can log in again.

### Delete a remembered identity

The system first backs up the database. A valid shared password still lets the user register again.

1. Select the identity in 「已註冊身分」.
2. Confirm deletion.

### Restart or reset the password

Both operations disconnect online sessions.

- To keep channels and registration data, select 「重新啟動 Mumble」.
- To change the local secret, select 「重設共用密碼並重新啟動」.

Check the online and registered identity lists. Then test Vx login again. TAK certificate revocation does not deactivate Mumble. A registered Vx identity may still log in directly after a password change.

![Mumble online and registered identities](../../images/console-task-10-mumble.png)

Figure 19: Manage online sessions and registered identities separately. No connections were online in this screenshot.

![Mumble server controls](../../images/console-task-10b-server-controls.png)

Figure 20: Restart and password reset are separate operations. Both disconnect sessions.

[Return to the task index](index.md)
