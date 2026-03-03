#!/usr/bin/env python
"""Configure admin user to use OpenAI GPT-4o"""
import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, UserCredential
from packages.shared.encryption import encrypt_key

async def main():
    api_key = "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"
    
    async with AsyncSessionFactory() as session:
        # Get admin user
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("❌ Admin user not found")
            return
        
        print(f"📝 Found admin user: {admin.username} ({admin.id})")
        
        # Get or create admin credentials
        cred_result = await session.execute(
            select(UserCredential).where(UserCredential.user_id == admin.id)
        )
        cred = cred_result.scalar_one_or_none()
        
        if cred:
            # Update existing
            print(f"📝 Updating existing credential record...")
            cred.ai_provider = "openai"
            cred.ai_api_key = encrypt_key(api_key)
            cred.ai_model = "gpt-4o"
        else:
            # Create new
            print(f"📝 Creating new credential record...")
            cred = UserCredential(
                user_id=admin.id,
                ai_provider="openai",
                ai_api_key=encrypt_key(api_key),
                ai_model="gpt-4o"
            )
            session.add(cred)
        
        await session.commit()
        print(f"✅ Admin configured: OpenAI GPT-4o")
        print(f"   • Provider: openai")
        print(f"   • Model: gpt-4o")
        print(f"   • API Key: {api_key[:20]}...{api_key[-10:]}")

asyncio.run(main())
