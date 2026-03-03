"""
Switch admin user to Mock provider (for testing)
"""
import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, UserCredential
from sqlalchemy import select

async def switch_to_mock():
    """Update admin user to mock provider"""
    async with AsyncSessionFactory() as session:
        # Get admin user
        admin_result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin = admin_result.scalar_one_or_none()
        
        if not admin:
            print("❌ Không tìm thấy admin user")
            return
        
        # Get credentials
        creds_result = await session.execute(
            select(UserCredential).where(UserCredential.user_id == admin.id)
        )
        creds = creds_result.scalar_one_or_none()
        
        if not creds:
            print("❌ Admin chưa có UserCredential")
            return
        
        old_provider = creds.ai_provider
        old_model = creds.ai_model
        
        creds.ai_provider = "mock"
        creds.ai_model = "mock-v1"
        
        await session.commit()
        
        print(f"✅ Đã chuyển sang Mock provider")
        print(f"   Provider: {old_provider} → mock")
        print(f"   Model: {old_model} → mock-v1")
        print(f"\n👉 Mock provider sẽ generate decisions không cần API key")
        print(f"   Restart worker để áp dụng thay đổi")

asyncio.run(switch_to_mock())
