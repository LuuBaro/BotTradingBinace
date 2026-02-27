
import asyncio
import json
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select
from packages.shared.models import BotConfig

async def check_config():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(BotConfig).order_by(BotConfig.id.desc()).limit(1))
        c = res.scalar_one_or_none()
        if c:
            print(json.dumps(c.risk_json, indent=2))
        else:
            print("No config found")

if __name__ == "__main__":
    asyncio.run(check_config())
