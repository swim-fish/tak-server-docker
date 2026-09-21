from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import signal
import threading
from pathlib import Path
from typing import Any

from zeroconf import IPVersion, NonUniqueNameException, ServiceInfo, Zeroconf


LOGGER = logging.getLogger("tak-mdns")


def _fqdn(value: str) -> str:
    return value.rstrip(".") + "."


def _load_config(path: Path) -> tuple[ipaddress.IPv4Address, str, list[ServiceInfo]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        config: dict[str, Any] = json.load(handle)

    address = ipaddress.IPv4Address(config["address"])
    hostname = _fqdn(str(config["hostname"]).lower())
    if not hostname.endswith(".local."):
        raise ValueError("hostname must end with .local")

    services: list[ServiceInfo] = []
    for service in config["services"]:
        service_type = _fqdn(str(service["type"]).lower())
        if not service_type.endswith("._tcp.local."):
            raise ValueError(f"unsupported service type: {service_type}")

        instance = str(service["name"]).strip()
        if not instance:
            raise ValueError("service name must not be empty")

        port = int(service["port"])
        if not 1 <= port <= 65535:
            raise ValueError(f"invalid service port: {port}")

        services.append(
            ServiceInfo(
                type_=service_type,
                name=f"{instance}.{service_type}",
                addresses=[address.packed],
                port=port,
                properties=service.get("properties", {}),
                server=hostname,
            )
        )

    if not services:
        raise ValueError("at least one service is required")

    return address, hostname, services


def _configure_logging(log_file: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish TAK services over Windows mDNS")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--log-file", type=Path)
    args = parser.parse_args()

    _configure_logging(args.log_file)
    address, hostname, services = _load_config(args.config)
    stopped = threading.Event()

    def stop(_signum: int, _frame: object) -> None:
        stopped.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, stop)

    zeroconf = Zeroconf(interfaces=[str(address)], ip_version=IPVersion.V4Only)
    registered: list[ServiceInfo] = []

    try:
        for service in services:
            zeroconf.register_service(service, allow_name_change=False)
            registered.append(service)
            LOGGER.info(
                "Published %s at %s:%d",
                service.name,
                address,
                service.port,
            )

        LOGGER.info("READY hostname=%s address=%s", hostname, address)
        stopped.wait()
        return 0
    except NonUniqueNameException:
        LOGGER.exception("An mDNS service name is already in use")
        return 2
    finally:
        for service in reversed(registered):
            try:
                zeroconf.unregister_service(service)
            except Exception:
                LOGGER.exception("Failed to unregister %s", service.name)
        zeroconf.close()


if __name__ == "__main__":
    raise SystemExit(main())
