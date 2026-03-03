"""
Debug script to check wallet balance discrepancy
- Checks Binance account info
- Checks income history (realized PnL)
- Compares with bot's API response
"""
import asyncio
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from packages.shared.exchange.binance_futures import BinanceFuturesClient
from packages.shared.config import settings
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential, TradeJournal
from sqlalchemy import select, func, desc
from packages.shared.encryption import decrypt_key

async def debug_wallet():
    print("=" * 80)
    print("WALLET BALANCE DIAGNOSTIC")
    print("=" * 80)
    
    # Check if using admin credentials or specific user
    async with AsyncSessionFactory() as session:
        # Get first user credential (or you can specify user_id)
        cred_res = await session.execute(select(UserCredential).limit(1))
        cred = cred_res.scalar_one_or_none()
        
        if cred and cred.binance_api_key:
            api_key = decrypt_key(cred.binance_api_key)
            api_secret = decrypt_key(cred.binance_api_secret)
            use_testnet = cred.use_testnet
            user_id = cred.user_id
            print(f"\n✓ Using credentials for user: {user_id}")
            print(f"  Testnet: {use_testnet}")
        else:
            api_key = settings.binance_api_key
            api_secret = settings.binance_api_secret
            use_testnet = settings.binance_testnet
            user_id = None
            print(f"\n✓ Using system credentials (admin)")
            print(f"  Testnet: {use_testnet}")
    
    # Connect to Binance
    async with BinanceFuturesClient(api_key=api_key, api_secret=api_secret, testnet=use_testnet) as exchange:
        print("\n" + "=" * 80)
        print("1. BINANCE ACCOUNT INFO")
        print("=" * 80)
        
        account_info = await exchange.get_account_info()
        wallet_balance = float(account_info.get("totalWalletBalance", 0))
        available_balance = float(account_info.get("availableBalance", 0))
        unrealized_pnl = float(account_info.get("totalUnrealizedProfit", 0))
        total_initial_margin = float(account_info.get("totalInitialMargin", 0))
        total_maint_margin = float(account_info.get("totalMaintMargin", 0))
        
        print(f"  Total Wallet Balance:     ${wallet_balance:,.2f}")
        print(f"  Available Balance:        ${available_balance:,.2f}")
        print(f"  Unrealized PnL:           ${unrealized_pnl:,.2f}")
        print(f"  Total Initial Margin:     ${total_initial_margin:,.2f}")
        print(f"  Total Maintenance Margin: ${total_maint_margin:,.2f}")
        
        print("\n" + "=" * 80)
        print("2. BINANCE INCOME HISTORY (Last 10 Realized PnL)")
        print("=" * 80)
        
        income_history = await exchange.get_income_history(limit=10)
        total_realized = 0
        
        if income_history:
            print(f"\n  Found {len(income_history)} income records:")
            print(f"  {'Time':<20} {'Symbol':<12} {'Income':<15} {'Type':<20}")
            print("  " + "-" * 70)
            
            for record in income_history:
                timestamp = datetime.fromtimestamp(record.get("time", 0) / 1000)
                symbol = record.get("symbol", "N/A")
                income = float(record.get("income", 0))
                income_type = record.get("incomeType", "N/A")
                total_realized += income
                
                print(f"  {timestamp:%Y-%m-%d %H:%M:%S} {symbol:<12} ${income:>12.4f} {income_type:<20}")
            
            print("  " + "-" * 70)
            print(f"  Total (last 10):          ${total_realized:,.4f}")
        else:
            print("  ⚠ No income history found")
        
        print("\n" + "=" * 80)
        print("3. OPEN POSITIONS")
        print("=" * 80)
        
        positions = await exchange.get_position_risk()
        active_positions = [p for p in positions if float(p.get("positionAmt", 0)) != 0]
        
        if active_positions:
            print(f"\n  Found {len(active_positions)} active positions:")
            print(f"  {'Symbol':<12} {'Side':<6} {'Size':<12} {'Entry Price':<15} {'Unrealized PnL':<15}")
            print("  " + "-" * 70)
            
            for pos in active_positions:
                symbol = pos.get("symbol")
                position_amt = float(pos.get("positionAmt", 0))
                side = "LONG" if position_amt > 0 else "SHORT"
                entry_price = float(pos.get("entryPrice", 0))
                unrealized = float(pos.get("unRealizedProfit", 0))
                
                print(f"  {symbol:<12} {side:<6} {abs(position_amt):<12.4f} ${entry_price:<14.2f} ${unrealized:>14.4f}")
        else:
            print("  ✓ No active positions")
    
    # Check database records
    print("\n" + "=" * 80)
    print("4. DATABASE TRADE JOURNAL (Last 24h)")
    print("=" * 80)
    
    async with AsyncSessionFactory() as session:
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        if user_id:
            pnl_result = await session.execute(
                select(func.sum(TradeJournal.pnl))
                .where(TradeJournal.closed_at >= yesterday, TradeJournal.user_id == user_id)
            )
        else:
            pnl_result = await session.execute(
                select(func.sum(TradeJournal.pnl))
                .where(TradeJournal.closed_at >= yesterday)
            )
        
        db_realized_pnl_24h = float(pnl_result.scalar() or 0.0)
        print(f"  Realized PnL (24h from DB): ${db_realized_pnl_24h:,.4f}")
        
        # Get recent trades
        if user_id:
            trades_result = await session.execute(
                select(TradeJournal)
                .where(TradeJournal.user_id == user_id)
                .order_by(desc(TradeJournal.closed_at))
                .limit(5)
            )
        else:
            trades_result = await session.execute(
                select(TradeJournal)
                .order_by(desc(TradeJournal.closed_at))
                .limit(5)
            )
        
        db_trades = trades_result.scalars().all()
        
        if db_trades:
            print(f"\n  Last 5 trades in database:")
            print(f"  {'Closed At':<20} {'Symbol':<12} {'Side':<6} {'PnL':<15}")
            print("  " + "-" * 60)
            
            for trade in db_trades:
                print(f"  {trade.closed_at:%Y-%m-%d %H:%M:%S} {trade.symbol:<12} {trade.side:<6} ${trade.pnl:>12.4f}")
        else:
            print("  ⚠ No trades found in database")
    
    print("\n" + "=" * 80)
    print("5. SUMMARY & DIAGNOSIS")
    print("=" * 80)
    
    print(f"\n  Binance Wallet Balance:    ${wallet_balance:,.2f}  ← This is what Binance shows")
    print(f"  Bot displays:              Check frontend")
    print(f"\n  Unrealized PnL:            ${unrealized_pnl:,.2f}  (from open positions)")
    print(f"  Realized PnL (last 10):    ${total_realized:,.4f}  (from income history)")
    print(f"  DB Realized PnL (24h):     ${db_realized_pnl_24h:,.4f}  (from trade journal)")
    
    print("\n  POTENTIAL ISSUES:")
    if abs(wallet_balance - 10000) < 100:  # Close to 10k
        print("  ✓ Binance shows ~10k as reported")
    else:
        print(f"  ⚠ Binance shows ${wallet_balance:,.2f}, not ~10k")
    
    print("\n  RECOMMENDATIONS:")
    print("  1. Check frontend WalletIndicator.tsx - is it displaying wallet_balance correctly?")
    print("  2. Check if initial_balance setting is correct (should match starting capital)")
    print("  3. Income history shows realized PnL from closed positions")
    print("  4. Wallet balance = initial capital + all realized PnL + unrealized PnL")
    print("  5. If you just closed a position, check income history for that transaction")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_wallet())
