import asyncio
from packages.shared.database import engine
import sqlalchemy as sa

async def check():
    async with engine.begin() as conn:
        def _inspect(sync_conn):
            inspector = sa.inspect(sync_conn)
            tables = inspector.get_table_names()
            print(f'Tables: {tables}')
            
            if 'positions' in tables:
                cols = inspector.get_columns('positions')
                print('Positions columns:')
                for c in cols:
                    print(f'  {c["name"]}')
            else:
                print('NO positions table!')
        
        await conn.run_sync(_inspect)

asyncio.run(check())
