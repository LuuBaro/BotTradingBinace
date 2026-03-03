
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select
from packages.shared.models import User, UserCredential
from packages.shared.encryption import decrypt_key

async def check_trader_keys():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(User).where(User.username == "trader"))
        user = res.scalar_one_or_none()
        if not user:
            print("Trader not found")
            return
            
        res = await db.execute(select(UserCredential).where(UserCredential.user_id == user.id))
        cred = res.scalar_one_or_none()
        if cred:
            print(f"Trader Key: {decrypt_key(cred.binance_api_key) if cred.binance_api_key else 'None'}")
            print(f"Trader Secret: {decrypt_key(cred.binance_api_secret) if cred.binance_api_secret else 'None'}")
            print(f"Use Testnet: {cred.use_testnet}")
        else:
            print("No credentials found for trader")

if __name__ == "__main__":
    asyncio.run(check_trader_keys())
