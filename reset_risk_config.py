"""
Reset Risk Configuration to New Enhanced Parameters
Xóa cấu hình cũ, tạo mới với tất cả 22 tham số
"""
import asyncio
from sqlalchemy import delete
from packages.shared.database import AsyncSessionFactory, init_db
from packages.shared.models import BotConfig
from packages.shared.schemas import RiskConfig


async def reset_config():
    """Reset BotConfig to new risk parameters"""
    await init_db()
    
    async with AsyncSessionFactory() as session:
        # Delete all old configs
        await session.execute(delete(BotConfig))
        await session.commit()
        print("✅ Deleted all old configs")
        
        # Create new enhanced risk config
        risk_config = RiskConfig(
            enabled=True,
            max_drawdown_day_pct=0.05,
            max_daily_loss_pct=0.03,
            max_position_pct=0.15,
            max_position_per_symbol=0.08,
            max_leverage=5,
            max_risk_per_trade_pct=0.02,
            max_orders_per_hour=10,
            max_concurrent_positions=3,
            max_consecutive_losses=3,
            min_risk_reward_ratio=1.5,
            min_confidence_level=0.7,
            min_balance_threshold=100.0,
            cooldown_after_loss=600,
            recovery_days_after_max_loss=1,
            mandatory_sl_tp=True,
            max_slippage_pct=0.005,
            use_trailing_stop=True,
        )
        
        # Create new bot config
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
        )
        
        session.add(bot_config)
        await session.commit()
        
        print("\n✅ ĐÃ CẬP NHẬT RISK CONFIG")
        print("\n📊 Các tham số mới:")
        for key, value in risk_config.model_dump().items():
            print(f"  • {key}: {value}")
        print("\n🔄 Hãy refresh dashboard để xem 22 tham số mới !")


if __name__ == "__main__":
    asyncio.run(reset_config())
