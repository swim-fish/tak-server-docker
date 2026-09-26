"""Build the console manual and certificate trust report from Markdown sources.

Run with the Codex workspace Python runtime, which provides python-docx and Pillow.
The Markdown files remain the editable source of truth.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "docs" / "reports"
MANUAL_SOURCES = [
    ROOT / "docs" / "tak-server" / "console-task-manual.md",
    ROOT / "docs" / "tak-server" / "console-task-manual" / "certificates-and-groups.md",
    ROOT / "docs" / "tak-server" / "console-task-manual" / "vx-and-mumble.md",
    ROOT / "docs" / "tak-server" / "console-task-manual" / "icu-and-mediamtx.md",
    ROOT / "docs" / "tak-server" / "console-task-manual" / "sharing-and-troubleshooting.md",
]
TRUST_SOURCE = REPORTS / "tak-certificate-trust-design-report.md"
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^]]+\]\([^)]+\))")
IMAGE = re.compile(r"^!\[([^]]*)\]\(([^)]+)\)$")
LIST = re.compile(r"^(\d+)\.\s+(.+)$|^[-*]\s+(.+)$")


def set_font(style, size: float, *, bold: bool = False) -> None:
    style.font.name = "Microsoft JhengHei"
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")


def set_cell_fill(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_borders(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        tag = OxmlElement(f"w:{side}")
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), "4")
        tag.set(qn("w:color"), "D9D9D9")
        borders.append(tag)
    tc_pr.append(borders)


def add_inline(paragraph, text: str) -> None:
    parts = INLINE.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        elif part.startswith("["):
            match = re.match(r"\[([^]]+)\]\(([^)]+)\)", part)
            if match:
                paragraph.add_run(match.group(1))
            else:
                paragraph.add_run(part)
        else:
            paragraph.add_run(part)


def make_document(short_title: str) -> Document:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.66)
    section.left_margin = Inches(0.82)
    section.right_margin = Inches(0.82)
    section.header_distance = Inches(0.35)
    section.footer_distance = Inches(0.34)

    styles = doc.styles
    set_font(styles["Normal"], 10.5)
    styles["Normal"].paragraph_format.space_after = Pt(7)
    styles["Normal"].paragraph_format.line_spacing = 1.2
    set_font(styles["Title"], 20, bold=True)
    styles["Title"].paragraph_format.space_after = Pt(14)
    title_properties = styles["Title"]._element.get_or_add_pPr()
    for border in title_properties.findall(qn("w:pBdr")):
        title_properties.remove(border)
    for name, size, before, after in (
        ("Heading 1", 14, 14, 8),
        ("Heading 2", 12, 11, 6),
        ("Heading 3", 11, 9, 4),
    ):
        set_font(styles[name], size, bold=True)
        styles[name].paragraph_format.space_before = Pt(before)
        styles[name].paragraph_format.space_after = Pt(after)
        styles[name].paragraph_format.keep_with_next = True
    set_font(styles["List Number"], 10.5)
    set_font(styles["List Bullet"], 10.5)

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run(short_title)
    run.font.name = "Microsoft JhengHei"
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(90, 90, 90)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run("TAK 5.8 · 2026-09-26 · ")
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    return doc


def add_image(doc: Document, source: Path, alt: str, path_text: str) -> None:
    path = (source.parent / path_text).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{source}: {path_text}")
    with Image.open(path) as img:
        width_px, height_px = img.size
    max_width = 6.7
    max_height = 4.55 if height_px > width_px else 4.1
    # A short banner or compact diagram should not be enlarged past its natural size.
    width = min(max_width, max_height * width_px / height_px)
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(7)
    para.paragraph_format.space_after = Pt(2)
    para.paragraph_format.keep_with_next = True
    shape = para.add_run().add_picture(str(path), width=Inches(width))
    shape._inline.docPr.set("descr", alt)


def add_table(doc: Document, rows: list[str]) -> None:
    parsed = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in rows]
    parsed = [row for row in parsed if not all(re.fullmatch(r":?-+:?", value) for value in row)]
    columns = max(len(row) for row in parsed)
    table = doc.add_table(rows=len(parsed), cols=columns)
    table.autofit = True
    for row_index, row in enumerate(parsed):
        for col_index in range(columns):
            cell = table.cell(row_index, col_index)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_borders(cell)
            if row_index == 0:
                set_cell_fill(cell, "E5ECF0")
            elif row_index % 2 == 0:
                set_cell_fill(cell, "F7F9FA")
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.paragraph_format.space_before = Pt(2)
            add_inline(paragraph, row[col_index] if col_index < len(row) else "")
            if row_index == 0:
                for run in paragraph.runs:
                    run.bold = True
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_source(doc: Document, source: Path, *, first: bool) -> None:
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    index = 0
    if not first:
        # The chapter title becomes a section heading in the combined manual.
        while index < len(lines) and not lines[index].startswith("# "):
            index += 1
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line or line.startswith("<a id=") or line == "[返回任務索引](../console-task-manual.md)":
            continue
        if line.startswith("| "):
            rows = [line]
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(lines[index].strip())
                index += 1
            add_table(doc, rows)
            continue
        image = IMAGE.match(line)
        if image:
            add_image(doc, source, image.group(1), image.group(2))
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            depth = len(heading.group(1))
            style = "Title" if first and depth == 1 else f"Heading {max(1, depth - 1) if first else depth}"
            para = doc.add_paragraph(style=style)
            if source.name == "console-task-manual.md" and heading.group(2) == "依任務找頁面":
                para.paragraph_format.page_break_before = True
            add_inline(para, heading.group(2))
            continue
        list_match = LIST.match(line)
        if list_match:
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Inches(0.26)
            para.paragraph_format.first_line_indent = Inches(-0.26)
            marker = f"{list_match.group(1)}. " if list_match.group(1) else "• "
            para.add_run(marker)
            add_inline(para, list_match.group(2) or list_match.group(3))
            continue
        if line.startswith("圖 ") or re.match(r"圖\s*[A-Z]\s*：", line):
            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.space_after = Pt(10)
            para.paragraph_format.keep_together = True
            add_inline(para, line)
            for run in para.runs:
                run.font.size = Pt(8.5)
                run.font.color.rgb = RGBColor(70, 70, 70)
            continue
        paragraph_lines = [line]
        while index < len(lines) and lines[index].strip() and not re.match(
            r"^(#|!\[|\| |<a id=|\d+\.\s+|[-*]\s+)", lines[index].strip()
        ):
            paragraph_lines.append(lines[index].strip())
            index += 1
        para = doc.add_paragraph()
        add_inline(para, " ".join(paragraph_lines))


def build(source_files: list[Path], output: Path, short_title: str) -> None:
    doc = make_document(short_title)
    for offset, source in enumerate(source_files):
        add_source(doc, source, first=offset == 0)
    doc.core_properties.title = short_title
    doc.core_properties.subject = "Generated from repository Markdown sources"
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    print(f"{output}: {len(doc.inline_shapes)} images, {len(doc.tables)} tables")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate referenced Markdown images only")
    args = parser.parse_args()
    sources = [TRUST_SOURCE, *MANUAL_SOURCES]
    for source in sources:
        for alt, path in IMAGE.findall(source.read_text(encoding="utf-8-sig")):
            if not (source.parent / path).resolve().is_file():
                raise FileNotFoundError(f"{source}: {path} ({alt})")
    if args.check:
        print(f"Validated images in {len(sources)} Markdown files")
        return
    build([TRUST_SOURCE], REPORTS / "tak-certificate-trust-design-report.docx", "TAK 憑證信任設計報告")
    build(MANUAL_SOURCES, REPORTS / "tak-console-task-manual.docx", "TAK 控制台任務操作手冊")


if __name__ == "__main__":
    main()
