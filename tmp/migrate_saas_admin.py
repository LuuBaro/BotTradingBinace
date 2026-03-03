
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import (
    User, BotConfig, Decision, Signal, Order, Position, 
    TradeJournal, Event, ChatMessage, SystemNotification
)
from sqlalchemy import select, update, or_

async def migrate_admin_data():
    async with AsyncSessionFactory() as session:
        # 1. Get the actual UUID for the 'admin' username
        res = await session.execute(select(User).where(User.username == "admin"))
        admin_user = res.scalar_one_or_none()
        
        if not admin_user:
            print("❌ Error: No user found with username 'admin'. Please create it first.")
            return
            
        admin_uuid = admin_user.id
        print(f"✅ Found Admin User: {admin_user.username} (ID: {admin_uuid})")

        # 2. Define tables to update (Table Class, Column Name)
        migration_targets = [
            (BotConfig, "user_id"),
            (Decision, "user_id"),
            (Signal, "user_id"),
            (Order, "user_id"),
            (Position, "user_id"),
            (TradeJournal, "user_id"),
            (Event, "user_id"),
            (ChatMessage, "user_id"),
            (SystemNotification, "target_user_id"),
        ]

        print("\n--- Starting Migration ---")
        for model, col_name in migration_targets:
            try:
                # Find records where user_id is literal string 'admin' or NULL (if it should be admin's)
                # Note: We only map literal 'admin' to the new UUID. 
                # If it's NULL, it might be truly global (like notifications), so we only map 'admin' string.
                attr = getattr(model, col_name)
                
                # Check how many would be updated
                count_res = await session.execute(
                    select(model).where(or_(attr == "admin", attr == None if model != SystemNotification else False))
                )
                to_update = count_res.scalars().all()
                
                if not to_update:
                    print(f"ℹ️ {model.__tablename__}: No records with user_id='admin' found.")
                    continue

                # Execute update
                upd_res = await session.execute(
                    update(model)
                    .where(attr == "admin")
                    .values({col_name: admin_uuid})
                )
                print(f"🚀 {model.__tablename__}: Updated {upd_res.rowcount} records to ID {admin_uuid}")
                
            except Exception as e:
                print(f"❌ Error updating {model.__tablename__}: {e}")

        await session.commit()
        print("\n✅ Migration complete. Old 'admin' string records are now linked to UUID.")

if __name__ == "__main__":
    asyncio.run(migrate_admin_data())
