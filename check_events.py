
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select
from packages.shared.models import Event

async def check_events():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(Event).order_by(Event.id.desc()).limit(20))
        events = res.scalars().all()
        print(f"Latest 20 events:")
        for e in events:
            user_id = e.user_id if hasattr(e, 'user_id') else "global"
            print(f"[{e.timestamp}] {e.level} | {e.code} | User: {user_id} | {e.message}")

if __name__ == "__main__":
    asyncio.run(check_events())
