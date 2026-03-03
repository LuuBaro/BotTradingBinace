#!/usr/bin/env python3
"""Debug: Check actual Order statuses in database"""
import asyncio
import os
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/api'))

from shared.models import User, Order, TradeJournal
from structlog import get_logger

logger = get_logger()

async def check():
    DATABASE_URL = "sqlite+aiosqlite:///./data/trading.db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get all users
        stmt = select(User)
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        logger.info("📊 === ALL USERS ===")
        for user in users:
            logger.info(f"   {user.username} ({user.id})")
        
        # For each user, show their orders with detailed status
        for user in users:
            logger.info(f"\n👤 USER: {user.username}")
            
            stmt = select(Order).where(Order.user_id == user.id)
            result = await db.execute(stmt)
            orders = result.scalars().all()
            
            logger.info(f"   Total Orders: {len(orders)}")
            
            # Group by status
            status_counts = {}
            for order in orders:
                status = order.status or "NULL"
                status_counts[status] = status_counts.get(status, 0) + 1
                logger.info(
                    f"     - {order.symbol} | "
                    f"Side: {order.side} | "
                    f"Status: {status} | "
                    f"Qty: {order.quantity} | "
                    f"Filled: {order.filled_qty} | "
                    f"Price: {order.avg_price}"
                )
            
            logger.info(f"\n   STATUS SUMMARY:")
            for status, count in status_counts.items():
                logger.info(f"     {status}: {count} orders")
            
            # Show TradeJournal for comparison
            stmt = select(TradeJournal).where(TradeJournal.user_id == user.id)
            result = await db.execute(stmt)
            trades = result.scalars().all()
            logger.info(f"   TradeJournal Records: {len(trades)}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
