
import asyncio
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from packages.shared.config import settings

async def check_binance():
    print(f"Testing Binance with API Key: {settings.binance_api_key[:5]}...")
    async with BinanceFuturesClient() as client:
        try:
            balance = await client.get_account_balance()
            print("Successfully connected to Binance!")
            
            positions = await client.get_position_risk()
            active_positions = [p for p in positions if float(p['positionAmt']) != 0]
            print(f"Found {len(active_positions)} active positions on Binance")
            for p in active_positions:
                print(f"  - {p['symbol']}: {p['positionAmt']} @ {p['entryPrice']}")
        except Exception as e:
            print(f"Failed to connect to Binance: {e}")

if __name__ == "__main__":
    asyncio.run(check_binance())
