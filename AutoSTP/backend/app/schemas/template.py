from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from app.models.template import TemplateType

# ---------------------------------------------------------------------------
# Sanitiser helpers
# ---------------------------------------------------------------------------

_BOOL_FIELDS = {
    "first_page_numbered", "hyphenation_in_body", "hyphenation_in_headings",
    "hyphenation_in_tables", "hyphenation_in_captions",
    "main_bold", "main_italic", "latin_formula_italic", "cyrillic_formula_italic",
    "greek_formula_italic",
    "bold", "italic", "underline", "uppercase", "first_letter_uppercase",
    "numbered", "new_page", "indent_from_paragraph", "multiline_align_to_first_char",
    "no_period_at_end", "two_sentences_separated_by_dot", "move_to_next_page_if_no_body_fits",
    "has_heading", "number_has_trailing_dot",
    "title_uppercase", "title_bold", "dot_leader",
    "include_level_1", "include_level_2", "include_level_3",
    "include_appendices", "include_references", "include_document_list",
    "unnumbered_no_paragraph_indent", "numbered_alignment_left",
    "each_item_new_line", "inline_allowed",
    "intro_phrase_must_not_end_with_preposition",
    "semicolon_after_simple", "period_after_complex",
    "placed_on_separate_line", "inline_allowed_for_short_aux",
    "no_period_after_number", "title_starts_uppercase", "reference_in_text_mandatory",
    "uniform_style_throughout", "uppercase_1_3_larger_than_lowercase",
    "no_diagonal_split_cell", "no_abbreviations", "nominative_case_singular",
    "no_period_at_header_end", "header_bold",
    "border_left", "border_right", "border_bottom", "border_top",
    "omit_bottom_if_continues", "no_empty_cells",
    "numbers_aligned_by_digit_position", "numbers_of_different_units_centered",
    "decimal_places_consistent_per_column", "no_order_number_column",
    "repeat_header", "header_replaceable_by_column_numbers",
    "split_narrow_table_side_by_side",
    "center", "separate_with_blank_line",
    "no_wrap_on_division", "no_wrap_on_root_integral_log_trig",
    "operator_repeated_at_wrap", "allowed",
    "no_colon_after_where", "from_new_line", "no_paragraph_indent",
    "symbols_aligned", "alternative_with_period_before",
    "numbering_per_section", "separated_by_blank_lines",
    "title_new_page", "label_uppercase", "separator_line",
    "required", "counted_in_pagination", "page_number_shown",
    "title_no_paragraph_indent", "has_subsections",
    "included_in_page_numbering", "reference_mandatory_in_text",
    "ordered_by_reference_order", "restart_per_appendix",
    "word_first_letter_uppercase", "text_from_paragraph_indent", "marker_repeated_below",
    "department_no_abbreviation", "faculty_no_abbreviation",
    "topic_matches_order_exactly",
    "no_foreign_terms_if_russian_exists",
    "numbers_1_to_9_without_units_as_words", "numbers_above_9_as_digits",
    "fractions_as_decimal", "ordinal_numbers_with_inflection",
    "math_signs_without_values_as_words", "range_unit_after_last_value",
    "no_dash_before_number_with_unit",
    "fraction_number_at_mid_bar", "multiline_number_at_last_line",
    "number_in_parentheses",
}

_TRUE_STRINGS = {"true", "да", "yes", "1"}
_FALSE_STRINGS = {"false", "нет", "no", "0"}

_STRING_ONLY_FIELDS = {
    "size", "orientation", "page_number_pos", "text_alignment",
    "main_family", "numbered_alignment", "unnumbered_alignment",
    "alignment", "title_alignment", "label_alignment", "caption_alignment",
    "caption_pos", "caption_prefix", "caption_separator", "caption_word",
    "numbering_style", "number_format", "number_format_continuous",
    "number_format_per_section", "appendix_format", "example",
    "marker", "marker_type", "marker_example", "indent_type",
    "item_end_punctuation", "last_item_end_punctuation", "inline_separator",
    "multipage_label",
    "continuation_label", "separator",
    "starts_with_word", "symbol_separator", "each_entry_ends_with",
    "unit_separator", "alternative_start",
    "multiplication_sign_at_wrap",
    "citation_words",
    "title", "label_word", "word",
    "format_standard", "citation_style", "ordering",
    "standard", "type", "letter_sequence_start",
    "single_format", "multiple_format",
    "marker_style", "marker_position", "text_indent",
    "placed_after", "subsection_heading_level",
    "binding", "role",
    "physical_units_standard",
    "document_code_format",
    "single_appendix_label",
    "placement",
}


def _sanitize_value(v: Any, key: str = "") -> Any:
    if isinstance(v, dict):
        return {k: _sanitize_value(val, k) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize_value(item, "") for item in v]
    if isinstance(v, bool) and key in _STRING_ONLY_FIELDS:
        return None
    if isinstance(v, str):
        low = v.strip().lower()
        if key in _BOOL_FIELDS:
            if low in _TRUE_STRINGS:
                return True
            if low in _FALSE_STRINGS:
                return False
            return None
        cleaned = v.replace(",", ".").strip()
        if cleaned.count(".") <= 1:
            no_dot = cleaned.replace(".", "").replace("-", "")
            if no_dot.isdigit():
                return float(cleaned)
    return v


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

class PageConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    size: Optional[str] = "A4"
    orientation: Optional[str] = "portrait"
    margin_left_mm: Optional[float] = 30.0
    margin_right_mm: Optional[float] = 15.0
    margin_top_mm: Optional[float] = 20.0
    margin_bottom_mm: Optional[float] = 20.0
    page_number_pos: Optional[str] = "bottom_right"
    page_number_font_size_pt: Optional[float] = None
    page_number_font_family: Optional[str] = None
    first_page_numbered: Optional[bool] = False
    pages_counted_not_numbered: Optional[List[str]] = Field(
        default_factory=lambda: ["title_page", "abstract", "task"]
    )
    hyphenation_in_body: Optional[bool] = True
    hyphenation_in_headings: Optional[bool] = False
    hyphenation_in_tables: Optional[bool] = False
    hyphenation_in_captions: Optional[bool] = False

    @field_validator("pages_counted_not_numbered", mode="before")
    @classmethod
    def _coerce_pages_list(cls, v: Any) -> Any:
        if isinstance(v, bool):
            return ["title_page", "abstract", "task"] if v else []
        return v


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

class FontConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    main_family: Optional[str] = "Times New Roman"
    main_size_pt: Optional[float] = 14.0
    main_bold: Optional[bool] = False
    main_italic: Optional[bool] = False
    line_height_multiple: Optional[float] = 1.0
    line_height_pt: Optional[float] = 18.0
    paragraph_indent_mm: Optional[float] = 12.5
    text_alignment: Optional[str] = "justify"
    latin_formula_italic: Optional[bool] = True
    cyrillic_formula_italic: Optional[bool] = False
    greek_formula_italic: Optional[bool] = False

    # Legacy alias kept for old templates stored in DB
    @model_validator(mode="before")
    @classmethod
    def _compat(cls, data: Any) -> Any:
        if isinstance(data, dict) and "line_height" in data and "line_height_multiple" not in data:
            data = dict(data)
            data["line_height_multiple"] = data.pop("line_height")
        return data


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------

class HeaderLevelConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    font_family: Optional[str] = None
    font_size_pt: Optional[float] = 14.0
    bold: Optional[bool] = None
    italic: Optional[bool] = False
    underline: Optional[bool] = False
    uppercase: Optional[bool] = None
    first_letter_uppercase: Optional[bool] = None
    numbered: Optional[bool] = None
    number_format: Optional[str] = None
    number_has_trailing_dot: Optional[bool] = False
    new_page: Optional[bool] = None
    spacing_before_lines: Optional[int] = 0
    spacing_after_lines: Optional[int] = 1
    indent_from_paragraph: Optional[bool] = None
    multiline_align_to_first_char: Optional[bool] = None
    no_period_at_end: Optional[bool] = True
    two_sentences_separated_by_dot: Optional[bool] = None
    move_to_next_page_if_no_body_fits: Optional[bool] = None
    has_heading: Optional[bool] = None

    # Legacy fields from old schema
    alignment: Optional[str] = None
    spacing_before_pt: Optional[float] = None
    spacing_after_pt: Optional[float] = None
    indent_first_line: Optional[bool] = None


class HeadersConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    numbered_alignment: Optional[str] = "left"
    unnumbered_alignment: Optional[str] = "center"
    unnumbered_no_paragraph_indent: Optional[bool] = True
    level_1: Optional[HeaderLevelConfig] = Field(default_factory=HeaderLevelConfig)
    level_2: Optional[HeaderLevelConfig] = Field(default_factory=HeaderLevelConfig)
    level_3: Optional[HeaderLevelConfig] = Field(default_factory=HeaderLevelConfig)
    level_4: Optional[HeaderLevelConfig] = Field(default_factory=HeaderLevelConfig)

    @model_validator(mode="before")
    @classmethod
    def _passthrough_dict(cls, data: Any) -> Any:
        # Old schema stored headers as {"level_1": {...}, "level_2": {...}} directly
        # New schema wraps them in HeadersConfig — both work.
        return data


# ---------------------------------------------------------------------------
# Table of Contents
# ---------------------------------------------------------------------------

class TableOfContentsConfig(BaseModel):
    title: Optional[str] = "СОДЕРЖАНИЕ"
    title_uppercase: Optional[bool] = True
    title_bold: Optional[bool] = True
    title_font_size_pt: Optional[float] = 14.0
    title_font_size_pt_max: Optional[float] = 16.0
    title_alignment: Optional[str] = "center"
    spacing_after_title_lines: Optional[int] = 1
    indent_per_level_chars: Optional[int] = 2
    indent_per_level_mm: Optional[float] = None
    dot_leader: Optional[bool] = True
    page_number_column: Optional[str] = "right"
    include_level_1: Optional[bool] = True
    include_level_2: Optional[bool] = True
    include_level_3: Optional[bool] = False
    include_appendices: Optional[bool] = True
    include_references: Optional[bool] = True
    include_document_list: Optional[bool] = True
    include_subsections: Optional[bool] = True
    placed_after: Optional[str] = "task"


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

class SimpleListConfig(BaseModel):
    marker: Optional[str] = "–"
    each_item_new_line: Optional[bool] = True
    indent_type: Optional[str] = "paragraph_indent"
    item_end_punctuation: Optional[str] = ";"
    last_item_end_punctuation: Optional[str] = "."
    inline_allowed: Optional[bool] = True
    inline_separator: Optional[str] = ","


class NumberedListConfig(BaseModel):
    marker_type: Optional[str] = "arabic_no_bracket"
    each_item_new_line: Optional[bool] = True
    indent_type: Optional[str] = "paragraph_indent"
    first_letter_uppercase: Optional[bool] = True
    item_end_punctuation: Optional[str] = "."


class LetteredListConfig(BaseModel):
    marker_type: Optional[str] = "cyrillic_lowercase_bracket"
    marker_example: Optional[str] = "а)"
    each_item_new_line: Optional[bool] = True
    indent_type: Optional[str] = "paragraph_indent"
    item_end_punctuation: Optional[str] = ";"


class SubLetteredListConfig(BaseModel):
    marker_type: Optional[str] = "arabic_bracket"
    marker_example: Optional[str] = "1)"
    each_item_new_line: Optional[bool] = True
    indent_type: Optional[str] = "paragraph_indent_level_2"
    item_end_punctuation: Optional[str] = ";"


class ListConfig(BaseModel):
    simple: Optional[SimpleListConfig] = Field(default_factory=SimpleListConfig)
    complex_numbered: Optional[NumberedListConfig] = Field(default_factory=NumberedListConfig)
    lettered: Optional[LetteredListConfig] = Field(default_factory=LetteredListConfig)
    sub_lettered: Optional[SubLetteredListConfig] = Field(default_factory=SubLetteredListConfig)
    intro_phrase_must_not_end_with_preposition: Optional[bool] = True

    # Legacy flat fields
    simple_marker: Optional[str] = None
    sub_list_marker: Optional[str] = None
    sub_sub_marker: Optional[str] = None
    indent_main_mm: Optional[float] = None
    indent_sub_mm: Optional[float] = None
    semicolon_after_simple: Optional[bool] = True
    period_after_complex: Optional[bool] = True
    complex_numbering: Optional[str] = None


# ---------------------------------------------------------------------------
# Text rules
# ---------------------------------------------------------------------------

class TextRulesConfig(BaseModel):
    numbers_1_to_9_without_units_as_words: Optional[bool] = True
    numbers_above_9_as_digits: Optional[bool] = True
    fractions_as_decimal: Optional[bool] = True
    ordinal_numbers_with_inflection: Optional[bool] = True
    math_signs_without_values_as_words: Optional[bool] = True
    range_unit_after_last_value: Optional[bool] = True
    no_dash_before_number_with_unit: Optional[bool] = True
    physical_units_standard: Optional[str] = "ГОСТ 8.417–2002"
    no_foreign_terms_if_russian_exists: Optional[bool] = True
    language_style_mandatory_words: Optional[List[str]] = Field(
        default_factory=lambda: ["должен", "следует", "необходимо", "не допускается", "запрещается"]
    )
    language_style_permissive_words: Optional[List[str]] = Field(
        default_factory=lambda: ["допускают", "указывают", "применяют"]
    )


# ---------------------------------------------------------------------------
# Formulas
# ---------------------------------------------------------------------------

class FormulaNumberingConfig(BaseModel):
    style: Optional[str] = "per_section"
    format: Optional[str] = "(section.number)"
    example: Optional[str] = "(2.7)"
    appendix_format: Optional[str] = "(AppLetter.number)"
    appendix_example: Optional[str] = "(Б.2)"
    continuous_allowed: Optional[bool] = True
    position: Optional[str] = "right_margin"
    number_in_parentheses: Optional[bool] = True
    fraction_number_at_mid_bar: Optional[bool] = True
    multiline_number_at_last_line: Optional[bool] = True


class FormulaExplanationConfig(BaseModel):
    starts_with_word: Optional[str] = "где"
    no_colon_after_where: Optional[bool] = True
    from_new_line: Optional[bool] = True
    no_paragraph_indent: Optional[bool] = True
    symbol_separator: Optional[str] = "–"
    symbols_aligned: Optional[bool] = True
    each_entry_ends_with: Optional[str] = ";"
    unit_at_end_of_entry: Optional[bool] = True
    unit_separator: Optional[str] = ","
    alternative_start: Optional[str] = "здесь"
    alternative_with_period_before: Optional[bool] = True


class FormulaWrapConfig(BaseModel):
    allowed: Optional[bool] = True
    operator_repeated_at_wrap: Optional[bool] = True
    multiplication_sign_at_wrap: Optional[str] = "×"
    no_wrap_on_division: Optional[bool] = True
    no_wrap_on_root_integral_log_trig: Optional[bool] = True


class FormulaConfig(BaseModel):
    alignment: Optional[str] = "center"
    placed_on_separate_line: Optional[bool] = True
    spacing_before_lines: Optional[int] = 1
    spacing_after_lines: Optional[int] = 1
    simple_formula_spacing_intervals: Optional[int] = 6
    complex_formula_spacing_intervals: Optional[int] = 8
    inline_allowed_for_short_aux: Optional[bool] = True
    multi_formula_per_line_separator: Optional[str] = ";"
    numbering: Optional[FormulaNumberingConfig] = Field(default_factory=FormulaNumberingConfig)
    explanation: Optional[FormulaExplanationConfig] = Field(default_factory=FormulaExplanationConfig)
    wrap: Optional[FormulaWrapConfig] = Field(default_factory=FormulaWrapConfig)

    # Legacy flat fields
    numbering_alignment: Optional[str] = None
    numbering_style: Optional[str] = None
    numbering_per_section: Optional[bool] = True
    separated_by_blank_lines: Optional[bool] = True
    explanation_starts_with: Optional[str] = "где"


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

class ImageCaptionConfig(BaseModel):
    pos: Optional[str] = "bottom"
    alignment: Optional[str] = "center"
    prefix_word: Optional[str] = "Рисунок"
    prefix_no_abbreviation: Optional[bool] = True
    separator: Optional[str] = "–"
    numbering_style: Optional[str] = "continuous"
    number_format_continuous: Optional[str] = "Рисунок N"
    number_format_per_section: Optional[str] = "Рисунок N.M"
    appendix_format: Optional[str] = "Рисунок А.2"
    no_period_after_number: Optional[bool] = True
    title_starts_uppercase: Optional[bool] = True
    no_period_at_end: Optional[bool] = True
    example: Optional[str] = "Рисунок 2.1 – Структурная схема"
    multipage_label: Optional[str] = "лист N"


class ImageInlineExplanationConfig(BaseModel):
    position: Optional[str] = "between_image_and_caption"
    separator: Optional[str] = ";"
    no_decode_if_explained_in_text: Optional[bool] = True


class ImageConfig(BaseModel):
    universal_term: Optional[str] = "Рисунок"
    alignment: Optional[str] = "center"
    spacing_before_lines: Optional[int] = 1
    spacing_after_caption_lines: Optional[int] = 1
    recommended_sizes_mm: Optional[List[Dict[str, float]]] = Field(
        default_factory=lambda: [{"width": 92, "height": 150}, {"width": 150, "height": 240}]
    )
    placed_after_first_reference_paragraph: Optional[bool] = True
    multiple_per_page_allowed: Optional[bool] = True
    orientation_max_rotation_deg: Optional[int] = 90
    caption: Optional[ImageCaptionConfig] = Field(default_factory=ImageCaptionConfig)
    inline_explanations: Optional[ImageInlineExplanationConfig] = Field(
        default_factory=ImageInlineExplanationConfig
    )
    inscription_min_height_mm: Optional[float] = 2.5
    uppercase_1_3_larger_than_lowercase: Optional[bool] = True
    reference_in_text_mandatory: Optional[bool] = True
    uniform_style_throughout: Optional[bool] = True

    # Legacy flat fields
    caption_pos: Optional[str] = None
    caption_alignment: Optional[str] = None
    caption_prefix: Optional[str] = "Рисунок"
    caption_separator: Optional[str] = "–"
    numbering_style: Optional[str] = None
    recommended_sizes: Optional[Any] = None
    center: Optional[bool] = True
    separate_with_blank_line: Optional[bool] = True

    @field_validator("recommended_sizes", mode="before")
    @classmethod
    def coerce_sizes_to_list(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip():
            return [v.strip()]
        return v


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class TableCaptionConfig(BaseModel):
    pos: Optional[str] = "top"
    alignment: Optional[str] = "left"
    aligned_to: Optional[str] = "table_left_border"
    word: Optional[str] = "Таблица"
    word_no_abbreviation: Optional[bool] = True
    separator: Optional[str] = "–"
    numbering_style: Optional[str] = "continuous"
    number_format_per_section: Optional[str] = "Таблица N.M"
    appendix_format: Optional[str] = "Таблица Б.2"
    example: Optional[str] = "Таблица 2 – Заголовок таблицы"


class TableBordersConfig(BaseModel):
    left: Optional[bool] = True
    right: Optional[bool] = True
    bottom: Optional[bool] = True
    top: Optional[bool] = True
    omit_bottom_if_continues: Optional[bool] = True


class TableHeaderRowConfig(BaseModel):
    bold: Optional[bool] = True
    uppercase_first_letter: Optional[bool] = True
    nominative_case_singular: Optional[bool] = True
    no_period_at_end: Optional[bool] = True
    no_abbreviations: Optional[bool] = True
    no_diagonal_split_cell: Optional[bool] = True


class TableBodyConfig(BaseModel):
    no_empty_cells: Optional[bool] = True
    empty_cell_placeholder: Optional[str] = "–"
    numbers_aligned_by_digit_position: Optional[bool] = True
    numbers_of_different_units_centered: Optional[bool] = True
    decimal_places_consistent_per_column: Optional[bool] = True
    no_order_number_column: Optional[bool] = True


class TableContinuationConfig(BaseModel):
    label: Optional[str] = "Продолжение таблицы"
    repeat_header: Optional[bool] = True
    header_replaceable_by_column_numbers: Optional[bool] = True


class TableConfig(BaseModel):
    caption: Optional[TableCaptionConfig] = Field(default_factory=TableCaptionConfig)
    spacing_before_lines: Optional[int] = 1
    spacing_after_lines: Optional[int] = 1
    caption_to_table_spacing_lines: Optional[int] = 0
    borders: Optional[TableBordersConfig] = Field(default_factory=TableBordersConfig)
    header_row: Optional[TableHeaderRowConfig] = Field(default_factory=TableHeaderRowConfig)
    body: Optional[TableBodyConfig] = Field(default_factory=TableBodyConfig)
    continuation: Optional[TableContinuationConfig] = Field(default_factory=TableContinuationConfig)
    notes: Optional[Dict[str, str]] = Field(
        default_factory=lambda: {"placement": "end_of_table_above_bottom_line"}
    )
    split_narrow_table_side_by_side: Optional[bool] = True
    split_separator: Optional[str] = "double_line"

    # Legacy flat fields
    caption_pos: Optional[str] = None
    caption_alignment: Optional[str] = None
    caption_word: Optional[str] = "Таблица"
    caption_separator: Optional[str] = "–"
    font_size_pt: Optional[float] = None
    line_height: Optional[float] = None
    border_left: Optional[bool] = None
    border_right: Optional[bool] = None
    border_bottom: Optional[bool] = None
    border_top: Optional[bool] = None
    header_bold: Optional[bool] = True
    header_uppercase: Optional[bool] = None
    numbering_style: Optional[str] = None
    continuation_label: Optional[str] = None


# ---------------------------------------------------------------------------
# Bibliography
# ---------------------------------------------------------------------------

class BibliographyCitationConfig(BaseModel):
    type: Optional[str] = "square_brackets_number"
    example: Optional[str] = "[6]"
    ordered_ascending: Optional[bool] = True
    period_after_closing_bracket_if_sentence_end: Optional[bool] = True
    no_orphan_bracket_at_line_start: Optional[bool] = True


class BibliographyFormattingConfig(BaseModel):
    lastname_initials_separator: Optional[str] = ","
    initials_separator: Optional[str] = " "
    publication_type_lowercase: Optional[bool] = True
    bibliographic_signs_spaces: Optional[str] = "both_sides"
    bibliographic_signs: Optional[List[str]] = Field(default_factory=lambda: [":", ";", "–", "/"])
    city_minsk_full_form: Optional[bool] = True
    no_abbreviated_city_minsk: Optional[bool] = True


class BibliographyConfig(BaseModel):
    title: Optional[str] = "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"
    title_uppercase: Optional[bool] = True
    title_bold: Optional[bool] = None
    title_alignment: Optional[str] = "center"
    title_new_page: Optional[bool] = True
    standard: Optional[str] = "ГОСТ 7.1–2003"
    citation: Optional[BibliographyCitationConfig] = Field(default_factory=BibliographyCitationConfig)
    formatting_rules: Optional[BibliographyFormattingConfig] = Field(
        default_factory=BibliographyFormattingConfig
    )
    entry_ordering: Optional[str] = "order_of_appearance"
    placement: Optional[str] = "before_appendices"

    # Legacy fields
    format_standard: Optional[str] = None
    citation_style: Optional[str] = None
    ordering: Optional[str] = None
    hanging_indent_mm: Optional[float] = None


# ---------------------------------------------------------------------------
# Appendix
# ---------------------------------------------------------------------------

class AppendixInternalNumberingConfig(BaseModel):
    formulas: Optional[str] = "AppLetter.N"
    figures: Optional[str] = "AppLetter.N"
    tables: Optional[str] = "AppLetter.N"
    restart_per_appendix: Optional[bool] = True


class AppendixConfig(BaseModel):
    letter_sequence_start: Optional[str] = "А"
    excluded_letters: Optional[List[str]] = Field(
        default_factory=lambda: ["Ё", "З", "Й", "О", "Ч", "Ъ", "Ы", "Ь"]
    )
    new_page: Optional[bool] = True
    label_word: Optional[str] = "ПРИЛОЖЕНИЕ"
    label_uppercase: Optional[bool] = True
    label_alignment: Optional[str] = "center"
    type_label_in_parentheses: Optional[bool] = True
    type_label_variants: Optional[List[str]] = Field(
        default_factory=lambda: ["обязательное", "рекомендуемое", "справочное"]
    )
    title_alignment: Optional[str] = "center"
    title_first_letter_uppercase: Optional[bool] = True
    internal_numbering: Optional[AppendixInternalNumberingConfig] = Field(
        default_factory=AppendixInternalNumberingConfig
    )
    included_in_page_numbering: Optional[bool] = True
    reference_mandatory_in_text: Optional[bool] = True
    ordered_by_reference_order: Optional[bool] = True
    single_appendix_label: Optional[str] = "ПРИЛОЖЕНИЕ А"

    # Legacy fields
    numbering: Optional[str] = None
    type_label: Optional[str] = None


# ---------------------------------------------------------------------------
# Footnotes & Notes
# ---------------------------------------------------------------------------

class FootnotesConfig(BaseModel):
    marker_style: Optional[str] = "arabic_with_closing_bracket"
    marker_example: Optional[str] = "1)"
    marker_position: Optional[str] = "superscript_right_top_of_word"
    separator_line: Optional[bool] = True
    text_from_paragraph_indent: Optional[bool] = True
    marker_repeated_below: Optional[bool] = True
    text_indent: Optional[str] = None


class NotesConfig(BaseModel):
    word: Optional[str] = "Примечание"
    word_first_letter_uppercase: Optional[bool] = True
    placement: Optional[str] = "after_related_material"
    indent: Optional[str] = "paragraph_indent"
    single_format: Optional[str] = "Примечание – текст с прописной буквы"
    multiple_format: Optional[str] = "numbered_arabic"
    table_note_position: Optional[str] = "end_of_table_above_bottom_line"


# ---------------------------------------------------------------------------
# Work structure section
# ---------------------------------------------------------------------------

class SectionTemplate(BaseModel):
    role: str
    title_hints: List[str] = Field(default_factory=list)
    required: Optional[bool] = True
    heading_level: Optional[int] = None
    numbered: Optional[bool] = None
    title_uppercase: Optional[bool] = None
    title_bold: Optional[bool] = None
    title_alignment: Optional[str] = None
    title_no_paragraph_indent: Optional[bool] = None
    new_page: Optional[bool] = None
    counted_in_pagination: Optional[bool] = True
    page_number_shown: Optional[bool] = True
    min_pages: Optional[int] = None
    max_pages: Optional[int] = None
    has_subsections: Optional[bool] = None
    subsection_heading_level: Optional[int] = None
    placed_after: Optional[str] = None
    max_percent_of_total: Optional[float] = None
    max_percent_of_total_min: Optional[float] = None
    max_percent_of_total_max: Optional[float] = None

    # Legacy field
    numbering: Optional[str] = None


# ---------------------------------------------------------------------------
# Volume requirements
# ---------------------------------------------------------------------------

class VolumeRequirementsConfig(BaseModel):
    total_pages_without_reference_appendices_min: Optional[int] = 60
    total_pages_without_reference_appendices_max: Optional[int] = 80
    binding: Optional[str] = "hard_cover"


# ---------------------------------------------------------------------------
# Root template configuration
# ---------------------------------------------------------------------------

class TemplateConfiguration(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page: Optional[PageConfig] = Field(default_factory=PageConfig)
    fonts: Optional[FontConfig] = Field(default_factory=FontConfig)
    headers: Optional[HeadersConfig] = Field(default_factory=HeadersConfig)
    table_of_contents: Optional[TableOfContentsConfig] = Field(default_factory=TableOfContentsConfig)
    lists: Optional[ListConfig] = Field(default_factory=ListConfig)
    text_rules: Optional[TextRulesConfig] = Field(default_factory=TextRulesConfig)
    formulas: Optional[FormulaConfig] = Field(default_factory=FormulaConfig)
    images: Optional[ImageConfig] = Field(default_factory=ImageConfig)
    tables: Optional[TableConfig] = Field(default_factory=TableConfig)
    bibliography: Optional[BibliographyConfig] = Field(default_factory=BibliographyConfig)
    appendix: Optional[AppendixConfig] = Field(default_factory=AppendixConfig)
    footnotes: Optional[FootnotesConfig] = Field(default_factory=FootnotesConfig)
    notes: Optional[NotesConfig] = Field(default_factory=NotesConfig)
    work_structure: Optional[List[SectionTemplate]] = Field(default_factory=list)
    volume_requirements: Optional[VolumeRequirementsConfig] = Field(
        default_factory=VolumeRequirementsConfig
    )
    extra_rules: Optional[List[str]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def sanitize_all(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return _sanitize_value(data)
        return data


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------

class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    template_json: TemplateConfiguration
    type: TemplateType = TemplateType.PERSONAL


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_json: Optional[TemplateConfiguration] = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: Optional[UUID]
    name: str
    description: Optional[str]
    type: TemplateType
    template_json: TemplateConfiguration
    created_at: datetime
    updated_at: datetime


class TemplateListResponse(BaseModel):
    items: List[TemplateOut]
    total: int
