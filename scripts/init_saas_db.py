import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from packages.shared.database import engine, AsyncSessionFactory
from packages.shared.models import Base, User, UserCredential
from packages.shared.encryption import encrypt_key

async def init_db():
    print("🚀 Initializing SaaS Phase 1 Database...")
    
    # Create tables
    async with engine.begin() as conn:
        # Check if tables exist
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Tables created or already existed.")
    
    # Create initial admin user if not exists
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("👤 Creating admin user...")
            # We'll use 'admin' as password for demo, hashed later
            # For now, let's just use a simple hash or plain text just to boot up
            from apps.api.auth import user_manager
            # DemoUserManager has 'admin' as admin password
            
            new_admin = User(
                username="admin",
                email="admin@trading.bot",
                password_hash="admin", # Will be updated to real hash in next step
                role="admin",
                is_active=True,
                is_whitelisted=True
            )
            session.add(new_admin)
            await session.flush()
            
            # Link existing credentials if any
            from packages.shared.config import settings
            creds = UserCredential(
                user_id=new_admin.id,
                binance_api_key=encrypt_key(settings.binance_api_key),
                binance_api_secret=encrypt_key(settings.binance_api_secret),
                use_testnet=settings.binance_testnet,
                ai_provider=settings.selected_llm,
                ai_api_key=encrypt_key(settings.openai_api_key) if settings.openai_api_key else None
            )
            session.add(creds)
            print(f"🔗 Linked admin credentials (encrypted).")
            
        await session.commit()
    print("✨ Database initialization complete.")

if __name__ == "__main__":
    asyncio.run(init_db())
