"""
Setup Gemini cho admin user
"""
import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential, User
from packages.shared.encryption import encrypt_key
from sqlalchemy import select

async def setup_gemini():
    """Cấu hình Gemini cho admin"""
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
        
        # Setup Gemini
        gemini_key = "AIzaSyC3D5dTAUZuUN_401vSPRL54-Ix24aSAYY"
        
        print(f"\n⚙️  Cấu hình hiện tại:")
        print(f"   Provider: {creds.ai_provider}")
        print(f"   Model: {creds.ai_model}")
        
        # Update to Gemini
        old_provider = creds.ai_provider
        old_model = creds.ai_model
        
        creds.ai_provider = "gemini"
        creds.ai_model = "gemini-1.5-pro"
        creds.ai_api_key = encrypt_key(gemini_key)
        
        await session.commit()
        
        print(f"\n✅ Đã cấu hình Gemini!")
        print(f"   Provider: {old_provider} → {creds.ai_provider}")
        print(f"   Model: {old_model} → {creds.ai_model}")
        print(f"   API Key: AIzaSyC3D5dTAUZuUN_401vSPRL54-Ix24aSAYY (encrypted)")
        
        print(f"\n⚡ Giờ bạn có:")
        print(f"   ✓ .env: SELECTED_LLM='gemini'")
        print(f"   ✓ Database: admin user → Gemini")
        print(f"   ✓ API Key: {gemini_key[:20]}...")
        
        print(f"\n👉 Restart worker:")
        print(f"   Get-Process python | Where-Object {{...")
        print(f"   CommandLine -match 'apps.worker.main'}} | Stop-Process -Force")
        print(f"   python -m apps.worker.main")

asyncio.run(setup_gemini())
