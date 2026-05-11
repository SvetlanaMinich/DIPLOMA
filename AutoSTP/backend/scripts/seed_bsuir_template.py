import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select

# Добавляем путь к приложению в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import async_session_maker
from app.models.template import Template, TemplateType

async def seed():
    print("Seeding BSUIR STP 01-2024 template...")
    
    bsuir_config = {
        "page": {
            "size": "A4",
            "margin_top": 20.0,
            "margin_bottom": 20.0,
            "margin_left": 30.0,
            "margin_right": 10.0,
            "page_number_pos": "bottom_right"
        },
        "fonts": {
            "main_family": "Times New Roman",
            "main_size": 14.0,
            "line_height": 1.5,
            "paragraph_indent": 12.5
        },
        "headers": {
            "level_1": {
                "size": 14.0,
                "bold": True,
                "italic": False,
                "uppercase": True,
                "alignment": "center",
                "new_page": True,
                "spacing_before": 12.0,
                "spacing_after": 12.0,
                "indent_first_line": False
            },
            "level_2": {
                "size": 14.0,
                "bold": True,
                "italic": False,
                "uppercase": False,
                "alignment": "left",
                "new_page": False,
                "spacing_before": 8.0,
                "spacing_after": 8.0,
                "indent_first_line": True
            },
            "level_3": {
                "size": 14.0,
                "bold": False,
                "italic": False,
                "uppercase": False,
                "alignment": "left",
                "new_page": False,
                "spacing_before": 6.0,
                "spacing_after": 6.0,
                "indent_first_line": True
            }
        },
        "lists": {
            "marker_level_1": "-",
            "marker_level_2": "а)",
            "indent_main": 12.5,
            "indent_item": 0.0
        },
        "tables": {
            "caption_pos": "top",
            "caption_alignment": "left",
            "font_size": 12.0,
            "line_height": 1.0,
            "border_width": 0.5,
            "header_bold": False
        },
        "images": {
            "caption_pos": "bottom",
            "caption_alignment": "center",
            "caption_prefix": "Рисунок"
        },
        "formulas": {
            "alignment": "center",
            "numbering_alignment": "right",
            "numbering_style": "(1.1)"
        },
        "work_structure": [
            {"role": "referat", "title_hints": ["РЕФЕРАТ"], "required": True},
            {"role": "content", "title_hints": ["СОДЕРЖАНИЕ"], "required": True},
            {"role": "introduction", "title_hints": ["ВВЕДЕНИЕ"], "required": True},
            {"role": "conclusion", "title_hints": ["ЗАКЛЮЧЕНИЕ"], "required": True},
            {"role": "references", "title_hints": ["СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"], "required": True}
        ]
    }

    async with async_session_maker() as session:
        res = await session.execute(select(Template).where(Template.name == "БГУИР СТП 01-2024"))
        if res.scalar_one_or_none():
            print("Template already exists. Skipping.")
            return

        db_obj = Template(
            id=uuid4(),
            name="БГУИР СТП 01-2024",
            description="Основной стандарт оформления пояснительных записок БГУИР.",
            type=TemplateType.SYSTEM,
            template_json=bsuir_config
        )
        session.add(db_obj)
        await session.commit()
        print("Success! BSUIR template seeded.")

if __name__ == "__main__":
    asyncio.run(seed())
