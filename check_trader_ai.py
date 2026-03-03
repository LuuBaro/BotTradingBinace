
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select
from packages.shared.models import User, UserCredential
from packages.shared.encryption import decrypt_key

async def check_trader_cred():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(User).where(User.username == 'trader'))
        user = res.scalar_one_or_none()
        if not user:
            print("Trader not found")
            return
        res = await db.execute(select(UserCredential).where(UserCredential.user_id == user.id))
        cred = res.scalar_one_or_none()
        if cred:
            print(f"Trader AI Provider: {cred.ai_provider}")
            print(f"Trader AI Model: {cred.ai_model}")
            key = decrypt_key(cred.ai_api_key) if cred.ai_api_key else "None"
            print(f"Trader AI Key Length: {len(key)}")
            print(f"Trader AI Key Start: {key[:10]}...")
            
            # Compare with .env key
            import os
            from dotenv import load_dotenv
            load_dotenv()
            env_key = os.getenv('BOT_OPENAI_API_KEY', '')
            print(f"Env Key Start: {env_key[:10]}...")
            print(f"Keys match: {key == env_key}")

if __name__ == "__main__":
    asyncio.run(check_trader_cred())
