#!/usr/bin/env python3
"""Test learning endpoint directly"""
import asyncio
import sys
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/api'))

from shared.models import User, TradeJournal
from shared.learning_agent import LearningAgent

async def test():
    DATABASE_URL = "sqlite+aiosqlite:///./data/trading.db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get trader
        trader_res = await db.execute(select(User).where(User.username == "trader"))
        trader = trader_res.scalar_one_or_none()
        if not trader:
            print("Trader not found")
            return
        
        trader_id = trader.id
        print(f"Testing learning for trader: {trader_id}\n")
        
        # Get trades
        trades_res = await db.execute(select(TradeJournal).where(TradeJournal.user_id == trader_id))
        trades = trades_res.scalars().all()
        print(f"📊 Available trades: {len(trades)}")
        
        if len(trades) < 5:
            print(f"❌ Not enough trades for analysis (need 5, have {len(trades)})")
            return
        
        # Create learning agent
        print("\n🔄 Creating LearningAgent...")
        agent = LearningAgent(trades=trades)
        
        # Run analysis
        print("🔄 Running analysis...")
        report = agent.analyze()
        
        print("\n✅ Learning Analysis Complete!")
        print(f"\n📈 Report:")
        print(f"   Trades Analyzed: {report.trades_analyzed}")
        print(f"   Win Rate: {report.stats.win_rate:.1%}" if report.stats else "   Win Rate: N/A")
        print(f"   Profit Factor: {report.stats.profit_factor:.2f}" if report.stats else "   Profit Factor: N/A")
        print(f"   Max Drawdown: {report.stats.max_drawdown:.1f}%" if report.stats else "   Max Drawdown: N/A")
        print(f"   Total PnL: {sum(t.pnl for t in trades):.2f}")
        print(f"\n   Top 3 Patterns Identified:")
        for i, pattern in enumerate(report.losing_patterns[:3], 1):
            print(f"     {i}. {pattern.pattern_name}: {pattern.description}")

if __name__ == "__main__":
    asyncio.run(test())
