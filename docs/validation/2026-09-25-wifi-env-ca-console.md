# Wi-Fi `.env` binding and CA console replacement

Date: 2026-09-25. This is a local test deployment. The Android operator controls ATAK and Vx screens.

## Wi-Fi address change

The Windows Wi-Fi interface had `10.0.20.27/24`; the Android test device had `10.0.20.24/24`. The local ignored `.env` set `TAK_BIND_IP=10.0.20.27` and `TAK_ALLOWED_SUBNET=10.0.20.0/24`. `docker compose --profile sharing up -d --no-build` bound TAK, Mumble, MediaMTX, public viewer, and share download to that address. The management page remained on `127.0.0.1:10066`.

The mDNS installer republished `takbox.local → 10.0.20.27`; its query found both the Mumble 40000 and TAK 8089 service records. Android resolved and pinged the name. From Android, TCP connection probes to 8089, 8443, 40000, 8322, 10065, and 8889 all succeeded. A read-only TAK administration API request succeeded. These probes establish network reachability, not ATAK or ICU application login.

The existing TAK and MediaMTX Windows firewall rules still referred to the previous hotspot at the first inspection. The TAK firewall script was changed to request UAC and read `.env`, but its first UAC request was canceled, so that attempt did not replace the old rules. The current Android TCP reachability result does not prove the new scoped firewall rules are installed. Re-run the TAK and MediaMTX firewall scripts and inspect their local/remote address filters before calling firewall migration complete.

## CA replacement through the browser

The CA page displayed one eligible registered Alpha certificate. In Chrome, the operator selected it, chose the 730-day preset, checked both confirmation boxes, and submitted the replacement. The new service certificates were staged, and TAK, Mumble, and MediaMTX switched to the replacement issuing CA.

The first batch registration check failed because it waited only 20 seconds after a TAK restart. TAK's 8089 listener had returned, but its user-management API was not ready. The certificate and DPK had already been signed, and the new user and `team-alpha` group were present once the API recovered. The batch was resumed using its original job ID without signing a second certificate. The code now waits up to 150 seconds for the API group check. After the batch reached `complete`, the staged Root CRL was published, the former CA direct trust anchor was removed, and TAK was restarted. The failed job was marked complete only after these checks, with the recovery cause retained in its job record. This run verifies successful completion **with manual recovery**, not an uninterrupted automatic replacement.

Checks after recovery:

- Root CRL contains the former issuing CA serial `1000` and does not contain replacement CA serial `1001`.
- Offline OpenSSL validation of the archived Alpha certificate and full CRL chain returned `error 23: certificate revoked` at the former issuing CA.
- The former Alpha certificate failed a fresh 8089 TLS test; the replacement certificate succeeded. The TAK-side TLS alert for the old certificate was generic (`internal error`), so the Root CRL and chain check establish the revocation reason.
- The replacement Alpha certificate retained `team-alpha` In and Out group membership, and the TAK administration API returned that group. Its new expiration is 2028-09-24 17:45 Taiwan time.
- TAK Server, database, Mumble, share services, and MediaMTX were running; TAK and Mumble health checks passed. The replacement TAK service certificate has `DNS:takbox.local` and `IP:10.0.20.27` SAN. Mumble and MediaMTX kept `DNS:takbox.local` SAN.
- The browser CA page reported one reissued certificate. The inventory's archived Alpha entry showed `簽發 CA 已撤銷`; the new Alpha entry appeared under `使用中`.

![CA replacement completed](../images/console-ca-rotation-complete.png)

![Former CA entry shown as revoked](../images/console-ca-rotation-revoked.png)

The replacement DPK was copied directly to the Android test device's Download directory for manual ATAK import. ATAK 8089 login, 8443 package listing, and Vx four-channel checks are separate device acceptance steps. No claim is made here about 8443 rejecting the former client certificate: that connector currently has no explicit `crlFile` and requires its own test.
