"""
Real-time PnL Broadcasting for WebSocket Streaming
Calculates and broadcasts position PnL every interval
"""
import asyncio
from typing import Dict, Any
from packages.shared.logger import logger
from packages.shared.models import Position
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def calculate_position_pnl(
    position: Position,
    current_mark_price: float
) -> Dict[str, Any]:
    """Calculate unrealized PnL for a position"""
    if position.position_amt == 0:
        return {
            "symbol": position.symbol,
            "position_amt": 0,
            "entry_price": 0,
            "unrealized_pnl": 0,
            "unrealized_pnl_pct": 0,
            "mark_price": current_mark_price,
        }
    
    # Calculate unrealized PnL
    price_diff = current_mark_price - position.entry_price
    unrealized_pnl = position.position_amt * price_diff
    unrealized_pnl_pct = (price_diff / position.entry_price) * 100 if position.entry_price else 0
    
    return {
        "symbol": position.symbol,
        "position_amt": float(position.position_amt),
        "entry_price": float(position.entry_price),
        "mark_price": float(current_mark_price),
        "unrealized_pnl": float(unrealized_pnl),
        "unrealized_pnl_pct": float(unrealized_pnl_pct),
        "realized_pnl": float(position.realized_pnl) if position.realized_pnl else 0,
    }


async def get_all_positions_pnl(
    session: AsyncSession,
    user_id: str,
) -> Dict[str, Any]:
    """Get all positions with current PnL for a user"""
    result = await session.execute(
        select(Position).where(Position.user_id == user_id)
    )
    positions = result.scalars().all()
    
    # For now, use mark_price from position record (would be updated by reconciler)
    position_pnls = []
    total_unrealized = 0
    
    for pos in positions:
        if pos.position_amt != 0:
            pnl_data = await calculate_position_pnl(pos, pos.mark_price or pos.entry_price)
            position_pnls.append(pnl_data)
            total_unrealized += pnl_data["unrealized_pnl"]
    
    return {
        "user_id": user_id,
        "timestamp": asyncio.get_event_loop().time(),
        "total_unrealized_pnl": float(total_unrealized),
        "positions": position_pnls,
    }


# Hook for reconciler to broadcast PnL updates
async def broadcast_position_pnl_update(
    session: AsyncSession,
    user_id: str,
    ws_manager: Any  # Avoid circular import
):
    """Called by reconciler after updating positions"""
    try:
        pnl_data = await get_all_positions_pnl(session, user_id)
        await ws_manager.broadcast_status(pnl_data)
    except Exception as e:
        logger.error("pnl_broadcast_failed", user_id=user_id, error=str(e))
