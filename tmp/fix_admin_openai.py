"""
Script chuyển admin user sang dùng OpenAI thay vì Claude
"""
import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential, User
from packages.shared.encryption import encrypt_key, decrypt_key
from packages.shared.config import settings
from sqlalchemy import select

async def fix_admin_llm():
    """Chuyển admin sang OpenAI"""
    async with AsyncSessionFactory() as session:
        # Get admin user
        admin_result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin = admin_result.scalar_one_or_none()
        
        if not admin:
            print("❌ Không tìm thấy admin user")
            return
        
        # Get admin credentials
        creds_result = await session.execute(
            select(UserCredential).where(UserCredential.user_id == admin.id)
        )
        creds = creds_result.scalar_one_or_none()
        
        if not creds:
            print("❌ Admin chưa có UserCredential")
            return
        
        print(f"\n⚙️  Cấu hình hiện tại:")
        print(f"   Provider: {creds.ai_provider}")
        print(f"   Model: {creds.ai_model}")
        
        # Lấy OpenAI key từ .env
        openai_key = settings.bot_openai_api_key
        if not openai_key:
            print("\n❌ Không có OPENAI_API_KEY trong .env!")
            print("   Thêm vào file .env:")
            print("   BOT_OPENAI_API_KEY='sk-proj-...'")
            return
        
        # Update credentials
        old_provider = creds.ai_provider
        creds.ai_provider = "openai"
        creds.ai_model = "gpt-4-turbo-preview"  # Hoặc gpt-4o-mini
        creds.ai_api_key = encrypt_key(openai_key)
        
        await session.commit()
        
        print(f"\n✅ Đã chuyển admin: {old_provider} → OpenAI")
        print(f"   Model: {creds.ai_model}")
        print(f"   API Key: {openai_key[:10]}...")
        print(f"\n👉 Restart worker để áp dụng:")
        print(f"   Get-Process python | Where-Object {{(Get-CimInstance Win32_Process -Filter \"ProcessId = `$(`$_.Id)\").CommandLine -match 'apps.worker.main'}} | Stop-Process -Force")
        print(f"   python -m apps.worker.main")

asyncio.run(fix_admin_llm())
