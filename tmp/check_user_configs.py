
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import BotConfig, User
from sqlalchemy import select

async def check():
    async with AsyncSessionFactory() as session:
        # Check users
        print("--- Users ---")
        u_res = await session.execute(select(User.id, User.username))
        for uid, uname in u_res:
            print(f"ID={uid}, Username={uname}")
            
        # Check configs
        print("\n--- BotConfigs ---")
        c_res = await session.execute(select(BotConfig.id, BotConfig.user_id, BotConfig.is_active))
        for cid, cuid, is_active in c_res:
            print(f"ID={cid}, UserID={cuid}, Active={is_active}")

if __name__ == "__main__":
    asyncio.run(check())
