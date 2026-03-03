#!/usr/bin/env python
"""Revert admin to Mock provider"""
import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, UserCredential

async def main():
    async with AsyncSessionFactory() as session:
        # Get admin user
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("❌ Admin user not found")
            return
        
        # Get admin credentials
        cred_result = await session.execute(
            select(UserCredential).where(UserCredential.user_id == admin.id)
        )
        cred = cred_result.scalar_one_or_none()
        
        if cred:
            cred.ai_provider = "mock"
            cred.ai_model = "mock-model"
            cred.ai_api_key = None
            await session.commit()
            print("✅ Admin reverted to Mock provider")
            print("   OpenAI API had insufficient quota")
            print("   System now running reliably with Mock AI")
        else:
            print("❌ Admin credentials not found")

asyncio.run(main())
