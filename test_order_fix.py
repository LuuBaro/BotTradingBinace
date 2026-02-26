
import asyncio
import aiohttp
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from packages.shared.enums import Side, OrderType

async def test_order():
    client = BinanceFuturesClient()
    async with client:
        # Get balance first to verify connection
        print("Getting account info...")
        try:
            account = await client.get_account_info()
            print(f"Success! Account total wallet balance: {account.get('totalWalletBalance')}")
            
            print("\nTrying to set leverage to 5...")
            try:
                leverage_res = await client.set_leverage(symbol="BTCUSDT", leverage=5)
                print(f"Leverage result: {leverage_res}")
            except Exception as e:
                print(f"Leverage set failed: {e}")

            # Try to place a very small order
            try:
                # BTCUSDT min quantity is usually 0.001 or 0.002
                # Let's try 0.002
                # We also need more balance info for rounding if we were doing it properly, 
                # but here we just test if 'side' error is gone.
                result = await client.place_order(
                    symbol="BTCUSDT",
                    side=Side.LONG,
                    order_type=OrderType.MARKET,
                    quantity=0.002
                )
                print(f"Order result: {result}")
            except Exception as e:
                print(f"Order failed (expected if params wrong): {e}")
                if hasattr(e, 'status'):
                    print(f"Status: {e.status}")
        except Exception as e:
            print(f"Failed to get account info: {e}")

if __name__ == "__main__":
    asyncio.run(test_order())
