
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Decision

async def check_all():
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select, desc
        res = await session.execute(select(Decision).order_by(desc(Decision.timestamp)).limit(5))
        decisions = res.scalars().all()
        for d in decisions:
            print(f"\n--- DECISION {d.id} ---")
            print(f"TS: {d.timestamp} | Type: {d.decision_type}")
            print(f"Rationale: {d.rationale}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(check_all())
