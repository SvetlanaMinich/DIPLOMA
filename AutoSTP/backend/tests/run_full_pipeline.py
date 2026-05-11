"""Full pipeline: register → upload → segment (LLM) → format → export."""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import httpx

BASE = "http://localhost:8000/api/v1"
INPUT_FILE = Path(__file__).resolve().parent / "for-test.txt"
OUTPUT_DIR = Path(__file__).resolve().parent / "output_formatted"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def pp(label, resp):
    print(f"  [{resp.status_code}] {label}")
    if resp.status_code >= 400:
        print(f"    ERROR: {resp.text[:300]}")


async def main():
    async with httpx.AsyncClient(timeout=120) as c:
        # 1. Register
        r = await c.post(f"{BASE}/auth/register", json={
            "email": "test_pipeline@autostp.io",
            "password": "TestPass123!",
            "full_name": "Pipeline Tester",
        })
        pp("register", r)

        # 2. Login
        r = await c.post(f"{BASE}/auth/login", json={
            "email": "test_pipeline@autostp.io",
            "password": "TestPass123!",
        })
        pp("login", r)
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"  token: {token[:30]}...")

        # 3. Create template
        r = await c.post(f"{BASE}/templates/", headers=headers, json={
            "name": "СТП 01-2024",
            "type": "personal",
            "template_json": {
                "work_structure": [
                    {"role": "abstract", "title_hints": ["РЕФЕРАТ"], "required": True},
                    {"role": "introduction", "title_hints": ["ВВЕДЕНИЕ"], "required": True},
                    {"role": "main_body", "title_hints": ["Обзор", "Разработка", "Тестирование"], "required": True, "has_subsections": True},
                    {"role": "conclusion", "title_hints": ["ЗАКЛЮЧЕНИЕ"], "required": True},
                ]
            }
        })
        pp("create template", r)
        tmpl_id = r.json()["id"]
        print(f"  template_id: {tmpl_id}")

        # 4. Upload document
        file_bytes = INPUT_FILE.read_bytes()
        r = await c.post(
            f"{BASE}/documents/upload",
            headers=headers,
            files={"file": ("for-test.txt", file_bytes, "text/plain")},
            data={"document_type": "di", "title": "AutoSTP Diploma Test"},
        )
        pp("upload", r)
        doc_id = r.json()["id"]
        print(f"  document_id: {doc_id}")

        # 5. Segment (LLM!)
        print("\n  Segmenting via LLM (this may take 30-120s)...")
        t0 = time.time()
        r = await c.post(
            f"{BASE}/documents/{doc_id}/segment",
            headers=headers,
            json={"template_id": tmpl_id},
            timeout=180,
        )
        elapsed = time.time() - t0
        pp(f"segment ({elapsed:.1f}s)", r)
        if r.status_code == 200:
            seg_data = r.json()
            print(f"  sections: {seg_data['total_sections']}")
            for s in seg_data["sections"]:
                print(f"    [{s['section_type']}] {s['title'][:60]}")

        # 6. Format
        print("\n  Formatting via LaTeX pipeline...")
        r = await c.post(
            f"{BASE}/documents/{doc_id}/format",
            headers=headers,
            json={"template_id": tmpl_id},
            timeout=180,
        )
        pp("format", r)

        # 7. Export DOCX
        r = await c.get(f"{BASE}/documents/{doc_id}/export/docx", headers=headers)
        pp("export docx", r)
        if r.status_code == 200:
            docx_path = OUTPUT_DIR / "pipeline_formatted.docx"
            docx_path.write_bytes(r.content)
            print(f"  saved: {docx_path} ({len(r.content):,} bytes)")

        # 8. Export PDF
        r = await c.get(f"{BASE}/documents/{doc_id}/export/pdf", headers=headers)
        pp("export pdf", r)
        if r.status_code == 200:
            pdf_path = OUTPUT_DIR / "pipeline_formatted.pdf"
            pdf_path.write_bytes(r.content)
            print(f"  saved: {pdf_path} ({len(r.content):,} bytes)")

        # 9. Export TEX
        r = await c.get(f"{BASE}/documents/{doc_id}/export/tex", headers=headers)
        pp("export tex", r)
        if r.status_code == 200:
            tex_path = OUTPUT_DIR / "pipeline_formatted.tex"
            tex_path.write_bytes(r.content)
            print(f"  saved: {tex_path} ({len(r.content):,} bytes)")


import asyncio
asyncio.run(main())
