# Service health and lifecycle

The local console exposes a service page at `http://127.0.0.1:10066/services`
when the local `.env` uses port 10066. The page uses the existing admin Basic
authentication and CSRF protection.

## Health layers

| Layer | Source | Meaning |
| --- | --- | --- |
| Process liveness | `GET /healthz` | Gunicorn/Flask can answer. This remains the Compose health check. |
| Container state | Windows service worker calls `docker compose ps --all --format json` | A container exists, is running, and has a Compose health result where configured. |
| Application connectivity | MediaMTX API and HTTP `/healthz` endpoints | Video services and the optional sharing gateway answer at their own application boundary. |
| Management capability | Three Windows worker heartbeat files | The certificate, Mumble, and service workers can receive management requests. |
| Aggregate readiness | Authenticated `GET /readyz` | Returns HTTP 200 only when required containers, application probes, and workers are ready; otherwise HTTP 503. The JSON identifies the failing layer. |

The optional `share-public` container may be stopped without degrading overall
readiness. Stopping the public viewing switch does not stop its containers and
is reported on the MediaMTX page. A failed `/readyz` is diagnostic and does not
restart healthy containers; Compose continues to use `/healthz` for the admin
container's liveness check.

## Service controls

The service page offers `start`, `stop`, and `restart` for Mumble, MediaMTX,
WebRTC viewer, WebRTC gateway, preview, and optional QR sharing. The browser
submits a fixed service name and action to the Windows service worker, which
checks both against an allowlist and confirms the post-action container state.
Actions require an explicit confirmation checkbox. They can interrupt active
voice or video connections. `start` only starts an existing container; it does
not deploy, build, update, or remove a service.

PostgreSQL, TAK Server, and `share-admin` are read-only on this page. Use their
existing maintenance procedures for changes to those services. The admin
container has no Docker socket, and the worker returns no raw Docker logs or
command diagnostics to the browser. Service actions are recorded in
`runtime/service-control/actions.jsonl`; worker errors are recorded in
`runtime/service-control/worker.log`. Both are local runtime files.

## Existing installation upgrade

Run these commands from the project root after reviewing the changes. They do
not recreate TAK Server or the database:

```powershell
python .\scripts\init_share_portal.py
.\scripts\Manage-TakControlWorkers.ps1 -Action Install
docker compose up -d --build --no-deps share-admin
.\scripts\Manage-TakControlWorkers.ps1 -Action Status
```

`-Action Install` keeps already installed worker tasks and adds the service
worker. The worker requires an interactive Windows logon, as the existing
certificate and Mumble workers do. After the container rebuild, open
`/services` and check both `/healthz` and the authenticated `/readyz`.
