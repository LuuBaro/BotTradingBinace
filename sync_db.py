import asyncio
from packages.shared.models import Base
from packages.shared.database import engine

async def update_schema():
    print("Upgrading database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Schema upgrade complete.")

if __name__ == "__main__":
    asyncio.run(update_schema())
