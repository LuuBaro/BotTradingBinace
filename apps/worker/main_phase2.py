"""
Phase 2 Worker - Enhanced with Reconciliation and Circuit Breaker
Coordinates AI trading with reconciliation loop and safe mode
"""
import asyncio
import signal
import sys
import uuid
import random
from datetime import datetime
from sqlalchemy import select
from packages.shared.config import settings
from packages.shared.database import AsyncSessionFactory, init_db, close_db
from packages.shared.models import BotConfig, Decision as DecisionModel, RiskLog, Position, Event
from packages.shared.schemas import RiskConfig, MarketSnapshot
from packages.shared.exchange.mock import MockExchange
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from packages.shared.risk_engine import RiskEngine
from packages.shared.logger import logger
from apps.worker.agents.trader_stub import TraderStub
from apps.worker.engine.execution import ExecutionEngine
from apps.worker.engine.reconciler import ReconcilerEngine
from apps.worker.engine.circuit_breaker import CircuitBreaker


class Phase2TradingWorker:
    """
    Phase 2 trading worker with reconciliation and circuit breaker
    - Executes main trading loop (10s interval)
    - Reconciles positions every 5-10s
    - Monitors circuit breaker for safe mode
    - Respects pause/resume commands from API
    """

    def __init__(self):
        self.running = False
        self.paused = False
        self.loop_count = 0
        self.recon_count = 0
        
        # Initialize exchange (Binance or Mock based on settings)
        self._init_exchange()
        
        # Initialize components
        self.trader = TraderStub()
        self.execution_engine = ExecutionEngine(self.exchange)
        self.reconciler = ReconcilerEngine(self.exchange)
        self.circuit_breaker = CircuitBreaker()
        self.risk_engine: RiskEngine | None = None

    def _init_exchange(self):
        """Initialize exchange (Binance or Mock)"""
        if settings.binance_api_key and settings.binance_api_secret:
            # Use Binance
            self.exchange = BinanceFuturesClient()
            logger.info("exchange_initialized", type="binance_futures")
        else:
            # Use Mock (for development/testing)
            self.exchange = MockExchange()
            logger.info("exchange_initialized", type="mock_exchange")

    async def initialize(self) -> None:
        """Initialize worker"""
        logger.info("phase2_worker_initializing")
        
        # Initialize database
        await init_db()
        
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
        
        # Connect to exchange if Binance
        if isinstance(self.exchange, BinanceFuturesClient):
            await self.exchange.__aenter__()
            logger.info("binance_client_connected")
        
        logger.info("phase2_worker_initialized")

    async def run(self) -> None:
        """Main worker loop with separate reconciliation task"""
        self.running = True
        logger.info(
            "phase2_worker_started",
            loop_interval_sec=settings.worker_loop_interval_sec,
        )
        
        # Start background reconciliation task
        recon_task = asyncio.create_task(self._reconciliation_loop())
        
        try:
            while self.running:
                try:
                    self.loop_count += 1
                    
                    # Check if paused
                    if self.paused:
                        logger.debug("worker_paused_skipping_iteration")
                        await asyncio.sleep(settings.worker_loop_interval_sec)
                        continue
                    
                    # Check circuit breaker
                    if not self.circuit_breaker.is_safe_for_trading():
                        logger.warning("circuit_breaker_open_safe_mode")
                        # Still run the loop but won't execute new trades
                    
                    await self._execute_loop_iteration()
                    await asyncio.sleep(settings.worker_loop_interval_sec)
                
                except asyncio.CancelledError:
                    logger.info("worker_loop_cancelled")
                    break
                except Exception as e:
                    logger.error("worker_loop_error", error=str(e), exc_info=True)
                    await asyncio.sleep(5)
        
        finally:
            recon_task.cancel()
            try:
                await recon_task
            except asyncio.CancelledError:
                pass

    async def _execute_loop_iteration(self) -> None:
        """Execute one iteration of the trading loop"""
        trace_id = str(uuid.uuid4())
        logger.info("trading_iteration_start", loop_count=self.loop_count, trace_id=trace_id)

        async with AsyncSessionFactory() as session:
            try:
                # Generate market snapshot
                snapshot = self._generate_mock_snapshot()

                # Get AI decision
                decision = await self.trader.decide(snapshot)

                # Save decision to database
                decision_record = DecisionModel(
                    timestamp=datetime.utcnow(),
                    trace_id=trace_id,
                    decision_json=decision.model_dump(),
                    confidence=decision.confidence,
                    regime=decision.regime.value,
                )
                session.add(decision_record)
                await session.flush()

                logger.info(
                    "decision_made",
                    trace_id=trace_id,
                    action=decision.action.value,
                    confidence=decision.confidence,
                )

                # Risk validation
                if self.risk_engine:
                    positions_result = await session.execute(select(Position))
                    current_positions = [
                        {"symbol": p.symbol, "side": p.side, "qty": p.qty}
                        for p in positions_result.scalars().all()
                    ]

                    # Get balance
                    if isinstance(self.exchange, BinanceFuturesClient):
                        balance_info = await self.exchange.get_account_balance()
                        usdt_balance = next(
                            (b for b in balance_info if b["asset"] == "USDT"),
                            {"balance": "0"},
                        )
                        balance = float(usdt_balance.get("balance", 0))
                    else:
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

                    # Execute if approved and safe mode is off
                    if risk_result.approved and self.circuit_breaker.is_safe_for_trading():
                        try:
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
                            self.circuit_breaker.record_rest_request(success=True)
                        
                        except Exception as e:
                            logger.error("execution_failed", trace_id=trace_id, error=str(e))
                            self.circuit_breaker.record_rest_request(success=False)
                    
                    elif not risk_result.approved:
                        logger.warning(
                            "decision_rejected_by_risk",
                            trace_id=trace_id,
                            reason=risk_result.reason,
                        )
                    
                    else:
                        logger.warning("decision_skipped_safe_mode", trace_id=trace_id)

                await session.commit()
                logger.info("trading_iteration_completed", loop_count=self.loop_count)

            except Exception as e:
                await session.rollback()
                logger.error(
                    "trading_iteration_failed",
                    loop_count=self.loop_count,
                    error=str(e),
                    exc_info=True,
                )
                self.circuit_breaker.record_rest_request(success=False)

    async def _reconciliation_loop(self) -> None:
        """Background reconciliation loop (every 10 seconds)"""
        try:
            while self.running:
                try:
                    self.recon_count += 1
                    await asyncio.sleep(10)  # Reconcile every 10 seconds
                    
                    logger.info("reconciliation_starting", recon_count=self.recon_count)
                    
                    async with AsyncSessionFactory() as session:
                        # Run reconciliation
                        summary = await self.reconciler.reconcile(session)
                        
                        # Log summary
                        logger.info(
                            "reconciliation_completed",
                            recon_count=self.recon_count,
                            mismatches=summary["total_mismatches"],
                        )
                        
                        # If no mismatches, all good
                        if summary["total_mismatches"] == 0:
                            logger.info("reconciliation_no_mismatches")
                
                except asyncio.CancelledError:
                    logger.info("reconciliation_loop_cancelled")
                    break
                except Exception as e:
                    logger.error("reconciliation_loop_error", error=str(e))
                    # Continue on error, don't break the loop

        except Exception as e:
            logger.error("reconciliation_loop_fatal", error=str(e))

    def set_paused(self, paused: bool) -> None:
        """Set worker paused state"""
        self.paused = paused
        logger.info("worker_pause_state_changed", paused=paused)

    def _generate_mock_snapshot(self) -> MarketSnapshot:
        """Generate mock market data"""
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

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("phase2_worker_shutting_down")
        self.running = False
        
        # Disconnect from exchange if Binance
        if isinstance(self.exchange, BinanceFuturesClient):
            await self.exchange.__aexit__(None, None, None)
            logger.info("binance_client_disconnected")
        
        await close_db()
        logger.info("phase2_worker_shutdown_complete")


async def main():
    """Main entry point"""
    worker = Phase2TradingWorker()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig):
        logger.info("signal_received", signal=sig)
        asyncio.create_task(worker.shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    try:
        await worker.initialize()
        await worker.run()
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
