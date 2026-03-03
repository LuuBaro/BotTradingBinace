
import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import BotConfig, User
from sqlalchemy import select, update

async def fix_configs():
    async with AsyncSessionFactory() as session:
        # Get actual admin ID
        res = await session.execute(select(User).where(User.username == "admin"))
        admin = res.scalar_one_or_none()
        
        if admin:
            # Update all BotConfigs with user_id="admin" to use the UUID
            await session.execute(
                update(BotConfig)
                .where(BotConfig.user_id == "admin")
                .values(user_id=admin.id)
            )
            print(f"Updated BotConfigs to use admin ID: {admin.id}")
        
        await session.commit()
    print("Fix complete.")

if __name__ == "__main__":
    asyncio.run(fix_configs())
