"""Fix all users to use Mock provider"""
import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential, User

async def fix_all_to_mock():
    async with AsyncSessionFactory() as session:
        # Get all active users
        users_result = await session.execute(
            select(User).where(User.is_active == True)
        )
        users = users_result.scalars().all()
        
        print(f"🔧 Fixing {len(users)} active users to use Mock provider...\n")
        
        for user in users:
            cred_result = await session.execute(
                select(UserCredential).where(UserCredential.user_id == user.id)
            )
            cred = cred_result.scalar_one_or_none()
            
            if cred:
                old_provider = cred.ai_provider
                old_model = cred.ai_model
                
                cred.ai_provider = "mock"
                cred.ai_model = "mock-model"
                cred.ai_api_key = None  # Clear invalid keys
                
                session.add(cred)
                
                print(f"✓ User {user.id} ({user.role})")
                print(f"  {old_provider}/{old_model} → mock/mock-model")
        
        await session.commit()
        print(f"\n✅ All users updated to Mock provider!")

if __name__ == "__main__":
    asyncio.run(fix_all_to_mock())
