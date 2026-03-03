import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, BotConfig
from sqlalchemy import select

async def check_bot_configs():
    async with AsyncSessionFactory() as session:
        users_result = await session.execute(select(User))
        users = users_result.scalars().all()
        
        print("[Bot Configuration Status]")
        for user in users:
            configs_result = await session.execute(
                select(BotConfig).where(BotConfig.user_id == user.id)
            )
            configs = configs_result.scalars().all()
            print(f"\nUser: {user.username} (ID: {user.id})")
            if not configs:
                print(f"  [ERROR] No BotConfig found!")
            else:
                for config in configs:
                    print(f"  - ID: {config.id}")
                    print(f"    is_active: {config.is_active}")
                    print(f"    active_prompt_pack_id: {config.active_prompt_pack_id}")
                    print(f"    symbols: {config.symbols_json}")

asyncio.run(check_bot_configs())
