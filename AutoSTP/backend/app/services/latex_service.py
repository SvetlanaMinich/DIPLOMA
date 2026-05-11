"""LaTeX generation, XeLaTeX compilation, and Pandoc DOCX conversion."""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.document_content import (
    BibliographicReference,
    DocumentImage,
    DocumentTable,
    Section,
    TextElement,
)
from app.schemas.template import (
    FontConfig,
    HeaderLevelConfig,
    HeadersConfig,
    PageConfig,
    TemplateConfiguration,
)

logger = logging.getLogger(__name__)

_UNNUMBERED_ROLES = {
    "title_page",
    "abstract",
    "task",
    "contents",
    "abbreviations",
    "introduction",
    "conclusion",
    "references",
    "appendices",
    "document_list",
    "safety_ecology",
    "tech_economy",
}

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "latex"


def _escape_latex(text: str) -> str:
    if not text:
        return ""
    out: list[str] = []
    for ch in text:
        match ch:
            case "\\":
                out.append(r"\textbackslash{}")
            case "{":
                out.append(r"\{")
            case "}":
                out.append(r"\}")
            case "$":
                out.append(r"\$")
            case "&":
                out.append(r"\&")
            case "#":
                out.append(r"\#")
            case "^":
                out.append(r"\textasciicircum{}")
            case "_":
                out.append(r"\_")
            case "~":
                out.append(r"\textasciitilde{}")
            case "%":
                out.append(r"\%")
            case _:
                out.append(ch)
    return "".join(out)


def _jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(default=False),
        keep_trailing_newline=True,
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<#",
        comment_end_string="#>",
    )
    env.filters["escape_latex"] = _escape_latex
    return env


def _build_section_context(
    section: Section,
    section_number: int | None,
    cfg: TemplateConfiguration,
) -> dict[str, Any]:
    fonts = cfg.fonts or FontConfig()
    headers = cfg.headers or HeadersConfig()

    is_unnumbered = section.section_type in _UNNUMBERED_ROLES
    level = section.level or 1

    title = section.title or ""
    if not is_unnumbered and section_number is not None:
        if title and not title[:3].replace(".", "").replace(" ", "").isdigit():
            title = f"{section_number} {title}"

    _LEADING_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+")
    display_title = title
    if not is_unnumbered:
        m = _LEADING_NUM_RE.match(display_title)
        if m:
            display_title = display_title[m.end():]

    paragraphs: list[dict[str, Any]] = []
    for te in sorted(section.text_elements, key=lambda e: e.order_number):
        content = (te.content or "").strip()
        if not content:
            continue
        paragraphs.append({"text": _escape_latex(content), "is_list": False, "is_table": False, "is_image": False})

    for tbl in sorted(section.tables, key=lambda t: t.order_number):
        rows: list[list[str]] = []
        cells_sorted = sorted(tbl.cells, key=lambda c: (c.row_index, c.column_index))
        current_row = -1
        row_data: list[str] = []
        for cell in cells_sorted:
            if cell.row_index != current_row:
                if row_data:
                    rows.append(row_data)
                row_data = []
                current_row = cell.row_index
            row_data.append(_escape_latex(cell.content or ""))
        if row_data:
            rows.append(row_data)

        col_count = tbl.columns_number or (len(rows[0]) if rows else 1)
        paragraphs.append(
            {
                "is_table": True,
                "is_list": False,
                "is_image": False,
                "table_caption": _escape_latex(tbl.caption) if tbl.caption else None,
                "table_columns": list(range(col_count)),
                "table_rows": rows,
            }
        )

    for img in sorted(section.images, key=lambda i: i.order_number):
        paragraphs.append(
            {
                "is_image": True,
                "is_list": False,
                "is_table": False,
                "image_path": "",
                "image_caption": _escape_latex(img.caption) if img.caption else None,
            }
        )

    lvl = headers.level_1 or HeaderLevelConfig()
    new_page = lvl.new_page if lvl.new_page is not None else True

    return {
        "title_escaped": _escape_latex(display_title),
        "is_unnumbered": is_unnumbered,
        "add_to_toc": True,
        "level": level,
        "new_page": new_page,
        "paragraphs": paragraphs,
    }


def _build_references_context(
    references: list[BibliographicReference],
    cfg: TemplateConfiguration,
) -> tuple[list[dict[str, Any]], str]:
    bib = cfg.bibliography
    title = "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"
    if bib and bib.title:
        title = bib.title
    if bib and bib.title_uppercase:
        title = title.upper()

    refs: list[dict[str, Any]] = []
    for ref in sorted(references, key=lambda r: r.order_number):
        parts: list[str] = []
        if ref.authors:
            parts.append(_escape_latex(ref.authors))
        if ref.source_title:
            parts.append(_escape_latex(ref.source_title))
        if ref.source_type:
            parts.append(f"// {_escape_latex(ref.source_type)}")
        if ref.source_link:
            parts.append(f"URL: {_escape_latex(ref.source_link)}")
        refs.append({"text": " ".join(parts) if parts else _escape_latex(str(ref.id))})

    return refs, _escape_latex(title)


def build_template_context(
    sections: list[Section],
    cfg: TemplateConfiguration,
    references: list[BibliographicReference] | None = None,
    document_title: str = "",
) -> dict[str, Any]:
    page = cfg.page or PageConfig()
    fonts = cfg.fonts or FontConfig()
    headers = cfg.headers or HeadersConfig()
    toc = cfg.table_of_contents

    main_size = fonts.main_size_pt or 14.0
    line_height = fonts.line_height_pt or 18.0
    line_spread = round(line_height / main_size, 4)

    lvl1 = headers.level_1 or HeaderLevelConfig()
    lvl2 = headers.level_2 or HeaderLevelConfig()
    lvl3 = headers.level_3 or HeaderLevelConfig()

    heading_size = lvl1.font_size_pt or fonts.main_size_pt or 14.0
    heading2_size = lvl2.font_size_pt or fonts.main_size_pt or 14.0
    heading3_size = lvl3.font_size_pt or fonts.main_size_pt or 14.0

    sections_ctx: list[dict[str, Any]] = []
    numbered_count = 0
    for section in sorted(sections, key=lambda s: s.order_number):
        is_numbered = section.section_type not in _UNNUMBERED_ROLES
        num = None
        if is_numbered:
            numbered_count += 1
            num = numbered_count
        sections_ctx.append(_build_section_context(section, num, cfg))

    refs_ctx: list[dict[str, Any]] = []
    refs_title = "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"
    if references:
        refs_ctx, refs_title = _build_references_context(references, cfg)

    lists_cfg = cfg.lists

    return {
        "font_family": fonts.main_family or "Times New Roman",
        "font_size_pt": int(main_size),
        "margin_left_mm": page.margin_left_mm or 30.0,
        "margin_right_mm": page.margin_right_mm or 15.0,
        "margin_top_mm": page.margin_top_mm or 20.0,
        "margin_bottom_mm": page.margin_bottom_mm or 20.0,
        "line_spread": line_spread,
        "paragraph_indent_mm": fonts.paragraph_indent_mm or 12.5,
        "text_alignment": fonts.text_alignment or "justify",
        "page_number_pos": page.page_number_pos or "bottom_right",
        "no_page_number_sections": page.pages_counted_not_numbered or [],
        "heading_font_size_pt": int(heading_size),
        "heading2_font_size_pt": int(heading2_size),
        "heading3_font_size_pt": int(heading3_size),
        "numbered_heading_bold": lvl1.bold if lvl1.bold is not None else True,
        "unnumbered_heading_bold": lvl1.bold if lvl1.bold is not None else True,
        "unnumbered_uppercase": lvl1.uppercase if lvl1.uppercase is not None else True,
        "heading_level2_defined": True,
        "heading_level3_defined": True,
        "toc_title": _escape_latex(toc.title) if toc and toc.title else "СОДЕРЖАНИЕ",
        "simple_list_marker": lists_cfg.simple.marker if lists_cfg and lists_cfg.simple else "–",
        "numbered_list_format": "arabic" if not lists_cfg or not lists_cfg.complex_numbered else "arabic",
        "image_alignment": "center",
        "bibliography_enabled": False,
        "pdf_title": _escape_latex(document_title or "Document"),
        "sections": sections_ctx,
        "references": refs_ctx if refs_ctx else None,
        "references_title": refs_title,
    }


def render_latex(context: dict[str, Any]) -> str:
    env = _jinja_env()
    template = env.get_template("stp_template.tex.j2")
    return template.render(**context)


def _find_xelatex() -> str | None:
    return shutil.which("xelatex")


def _find_pandoc() -> str | None:
    return shutil.which("pandoc")


def compile_latex_to_pdf(tex_source: str, output_dir: Path | None = None) -> bytes:
    xelatex = _find_xelatex()
    if xelatex is None:
        raise RuntimeError("xelatex not found. Install texlive-xetex.")

    tmp_dir = None
    if output_dir is None:
        tmp_dir = tempfile.mkdtemp(prefix="autostp_latex_")
        output_dir = Path(tmp_dir)

    try:
        tex_path = output_dir / "document.tex"
        pdf_path = output_dir / "document.pdf"
        tex_path.write_text(tex_source, encoding="utf-8")

        for pass_num in range(1, 3):
            result = subprocess.run(
                [
                    xelatex,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    f"-output-directory={output_dir}",
                    str(tex_path),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(output_dir),
            )
            if result.returncode != 0:
                log_path = output_dir / "document.log"
                log_content = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else result.stderr
                logger.error("XeLaTeX pass %d failed:\n%s", pass_num, log_content[-3000:])
                raise RuntimeError(f"XeLaTeX compilation failed (pass {pass_num})")

        if not pdf_path.exists():
            raise RuntimeError("PDF was not produced by XeLaTeX")

        return pdf_path.read_bytes()
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def convert_latex_to_docx(tex_source: str, output_dir: Path | None = None) -> bytes:
    pandoc = _find_pandoc()
    if pandoc is None:
        raise RuntimeError("pandoc not found. Install pandoc.")

    tmp_dir = None
    if output_dir is None:
        tmp_dir = tempfile.mkdtemp(prefix="autostp_pandoc_")
        output_dir = Path(tmp_dir)

    try:
        tex_path = output_dir / "document.tex"
        docx_path = output_dir / "document.docx"
        tex_path.write_text(tex_source, encoding="utf-8")

        result = subprocess.run(
            [
                pandoc,
                "-f", "latex",
                "-t", "docx",
                "-o", str(docx_path),
                str(tex_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error("Pandoc conversion failed: %s", result.stderr)
            raise RuntimeError(f"Pandoc conversion failed: {result.stderr}")

        if not docx_path.exists():
            raise RuntimeError("DOCX was not produced by Pandoc")

        return docx_path.read_bytes()
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
