import asyncio
import json
from packages.shared.exchange.binance_futures import BinanceFuturesClient

async def test_client():
    async with BinanceFuturesClient() as client:
        # 1. Get balance
        balance = await client.get_balance()
        print(f"Balance: {balance}")
        
        # 2. Get positions
        positions = await client.get_position_risk()
        active = [p['symbol'] for p in positions if float(p['positionAmt']) != 0]
        print(f"Active Symbols: {active}")
        
        # 3. Get trades for some symbols
        test_symbols = active if active else ["BTCUSDT", "ETHUSDT"]
        for s in test_symbols:
            trades = await client.get_user_trades(s, limit=10)
            print(f"Trades for {s}: {len(trades)}")
            if trades:
                print(trades[0])

if __name__ == "__main__":
    asyncio.run(test_client())
