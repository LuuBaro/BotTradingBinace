"""
Worker Main Loop - Trading engine orchestrator
Coordinates AI decision making, risk validation, and execution
"""
import asyncio
import signal
import sys
import uuid
import random
from datetime import datetime
from sqlalchemy import select, desc
from packages.shared.config import settings
from packages.shared.database import AsyncSessionFactory, init_db, close_db
from packages.shared.models import (
    BotConfig, 
    Decision as DecisionModel, 
    RiskLog, 
    Position, 
    Signal as SignalModel
)
from packages.shared.schemas import RiskConfig, MarketSnapshot, Decision as DecisionSchema
from packages.shared.exchange.mock import MockExchange
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from packages.shared.risk_engine import RiskEngine
from packages.shared.logger import logger
from apps.worker.agents.trader_stub import TraderStub
from apps.worker.engine.execution import ExecutionEngine
from apps.worker.engine.reconciler import ReconcilerEngine

class TradingWorker:
    """
    Main trading worker orchestrator
    Runs the decision → validation → execution loop
    """

    def __init__(self):
        self.running = False
        # Choose exchange based on configuration
        if settings.binance_api_key and settings.binance_api_secret:
            self.exchange = BinanceFuturesClient()
            self.is_binance = True
            logger.info(
                "exchange_initialized",
                type="binance",
                testnet=settings.binance_testnet,
            )
        else:
            self.exchange = MockExchange()
            self.is_binance = False
            logger.info("exchange_initialized", type="mock")
        
        self.trader = TraderStub()
        self.execution_engine = ExecutionEngine(self.exchange)
        self.reconciler = ReconcilerEngine(self.exchange)
        self.risk_engine: RiskEngine | None = None
        self.loop_count = 0
        self.binance_session = None  # For Binance async client

    async def initialize(self) -> None:
        """Initialize worker"""
        logger.info("worker_initializing")
        
        # Initialize database
        await init_db()
        
        # Initialize Binance client session if using Binance
        if self.is_binance and not self.exchange.session:
            import aiohttp
            # Force ThreadedResolver to avoid DNS issues with aiodns on Windows
            connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
            self.binance_session = aiohttp.ClientSession(connector=connector)
            self.exchange.session = self.binance_session
            await self.exchange.sync_server_time()
            logger.info("binance_session_initialized")
        
        # Load risk config from database
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(BotConfig).where(BotConfig.is_active == True).order_by(BotConfig.id.desc())
            )
            bot_config = result.scalar_one_or_none()
            
            if not bot_config:
                logger.warning("no_active_bot_config_using_default")
                risk_config = RiskConfig()
            else:
                risk_config = RiskConfig(**bot_config.risk_json)
                logger.info("risk_config_loaded", version=bot_config.version)
        
        # Initialize risk engine
        self.risk_engine = RiskEngine(risk_config)
        
        # ✅ CRITICAL: Initialize trader with max_position_pct limit
        # This ensures AI never generates size > config limit
        self.trader = TraderStub(max_position_pct=risk_config.max_position_pct)
        logger.info(
            "trader_stub_initialized_with_limit",
            max_position_pct=f"{risk_config.max_position_pct*100:.1f}%",
            context="AI will generate sizes within [30%, 95%] of max to maintain safety margin"
        )
        
        logger.info("worker_initialized")

    async def run(self) -> None:
        """Main worker loop"""
        self.running = True
        logger.info("worker_started", loop_interval_sec=settings.worker_loop_interval_sec)
        
        while self.running:
            try:
                self.loop_count += 1
                await self._execute_loop_iteration()
                await self._process_pending_approvals()  # Process manual approvals
                await asyncio.sleep(settings.worker_loop_interval_sec)
            except asyncio.CancelledError:
                logger.info("worker_loop_cancelled")
                break
            except Exception as e:
                logger.error("worker_loop_error", error=str(e), exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

    async def _execute_loop_iteration(self) -> None:
        """Execute one iteration of the trading loop"""
        trace_id = str(uuid.uuid4())
        logger.info("loop_iteration_start", loop_count=self.loop_count, trace_id=trace_id)

        async with AsyncSessionFactory() as session:
            try:
                # Reconcile exchange positions with database
                await self.reconciler.sync_positions(session)

                # Step 1: Get market snapshot (real from Binance or mock)
                if self.is_binance:
                    snapshot = await self._fetch_binance_snapshot()
                    if not snapshot:
                        # Fallback to mock if Binance fails
                        snapshot = self._generate_mock_snapshot()
                        logger.info("fallback_to_mock_snapshot")
                else:
                    snapshot = self._generate_mock_snapshot()
                
                logger.debug("market_snapshot_generated", symbol=snapshot.symbol, price=snapshot.close)

                # Step 2: Get AI decision
                decision = await self.trader.decide(snapshot)

                # Step 3: Save decision to database
                decision_record = DecisionModel(
                    timestamp=datetime.utcnow(),
                    trace_id=trace_id,
                    decision_json=decision.model_dump(),
                    confidence=decision.confidence,
                    regime=decision.regime.value,
                    rationale=decision.rationale,
                    checklist_results=[c.model_dump(by_alias=True) for c in decision.checklist],
                    status="PENDING",
                )
                session.add(decision_record)
                await session.flush()

                try:
                    rationale_text = decision.rationale[:50] + "..." if len(decision.rationale) > 50 else decision.rationale
                    rationale_text = rationale_text.encode('ascii', errors='ignore').decode('ascii')
                except Exception:
                    rationale_text = "See detailed rationale in database."

                logger.info(
                    "decision_made",
                    trace_id=trace_id,
                    action=decision.action.value,
                    regime=decision.regime.value,
                    confidence=decision.confidence,
                    rationale=rationale_text
                )
                
                # Step 3b: AI Intelligence Analysis & Watchlist
                try:
                    analysis = await self.trader.get_analysis(snapshot)
                    upcoming = analysis.get("upcoming_signals", [])
                    for sig_data in upcoming:
                        signal_record = SignalModel(
                            timestamp=datetime.utcnow(),
                            symbol=sig_data["symbol"],
                            side=sig_data["side"],
                            entry_zone=sig_data["entry_zone"],
                            probability=sig_data["probability"],
                            rationale=sig_data["rationale"],
                            status="ACTIVE"
                        )
                        session.add(signal_record)
                    
                    logger.debug("ai_signals_updated", count=len(upcoming))
                except Exception as ex:
                    logger.warning("failed_to_process_signals", error=str(ex))

                # Step 4: Risk validation
                if self.risk_engine:
                    # Get current positions
                    positions_result = await session.execute(select(Position))
                    current_positions = [
                        {"symbol": p.symbol, "side": p.side, "qty": p.qty}
                        for p in positions_result.scalars().all()
                    ]

                    # Get balance
                    balance_info = await self.exchange.get_balance()
                    balance = balance_info["balance"]

                    # Validate decision
                    risk_result = await self.risk_engine.validate_decision(
                        decision=decision,
                        current_positions=current_positions,
                        balance=balance,
                        current_price=snapshot.close,
                    )

                    # Log risk validation
                    risk_log = RiskLog(
                        trace_id=trace_id,
                        result=risk_result.result.value,
                        reason=risk_result.reason,
                        timestamp=datetime.utcnow(),
                    )
                    session.add(risk_log)
                    await session.flush()

                    logger.info(
                        "risk_validation_completed",
                        trace_id=trace_id,
                        result=risk_result.result.value,
                        approved=risk_result.approved,
                    )

                    # Update decision record with risk results
                    decision_record.risk_passed = risk_result.approved
                    decision_record.risk_approval_reason = risk_result.reason
                    decision_record.status = "APPROVED" if risk_result.approved else "REJECTED"
                    await session.flush()

                    # Step 5: Execute if approved
                    if risk_result.approved:
                        # Fetch current config to check for manual approval mode
                        config_result = await session.execute(
                            select(BotConfig).where(BotConfig.is_active == True).order_by(desc(BotConfig.version)).limit(1)
                        )
                        active_config = config_result.scalar_one_or_none()
                        
                        if active_config and active_config.approval_mode:
                            logger.info("manual_approval_required", trace_id=trace_id)
                            decision_record.status = "AWAITING_APPROVAL"
                            await session.flush()
                        else:
                            execution_result = await self.execution_engine.execute_decision(
                                decision=decision,
                                trace_id=trace_id,
                                session=session,
                            )
                            logger.info(
                                "execution_completed",
                                trace_id=trace_id,
                                result=execution_result.get("status"),
                            )
                            # Update decision record with execution status
                            decision_record.status = "EXECUTED" if execution_result.get("status") == "success" else "FAILED"
                            decision_record.execution_status = execution_result.get("status")
                            if execution_result.get("status") == "error":
                                decision_record.execution_error = execution_result.get("error")
                            await session.flush()
                    else:
                        logger.warning(
                            "decision_rejected_by_risk",
                            trace_id=trace_id,
                            reason=risk_result.reason,
                        )

                await session.commit()
                
                # Step 6: Update all active positions PnL
                await self._update_active_positions_pnl(snapshot)
                
                logger.info("loop_iteration_completed", loop_count=self.loop_count)

            except Exception as e:
                await session.rollback()
                logger.error(
                    "loop_iteration_failed",
                    loop_count=self.loop_count,
                    trace_id=trace_id,
                    error=str(e),
                    exc_info=True,
                )

    async def _update_active_positions_pnl(self, snapshot: MarketSnapshot) -> None:
        """Update unrealized PnL for all active positions in database"""
        async with AsyncSessionFactory() as session:
            try:
                result = await session.execute(select(Position))
                positions = result.scalars().all()
                
                if not positions:
                    return

                for pos in positions:
                    # For now, we only update if symbol matches snapshot
                    # In future, worker might fetch price for all symbols in positions
                    if pos.symbol == snapshot.symbol:
                        current_price = snapshot.close
                        entry_price = float(pos.entry_price)
                        qty = float(pos.qty)
                        
                        if pos.side.lower() == "long":
                            unrealized_pnl = (current_price - entry_price) * qty
                        else:
                            unrealized_pnl = (entry_price - current_price) * qty
                            
                        pos.unrealized_pnl = unrealized_pnl
                        pos.updated_at = datetime.utcnow()
                
                await session.commit()
                logger.debug("positions_pnl_updated", count=len(positions))
            except Exception as e:
                logger.error("failed_to_update_positions_pnl", error=str(e))

    async def _process_pending_approvals(self) -> None:
        """Fetch and execute decisions that were manually approved"""
        async with AsyncSessionFactory() as session:
            try:
                # Find decisions set to APPROVED_MANUALLY by API
                result = await session.execute(
                    select(DecisionModel).where(DecisionModel.status == "APPROVED_MANUALLY")
                )
                pending = result.scalars().all()
                
                if not pending:
                    return

                logger.info("processing_manual_approvals", count=len(pending))
                
                for decision_record in pending:
                    try:
                        trace_id = decision_record.trace_id
                        logger.info("executing_manually_approved_decision", trace_id=trace_id)
                        
                        # Reconstruct decision schema
                        decision_data = decision_record.decision_json
                        # Fix for potential string JSON
                        if isinstance(decision_data, str):
                            import json
                            decision_data = json.loads(decision_data)
                            
                        decision = DecisionSchema.model_validate(decision_data)
                        
                        # Execute
                        execution_result = await self.execution_engine.execute_decision(
                            decision=decision,
                            trace_id=trace_id,
                            session=session,
                        )
                        
                        # Update status
                        decision_record.status = "EXECUTED" if execution_result.get("status") == "success" else "FAILED"
                        decision_record.execution_status = execution_result.get("status")
                        if execution_result.get("status") == "error":
                            decision_record.execution_error = execution_result.get("error")
                            
                        await session.commit()
                        logger.info("manual_execution_completed", trace_id=trace_id, status=decision_record.status)
                        
                    except Exception as ex:
                        logger.error("manual_execution_failed", trace_id=decision_record.trace_id, error=str(ex))
                        decision_record.status = "FAILED"
                        decision_record.execution_error = str(ex)
                        await session.commit()
                        
            except Exception as e:
                logger.error("failed_to_process_pending_approvals", error=str(e))

    def _generate_mock_snapshot(self) -> MarketSnapshot:
        """Generate mock market data"""
        # Mock BTCUSDT price around 50000 with some randomness
        base_price = 50000.0
        variation = random.uniform(-1000, 1000)
        close = base_price + variation
        high = close + random.uniform(0, 500)
        low = close - random.uniform(0, 500)
        open_price = close + random.uniform(-200, 200)
        volume = random.uniform(1000, 5000)

        return MarketSnapshot(
            symbol="BTCUSDT",
            timestamp=datetime.utcnow(),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            spread=random.uniform(0.5, 2.0),
        )

    async def _fetch_binance_snapshot(self) -> MarketSnapshot | None:
        """Fetch real market data from Binance Testnet"""
        try:
            # Get 1-minute klines for BTCUSDT
            klines = await self.exchange.get_klines(
                symbol="BTCUSDT",
                interval="1m",
                limit=1
            )
            
            if not klines or len(klines) == 0:
                logger.warning("no_klines_data_from_binance")
                return None
            
            # Parse latest kline
            latest_kline = klines[-1]
            open_price = float(latest_kline[1])
            high_price = float(latest_kline[2])
            low_price = float(latest_kline[3])
            close_price = float(latest_kline[4])
            volume = float(latest_kline[7])
            timestamp = int(latest_kline[0])
            
            # Get bid-ask spread from ticker
            ticker = await self.exchange.get_ticker_price("BTCUSDT")
            bid = float(ticker.get("bidPrice", close_price))
            ask = float(ticker.get("askPrice", close_price))
            spread = ask - bid if ask > bid else 0.1
            
            snapshot = MarketSnapshot(
                symbol="BTCUSDT",
                timestamp=datetime.utcfromtimestamp(timestamp / 1000),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                spread=spread,
            )
            
            logger.debug(
                "binance_snapshot_fetched",
                symbol="BTCUSDT",
                close=close_price,
                volume=volume,
            )
            
            return snapshot
            
        except Exception as e:
            logger.warning("binance_snapshot_fetch_failed", error=str(e), exc_info=True)
            return None

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("worker_shutting_down")
        self.running = False
        
        # Close Binance session if it was created
        if self.binance_session:
            await self.binance_session.close()
            logger.info("binance_session_closed")
        
        await close_db()
        logger.info("worker_shutdown_complete")


async def main():
    """Main entry point"""
    worker = TradingWorker()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig):
        logger.info("signal_received", signal=sig)
        asyncio.create_task(worker.shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        except NotImplementedError:
            signal.signal(sig, lambda s, f: asyncio.create_task(worker.shutdown()))

    try:
        await worker.initialize()
        await worker.run()
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
