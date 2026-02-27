
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select
from packages.shared.models import Decision

async def check_decision():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(Decision).where(Decision.trace_id.like('%72b95e1c%')))
        d = res.scalar_one_or_none()
        if d:
            print(f"Decision Found:")
            print(f"Trace: {d.trace_id}")
            print(f"Action: {d.decision_json.get('action')}")
            print(f"Side: {d.decision_json.get('side')}")
        else:
            print("No decision found for trace 72b95e1c")

if __name__ == "__main__":
    asyncio.run(check_decision())
