#!/usr/bin/env python
"""Configure admin and trader users with Google Gemini API"""
import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, UserCredential
from packages.shared.encryption import encrypt_key

async def main():
    api_keys = {
        "admin": "AIzaSyCnN-7s9XhMj9rwyaGbKCV9J51uflEm8d0",
        "trader": "AIzaSyCBZkZpw5JTfpENKcTjR8jg7R6Z0yQweRM"
    }
    
    async with AsyncSessionFactory() as session:
        for username, api_key in api_keys.items():
            # Get user
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ {username.upper()} user not found")
                continue
            
            print(f"📝 Configuring {username.upper()} user...")
            
            # Get or create credentials
            cred_result = await session.execute(
                select(UserCredential).where(UserCredential.user_id == user.id)
            )
            cred = cred_result.scalar_one_or_none()
            
            if cred:
                # Update existing
                cred.ai_provider = "gemini"
                cred.ai_api_key = encrypt_key(api_key)
                cred.ai_model = "gemini-1.5-pro"
            else:
                # Create new
                cred = UserCredential(
                    user_id=user.id,
                    ai_provider="gemini",
                    ai_api_key=encrypt_key(api_key),
                    ai_model="gemini-1.5-pro"
                )
                session.add(cred)
            
            await session.commit()
            print(f"✅ {username.upper()}: Gemini 1.5 Pro configured")
            print(f"   • Provider: gemini")
            print(f"   • Model: gemini-1.5-pro")
            print(f"   • API Key: {api_key[:15]}...{api_key[-10:]}")
            print()

asyncio.run(main())
