"""
Fix model name cho Gemini - Dùng gemini-pro thay vì gemini-1.5-pro
"""
import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential, User
from sqlalchemy import select

async def fix_gemini_model():
    """Chuyển sang model name đúng"""
    async with AsyncSessionFactory() as session:
        admin_result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin = admin_result.scalar_one_or_none()
        
        if not admin:
            return
        
        creds_result = await session.execute(
            select(UserCredential).where(UserCredential.user_id == admin.id)
        )
        creds = creds_result.scalar_one_or_none()
        
        if not creds:
            return
        
        # Gemini models đã test:
        # - gemini-pro (stable)
        # - gemini-1.0-pro (stable)
        # - gemini-1.5-pro (latest, nhưng API có thể khác tên)
        
        old_model = creds.ai_model
        creds.ai_model = "gemini-pro"  # Model mặc định hoạt động tốt
        
        await session.commit()
        
        print(f"✅ Đã chuyển model: {old_model} → {creds.ai_model}")
        print(f"\nRestart worker:")
        print(f"   Get-Process python | Where-Object {{...}} | Stop-Process")
        print(f"   python -m apps.worker.main")

asyncio.run(fix_gemini_model())
