import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Position
from sqlalchemy import select, func

async def check_positions():
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(func.count(Position.id)))
        count = result.scalar()
        print(f'✅ Total positions in DB: {count}')
        
        if count > 0:
            result2 = await session.execute(select(Position).order_by(Position.id.desc()).limit(3))
            positions = result2.scalars().all()
            print(f'\nRecent {len(positions)} positions:')
            for p in positions:
                print(f'  {p.symbol:8} {p.side:5} | Entry: {p.entry_price:10.0f} | Qty: {p.qty:8.4f}')

asyncio.run(check_positions())
