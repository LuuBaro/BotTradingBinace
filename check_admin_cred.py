
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select
from packages.shared.models import User, UserCredential

async def check_admin_cred():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(User).where(User.username == 'admin'))
        user = res.scalar_one_or_none()
        if not user:
            print("Admin not found")
            return
        res = await db.execute(select(UserCredential).where(UserCredential.user_id == user.id))
        cred = res.scalar_one_or_none()
        print(f"Admin has cred: {cred is not None}")
        if cred:
            print(f"Admin AI provider: {cred.ai_provider}")
            print(f"Admin AI model: {cred.ai_model}")

if __name__ == "__main__":
    asyncio.run(check_admin_cred())
