#!/usr/bin/env python
"""Verify signals created in database"""
import asyncio
import sys
from sqlalchemy import select, desc
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Signal

async def main():
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Signal).order_by(desc(Signal.timestamp)).limit(100))
        signals = result.scalars().all()
        
        print(f"✅ Total signals: {len(signals)}")
        if signals:
            print(f"\nLatest 10 signals:")
            for sig in signals[:10]:
                prob = float(sig.probability) if isinstance(sig.probability, str) else sig.probability
                print(f"  {sig.symbol}: {sig.side} @ {sig.entry_zone} ({sig.status}) - Prob: {prob:.2f}")
        else:
            print("  [No signals yet...]")

if __name__ == "__main__":
    asyncio.run(main())
