#!/usr/bin/env python
import asyncio
from sqlalchemy import select, desc
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, BotConfig, Position, Decision, RiskLog


def fmt(v):
    try:
        return f"{float(v):,.6f}"
    except Exception:
        return str(v)


async def main():
    async with AsyncSessionFactory() as session:
        users = (await session.execute(select(User))).scalars().all()
        print("=" * 80)
        print("USER LOSS DIAGNOSTIC")
        print("=" * 80)

        for u in users:
            print(f"\n--- User: {u.username} | role={u.role} | id={u.id}")

            cfg = (await session.execute(
                select(BotConfig)
                .where(BotConfig.user_id == u.id)
                .order_by(desc(BotConfig.id))
                .limit(1)
            )).scalar_one_or_none()

            if cfg:
                risk = cfg.risk_json or {}
                print("  Risk config:")
                for k in [
                    "max_position_pct", "max_leverage", "max_risk_per_trade_pct",
                    "max_concurrent_positions", "max_orders_per_hour", "mandatory_sl_tp"
                ]:
                    print(f"    - {k}: {risk.get(k)}")
            else:
                print("  Risk config: NONE")

            positions = (await session.execute(
                select(Position).where(Position.user_id == u.id)
            )).scalars().all()
            print(f"  Open positions: {len(positions)}")
            for p in positions:
                notional = (float(p.qty or 0) * float(p.entry_price or 0))
                pnl = float(p.unrealized_pnl or 0)
                pnl_pct_on_notional = (pnl / notional * 100) if notional else 0
                print(
                    f"    * {p.symbol} {p.side} qty={fmt(p.qty)} entry={fmt(p.entry_price)} mark? liq={fmt(p.liquidation_price)} lev={p.leverage}"
                )
                print(
                    f"      notional≈${notional:,.2f} unrealized_pnl=${pnl:,.2f} ({pnl_pct_on_notional:.2f}% of notional)"
                )

            decisions = (await session.execute(
                select(Decision)
                .where(Decision.user_id == u.id)
                .order_by(desc(Decision.timestamp))
                .limit(5)
            )).scalars().all()
            print(f"  Last decisions: {len(decisions)}")
            for d in decisions:
                dj = d.decision_json or {}
                print(
                    f"    - {d.timestamp} status={d.status} type={d.decision_type} symbol={dj.get('symbol')} size_pct={dj.get('size_pct')} lev={dj.get('leverage')}"
                )

            risks = (await session.execute(
                select(RiskLog)
                .where(RiskLog.user_id == u.id)
                .order_by(desc(RiskLog.timestamp))
                .limit(3)
            )).scalars().all()
            print(f"  Last risk logs: {len(risks)}")
            for r in risks:
                print(f"    - {r.timestamp} {r.result}: {r.reason[:140]}")

if __name__ == '__main__':
    asyncio.run(main())
