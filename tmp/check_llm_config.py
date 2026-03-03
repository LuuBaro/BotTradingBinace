import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential, User
from packages.shared.encryption import decrypt_key
from sqlalchemy import select

async def check_llm_config():
    """Kiểm tra cấu hình LLM của mỗi user"""
    async with AsyncSessionFactory() as session:
        users_result = await session.execute(select(User))
        users = users_result.scalars().all()
        
        print("\n=== Cấu hình LLM hiện tại ===\n")
        
        for user in users:
            creds_result = await session.execute(
                select(UserCredential).where(UserCredential.user_id == user.id)
            )
            creds = creds_result.scalar_one_or_none()
            
            if creds:
                print(f"User: {user.username}")
                print(f"  AI Provider: {creds.ai_provider}")
                print(f"  AI Model: {creds.ai_model}")
                if creds.ai_api_key:
                    try:
                        decrypted = decrypt_key(creds.ai_api_key)
                        print(f"  API Key: {'✓ Set (' + decrypted[:10] + '...)'}")
                    except:
                        print(f"  API Key: ✗ Invalid/Cannot decrypt")
                else:
                    print(f"  API Key: ✗ Not set (sẽ dùng từ .env)")
                print()
            else:
                print(f"User: {user.username}")
                print(f"  ⚠ Không có UserCredential (sẽ dùng settings từ .env)")
                print()

asyncio.run(check_llm_config())
