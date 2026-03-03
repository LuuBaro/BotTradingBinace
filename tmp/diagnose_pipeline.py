#!/usr/bin/env python
"""Check AI decision pipeline and execution status"""
import asyncio
from sqlalchemy import select, desc, func
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import (
    Decision, 
    Signal, 
    User, 
    UserCredential,
    OrderIntent
)

async def main():
    async with AsyncSessionFactory() as session:
        # Get user info
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"📊 System Status")
        print(f"Active Users: {len(users)}")
        for u in users:
            cred_res = await session.execute(
                select(UserCredential).where(UserCredential.user_id == u.id)
            )
            cred = cred_res.scalar_one_or_none()
            provider = cred.ai_provider if cred else "unknown"
            print(f"  • {u.username}: LLM={provider}")
        print()
        
        # Get recent decisions
        result = await session.execute(
            select(Decision).order_by(desc(Decision.timestamp)).limit(5)
        )
        decisions = result.scalars().all()
        print(f"📋 Recent Decisions: {len(decisions)}")
        for d in decisions:
            symbol = "?"
            if d.order_spec and isinstance(d.order_spec, dict):
                symbol = d.order_spec.get("symbol", "?")
            elif d.decision_json and isinstance(d.decision_json, dict):
                symbol = d.decision_json.get("symbol", "?")
            print(f"  {symbol}: {d.decision_type} ({d.status})")
            if d.rationale:
                print(f"     └─ {d.rationale[:70]}...")
        print()
        
        # Count signals
        result = await session.execute(select(func.count(Signal.id)))
        signal_count = result.scalar()
        print(f"📡 Signals in Watchlist: {signal_count}")
        
        # Count orders
        result = await session.execute(select(func.count(OrderIntent.id)))
        order_count = result.scalar()
        print(f"📦 Executed Orders: {order_count}")

asyncio.run(main())
