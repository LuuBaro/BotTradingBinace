#!/usr/bin/env python3
import os
import sys
import asyncio
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.shared.db import get_db, init_db
from packages.shared.models import UserCredential
from sqlalchemy.ext.asyncio import AsyncSession

async def main():
    await init_db()
    
    async with get_db() as db:
        # Get admin user
        query_result = await db.execute(
            "SELECT id FROM user_credential WHERE user_name = 'admin' LIMIT 1"
        )
        admin_id = query_result.scalar()
        
        if not admin_id:
            print("❌ Admin user not found")
            return
        
        # Update model name
        await db.execute(
            "UPDATE user_credential SET ai_model = ? WHERE user_name = 'admin'",
            ("gemini-1.5-flash",)
        )
        await db.commit()
        
        print("✅ Model updated: gemini-pro → gemini-1.5-flash")
        print("   Admin user now uses: gemini-1.5-flash")
        print("\nRestart worker to apply changes...")

if __name__ == "__main__":
    asyncio.run(main())
