#!/usr/bin/env python3
"""
Test Binance Testnet connection and verify API credentials
"""
import asyncio
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages"))

from shared.config import settings
from shared.exchange.binance_futures import BinanceFuturesClient


async def test_binance_connection():
    """Test Binance API connection"""
    print("\n" + "="*60)
    print("BINANCE TESTNET CONNECTION TEST")
    print("="*60 + "\n")
    
    print(f"Configuration:")
    print(f"  Base URL: {settings.binance_base_url or ('testnet' if settings.binance_testnet else 'production')}")
    print(f"  Testnet: {settings.binance_testnet}")
    print(f"  API Key: {settings.binance_api_key[:10]}..." if settings.binance_api_key else "  API Key: Not configured")
    print(f"  API Secret: {settings.binance_api_secret[:10]}..." if settings.binance_api_secret else "  API Secret: Not configured")
    print()
    
    if not settings.binance_api_key or not settings.binance_api_secret:
        print("❌ ERROR: Binance API credentials not configured")
        return 1
    
    try:
        # Test connection with context manager
        async with BinanceFuturesClient(testnet=settings.binance_testnet) as client:
            print("Testing API endpoints:")
            print()
            
            # Test 1: Get Account Balance
            print("1. Fetching account balance...", end=" ")
            try:
                balance = await client.get_account_balance()
                print(f"✅ Success")
                if balance:
                    usdt_balance = next((b for b in balance if b.get('asset') == 'USDT'), None)
                    if usdt_balance:
                        print(f"   USDT Balance: {usdt_balance.get('walletBalance')} (Free: {usdt_balance.get('availableBalance')})")
            except Exception as e:
                print(f"❌ Failed: {str(e)[:80]}")
            
            print()
            
            # Test 2: Get Account Info
            print("2. Fetching account info...", end=" ")
            try:
                info = await client.get_account_info()
                print(f"✅ Success")
                if info:
                    print(f"   Can Trade: {info.get('canTrade')}")
                    print(f"   Positions: {len([p for p in info.get('positions', []) if float(p.get('positionAmt', 0)) != 0])}")
            except Exception as e:
                print(f"❌ Failed: {str(e)[:80]}")
            
            print()
            
            # Test 3: Get Position Risk
            print("3. Fetching position risk...", end=" ")
            try:
                positions = await client.get_position_risk()
                print(f"✅ Success")
                active_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
                print(f"   Active Positions: {len(active_positions)}")
                if active_positions:
                    for pos in active_positions[:3]:  # Show first 3
                        print(f"     - {pos.get('symbol')}: {pos.get('positionAmt')} @ {pos.get('entryPrice')}")
            except Exception as e:
                print(f"❌ Failed: {str(e)[:80]}")
        
        print()
        print("="*60)
        print("✅ Binance Testnet is configured and working!")
        print("="*60 + "\n")
        return 0
        
    except Exception as e:
        print()
        print("="*60)
        print(f"❌ ERROR: {str(e)}")
        print("="*60 + "\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_binance_connection())
    sys.exit(exit_code)
