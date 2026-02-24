"""
Reconciler - Sync database state with exchange state
Detects mismatches between position tracking and actual exchange positions
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.shared.models import (
    Position as PositionModel,
    Order as OrderModel,
    Event as EventModel,
    AuditLog as AuditLogModel,
)
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from packages.shared.exchange.mock import MockExchange
from packages.shared.logger import logger


class ReconcilerEngine:
    """
    Reconciles database state with exchange state
    - Syncs positions: DB ↔ Binance every 5-10s
    - Detects position mismatches
    - Detects order status mismatches
    - Emits events for reconciliation issues
    """

    def __init__(self, exchange):
        self.exchange = exchange
        self.is_binance = isinstance(exchange, BinanceFuturesClient)
        logger.info(
            "reconciler_initialized",
            exchange_type="binance" if self.is_binance else "mock",
        )

    async def reconcile(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Full reconciliation cycle
        
        Returns:
            Summary dict with mismatches found
        """
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "position_mismatches": [],
            "order_mismatches": [],
            "total_mismatches": 0,
        }

        try:
            # Get DB positions
            db_positions = await self._get_db_positions(session)
            
            # Get exchange positions
            exchange_positions = await self._get_exchange_positions()
            
            # Compare and detect mismatches
            position_mismatches = await self._compare_positions(
                db_positions, exchange_positions, session
            )
            summary["position_mismatches"] = position_mismatches
            
            # Get DB orders
            db_orders = await self._get_db_orders(session)
            
            # Get exchange open orders
            exchange_orders = await self._get_exchange_orders()
            
            # Compare order statuses
            order_mismatches = await self._compare_orders(
                db_orders, exchange_orders, session
            )
            summary["order_mismatches"] = order_mismatches
            
            # Update summary
            summary["total_mismatches"] = len(position_mismatches) + len(order_mismatches)
            
            # Log reconciliation result
            if summary["total_mismatches"] > 0:
                logger.warning(
                    "reconciliation_completed_with_mismatches",
                    mismatches=summary["total_mismatches"],
                )
                
                # Emit reconciliation event
                event = EventModel(
                    timestamp=datetime.utcnow(),
                    level="WARNING",
                    code="RECONCILIATION_MISMATCH",
                    message=f"Found {summary['total_mismatches']} reconciliation mismatches",
                    data_json=summary,
                )
                session.add(event)
            else:
                logger.info("reconciliation_completed_no_mismatches")
            
            await session.commit()
            return summary

        except Exception as e:
            logger.error("reconciliation_failed", error=str(e))
            # Emit error event
            event = EventModel(
                timestamp=datetime.utcnow(),
                level="ERROR",
                code="RECONCILIATION_ERROR",
                message=f"Reconciliation error: {str(e)}",
                data_json={"error": str(e)},
            )
            session.add(event)
            await session.commit()
            raise

    async def _get_db_positions(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Get all positions from database"""
        result = await session.execute(select(PositionModel))
        positions = result.scalars().all()
        
        return [
            {
                "symbol": p.symbol,
                "side": p.side,
                "qty": p.qty,
                "entry_price": p.entry_price,
                "leverage": p.leverage,
                "liquidation_price": p.liquidation_price,
            }
            for p in positions
        ]

    async def _get_exchange_positions(self) -> List[Dict[str, Any]]:
        """Get positions from exchange"""
        try:
            if self.is_binance:
                # Binance: Get position risk
                positions = await self.exchange.get_position_risk()
                return [
                    {
                        "symbol": p["symbol"],
                        "side": p["positionSide"],  # LONG, SHORT, BOTH
                        "qty": float(p["positionAmt"]),
                        "entry_price": float(p["entryPrice"]),
                        "leverage": int(p["leverage"]),
                        "liquidation_price": float(p["liquidationPrice"]),
                    }
                    for p in positions
                    if float(p["positionAmt"]) != 0  # Only non-zero positions
                ]
            else:
                # Mock: Get positions from memory
                # Mock exchange doesn't have get_positions, return stub
                return []
        
        except Exception as e:
            logger.error("get_exchange_positions_failed", error=str(e))
            return []

    async def _get_db_orders(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Get all non-filled orders from database"""
        result = await session.execute(
            select(OrderModel).where(
                OrderModel.status.in_(["new", "partially_filled"])
            )
        )
        orders = result.scalars().all()
        
        return [
            {
                "client_order_id": o.client_order_id,
                "exchange_order_id": o.exchange_order_id,
                "symbol": o.symbol,
                "status": o.status,
                "filled_qty": o.filled_qty,
            }
            for o in orders
        ]

    async def _get_exchange_orders(self) -> List[Dict[str, Any]]:
        """Get open orders from exchange"""
        try:
            if self.is_binance:
                orders = await self.exchange.get_open_orders()
                return [
                    {
                        "orderId": str(o["orderId"]),
                        "clientOrderId": o["clientOrderId"],
                        "symbol": o["symbol"],
                        "status": o["status"],
                        "executedQty": float(o["executedQty"]),
                    }
                    for o in orders
                ]
            else:
                # Mock: return empty list
                return []
        
        except Exception as e:
            logger.error("get_exchange_orders_failed", error=str(e))
            return []

    async def _compare_positions(
        self,
        db_positions: List[Dict[str, Any]],
        exchange_positions: List[Dict[str, Any]],
        session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """Compare DB positions with exchange positions"""
        mismatches = []
        
        # Create lookup by symbol
        exchange_by_symbol = {p["symbol"]: p for p in exchange_positions}
        db_by_symbol = {p["symbol"]: p for p in db_positions}
        
        # Check for positions in DB but not on exchange
        for symbol, db_pos in db_by_symbol.items():
            if symbol not in exchange_by_symbol:
                mismatch = {
                    "type": "position_missing_on_exchange",
                    "symbol": symbol,
                    "db_qty": db_pos["qty"],
                }
                mismatches.append(mismatch)
                logger.warning(
                    "position_missing_on_exchange",
                    symbol=symbol,
                    db_qty=db_pos["qty"],
                )
        
        # Check for positions on exchange but not in DB
        for symbol, ex_pos in exchange_by_symbol.items():
            if symbol not in db_by_symbol:
                mismatch = {
                    "type": "position_missing_in_db",
                    "symbol": symbol,
                    "exchange_qty": ex_pos["qty"],
                }
                mismatches.append(mismatch)
                logger.warning(
                    "position_missing_in_db",
                    symbol=symbol,
                    exchange_qty=ex_pos["qty"],
                )
        
        # Check for quantity mismatches
        for symbol in db_by_symbol:
            if symbol in exchange_by_symbol:
                db_pos = db_by_symbol[symbol]
                ex_pos = exchange_by_symbol[symbol]
                
                qty_tolerance = 0.001  # Small tolerance for floating point
                if abs(db_pos["qty"] - ex_pos["qty"]) > qty_tolerance:
                    mismatch = {
                        "type": "quantity_mismatch",
                        "symbol": symbol,
                        "db_qty": db_pos["qty"],
                        "exchange_qty": ex_pos["qty"],
                    }
                    mismatches.append(mismatch)
                    logger.warning(
                        "quantity_mismatch",
                        symbol=symbol,
                        db_qty=db_pos["qty"],
                        exchange_qty=ex_pos["qty"],
                    )
        
        return mismatches

    async def _compare_orders(
        self,
        db_orders: List[Dict[str, Any]],
        exchange_orders: List[Dict[str, Any]],
        session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """Compare DB order statuses with exchange order statuses"""
        mismatches = []
        
        # Create lookup by client order ID
        exchange_by_client_id = {
            o["clientOrderId"]: o for o in exchange_orders
        }
        
        for db_order in db_orders:
            client_order_id = db_order["client_order_id"]
            
            if client_order_id not in exchange_by_client_id:
                # Order in DB but not on exchange (might be filled)
                mismatch = {
                    "type": "order_missing_on_exchange",
                    "client_order_id": client_order_id,
                    "symbol": db_order["symbol"],
                    "db_status": db_order["status"],
                }
                mismatches.append(mismatch)
                logger.warning(
                    "order_missing_on_exchange",
                    client_order_id=client_order_id,
                    db_status=db_order["status"],
                )
            else:
                ex_order = exchange_by_client_id[client_order_id]
                
                if db_order["status"] != ex_order["status"]:
                    mismatch = {
                        "type": "order_status_mismatch",
                        "client_order_id": client_order_id,
                        "symbol": db_order["symbol"],
                        "db_status": db_order["status"],
                        "exchange_status": ex_order["status"],
                    }
                    mismatches.append(mismatch)
                    logger.warning(
                        "order_status_mismatch",
                        client_order_id=client_order_id,
                        db_status=db_order["status"],
                        exchange_status=ex_order["status"],
                    )
        
        return mismatches

    async def sync_positions(self, session: AsyncSession) -> None:
        """
        Force sync positions from exchange to DB
        (Auto-heal mismatches)
        """
        try:
            if not self.is_binance:
                logger.debug("sync_positions_skipped_mock_exchange")
                return
            
            # Get exchange positions
            exchange_positions = await self._get_exchange_positions()
            
            # Update DB from exchange
            for ex_pos in exchange_positions:
                result = await session.execute(
                    select(PositionModel).where(
                        PositionModel.symbol == ex_pos["symbol"]
                    )
                )
                db_pos = result.scalar_one_or_none()
                
                if db_pos:
                    # Update existing position
                    db_pos.qty = abs(ex_pos["qty"])
                    db_pos.entry_price = ex_pos["entry_price"]
                    db_pos.leverage = ex_pos["leverage"]
                    db_pos.liquidation_price = ex_pos["liquidation_price"]
                    db_pos.updated_at = datetime.utcnow()
                else:
                    # Create new position (shouldn't happen normally)
                    db_pos = PositionModel(
                        symbol=ex_pos["symbol"],
                        side="LONG" if ex_pos["qty"] > 0 else "SHORT",
                        qty=abs(ex_pos["qty"]),
                        entry_price=ex_pos["entry_price"],
                        leverage=ex_pos["leverage"],
                        liquidation_price=ex_pos["liquidation_price"],
                    )
                    session.add(db_pos)
            
            await session.commit()
            logger.info("positions_synced_from_exchange")
        
        except Exception as e:
            logger.error("sync_positions_failed", error=str(e))
            raise
