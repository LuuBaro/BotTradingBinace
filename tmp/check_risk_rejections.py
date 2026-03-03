#!/usr/bin/env python
"""Check why risk engine is rejecting decisions"""
import asyncio
from sqlalchemy import select, desc
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import RiskLog

async def main():
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(RiskLog).order_by(desc(RiskLog.timestamp)).limit(10)
        )
        logs = result.scalars().all()
        
        print(f"🔍 Risk Engine Rejection Log ({len(logs)} entries)")
        print()
        for log in logs:
            print(f"Result: {log.result}")
            print(f"Reason: {log.reason[:100]}")
            print(f"User: {log.user_id}")
            print()

asyncio.run(main())
