
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Decision, TradeJournal, TraderContext, Event

async def status_check():
    async with AsyncSessionFactory() as session:
        from sqlalchemy import text
        
        counts = {}
        for table in ["decisions", "trade_journal", "trader_contexts", "events", "positions", "orders"]:
            res = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = res.scalar()
            
        print(f"=== DATABASE STATUS ===")
        for table, count in counts.items():
            print(f"{table:15} : {count}")
            
        # Get latest event errors
        print("\n=== LATEST ERROR EVENTS ===")
        res = await session.execute(text("SELECT message, timestamp FROM events WHERE level='ERROR' ORDER BY timestamp DESC LIMIT 5"))
        for msg, ts in res.all():
            print(f"[{ts}] {msg}")

        # Get latest wins/losses details to analyze why
        print("\n=== LATEST TRADE RESULTS ===")
        res = await session.execute(text("SELECT symbol, side, pnl, exit_reason, closed_at FROM trade_journal ORDER BY closed_at DESC LIMIT 10"))
        for row in res.all():
            print(f"[{row.closed_at}] {row.symbol} {row.side} | PNL: ${row.pnl:.4f} | EXIT: {row.exit_reason}")

if __name__ == "__main__":
    asyncio.run(status_check())
