import asyncio
from sqlalchemy import text
from packages.shared.database import engine
from packages.shared.models import Base

async def migrate_to_multi_user():
    print("🚀 Starting Multi-User SaaS Migration...")
    
    # 1. Create new table(s) if not exists
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Add user_id column to existing tables (SQLite safe approach)
    tables_to_update = [
        "bot_config", "decisions", "orders", "positions", 
        "trade_journal", "signals", "events", "audit_logs", "chat_messages",
        "risk_logs", "order_intents", "learning_reports", "trader_contexts"
    ]
    
    async with engine.begin() as conn:
        for table in tables_to_update:
            try:
                print(f"Adding user_id to {table}...")
                # SQLite ALTER TABLE is simple, but might fail if column already exists
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id VARCHAR(50) DEFAULT 'admin'"))
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(f"Column user_id already exists in {table}, skipping.")
                else:
                    print(f"Error updating {table}: {e}")
        
        # 3. Ensure existing data belongs to 'admin'
        for table in tables_to_update:
            print(f"Setting default user_id for {table}...")
            await conn.execute(text(f"UPDATE {table} SET user_id = 'admin' WHERE user_id IS NULL"))

    print("✅ Migration to Multi-User complete.")

if __name__ == "__main__":
    asyncio.run(migrate_to_multi_user())
