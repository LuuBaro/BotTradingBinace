"""
Switch to Mock LLM Mode for Testing
Chuyển sang chế độ mock (AI giả định) để test không cần API credit
"""
import asyncio
from packages.shared.database import AsyncSessionFactory, init_db
from packages.shared.models import BotConfig
from packages.shared.schemas import RiskConfig
from sqlalchemy import select


async def switch_to_mock():
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
        
        config.risk_json['mock_mode'] = True
        session.add(config)
        await session.commit()
        
        print("✅ SWITCHED TO MOCK MODE")
        print("\n📝 Để áp dụng:")
        print("   1. Chỉnh trong .env: SELECTED_LLM='mock'")
        print("   2. Restart backend và worker")
        print("\n⚠️ Lưu ý: Mock mode TỰ SỬ DỤNG các decision đã học từ trước")
        print("   AI không gọi OpenAI API, nên free nhưng decision kém sophisticated")


if __name__ == "__main__":
    asyncio.run(switch_to_mock())
