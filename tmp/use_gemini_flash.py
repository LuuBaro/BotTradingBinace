"""
Update Gemini model to gemini-1.5-flash
"""
import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential, User
from sqlalchemy import select

async def update_model():
    """Update admin user to gemini-1.5-flash"""
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
        
        old_model = creds.ai_model
        creds.ai_model = "gemini-1.5-flash"
        
        await session.commit()
        
        print(f"✅ Model updated: {old_model} → gemini-1.5-flash")
        print(f"   Admin user now uses: gemini-1.5-flash")
        print(f"\n👉 Restart worker to apply changes")

asyncio.run(update_model())
