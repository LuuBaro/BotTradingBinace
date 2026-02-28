
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import TraderContext, Decision, TradeJournal

async def analyze_strategy():
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select, desc
        
        # 1. Get current strategy
        res = await session.execute(select(TraderContext).order_by(desc(TraderContext.timestamp)).limit(1))
        context = res.scalar_one_or_none()
        print("\n=== CURRENT STRATEGY PROMPT ===")
        if context:
            print(f"Trader: {context.trader_name}")
            print(f"Prompt: {context.prompt}")
        else:
            print("No strategy context found.")

        # 2. Get recent decisions for losing trades
        print("\n=== RECENT DECISION RATIONALES ===")
        res = await session.execute(select(Decision).order_by(desc(Decision.timestamp)).limit(10))
        decisions = res.scalars().all()
        for d in decisions:
            # Extract symbol and side from decision_json or order_spec
            symbol = d.decision_json.get("symbol") if isinstance(d.decision_json, dict) else "UNKNOWN"
            side = d.decision_json.get("side") if isinstance(d.decision_json, dict) else "UNKNOWN"
            if not symbol and d.order_spec:
                symbol = d.order_spec.get("symbol")
            if not side and d.order_spec:
                side = d.order_spec.get("side")
            
            print(f"[{d.timestamp}] SYMBOL: {symbol} | SIDE: {side} | TYPE: {d.decision_type} | STATUS: {d.status}")
            print(f"Rationale: {d.rationale}")
            print(f"Risk Assessment: {d.risk_assessment}")
            print("-" * 50)

        # 3. Get recent trade journal entries to see actual win/loss
        print("\n=== RECENT TRADES (JOURNAL) ===")
        res = await session.execute(select(TradeJournal).order_by(desc(TradeJournal.closed_at)).limit(10))
        trades = res.scalars().all()
        for t in trades:
            print(f"[{t.closed_at}] {t.symbol} {t.side} | PNL: {t.pnl} | EXIT: {t.exit_reason}")
            # Try to find the decision that opened this trade
            # Note: trace_id might be different if it's a SL/TP exit
            print(f"TraceID: {t.trace_id}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(analyze_strategy())
