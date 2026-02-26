#!/usr/bin/env python3
"""Create test positions for demo"""
import asyncio
from packages.shared.database import AsyncSessionFactory, init_db
from packages.shared.models import Position, Order
from packages.shared.enums import Side, OrderType, OrderStatus

async def main():
    await init_db()
    
    async with AsyncSessionFactory() as session:
        # Create position 1
        pos1 = Position(
            symbol="BTCUSDT",
            side=Side.LONG,
            entry_price=50000.0,
            qty=0.1,
            sl_order_id="order_sl_1",
            tp_order_id="order_tp_1",
            leverage=2,
            margin_type="CROSSED",
            unrealized_pnl=500.0,
        )
        session.add(pos1)
        
        # Create position 2
        pos2 = Position(
            symbol="ETHUSDT",
            side=Side.SHORT,
            entry_price=3000.0,
            qty=1.0,
            sl_order_id="order_sl_2",
            tp_order_id="order_tp_2",
            leverage=3,
            margin_type="CROSSED",
            unrealized_pnl=-200.0,
        )
        session.add(pos2)
        
        # Create orders for pos1
        order1 = Order(
            client_order_id="order_1",
            symbol="BTCUSDT",
            side=Side.LONG,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            avg_price=49500.0,
            filled_qty=0.1,
            status=OrderStatus.FILLED,
        )
        session.add(order1)
        
        order2 = Order(
            client_order_id="order_2",
            symbol="BTCUSDT",
            side=Side.LONG,
            order_type=OrderType.STOP_MARKET,
            quantity=0.1,
            avg_price=49000.0,
            filled_qty=0.0,
            status=OrderStatus.PENDING,
        )
        session.add(order2)
        
        await session.commit()
        print("✓ Created 2 test positions and 2 orders")

if __name__ == "__main__":
    asyncio.run(main())
