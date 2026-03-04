#!/usr/bin/env python3
"""
Check Binance wallet balance and compare with demo account
"""
import asyncio
import json
from packages.shared.exchange.binance_futures import BinanceFuturesClient

async def main():
    client = BinanceFuturesClient()
    
    print("=" * 80)
    print("📊 GETTING WALLET BALANCE FROM BINANCE API")
    print("=" * 80)
    print(f"✓ Connected to: {client.base_url}")
    print()
    
    try:
        async with client:
            # Get account info
            account_info = await client.get_account_info()
            
            print("📈 ACCOUNT DATA:")
            print("-" * 80)
            # Only print selected fields to keep it readable
            print(json.dumps({
                'totalInitialMargin': account_info.get('totalInitialMargin'),
                'totalMaintMargin': account_info.get('totalMaintMargin'),
                'totalWalletBalance': account_info.get('totalWalletBalance'),
                'totalUnrealizedProfit': account_info.get('totalUnrealizedProfit'),
                'assets_count': len(account_info.get('assets', []))
            }, indent=2))
            print()
            
            # Extract wallet balance
            if 'assets' in account_info and len(account_info['assets']) > 0:
                print("💰 WALLET BALANCES:")
                print("-" * 80)
                total_usdt = 0
                for asset in account_info['assets']:
                    symbol = asset.get('asset', 'UNKNOWN')
                    wallet_balance = float(asset.get('walletBalance', 0))
                    available_balance = float(asset.get('availableBalance', 0))
                    
                    if wallet_balance > 0.0001 or available_balance > 0.0001:
                        print(f"{symbol:10s} | Wallet: {wallet_balance:15.8f} | Available: {available_balance:15.8f}")
                        
                        # Sum USDT
                        if symbol == 'USDT':
                            total_usdt = wallet_balance
                
                print("-" * 80)
                print(f"🎯 TOTAL USDT IN WALLET: {total_usdt:.2f}")
                print()
                print("📌 REFERENCE FROM SCREENSHOT: $5,154.03")
                print()
                if abs(total_usdt - 5154.03) < 1:
                    print("✅ MATCH! Balance matches your Binance dashboard")
                else:
                    print(f"⚠️  MISMATCH! Expected ~5154.03, got {total_usdt:.2f}")
                    print(f"   Difference: {abs(total_usdt - 5154.03):.2f} USDT")
            else:
                print("⚠️  No assets found in account")
                
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
