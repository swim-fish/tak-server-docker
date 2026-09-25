"""Write public identity metadata for a bootstrap ATAK login package."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


CN = re.compile(r"subject=CN=([A-Za-z0-9][A-Za-z0-9._-]{0,62})(?:,|$)")
SERIAL = re.compile(r"serial=([0-9A-Fa-f]+)\Z")


def write_identity(package: Path, client_certificate: Path) -> Path:
    """Bind the public CN and serial to the exact DPK bytes for UI labels."""
    openssl = shutil.which("openssl")
    if not openssl:
        raise RuntimeError("openssl must be available on PATH")
    result = subprocess.run(
        [openssl, "x509", "-in", str(client_certificate), "-noout", "-subject",
         "-serial", "-nameopt", "RFC2253"],
        capture_output=True, text=True, check=True,
    )
    lines = result.stdout.strip().splitlines()
    subject = next((line for line in lines if line.startswith("subject=")), "")
    serial_line = next((line for line in lines if line.startswith("serial=")), "")
    cn_match = CN.match(subject)
    serial_match = SERIAL.fullmatch(serial_line)
    if not cn_match or not serial_match:
        raise RuntimeError("Could not read a safe CN and serial from the ATAK client certificate")
    metadata = {
        "filename": package.name,
        "sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
        "cn": cn_match.group(1),
        "serial": serial_match.group(1).upper(),
    }
    destination = package.with_suffix(".identity.json")
    temporary = destination.with_suffix(".identity.json.pending")
    temporary.write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, destination)
    return destination
