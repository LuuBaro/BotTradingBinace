"""
Initialize custom news sources as requested by user.
Registers Telegram, NewsNow, and Phemex.
"""
import asyncio
from packages.shared.database import init_db, AsyncSessionFactory
from packages.shared.models import NewsSource
from sqlalchemy import select

async def main():
    await init_db()
    
    sources = [
        {
            "name": "Coin 369 Telegram",
            "url": "https://t.me/s/coin369channel", # Use public preview URL
            "source_type": "telegram"
        },
        {
            "name": "NewsNow Crypto",
            "url": "https://www.newsnow.co.uk/h/Business+&+Finance/Cryptocurrencies",
            "source_type": "web" # Generic web for aggregator
        },
        {
            "name": "Phemex News",
            "url": "https://phemex.com/news",
            "source_type": "web"
        }
    ]
    
    async with AsyncSessionFactory() as session:
        for s in sources:
            result = await session.execute(select(NewsSource).where(NewsSource.url == s["url"]))
            existing = result.scalar_one_or_none()
            
            if not existing:
                print(f"✅ Registering source: {s['name']}")
                new_source = NewsSource(**s)
                session.add(new_source)
            else:
                print(f"ℹ️ Source already exists: {s['name']}")
                
        await session.commit()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
