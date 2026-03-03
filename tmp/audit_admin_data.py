
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, UserCredential, BotConfig, Event, Decision, AuditLog
from sqlalchemy import select, func

async def audit_system():
    async with AsyncSessionFactory() as session:
        # 1. Check Admin User
        res = await session.execute(select(User).where(User.username == "admin"))
        admin = res.scalar_one_or_none()
        if not admin:
            print("❌ Admin user NOT FOUND in database!")
            return
        print(f"✅ Admin User Found: ID={admin.id}")

        # 2. Check Admin Credentials (API Keys)
        res = await session.execute(select(UserCredential).where(UserCredential.user_id == admin.id))
        creds = res.scalar_one_or_none()
        if not creds:
            print("⚠️ User-specific credentials NOT FOUND for admin. Falling back to .env global keys.")
        else:
            print(f"✅ User-specific credentials found for admin.")
            print(f"   - Binance Key: {'Set' if creds.binance_api_key else 'Empty'}")
            print(f"   - AI Provider: {creds.ai_provider}")
            print(f"   - AI Key: {'Set' if creds.ai_api_key else 'Empty'}")

        # 3. Check Data Counts
        tables = [
            ("BotConfig", BotConfig),
            ("Events", Event),
            ("Decisions", Decision),
            ("AuditLogs", AuditLog)
        ]
        print("\n--- Data Inventory ---")
        for name, model in tables:
            count_res = await session.execute(select(func.count()).select_from(model))
            count = count_res.scalar()
            print(f"📦 {name}: {count} records")
            
            # If config, check if any active
            if name == "BotConfig":
                active_res = await session.execute(select(BotConfig).where(BotConfig.is_active == True))
                active = active_res.scalars().all()
                print(f"   - Active Configs: {len(active)}")
                for a in active:
                    print(f"     - ID={a.id}, UserID={a.user_id}")

        # 4. Check for Global/System Events (Neural Event Stream)
        res = await session.execute(select(Event).limit(5).order_by(Event.timestamp.desc()))
        events = res.scalars().all()
        print("\n--- Latest Events ---")
        for e in events:
            print(f"[{e.timestamp}] {e.level}: {e.code} - {e.message}")

if __name__ == "__main__":
    asyncio.run(audit_system())
