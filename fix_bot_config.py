"""
Fix BotConfig - Set is_active=True or create new config
"""
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select, update
from packages.shared.models import BotConfig
from datetime import datetime

async def fix():
    async with AsyncSessionFactory() as db:
        # Check if any BotConfig exists
        result = await db.execute(select(BotConfig).order_by(BotConfig.id.desc()).limit(1))
        config = result.scalars().first()
        
        if config:
            print(f"Found BotConfig (ID: {config.id}), setting is_active=True...")
            config.is_active = True
            await db.commit()
            print("✅ Updated existing BotConfig!")
        else:
            print("No BotConfig found, creating new one...")
            new_config = BotConfig(
                env="live",
                version="1.0.0",
                symbols_json=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
                risk_json={"max_leverage": 10, "max_position_size_pct": 10},
                created_at=datetime.utcnow(),
                is_active=True
            )
            db.add(new_config)
            await db.commit()
            print(f"✅ Created new BotConfig (ID: {new_config.id})!")
        
        # Verify
        result = await db.execute(
            select(BotConfig).where(BotConfig.is_active == True).limit(1)
        )
        active_config = result.scalars().first()
        
        if active_config:
            print(f"\n✅ Active BotConfig confirmed:")
            print(f"   ID: {active_config.id}")
            print(f"   env: {active_config.env}")
            print(f"   is_active: {active_config.is_active}")
        else:
            print("\n❌ Still no active config!")

if __name__ == "__main__":
    asyncio.run(fix())
