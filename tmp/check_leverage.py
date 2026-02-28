
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Decision

async def check_leverage():
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select, desc
        res = await session.execute(select(Decision).where(Decision.decision_type == "ENTRY").order_by(desc(Decision.timestamp)).limit(10))
        decisions = res.scalars().all()
        print("\n=== RECENT ENTRIES (LEVERAGE & SIZE) ===")
        for d in decisions:
            spec = d.order_spec or {}
            risk = d.risk_assessment or {}
            print(f"[{d.timestamp}] {spec.get('symbol')} {spec.get('side')}")
            print(f"  Leverage: {spec.get('leverage')}x")
            print(f"  Quantity: {spec.get('quantity')}")
            print(f"  Position %: {risk.get('position_pct')}%")
            print(f"  Expected Profit: {risk.get('expected_profit_usd')}")
            print(f"  Rationale: {d.rationale[:100]}...")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(check_leverage())
