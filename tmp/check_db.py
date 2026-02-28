
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.db import AsyncSessionFactory
from packages.shared.models import Decision, TradeJournal
from sqlalchemy import select

async def check_data():
    async with AsyncSessionFactory() as session:
        # Check Decisions
        d_res = await session.execute(select(Decision).limit(10))
        decisions = d_res.scalars().all()
        print(f"--- Decisions Found: {len(decisions)} ---")
        for d in decisions:
            print(f"ID: {d.id}, OrderID: {d.order_id}, Rationale: {d.rationale}")
        
        # Check TradeJournal
        t_res = await session.execute(select(TradeJournal).limit(10))
        trades = t_res.scalars().all()
        print(f"\n--- TradeJournal Found: {len(trades)} ---")
        for t in trades:
            print(f"ID: {t.id}, PnL: {t.pnl}, DecisionJSON: {t.decision_json}")

if __name__ == "__main__":
    asyncio.run(check_data())
