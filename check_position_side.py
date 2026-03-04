#!/usr/bin/env python3
"""Check position.side values in database"""

import asyncio
from sqlalchemy.future import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Position

async def check_sides():
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Position))
        positions = result.scalars().all()
        
        print("=" * 60)
        print("POSITION SIDE VALUES IN DATABASE")
        print("=" * 60)
        
        for pos in positions:
            print(f"{pos.symbol:10} | side='{pos.side}' | Type: {type(pos.side).__name__} | Repr: {repr(pos.side)}")
        
        print("\n" + "=" * 60)
        print("Side ENUM VALUES")
        print("=" * 60)
        from packages.shared.enums import Side
        print(f"Side.LONG.value = '{Side.LONG.value}'")
        print(f"Side.SHORT.value = '{Side.SHORT.value}'")
        
        print("\n" + "=" * 60)
        print("COMPARISON TEST")
        print("=" * 60)
        if positions:
            pos = positions[0]
            print(f"position.side == Side.LONG.value: {pos.side == Side.LONG.value}")
            print(f"position.side == 'LONG': {pos.side == 'LONG'}")
            print(f"position.side.lower() == 'long': {pos.side.lower() == 'long'}")
            print(f"position.side.upper() == 'LONG': {pos.side.upper() == 'LONG'}")

if __name__ == "__main__":
    asyncio.run(check_sides())
