"""
Test idempotency - same trace_id should not create duplicate orders
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory, init_db, drop_db
from packages.shared.models import OrderIntent, Order
from packages.shared.schemas import Decision
from packages.shared.enums import MarketRegime, ActionType, Side, OrderType
from packages.shared.exchange.mock import MockExchange
from apps.worker.engine.execution import ExecutionEngine


@pytest.fixture
async def setup_db():
    """Setup test database"""
    await drop_db()
    await init_db()
    yield
    await drop_db()


@pytest.fixture
def mock_decision():
    """Create a mock decision for testing"""
    return Decision(
        regime=MarketRegime.TREND,
        action=ActionType.OPEN,
        symbol="BTCUSDT",
        side=Side.LONG,
        entry_type=OrderType.MARKET,
        entry_price=50000.0,
        size_pct=0.1,
        leverage=3,
        stop_loss=49000.0,
        take_profit=52000.0,
        confidence=0.8,
        rationale="Test decision",
        checklist=[],
    )


@pytest.mark.asyncio
async def test_idempotent_order_execution(setup_db, mock_decision):
    """Test that executing same decision twice doesn't create duplicate orders"""
    exchange = MockExchange()
    execution_engine = ExecutionEngine(exchange)
    trace_id = str(uuid.uuid4())

    # Execute decision first time
    async with AsyncSessionFactory() as session:
        result1 = await execution_engine.execute_decision(
            decision=mock_decision,
            trace_id=trace_id,
            session=session,
        )
        await session.commit()

    assert result1["status"] == "success"
    first_client_order_id = result1["client_order_id"]

    # Execute same decision again with same trace_id
    async with AsyncSessionFactory() as session:
        result2 = await execution_engine.execute_decision(
            decision=mock_decision,
            trace_id=trace_id,  # Same trace_id!
            session=session,
        )
        await session.commit()

    # Second execution should be detected as duplicate
    assert result2["status"] == "duplicate"
    assert result2["client_order_id"] == first_client_order_id

    # Verify only one order intent exists
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(OrderIntent))
        intents = result.scalars().all()
        assert len(intents) == 1

        # Verify only one order exists
        result = await session.execute(select(Order))
        orders = result.scalars().all()
        # Should have 1 main order + SL + TP = 3 orders total
        assert len(orders) == 3


@pytest.mark.asyncio
async def test_different_trace_ids_create_separate_orders(setup_db, mock_decision):
    """Test that different trace_ids create separate orders"""
    exchange = MockExchange()
    execution_engine = ExecutionEngine(exchange)

    # Execute with first trace_id
    trace_id_1 = str(uuid.uuid4())
    async with AsyncSessionFactory() as session:
        result1 = await execution_engine.execute_decision(
            decision=mock_decision,
            trace_id=trace_id_1,
            session=session,
        )
        await session.commit()

    assert result1["status"] == "success"

    # Execute with second trace_id
    trace_id_2 = str(uuid.uuid4())
    async with AsyncSessionFactory() as session:
        result2 = await execution_engine.execute_decision(
            decision=mock_decision,
            trace_id=trace_id_2,
            session=session,
        )
        await session.commit()

    assert result2["status"] == "success"
    assert result1["client_order_id"] != result2["client_order_id"]

    # Verify two order intents exist
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(OrderIntent))
        intents = result.scalars().all()
        assert len(intents) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
