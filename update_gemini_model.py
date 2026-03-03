import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential

async def main():
    model_name = "gemini-2.5-flash"  # Latest available model
    
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(UserCredential))
        creds = result.scalars().all()
        
        count = 0
        for cred in creds:
            if cred.ai_provider == "gemini":
                cred.ai_model = model_name
                count += 1
        
        await session.commit()
        print(f"✅ Updated {count} users to: {model_name}")
        print("   (Latest Gemini model - Free tier compatible)")

asyncio.run(main())
