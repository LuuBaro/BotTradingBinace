
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select
from packages.shared.models import User, BotConfig

async def debug_active_users():
    async with AsyncSessionFactory() as db:
        res = await db.execute(
            select(User).join(BotConfig, User.id == BotConfig.user_id).where(BotConfig.is_active == True).distinct()
        )
        users = res.scalars().all()
        print(f"Active users in worker loop: {len(users)}")
        for u in users:
            print(f"- {u.username} ({u.id})")

if __name__ == "__main__":
    asyncio.run(debug_active_users())
