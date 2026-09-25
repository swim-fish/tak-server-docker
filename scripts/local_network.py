"""Read the local Compose bind address from the project's .env file."""

from __future__ import annotations

import ipaddress
import os
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_BIND_IP = "192.168.137.1"
DEFAULT_ALLOWED_SUBNET = "192.168.137.0/24"


def setting(name: str, default: str) -> str:
    value = os.environ.get(name)
    if not value:
        dotenv = PROJECT / ".env"
        if dotenv.is_file():
            for line in dotenv.read_text(encoding="utf-8").splitlines():
                if line.startswith(name + "="):
                    value = line.partition("=")[2].strip().strip('"\'')
                    break
    return value or default


def bind_ip() -> str:
    value = setting("TAK_BIND_IP", DEFAULT_BIND_IP)
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise ValueError("TAK_BIND_IP must be an IPv4 address") from exc
    if address.is_unspecified or address.is_multicast or address.is_loopback:
        raise ValueError("TAK_BIND_IP must identify a local network interface")
    return str(address)


def allowed_subnet() -> str:
    value = setting("TAK_ALLOWED_SUBNET", DEFAULT_ALLOWED_SUBNET)
    try:
        network = ipaddress.IPv4Network(value, strict=False)
    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError) as exc:
        raise ValueError("TAK_ALLOWED_SUBNET must be an IPv4 CIDR") from exc
    if ipaddress.IPv4Address(bind_ip()) not in network:
        raise ValueError("TAK_BIND_IP must be inside TAK_ALLOWED_SUBNET")
    return str(network)
