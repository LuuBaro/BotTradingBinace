import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select, desc
from packages.shared.models import BotConfig
from packages.shared.config import settings

async def check():
    print("\n=== CHECKING SETTINGS ===")
    print(f"settings.binance_api_key: {settings.binance_api_key[:20]}...")
    print(f"settings.binance_api_secret: {settings.binance_api_secret[:20]}...")
    print(f"Has keys: {bool(settings.binance_api_key and settings.binance_api_secret)}")
    
    mode_from_logic = "Live" if (settings.binance_api_key and settings.binance_api_secret) else "Demo"
    print(f"\nMode từ logic: {mode_from_logic}")
    
    print("\n=== CHECKING DATABASE ===")
    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(BotConfig).where(BotConfig.is_active == True).order_by(desc(BotConfig.id)).limit(1)
        )
        config = result.scalars().first()
        
        if config:
            print(f"Found BotConfig:")
            print(f"  ID: {config.id}")
            print(f"  env: {config.env}")
            print(f"  version: {config.version}")
            print(f"  is_active: {config.is_active}")
            print(f"  created_at: {config.created_at}")
        else:
            print("No active BotConfig found!")
            print("\nĐây là lý do! API sẽ return fallback mode='Demo'")
            print("Cần tạo BotConfig mới hoặc set is_active=True")

if __name__ == "__main__":
    asyncio.run(check())
