"""
Fix lỗi OpenAI 404 - chuyển sang model chính xác
"""
import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential, User
from sqlalchemy import select

async def fix_openai_model():
    """Chuyển sang model OpenAI đúng"""
    async with AsyncSessionFactory() as session:
        # Get admin
        admin_result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin = admin_result.scalar_one_or_none()
        
        if not admin:
            print("❌ Không tìm thấy admin")
            return
        
        # Get credentials
        creds_result = await session.execute(
            select(UserCredential).where(UserCredential.user_id == admin.id)
        )
        creds = creds_result.scalar_one_or_none()
        
        if not creds:
            return
        
        print(f"Hiện tại: {creds.ai_model}")
        
        # Các model OpenAI có sẵn:
        # - gpt-4o (newest, most capable)
        # - gpt-4o-mini (cheaper, faster)  
        # - gpt-4-turbo (older, may not exist)
        # - gpt-3.5-turbo (cheap, fast)
        
        old_model = creds.ai_model
        creds.ai_model = "gpt-4o-mini"  # Model rẻ và nhanh nhất
        
        await session.commit()
        
        print(f"✅ Đã chuyển: {old_model} → {creds.ai_model}")
        print(f"\n👉 Restart worker:")
        print(f"   Get-Process python | Where-Object {{(Get-CimInstance Win32_Process -Filter \"ProcessId = `$(`$_.Id)\").CommandLine -match 'apps.worker.main'}} | Stop-Process -Force")
        print(f"   python -m apps.worker.main")

asyncio.run(fix_openai_model())
