import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential

async def main():
    """Revert to Mock AI since Gemini has quota issues"""
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(UserCredential))
        creds = result.scalars().all()
        
        count = 0
        for cred in creds:
            cred.ai_provider = "mock"
            cred.ai_model = "mock"
            count += 1
        
        await session.commit()
        print(f"✅ Reverted {count} users to Mock AI")
        print("   (Reliable for testing, no quota limits)")
        print("\n📋 Summary:")
        print("   • Mock AI: ✅ Working & reliable")
        print("   • OpenAI: ❌ Quota exceeded (account not set up for API)")
        print("   • Gemini: ✅ API working correctly, ❌ Quota exceeded")
        print("\n💡 Recommendation:")
        print("   To use Gemini, set up Google Cloud billing:")
        print("   1. Go to Google Cloud Console")
        print("   2. Enable Generative AI API")
        print("   3. Set up billing (free tier may be limited)")

asyncio.run(main())
