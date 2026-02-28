
import asyncio
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Event

async def check():
    async with AsyncSessionFactory() as session:
        from sqlalchemy import text
        res = await session.execute(text("SELECT message, timestamp FROM events ORDER BY timestamp DESC LIMIT 5"))
        rows = res.all()
        print(f"Current local time: {datetime.now()}")
        if rows:
            print("--- RECENT EVENTS ---")
            for msg, ts in rows:
                print(f"{ts} - {msg}")
        else:
            print("No events found.")

if __name__ == "__main__":
    asyncio.run(check())
