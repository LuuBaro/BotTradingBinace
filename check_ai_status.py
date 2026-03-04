"""
Check AI Status and Recent Activity
"""
import asyncio
from datetime import datetime
from packages.shared.database import AsyncSessionFactory, init_db
from packages.shared.models import BotConfig, Event, Decision
from sqlalchemy import select, desc


async def check_status():
    await init_db()
    
    async with AsyncSessionFactory() as session:
        # Check bot config
        print("\n" + "="*60)
        print("🤖 BOT CONFIG STATUS")
        print("="*60)
        result = await session.execute(
            select(BotConfig).where(BotConfig.is_active == True).order_by(BotConfig.id.desc())
        )
        config = result.scalar_one_or_none()
        
        if config:
            print(f"✅ Active Config Found (v{config.version})")
            print(f"   Environment: {config.env}")
            print(f"   Symbols: {config.symbols_json}")
            
            risk = config.risk_json
            print(f"\n   Risk Config:")
            print(f"     • Enabled: {risk.get('enabled', 'N/A')}")
            print(f"     • Min Confidence: {risk.get('min_confidence_level', 'N/A')}")
            print(f"     • Min R/R: {risk.get('min_risk_reward_ratio', 'N/A')}")
            print(f"     • Max Leverage: {risk.get('max_leverage', 'N/A')}")
            print(f"     • Max Position %: {risk.get('max_position_pct', 'N/A')}")
            print(f"     • Mandatory SL/TP: {risk.get('mandatory_sl_tp', 'N/A')}")
        else:
            print("❌ NO ACTIVE BOT CONFIG FOUND!")
        
        # Check recent decisions
        print("\n" + "="*60)
        print("📊 AI DECISIONS (Last 5)")
        print("="*60)
        result = await session.execute(
            select(Decision).order_by(desc(Decision.timestamp)).limit(5)
        )
        decisions = result.scalars().all()
        
        if decisions:
            for dec in decisions:
                print(f"⏰ {dec.timestamp.strftime('%H:%M:%S')}")
                print(f"   Trace ID: {dec.trace_id}")
                print(f"   Type: {dec.decision_type}")
                print(f"   Status: {dec.status}")
                print(f"   Confidence: {dec.confidence}")
                print(f"   Risk Passed: {dec.risk_passed}")
                print()
        else:
            print("❌ NO DECISIONS MADE YET")
        
        # Check recent events
        print("="*60)
        print("🔔 RECENT EVENTS (Last 15)")
        print("="*60)
        result = await session.execute(
            select(Event).order_by(desc(Event.timestamp)).limit(15)
        )
        events = result.scalars().all()
        
        if events:
            for evt in events:
                ts = evt.timestamp.strftime("%H:%M:%S")
                print(f"{ts} [{evt.code:20s}] {evt.message}")
        else:
            print("❌ NO EVENTS FOUND")


if __name__ == "__main__":
    asyncio.run(check_status())
