import asyncio
from sqlalchemy import text
from packages.shared.database import engine
from packages.shared.models import Base

async def reset_chat_table():
    print("Resetting chat_messages table...")
    async with engine.begin() as conn:
        # Check if table exists
        await conn.execute(text("DROP TABLE IF EXISTS chat_messages"))
        # Recreate everything
        await conn.run_sync(Base.metadata.create_all)
    print("Reset complete.")

if __name__ == "__main__":
    asyncio.run(reset_chat_table())
