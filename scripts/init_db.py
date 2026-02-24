"""
Initialize database with default configuration
Run this after: alembic upgrade head
"""
import asyncio
from datetime import datetime
from packages.shared.database import AsyncSessionFactory, init_db
from packages.shared.models import BotConfig, PromptPack
from packages.shared.schemas import RiskConfig
from packages.shared.logger import logger


async def seed_database():
    """Seed database with initial data"""
    logger.info("database_seeding_started")
    
    # Initialize database
    await init_db()
    
    async with AsyncSessionFactory() as session:
        # Check if bot config already exists
        from sqlalchemy import select
        result = await session.execute(select(BotConfig))
        existing_config = result.scalar_one_or_none()
        
        if existing_config:
            logger.info("database_already_seeded")
            return
        
        # Create default risk config
        risk_config = RiskConfig(
            max_drawdown_day_pct=0.05,
            max_position_pct=0.3,
            max_leverage=5,
            max_risk_per_trade_pct=0.02,
            max_orders_per_hour=10,
            max_concurrent_positions=3,
            cooldown_after_loss=300,
            mandatory_sl_tp=True,
        )
        
        # Create default bot config
        bot_config = BotConfig(
            env="demo",
            symbols_json={"symbols": ["BTCUSDT", "ETHUSDT"]},
            risk_json=risk_config.model_dump(),
            execution_json={
                "slippage_tolerance": 0.001,
                "max_order_retry": 3,
            },
            version=1,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(bot_config)
        
        # Create default prompt pack (placeholder for Phase 5)
        prompt_pack = PromptPack(
            name="default_trader_v1",
            version="1.0.0",
            content_json={
                "system_prompt": "You are a professional crypto trader.",
                "decision_prompt": "Analyze market and make decision.",
                "risk_prompt": "Consider risk management.",
            },
            created_at=datetime.utcnow(),
        )
        session.add(prompt_pack)
        
        await session.commit()
        
        logger.info(
            "database_seeded_successfully",
            bot_config_version=bot_config.version,
            prompt_pack_version=prompt_pack.version,
        )
        
        print("\n✅ Database seeded successfully!")
        print(f"   Bot Config Version: {bot_config.version}")
        print(f"   Prompt Pack: {prompt_pack.name} v{prompt_pack.version}")
        print(f"   Risk Config: {risk_config.model_dump()}")


if __name__ == "__main__":
    asyncio.run(seed_database())
