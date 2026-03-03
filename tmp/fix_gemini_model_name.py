#!/usr/bin/env python
"""Fix Gemini model name to use correct API version"""
import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, UserCredential

async def main():
    # Update to use gemini-pro which is available in v1 API
    model_name = "gemini-pro"
    
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(UserCredential))
        creds = result.scalars().all()
        
        for cred in creds:
            if cred.ai_provider == "gemini":
                cred.ai_model = model_name
                print(f"✅ Updated: {model_name}")
        
        await session.commit()
        print()
        print("🔄 Using Gemini Pro (stable, free tier compatible)")
        print("   For gemini-1.5-pro: May need Gemini 2.0 API or premium tier")

asyncio.run(main())
