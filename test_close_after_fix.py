import asyncio
from sqlalchemy import select

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Position
from packages.shared.schemas import Decision
from packages.shared.enums import ActionType, MarketRegime, Side
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from apps.worker.engine.execution import ExecutionEngine


async def main():
    symbol = "XRPUSDT"

    async with AsyncSessionFactory() as session:
        pos_result = await session.execute(select(Position).where(Position.symbol == symbol))
        pos = pos_result.scalar_one_or_none()
        if not pos:
            print(f"No DB position for {symbol}")
            return

        print(f"DB Position: {pos.symbol} side={pos.side} qty={pos.qty}")

        # Side is not used by _close_position logic, but schema requires it
        decision = Decision(
            regime=MarketRegime.RANGE,
            action=ActionType.CLOSE,
            symbol=symbol,
            side=Side.SHORT,
            size_pct=0.01,
            leverage=1,
            entry_price=float(pos.entry_price),
            confidence=1.0,
            rationale="Manual test close after side-fix",
            checklist=[]
        )

        async with BinanceFuturesClient() as exchange:
            engine = ExecutionEngine(exchange)
            trace_id = "manualfix_xrp_001"
            try:
                result = await engine.execute_decision(decision=decision, trace_id=trace_id, session=session)
                print("Execution result:", result)
            except Exception as e:
                print("Execution error:", str(e))


if __name__ == "__main__":
    asyncio.run(main())
