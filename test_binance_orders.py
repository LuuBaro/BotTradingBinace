import asyncio
import aiohttp
from packages.shared.config import settings
from packages.shared.exchange.binance_futures import BinanceFuturesClient

async def get_orders():
    client = BinanceFuturesClient()
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    async with aiohttp.ClientSession(connector=connector) as session:
        client.session = session
        await client.sync_server_time()
        print("Fetching ALL orders from Binance...")
        binance_orders = await client.get_all_orders("BTCUSDT", limit=50)
        print("GOT", len(binance_orders), "orders.")
        for o in binance_orders[:2]:
            print(o)

if __name__ == "__main__":
    asyncio.run(get_orders())
