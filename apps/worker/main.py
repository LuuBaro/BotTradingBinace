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
    Signal as SignalModel,
    Event
)
from packages.shared.schemas import RiskConfig, MarketSnapshot, Decision as DecisionSchema
from packages.shared.enums import ActionType
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
        
        last_heartbeat = datetime.utcnow() # Initialize heartbeat timer
        
        while self.running:
            try:
                # Send heartbeat every 30 seconds
                if (datetime.utcnow() - last_heartbeat).total_seconds() > 30:
                    async with AsyncSessionFactory() as session:
                        heartbeat = Event(
                            timestamp=datetime.utcnow(),
                            level="INFO",
                            code="WORKER_HEARTBEAT",
                            message=f"Worker active. Monitoring {len(self.symbols_to_monitor)} symbols.",
                            data_json={"symbols_count": len(self.symbols_to_monitor)}
                        )
                        session.add(heartbeat)
                        await session.commit()
                    last_heartbeat = datetime.utcnow()
                    logger.debug("worker_heartbeat_sent")
                    
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
        """Execute one iteration of the trading loop for all configured symbols"""
        # Danh sách các cặp coin AI sẽ theo dõi
        symbols = [
            "BTCUSDT", "ETHUSDT", "LINKUSDT", "XRPUSDT", 
            "DOTUSDT", "UNIUSDT", "DOGEUSDT", "SOLUSDT", 
            "ADAUSDT", "MATICUSDT", "AVAXUSDT"
        ]
        
        async with AsyncSessionFactory() as session:
            try:
                # Reconcile exchange positions with database
                await self.reconciler.sync_positions(session)
                
                # Get current positions from DB to share with AI
                positions_result = await session.execute(select(Position))
                db_positions = {p.symbol: p for p in positions_result.scalars().all()}

                for symbol in symbols:
                    trace_id = str(uuid.uuid4())
                    
                    # Step 1: Get market snapshot
                    if self.is_binance:
                        snapshot = await self._fetch_binance_snapshot(symbol)
                        if not snapshot:
                            snapshot = self._generate_mock_snapshot(symbol)
                    else:
                        snapshot = self._generate_mock_snapshot(symbol)
                    
                    if not snapshot:
                        continue

                    # Update PNL for this specific symbol if position exists
                    if symbol in db_positions:
                        pos = db_positions[symbol]
                        current_price = snapshot.close
                        entry_price = float(pos.entry_price)
                        qty = float(pos.qty)
                        
                        if pos.side.lower() == "long":
                            pos.unrealized_pnl = (current_price - entry_price) * qty
                        else:
                            pos.unrealized_pnl = (entry_price - current_price) * qty
                        pos.updated_at = datetime.utcnow()

                    # Step 2: Get AI decision (passing active position context)
                    active_pos = db_positions.get(symbol)
                    decision = await self.trader.decide(snapshot, active_position=active_pos)

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

                    if decision.action != ActionType.HOLD:
                        # Fetch balance and current positions for risk validation
                        balance_info = await self.exchange.get_account_balance() if self.is_binance else await self.exchange.get_balance()
                        balance = float(balance_info[0]["balance"]) if self.is_binance and isinstance(balance_info, list) else float(balance_info.get("balance", 0))
                        
                        current_positions = [
                            {"symbol": p.symbol, "side": p.side, "qty": p.qty}
                            for p in db_positions.values()
                        ]

                        # Risk Validation
                        risk_result = await self.risk_engine.validate_decision(
                            decision=decision,
                            current_positions=current_positions,
                            balance=balance,
                            current_price=snapshot.close,
                        )

                        decision_record.risk_passed = risk_result.approved
                        decision_record.risk_approval_reason = risk_result.reason
                        await session.flush()

                        if risk_result.approved:
                            try:
                                execution_result = await self.execution_engine.execute_decision(
                                    decision=decision,
                                    trace_id=trace_id,
                                    session=session
                                )
                                
                                if execution_result.get("status") == "success":
                                    decision_record.status = "EXECUTED"
                                    logger.info(f"✅ Executed {decision.action} for {symbol}", trace_id=trace_id)
                                else:
                                    decision_record.status = "FAILED"
                            except Exception as exec_err:
                                logger.error(f"❌ Execution failed for {symbol}: {str(exec_err)}")
                                decision_record.status = "FAILED"
                        else:
                            decision_record.status = "REJECTED"
                            logger.warning(f"🛡️ Risk REJECTED {decision.action} for {symbol}: {risk_result.reason}")

                await session.commit()
                logger.info(f"loop_iteration_complete", loop_count=self.loop_count)

            except Exception as e:
                logger.error("worker_loop_iteration_error", error=str(e), exc_info=True)
                await session.rollback()

    async def _update_positions_pnl(self, snapshot: MarketSnapshot) -> None:
        """Legacy method - now integrated into the main loop for efficiency"""
        pass


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

    def _generate_mock_snapshot(self, symbol: str) -> MarketSnapshot:
        """Generate mock market data for any symbol"""
        # Mock price ranges based on symbol
        prices = {
            "BTCUSDT": 68000.0,
            "ETHUSDT": 3500.0,
            "LINKUSDT": 18.0,
            "XRPUSDT": 0.6,
            "DOTUSDT": 7.5,
            "UNIUSDT": 10.0,
            "DOGEUSDT": 0.15
        }
        base_price = prices.get(symbol, 100.0)
        variation = random.uniform(-base_price * 0.02, base_price * 0.02)
        close = base_price + variation
        high = close + random.uniform(0, base_price * 0.01)
        low = close - random.uniform(0, base_price * 0.01)
        open_price = close + random.uniform(-base_price * 0.005, base_price * 0.005)
        volume = random.uniform(1000000, 5000000)

        return MarketSnapshot(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            spread=random.uniform(0.01, 0.5),
        )

    async def _fetch_binance_snapshot(self, symbol: str) -> MarketSnapshot | None:
        """Fetch real market data from Binance Testnet for a specific symbol"""
        try:
            # Get 1-minute klines
            klines = await self.exchange.get_klines(
                symbol=symbol,
                interval="1m",
                limit=1
            )
            
            if not klines or len(klines) == 0:
                logger.warning(f"no_klines_data_from_binance_for_{symbol}")
                return None
            
            # Parse latest kline
            latest_kline = klines[-1]
            open_price = float(latest_kline[1])
            high_price = float(latest_kline[2])
            low_price = float(latest_kline[3])
            close_price = float(latest_kline[4])
            volume = float(latest_kline[7])
            timestamp = int(latest_kline[0])
            
            # Get bid-ask spread
            ticker = await self.exchange.get_ticker_price(symbol)
            bid = float(ticker.get("bidPrice", close_price))
            ask = float(ticker.get("askPrice", close_price))
            spread = ask - bid if ask > bid else 0.01
            
            snapshot = MarketSnapshot(
                symbol=symbol,
                timestamp=datetime.utcfromtimestamp(timestamp / 1000),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                spread=spread,
            )
            
            logger.debug(f"binance_snapshot_fetched_{symbol}", close=close_price)
            return snapshot
            
        except Exception as e:
            logger.warning(f"binance_snapshot_fetch_failed_{symbol}", error=str(e), exc_info=True)
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
