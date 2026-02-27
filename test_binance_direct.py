import asyncio
import aiohttp
import time
import hmac
import hashlib
from packages.shared.config import settings

async def test_all_symbols():
    api_key = settings.binance_api_key
    api_secret = settings.binance_api_secret
    base_url = "https://testnet.binancefuture.com" if settings.binance_testnet else "https://fapi.binance.com"
    
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())) as session:
        # 1. Get symbols with positions
        timestamp = int(time.time() * 1000)
        query = f"timestamp={timestamp}"
        signature = hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        
        headers = {"X-MBX-APIKEY": api_key}
        url = f"{base_url}/fapi/v2/positionRisk?{query}&signature={signature}"
        
        async with session.get(url, headers=headers) as res:
            if res.status != 200:
                print(f"Error fetching positions: {await res.text()}")
                return
            positions = await res.json()
            
        active_symbols = [p['symbol'] for p in positions if float(p['positionAmt']) != 0]
        print(f"Active symbols (with positions): {active_symbols}")
        
        # 2. Try fetching trades for BTCUSDT anyway
        query = f"symbol=BTCUSDT&timestamp={timestamp}"
        signature = hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        url = f"{base_url}/fapi/v1/userTrades?{query}&signature={signature}"
        
        async with session.get(url, headers=headers) as res:
            print(f"BTCUSDT trades status: {res.status}")
            if res.status == 200:
                trades = await res.json()
                print(f"Found {len(trades)} trades for BTCUSDT")
            else:
                print(f"Error BTCUSDT: {await res.text()}")

if __name__ == "__main__":
    asyncio.run(test_all_symbols())
