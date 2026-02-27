
import asyncio
import json
from packages.shared.exchange.binance_futures import BinanceFuturesClient

async def get_raw_order(order_id, symbol):
    async with BinanceFuturesClient() as client:
        order = await client._request("GET", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id}, signed=True)
        print(json.dumps(order, indent=2))

if __name__ == "__main__":
    asyncio.run(get_raw_order(12554053836, "BTCUSDT"))
