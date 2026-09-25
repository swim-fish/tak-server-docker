#!/usr/bin/env python3
"""Refresh the public WebRTC ICE host after changing TAK_BIND_IP."""

from __future__ import annotations

import re
from pathlib import Path

from local_network import bind_ip


PROJECT = Path(__file__).resolve().parents[1]
CONFIG = PROJECT / "runtime" / "mediamtx" / "viewer-public.yml"
HOSTS = re.compile(r"(?m)^webrtcAdditionalHosts: \[[^\r\n]*\]$")


def update(path: Path, address: str) -> bool:
    original = path.read_text(encoding="utf-8")
    changed, count = HOSTS.subn(f"webrtcAdditionalHosts: [takbox.local, {address}]", original)
    if count != 1:
        raise RuntimeError("Expected exactly one webrtcAdditionalHosts entry")
    if changed == original:
        return False
    path.write_text(changed, encoding="utf-8")
    return True


if __name__ == "__main__":
    print("Updated public WebRTC host" if update(CONFIG, bind_ip()) else "Public WebRTC host already matches .env")
