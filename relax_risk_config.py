"""
Adjust Risk Config to Enable MORE AI Trading
Giảm threshold để AI dễ vào lệnh hơn
"""
import asyncio
from packages.shared.database import AsyncSessionFactory, init_db
from packages.shared.models import BotConfig
from packages.shared.schemas import RiskConfig
from sqlalchemy import select


async def adjust_config():
    """Make risk config more permissive for testing"""
    await init_db()
    
    async with AsyncSessionFactory() as session:
        # Load current config
        result = await session.execute(
            select(BotConfig).where(BotConfig.is_active == True).order_by(BotConfig.id.desc())
        )
        config = result.scalar_one_or_none()
        
        if not config:
            print("❌ No active config found!")
            return
        
        # Update risk config to be more permissive
        new_risk = RiskConfig(
            enabled=True,
            max_drawdown_day_pct=0.10,           # ↑ Từ 5% lên 10% (học hỏi thêm)
            max_daily_loss_pct=0.05,             # ↑ Từ 3% lên 5%
            max_position_pct=0.20,               # ↑ Từ 15% lên 20%
            max_position_per_symbol=0.10,        # ↑ Từ 8% lên 10%
            max_leverage=5,
            max_risk_per_trade_pct=0.025,        # ↑ Từ 2% lên 2.5%
            max_orders_per_hour=15,              # ↑ Từ 10 lên 15
            max_concurrent_positions=4,          # ↑ Từ 3 lên 4
            max_consecutive_losses=4,            # ↑ Từ 3 lên 4
            min_risk_reward_ratio=1.2,           # ↓ Từ 1.5 xuống 1.2 (dễ hơn)
            min_confidence_level=0.55,           # ↓ Từ 0.7 xuống 0.55 (AI tự tin hơn)
            min_balance_threshold=100.0,
            cooldown_after_loss=300,             # ↓ Từ 600 xuống 5 phút
            recovery_days_after_max_loss=0,      # Không cần tạm dừng
            mandatory_sl_tp=True,
            max_slippage_pct=0.01,               # ↑ Từ 0.5% lên 1%
            use_trailing_stop=True,
        )
        
        config.risk_json = new_risk.model_dump()
        session.add(config)
        await session.commit()
        
        print("✅ RISK CONFIG UPDATED FOR MORE AI TRADING!")
        print("\n🔧 Thay đổi:")
        print("   • min_confidence_level: 0.70 → 0.55 (AI tự tin 55% là được)")
        print("   • min_risk_reward_ratio: 1.5 → 1.2 (R/R yêu cầu thấp hơn)")
        print("   • max_position_pct: 15% → 20% (Lệnh lớn hơn)")
        print("   • max_concurrent_positions: 3 → 4 (Nhiều lệnh hơn)")
        print("   • cooldown_after_loss: 600s → 300s (Faster recovery)")
        print("\n🔄 Khởi động lại backend và worker để áp dụng!")


if __name__ == "__main__":
    asyncio.run(adjust_config())
