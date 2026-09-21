from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
from typing import Any

from zeroconf import IPVersion, Zeroconf


def _fqdn(value: str) -> str:
    return value.rstrip(".") + "."


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the local TAK mDNS records")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--timeout-ms", type=int, default=5000)
    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8-sig") as handle:
        config: dict[str, Any] = json.load(handle)

    expected_address = ipaddress.IPv4Address(config["address"])
    hostname = _fqdn(str(config["hostname"]).lower())
    zeroconf = Zeroconf(
        interfaces=[str(expected_address)],
        ip_version=IPVersion.V4Only,
    )

    failures: list[str] = []
    try:
        for service in config["services"]:
            service_type = _fqdn(str(service["type"]).lower())
            service_name = f"{str(service['name']).strip()}.{service_type}"
            info = zeroconf.get_service_info(
                service_type,
                service_name,
                timeout=args.timeout_ms,
            )
            if info is None:
                failures.append(f"missing service: {service_name}")
                continue

            addresses = [ipaddress.ip_address(raw) for raw in info.addresses]
            if expected_address not in addresses:
                failures.append(
                    f"wrong address for {service_name}: "
                    f"{', '.join(str(item) for item in addresses)}"
                )
            if info.server.lower() != hostname:
                failures.append(
                    f"wrong hostname for {service_name}: {info.server}"
                )
            if info.port != int(service["port"]):
                failures.append(
                    f"wrong port for {service_name}: {info.port}"
                )

            print(
                f"OK {service_name} -> {info.server} "
                f"{','.join(str(item) for item in addresses)}:{info.port}"
            )
    finally:
        zeroconf.close()

    if failures:
        for failure in failures:
            print(f"ERROR {failure}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
