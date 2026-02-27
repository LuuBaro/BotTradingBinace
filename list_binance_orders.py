
import asyncio
from packages.shared.exchange.binance_futures import BinanceFuturesClient

async def list_orders(symbol):
    async with BinanceFuturesClient() as client:
        orders = await client.get_all_orders(symbol, limit=10)
        print(f"{'ID':<15} | {'Side':<10} | {'Status':<15} | {'Qty':<10} | {'Price':<10}")
        print("-" * 65)
        for o in reversed(orders):
            print(f"{o['orderId']:<15} | {o['side']:<10} | {o['status']:<15} | {o['origQty']:<10} | {o['avgPrice']:<10}")

if __name__ == "__main__":
    asyncio.run(list_orders("BTCUSDT"))
