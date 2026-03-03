
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from sqlalchemy import text

async def data_inventory():
    async with AsyncSessionFactory() as session:
        # 1. Get current users
        users_res = await session.execute(text("SELECT id, username FROM users"))
        users = {row[0]: row[1] for row in users_res.all()}
        print(f"👥 Users in DB: {users}")
        
        # 2. Inventory of key tables
        tables = [
            "bot_config", "decisions", "signals", "orders", 
            "positions", "trade_journal", "events", "user_credentials"
        ]
        
        print("\n--- Table Inventory ---")
        for table in tables:
            try:
                # Get unique user_ids and their counts
                res = await session.execute(text(f"SELECT user_id, COUNT(*) FROM {table} GROUP BY user_id"))
                rows = res.all()
                if not rows:
                    print(f"📦 {table}: EMPTY")
                    continue
                    
                print(f"📦 {table}:")
                for uid, count in rows:
                    status = "✅ Valid User" if uid in users else "⚠️ ORPHAN/OLD"
                    user_label = users.get(uid, f"Literal '{uid}'")
                    print(f"  - User: {user_label} (ID: {uid}) -> {count} records [{status}]")
                    
            except Exception as e:
                print(f"❌ Error in table {table}: {e}")

if __name__ == "__main__":
    asyncio.run(data_inventory())
