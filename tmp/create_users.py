
import asyncio
import hashlib
from datetime import datetime
from packages.shared.database import AsyncSessionFactory, init_db
from packages.shared.models import User
from sqlalchemy import select

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

async def create_users():
    print("Creating admin and user accounts...")
    await init_db()
    
    async with AsyncSessionFactory() as session:
        # Check if they exist
        result = await session.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            print("Admin user already exists.")
        else:
            admin = User(
                username="admin",
                email="admin@example.com",
                password_hash=_hash_password("admin123"),
                role="admin",
                is_active=True,
                is_whitelisted=True,
                created_at=datetime.utcnow()
            )
            session.add(admin)
            print("Admin created: user=admin, pass=admin123")

        result = await session.execute(select(User).where(User.username == "trader"))
        if result.scalar_one_or_none():
            print("Trader user already exists.")
        else:
            trader = User(
                username="trader",
                email="trader@example.com",
                password_hash=_hash_password("trader123"),
                role="trader",
                is_active=True,
                is_whitelisted=True,
                created_at=datetime.utcnow()
            )
            session.add(trader)
            print("Trader created: user=trader, pass=trader123")
            
        await session.commit()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(create_users())
