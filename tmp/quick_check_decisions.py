import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Decision
from sqlalchemy import select, func, desc

async def check():
    async with AsyncSessionFactory() as s:
        c = await s.execute(select(func.count(Decision.id)))
        total = c.scalar()
        print(f'Total Decisions: {total}')
        
        r = await s.execute(select(Decision).order_by(desc(Decision.id)).limit(5))
        print('\nLast 5 decisions:')
        for d in r.scalars():
            user_short = d.user_id[:8] if d.user_id else 'N/A'
            rationale_short = d.rationale[:60] if d.rationale else 'No rationale'
            print(f'  ID {d.id}: {d.decision_type} (user: {user_short}...)')
            print(f'    Rationale: {rationale_short}...')

asyncio.run(check())
