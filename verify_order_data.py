
import asyncio
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from packages.shared.config import settings

async def verify_order(order_id: int, symbol: str):
    print(f"--- Verifying Order {order_id} for {symbol} ---")
    print(f"Environment: {'Testnet' if settings.binance_testnet else 'Mainnet'}")
    
    async with BinanceFuturesClient() as client:
        try:
            # We use get_all_orders or a specific order endpoint if available
            # get_all_orders(symbol, orderId=...)
            orders = await client._request("GET", "/fapi/v1/allOrders", params={"symbol": symbol, "orderId": order_id}, signed=True)
            
            if not orders or not isinstance(orders, list):
                 # Try single order endpoint
                 order = await client._request("GET", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id}, signed=True)
                 orders = [order]
            
            for o in orders:
                if str(o['orderId']) == str(order_id):
                    print(f"ID: {o['orderId']}")
                    print(f"Status: {o['status']}")
                    print(f"Side: {o['side']}")
                    print(f"PositionSide: {o.get('positionSide')}")
                    print(f"Price: {o['price']}")
                    print(f"Avg Price: {o.get('avgPrice')}")
                    print(f"Orig Qty: {o['origQty']}")
                    print(f"Executed Qty: {o['executedQty']}")
                    print(f"Type: {o['type']}")
                    print(f"Time: {o['time']}")
                    return
            print("Order not found in history.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # From screenshot: 12554053836
    asyncio.run(verify_order(12554053836, "BTCUSDT"))
