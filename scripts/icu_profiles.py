"""Validate ICU stream paths used by the guided provisioning flow."""

from __future__ import annotations

import re


SQUADS = ("default", "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel")
SEGMENT = re.compile(r"[A-Za-z0-9_-]+\Z")


def stream_path(squad: str, person: str, custom: str = "") -> str:
    if squad not in SQUADS:
        raise ValueError("Invalid ICU squad")
    if person and (not person.isdecimal() or not 1 <= int(person) <= 10 or person != str(int(person))):
        raise ValueError("Person ID must be between 1 and 10")
    if custom:
        if not custom.startswith("live/") or not custom.endswith("/") or len(custom) > 160:
            raise ValueError("Custom Stream Path must begin with live/ and end with /")
        parts = custom[5:-1].split("/") if custom != "live/" else []
        if any(not SEGMENT.fullmatch(part) for part in parts):
            raise ValueError("Custom Stream Path contains an invalid segment")
        return custom
    parts = ["live"]
    if squad != "default":
        parts.append(squad)
    if person:
        parts.append(person)
    return "/".join(parts) + "/"
