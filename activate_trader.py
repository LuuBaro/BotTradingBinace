
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select, update
from packages.shared.models import User, BotConfig

async def fix_trader():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(User).where(User.username == "trader"))
        user = res.scalar_one_or_none()
        if not user:
            print("Trader user not found")
            return

        print(f"Fixing trader: {user.username} ({user.id})")
        
        # Check for any configs
        cfg_res = await db.execute(select(BotConfig).where(BotConfig.user_id == user.id))
        cfgs = cfg_res.scalars().all()
        
        if cfgs:
            print(f"Found {len(cfgs)} inactive configs. Activating the latest one...")
            latest = sorted(cfgs, key=lambda x: x.id, reverse=True)[0]
            latest.is_active = True
            await db.commit()
            print(f"Activated config ID: {latest.id}")
        else:
            print("No configs found at all. Creating a default active config...")
            new_cfg = BotConfig(
                user_id=user.id,
                env="demo",
                version=1,
                is_active=True,
                risk_json={
                    "max_drawdown_day_pct": 0.05,
                    "max_position_pct": 0.3,
                    "max_leverage": 5,
                    "max_risk_per_trade_pct": 0.02,
                    "max_orders_per_hour": 10,
                    "max_concurrent_positions": 3,
                    "cooldown_after_loss": 300,
                    "mandatory_sl_tp": True
                },
                symbols_json=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                approval_mode=False
            )
            db.add(new_cfg)
            await db.commit()
            print("Created default active config.")

if __name__ == "__main__":
    asyncio.run(fix_trader())
