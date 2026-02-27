
import asyncio
from packages.shared.database import AsyncSessionFactory, init_db
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from apps.worker.engine.reconciler import ReconcilerEngine
import logging

# Setup logging to see our debug messages
logging.basicConfig(level=logging.DEBUG)

async def test_manual_sync():
    await init_db()
    async with BinanceFuturesClient() as exchange:
        reconciler = ReconcilerEngine(exchange)
        async with AsyncSessionFactory() as session:
            print("--- TRIGGERING SYNC ---")
            await reconciler.sync_positions(session)
            print("--- SYNC COMPLETED ---")

if __name__ == "__main__":
    asyncio.run(test_manual_sync())
