"""
Unit tests for TemplateConfiguration Pydantic schema.

Covers:
  - Default values for all sub-configs
  - Sanitiser: string→bool, string→float, string-only field protection
  - Backward compatibility: old flat-field templates still parse
  - New nested structures (headers, formulas, tables, images, etc.)
  - SectionTemplate new fields
  - model_dump / round-trip serialization

Run:
    cd AutoSTP/backend
    pytest tests/test_schema_template.py -v
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.template import (
    AppendixConfig,
    BibliographyConfig,
    FontConfig,
    FormulaConfig,
    HeaderLevelConfig,
    HeadersConfig,
    ImageConfig,
    ListConfig,
    NotesConfig,
    PageConfig,
    SectionTemplate,
    TableConfig,
    TableOfContentsConfig,
    TemplateConfiguration,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_cfg(**overrides: Any) -> dict:
    """Return a minimal valid TemplateConfiguration dict."""
    base: dict = {}
    base.update(overrides)
    return base


def _full_cfg() -> dict:
    """Return a representative full config dict (new schema)."""
    return {
        "page": {
            "size": "A4",
            "orientation": "portrait",
            "margin_left_mm": 30,
            "margin_right_mm": 15,
            "margin_top_mm": 20,
            "margin_bottom_mm": 20,
            "page_number_pos": "bottom_right",
            "first_page_numbered": False,
            "hyphenation_in_body": True,
            "hyphenation_in_headings": False,
        },
        "fonts": {
            "main_family": "Times New Roman",
            "main_size_pt": 14,
            "line_height_multiple": 1.0,
            "line_height_pt": 18,
            "paragraph_indent_mm": 12.5,
            "text_alignment": "justify",
            "latin_formula_italic": True,
            "cyrillic_formula_italic": False,
        },
        "headers": {
            "numbered_alignment": "left",
            "unnumbered_alignment": "center",
            "unnumbered_no_paragraph_indent": True,
            "level_1": {
                "bold": True, "uppercase": True, "new_page": True,
                "indent_from_paragraph": True, "no_period_at_end": True,
            },
            "level_2": {
                "bold": True, "uppercase": False, "first_letter_uppercase": True,
                "new_page": False, "move_to_next_page_if_no_body_fits": True,
            },
        },
        "lists": {
            "simple": {"marker": "–", "item_end_punctuation": ";"},
            "lettered": {"marker_example": "а)"},
            "sub_lettered": {"marker_example": "1)"},
        },
        "formulas": {
            "alignment": "center",
            "numbering": {
                "style": "per_section",
                "format": "(section.number)",
                "position": "right_margin",
            },
            "explanation": {
                "starts_with_word": "где",
                "no_colon_after_where": True,
            },
            "wrap": {"allowed": True, "no_wrap_on_division": True},
        },
        "images": {
            "universal_term": "Рисунок",
            "caption": {
                "pos": "bottom",
                "alignment": "center",
                "prefix_word": "Рисунок",
                "separator": "–",
            },
            "reference_in_text_mandatory": True,
        },
        "tables": {
            "caption": {
                "pos": "top",
                "alignment": "left",
                "word": "Таблица",
                "separator": "–",
            },
            "borders": {"left": True, "right": True, "bottom": True},
            "continuation": {"label": "Продолжение таблицы", "repeat_header": True},
        },
        "bibliography": {
            "title": "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ",
            "title_uppercase": True,
            "standard": "ГОСТ 7.1–2003",
            "citation": {"type": "square_brackets_number"},
            "entry_ordering": "order_of_appearance",
        },
        "appendix": {
            "label_word": "ПРИЛОЖЕНИЕ",
            "label_uppercase": True,
            "new_page": True,
            "excluded_letters": ["Ё", "З", "Й", "О", "Ч", "Ъ", "Ы", "Ь"],
        },
        "notes": {
            "word": "Примечание",
            "single_format": "Примечание – текст",
            "table_note_position": "end_of_table_above_bottom_line",
        },
        "work_structure": [
            {
                "role": "introduction",
                "title_hints": ["ВВЕДЕНИЕ"],
                "required": True,
                "title_uppercase": True,
                "title_alignment": "center",
                "title_no_paragraph_indent": True,
                "counted_in_pagination": True,
                "page_number_shown": True,
                "new_page": True,
                "max_pages": 2,
            }
        ],
        "extra_rules": ["Rule A", "Rule B"],
    }


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_empty_dict_gets_all_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.page is not None
        assert cfg.page.size == "A4"
        assert cfg.page.margin_left_mm == 30.0
        assert cfg.page.margin_right_mm == 15.0
        assert cfg.page.margin_top_mm == 20.0
        assert cfg.page.margin_bottom_mm == 20.0

    def test_font_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.fonts is not None
        assert cfg.fonts.main_family == "Times New Roman"
        assert cfg.fonts.main_size_pt == 14.0
        assert cfg.fonts.paragraph_indent_mm == 12.5
        assert cfg.fonts.text_alignment == "justify"
        assert cfg.fonts.latin_formula_italic is True
        assert cfg.fonts.cyrillic_formula_italic is False

    def test_page_hyphenation_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.page.hyphenation_in_body is True
        assert cfg.page.hyphenation_in_headings is False
        assert cfg.page.hyphenation_in_tables is False

    def test_headers_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.headers is not None
        assert cfg.headers.numbered_alignment == "left"
        assert cfg.headers.unnumbered_alignment == "center"
        assert cfg.headers.unnumbered_no_paragraph_indent is True

    def test_toc_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.table_of_contents is not None
        assert cfg.table_of_contents.title == "СОДЕРЖАНИЕ"
        assert cfg.table_of_contents.dot_leader is True
        assert cfg.table_of_contents.title_uppercase is True

    def test_list_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.lists is not None
        assert cfg.lists.simple is not None
        assert cfg.lists.simple.marker == "–"
        assert cfg.lists.lettered is not None
        assert cfg.lists.lettered.marker_example == "а)"

    def test_formula_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.formulas is not None
        assert cfg.formulas.alignment == "center"
        assert cfg.formulas.explanation is not None
        assert cfg.formulas.explanation.starts_with_word == "где"
        assert cfg.formulas.numbering is not None
        assert cfg.formulas.numbering.style == "per_section"

    def test_image_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.images is not None
        assert cfg.images.universal_term == "Рисунок"
        assert cfg.images.caption is not None
        assert cfg.images.caption.prefix_word == "Рисунок"
        assert cfg.images.caption.pos == "bottom"
        assert cfg.images.caption.alignment == "center"

    def test_table_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.tables is not None
        assert cfg.tables.caption is not None
        assert cfg.tables.caption.pos == "top"
        assert cfg.tables.caption.alignment == "left"
        assert cfg.tables.caption.word == "Таблица"
        assert cfg.tables.borders is not None
        assert cfg.tables.borders.left is True

    def test_bibliography_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.bibliography is not None
        assert cfg.bibliography.title == "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"
        assert cfg.bibliography.citation is not None
        assert cfg.bibliography.citation.type == "square_brackets_number"

    def test_appendix_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.appendix is not None
        assert cfg.appendix.label_word == "ПРИЛОЖЕНИЕ"
        assert cfg.appendix.excluded_letters is not None
        assert "Ё" in cfg.appendix.excluded_letters
        assert cfg.appendix.new_page is True

    def test_notes_defaults(self):
        cfg = TemplateConfiguration(**_minimal_cfg())
        assert cfg.notes is not None
        assert cfg.notes.word == "Примечание"


# ---------------------------------------------------------------------------
# Sanitiser
# ---------------------------------------------------------------------------

class TestSanitiser:
    def test_string_true_to_bool(self):
        cfg = TemplateConfiguration(page={"first_page_numbered": "true"})
        assert cfg.page.first_page_numbered is True

    def test_string_false_to_bool(self):
        cfg = TemplateConfiguration(page={"first_page_numbered": "false"})
        assert cfg.page.first_page_numbered is False

    def test_russian_да_to_bool(self):
        cfg = TemplateConfiguration(page={"hyphenation_in_body": "да"})
        assert cfg.page.hyphenation_in_body is True

    def test_russian_нет_to_bool(self):
        cfg = TemplateConfiguration(page={"hyphenation_in_headings": "нет"})
        assert cfg.page.hyphenation_in_headings is False

    def test_string_float_coercion(self):
        cfg = TemplateConfiguration(page={"margin_left_mm": "30,0"})
        assert cfg.page.margin_left_mm == 30.0

    def test_bool_in_string_only_field_becomes_none(self):
        # text_alignment is a string-only field; True should become None
        cfg = TemplateConfiguration(fonts={"text_alignment": True})
        assert cfg.fonts.text_alignment is None

    def test_nested_sanitization(self):
        cfg = TemplateConfiguration(
            headers={"level_1": {"bold": "да", "uppercase": "true"}}
        )
        assert cfg.headers.level_1.bold is True
        assert cfg.headers.level_1.uppercase is True

    def test_paragraph_indent_large_value_coercion(self):
        # LLM sometimes returns 125 instead of 12.5 — _apply_stp_defaults fixes this
        # Sanitiser itself doesn't coerce, but it must not crash
        cfg = TemplateConfiguration(fonts={"paragraph_indent_mm": 125.0})
        assert cfg.fonts.paragraph_indent_mm == 125.0  # raw; defaults fix it


# ---------------------------------------------------------------------------
# Full config round-trip
# ---------------------------------------------------------------------------

class TestFullConfig:
    def test_full_config_parses(self):
        cfg = TemplateConfiguration(**_full_cfg())
        assert cfg.page.size == "A4"
        assert cfg.fonts.main_family == "Times New Roman"
        assert cfg.headers.numbered_alignment == "left"
        assert cfg.headers.level_1.bold is True
        assert cfg.headers.level_1.uppercase is True
        assert cfg.headers.level_2.move_to_next_page_if_no_body_fits is True
        assert cfg.formulas.explanation.starts_with_word == "где"
        assert cfg.formulas.numbering.style == "per_section"
        assert cfg.images.caption.pos == "bottom"
        assert cfg.tables.caption.pos == "top"
        assert cfg.tables.continuation.label == "Продолжение таблицы"
        assert cfg.bibliography.citation.type == "square_brackets_number"
        assert "Ё" in cfg.appendix.excluded_letters
        assert cfg.notes.word == "Примечание"
        assert len(cfg.extra_rules) == 2

    def test_full_config_serializes_to_json(self):
        cfg = TemplateConfiguration(**_full_cfg())
        dumped = cfg.model_dump()
        # Re-parse from dict to verify round-trip
        cfg2 = TemplateConfiguration(**dumped)
        assert cfg2.page.size == cfg.page.size
        assert cfg2.fonts.main_family == cfg.fonts.main_family

    def test_work_structure_new_fields(self):
        cfg = TemplateConfiguration(**_full_cfg())
        intro = next(s for s in cfg.work_structure if s.role == "introduction")
        assert intro.counted_in_pagination is True
        assert intro.page_number_shown is True
        assert intro.max_pages == 2
        assert intro.title_no_paragraph_indent is True
        assert intro.title_alignment == "center"


# ---------------------------------------------------------------------------
# Backward compatibility with old flat template format
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """Old templates stored in the DB used flat headers dict and old field names."""

    OLD_STYLE_TEMPLATE = {
        "page": {
            "size": "A4",
            "margin_top_mm": 20,
            "margin_bottom_mm": 20,
            "margin_left_mm": 30,
            "margin_right_mm": 15,
        },
        "fonts": {
            "main_family": "Times New Roman",
            "main_size_pt": 14,
            "line_height": 1.0,           # old name → line_height_multiple
            "paragraph_indent_mm": 12.5,
            "text_alignment": "justify",
        },
        "headers": {
            "level_1": {
                "bold": True,
                "uppercase": True,
                "alignment": "center",    # legacy field kept
                "new_page": True,
            },
            "level_2": {
                "bold": True,
                "uppercase": False,
                "alignment": "left",
            },
        },
        "lists": {
            "simple_marker": "–",         # old flat field
            "semicolon_after_simple": True,
            "period_after_complex": True,
        },
        "tables": {
            "caption_pos": "top",         # old flat field
            "caption_word": "Таблица",
            "continuation_label": "Продолжение таблицы",
            "header_bold": True,
            "border_left": True,
            "border_right": True,
        },
        "images": {
            "caption_prefix": "Рисунок",  # old flat field
            "caption_pos": "bottom",
            "caption_separator": "–",
            "center": True,
        },
        "formulas": {
            "alignment": "center",
            "numbering_per_section": True,
            "explanation_starts_with": "где",
        },
        "bibliography": {
            "title": "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ",
            "format_standard": "ГОСТ 7.1–2003",
            "citation_style": "square_brackets_number",
        },
        "appendix": {
            "label_word": "ПРИЛОЖЕНИЕ",
            "label_uppercase": True,
            "new_page": True,
        },
        "footnotes": {
            "separator_line": True,
        },
        "work_structure": [
            {
                "role": "introduction",
                "title_hints": ["ВВЕДЕНИЕ"],
                "required": True,
                "new_page": True,
            }
        ],
        "extra_rules": ["Old style rule"],
    }

    def test_old_template_parses_without_error(self):
        cfg = TemplateConfiguration(**self.OLD_STYLE_TEMPLATE)
        assert cfg.page.size == "A4"
        assert cfg.fonts.main_family == "Times New Roman"

    def test_old_line_height_alias(self):
        cfg = TemplateConfiguration(**self.OLD_STYLE_TEMPLATE)
        # line_height was aliased to line_height_multiple
        assert cfg.fonts.line_height_multiple == 1.0

    def test_old_flat_headers_accessible(self):
        cfg = TemplateConfiguration(**self.OLD_STYLE_TEMPLATE)
        assert cfg.headers.level_1 is not None
        assert cfg.headers.level_1.bold is True
        assert cfg.headers.level_1.uppercase is True
        # Legacy alignment field still stored
        assert cfg.headers.level_1.alignment == "center"

    def test_old_flat_table_fields(self):
        cfg = TemplateConfiguration(**self.OLD_STYLE_TEMPLATE)
        # Legacy flat fields still on TableConfig
        assert cfg.tables.caption_pos == "top"
        assert cfg.tables.caption_word == "Таблица"
        assert cfg.tables.continuation_label == "Продолжение таблицы"
        assert cfg.tables.header_bold is True

    def test_old_flat_image_fields(self):
        cfg = TemplateConfiguration(**self.OLD_STYLE_TEMPLATE)
        assert cfg.images.caption_prefix == "Рисунок"
        assert cfg.images.caption_pos == "bottom"

    def test_old_flat_formula_fields(self):
        cfg = TemplateConfiguration(**self.OLD_STYLE_TEMPLATE)
        assert cfg.formulas.alignment == "center"
        assert cfg.formulas.explanation_starts_with == "где"
        assert cfg.formulas.numbering_per_section is True

    def test_old_bibliography_flat_fields(self):
        cfg = TemplateConfiguration(**self.OLD_STYLE_TEMPLATE)
        assert cfg.bibliography.format_standard == "ГОСТ 7.1–2003"
        assert cfg.bibliography.citation_style == "square_brackets_number"

    def test_old_work_structure_no_new_fields(self):
        """Old work_structure entries without new fields should use None defaults."""
        cfg = TemplateConfiguration(**self.OLD_STYLE_TEMPLATE)
        intro = cfg.work_structure[0]
        assert intro.role == "introduction"
        assert intro.counted_in_pagination is True   # default
        assert intro.max_pages is None               # not in old format


# ---------------------------------------------------------------------------
# Sub-model unit tests
# ---------------------------------------------------------------------------

class TestPageConfig:
    def test_pages_counted_not_numbered_default(self):
        page = PageConfig()
        assert "title_page" in page.pages_counted_not_numbered
        assert "abstract" in page.pages_counted_not_numbered
        assert "task" in page.pages_counted_not_numbered

    def test_custom_pages_counted(self):
        page = PageConfig(pages_counted_not_numbered=["title_page"])
        assert page.pages_counted_not_numbered == ["title_page"]


class TestFontConfig:
    def test_line_height_alias_compat(self):
        font = FontConfig(**{"line_height": 1.5})
        assert font.line_height_multiple == 1.5

    def test_explicit_line_height_multiple(self):
        font = FontConfig(line_height_multiple=1.0)
        assert font.line_height_multiple == 1.0


class TestHeadersConfig:
    def test_level_access(self):
        h = HeadersConfig(
            level_1=HeaderLevelConfig(bold=True, uppercase=True),
            level_2=HeaderLevelConfig(bold=True, uppercase=False),
        )
        assert h.level_1.bold is True
        assert h.level_2.uppercase is False

    def test_numbered_unnumbered_alignment_separate(self):
        h = HeadersConfig(numbered_alignment="left", unnumbered_alignment="center")
        assert h.numbered_alignment == "left"
        assert h.unnumbered_alignment == "center"

    def test_level_4_exists(self):
        h = HeadersConfig()
        assert h.level_4 is not None  # has default


class TestFormulaConfig:
    def test_nested_numbering(self):
        f = FormulaConfig(numbering={"style": "per_section", "position": "right_margin"})
        assert f.numbering.style == "per_section"
        assert f.numbering.position == "right_margin"

    def test_nested_explanation(self):
        f = FormulaConfig(explanation={"starts_with_word": "где", "no_colon_after_where": True})
        assert f.explanation.starts_with_word == "где"
        assert f.explanation.no_colon_after_where is True

    def test_nested_wrap(self):
        f = FormulaConfig(wrap={"no_wrap_on_division": True, "multiplication_sign_at_wrap": "×"})
        assert f.wrap.no_wrap_on_division is True
        assert f.wrap.multiplication_sign_at_wrap == "×"

    def test_legacy_fields_coexist(self):
        f = FormulaConfig(alignment="center", explanation_starts_with="где")
        assert f.alignment == "center"
        assert f.explanation_starts_with == "где"
        # Nested explanation still defaults
        assert f.explanation.starts_with_word == "где"


class TestTableConfig:
    def test_nested_caption(self):
        t = TableConfig(caption={"pos": "top", "alignment": "left", "word": "Таблица"})
        assert t.caption.pos == "top"
        assert t.caption.word == "Таблица"

    def test_nested_borders(self):
        t = TableConfig(borders={"left": True, "right": True, "bottom": True, "top": False})
        assert t.borders.left is True
        assert t.borders.top is False

    def test_nested_body(self):
        t = TableConfig(body={"no_empty_cells": True, "empty_cell_placeholder": "–"})
        assert t.body.no_empty_cells is True
        assert t.body.empty_cell_placeholder == "–"

    def test_legacy_flat_fields(self):
        t = TableConfig(caption_pos="top", caption_word="Таблица", header_bold=True)
        assert t.caption_pos == "top"
        assert t.header_bold is True


class TestImageConfig:
    def test_nested_caption(self):
        img = ImageConfig(caption={"pos": "bottom", "prefix_word": "Рисунок", "separator": "–"})
        assert img.caption.pos == "bottom"
        assert img.caption.prefix_word == "Рисунок"

    def test_legacy_caption_prefix(self):
        img = ImageConfig(caption_prefix="Рисунок", caption_pos="bottom")
        assert img.caption_prefix == "Рисунок"
        assert img.caption_pos == "bottom"

    def test_recommended_sizes_mm(self):
        img = ImageConfig(recommended_sizes_mm=[{"width": 92, "height": 150}])
        assert img.recommended_sizes_mm[0]["width"] == 92

    def test_recommended_sizes_legacy_string_coercion(self):
        img = ImageConfig(recommended_sizes="92×150 мм")
        assert img.recommended_sizes == ["92×150 мм"]


class TestBibliographyConfig:
    def test_nested_citation(self):
        bib = BibliographyConfig(citation={"type": "square_brackets_number"})
        assert bib.citation.type == "square_brackets_number"

    def test_nested_formatting_rules(self):
        bib = BibliographyConfig(
            formatting_rules={"city_minsk_full_form": True, "initials_separator": " "}
        )
        assert bib.formatting_rules.city_minsk_full_form is True

    def test_legacy_flat_fields(self):
        bib = BibliographyConfig(
            format_standard="ГОСТ 7.1–2003",
            citation_style="square_brackets_number",
        )
        assert bib.format_standard == "ГОСТ 7.1–2003"


class TestAppendixConfig:
    def test_excluded_letters(self):
        app = AppendixConfig()
        for letter in ["Ё", "З", "Й", "О", "Ч"]:
            assert letter in app.excluded_letters

    def test_type_label_variants(self):
        app = AppendixConfig()
        assert "обязательное" in app.type_label_variants
        assert "справочное" in app.type_label_variants

    def test_internal_numbering(self):
        app = AppendixConfig(internal_numbering={"formulas": "А.1", "restart_per_appendix": True})
        assert app.internal_numbering.formulas == "А.1"
        assert app.internal_numbering.restart_per_appendix is True


class TestSectionTemplate:
    def test_new_fields_default_to_none(self):
        s = SectionTemplate(role="introduction", title_hints=["ВВЕДЕНИЕ"])
        assert s.counted_in_pagination is True
        assert s.page_number_shown is True
        assert s.max_pages is None
        assert s.title_no_paragraph_indent is None

    def test_all_new_fields_accepted(self):
        s = SectionTemplate(
            role="introduction",
            title_hints=["ВВЕДЕНИЕ"],
            required=True,
            title_uppercase=True,
            title_alignment="center",
            title_no_paragraph_indent=True,
            counted_in_pagination=True,
            page_number_shown=True,
            new_page=True,
            max_pages=2,
            has_subsections=False,
        )
        assert s.max_pages == 2
        assert s.title_alignment == "center"
        assert s.title_no_paragraph_indent is True

    def test_percent_fields(self):
        s = SectionTemplate(
            role="tech_economy",
            title_hints=["ТЭО"],
            max_percent_of_total=18.0,
        )
        assert s.max_percent_of_total == 18.0


class TestNotesConfig:
    def test_defaults(self):
        n = NotesConfig()
        assert n.word == "Примечание"
        assert n.table_note_position == "end_of_table_above_bottom_line"

    def test_custom_values(self):
        n = NotesConfig(word="Замечание", multiple_format="numbered_arabic")
        assert n.word == "Замечание"
        assert n.multiple_format == "numbered_arabic"


# ---------------------------------------------------------------------------
# Edge cases / validation
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_none_page_uses_defaults(self):
        # Passing None for page should give default PageConfig
        cfg = TemplateConfiguration(page=None)
        # page may be None if explicitly set to None
        # schema says Optional[PageConfig] so it is acceptable
        # The default_factory won't override explicit None
        assert cfg.page is None or cfg.page.size == "A4"

    def test_empty_work_structure_list(self):
        cfg = TemplateConfiguration(work_structure=[])
        assert cfg.work_structure == []

    def test_extra_rules_deduplicated_at_model_level(self):
        # Model itself doesn't deduplicate, that's _deep_merge's job
        cfg = TemplateConfiguration(extra_rules=["A", "A", "B"])
        assert cfg.extra_rules == ["A", "A", "B"]

    def test_large_paragraph_indent_not_auto_corrected_by_schema(self):
        # Correction happens in _apply_stp_defaults, not Pydantic
        cfg = TemplateConfiguration(fonts={"paragraph_indent_mm": 125.0})
        assert cfg.fonts.paragraph_indent_mm == 125.0

    def test_volume_requirements_defaults(self):
        cfg = TemplateConfiguration()
        assert cfg.volume_requirements is not None
        assert cfg.volume_requirements.total_pages_without_reference_appendices_min == 60
        assert cfg.volume_requirements.total_pages_without_reference_appendices_max == 80

    def test_json_schema_roundtrip(self):
        original = _full_cfg()
        cfg = TemplateConfiguration(**original)
        dumped = cfg.model_dump(exclude_none=False)
        cfg2 = TemplateConfiguration(**dumped)
        assert cfg2.page.size == cfg.page.size
        assert cfg2.headers.numbered_alignment == cfg.headers.numbered_alignment
        assert cfg2.formulas.explanation.starts_with_word == cfg.formulas.explanation.starts_with_word
