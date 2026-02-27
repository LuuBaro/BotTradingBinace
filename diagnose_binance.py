
import asyncio
import os
import sys
from packages.shared.config import settings
from packages.shared.exchange.binance_futures import BinanceFuturesClient

async def diagnose_account():
    print(f"--- SYSTEM DIAGNOSTIC REPORT ---")
    print(f"Current .env Config:")
    print(f"- BINANCE_TESTNET: {settings.binance_testnet}")
    print(f"- API Key: {settings.binance_api_key[:10]}...")
    
    envs = [
        ("Testnet", "https://testnet.binancefuture.com"),
        ("Mainnet", "https://fapi.binance.com")
    ]
    
    for name, url in envs:
        print(f"\nChecking {name} ({url})...")
        client = BinanceFuturesClient()
        client.base_url = url
        import aiohttp
        connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
        async with aiohttp.ClientSession(connector=connector) as session:
            client.session = session
            try:
                acc_info = await client.get_account_info()
                print(f"FOUND MATCH with {name}!")
                print(f"- Balance: {acc_info.get('totalWalletBalance')} USDT")
                
                positions = await client.get_position_risk()
                active = [p for p in positions if float(p['positionAmt']) != 0]
                print(f"- Open Positions: {len(active)}")
                for p in active:
                    print(f"  + {p['symbol']}: {p['positionAmt']} (Entry: {p['entryPrice']})")
                
                print(f"\nFIX: You should set BINANCE_TESTNET='{'true' if name == 'Testnet' else 'false'}' in .env")
            except Exception as e:
                print(f"Connection to {name} failed or unauthorized.")

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    asyncio.run(diagnose_account())
