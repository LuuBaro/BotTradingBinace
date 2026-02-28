
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Decision

async def check():
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select, desc
        res = await session.execute(select(Decision).order_by(desc(Decision.timestamp)).limit(20))
        rows = res.scalars().all()
        print(f"Total rows found: {len(rows)}")
        for d in rows:
            print(f"[{d.timestamp}] ID: {d.id} | TYPE: {d.decision_type} | STATUS: {d.status}")
            print(f"  Rationale: {d.rationale[:80]}...")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(check())
