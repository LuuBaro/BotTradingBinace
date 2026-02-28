
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Decision

async def check_entry():
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select, desc
        res = await session.execute(select(Decision).where(Decision.decision_type == "ENTRY").order_by(desc(Decision.timestamp)).limit(5))
        decisions = res.scalars().all()
        for d in decisions:
            print(f"\n=== ENTRY DECISION {d.id} ===")
            print(f"Symbol: {d.order_spec.get('symbol') if d.order_spec else '??'}")
            print(f"Rationale: {d.rationale}")
            print(f"Order Spec: {d.order_spec}")
            print(f"Risk Assessment: {d.risk_assessment}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(check_entry())
