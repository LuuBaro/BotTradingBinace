#!/usr/bin/env python3
"""
Convert real Order records into TradeJournal records
Extract actual prices and timing from Order table, not using mock data
"""
import asyncio
import json
from datetime import datetime
from sqlalchemy import select, desc, func
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Order, TradeJournal, User
from packages.shared.logger import logger


async def convert_orders_to_trades(user_id: str | None = None, limit: int = 5):
    """
    Convert real Order records to TradeJournal
    - Use ENTRY orders (OPEN position)
    - Match with EXIT orders (CLOSE position)
    - Extract real prices and timing
    """
    async with AsyncSessionFactory() as db:
        # Get first user if not specified
        if not user_id:
            user_result = await db.execute(select(User.id).limit(1))
            user_id = user_result.scalar()
        
        if not user_id:
            logger.error("❌ No users found in database")
            return
        
        logger.info(f"🔄 Converting Orders → TradeJournal for user: {user_id[:8]}...")
        
        # Get all completed orders for this user
        # Completed = FILLED orders
        orders_result = await db.execute(
            select(Order)
            .where(Order.user_id == user_id, Order.status.in_(["FILLED", "PARTIALLY_FILLED"]))
            .order_by(Order.created_at)
        )
        all_orders = orders_result.scalars().all()
        
        logger.info(f"📊 Found {len(all_orders)} completed orders for user")
        
        if len(all_orders) < 2:
            logger.warning(f"⚠️  Need at least 2 orders to create trades (Entry + Exit)")
            return
        
        # Group orders by symbol to find entry/exit pairs
        orders_by_symbol = {}
        for order in all_orders:
            symbol = order.symbol
            if symbol not in orders_by_symbol:
                orders_by_symbol[symbol] = []
            orders_by_symbol[symbol].append(order)
        
        trades_created = 0
        
        # Process each symbol
        for symbol, symbol_orders in orders_by_symbol.items():
            logger.info(f"\n  Processing {symbol} ({len(symbol_orders)} orders)...")
            
            # LONG orders: BUY (entry), then SELL (exit)
            # SHORT orders: SELL (entry), then BUY (exit)
            
            entry_orders = [o for o in symbol_orders if o.side == "BUY"]
            exit_orders = [o for o in symbol_orders if o.side == "SELL"]
            
            # Pair entry with exit
            for i, entry in enumerate(entry_orders[:limit]):
                if i >= len(exit_orders):
                    continue  # Not enough exits
                
                exit_order = exit_orders[i]
                
                # Calculate trade metrics
                entry_price = float(entry.avg_price or entry.quantity)
                exit_price = float(exit_order.avg_price or exit_order.quantity)
                quantity = float(entry.filled_qty or entry.quantity)
                pnl = (exit_price - entry_price) * quantity
                pnl_percent = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
                
                # Holding time
                holding_time = int((exit_order.updated_at - entry.created_at).total_seconds())
                
                # Risk-Reward ratio
                rr = 1.0 if pnl == 0 else abs(pnl) / max(abs(pnl), 1)
                
                # Determine regime from decision or default
                regime = "trending" if pnl_percent > 0 else "consolidation"
                
                # Create TradeJournal record
                trade = TradeJournal(
                    trace_id=f"order_{entry.id}_{exit_order.id}",
                    symbol=symbol,
                    side="long",  # Since we're BUY then SELL
                    entry_price=entry_price,
                    exit_price=exit_price,
                    pnl=pnl,
                    rr=rr,
                    holding_time=holding_time,
                    regime=regime,
                    exit_reason="FILLED",
                    user_id=user_id,
                    features_json={
                        "entry_quantity": quantity,
                        "entry_order_id": entry.id,
                        "exit_order_id": exit_order.id,
                        "entry_time": entry.created_at.isoformat(),
                        "exit_time": exit_order.updated_at.isoformat(),
                        "pnl_pct": pnl_percent,
                        "entry_fee": float(entry.quantity * 0.0002),  # Assuming 0.02% maker fee
                        "exit_fee": float(exit_order.quantity * 0.0002),
                    },
                    decision_json={
                        "symbol": symbol,
                        "action": "close",
                        "side": "long",
                        "confidence": 0.8 if pnl_percent > 0 else 0.6,
                        "rationale": f"Converted from orders {entry.id} (entry) and {exit_order.id} (exit)",
                        "entry_reason": "MANUAL" if not entry.client_order_id else "AI",
                        "exit_reason": "FILLED",
                    },
                    closed_at=exit_order.updated_at if exit_order.updated_at else datetime.utcnow(),
                )
                
                db.add(trade)
                trades_created += 1
                
                logger.info(f"    ✅ Trade #{trades_created}: {symbol} LONG")
                logger.info(f"       Entry: ${entry_price:.2f} (Q: {quantity})")
                logger.info(f"       Exit:  ${exit_price:.2f}")
                logger.info(f"       P&L:   ${pnl:.2f} ({pnl_percent:.2f}%)")
                logger.info(f"       Time:  {holding_time}s")
            
            # SHORT orders: SELL (entry), then BUY (exit)
            short_entries = [o for o in symbol_orders if o.side == "SELL"]
            short_exits = [o for o in symbol_orders if o.side == "BUY"]
            
            for i, entry in enumerate(short_entries[:limit]):
                if i >= len(short_exits):
                    continue
                
                exit_order = short_exits[i]
                
                entry_price = float(entry.avg_price or entry.quantity)
                exit_price = float(exit_order.avg_price or exit_order.quantity)
                quantity = float(entry.filled_qty or entry.quantity)
                pnl = (entry_price - exit_price) * quantity  # Inverted for short
                pnl_percent = ((entry_price - exit_price) / entry_price * 100) if entry_price > 0 else 0
                
                holding_time = int((exit_order.updated_at - entry.created_at).total_seconds())
                rr = 1.0 if pnl == 0 else abs(pnl) / max(abs(pnl), 1)
                
                regime = "bearish" if pnl_percent > 0 else "consolidation"
                
                trade = TradeJournal(
                    trace_id=f"order_{entry.id}_{exit_order.id}_short",
                    symbol=symbol,
                    side="short",
                    entry_price=entry_price,
                    exit_price=exit_price,
                    pnl=pnl,
                    rr=rr,
                    holding_time=holding_time,
                    regime=regime,
                    exit_reason="FILLED",
                    user_id=user_id,
                    features_json={
                        "entry_quantity": quantity,
                        "entry_order_id": entry.id,
                        "exit_order_id": exit_order.id,
                        "entry_time": entry.created_at.isoformat(),
                        "exit_time": exit_order.updated_at.isoformat(),
                        "pnl_pct": pnl_percent,
                        "entry_fee": float(entry.quantity * 0.0002),
                        "exit_fee": float(exit_order.quantity * 0.0002),
                    },
                    decision_json={
                        "symbol": symbol,
                        "action": "close",
                        "side": "short",
                        "confidence": 0.8 if pnl_percent > 0 else 0.6,
                        "rationale": f"Converted from orders {entry.id} (entry) and {exit_order.id} (exit)",
                        "entry_reason": "MANUAL" if not entry.client_order_id else "AI",
                        "exit_reason": "FILLED",
                    },
                    closed_at=exit_order.updated_at if exit_order.updated_at else datetime.utcnow(),
                )
                
                db.add(trade)
                trades_created += 1
                
                logger.info(f"    ✅ Trade #{trades_created}: {symbol} SHORT")
                logger.info(f"       Entry: ${entry_price:.2f} (Q: {quantity})")
                logger.info(f"       Exit:  ${exit_price:.2f}")
                logger.info(f"       P&L:   ${pnl:.2f} ({pnl_percent:.2f}%)")
                logger.info(f"       Time:  {holding_time}s")
        
        # Commit all trades
        if trades_created > 0:
            await db.commit()
            logger.info(f"\n✅ Successfully created {trades_created} TradeJournal records from real Orders!")
        else:
            logger.warning("⚠️  No trades could be created (need entry/exit order pairs)")
        
        # Verify
        count_result = await db.execute(
            select(func.count(TradeJournal.id)).where(TradeJournal.user_id == user_id)
        )
        final_count = count_result.scalar() or 0
        logger.info(f"📊 Total TradeJournal records now: {final_count}")


if __name__ == "__main__":
    asyncio.run(convert_orders_to_trades())
