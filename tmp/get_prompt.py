
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import TraderContext

async def get_prompt():
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select, desc
        res = await session.execute(select(TraderContext).order_by(desc(TraderContext.timestamp)).limit(2))
        rows = res.all()
        for idx, row in enumerate(rows):
            ctx = row[0]
            print(f"--- PROMPT {idx} ({ctx.trader_name}) ---")
            print(ctx.prompt)
            print("="*60)

if __name__ == "__main__":
    asyncio.run(get_prompt())
