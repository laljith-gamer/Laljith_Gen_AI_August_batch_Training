"""
Generate a PDF version of the final project report from final_report.md.

Dual-engine implementation:
  1. Primary: Uses `fpdf2` if installed.
  2. Fallback: Creates a valid PDF-1.4 file using raw PDF bytes (pure Python stdlib, zero dependencies).

Usage (from project root):
    python scripts/generate_report_pdf.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_MD = PROJECT_ROOT / "reports" / "final_report.md"
REPORT_PDF = PROJECT_ROOT / "reports" / "final_report.pdf"


def _sanitize(text: str) -> str:
    """Replace Unicode characters unsupported by latin-1 with ASCII equivalents."""
    replacements = {
        "\u2014": "--", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2022": "-", "\u2026": "...",
        "\u2192": "->", "\u2190": "<-", "\u00a0": " ",
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _clean_md(text: str) -> str:
    """Strip markdown formatting from text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def _generate_fpdf() -> None:
    from fpdf import FPDF

    md_text = _sanitize(REPORT_MD.read_text(encoding="utf-8"))

    pdf = FPDF()
    pdf.add_page()
    left_margin = pdf.l_margin

    def mc(height: int, text: str) -> None:
        """multi_cell wrapper that resets X to left margin after each call."""
        pdf.multi_cell(0, height, text)
        pdf.set_x(left_margin)

    pdf.set_font("Helvetica", size=10)

    for line in md_text.split("\n"):
        stripped = line.strip()

        if not stripped:
            pdf.ln(3)
            continue

        if stripped.startswith("---"):
            pdf.ln(4)
            continue

        # H1
        if stripped.startswith("# ") and not stripped.startswith("##"):
            title = stripped.lstrip("# ").strip()
            pdf.set_font("Helvetica", "B", 16)
            mc(9, title)
            pdf.ln(2)
            pdf.set_font("Helvetica", size=10)
            continue

        # H2
        if stripped.startswith("## "):
            title = stripped.lstrip("# ").strip()
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 13)
            mc(8, title)
            pdf.ln(1)
            pdf.set_font("Helvetica", size=10)
            continue

        # H3
        if stripped.startswith("### "):
            title = stripped.lstrip("# ").strip()
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 11)
            mc(7, title)
            pdf.ln(1)
            pdf.set_font("Helvetica", size=10)
            continue

        # Bold metadata lines
        if stripped.startswith("**") and ":**" in stripped:
            clean = _clean_md(stripped)
            pdf.set_font("Helvetica", "B", 10)
            mc(6, clean)
            pdf.set_font("Helvetica", size=10)
            continue

        # Numbered list items
        if re.match(r"^\d+\.\s", stripped):
            clean = _clean_md(stripped)
            mc(6, clean)
            continue

        # Bullet list items
        if stripped.startswith("- "):
            clean = _clean_md(stripped[2:])
            mc(6, "  - " + clean)
            continue

        # Indented sub-items
        if line.startswith("  ") and stripped:
            clean = _clean_md(stripped)
            mc(6, "    " + clean)
            continue

        # Regular paragraph text
        clean = _clean_md(stripped)
        mc(6, clean)

    REPORT_PDF.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(REPORT_PDF))
    size = REPORT_PDF.stat().st_size
    print(f"[DONE] PDF written to {REPORT_PDF} ({size:,} bytes) via fpdf2")


def _wrap_text(text: str, max_chars: int = 85) -> List[str]:
    """Wrap plain text into lines of at most max_chars."""
    words = text.split(" ")
    lines = []
    cur = []
    cur_len = 0
    for w in words:
        if not w:
            continue
        if cur_len + len(w) + (1 if cur else 0) <= max_chars:
            cur.append(w)
            cur_len += len(w) + (1 if len(cur) > 1 else 0)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
    if cur:
        lines.append(" ".join(cur))
    return lines or [""]


def _escape_pdf(s: str) -> str:
    """Escape string characters for PDF text operators."""
    s = s.encode("latin-1", "replace").decode("latin-1")
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _generate_raw_pdf() -> None:
    """Pure-Python standard library PDF-1.4 generation fallback."""
    md_text = _sanitize(REPORT_MD.read_text(encoding="utf-8"))

    page_width, page_height = 612.0, 792.0
    left_margin, right_margin = 54.0, 558.0
    top_margin, bottom_margin = 738.0, 54.0

    pages_streams: List[str] = []
    current_stream: List[str] = []
    current_y = top_margin

    def new_page():
        nonlocal current_y, current_stream
        if current_stream:
            page_num = len(pages_streams) + 1
            footer = (
                f"BT /F1 8 Tf 0.5 0.5 0.5 rg {page_width/2 - 35:.1f} 32 Td "
                f"({_escape_pdf(f'Page {page_num}')}) Tj ET\n"
                f"0.8 0.8 0.8 RG 0.5 w {left_margin:.1f} 44 m {right_margin:.1f} 44 l S\n"
            )
            current_stream.append(footer)
            pages_streams.append("".join(current_stream))
        current_stream = []
        current_y = top_margin
        if len(pages_streams) >= 1:
            header = (
                f"BT /F1 8 Tf 0.45 0.5 0.55 rg {right_margin - 220:.1f} 755 Td "
                f"({_escape_pdf('SmartHire GenAI -- Capstone Final Report')}) Tj ET\n"
                f"0.85 0.85 0.85 RG 0.5 w {left_margin:.1f} 748 m {right_margin:.1f} 748 l S\n"
            )
            current_stream.append(header)
            current_y = 730.0

    def check_space(needed: float):
        nonlocal current_y
        if current_y - needed < bottom_margin:
            new_page()

    for line in md_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            current_y -= 6
            continue

        if stripped.startswith("---"):
            check_space(15)
            current_stream.append(
                f"0.85 0.85 0.85 RG 0.5 w {left_margin:.1f} {current_y:.1f} m {right_margin:.1f} {current_y:.1f} l S\n"
            )
            current_y -= 14
            continue

        if stripped.startswith("# ") and not stripped.startswith("##"):
            title = _clean_md(stripped.lstrip("# ").strip())
            check_space(30)
            current_stream.append(
                f"BT /F2 16 Tf 0.08 0.12 0.20 rg {left_margin:.1f} {current_y:.1f} Td "
                f"({_escape_pdf(title)}) Tj ET\n"
            )
            current_y -= 22
            continue

        if stripped.startswith("## "):
            title = _clean_md(stripped.lstrip("# ").strip())
            check_space(26)
            current_y -= 4
            current_stream.append(
                f"0.15 0.35 0.85 rg {left_margin:.1f} {current_y - 2:.1f} 3.0 12.0 re f\n"
                f"BT /F2 13 Tf 0.08 0.12 0.20 rg {left_margin + 7:.1f} {current_y:.1f} Td "
                f"({_escape_pdf(title)}) Tj ET\n"
            )
            current_y -= 18
            continue

        if stripped.startswith("### "):
            title = _clean_md(stripped.lstrip("# ").strip())
            check_space(20)
            current_stream.append(
                f"BT /F2 11 Tf 0.12 0.23 0.54 rg {left_margin:.1f} {current_y:.1f} Td "
                f"({_escape_pdf(title)}) Tj ET\n"
            )
            current_y -= 15
            continue

        if stripped.startswith("**") and ":**" in stripped:
            clean = _clean_md(stripped)
            wrapped = _wrap_text(clean, max_chars=82)
            check_space(len(wrapped) * 12 + 4)
            for w in wrapped:
                current_stream.append(
                    f"BT /F2 10 Tf 0.15 0.20 0.28 rg {left_margin:.1f} {current_y:.1f} Td "
                    f"({_escape_pdf(w)}) Tj ET\n"
                )
                current_y -= 12
            current_y -= 2
            continue

        if stripped.startswith("- "):
            clean = "  - " + _clean_md(stripped[2:])
            wrapped = _wrap_text(clean, max_chars=84)
            check_space(len(wrapped) * 12 + 2)
            for w in wrapped:
                current_stream.append(
                    f"BT /F1 9.5 Tf 0.20 0.25 0.33 rg {left_margin:.1f} {current_y:.1f} Td "
                    f"({_escape_pdf(w)}) Tj ET\n"
                )
                current_y -= 12
            continue

        if re.match(r"^\d+\.\s", stripped):
            clean = _clean_md(stripped)
            wrapped = _wrap_text(clean, max_chars=84)
            check_space(len(wrapped) * 12 + 2)
            for w in wrapped:
                current_stream.append(
                    f"BT /F1 9.5 Tf 0.20 0.25 0.33 rg {left_margin:.1f} {current_y:.1f} Td "
                    f"({_escape_pdf(w)}) Tj ET\n"
                )
                current_y -= 12
            continue

        if line.startswith("  ") and stripped:
            clean = "    " + _clean_md(stripped)
            wrapped = _wrap_text(clean, max_chars=80)
            check_space(len(wrapped) * 12 + 2)
            for w in wrapped:
                current_stream.append(
                    f"BT /F1 9.5 Tf 0.20 0.25 0.33 rg {left_margin:.1f} {current_y:.1f} Td "
                    f"({_escape_pdf(w)}) Tj ET\n"
                )
                current_y -= 12
            continue

        clean = _clean_md(stripped)
        wrapped = _wrap_text(clean, max_chars=86)
        check_space(len(wrapped) * 12 + 4)
        for w in wrapped:
            current_stream.append(
                f"BT /F1 9.5 Tf 0.20 0.25 0.33 rg {left_margin:.1f} {current_y:.1f} Td "
                f"({_escape_pdf(w)}) Tj ET\n"
            )
            current_y -= 12
        current_y -= 3

    if current_stream:
        page_num = len(pages_streams) + 1
        footer = (
            f"BT /F1 8 Tf 0.5 0.5 0.5 rg {page_width/2 - 35:.1f} 32 Td "
            f"({_escape_pdf(f'Page {page_num}')}) Tj ET\n"
            f"0.8 0.8 0.8 RG 0.5 w {left_margin:.1f} 44 m {right_margin:.1f} 44 l S\n"
        )
        current_stream.append(footer)
        pages_streams.append("".join(current_stream))

    num_pages = len(pages_streams)
    kids = " ".join(f"{6 + 2*k} 0 R" for k in range(num_pages))

    objs = {}
    objs[1] = "<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = f"<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>"
    objs[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    objs[4] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
    objs[5] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>"

    for k, stream_content in enumerate(pages_streams):
        page_id = 6 + 2 * k
        stream_id = 7 + 2 * k
        objs[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Contents {stream_id} 0 R "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> >>"
        )
        stream_bytes = stream_content.encode("latin-1", "replace")
        objs[stream_id] = (
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1")
            + stream_bytes
            + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    xref = {}
    for obj_id in sorted(objs.keys()):
        xref[obj_id] = len(out)
        out.extend(f"{obj_id} 0 obj\n".encode("latin-1"))
        val = objs[obj_id]
        if isinstance(val, str):
            out.extend(val.encode("latin-1"))
        else:
            out.extend(val)
        out.extend(b"\nendobj\n")

    xref_offset = len(out)
    total_objs = len(objs) + 1
    out.extend(f"xref\n0 {total_objs}\n0000000000 65535 f \n".encode("latin-1"))
    for obj_id in sorted(objs.keys()):
        offset = xref[obj_id]
        out.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    out.extend(
        f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
    )

    REPORT_PDF.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PDF, "wb") as f:
        f.write(out)
    size = REPORT_PDF.stat().st_size
    print(f"[DONE] PDF written to {REPORT_PDF} ({size:,} bytes) via pure-Python raw PDF generator")


def generate_pdf() -> None:
    """Generate the PDF using fpdf2, falling back to raw PDF generation."""
    try:
        from fpdf import FPDF
        _generate_fpdf()
    except ImportError:
        print("[Notice] fpdf2 not installed. Falling back to built-in raw PDF generator...", file=sys.stderr)
        _generate_raw_pdf()


if __name__ == "__main__":
    generate_pdf()
