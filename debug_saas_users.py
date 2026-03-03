
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select
from packages.shared.models import User, BotConfig, UserCredential

async def debug_users():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(User))
        users = res.scalars().all()
        print(f"Found {len(users)} users:")
        for u in users:
            print(f"- {u.username} (ID: {u.id}, Role: {u.role})")
            
            # Check active config
            cfg_res = await db.execute(select(BotConfig).where(BotConfig.user_id == u.id, BotConfig.is_active == True))
            cfgs = cfg_res.scalars().all()
            print(f"  Active BotConfigs: {len(cfgs)}")
            for c in cfgs:
                print(f"    - Version: {c.version}, Active: {c.is_active}")
            
            # Check credentials
            cred_res = await db.execute(select(UserCredential).where(UserCredential.user_id == u.id))
            cred = cred_res.scalar_one_or_none()
            if cred:
                print(f"  Credentials: Found (API key present: {bool(cred.binance_api_key)})")
            else:
                print(f"  Credentials: NOT FOUND")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(debug_users())
