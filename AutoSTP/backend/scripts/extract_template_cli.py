"""
CLI tool for extracting formatting rules from a PDF/DOCX/TXT file.

Usage:
    cd AutoSTP/backend
    python scripts/extract_template_cli.py ../../12_100229_1_185586.pdf

Optional flags:
    --out  PATH      Write JSON to this file (default: extracted_template.json)
    --text PATH      Also write the extracted raw text to this file (for debug)
    --no-defaults    Skip applying STP-01-2024 fallback defaults
    --verbose        Show per-chunk LLM responses
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Allow running from both  backend/  and  backend/scripts/
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

# Load .env before importing app modules
from dotenv import load_dotenv

for _candidate in [
    _HERE.parent / ".env",
    _HERE.parent.parent / ".env",
]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break

from app.services.template_service import (
    extract_text_from_bytes,
    find_formatting_section,
    make_chunks,
    _apply_stp_defaults,
    _call_llm_for_chunk,
    _deep_merge,
)
from app.schemas.template import TemplateConfiguration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _count_filled(d: object, depth: int = 0) -> tuple[int, int]:
    """Return (filled, total) count of leaf values in a dict."""
    if isinstance(d, dict):
        filled = total = 0
        for v in d.values():
            f, t = _count_filled(v, depth + 1)
            filled += f
            total += t
        return filled, total
    if isinstance(d, list):
        return (1, 1) if d else (0, 1)
    if d is None:
        return 0, 1
    return 1, 1


def _print_summary(cfg: dict) -> None:
    sections = ["page", "fonts", "headers", "table_of_contents", "lists",
                "tables", "images", "formulas", "bibliography", "appendix",
                "footnotes"]
    print("\n--- Extraction summary ---")
    print(f"{'Section':<26} {'Filled':>6} / {'Total':<6} {'Bar'}")
    print("-" * 55)
    for sec in sections:
        data = cfg.get(sec, {})
        f, t = _count_filled(data)
        pct = int(f / max(t, 1) * 20)
        bar = "#" * pct + "." * (20 - pct)
        print(f"  {sec:<24} {f:>4}/{t:<4}  [{bar}]")
    ws = cfg.get("work_structure", [])
    print(f"  {'work_structure':<24} {len(ws):>4} sections")
    er = cfg.get("extra_rules", [])
    print(f"  {'extra_rules':<24} {len(er):>4} rules")
    print("-" * 55)


async def run(args: argparse.Namespace) -> None:
    input_path = Path(args.file).resolve()
    if not input_path.exists():
        sys.exit(f"ERROR: file not found: {input_path}")

    out_path = Path(args.out) if args.out else input_path.parent / "extracted_template.json"

    def _p(s: str) -> None:
        print(s.encode("utf-8", errors="replace").decode(
            __import__("sys").stdout.encoding or "utf-8", errors="replace"
        ))

    _p(f"\n{'='*56}")
    _p(f"  AutoSTP template extractor")
    _p(f"  Input : {input_path}")
    _p(f"  Output: {out_path}")
    _p(f"{'='*56}\n")

    # 1. Read file
    t0 = time.perf_counter()
    file_bytes = input_path.read_bytes()
    print(f"[1/5] Read {len(file_bytes):,} bytes from '{input_path.name}'")

    # 2. Extract text
    text = extract_text_from_bytes(file_bytes, input_path.name)
    print(f"[2/5] Extracted {len(text):,} chars of plain text")

    if args.text:
        Path(args.text).write_text(text, encoding="utf-8")
        print(f"      (raw text saved to {args.text})")

    # 3. Find formatting section
    section = find_formatting_section(text)
    print(f"[3/5] Formatting section: {len(section):,} chars")

    # 4. Chunk and call LLM
    chunks = make_chunks(section, chunk_size=5_000, overlap=500)
    print(f"[4/5] Sending {len(chunks)} chunk(s) to LLM …\n")

    final_config: dict = {"extra_rules": []}
    for idx, chunk in enumerate(chunks):
        print(f"      Chunk {idx+1}/{len(chunks)} ({len(chunk):,} chars) …", end="", flush=True)
        try:
            result = await _call_llm_for_chunk(chunk)
            _deep_merge(final_config, result)
            if args.verbose:
                print()
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                # Count non-null leaf values in this chunk's result
                f, t = _count_filled(result)
                print(f" ->{f}/{t} fields filled")
        except Exception as e:
            print(f" ERR:{e}")

        if idx < len(chunks) - 1:
            await asyncio.sleep(0.8)

    # 5. Apply defaults (unless disabled)
    if not args.no_defaults:
        _apply_stp_defaults(final_config)
        print("\n[5/5] Applied STP-01-2024 fallback defaults")
    else:
        print("\n[5/5] Skipped defaults (--no-defaults)")

    # Validate with Pydantic
    try:
        cfg_obj = TemplateConfiguration(**final_config)
        final_dict = cfg_obj.model_dump()
    except Exception as e:
        logger.warning("Pydantic validation warning: %s — saving raw dict", e)
        final_dict = final_config

    # Save
    out_path.write_text(json.dumps(final_dict, ensure_ascii=False, indent=2), encoding="utf-8")

    elapsed = time.perf_counter() - t0
    print(f"\n[+] Done in {elapsed:.1f}s -> {out_path}")

    _print_summary(final_dict)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract formatting rules from a PDF/DOCX/TXT and output JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("file", help="Path to the source file (PDF, DOCX, TXT)")
    parser.add_argument("--out", metavar="PATH", help="Output JSON file path")
    parser.add_argument("--text", metavar="PATH", help="Save extracted plain text here (debug)")
    parser.add_argument("--no-defaults", action="store_true",
                        help="Do not fill in STP-01-2024 fallback defaults")
    parser.add_argument("--verbose", action="store_true",
                        help="Print raw LLM response for each chunk")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
