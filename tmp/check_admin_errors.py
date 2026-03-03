#!/usr/bin/env python
"""Check recent admin decisions with OpenAI"""
import asyncio
from sqlalchemy import select, desc
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Decision, User, Event

async def main():
    async with AsyncSessionFactory() as session:
        # Get admin
        admin_res = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin = admin_res.scalar_one_or_none()
        
        if not admin:
            print("❌ Admin not found")
            return
        
        print(f"📊 Recent Admin Decisions:")
        print()
        
        # Get recent decisions
        dec_res = await session.execute(
            select(Decision)
            .order_by(desc(Decision.timestamp))
            .limit(5)
        )
        decisions = dec_res.scalars().all()
        
        for d in decisions:
            status_icon = "✅" if d.status == "EXECUTED" else "❌" if d.status == "REJECTED" else "⏳"
            print(f"{status_icon} {d.decision_type} ({d.status})")
            if d.rationale:
                print(f"   └─ {d.rationale[:80]}")
        
        print()
        print("📋 Recent Errors:")
        print()
        
        # Get recent error events
        evt_res = await session.execute(
            select(Event)
            .where(Event.level == "ERROR")
            .order_by(desc(Event.timestamp))
            .limit(5)
        )
        events = evt_res.scalars().all()
        
        for e in events:
            print(f"❌ {e.code}: {e.message[:80]}")

asyncio.run(main())
