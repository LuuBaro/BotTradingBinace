
import asyncio
from sqlalchemy import select
from packages.shared.models import Position
from packages.shared.database import AsyncSessionFactory, init_db

async def check_db_positions():
    await init_db()
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Position))
        positions = result.scalars().all()
        print(f"--- DATABASE POSITIONS ---")
        if not positions:
            print("No positions in database.")
        for p in positions:
            print(f"Symbol: {p.symbol}, Side: {p.side}, Qty: {p.qty}, PnL: {p.unrealized_pnl}")

if __name__ == "__main__":
    asyncio.run(check_db_positions())
