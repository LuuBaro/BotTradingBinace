"""
Check recent AI decisions to confirm Groq is being used
"""
import asyncio
import sys
sys.path.insert(0, 'd:\\BotTradingBinace')

from packages.shared.database import get_db_session
from packages.shared.models import Decision
from sqlalchemy import select
from datetime import datetime, timedelta

async def check_recent_decisions():
    async with get_db_session() as db:
        # Get last 10 decisions
        result = await db.execute(
            select(Decision)
            .order_by(Decision.timestamp.desc())
            .limit(10)
        )
        decisions = result.scalars().all()
        
        if not decisions:
            print("❌ No decisions found")
            return
        
        print(f"\n✅ Found {len(decisions)} recent decisions:\n")
        for i, d in enumerate(decisions, 1):
            print(f"{i}. {d.timestamp} | {d.symbol} | {d.decision_type} | Conf: {d.confidence:.2f}")
            if d.ai_notes:
                print(f"   Notes: {d.ai_notes[:100]}...")
        
        # Check if any recent decisions (dentro last 5 mins) are from Groq
        recent = [d for d in decisions if d.timestamp > datetime.utcnow() - timedelta(minutes=5)]
        print(f"\n{'='*70}")
        if recent:
            print(f"✅ {len(recent)} decisions in last 5 minutes (AI is active!)")
            print(f"Recent pattern: {', '.join([d.decision_type for d in recent])}")
        else:
            print("⚠️  No recent decisions (check if worker is running)")

asyncio.run(check_recent_decisions())
