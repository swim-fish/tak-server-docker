"""Persistent ICU squad to TAK group mapping."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path


SQUADS = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel")
ALL_GROUP = "team-all"
MAPPING_FILE = Path(os.environ.get("SQUAD_GROUPS_FILE", "/cert-control/squad_groups.json"))
GROUP_PATTERN = re.compile(r"team-[A-Za-z0-9][A-Za-z0-9_-]{0,58}$")


def defaults() -> dict[str, str]:
    return {squad: f"team-{squad}" for squad in SQUADS}


def validate(mapping: dict) -> dict[str, str]:
    if not isinstance(mapping, dict) or set(mapping) != set(SQUADS):
        raise ValueError("Provide one TAK group for each ICU squad")
    result = {}
    for squad in SQUADS:
        group = mapping[squad]
        if not isinstance(group, str) or not GROUP_PATTERN.fullmatch(group) or group == ALL_GROUP:
            raise ValueError(f"Invalid TAK group for {squad}")
        result[squad] = group
    if len(set(result.values())) != len(SQUADS):
        raise ValueError("Each ICU squad needs a distinct TAK group")
    return result


def load() -> dict[str, str]:
    if not MAPPING_FILE.is_file():
        return defaults()
    data = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("Unsupported squad mapping version")
    return validate(data["groups"])


def save(mapping: dict) -> None:
    validated = validate(mapping)
    MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
    pending = MAPPING_FILE.with_name(MAPPING_FILE.name + "." + uuid.uuid4().hex + ".pending")
    try:
        pending.write_text(json.dumps({"version": 1, "groups": validated}, indent=2) + "\n",
                           encoding="utf-8")
        os.replace(pending, MAPPING_FILE)
    finally:
        pending.unlink(missing_ok=True)


def catalog(existing: list[str]) -> list[str]:
    return sorted(set(existing) | set(load().values()) | {ALL_GROUP})
