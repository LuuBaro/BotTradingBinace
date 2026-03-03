
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select
from packages.shared.models import User, UserCredential

async def check_trader_model():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(User).where(User.username == 'trader'))
        user = res.scalar_one_or_none()
        if not user:
            print("Trader not found")
            return
        res = await db.execute(select(UserCredential).where(UserCredential.user_id == user.id))
        cred = res.scalar_one_or_none()
        print(f"Trader AI Provider: {cred.ai_provider if cred else 'N/A'}")
        print(f"Trader AI Model: {cred.ai_model if cred else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(check_trader_model())
