import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential
from sqlalchemy import select

async def check():
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(UserCredential))
        creds = result.scalars().all()
        print(f'Found {len(creds)} user credentials:')
        for c in creds:
            print(f'  - User ID: {c.user_id}')
            print(f'    Testnet: {c.use_testnet}')
            print(f'    Has API Key: {bool(c.binance_api_key)}')
            print()

asyncio.run(check())
