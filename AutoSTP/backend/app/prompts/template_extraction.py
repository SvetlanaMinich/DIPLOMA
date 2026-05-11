"""Prompts for extracting formatting rules from STP/GOST standard documents.

Strategy: one comprehensive prompt per text chunk.
Placeholder __TEXT_PLACEHOLDER__ is replaced by str.replace(), not .format().
"""

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a Document Standards Analyst specialising in academic formatting "
    "standards (STP / GOST / university guidelines). "
    "CRITICAL RULES:\n"
    "- Extract ONLY values that are EXPLICITLY stated in the text.\n"
    "- Do NOT invent or infer values that are not written.\n"
    "- For missing fields output null, not empty string.\n"
    "- Output valid JSON only — no markdown fences, no prose.\n"
    "- Margins and indents: numbers in millimetres (mm). "
    "  Typical paragraph indent 12–13 mm; if you get >25 divide by 10.\n"
    "- Font sizes and line spacing: numbers in points (pt).\n"
    "- Line height ratio (e.g. 1.0): plain float, not points.\n"
    "- Boolean fields: true / false / null.\n"
    "- Russian text in values is fine.\n"
)

# ---------------------------------------------------------------------------
# Comprehensive single-pass extraction prompt
# ---------------------------------------------------------------------------

COMPREHENSIVE_PROMPT = """\
Extract EVERY formatting rule you can find in the text below.
Cover ALL of the following areas exhaustively:
  page layout, fonts/spacing, headings (levels 1-4), table of contents,
  lists/enumerations, text style rules, mathematical formulas,
  figures/images, tables, bibliography/references, appendices,
  footnotes, notes (примечания), document structure (required sections).

Output ONE JSON object with EXACTLY this structure.
Use null for any field not mentioned in the text.
Put any rule that does not fit a structured field into extra_rules as a string.

{
  "page": {
    "size": null,
    "orientation": null,
    "margin_left_mm": null,
    "margin_right_mm": null,
    "margin_top_mm": null,
    "margin_bottom_mm": null,
    "page_number_pos": null,
    "page_number_font_size_pt": null,
    "first_page_numbered": null,
    "pages_counted_not_numbered": null,
    "hyphenation_in_body": null,
    "hyphenation_in_headings": null,
    "hyphenation_in_tables": null,
    "hyphenation_in_captions": null
  },
  "fonts": {
    "main_family": null,
    "main_size_pt": null,
    "main_bold": null,
    "main_italic": null,
    "line_height_multiple": null,
    "line_height_pt": null,
    "paragraph_indent_mm": null,
    "text_alignment": null,
    "latin_formula_italic": null,
    "cyrillic_formula_italic": null,
    "greek_formula_italic": null
  },
  "headers": {
    "numbered_alignment": null,
    "unnumbered_alignment": null,
    "unnumbered_no_paragraph_indent": null,
    "level_1": {
      "font_size_pt": null, "bold": null, "italic": null, "underline": null,
      "uppercase": null, "numbered": null, "number_has_trailing_dot": null,
      "new_page": null, "spacing_before_lines": null, "spacing_after_lines": null,
      "indent_from_paragraph": null, "multiline_align_to_first_char": null,
      "no_period_at_end": null, "two_sentences_separated_by_dot": null
    },
    "level_2": {
      "font_size_pt": null, "bold": null, "italic": null, "underline": null,
      "uppercase": null, "first_letter_uppercase": null, "numbered": null,
      "number_format": null, "number_has_trailing_dot": null,
      "new_page": null, "spacing_before_lines": null, "spacing_after_lines": null,
      "indent_from_paragraph": null, "multiline_align_to_first_char": null,
      "no_period_at_end": null, "move_to_next_page_if_no_body_fits": null
    },
    "level_3": {
      "font_size_pt": null, "bold": null, "uppercase": null,
      "first_letter_uppercase": null, "numbered": null,
      "number_format": null, "has_heading": null,
      "new_page": null, "spacing_after_lines": null
    },
    "level_4": {
      "font_size_pt": null, "bold": null, "uppercase": null,
      "numbered": null, "number_format": null,
      "has_heading": null, "new_page": null
    }
  },
  "table_of_contents": {
    "title": null,
    "title_uppercase": null,
    "title_bold": null,
    "title_font_size_pt": null,
    "title_font_size_pt_max": null,
    "title_alignment": null,
    "spacing_after_title_lines": null,
    "indent_per_level_chars": null,
    "indent_per_level_mm": null,
    "dot_leader": null,
    "page_number_column": null,
    "include_level_1": null,
    "include_level_2": null,
    "include_level_3": null,
    "include_appendices": null,
    "include_references": null,
    "include_document_list": null,
    "placed_after": null
  },
  "lists": {
    "simple": {
      "marker": null,
      "each_item_new_line": null,
      "indent_type": null,
      "item_end_punctuation": null,
      "last_item_end_punctuation": null,
      "inline_allowed": null,
      "inline_separator": null
    },
    "complex_numbered": {
      "marker_type": null,
      "each_item_new_line": null,
      "indent_type": null,
      "first_letter_uppercase": null,
      "item_end_punctuation": null
    },
    "lettered": {
      "marker_type": null,
      "marker_example": null,
      "each_item_new_line": null,
      "indent_type": null,
      "item_end_punctuation": null
    },
    "sub_lettered": {
      "marker_type": null,
      "marker_example": null,
      "each_item_new_line": null,
      "indent_type": null,
      "item_end_punctuation": null
    },
    "intro_phrase_must_not_end_with_preposition": null
  },
  "text_rules": {
    "numbers_1_to_9_without_units_as_words": null,
    "numbers_above_9_as_digits": null,
    "fractions_as_decimal": null,
    "ordinal_numbers_with_inflection": null,
    "math_signs_without_values_as_words": null,
    "range_unit_after_last_value": null,
    "no_dash_before_number_with_unit": null,
    "physical_units_standard": null,
    "no_foreign_terms_if_russian_exists": null
  },
  "formulas": {
    "alignment": null,
    "placed_on_separate_line": null,
    "spacing_before_lines": null,
    "spacing_after_lines": null,
    "simple_formula_spacing_intervals": null,
    "complex_formula_spacing_intervals": null,
    "inline_allowed_for_short_aux": null,
    "multi_formula_per_line_separator": null,
    "numbering": {
      "style": null,
      "format": null,
      "example": null,
      "appendix_format": null,
      "continuous_allowed": null,
      "position": null,
      "number_in_parentheses": null,
      "fraction_number_at_mid_bar": null,
      "multiline_number_at_last_line": null
    },
    "explanation": {
      "starts_with_word": null,
      "no_colon_after_where": null,
      "from_new_line": null,
      "no_paragraph_indent": null,
      "symbol_separator": null,
      "symbols_aligned": null,
      "each_entry_ends_with": null,
      "unit_at_end_of_entry": null,
      "unit_separator": null,
      "alternative_start": null,
      "alternative_with_period_before": null
    },
    "wrap": {
      "allowed": null,
      "operator_repeated_at_wrap": null,
      "multiplication_sign_at_wrap": null,
      "no_wrap_on_division": null,
      "no_wrap_on_root_integral_log_trig": null
    }
  },
  "images": {
    "universal_term": null,
    "alignment": null,
    "spacing_before_lines": null,
    "spacing_after_caption_lines": null,
    "recommended_sizes_mm": null,
    "placed_after_first_reference_paragraph": null,
    "multiple_per_page_allowed": null,
    "orientation_max_rotation_deg": null,
    "caption": {
      "pos": null,
      "alignment": null,
      "prefix_word": null,
      "prefix_no_abbreviation": null,
      "separator": null,
      "numbering_style": null,
      "number_format_continuous": null,
      "number_format_per_section": null,
      "appendix_format": null,
      "no_period_after_number": null,
      "title_starts_uppercase": null,
      "no_period_at_end": null,
      "example": null,
      "multipage_label": null
    },
    "inscription_min_height_mm": null,
    "uppercase_1_3_larger_than_lowercase": null,
    "reference_in_text_mandatory": null,
    "uniform_style_throughout": null
  },
  "tables": {
    "caption": {
      "pos": null,
      "alignment": null,
      "aligned_to": null,
      "word": null,
      "word_no_abbreviation": null,
      "separator": null,
      "numbering_style": null,
      "number_format_per_section": null,
      "appendix_format": null,
      "example": null
    },
    "spacing_before_lines": null,
    "spacing_after_lines": null,
    "caption_to_table_spacing_lines": null,
    "borders": {
      "left": null, "right": null, "bottom": null, "top": null,
      "omit_bottom_if_continues": null
    },
    "header_row": {
      "bold": null,
      "uppercase_first_letter": null,
      "nominative_case_singular": null,
      "no_period_at_end": null,
      "no_abbreviations": null,
      "no_diagonal_split_cell": null
    },
    "body": {
      "no_empty_cells": null,
      "empty_cell_placeholder": null,
      "numbers_aligned_by_digit_position": null,
      "numbers_of_different_units_centered": null,
      "decimal_places_consistent_per_column": null,
      "no_order_number_column": null
    },
    "continuation": {
      "label": null,
      "repeat_header": null,
      "header_replaceable_by_column_numbers": null
    },
    "split_narrow_table_side_by_side": null,
    "split_separator": null
  },
  "bibliography": {
    "title": null,
    "title_uppercase": null,
    "title_bold": null,
    "title_alignment": null,
    "title_new_page": null,
    "standard": null,
    "citation": {
      "type": null,
      "example": null,
      "ordered_ascending": null,
      "period_after_closing_bracket_if_sentence_end": null,
      "no_orphan_bracket_at_line_start": null
    },
    "formatting_rules": {
      "lastname_initials_separator": null,
      "initials_separator": null,
      "publication_type_lowercase": null,
      "bibliographic_signs_spaces": null,
      "bibliographic_signs": null,
      "city_minsk_full_form": null
    },
    "entry_ordering": null,
    "placement": null
  },
  "appendix": {
    "letter_sequence_start": null,
    "excluded_letters": null,
    "new_page": null,
    "label_word": null,
    "label_uppercase": null,
    "label_alignment": null,
    "type_label_in_parentheses": null,
    "type_label_variants": null,
    "title_alignment": null,
    "title_first_letter_uppercase": null,
    "internal_numbering": {
      "formulas": null,
      "figures": null,
      "tables": null,
      "restart_per_appendix": null
    },
    "included_in_page_numbering": null,
    "reference_mandatory_in_text": null,
    "ordered_by_reference_order": null,
    "single_appendix_label": null
  },
  "footnotes": {
    "marker_style": null,
    "marker_example": null,
    "marker_position": null,
    "separator_line": null,
    "text_from_paragraph_indent": null,
    "marker_repeated_below": null
  },
  "notes": {
    "word": null,
    "word_first_letter_uppercase": null,
    "placement": null,
    "indent": null,
    "single_format": null,
    "multiple_format": null,
    "table_note_position": null
  },
  "work_structure": [
    {
      "role": "string — one of: title_page, abstract, task, contents, abbreviations, introduction, main_body, tech_economy, safety_ecology, conclusion, references, appendices, document_list",
      "title_hints": ["exact title string from the standard"],
      "required": true,
      "heading_level": null,
      "numbered": null,
      "title_uppercase": null,
      "title_bold": null,
      "title_alignment": null,
      "title_no_paragraph_indent": null,
      "new_page": null,
      "counted_in_pagination": null,
      "page_number_shown": null,
      "min_pages": null,
      "max_pages": null,
      "has_subsections": null,
      "placed_after": null,
      "max_percent_of_total": null
    }
  ],
  "extra_rules": ["plain-text string for any rule that does not fit the fields above"]
}

Notes on heading levels:
  level_1 = раздел (1, 2, 3 …) — numbered sections
  level_2 = подраздел (1.1, 1.2 …) — subsections
  level_3 = пункт (1.1.1 …) — points
  level_4 = подпункт (1.1.1.1 …) — sub-points

Unnumbered sections (Введение, Заключение, Содержание, Реферат, Список источников, Приложения):
  use unnumbered_alignment, NOT level_1 alignment.

TEXT:
__TEXT_PLACEHOLDER__"""
