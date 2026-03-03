"""Check and update admin user to use Mock provider"""
import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential

async def fix_admin_llm():
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(UserCredential)
            .where(UserCredential.user_id == "admin")
        )
        cred = result.scalar_one_or_none()
        
        if cred and cred.ai_api_key:
            print(f"✓ Found admin UserCredential:")
            print(f"  Provider: {cred.ai_provider}")
            print(f"  Model: {cred.ai_model}")
            print(f"  Has API Key: {bool(cred.ai_api_key)}")
            print("\n🔧 Setting to Mock provider...")
            
            cred.ai_provider = "mock"
            cred.ai_model = "mock-model"
            cred.ai_api_key = None  # Clear invalid OpenAI key
            
            session.add(cred)
            await session.commit()
            print("✅ Updated admin to use Mock provider")
        else:
            print("ℹ️ No UserCredential for admin, will use .env settings (already Mock)")

if __name__ == "__main__":
    asyncio.run(fix_admin_llm())
