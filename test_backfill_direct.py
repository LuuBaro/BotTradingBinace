#!/usr/bin/env python3
"""Test backfill directly without API"""
import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/api'))

from shared.models import User, Order, TradeJournal as TradeJournalModel
from structlog import get_logger

logger = get_logger()

async def test_backfill():
    DATABASE_URL = "sqlite+aiosqlite:///./data/trading.db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get trader user
        trader_res = await db.execute(select(User).where(User.username == "trader"))
        trader_user = trader_res.scalar_one_or_none()
        if not trader_user:
            print("❌ Trader user not found")
            return
        
        trader_id = trader_user.id
        print(f"👤 Trader ID: {trader_id}")
        
        # Import and run backfill directly
        print("\n🔄 Running backfill logic directly...")
        
        # Check current TradeJournal count before
        before_res = await db.execute(select(TradeJournalModel).where(TradeJournalModel.user_id == trader_id))
        before_trades = before_res.scalars().all()
        print(f"   Before backfill: {len(before_trades)} TradeJournal records")
        
        # Import the backfill function
        try:
            from phase6_routes import _backfill_trade_journal_from_orders
            
            created = await _backfill_trade_journal_from_orders(db, trader_id, min_needed=5)
            print(f"   Backfill result: {created} trades created")
            
            # Check current TradeJournal count after
            after_res = await db.execute(select(TradeJournalModel).where(TradeJournalModel.user_id == trader_id))
            after_trades = after_res.scalars().all()
            print(f"   After backfill: {len(after_trades)} TradeJournal records")
            
            if created > 0:
                print("\n✅ Backfill successful!")
                print("\nTrades created:")
                for trade in after_trades[-created:]:
                    print(f"   - {trade.symbol} {trade.side} Entry:{trade.entry_price} Exit:{trade.exit_price} PnL:{trade.pnl}")
            else:
                print("\n⚠️  Backfill returned 0 trades created")
        except Exception as e:
            print(f"❌ Error importing backfill function: {e}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_backfill())
