"""Quick check if signals are being created"""
import asyncio
from sqlalchemy import select, desc
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Signal

async def check_signals():
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Signal)
            .order_by(desc(Signal.timestamp))
            .limit(10)
        )
        signals = result.scalars().all()
        
        print(f"\n📊 Total signals in database: {len(signals)}")
        
        if signals:
            print("\n🔥 Recent signals:")
            for s in signals:
                print(f"  [{s.status}] {s.symbol} {s.side} | Confidence: {s.probability*100:.1f}% | {s.timestamp}")
                print(f"      Entry: {s.entry_zone}")
                print(f"      {s.rationale[:80]}...")
        else:
            print("❌ No signals found yet. Worker may still be processing...")

if __name__ == "__main__":
    asyncio.run(check_signals())
