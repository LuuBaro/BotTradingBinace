
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, TradeJournal, Event
from sqlalchemy import select

async def verify_api_logic():
    async with AsyncSessionFactory() as session:
        # Get admin
        res = await session.execute(select(User).where(User.username == "admin"))
        admin = res.scalar_one_or_none()
        
        if not admin:
            print("Admin not found")
            return
            
        print(f"Testing for Admin UUID: {admin.id}")
        
        # Test Trade Journal query (simulating /trade-journal or /trades)
        journal_res = await session.execute(
            select(TradeJournal).where(TradeJournal.user_id == admin.id).limit(5)
        )
        trades = journal_res.scalars().all()
        print(f"Found {len(trades)} trades in journal for admin UUID")
        for t in trades:
            print(f"  - Trade: {t.symbol} {t.side} PNL: {t.pnl}")
            
        # Test Events query (simulating /events)
        event_res = await session.execute(
            select(Event).where(Event.user_id == admin.id).limit(5)
        )
        events = event_res.scalars().all()
        print(f"Found {len(events)} events for admin UUID")
        for e in events:
            print(f"  - Event: [{e.timestamp}] {e.code}: {e.message[:50]}...")

if __name__ == "__main__":
    asyncio.run(verify_api_logic())
