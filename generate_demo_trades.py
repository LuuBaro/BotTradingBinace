#!/usr/bin/env python3
"""
Quick script to generate demo trades for Learning analysis testing
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, func
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import TradeJournal
from packages.shared.logger import logger


async def create_demo_trades(num_trades: int = 2):
    """Create demo trades to reach 5 for Learning analysis"""
    from sqlalchemy import select, func
    
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(func.count(TradeJournal.id)))
        count = result.scalar() or 0
        logger.info(f"📊 Current trades: {count}")
        
        new_trades = []
        base_time = datetime.utcnow()
        
        for i in range(num_trades):
            trade = TradeJournal(
                trace_id=f"demo_trade_{count + i + 1}",
                symbol="BTCUSDT",
                side="long" if i % 2 == 0 else "short",
                entry_price=49000 + (i * 100),
                exit_price=50000 + (i * 100),
                pnl=100 + (i * 50),  # Winning trades
                rr=1.5,
                holding_time=300 + (i * 100),
                regime="trending" if i % 2 == 0 else "consolidation",
                exit_reason="MANUAL",
                features_json={
                    "entry_time": (base_time - timedelta(hours=2-i)).isoformat(),
                    "exit_time": (base_time - timedelta(hours=1-i)).isoformat(),
                    "entry_quantity": 0.1,
                    "entry_leverage": 2.0,
                    "volatility_percentile": 60 - (i * 5),
                    "bid_ask_spread_pips": 0.5,
                    "funding_rate": 0.0001,
                    "position_pct": 0.3,
                    "stop_loss_pips": 50,
                    "take_profit_pips": 100,
                    "confidence": 0.65 + (i * 0.05),
                    "ai_model": "demo",
                    "prompt_pack_version": 1,
                    "pnl_pct": 0.02 + (i * 0.01),
                    "max_drawdown": 0.01,
                    "max_runup": 0.03,
                    "exit_reason": "MANUAL",
                },
                decision_json={
                    "regime": "trending" if i % 2 == 0 else "consolidation",
                    "action": "close",
                    "symbol": "BTCUSDT",
                    "side": "long" if i % 2 == 0 else "short",
                    "confidence": 0.65 + (i * 0.05),
                    "rationale": f"Demo trade for Learning testing - {i+1}"
                },
                closed_at=base_time - timedelta(hours=1-i),
            )
            new_trades.append(trade)
            session.add(trade)
        
        await session.commit()
        logger.info(f"✅ Generated {num_trades} demo trades")
        
        # Verify
        result = await session.execute(select(func.count(TradeJournal.id)))
        new_count = result.scalar()
        logger.info(f"📊 Total trades now: {new_count}")


if __name__ == "__main__":
    asyncio.run(create_demo_trades(2))
