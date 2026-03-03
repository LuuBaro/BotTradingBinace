"""Check all user credentials"""
import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential, User

async def check_all_creds():
    async with AsyncSessionFactory() as session:
        # Get all active users
        users_result = await session.execute(
            select(User).where(User.is_active == True)
        )
        users = users_result.scalars().all()
        
        print(f"📊 Active users: {len(users)}")
        for user in users:
            print(f"\n👤 User: {user.id} ({user.role})")
            
            # Check credentials
            cred_result = await session.execute(
                select(UserCredential).where(UserCredential.user_id == user.id)
            )
            cred = cred_result.scalar_one_or_none()
            
            if cred and cred.ai_api_key:
                print(f"   AI Provider: {cred.ai_provider}")
                print(f"   AI Model: {cred.ai_model}")
                print(f"   Has API Key: ✓")
            else:
                print(f"   AI Config: None (uses .env defaults)")

if __name__ == "__main__":
    asyncio.run(check_all_creds())
