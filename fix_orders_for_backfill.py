#!/usr/bin/env python3
"""Fix orders to enable learning page backfill"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


import sys
import os
from sqlalchemy import delete

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages'))

from shared.models import User, Order

async def fix_orders():
    DATABASE_URL = "sqlite+aiosqlite:///./data/trading.db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get trader user
        trader_res = await db.execute(select(User).where(User.username == "trader"))
        trader_user = trader_res.scalar_one_or_none()
        if not trader_user:
            print("❌ Trader user not found")
            return
        
        trader_id = trader_user.id
        print(f"👤 Trader user ID: {trader_id}")
        
        # Get existing orders
        orders_res = await db.execute(
            select(Order)
            .where(Order.user_id == trader_id)
            .order_by(Order.created_at.asc())
        )
        existing_orders = orders_res.scalars().all()
        print(f"\n📊 Found {len(existing_orders)} existing orders")
        
        # Delete existing orders
        if existing_orders:
            await db.execute(delete(Order).where(Order.user_id == trader_id))
            await db.commit()
            print("🗑️  Cleared existing orders")
        
        # Create realistic BUY/SELL pairs
        base_time = datetime.utcnow() - timedelta(hours=2)
        
        trades = [
            {"symbol": "BTCUSDT", "qty": 0.1, "entry_price": 42000, "exit_price": 43000},
            {"symbol": "ETHUSDT", "qty": 1.0, "entry_price": 2200, "exit_price": 2250},
            {"symbol": "SOLUSDT", "qty": 10, "entry_price": 140, "exit_price": 145},
            {"symbol": "LINKUSDT", "qty": 100, "entry_price": 28, "exit_price": 29},
            {"symbol": "ADAUSDT", "qty": 500, "entry_price": 1.1, "exit_price": 1.15},
        ]
        
        order_id = 1000
        for i, trade in enumerate(trades):
            symbol = trade["symbol"]
            qty = trade["qty"]
            entry_price = trade["entry_price"]
            exit_price = trade["exit_price"]
            
            # BUY order
            entry_time = base_time + timedelta(minutes=i*30)
            buy_order = Order(
                id=order_id,
                user_id=trader_id,
                                client_order_id=f"backfill_buy_{order_id}",
                symbol=symbol,
                side="BUY",
                quantity=qty,
                filled_qty=qty,
                avg_price=entry_price,
                status="FILLED",
                created_at=entry_time,
                updated_at=entry_time + timedelta(seconds=5),
            )
            db.add(buy_order)
            order_id += 1
            
            # SELL order (exit)
            exit_time = entry_time + timedelta(minutes=5)
            sell_order = Order(
                                client_order_id=f"backfill_sell_{order_id}",
                id=order_id,
                user_id=trader_id,
                symbol=symbol,
                side="SELL",
                quantity=qty,
                filled_qty=qty,
                avg_price=exit_price,
                status="FILLED",
                created_at=exit_time,
                updated_at=exit_time + timedelta(seconds=5),
            )
            db.add(sell_order)
            order_id += 1
            
            print(f"✅ Created trade pair: {symbol} BUY@{entry_price} SELL@{exit_price}")
        
        await db.commit()
        print(f"\n✅ Created {len(trades)} trading pairs (10 orders total)")

if __name__ == "__main__":
    asyncio.run(fix_orders())
