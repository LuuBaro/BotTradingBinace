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
from sqlalchemy import select
from packages.shared.config import settings
from packages.shared.database import AsyncSessionFactory, init_db, close_db
from packages.shared.models import BotConfig, Decision as DecisionModel, RiskLog, Position
from packages.shared.schemas import RiskConfig, MarketSnapshot
from packages.shared.exchange.mock import MockExchange
from packages.shared.risk_engine import RiskEngine
from packages.shared.logger import logger
from apps.worker.agents.trader_stub import TraderStub
from apps.worker.engine.execution import ExecutionEngine


class TradingWorker:
    """
    Main trading worker orchestrator
    Runs the decision → validation → execution loop
    """

    def __init__(self):
        self.running = False
        self.exchange = MockExchange()
        self.trader = TraderStub()
        self.execution_engine = ExecutionEngine(self.exchange)
        self.risk_engine: RiskEngine | None = None
        self.loop_count = 0

    async def initialize(self) -> None:
        """Initialize worker"""
        logger.info("worker_initializing")
        
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
        
        logger.info("worker_initialized")

    async def run(self) -> None:
        """Main worker loop"""
        self.running = True
        logger.info("worker_started", loop_interval_sec=settings.worker_loop_interval_sec)
        
        while self.running:
            try:
                self.loop_count += 1
                await self._execute_loop_iteration()
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
                # Step 1: Generate mock market snapshot
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
                )
                session.add(decision_record)
                await session.flush()

                logger.info(
                    "decision_made",
                    trace_id=trace_id,
                    action=decision.action.value,
                    regime=decision.regime.value,
                    confidence=decision.confidence,
                )

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

                    # Step 5: Execute if approved
                    if risk_result.approved:
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
                    else:
                        logger.warning(
                            "decision_rejected_by_risk",
                            trace_id=trace_id,
                            reason=risk_result.reason,
                        )

                await session.commit()
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

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("worker_shutting_down")
        self.running = False
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
