
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select
from packages.shared.models import Order

async def check_db_order(order_id):
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(Order).where(Order.id == str(order_id)))
        o = res.scalar_one_or_none()
        if o:
            print(f"DB Order Found:")
            print(f"ID: {o.id}")
            print(f"Symbol: {o.symbol}")
            print(f"Side: {o.side}")
            print(f"Status: {o.status}")
            print(f"Qty: {o.quantity}")
        else:
            print(f"Order {order_id} not found in database.")

if __name__ == "__main__":
    asyncio.run(check_db_order(12554053836))
