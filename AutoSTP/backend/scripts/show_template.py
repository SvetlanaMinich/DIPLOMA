import sys, io, json, asyncio, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://autostp:autostp_password@localhost:5432/autostp_db"
)


async def main():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy import text

    e = create_async_engine(os.environ["DATABASE_URL"])
    async with async_sessionmaker(e)() as s:
        r = await s.execute(
            text(
                "SELECT template_json FROM templates "
                "WHERE name LIKE '%%01-2024' "
                "ORDER BY updated_at DESC LIMIT 1"
            )
        )
        row = r.scalar()
        print(json.dumps(row, indent=2, ensure_ascii=False))
    await e.dispose()


asyncio.run(main())
