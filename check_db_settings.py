import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select, text

async def check_settings():
    async with AsyncSessionFactory() as session:
        # Check if BotConfig table has api settings
        result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result.fetchall()]
        print("Tables:", tables)
        
        # Check if there's a bot_config with binance keys
        if 'bot_config' in tables:
            result = await session.execute(text("SELECT * FROM bot_config LIMIT 1"))
            rows = result.fetchall()
            if rows:
                columns = result.keys()
                print("\nbot_config columns:", list(columns))
                print("First row:", rows[0])
        
        # Check .env file directly
        from packages.shared.config import settings
        print("\n=== Current Settings ===")
        print(f"Binance API Key: {settings.binance_api_key}")
        print(f"Binance API Secret: {settings.binance_api_secret}")
        print(f"Binance Testnet: {settings.binance_testnet}")

if __name__ == "__main__":
    asyncio.run(check_settings())
