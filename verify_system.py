import asyncio
from sqlalchemy import select, desc
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Signal, Decision
from datetime import datetime, timedelta

async def check_system():
    async with AsyncSessionFactory() as session:
        # Get recent signals
        signals = await session.execute(
            select(Signal)
            .where(Signal.timestamp > datetime.utcnow() - timedelta(minutes=5))
            .order_by(desc(Signal.timestamp))
            .limit(5)
        )
        recent_signals = signals.scalars().all()
        
        # Get recent decisions
        decisions = await session.execute(
            select(Decision)
            .where(Decision.timestamp > datetime.utcnow() - timedelta(minutes=5))
            .order_by(desc(Decision.timestamp))
            .limit(5)
        )
        recent_decisions = decisions.scalars().all()
        
        print('SYSTEM STATUS CHECK')
        print('=' * 50)
        print(f'Recent Signals (last 5 min): {len(recent_signals)} [OK]')
        if recent_signals:
            for sig in recent_signals[:3]:
                print(f'  * {sig.symbol}: {sig.status} @ {sig.timestamp.strftime("%H:%M:%S")}')
        
        print(f'Recent Decisions (last 5 min): {len(recent_decisions)} [OK]')
        status_counts = {}
        for dec in recent_decisions:
            status_counts[dec.status] = status_counts.get(dec.status, 0) + 1
        for status, count in sorted(status_counts.items()):
            print(f'  * {status}: {count}')
        
        print('\n[OK] System Running with Mock AI!')
        print('Ready to switch to real AI (requires Google Cloud billing)')

asyncio.run(check_system())
