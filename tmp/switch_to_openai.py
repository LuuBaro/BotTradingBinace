"""
Script để chuyển LLM provider sang OpenAI hoặc Gemini
Sử dụng khi Claude hết credit
"""
import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential, User
from sqlalchemy import select

async def switch_llm_provider():
    """Chuyển tất cả users sang OpenAI"""
    async with AsyncSessionFactory() as session:
        # Get all users
        users_result = await session.execute(select(User))
        users = users_result.scalars().all()
        
        print("\n=== Chuyển LLM Provider ===\n")
        
        for user in users:
            # Get credentials
            creds_result = await session.execute(
                select(UserCredential).where(UserCredential.user_id == user.id)
            )
            creds = creds_result.scalar_one_or_none()
            
            if creds:
                old_provider = creds.llm_provider
                
                # Kiểm tra xem có OpenAI key không
                if creds.openai_api_key and len(creds.openai_api_key) > 10:
                    creds.llm_provider = "openai"
                    creds.llm_model = "gpt-4-turbo-preview"
                    print(f"✓ {user.username}: {old_provider} → OpenAI (gpt-4-turbo)")
                # Nếu không có OpenAI, thử Gemini
                elif creds.gemini_api_key and len(creds.gemini_api_key) > 10:
                    creds.llm_provider = "gemini"
                    creds.llm_model = "gemini-1.5-pro"
                    print(f"✓ {user.username}: {old_provider} → Gemini (1.5 pro)")
                else:
                    print(f"⚠ {user.username}: Không có OpenAI/Gemini key, giữ nguyên {old_provider}")
                    print(f"   Cần set OPENAI_API_KEY hoặc GEMINI_API_KEY trong .env")
        
        await session.commit()
        print("\n✅ Đã cập nhật LLM provider cho tất cả users!")
        print("\n👉 Restart worker để áp dụng thay đổi:")
        print("   Stop-Process -Name python -Force")
        print("   python -m apps.worker.main")

asyncio.run(switch_llm_provider())
