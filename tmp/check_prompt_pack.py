import asyncio
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import PromptPack
from sqlalchemy import select
import json

async def check_prompt_pack():
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(PromptPack).where(PromptPack.id == 1))
        pack = result.scalar_one_or_none()
        if pack:
            print(f"PromptPack ID: {pack.id}")
            print(f"Name: {pack.name}")
            print(f"Content JSON keys: {pack.content_json.keys() if isinstance(pack.content_json, dict) else 'Not a dict'}")
            print(f"Full Content: {json.dumps(pack.content_json, indent=2)}")
        else:
            print("PromptPack not found")

asyncio.run(check_prompt_pack())
