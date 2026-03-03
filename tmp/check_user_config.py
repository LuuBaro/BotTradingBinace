#!/usr/bin/env python
"""Verify user configurations"""
import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, UserCredential

async def main():
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        print("=" * 60)
        print("🔐 USER CONFIGURATION STATUS")
        print("=" * 60)
        
        for u in users:
            cred_result = await session.execute(
                select(UserCredential).where(UserCredential.user_id == u.id)
            )
            cred = cred_result.scalar_one_or_none()
            
            provider = cred.ai_provider if cred else "unknown"
            model = cred.ai_model if cred else "unknown"
            
            icon = "🟢" if provider == "openai" else "🔵" if provider == "mock" else "⚪"
            
            print(f"\n{icon} {u.username.upper()}")
            print(f"   Provider: {provider}")
            print(f"   Model: {model}")

asyncio.run(main())
