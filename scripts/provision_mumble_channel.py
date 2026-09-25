#!/usr/bin/env python3
"""Create persistent Mumble channels through the native TLS protocol."""

from __future__ import annotations

import argparse
import socket
import ssl
import struct
import time
from pathlib import Path
from local_network import bind_ip


PROJECT = Path(__file__).resolve().parents[1]
ROOT_CA = PROJECT / "runtime" / "pki" / "public" / "root-ca.crt.pem"
SUPERUSER_PASSWORD = PROJECT / "runtime" / "secrets" / "mumble_superuser_password"

MESSAGE_VERSION = 0
MESSAGE_AUTHENTICATE = 2
MESSAGE_REJECT = 4
MESSAGE_SERVER_SYNC = 5
MESSAGE_CHANNEL_STATE = 7
MESSAGE_PERMISSION_DENIED = 12


def encode_varint(value: int) -> bytes:
    output = bytearray()
    while value > 0x7F:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value)
    return bytes(output)


def protobuf_varint(field_number: int, value: int) -> bytes:
    return encode_varint(field_number << 3) + encode_varint(value)


def protobuf_bytes(field_number: int, value: bytes) -> bytes:
    return (
        encode_varint((field_number << 3) | 2)
        + encode_varint(len(value))
        + value
    )


def protobuf_string(field_number: int, value: str) -> bytes:
    return protobuf_bytes(field_number, value.encode("utf-8"))


def decode_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data):
        current = data[offset]
        offset += 1
        value |= (current & 0x7F) << shift
        if not current & 0x80:
            return value, offset
        shift += 7
        if shift > 63:
            break
    raise ValueError("Invalid protobuf varint")


def parse_protobuf(data: bytes) -> dict[int, list[int | bytes]]:
    fields: dict[int, list[int | bytes]] = {}
    offset = 0
    while offset < len(data):
        key, offset = decode_varint(data, offset)
        field_number = key >> 3
        wire_type = key & 7
        if wire_type == 0:
            value, offset = decode_varint(data, offset)
        elif wire_type == 1:
            value = data[offset : offset + 8]
            offset += 8
        elif wire_type == 2:
            length, offset = decode_varint(data, offset)
            value = data[offset : offset + length]
            offset += length
        elif wire_type == 5:
            value = data[offset : offset + 4]
            offset += 4
        else:
            raise ValueError(f"Unsupported protobuf wire type: {wire_type}")
        fields.setdefault(field_number, []).append(value)
    return fields


def text_field(fields: dict[int, list[int | bytes]], number: int) -> str:
    values = fields.get(number, [])
    if not values or not isinstance(values[0], bytes):
        return ""
    return values[0].decode("utf-8", errors="replace")


def integer_field(fields: dict[int, list[int | bytes]], number: int) -> int | None:
    values = fields.get(number, [])
    if not values or not isinstance(values[0], int):
        return None
    return values[0]


def read_exact(connection: ssl.SSLSocket, length: int) -> bytes:
    output = bytearray()
    while len(output) < length:
        chunk = connection.recv(length - len(output))
        if not chunk:
            raise ConnectionError("Mumble closed the TLS connection")
        output.extend(chunk)
    return bytes(output)


def read_message(connection: ssl.SSLSocket) -> tuple[int, bytes]:
    message_type, length = struct.unpack(">HI", read_exact(connection, 6))
    return message_type, read_exact(connection, length)


def send_message(connection: ssl.SSLSocket, message_type: int, payload: bytes) -> None:
    connection.sendall(struct.pack(">HI", message_type, len(payload)) + payload)


def describe_failure(message_type: int, payload: bytes) -> str:
    fields = parse_protobuf(payload)
    reason = text_field(fields, 2)
    return reason or f"Mumble message type {message_type}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "channels",
        nargs="*",
        help="Channels to create; defaults to Primary and Alternate",
    )
    parser.add_argument("--connect-host", default=bind_ip())
    parser.add_argument("--server-name", default="takbox.local")
    parser.add_argument("--port", type=int, default=40000)
    args = parser.parse_args()

    requested_channels = args.channels or ["Primary", "Alternate"]
    requested_channels = list(dict.fromkeys(name.strip() for name in requested_channels))
    if not all(requested_channels):
        raise SystemExit("Channel names must not be empty")

    if not ROOT_CA.is_file() or not SUPERUSER_PASSWORD.is_file():
        raise SystemExit("Missing Mumble CA or SuperUser secret")

    password = SUPERUSER_PASSWORD.read_text(encoding="utf-8").strip()
    context = ssl.create_default_context(cafile=str(ROOT_CA))
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    with socket.create_connection((args.connect_host, args.port), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname=args.server_name) as connection:
            connection.settimeout(5)
            version = protobuf_string(2, "tak-local-provisioner") + protobuf_string(
                3, "Windows"
            )
            authenticate = (
                protobuf_string(1, "SuperUser")
                + protobuf_string(2, password)
                + protobuf_varint(5, 1)
            )
            send_message(connection, MESSAGE_VERSION, version)
            send_message(connection, MESSAGE_AUTHENTICATE, authenticate)

            channels: dict[str, int] = {}
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                message_type, payload = read_message(connection)
                if message_type in (MESSAGE_REJECT, MESSAGE_PERMISSION_DENIED):
                    raise SystemExit(describe_failure(message_type, payload))
                if message_type == MESSAGE_CHANNEL_STATE:
                    fields = parse_protobuf(payload)
                    name = text_field(fields, 3)
                    channel_id = integer_field(fields, 1)
                    if name and channel_id is not None:
                        channels[name] = channel_id
                if message_type == MESSAGE_SERVER_SYNC:
                    break
            else:
                raise SystemExit("Mumble authentication timed out")

            for channel in requested_channels:
                if channel in channels:
                    print(f"Channel already exists: {channel} (id={channels[channel]})")
                    continue

                channel_state = (
                    protobuf_varint(2, 0)
                    + protobuf_string(3, channel)
                    + protobuf_varint(8, 0)
                )
                send_message(connection, MESSAGE_CHANNEL_STATE, channel_state)

                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    message_type, payload = read_message(connection)
                    if message_type in (MESSAGE_REJECT, MESSAGE_PERMISSION_DENIED):
                        raise SystemExit(describe_failure(message_type, payload))
                    if message_type != MESSAGE_CHANNEL_STATE:
                        continue
                    fields = parse_protobuf(payload)
                    name = text_field(fields, 3)
                    channel_id = integer_field(fields, 1)
                    if name and channel_id is not None:
                        channels[name] = channel_id
                    if name == channel and channel_id is not None:
                        print(f"Created channel: {channel} (id={channel_id})")
                        break
                else:
                    raise SystemExit(
                        f"Mumble did not confirm channel creation: {channel}"
                    )
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
