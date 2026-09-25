#!/usr/bin/env python3
"""Exercise local MediaMTX RTSP/RTSPS publishing and reading with FFmpeg."""

from __future__ import annotations

import argparse
import json
import socket
import ssl
import subprocess
import time
import uuid
from pathlib import Path
from local_network import bind_ip


PROJECT = Path(__file__).resolve().parents[1]
IMAGE = "bluenviron/mediamtx:1.21.1-ffmpeg"
NETWORK = "tak-local_tak-edge"
HOST_IP = bind_ip()
ROOT_CA = PROJECT / "runtime" / "pki" / "public" / "root-ca.crt.pem"
PUBLISH_PASS = PROJECT / "runtime" / "secrets" / "mediamtx_publish_password"
READ_PASS = PROJECT / "runtime" / "secrets" / "mediamtx_read_password"


def run(command: list[str], passwords: tuple[str, str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        message = (result.stdout + result.stderr)[-2500:]
        for password in passwords:
            message = message.replace(password, "<redacted>")
        raise RuntimeError(f"Command failed ({result.returncode}): {message}")
    return result


def ffmpeg_command(network: str, dns: str, address: str, *arguments: str) -> list[str]:
    return ["docker", "run", "--rm", "--network", network,
            "--add-host", f"{dns}:{address}",
            "--mount", f"type=bind,src={ROOT_CA},dst=/root-ca.pem,readonly",
            "--entrypoint", "ffmpeg", IMAGE, "-hide_banner", "-nostdin",
            "-loglevel", "error", *arguments]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-ip", default=HOST_IP)
    parser.add_argument("--dns", default="takbox.local")
    parser.add_argument("--include-udp", action="store_true")
    parser.add_argument("--via-host", action="store_true",
                        help="Test the Windows-published ports from Docker's default bridge")
    args = parser.parse_args()
    passwords = (PUBLISH_PASS.read_text(encoding="ascii").strip(),
                 READ_PASS.read_text(encoding="ascii").strip())
    if not all(passwords):
        raise SystemExit("MediaMTX credentials are missing")

    context = ssl.create_default_context(cafile=str(ROOT_CA))
    with socket.create_connection((args.host_ip, 8322), timeout=5) as connection:
        with context.wrap_socket(connection, server_hostname=args.dns) as secure:
            print(f"RTSPS TLS: trusted chain and {args.dns} hostname ({secure.version()})")

    if args.via_host:
        network = "bridge"
        address = args.host_ip
    else:
        network = NETWORK
        inspect = run(["docker", "inspect", "tak-local-mediamtx-1",
                       "--format", "{{json .NetworkSettings.Networks}}"], passwords)
        networks = json.loads(inspect.stdout)
        address = networks[NETWORK]["IPAddress"]
    cases = [("rtsp", "tcp"), ("rtsps", "tcp")]
    if args.include_udp:
        cases.extend((("rtsp", "udp"), ("rtsps", "udp")))

    for scheme, transport in cases:
        port = 8322 if scheme == "rtsps" else 8554
        publisher_url = f"{scheme}://atak-publisher:{passwords[0]}@{args.dns}:{port}/test"
        reader_url = f"{scheme}://atak-viewer:{passwords[1]}@{args.dns}:{port}/test"
        tls = ["-tls_verify", "1", "-ca_file", "/root-ca.pem"] if scheme == "rtsps" else []
        pub_args = ["-re", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=10",
                    "-t", "10", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-rtsp_transport", transport,
                    *tls, "-f", "rtsp", publisher_url]
        reader_args = ["-rtsp_transport", transport, *tls,
                       "-i", reader_url, "-t", "2", "-f", "null", "-"]
        name = "mediamtx-probe-" + uuid.uuid4().hex[:12]
        command = ffmpeg_command(network, args.dns, address, *pub_args)
        command[3:3] = ["--name", name]
        publisher = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True)
        try:
            time.sleep(2)
            if publisher.poll() is not None:
                _, error = publisher.communicate(timeout=2)
                for password in passwords:
                    error = error.replace(password, "<redacted>")
                raise RuntimeError(f"{scheme}/{transport} publisher exited: {error[-1500:]}")
            run(ffmpeg_command(network, args.dns, address, *reader_args), passwords, timeout=25)
            print(f"{scheme.upper()} over {transport.upper()}: publish and read passed")
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15)
            publisher.communicate(timeout=15)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
