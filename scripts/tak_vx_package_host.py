"""Build and replace the fixed-name Vx package through the TAK Server API."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import build_tak_vx_package
import tak_api_client


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime"
JOBS = RUNTIME / "tak-vx-control" / "jobs"
NATIVE = RUNTIME / "device-vx-2026-09-22" / "vx-mission-a-native.zip"
CHANNELS = RUNTIME / "packages" / "atak" / "channels.json"
DISPLAY_NAME = "ATAK Local Voice"
MISSION_NAME = "vx-local"
HOST = "takbox.local"
PORT = 40000
HASH = re.compile(r"[0-9a-fA-F]{64}\Z")
JOB_ID = re.compile(r"[0-9a-f]{32}\Z")


def job_dir(job_id: str) -> Path:
    if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
        raise ValueError("Invalid Vx operation ID")
    return JOBS / job_id


def read_job(job_id: str) -> dict:
    journal = job_dir(job_id) / "journal.json"
    if not journal.is_file():
        raise ValueError("Vx operation does not exist")
    return json.loads(journal.read_text(encoding="utf-8"))


def save_job(job_id: str, data: dict) -> None:
    journal = job_dir(job_id) / "journal.json"
    pending = journal.with_suffix(".pending")
    pending.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, journal)


def exact_packages() -> list[dict]:
    path = "/Marti/api/sync/search?name=" + quote(DISPLAY_NAME)
    response = json.loads(tak_api_client.package_request("GET", path))
    records = response.get("results", response.get("data", []))
    if not isinstance(records, list):
        raise RuntimeError("TAK package search returned an invalid result list")
    matched = []
    for item in records:
        if not isinstance(item, dict) or item.get("Name", item.get("name")) != DISPLAY_NAME:
            continue
        matched.append({"Name": DISPLAY_NAME, "Hash": item.get("Hash", item.get("hash")),
                        "Tool": item.get("Tool", item.get("tool")),
                        "Keywords": item.get("Keywords", item.get("keywords", [])),
                        "Filename": item.get("Filename", item.get("filename"))})
    for item in matched:
        if not isinstance(item.get("Hash"), str) or not HASH.fullmatch(item["Hash"]):
            raise RuntimeError("TAK package search returned an invalid hash")
    return matched


def manifest_summary(path: Path) -> dict:
    entries = build_tak_vx_package.read_archive(path)
    from xml.etree import ElementTree
    manifest = ElementTree.fromstring(entries["MANIFEST/manifest.xml"])
    config = manifest.find("Configuration")
    if config is None:
        raise RuntimeError("Vx package has no configuration")
    values = {entry.get("name"): entry.get("value") for entry in config}
    if values.get("name") != DISPLAY_NAME or values.get("onReceiveAction") != (
            "com.atakmap.android.gbr.multicastvoice.sharing.downloaded"):
        raise RuntimeError("Vx package manifest is not the expected server download package")
    contents = manifest.find("Contents")
    payloads = [element.get("zipEntry") for element in contents] if contents is not None else []
    if len(payloads) != 2 or set(entries) != set(payloads) | {"MANIFEST/manifest.xml"}:
        raise RuntimeError("Vx-only package contains unexpected files")
    proto_path = next((name for name in payloads if name.endswith("_proto")), None)
    json_path = next((name for name in payloads if name != proto_path), None)
    if not proto_path or not json_path:
        raise RuntimeError("Vx package is missing its mission payloads")
    legacy = json.loads(entries[json_path])
    expected_channels = json.loads(CHANNELS.read_text(encoding="utf-8-sig"))
    actual = legacy.get("channels", [])
    if (legacy.get("name") != MISSION_NAME or len(actual) != len(expected_channels) or
            any(not channel.get("isMumble") or channel.get("host") != f"{HOST}:{PORT}" or
                channel.get("name") != spec["alias"] or
                channel.get("subtitle") != spec["mumble_channel_name"] or
                channel.get("serverChannelId") != spec["mumble_channel_id"]
                for channel, spec in zip(actual, expected_channels))):
        raise RuntimeError("Vx JSON channels differ from the requested server and channel list")
    root = build_tak_vx_package.decode(entries[proto_path])
    wrappers = build_tak_vx_package.decode(build_tak_vx_package.field(root, 3))
    if (build_tak_vx_package.field(root, 2).decode() != MISSION_NAME or
            sum(number == 1 and wire == 2 for number, wire, _ in wrappers) != len(expected_channels)):
        raise RuntimeError("Vx protobuf mission differs from the requested channel list")
    return {"name": DISPLAY_NAME, "mission": MISSION_NAME, "host": HOST, "port": PORT,
            "channels": expected_channels}


def prepare(job_id: str) -> dict:
    directory = job_dir(job_id)
    if directory.exists():
        return read_job(job_id)
    if not NATIVE.is_file() or not CHANNELS.is_file():
        raise RuntimeError("Verified Vx native template or channel list is unavailable")
    existing = exact_packages()
    directory.mkdir(parents=True, exist_ok=False)
    output = directory / "atak-local-vx.dpk"
    save_job(job_id, {"job_id": job_id, "state": "preparing", "old": existing, "deleted": []})
    try:
        channels = json.loads(CHANNELS.read_text(encoding="utf-8-sig"))
        build_tak_vx_package.build(RUNTIME / "packages" / "atak" / "atak-local-test.dpk",
                                   NATIVE, output, HOST, PORT, MISSION_NAME,
                                   vx_only=True, channels=channels, package_name=DISPLAY_NAME)
        if output.stat().st_size > 10 * 1024 * 1024:
            raise RuntimeError("Vx package exceeds the size limit")
        summary = manifest_summary(output)
    except Exception as exc:
        save_job(job_id, {"job_id": job_id, "state": "failed-before-delete", "error": str(exc),
                          "old": existing, "deleted": []})
        raise
    result = {"job_id": job_id, "state": "prepared", "created_at": datetime.now(timezone.utc).isoformat(),
              "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "size": output.stat().st_size,
              "old": existing, "deleted": [], "uploaded": False, "summary": summary}
    save_job(job_id, result)
    return result


def upload(path: Path, filename: str = "atak-local-vx.dpk") -> str:
    if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,120}\.(?:dpk|zip)", filename):
        raise ValueError("Invalid Vx package filename")
    payload = path.read_bytes()
    expected = hashlib.sha256(payload).hexdigest()
    boundary = "takvx" + secrets.token_hex(12)
    multipart = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"assetfile\"; filename=\"{filename}\"\r\n"
        "Content-Type: application/x-zip-compressed\r\n\r\n".encode("ascii") + payload +
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"Name\"\r\n\r\n{DISPLAY_NAME}\r\n"
        f"--{boundary}--\r\n".encode("ascii"))
    response = tak_api_client.package_request("POST", "/Marti/sync/upload", multipart,
                                              "multipart/form-data; boundary=" + boundary)
    returned = json.loads(response)
    def has_expected_hash(value: object) -> bool:
        if isinstance(value, dict):
            return any(has_expected_hash(item) for item in value.values())
        if isinstance(value, list):
            return any(has_expected_hash(item) for item in value)
        return isinstance(value, str) and value.lower() == expected
    if not has_expected_hash(returned):
        raise RuntimeError("TAK upload returned a different SHA-256 hash")
    return expected


def set_public_metadata(digest: str) -> None:
    prefix = "/Marti/api/sync/metadata/" + digest
    # TAK's generic metadata endpoint reads a raw string and rejects JSON quotes.
    tak_api_client.package_request("PUT", prefix + "/tool", b"public", "application/json")
    tak_api_client.package_request("PUT", prefix + "/keywords", b'["missionpackage"]', "application/json")


def verify_single(digest: str) -> dict:
    for _ in range(12):
        matched = exact_packages()
        if len(matched) == 1 and matched[0]["Hash"].lower() == digest.lower():
            item = matched[0]
            if item.get("Tool") == "public" and "missionpackage" in item.get("Keywords", []):
                return item
        time.sleep(1)
    raise RuntimeError("TAK did not confirm one public missionpackage with the expected hash")


def replace(job_id: str) -> dict:
    data = read_job(job_id)
    if data["state"] == "complete":
        return data
    if data["state"] == "needs-recovery" and data.get("uploaded"):
        current = exact_packages()
        if len(current) == 1 and current[0]["Hash"].lower() == data["sha256"]:
            set_public_metadata(data["sha256"])
            data["server_record"] = verify_single(data["sha256"])
            data["state"] = "complete"
            data.pop("error", None)
            save_job(job_id, data)
            return data
    if data["state"] != "prepared":
        raise RuntimeError("Vx operation requires inspection or recovery before retry")
    current = exact_packages()
    if sorted(item["Hash"] for item in current) != sorted(item["Hash"] for item in data["old"]):
        raise RuntimeError("TAK package list changed after preview; prepare a new operation")
    output = job_dir(job_id) / "atak-local-vx.dpk"
    if hashlib.sha256(output.read_bytes()).hexdigest() != data["sha256"]:
        raise RuntimeError("Prepared Vx package changed")
    data["state"] = "backing-up"
    save_job(job_id, data)
    try:
        for item in data["old"]:
            digest = item["Hash"].lower()
            target = job_dir(job_id) / (digest + ".dpk")
            if not target.exists():
                content = tak_api_client.package_request("GET", "/Marti/api/files/" + digest)
                target.write_bytes(content)
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise RuntimeError("Backed-up Vx package has the wrong hash")
        data["state"] = "replacing"
        save_job(job_id, data)
        for item in data["old"]:
            digest = item["Hash"].lower()
            tak_api_client.package_request("DELETE", "/Marti/api/files/" + digest)
            data["deleted"].append(digest)
            save_job(job_id, data)
        if exact_packages():
            raise RuntimeError("Old fixed-name Vx package is still present after deletion")
        upload(output)
        data["uploaded"] = True
        save_job(job_id, data)
        set_public_metadata(data["sha256"])
        data["server_record"] = verify_single(data["sha256"])
        data["state"] = "complete"
        save_job(job_id, data)
        return data
    except Exception as exc:
        data["state"] = "needs-recovery" if data["deleted"] else "failed-before-delete"
        data["error"] = str(exc)
        save_job(job_id, data)
        raise


def restore(job_id: str) -> dict:
    data = read_job(job_id)
    if data["state"] == "restored":
        return data
    if data["state"] not in {"needs-recovery", "replacing"}:
        raise ValueError("This Vx operation does not need a backup restore")
    if not data["old"]:
        raise RuntimeError("No previous package exists to restore")
    for item in data["old"]:
        digest = item["Hash"].lower()
        backup = job_dir(job_id) / (digest + ".dpk")
        if not backup.is_file() or hashlib.sha256(backup.read_bytes()).hexdigest() != digest:
            raise RuntimeError("A required Vx backup is unavailable or damaged")
    current = exact_packages()
    for item in current:
        if item["Hash"].lower() == data["sha256"]:
            tak_api_client.package_request("DELETE", "/Marti/api/files/" + data["sha256"])
    for item in data["old"]:
        digest = item["Hash"].lower()
        if digest not in {entry["Hash"].lower() for entry in exact_packages()}:
            upload(job_dir(job_id) / (digest + ".dpk"), item.get("Filename") or "atak-local-vx.dpk")
        if item.get("Tool"):
            tak_api_client.package_request("PUT", "/Marti/api/sync/metadata/" + digest + "/tool",
                                           item["Tool"].encode("utf-8"), "application/json")
        if item.get("Keywords"):
            tak_api_client.package_request("PUT", "/Marti/api/sync/metadata/" + digest + "/keywords",
                                           json.dumps(item["Keywords"]).encode(), "application/json")
    current = exact_packages()
    if sorted(item["Hash"].lower() for item in current) != sorted(item["Hash"].lower() for item in data["old"]):
        raise RuntimeError("TAK did not restore the previous fixed-name package set")
    data["state"] = "restored"
    data["restored_at"] = datetime.now(timezone.utc).isoformat()
    save_job(job_id, data)
    return data
