#!/usr/bin/env python3
"""Debug why backfill from orders isn't working"""
import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, Order, TradeJournal
from packages.shared.logger import logger


async def debug():
    async with AsyncSessionFactory() as db:
        # Get trader user
        user_res = await db.execute(select(User).where(User.role == "trader"))
        trader = user_res.scalar()
        
        if not trader:
            logger.error("No trader found")
            return
        
        user_id = trader.id
        logger.info(f"\n=== DEBUG USER: {trader.username} ({user_id[:8]}...) ===\n")
        
        # Check Orders
        orders_res = await db.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.created_at)
        )
        orders = orders_res.scalars().all()
        logger.info(f"✓ Total Orders for user: {len(orders)}")
        
        for o in orders:
            logger.info(f"  - ID={o.id}, Symbol={o.symbol}, Side={o.side}, Status={o.status}, Qty={o.quantity}, AvgPrice={o.avg_price}, FilledQty={o.filled_qty}")
        
        # Group by symbol
        by_symbol = {}
        for o in orders:
            by_symbol.setdefault(o.symbol, []).append(o)
        
        logger.info(f"\n✓ Orders by Symbol:")
        for sym, items in by_symbol.items():
            logger.info(f"  {sym}: {len(items)} orders")
            for o in items:
                logger.info(f"    - {o.side} @ {o.avg_price} (qty={o.filled_qty}, status={o.status})")
        
        # Check if pairing is possible
        logger.info(f"\n✓ Can create trades from pairs?")
        for symbol, items in by_symbol.items():
            buys = [o for o in items if (o.side or "").upper() == "BUY"]
            sells = [o for o in items if (o.side or "").upper() == "SELL"]
            logger.info(f"  {symbol}: {len(buys)} BUYs × {len(sells)} SELLs = {min(len(buys), len(sells))} potential trades")
        
        # Check TradeJournal
        trades_res = await db.execute(
            select(TradeJournal).where(TradeJournal.user_id == user_id)
        )
        trades = trades_res.scalars().all()
        logger.info(f"\n✓ Current TradeJournal records: {len(trades)}")
        for t in trades:
            logger.info(f"  - {t.symbol} {t.side.upper()}: E=${t.entry_price} X=${t.exit_price} P&L=${t.pnl:.2f} (trace={t.trace_id[:20]}...)")


if __name__ == "__main__":
    asyncio.run(debug())
