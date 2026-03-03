
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select, update
from packages.shared.models import UserCredential

async def fix_all_models():
    async with AsyncSessionFactory() as db:
        await db.execute(
            update(UserCredential)
            .where(UserCredential.ai_model == 'gpt-4')
            .values(ai_model='gpt-4o-mini')
        )
        await db.commit()
        print("Updated all users using 'gpt-4' to 'gpt-4o-mini'")

if __name__ == "__main__":
    asyncio.run(fix_all_models())
