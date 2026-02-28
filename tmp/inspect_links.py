
import asyncio
import os
import sys
from sqlalchemy import select, func

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory, engine
from packages.shared.models import Decision, Order, OrderIntent, TradeJournal

async def deep_inspect():
    print(f"Connecting to: {engine.url}")
    async with AsyncSessionFactory() as session:
        # 1. Recent Decisions
        print("\n--- RECENT DECISIONS ---")
        d_res = await session.execute(select(Decision).order_by(Decision.timestamp.desc()).limit(5))
        for d in d_res.scalars().all():
            print(f"ID: {d.id} | Timestamp: {d.timestamp} | TraceID: {d.trace_id} | OrderID: {d.order_id} | Rationale: {d.rationale[:50] if d.rationale else 'NONE'}")

        # 2. Recent Orders
        print("\n--- RECENT ORDERS ---")
        o_res = await session.execute(select(Order).order_by(Order.created_at.desc()).limit(5))
        for o in o_res.scalars().all():
            print(f"ID: {o.id} | Symbol: {o.symbol} | ClientOID: {o.client_order_id} | ExchOID: {o.exchange_order_id} | Status: {o.status}")

        # 3. Recent OrderIntents
        print("\n--- RECENT INTENTS ---")
        i_res = await session.execute(select(OrderIntent).order_by(OrderIntent.created_at.desc()).limit(5))
        for i in i_res.scalars().all():
            print(f"ID: {i.id} | TraceID: {i.trace_id} | ClientOID: {i.client_order_id} | Status: {i.status}")

        # 4. Try to link manually (Pick a random Order)
        print("\n--- LINKAGE TEST ---")
        random_o_res = await session.execute(select(Order).limit(1))
        random_o = random_o_res.scalar_one_or_none()
        if random_o:
            print(f"Testing for Order: {random_o.exchange_order_id} (ClientOID: {random_o.client_order_id})")
            # Link to Intent
            intent_res = await session.execute(select(OrderIntent).where(OrderIntent.client_order_id == random_o.client_order_id))
            intent = intent_res.scalar_one_or_none()
            if intent:
                print(f"  -> Found Intent: {intent.trace_id}")
                # Link to Decision
                dec_res = await session.execute(select(Decision).where(Decision.trace_id == intent.trace_id))
                dec = dec_res.scalar_one_or_none()
                if dec:
                    print(f"  -> Found Decision Rationale: {dec.rationale[:50] if dec.rationale else 'NONE'}")
                else:
                    print("  -> NO Decision found for this TraceID")
            else:
                print("  -> NO Intent found for this ClientOID")

if __name__ == "__main__":
    asyncio.run(deep_inspect())
