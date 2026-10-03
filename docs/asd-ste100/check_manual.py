#!/usr/bin/env python3
"""Build and check the bilingual manual. Python standard library only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = HERE / "manual-data.json"
LINK = re.compile(r"(!?\[[^\]\n]*\])\(([^)\n]+)\)")
CODE = re.compile(r"\x60([^\x60\n]+)\x60")
REPORTS = HERE / "checks"


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read(path):
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def write_report(name, value):
    # Force LF so a run on Windows does not leave CRLF changes in tracked reports.
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def slug(doc):
    return "index" if doc["source"].endswith("/console-task-manual.md") else Path(doc["source"]).stem


def rebase(text, doc, destination, sources, language):
    def replace(match):
        label, target = match.groups()
        if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
            return match.group(0)
        name, mark, fragment = target.partition("#")
        resolved = (ROOT / doc["source"]).parent.joinpath(name).resolve()
        linked = sources.get(resolved)
        if linked and language in ("zh-TW", "en"):
            resolved = HERE / language / (slug(linked) + ".md")
        relative = os.path.relpath(resolved, destination.parent).replace(os.sep, "/")
        return f"{label}({relative}{mark}{fragment})"
    return LINK.sub(replace, text)


def cell(text):
    # Keep code and labels visible, but prevent raw anchors from affecting the table.
    text = re.sub(r'<a id="([^"]+)"></a>', r'Anchor: \1', text)
    text = re.sub(r"(?m)^#{1,6} (.+)$", r"**\1**", text)
    text = re.sub(r"!\[([^\]]*)\]", r"[\1]", text)
    # Escape pipes outside and inside code spans for CommonMark tables.
    return text.replace("|", r"\|").replace("\n", "<br>")


def render(data):
    outputs = {}
    sources = {(ROOT / d["source"]).resolve(): d for d in data["documents"]}
    for doc in data["documents"]:
        by_id = {b["id"]: b for b in doc["blocks"]}
        order = doc.get("order", list(by_id))
        for language, key in (("zh-TW", "zh"), ("en", "en")):
            destination = HERE / language / (slug(doc) + ".md")
            body = [rebase(by_id[i][key], doc, destination, sources, language) for i in order]
            outputs[destination] = "\n\n".join(body) + "\n"
        destination = HERE / "comparison" / (slug(doc) + ".md")
        title = doc["blocks"][0]["zh"].lstrip("# ")
        source_link = os.path.relpath(ROOT / doc["source"], destination.parent).replace(os.sep, "/")
        body = [
            f"# {title}：原文與中英文改寫對照",
            f"[原始手冊]({source_link}) · [繁中版](../zh-TW/{slug(doc)}.md) · [English](../en/{slug(doc)}.md)",
            "原文欄保留來源內容。段落 ID 用於追蹤對照。獨立手冊依操作順序排列，必要時將風險說明移到步驟前。",
        ]
        for block in doc["blocks"]:
            body.append(f"## B{block['id']:03d}")
            if block.get("correction"):
                body.append("修正說明：" + block["correction"]["reason"])
            cells = [
                cell(rebase(block[k], doc, destination, sources, "comparison"))
                for k in ("original", "zh", "en")
            ]
            body.append("| 原文 | 繁中改寫 | English STE draft |\n| --- | --- | --- |\n| " + " | ".join(cells) + " |")
        outputs[destination] = "\n\n".join(body) + "\n"
    return outputs


def anchors(text):
    result = set(re.findall(r'<a\s+id="([^"]+)"', text))
    counts = {}
    for heading in re.findall(r"(?m)^#{1,6}\s+(.+)$", text):
        value = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        count = counts.get(value, 0)
        counts[value] = count + 1
        result.add(value if count == 0 else f"{value}-{count}")
    return result


def numeric_values(text):
    text = re.sub(r"(?m)^\d+\.\s+", "", text)
    return set(re.findall(r"(?<![\w])\d+(?:\.\d+)*(?![\w])", text))


def procedure_lengths(path, text):
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        if not re.match(r"^\d+\. ", line):
            continue
        line = re.sub(r"^\d+\. ", "", line)
        line = CODE.sub("IDENTIFIER", line)
        line = re.sub(r"「[^」]+」", "LABEL", line)
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            words = re.findall(r"[A-Za-z0-9]+(?:[-'/][A-Za-z0-9]+)*", sentence)
            if len(words) > 20:
                findings.append(f"Procedure over 20 words: {path.name}:{number}: {len(words)}: {sentence}")
    return findings


def table_errors(path, text):
    """Check that every GFM table row has the same cell count as its header."""
    errors = []
    tables = 0
    width = None
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith(("~~~", "```")):
            fenced = not fenced
        if fenced or not line.startswith("|"):
            width = None
            continue
        cells = len(re.split(r"(?<!\\)\|", line.strip().strip("|")))
        if width is None:
            width = cells
            tables += 1
        elif cells != width:
            errors.append(f"Table cell count {cells} != {width}: {path.name}:{number}")
    return tables, errors


def markdown_files():
    return sorted(p for p in HERE.rglob("*.md") if p.is_file())


def validate(data, outputs):
    errors = []
    for doc in data["documents"]:
        source = ROOT / doc["source"]
        actual = re.split(r"\n\s*\n", read(source).strip())
        expected = [b["original"] for b in doc["blocks"]]
        if actual != expected:
            errors.append(f"Source changed or coverage incomplete: {doc['source']}")
        ids = [b["id"] for b in doc["blocks"]]
        order = doc.get("order", ids)
        if len(set(ids)) != len(ids) or sorted(order) != sorted(ids):
            errors.append(f"Invalid block IDs or output order: {doc['source']}")
        for block in doc["blocks"]:
            for language in ("zh", "en"):
                value = block.get(language, "")
                if not value.strip():
                    errors.append(f"Empty {language}: {doc['source']} B{block['id']:03d}")
                missing = set(CODE.findall(block["original"])) - set(CODE.findall(value))
                if missing:
                    errors.append(f"Missing identifiers in {language} {doc['source']} B{block['id']:03d}: {sorted(missing)}")
                missing_numbers = numeric_values(block["original"]) - numeric_values(value)
                if missing_numbers:
                    errors.append(f"Missing numeric values in {language} {doc['source']} B{block['id']:03d}: {sorted(missing_numbers)}")
                old_ids = re.findall(r'<a id="([^"]+)"', block["original"])
                new_ids = re.findall(r'<a id="([^"]+)"', value)
                if old_ids != new_ids:
                    errors.append(f"Changed task anchors: {doc['source']} B{block['id']:03d}")
    for file, expected in outputs.items():
        if file.parent.name == "en":
            errors.extend(procedure_lengths(file, expected))
        if not file.exists() or read(file) != expected:
            errors.append(f"Generated file missing or stale: {file.relative_to(HERE)}")
        for _, target in LINK.findall(expected):
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            name, mark, fragment = target.partition("#")
            resolved = file.parent.joinpath(name).resolve() if name else file
            if not resolved.is_file():
                errors.append(f"Missing link: {file.relative_to(HERE)} -> {target}")
            elif mark and resolved.suffix == ".md" and fragment not in anchors(read(resolved)):
                errors.append(f"Missing anchor: {file.relative_to(HERE)} -> {target}")
    for file in markdown_files():
        text = outputs.get(file) or read(file)
        errors.extend(table_errors(file, text)[1])
    return errors


class MCP:
    """Minimal JSON-RPC stdio client with bounded waits and no shell invocation."""
    def __init__(self, executable):
        self.proc = subprocess.Popen(
            [str(executable)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.inbox = queue.Queue()
        self.stderr_tail = []
        self.next_id = 0
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        self.call("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "tak-manual-check", "version": "1.0"},
        })
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _read_stdout(self):
        for line in self.proc.stdout:
            try:
                self.inbox.put(json.loads(line))
            except json.JSONDecodeError:
                self.inbox.put({"protocol_error": line.rstrip()})
        self.inbox.put({"eof": True})

    def _read_stderr(self):
        for line in self.proc.stderr:
            self.stderr_tail.append(line.rstrip())
            self.stderr_tail = self.stderr_tail[-10:]

    def send(self, message):
        self.proc.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def call(self, method, params):
        self.next_id += 1
        request_id = self.next_id
        self.send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + 60
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(f"MCP timeout: {method}")
            response = self.inbox.get(timeout=remaining)
            if response.get("eof") or response.get("protocol_error"):
                raise RuntimeError(f"MCP ended or sent invalid output: {response}; {self.stderr_tail}")
            if response.get("id") == request_id:
                if "error" in response:
                    raise RuntimeError(str(response["error"]))
                return response["result"]

    def close(self):
        if self.proc.stdin:
            self.proc.stdin.close()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            self.proc.wait(timeout=5)


def check_zhtw(outputs, executable):
    executable = executable or shutil.which("zhtw-mcp") or shutil.which("zhtw-mcp.exe")
    if not executable:
        raise RuntimeError("zhtw-mcp is unavailable. Use --zhtw-command PATH.")
    client = MCP(executable)
    errors = []
    results = []
    try:
        candidates = {p: t for p, t in outputs.items() if p.parent.name == "zh-TW"}
        candidates[HERE / "README.md"] = read(HERE / "README.md")
        for path, content in candidates.items():
            arguments = {
                "text": content, "content_type": "markdown", "fix_mode": "none",
                "max_errors": 0, "max_warnings": 0, "output": "full",
                "include_stats": True, "detect_style": True,
                "detect_ai": True, "detect_translationese": True,
                "consistency": True, "translationese_domain": "technical",
                "glossary": {"proper_nouns": json.loads(read(HERE / "glossary.json"))["proper_nouns"]},
            }
            response = client.call("tools/call", {"name": "zhtw", "arguments": arguments})
            payloads = [json.loads(c["text"]) for c in response.get("content", []) if c.get("type") == "text"]
            result = next((p for p in payloads if "accepted" in p), None)
            if result is None:
                raise RuntimeError(f"Missing zhtw result: {response}")
            results.append({
                "file": path.relative_to(HERE).as_posix(),
                "sha256": digest(content),
                "glossary_sha256": digest(read(HERE / "glossary.json")),
                # The echoed text duplicates the checked file; its hash is enough.
                "result": {k: v for k, v in result.items() if k != "text"},
            })
            if not result["accepted"] or result["summary"]["errors"] or result["summary"]["warnings"]:
                errors.append(f"zhtw gate failed: {path.name}: {result['summary']}")
            print(f"zhtw {path.name}: {result['summary']}")
    finally:
        client.close()
    write_report("zhtw.json", results)
    return errors


def check_ste(outputs, linter):
    if linter is None:
        raise RuntimeError("Use --ste-linter PATH for the skill's scripts/ste-lint.py.")
    paths = [p for p in outputs if p.parent.name == "en"]
    result = subprocess.run(
        [sys.executable, str(linter), *map(str, paths), "--json"],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"STE linter failed: {result.stderr or result.stdout}")
    report = json.loads(result.stdout)
    # Keep evidence portable: do not publish local checkout or skill paths.
    for finding in report.get("violations", []):
        if "file" in finding:
            finding["file"] = Path(finding["file"]).resolve().relative_to(ROOT).as_posix()
    write_report("ste.json", {
        "exit_code": result.returncode,
        "files": {p.relative_to(HERE).as_posix(): digest(outputs[p]) for p in paths},
        "report": report,
    })
    print(f"STE structural lint exit: {result.returncode}")
    return [] if result.returncode == 0 else ["STE structural gate failed; see checks/ste.json"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate manuals and comparisons.")
    parser.add_argument("--ste-linter", type=Path, help="Path to the invoked skill's ste-lint.py.")
    parser.add_argument("--zhtw", action="store_true", help="Run a fresh zero-error, zero-warning zhtw-mcp gate.")
    parser.add_argument("--zhtw-command", type=Path, help="Path to zhtw-mcp executable.")
    args = parser.parse_args()
    data = json.loads(read(DATA))
    outputs = render(data)
    if args.write:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    errors = validate(data, outputs)
    if args.ste_linter:
        errors.extend(check_ste(outputs, args.ste_linter))
    if args.zhtw:
        errors.extend(check_zhtw(outputs, args.zhtw_command))
    files = markdown_files()
    report = {
        "documents": len(data["documents"]),
        "blocks": sum(len(d["blocks"]) for d in data["documents"]),
        "generated_files": len(outputs),
        "markdown_files": len(files),
        "markdown_tables": sum(table_errors(p, outputs.get(p) or read(p))[0] for p in files),
        "checks": ["source coverage", "generated file freshness", "inline identifiers", "numeric values", "task anchors", "local links", "procedure sentence length", "markdown table cells"],
        "ste_requested": bool(args.ste_linter), "zhtw_requested": args.zhtw,
        "errors": errors,
    }
    # A plain check is read-only; only a full language run refreshes the evidence set.
    if args.ste_linter and args.zhtw:
        write_report("structure.json", report)
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, queue.Empty) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
