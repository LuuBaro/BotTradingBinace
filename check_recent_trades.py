#!/usr/bin/env python3
"""
Check if recent trades shown in dashboard are real from Binance or mock data
"""
import asyncio
from packages.shared.exchange.binance_futures import BinanceFuturesClient

async def main():
    client = BinanceFuturesClient()
    
    print("=" * 80)
    print("🔍 CHECKING REAL TRADES FROM BINANCE")
    print("=" * 80)
    print(f"Connected to: {client.base_url}")
    print()
    
    try:
        async with client:
            # Check for real trades on BTCUSDT
            print("📊 Fetching REAL trades from BTCUSDT...")
            trades = await client.get_user_trades("BTCUSDT", limit=10)
            
            print(f"Found {len(trades)} trades")
            print()
            
            if len(trades) == 0:
                print("❌ NO REAL TRADES FOUND ON TESTNET")
                print("   This means:")
                print("   ✓ Your account is connected correctly")
                print("   ✗ But you have NOT placed ANY real trades yet")
                print()
                print("   The trades shown in dashboard are DEMO/MOCK DATA only!")
            else:
                print("✅ REAL TRADES FOUND ON TESTNET!")
                print()
                for i, trade in enumerate(trades[:5], 1):
                    print(f"Trade #{i}:")
                    print(f"  Symbol: {trade.get('symbol')}")
                    print(f"  Side: {trade.get('side')}")
                    print(f"  Price: {trade.get('price')}")
                    print(f"  Qty: {trade.get('qty')}")
                    print(f"  Profit/Loss: {trade.get('realizedPnl', 'N/A')}")
                    print(f"  Time: {trade.get('time')}")
                    print()
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
