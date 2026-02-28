
import asyncio
import os
import sys
from sqlalchemy import select, func

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory, engine
from packages.shared.models import Decision, TradeJournal

async def check_data():
    print(f"Connecting to: {engine.url}")
    try:
        async with AsyncSessionFactory() as session:
            # Check Decisions count
            cnt_res = await session.execute(select(func.count()).select_from(Decision))
            cnt = cnt_res.scalar()
            print(f"Total Decisions: {cnt}")

            # Check Decisions info
            d_res = await session.execute(select(Decision).order_by(Decision.timestamp.desc()).limit(5))
            decisions = d_res.scalars().all()
            for d in decisions:
                print(f"Decision ID: {d.id}, OrderID: {d.order_id}, Rationale: {d.rationale}")

            # Check TradeJournal count
            cnt_tj_res = await session.execute(select(func.count()).select_from(TradeJournal))
            cnt_tj = cnt_tj_res.scalar()
            print(f"Total TradeJournal: {cnt_tj}")

            # Check TradeJournal info
            tj_res = await session.execute(select(TradeJournal).order_by(TradeJournal.closed_at.desc()).limit(5))
            tjs = tj_res.scalars().all()
            for tj in tjs:
                print(f"TJ ID: {tj.id}, PnL: {tj.pnl}, ExitReason: {tj.exit_reason}")
                print(f"  DecisionJSON: {tj.decision_json.get('rationale') if isinstance(tj.decision_json, dict) else 'N/A'}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_data())
