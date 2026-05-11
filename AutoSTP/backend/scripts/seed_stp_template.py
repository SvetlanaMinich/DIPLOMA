"""Seed the system STP 01-2024 template by extracting rules from the PDF.

Usage (from backend/):
    python scripts/seed_stp_template.py              # extract + save
    python scripts/seed_stp_template.py --dry-run     # extract only, print JSON
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io as _io

sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

if "/autostp_test_db" not in os.environ.get("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://autostp:autostp_password@localhost:5432/autostp_db",
    )

from app.schemas.template import TemplateConfiguration
from app.services.template_service import extract_template_from_file

PDF_PATH = r"c:\sem7\практика-преддиплом\диплом\12_100229_1_185586.pdf"


async def main(dry_run: bool = False) -> None:
    print(f"Reading {PDF_PATH} ...")
    with open(PDF_PATH, "rb") as f:
        content = f.read()
    print(f"File size: {len(content)} bytes")

    print("Extracting template via LLM (this will take a minute) ...")
    config = await extract_template_from_file(content, "12_100229_1_185586.pdf")

    as_dict = config.model_dump()
    print(json.dumps(as_dict, indent=2, ensure_ascii=False))

    if dry_run:
        print("\n[dry-run] Not saving to DB.")
        with open("extracted_template.json", "w", encoding="utf-8") as f:
            json.dump(as_dict, f, indent=2, ensure_ascii=False)
        print("Saved to extracted_template.json")
        return

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.core.config import settings
    import app.models  # noqa: F401  register all models
    from app.models.template import Template, TemplateType
    from app.core.database import Base

    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
        existing = await session.execute(
            __import__("sqlalchemy")
            .select(Template)
            .where(
                Template.type == TemplateType.SYSTEM,
                Template.name == "СТП БГУИР 01-2024",
            )
        )
        existing_tmpl = existing.scalar_one_or_none()
        if existing_tmpl:
            existing_tmpl.template_json = as_dict
            print(f"Updated existing system template {existing_tmpl.id}")
        else:
            tmpl = Template(
                user_id=None,
                name="СТП БГУИР 01-2024",
                description="Системный шаблон по СТП БГУИР 01-2024 (извлечён из PDF)",
                type=TemplateType.SYSTEM,
                template_json=as_dict,
            )
            session.add(tmpl)
            print("Created new system template")
        await session.commit()

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
