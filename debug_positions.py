
import asyncio
from sqlalchemy import select
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Position, Decision
from datetime import datetime
from sqlalchemy import desc

async def test_positions_endpoint():
    async with AsyncSessionFactory() as session:
        try:
            result = await session.execute(select(Position))
            positions = result.scalars().all()
            print(f"Found {len(positions)} positions")

            pos_list = []
            for p in positions:
                print(f"Processing {p.symbol}")
                decision_result = await session.execute(
                    select(Decision)
                    .order_by(desc(Decision.timestamp))
                    .limit(20) 
                )
                decisions = decision_result.scalars().all()
                
                latest_decision = None
                for d in decisions:
                    if d.decision_json.get('symbol') == p.symbol:
                        latest_decision = d
                        break
                
                pos_data = {
                    "id": str(p.id),
                    "symbol": p.symbol,
                    "side": p.side,
                    "qty": float(p.qty),
                    "entry_price": float(p.entry_price),
                    "unrealized_pnl": float(p.unrealized_pnl) if p.unrealized_pnl else 0.0,
                    "leverage": int(p.leverage) if p.leverage else 1,
                    "margin_type": p.margin_type or "CROSSED",
                    "sl_order_id": p.sl_order_id,
                    "tp_order_id": p.tp_order_id,
                    "stop_loss": float(p.stop_loss) if p.stop_loss else None,
                    "take_profit": float(p.take_profit) if p.take_profit else None,
                    "liquidation_price": float(p.liquidation_price) if p.liquidation_price else None,
                    "opened_at": p.opened_at.isoformat() if p.opened_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                    "rationale": latest_decision.rationale if latest_decision else None,
                    "regime": latest_decision.regime if latest_decision else None,
                    "confidence": float(latest_decision.confidence) if latest_decision else 0.85,
                }
                pos_list.append(pos_data)
                print(f"Created pos_data for {p.symbol}")

            print("Success!")
            print(pos_list)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_positions_endpoint())
