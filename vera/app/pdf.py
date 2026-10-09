# ruff: noqa: E501
"""A downloadable PDF of a review or paper, with its evidence (Increment 5).

Pure Python (fpdf2) and a bundled Unicode font family (DejaVu, `vera/app/fonts/`, licence alongside), so it works on a fresh install
with nothing else to set up. The PDF carries what the app's reader shows: the document, a reference list with one entry per line, the
audit result and its findings, and an appendix listing every claim with its source, locator and quote, so a printed copy can still be
checked. It never contains anything the run's own files do not: the title block states the cost and the audit light from them.
"""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

FONTS = Path(__file__).parent / "fonts"
MARGIN = 22
BODY = 10.5
INK = (28, 27, 25)
MUTED = (93, 90, 84)
RULE = (190, 186, 177)
LIGHTS = {"green": (31, 122, 77), "amber": (154, 106, 0), "red": (179, 38, 30)}
LIGHT_WORDS = {
    "green": "Green: the citations are real and each claim is supported by the passage it quotes",
    "amber": "Amber: no check failed, but there are warnings to read",
    "red": "Red: one or more checks failed",
}
REF_LINE = re.compile(r"^\[R\d+\]\s")
IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")


class Paper(FPDF):
    def __init__(self, footer_text: str) -> None:
        super().__init__(format="A4")
        self.footer_text = footer_text
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=MARGIN)
        self.add_font("serif", "", str(FONTS / "DejaVuSerif.ttf"))
        self.add_font("serif", "B", str(FONTS / "DejaVuSerif-Bold.ttf"))
        self.add_font("serif", "I", str(FONTS / "DejaVuSerif-Italic.ttf"))
        self.add_font("serif", "BI", str(FONTS / "DejaVuSerif-BoldItalic.ttf"))
        self.add_font("sans", "", str(FONTS / "DejaVuSans.ttf"))
        self.add_font("sans", "B", str(FONTS / "DejaVuSans-Bold.ttf"))
        self.alias_nb_pages()

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("sans", "", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, 6, self.footer_text, new_x=XPos.LEFT, new_y=YPos.TOP)
        self.cell(0, 6, f"{self.page_no()} / {{nb}}", align="R")


def inline(text: str) -> str:
    """The markdown subset fpdf2 draws (**bold**, __italic__); backticks are dropped, links keep their text."""
    text = re.sub(r"\[([^\]]+)\]\((?:https?://|#)[^)]*\)", r"\1", text)
    text = text.replace("`", "")
    text = re.sub(r"(?<![\*\w])\*([^*\n]+)\*(?!\*)", r"__\1__", text)
    return text


def heading(pdf: Paper, text: str, level: int) -> None:
    sizes = {2: 13.5, 3: 11.5, 4: 10.5}
    pdf.ln(3 if level > 2 else 5)
    pdf.set_font("serif", "B", sizes.get(level, 10.5))
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 6.5, inline(text).replace("**", ""), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if level == 2:
        pdf.set_draw_color(*RULE)
        pdf.line(MARGIN, pdf.get_y(), pdf.w - MARGIN, pdf.get_y())
        pdf.ln(2.5)
    else:
        pdf.ln(1)


def paragraph(pdf: Paper, text: str, *, size: float = BODY, indent: float = 0) -> None:
    pdf.set_font("serif", "", size)
    pdf.set_text_color(*INK)
    pdf.set_x(MARGIN + indent)
    pdf.multi_cell(0, size * 0.52, inline(text), markdown=True, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1.8)


def table(pdf: Paper, rows: list[list[str]]) -> None:
    pdf.set_font("serif", "", 8)
    pdf.set_text_color(*INK)
    pdf.ln(1)
    with pdf.table(
        first_row_as_headings=True, line_height=4.2, text_align="LEFT", borders_layout="HORIZONTAL_LINES",
        cell_fill_color=(244, 242, 236), cell_fill_mode="ROWS" if False else "NONE",
    ) as t:  # fmt: skip
        for r in rows:
            row = t.row()
            for cell in r:
                row.cell(inline(cell).replace("**", ""))
    pdf.ln(3)


def figure(pdf: Paper, base: Path | None, src: str, alt: str) -> None:
    path = (base / src) if base and not re.match(r"^(https?:|/)", src) else None
    if path and path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        width = pdf.w - 2 * MARGIN
        pdf.ln(1)
        if pdf.get_y() > pdf.h - 100:
            pdf.add_page()
        pdf.image(str(path), x=MARGIN, w=width)
        pdf.ln(2)
    elif alt:
        paragraph(pdf, f"[Figure not available: {alt}]", size=9)


def render_markdown(pdf: Paper, md: str, base: Path | None) -> None:
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        h = re.match(r"^(#{1,4})\s+(.*)$", line)
        if h:
            heading(pdf, h.group(2), min(len(h.group(1)) + 1, 4))
            i += 1
            continue
        img = IMAGE.match(line.strip())
        if img:
            figure(pdf, base, img.group(2), img.group(1))
            i += 1
            continue
        if re.match(r"^\s*\|.*\|\s*$", line):
            rows = []
            while i < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[i]):
                rows.append(lines[i])
                i += 1
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            cells = [r for r in cells if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
            width = max(len(r) for r in cells)
            table(pdf, [r + [""] * (width - len(r)) for r in cells])
            continue
        if re.match(r"^\s*[-*]\s+", line):
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                paragraph(pdf, "•  " + re.sub(r"^\s*[-*]\s+", "", lines[i]), indent=4)
                i += 1
            continue
        if REF_LINE.match(line):
            while i < len(lines) and REF_LINE.match(lines[i]):
                paragraph(pdf, lines[i], size=9, indent=0)  # one reference per line, as in the review's own list
                i += 1
            continue
        para = []
        while (
            i < len(lines)
            and lines[i].strip()
            and not re.match(r"^(#{1,4}\s|\s*\||\s*[-*]\s|!\[)", lines[i])
            and not REF_LINE.match(lines[i])
        ):
            para.append(lines[i].strip())
            i += 1
        paragraph(pdf, " ".join(para))


def render_pdf(paper: dict, meta: dict, base: Path | None = None) -> bytes:
    """`paper`: the reader's data (markdown, claims, sources, audit, audit_markdown). `meta`: title, question, kind, date,
    spent_usd, cap_usd, run_id."""
    pdf = Paper(footer_text=f"VERA · {meta.get('run_id', '')} · generated {meta.get('date', '')}")
    pdf.add_page()
    pdf.set_font("sans", "B", 7.5)
    pdf.set_text_color(*MUTED)
    kind = "LITERATURE REVIEW" if meta.get("kind", "literature") == "literature" else "RESEARCH PAPER"
    pdf.cell(0, 5, f"VERA  ·  {kind}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font("serif", "B", 17)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 8, meta.get("title", "Untitled"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    audit = (paper.get("audit") or {}).get("overall")
    pdf.set_font("sans", "", 8)
    pdf.set_text_color(*MUTED)
    facts = [meta.get("date", "")]
    if meta.get("spent_usd") is not None:
        facts.append(
            f"model cost ${meta['spent_usd']:.2f}"
            + (f" of a ${meta['cap_usd']:.2f} cap" if meta.get("cap_usd") else "")
        )
    lead = "  ·  ".join(f for f in facts if f) + "  ·  audit: "
    pdf.cell(pdf.get_string_width(lead) + 1, 5, lead, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font("sans", "B", 8)
    pdf.set_text_color(*LIGHTS.get(audit, MUTED))
    pdf.cell(0, 5, (audit or "not audited").upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if meta.get("question"):
        pdf.ln(3)
        pdf.set_font("serif", "I", 10)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(0, 5.2, "Research question: " + meta["question"], align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*RULE)
    pdf.ln(2)
    pdf.line(MARGIN, pdf.get_y(), pdf.w - MARGIN, pdf.get_y())
    pdf.ln(2)

    render_markdown(pdf, paper.get("markdown", ""), base)

    # Appendix A: the audit, in words
    pdf.add_page()
    heading(pdf, "Appendix A. The audit", 2)
    report = paper.get("audit") or {}
    paragraph(pdf, LIGHT_WORDS.get(audit, "This document was not audited."))
    if report.get("checks_run"):
        paragraph(
            pdf,
            "Checks run: "
            + ", ".join(report["checks_run"])
            + ". A green result means the citations are real and each claim is supported by the passage it quotes. It does not mean the review is complete or its conclusions are right.",
            size=9.5,
        )
    findings = report.get("findings") or []
    if findings:
        for f in findings:
            paragraph(pdf, f"•  [{f.get('severity', '')}] {f.get('summary', '')}", size=9.5, indent=4)
    else:
        paragraph(pdf, "No findings.", size=9.5)

    # Appendix B: every claim with its quote
    claims = paper.get("claims") or []
    if claims:
        heading(pdf, "Appendix B. Claims and the passages that support them", 2)
        paragraph(
            pdf,
            "Each cited sentence of the review, the source it rests on, where in that source the passage is, and the exact quote the audit checked it against.",
            size=9.5,
        )
        for n, c in enumerate(claims, start=1):
            if pdf.get_y() > pdf.h - 45:
                pdf.add_page()
            pdf.set_font("serif", "B", 9.5)
            pdf.set_text_color(*INK)
            pdf.multi_cell(
                0, 5, f"{n}.  [{c.get('source_key', '?')}]  {c.get('claim', '')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT
            )
            pdf.set_font("serif", "I", 9)
            pdf.set_text_color(*MUTED)
            pdf.set_x(MARGIN + 6)
            where = f"  ({c['locator']})" if c.get("locator") else ""
            pdf.multi_cell(0, 4.6, f"“{c.get('quote', '')}”{where}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)
    return bytes(pdf.output())
