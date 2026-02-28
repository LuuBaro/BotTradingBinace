
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import TraderContext, Decision

async def analyze_full():
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select, desc
        
        print("\n--- TRADER PROMPT ---")
        res = await session.execute(select(TraderContext).order_by(desc(TraderContext.timestamp)).limit(1))
        context = res.scalar_one_or_none()
        if context:
            print(context.prompt)
        
        print("\n--- RECENT AI DECISIONS (RATIONALE) ---")
        res = await session.execute(select(Decision).order_by(desc(Decision.timestamp)).limit(5))
        decisions = res.scalars().all()
        for d in decisions:
            sym = d.decision_json.get("symbol") if d.decision_json else "UNK"
            print(f"[{d.timestamp}] {sym} {d.decision_type}")
            print(f"Rationale: {d.rationale}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(analyze_full())
