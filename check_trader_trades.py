#!/usr/bin/env python3
"""Check TradeJournal data for trader"""
import asyncio
import sys
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages'))

from shared.models import User, TradeJournal

async def check():
    DATABASE_URL = "sqlite+aiosqlite:///./data/trading.db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        trader_res = await db.execute(select(User).where(User.username == "trader"))
        trader_user = trader_res.scalar_one_or_none()
        if not trader_user:
            print("Trader not found")
            return
        
        trader_id = trader_user.id
        trades_res = await db.execute(select(TradeJournal).where(TradeJournal.user_id == trader_id))
        trades = trades_res.scalars().all()
        
        print(f"✅ Trader has {len(trades)} TradeJournal records\n")
        
        if trades:
            print("Trade Details:")
            for i, t in enumerate(trades[:5], 1):
                entry_price = float(t.entry_price or 0)
                exit_price = float(t.exit_price or 0)
                pnl = float(t.pnl or 0)
                print(f"  {i}. {t.symbol} {t.side: <6} | Entry:{entry_price:>10.2f} Exit:{exit_price:>10.2f} | PnL:{pnl:>10.2f}")
        
        print(f"\n✅ /learning page should now be populated!")

if __name__ == "__main__":
    asyncio.run(check())
