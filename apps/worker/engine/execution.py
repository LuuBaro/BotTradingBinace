"""
Execution Engine - Idempotent order execution with crash safety
Manages order placement, position tracking, and SL/TP orders
Supports both MockExchange and Binance Futures
"""
import asyncio
from datetime import datetime
from typing import Union
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from packages.shared.schemas import Decision, OrderIntent
from packages.shared.enums import ActionType, OrderStatus, OrderType, Side, IntentStatus
from packages.shared.models import (
    OrderIntent as OrderIntentModel,
    Order as OrderModel,
    Position as PositionModel,
    Event as EventModel,
    AuditLog as AuditLogModel,
    TradeJournal as TradeJournalModel,
)
from packages.shared.trade_journal import ExitReason
from packages.shared.exchange.mock import MockExchange
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from packages.shared.logger import logger


async def _commit_with_retry(session: AsyncSession, retries: int = 3, delay: float = 0.3) -> None:
    for attempt in range(1, retries + 1):
        try:
            await session.commit()
            return
        except OperationalError as exc:
            await session.rollback()
            if attempt == retries:
                raise
            logger.warning("db_commit_retry", attempt=attempt, error=str(exc))
            await asyncio.sleep(delay)


class ExecutionEngine:
    """
    Execution engine with idempotency guarantees
    - Checks for existing order intents to prevent duplicates
    - Generates deterministic client_order_id
    - Creates positions and manages SL/TP orders
    - Supports both MockExchange and Binance Futures
    """

    def __init__(self, exchange: Union[MockExchange, BinanceFuturesClient]):
        self.exchange = exchange
        self.is_binance = isinstance(exchange, BinanceFuturesClient)
        logger.info(
            "execution_engine_initialized",
            exchange_type="binance" if self.is_binance else "mock",
        )

    async def _validate_position_size_explicitly(
        self,
        decision: Decision,
        trace_id: str,
        session: AsyncSession,
        user_id: str,
    ) -> None:
        """
        ✅ CRITICAL VALIDATION: Ensure position size does NOT exceed limits
        This is a safety check BEFORE execution to prevent oversized positions
        
        Args:
            decision: Trading decision to validate
            trace_id: Trace ID for logging
            session: Database session
            
        Raises:
            ValueError: If position size exceeds configured limits
        """
        # Get current positions for this user
        existing_positions = await session.execute(select(PositionModel).where(PositionModel.user_id == user_id))
        positions = existing_positions.scalars().all()
        
        # Get balance
        if self.is_binance:
            balance_info = await self.exchange.get_account_balance()
            usdt_balance = next(
                (b for b in balance_info if b["asset"] == "USDT"),
                {"balance": "0"}
            )
            balance = float(usdt_balance.get("balance", 0))
        else:
            balance_info = await self.exchange.get_balance()
            balance = balance_info["balance"]
        
        # Calculate position value
        position_notional = balance * decision.size_pct * decision.leverage
        position_size_pct = (position_notional / balance * 100) if balance > 0 else 0
        
        logger.info(
            "position_size_validation_check",
            trace_id=trace_id,
            symbol=decision.symbol,
            size_pct=f"{decision.size_pct*100:.2f}%",
            leverage=f"{decision.leverage}x",
            notional_pct=f"{position_size_pct:.2f}%",
            balance=f"${balance:.2f}",
            decision_status="EXPLICIT VALIDATION BEFORE EXECUTION"
        )
        
        # Hard constraint: position_size_pct must be <= balance (100%)
        if position_size_pct > 100:
            error_msg = (
                f"REJECTED: Position size {position_size_pct:.1f}% exceeds 100% of balance! "
                f"size_pct={decision.size_pct*100:.1f}%, leverage={decision.leverage}x"
            )
            logger.error("position_size_validation_failed", trace_id=trace_id, reason=error_msg)
            raise ValueError(error_msg)
        
        logger.info(
            "position_size_validation_passed",
            trace_id=trace_id,
            check_status="✅ SAFE TO EXECUTE",
            safety_buffer=f"{100 - position_size_pct:.1f}% remaining"
        )

    async def execute_decision(
        self,
        session: AsyncSession,
        user_id: str,
        decision: Decision,
        trace_id: str,
    ) -> dict:
        """
        Execute a trading decision with idempotency
        
        Args:
            decision: Validated trading decision
            trace_id: Unique trace ID for this decision
            session: Database session

        Returns:
            Execution result dict
        """
        # Handle HOLD action (no execution needed)
        if decision.action == ActionType.HOLD:
            logger.info("execution_skipped_hold", trace_id=trace_id)
            return {"status": "skipped", "reason": "HOLD action"}

        # Handle CLOSE action
        if decision.action == ActionType.CLOSE:
            return await self._close_position(session, user_id, decision, trace_id)

        # Handle OPEN action
        return await self._open_position(session, user_id, decision, trace_id)

    async def _open_position(
        self,
        session: AsyncSession,
        user_id: str,
        decision: Decision,
        trace_id: str,
    ) -> dict:
        """Open a new position"""
        # ✅ CRITICAL: Validate position size EXPLICITLY before execution
        # This prevents any position from exceeding configured limits
        await self._validate_position_size_explicitly(
            decision=decision,
            trace_id=trace_id,
            session=session,
            user_id=user_id
        )
        
        # Generate deterministic client_order_id
        client_order_id = f"{trace_id[:8]}_{decision.symbol}_{int(datetime.utcnow().timestamp())}"

        # Check idempotency: has this trace_id been executed for THIS user?
        existing_intent = await session.execute(
            select(OrderIntentModel).where(OrderIntentModel.trace_id == trace_id, OrderIntentModel.user_id == user_id)
        )
        existing = existing_intent.scalar_one_or_none()

        if existing:
            logger.warning(
                "execution_duplicate_prevented",
                trace_id=trace_id,
                existing_client_order_id=existing.client_order_id,
            )
            return {"status": "duplicate", "client_order_id": existing.client_order_id}

        # Create order intent record (pending)
        intent = OrderIntentModel(
            user_id=user_id,
            trace_id=trace_id,
            client_order_id=client_order_id,
            payload_json=decision.model_dump(),
            status=IntentStatus.PENDING.value,
            created_at=datetime.utcnow(),
        )
        session.add(intent)
        await session.flush()

        try:
            # Binance-specific: Set leverage and margin type
            if self.is_binance:
                await self._setup_binance_position_mode(decision.symbol, decision.leverage)
            
            # Get current balance and calculate quantity
            if self.is_binance:
                # Binance: Get futures account balance
                balance_info = await self.exchange.get_account_balance()
                # Find USDT balance
                usdt_balance = next(
                    (b for b in balance_info if b["asset"] == "USDT"),
                    {"balance": "0"}
                )
                balance = float(usdt_balance.get("balance", 0))
                
                # Get current mark price for calculation
                mark_price_info = await self.exchange.get_mark_price(decision.symbol)
                entry_price = decision.entry_price or float(mark_price_info["markPrice"])
            else:
                # Mock exchange
                balance_info = await self.exchange.get_balance()
                balance = balance_info["balance"]
                entry_price = decision.entry_price or self.exchange.get_mark_price(decision.symbol)
            
            position_value = balance * decision.size_pct * decision.leverage
            quantity = position_value / entry_price

            # Round quantity and price for Binance
            if self.is_binance:
                symbol_info = await self.exchange.get_symbol_info(decision.symbol)
                if symbol_info:
                    quantity = self.exchange.round_quantity(symbol_info, quantity)
                    if decision.entry_price:
                        decision.entry_price = self.exchange.round_price(symbol_info, decision.entry_price)
                    if decision.stop_loss:
                        decision.stop_loss = self.exchange.round_price(symbol_info, decision.stop_loss)
                    if decision.take_profit:
                        decision.take_profit = self.exchange.round_price(symbol_info, decision.take_profit)

            # Place order on exchange
            if self.is_binance:
                order_result = await self.exchange.place_order(
                    symbol=decision.symbol,
                    side=decision.side,
                    order_type=decision.entry_type,
                    quantity=quantity,
                    price=decision.entry_price,
                    client_order_id=client_order_id,
                )
                # Convert Binance response to standard format
                order_status = self.exchange._convert_order_status(order_result.get("status", "NEW"))
                order_data = {
                    "order_id": str(order_result["orderId"]),
                    "status": order_status.value,
                    "filled_qty": float(order_result.get("executedQty", 0)),
                    "avg_price": float(order_result.get("avgPrice", 0)) if float(order_result.get("avgPrice", 0)) > 0 else None,
                }
            else:
                order_result = await self.exchange.place_order(
                    symbol=decision.symbol,
                    side=decision.side,
                    order_type=decision.entry_type,
                    quantity=quantity,
                    price=decision.entry_price,
                    client_order_id=client_order_id,
                )
                order_data = {
                    "order_id": order_result["order_id"],
                    "status": order_result["status"],
                    "filled_qty": order_result.get("filled_qty", 0.0),
                    "avg_price": order_result.get("avg_price"),
                }

            # Create order record
            order = OrderModel(
                user_id=user_id,
                client_order_id=client_order_id,
                exchange_order_id=order_data["order_id"],
                symbol=decision.symbol,
                side=decision.side.value,
                order_type=decision.entry_type.value,
                status=order_data["status"],
                quantity=quantity,
                filled_qty=order_data["filled_qty"],
                avg_price=order_data["avg_price"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(order)

            # Update intent status
            intent.status = IntentStatus.EXECUTED.value

            # Wait for fill
            if self.is_binance:
                # Binance: Market orders usually fill immediately, wait briefly
                await asyncio.sleep(0.2)
                filled_order_response = await self.exchange.get_order(
                    symbol=decision.symbol,
                    client_order_id=client_order_id,
                )
                filled_order = {
                    "filled_qty": float(filled_order_response.get("executedQty", 0)),
                    "avg_price": float(filled_order_response.get("avgPrice", 0)),
                    "status": self.exchange._convert_order_status(filled_order_response.get("status", "NEW")).value,
                }
            else:
                # Mock exchange
                await asyncio.sleep(0.5)
                filled_order = await self.exchange.get_order(order_data["order_id"])

            # Create/update position
            await self._create_position(
                session, user_id, decision, filled_order, trace_id
            )

            # Create SL/TP orders if specified
            sl_order_id = None
            tp_order_id = None
            
            if decision.stop_loss:
                sl_order_id = await self._create_sl_order(session, user_id, decision, quantity, trace_id)
            if decision.take_profit:
                tp_order_id = await self._create_tp_order(session, user_id, decision, quantity, trace_id)
            
            # Update position with SL/TP order IDs
            if sl_order_id or tp_order_id:
                await self._update_position_sl_tp(
                    session, user_id, decision.symbol, sl_order_id, tp_order_id
                )

            # Log event
            event = EventModel(
                user_id=user_id,
                timestamp=datetime.utcnow(),
                level="INFO",
                code="ORDER_FILLED",
                message=f"Order filled: {decision.symbol} {decision.side.value} {quantity:.4f}",
                trace_id=trace_id,
                data_json={"order_id": order_data["order_id"], "price": filled_order["avg_price"]},
            )
            session.add(event)

            # Audit log
            audit = AuditLogModel(
                user_id=user_id,
                timestamp=datetime.utcnow(),
                actor="system",
                action="place_order",
                target=decision.symbol,
                details_json={"client_order_id": client_order_id, "quantity": quantity},
            )
            session.add(audit)

            await _commit_with_retry(session)

            logger.info(
                "position_opened",
                trace_id=trace_id,
                symbol=decision.symbol,
                quantity=quantity,
                avg_price=filled_order["avg_price"],
            )

            return {
                "status": "success",
                "order_id": order_data["order_id"],
                "client_order_id": client_order_id,
                "quantity": quantity,
                "avg_price": filled_order["avg_price"],
            }

        except Exception as e:
            # Mark intent as failed
            intent.status = IntentStatus.FAILED.value
            await _commit_with_retry(session)
            
            logger.error(
                "execution_failed",
                trace_id=trace_id,
                error=str(e),
            )
            raise

    async def _setup_binance_position_mode(self, symbol: str, leverage: int) -> None:
        """Setup Binance position mode (leverage and margin type)"""
        try:
            # Set leverage
            await self.exchange.set_leverage(symbol=symbol, leverage=leverage)
            
            # Set margin type to CROSSED (default)
            await self.exchange.set_margin_type(symbol=symbol, margin_type="CROSSED")
        except Exception as e:
            logger.warning(
                "binance_position_mode_setup_error",
                symbol=symbol,
                error=str(e),
            )

    async def _create_position(
        self,
        session: AsyncSession,
        user_id: str,
        decision: Decision,
        filled_order: dict,
        trace_id: str,
    ) -> None:
        """Create or update position record"""
        # Check existing position for THIS user
        existing_pos = await session.execute(
            select(PositionModel).where(PositionModel.symbol == decision.symbol, PositionModel.user_id == user_id)
        )
        position = existing_pos.scalar_one_or_none()

        if not position:
            # New position
            position = PositionModel(
                user_id=user_id,
                symbol=decision.symbol,
                side=decision.side.value,
                qty=filled_order["filled_qty"],
                entry_price=filled_order["avg_price"],
                unrealized_pnl=0.0,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                opened_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(position)
            logger.info(
                "position_record_created",
                trace_id=trace_id,
                symbol=decision.symbol,
                side=decision.side.value,
                qty=filled_order["filled_qty"],
                entry_price=filled_order["avg_price"],
                message="Position added to session, pending commit"
            )
        else:
            # Update existing position (add to position)
            position.qty += filled_order["filled_qty"]
            position.entry_price = filled_order["avg_price"]  # Simplified
            position.updated_at = datetime.utcnow()

    async def _create_sl_order(
        self,
        session: AsyncSession,
        user_id: str,
        decision: Decision,
        quantity: float,
        trace_id: str,
    ) -> str | None:
        """Create stop loss order, return order ID"""
        try:
            sl_client_order_id = f"SL_{trace_id[:8]}_{decision.symbol}"
            
            # Round quantity and stop_price for Binance
            if self.is_binance:
                symbol_info = await self.exchange.get_symbol_info(decision.symbol)
                if symbol_info:
                    quantity = self.exchange.round_quantity(symbol_info, quantity)
                    decision.stop_loss = self.exchange.round_price(symbol_info, decision.stop_loss)

            # Place SL order on exchange
            if self.is_binance:
                sl_order = await self.exchange.place_order(
                    symbol=decision.symbol,
                    side=Side.SHORT if decision.side == Side.LONG else Side.LONG,
                    order_type=OrderType.STOP_MARKET,
                    quantity=quantity,
                    stop_price=decision.stop_loss,
                    client_order_id=sl_client_order_id,
                )
                sl_order_id = str(sl_order["orderId"])
                sl_status = self.exchange._convert_order_status(sl_order.get("status", "NEW")).value
            else:
                sl_order = await self.exchange.place_order(
                    symbol=decision.symbol,
                    side=Side.SHORT if decision.side == Side.LONG else Side.LONG,
                    order_type=OrderType.STOP_MARKET,
                    quantity=quantity,
                    stop_price=decision.stop_loss,
                    client_order_id=sl_client_order_id,
                )
                sl_order_id = sl_order["order_id"]
                sl_status = sl_order["status"]

            # Create order record
            order = OrderModel(
                user_id=user_id,
                client_order_id=sl_client_order_id,
                exchange_order_id=sl_order_id,
                symbol=decision.symbol,
                side=Side.SHORT.value if decision.side == Side.LONG else Side.LONG.value,
                order_type=OrderType.STOP_MARKET.value,
                status=sl_status,
                quantity=quantity,
                filled_qty=0.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(order)

            logger.info("sl_order_created", trace_id=trace_id, stop_price=decision.stop_loss)
            return sl_order_id
        
        except Exception as e:
            logger.error("sl_order_creation_failed", trace_id=trace_id, error=str(e))
            return None

    async def _create_tp_order(
        self,
        session: AsyncSession,
        user_id: str,
        decision: Decision,
        quantity: float,
        trace_id: str,
    ) -> str | None:
        """Create take profit order, return order ID"""
        try:
            tp_client_order_id = f"TP_{trace_id[:8]}_{decision.symbol}"
            
            # Round quantity and stop_price for Binance
            if self.is_binance:
                symbol_info = await self.exchange.get_symbol_info(decision.symbol)
                if symbol_info:
                    quantity = self.exchange.round_quantity(symbol_info, quantity)
                    decision.take_profit = self.exchange.round_price(symbol_info, decision.take_profit)

            # Place TP order on exchange
            if self.is_binance:
                tp_order = await self.exchange.place_order(
                    symbol=decision.symbol,
                    side=Side.SHORT if decision.side == Side.LONG else Side.LONG,
                    order_type=OrderType.TAKE_PROFIT_MARKET,
                    quantity=quantity,
                    stop_price=decision.take_profit,
                    client_order_id=tp_client_order_id,
                )
                tp_order_id = str(tp_order["orderId"])
                tp_status = self.exchange._convert_order_status(tp_order.get("status", "NEW")).value
            else:
                tp_order = await self.exchange.place_order(
                    symbol=decision.symbol,
                    side=Side.SHORT if decision.side == Side.LONG else Side.LONG,
                    order_type=OrderType.TAKE_PROFIT_MARKET,
                    quantity=quantity,
                    stop_price=decision.take_profit,
                    client_order_id=tp_client_order_id,
                )
                tp_order_id = tp_order["order_id"]
                tp_status = tp_order["status"]

            # Create order record
            order = OrderModel(
                user_id=user_id,
                client_order_id=tp_client_order_id,
                exchange_order_id=tp_order_id,
                symbol=decision.symbol,
                side=Side.SHORT.value if decision.side == Side.LONG else Side.LONG.value,
                order_type=OrderType.TAKE_PROFIT_MARKET.value,
                status=tp_status,
                quantity=quantity,
                filled_qty=0.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(order)

            logger.info("tp_order_created", trace_id=trace_id, take_profit=decision.take_profit)
            return tp_order_id
        
        except Exception as e:
            logger.error("tp_order_creation_failed", trace_id=trace_id, error=str(e))
            return None

    async def _update_position_sl_tp(
        self,
        session: AsyncSession,
        user_id: str,
        symbol: str,
        sl_order_id: str | None,
        tp_order_id: str | None,
    ) -> None:
        """Update position with SL/TP order IDs"""
        result = await session.execute(
            select(PositionModel).where(PositionModel.symbol == symbol, PositionModel.user_id == user_id)
        )
        position = result.scalar_one_or_none()
        
        if position:
            if sl_order_id:
                position.sl_order_id = sl_order_id
            if tp_order_id:
                position.tp_order_id = tp_order_id
            position.updated_at = datetime.utcnow()

    async def _close_position(
        self,
        session: AsyncSession,
        user_id: str,
        decision: Decision,
        trace_id: str,
    ) -> dict:
        """Close an existing position"""
        # Get position for THIS user
        existing_pos = await session.execute(
            select(PositionModel).where(PositionModel.symbol == decision.symbol, PositionModel.user_id == user_id)
        )
        position = existing_pos.scalar_one_or_none()

        if not position:
            logger.warning("close_position_not_found", symbol=decision.symbol)
            return {"status": "error", "reason": "Position not found"}

        # Generate client_order_id for close order
        client_order_id = f"CLOSE_{trace_id[:8]}_{decision.symbol}"

        # Place market order to close (opposite side, reduce-only)
        # position.side is stored as string (e.g., "LONG", "long", "SHORT", "short")
        position_side_lower = position.side.lower() if position.side else "long"
        close_side = Side.SHORT if position_side_lower == "long" else Side.LONG
        
        logger.info(
            "closing_position",
            symbol=decision.symbol,
            position_side=position.side,
            close_side=close_side.value,
            quantity=position.qty
        )
        
        if self.is_binance:
            close_order = await self.exchange.place_order(
                symbol=decision.symbol,
                side=close_side,
                order_type=OrderType.MARKET,
                quantity=position.qty,
                client_order_id=client_order_id,
                reduce_only=True,
            )
            close_order_id = str(close_order["orderId"])
        else:
            close_order = await self.exchange.place_order(
                symbol=decision.symbol,
                side=close_side,
                order_type=OrderType.MARKET,
                quantity=position.qty,
                client_order_id=client_order_id,
            )
            close_order_id = close_order["order_id"]

        # Determine exit price
        if self.is_binance:
            await asyncio.sleep(0.2)
            order_info = await self.exchange.get_order(
                symbol=decision.symbol,
                client_order_id=client_order_id,
            )
            exit_price = float(order_info.get("avgPrice", 0)) if order_info else 0.0
            if exit_price <= 0:
                mark = await self.exchange.get_mark_price(decision.symbol)
                exit_price = float(mark.get("markPrice", 0))
        else:
            await asyncio.sleep(0.5)
            order_info = await self.exchange.get_order(close_order_id)
            exit_price = float(order_info.get("avg_price") or 0.0)
            if exit_price <= 0:
                exit_price = float(self.exchange.get_mark_price(decision.symbol))

        # Compute trade metrics
        entry_price = float(position.entry_price)
        qty = float(position.qty)
        side = position.side
        exit_time = datetime.utcnow()
        entry_time = position.opened_at
        holding_time_sec = int((exit_time - entry_time).total_seconds()) if entry_time else 0

        if side.lower() == Side.LONG.value:
            pnl = (exit_price - entry_price) * qty
        else:
            pnl = (entry_price - exit_price) * qty

        denom = abs(entry_price * qty)
        pnl_pct = (pnl / denom) if denom > 0 else 0.0

        if decision.stop_loss and decision.take_profit and entry_price > 0:
            rr = abs(decision.take_profit - entry_price) / max(abs(entry_price - decision.stop_loss), 1e-9)
            stop_loss_pips = abs(entry_price - decision.stop_loss)
            take_profit_pips = abs(decision.take_profit - entry_price)
        else:
            rr = 1.0
            stop_loss_pips = 0.0
            take_profit_pips = 0.0

        # Estimate position size %
        if self.is_binance:
            balance_info = await self.exchange.get_account_balance()
            usdt_balance = next(
                (b for b in balance_info if b["asset"] == "USDT"),
                {"balance": "0"}
            )
            balance = float(usdt_balance.get("balance", 0))
        else:
            balance_info = await self.exchange.get_balance()
            balance = float(balance_info.get("balance", 0))

        position_value = abs(entry_price * qty)
        position_pct = (position_value / balance) if balance > 0 else 0.0

        trade = TradeJournalModel(
            user_id=user_id,
            trace_id=trace_id,
            symbol=decision.symbol,
            side=side,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            rr=rr,
            holding_time=holding_time_sec,
            regime=getattr(decision.regime, "value", str(decision.regime)),
            features_json={
                "entry_time": entry_time.isoformat() if entry_time else None,
                "exit_time": exit_time.isoformat(),
                "entry_quantity": qty,
                "entry_leverage": float(getattr(decision, "leverage", 1)),
                "volatility_percentile": 50,
                "bid_ask_spread_pips": 0.5,
                "funding_rate": 0.0,
                "position_pct": position_pct,
                "stop_loss_pips": stop_loss_pips,
                "take_profit_pips": take_profit_pips,
                "confidence": float(getattr(decision, "confidence", 0.0)),
                "ai_model": "mock" if not self.is_binance else "binance",
                "prompt_pack_version": 1,
                "pnl_pct": pnl_pct,
                "max_drawdown": 0.0,
                "max_runup": 0.0,
            },
            decision_json=decision.model_dump(),
            exit_reason=str(decision.decision_type.value) if hasattr(decision.decision_type, 'value') else str(decision.decision_type or ExitReason.MANUAL.value),
            closed_at=exit_time,
        )
        session.add(trade)

        # Delete position
        await session.delete(position)

        # Log event
        event = EventModel(
            user_id=user_id,
            timestamp=datetime.utcnow(),
            level="INFO",
            code="POSITION_CLOSED",
            message=f"Position closed: {decision.symbol}",
            trace_id=trace_id,
            data_json={"order_id": close_order_id},
        )
        session.add(event)

        await _commit_with_retry(session)

        logger.info("position_closed", trace_id=trace_id, symbol=decision.symbol)

        return {"status": "success", "order_id": close_order_id}
