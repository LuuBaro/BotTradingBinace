
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select, update
from packages.shared.models import User, UserCredential

async def fix_trader_model():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(User).where(User.username == 'trader'))
        user = res.scalar_one_or_none()
        if not user:
            print("Trader not found")
            return
            
        await db.execute(
            update(UserCredential)
            .where(UserCredential.user_id == user.id)
            .values(ai_model='gpt-4o-mini')
        )
        await db.commit()
        print("Updated trader AI model to gpt-4o-mini")

if __name__ == "__main__":
    asyncio.run(fix_trader_model())
