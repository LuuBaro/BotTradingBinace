import asyncio
import aiohttp
import json
from packages.shared.config import settings
from packages.shared.exchange.binance_futures import BinanceFuturesClient

async def test_trades():
    if not settings.binance_api_key or not settings.binance_api_secret:
        print("Binance credentials missing")
        return

    client = BinanceFuturesClient()
    connector = aiohttp.TCPConnector()
    async with aiohttp.ClientSession(connector=connector) as session:
        client.session = session
        await client.sync_server_time()
        
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        for s in symbols:
            try:
                trades = await client.get_user_trades(s, limit=5)
                print(f"Symbol {s}: Found {len(trades)} trades")
                if trades:
                    print(json.dumps(trades[0], indent=2))
            except Exception as e:
                print(f"Error for {s}: {e}")

if __name__ == "__main__":
    asyncio.run(test_trades())
