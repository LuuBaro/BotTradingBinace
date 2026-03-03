import asyncio
import json
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Decision, Event, User
from sqlalchemy import select, func

async def check_decisions():
    async with AsyncSessionFactory() as session:
        # Count decisions
        decision_count = await session.execute(select(func.count(Decision.id)))
        total_decisions = decision_count.scalar()
        
        # Count events
        event_count = await session.execute(select(func.count(Event.id)))
        total_events = event_count.scalar()
        
        # Get users
        users_result = await session.execute(select(User))
        users = users_result.scalars().all()
        
        print(f"\n[Current State]")
        print(f"  Total Decisions: {total_decisions}")
        print(f"  Total Events: {total_events}")
        print(f"\nUsers in System:")
        for user in users:
            user_decisions = await session.execute(select(func.count(Decision.id)).where(Decision.user_id == user.id))
            user_decision_count = user_decisions.scalar()
            user_events = await session.execute(select(func.count(Event.id)).where(Event.user_id == user.id))
            user_event_count = user_events.scalar()
            print(f"  {user.username}: {user_decision_count} decisions, {user_event_count} events")
        
        # Show recent decisions
        if total_decisions > 0:
            print(f"\n[Last 5 Decisions]")
            decisions_result = await session.execute(
                select(Decision)
                .order_by(Decision.timestamp.desc())
                .limit(5)
            )
            decisions = decisions_result.scalars().all()
            for d in decisions:
                print(f"  - {d.user_id}: {d.decision_type} (confidence: {d.confidence}, status: {d.status})")

asyncio.run(check_decisions())
