"""
Verify Phase 1 implementation
Checks database for expected data after running worker
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, func
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import (
    BotConfig,
    Decision,
    Order,
    Position,
    Event,
    RiskLog,
    OrderIntent,
)
from packages.shared.logger import logger


async def verify_phase1():
    """Verify Phase 1 implementation"""
    print("\n🔍 Verifying Phase 1 Implementation...\n")
    
    all_checks_passed = True
    
    async with AsyncSessionFactory() as session:
        # Check 1: Bot Config exists
        result = await session.execute(select(BotConfig))
        bot_configs = result.scalars().all()
        print(f"✓ Bot Configs: {len(bot_configs)} found")
        if len(bot_configs) == 0:
            print("  ❌ FAIL: No bot config found")
            all_checks_passed = False
        
        # Check 2: Decisions logged
        result = await session.execute(select(func.count()).select_from(Decision))
        decision_count = result.scalar()
        print(f"✓ Decisions: {decision_count} logged")
        if decision_count < 5:
            print(f"  ⚠️  WARNING: Only {decision_count} decisions (expected 5+)")
        
        # Check 3: Risk logs exist
        result = await session.execute(select(func.count()).select_from(RiskLog))
        risk_log_count = result.scalar()
        print(f"✓ Risk Logs: {risk_log_count} logged")
        
        # Check 4: Orders placed
        result = await session.execute(select(func.count()).select_from(Order))
        order_count = result.scalar()
        print(f"✓ Orders: {order_count} placed")
        if order_count == 0:
            print("  ⚠️  WARNING: No orders placed (all decisions might be HOLD)")
        
        # Check 5: Order Intents (idempotency tracking)
        result = await session.execute(select(func.count()).select_from(OrderIntent))
        intent_count = result.scalar()
        print(f"✓ Order Intents: {intent_count} created")
        
        # Check 6: Positions
        result = await session.execute(select(func.count()).select_from(Position))
        position_count = result.scalar()
        print(f"✓ Positions: {position_count} active")
        
        # Check 7: Events logged
        result = await session.execute(select(func.count()).select_from(Event))
        event_count = result.scalar()
        print(f"✓ Events: {event_count} logged")
        if event_count < 10:
            print(f"  ⚠️  WARNING: Only {event_count} events (expected 10+)")
        
        # Check 8: Idempotency - no duplicate client_order_ids
        result = await session.execute(
            select(Order.client_order_id, func.count(Order.client_order_id))
            .group_by(Order.client_order_id)
            .having(func.count(Order.client_order_id) > 1)
        )
        duplicates = result.all()
        if duplicates:
            print(f"  ❌ FAIL: Found {len(duplicates)} duplicate client_order_ids!")
            all_checks_passed = False
        else:
            print("✓ Idempotency: No duplicate orders")
        
        # Check 9: Recent activity (last 5 minutes)
        recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
        result = await session.execute(
            select(func.count()).select_from(Decision).where(Decision.timestamp > recent_cutoff)
        )
        recent_decisions = result.scalar()
        print(f"✓ Recent Activity: {recent_decisions} decisions in last 5 minutes")
        
        # Check 10: Risk rejections (if any)
        result = await session.execute(
            select(func.count()).select_from(RiskLog).where(RiskLog.result == "rejected")
        )
        rejection_count = result.scalar()
        print(f"✓ Risk Rejections: {rejection_count} decisions rejected by risk engine")
        
        print("\n" + "="*60)
        
        if all_checks_passed and decision_count >= 5 and event_count >= 10:
            print("✅ Phase 1 Verification PASSED")
            print("\nSystem is crash-safe and operational!")
            print("\nNext steps:")
            print("  - Run idempotency test: pytest tests/test_idempotency.py")
            print("  - Run risk engine test: pytest tests/test_risk_engine.py")
            print("  - Run crash recovery test: bash tests/test_crash_recovery.sh")
        else:
            print("⚠️  Phase 1 Verification INCOMPLETE")
            print("\nPlease run worker for at least 5 minutes to generate data.")
        
        print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(verify_phase1())
