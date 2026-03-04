"""
Check Worker Activity & Errors
Kiểm tra tại sao AI không gọi OpenAI nữa
"""
import asyncio
from datetime import datetime, timedelta
from packages.shared.database import AsyncSessionFactory, init_db
from packages.shared.models import Event
from sqlalchemy import select, desc


async def check_errors():
    await init_db()
    
    async with AsyncSessionFactory() as session:
        # Get errors from last 30 minutes
        since = datetime.utcnow() - timedelta(minutes=30)
        
        result = await session.execute(
            select(Event)
            .where(Event.timestamp >= since)
            .order_by(desc(Event.timestamp))
        )
        events = result.scalars().all()
        
        print("\n" + "="*70)
        print("🔍 WORKER ERRORS (Last 30 mins)")
        print("="*70)
        
        errors = [e for e in events if e.level in ['ERROR', 'WARNING']]
        
        if not errors:
            print("✅ No errors found in last 30 minutes")
            print("\n📊 Recent Events:")
            for evt in events[:20]:
                ts = evt.timestamp.strftime("%H:%M:%S")
                print(f"  {ts} [{evt.level:10s}] {evt.code:25s} - {evt.message[:80]}")
        else:
            print(f"❌ Found {len(errors)} errors:")
            for err in errors[:15]:
                ts = err.timestamp.strftime("%H:%M:%S")
                print(f"\n  {ts} [{err.level}]")
                print(f"    Code: {err.code}")
                print(f"    Message: {err.message}")
                if err.data_json:
                    print(f"    Data: {err.data_json}")


if __name__ == "__main__":
    asyncio.run(check_errors())
