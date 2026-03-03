
import asyncio
import sqlite3
import os

async def migrate():
    db_path = "data/trading_bot.db"
    if not os.path.exists(db_path):
        print("Database not found, skip migration.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tables to check for user_id
    tables = ["events", "bot_config", "decisions", "signals", "orders", "positions", "trade_journal", "chat_messages"]
    
    for table in tables:
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            if "user_id" not in columns:
                print(f"Adding user_id to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id VARCHAR(50) DEFAULT 'admin'")
        except Exception as e:
            print(f"Error migrating {table}: {e}")
            
    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    asyncio.run(migrate())
