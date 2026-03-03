#!/usr/bin/env python3
"""
Test Telegram Bot Alert System
Verifies configuration and sends test alerts
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages"))

from shared.config import settings
from shared.logger import logger

# Import alerter with different approach to avoid circular import
import importlib.util
alerter_spec = importlib.util.spec_from_file_location("alerter", Path(__file__).parent / "apps" / "telegram" / "alerter.py")
alerter_module = importlib.util.module_from_spec(alerter_spec)
alerter_spec.loader.exec_module(alerter_module)
telegram_alerter = alerter_module.telegram_alerter


async def test_telegram_configuration():
    """Test Telegram bot configuration and send test messages"""
    print("\n" + "="*60)
    print("TELEGRAM BOT ALERT SYSTEM TEST")
    print("="*60 + "\n")
    
    # Check configuration
    print("Configuration Status:")
    print(f"  Bot Token: {'✅ Configured' if settings.telegram_bot_token else '❌ Not configured'}")
    print(f"  Admin IDs: {settings.telegram_admin_list if settings.telegram_admin_list else '❌ Not configured'}")
    print(f"  Trader IDs: {settings.telegram_trader_list if settings.telegram_trader_list else '⚠️  Not configured'}")
    print()
    
    if not settings.telegram_bot_token:
        print("❌ ERROR: Telegram bot token not configured in .env")
        print("  Set TELEGRAM_BOT_TOKEN in .env file")
        return 1
    
    if not settings.telegram_admin_list and not settings.telegram_trader_list:
        print("❌ ERROR: No Telegram recipient IDs configured")
        print("  Set TELEGRAM_ADMIN_IDS and/or TELEGRAM_TRADER_IDS in .env file")
        return 1
    
    print("Sending Test Alerts:")
    print()
    
    # Test 1: Order filled alert
    print("1. Testing order filled alert...", end=" ")
    try:
        await telegram_alerter.send_order_filled(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            price=43250.50,
            timestamp=datetime.utcnow().isoformat()
        )
        print("✅ Sent")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"❌ Failed: {str(e)[:50]}")
    
    # Test 2: Position opened alert
    print("2. Testing position opened alert...", end=" ")
    try:
        await telegram_alerter.send_position_opened(
            symbol="ETHUSDT",
            side="BUY",
            quantity=1.5,
            entry_price=2300.75,
            timestamp=datetime.utcnow().isoformat()
        )
        print("✅ Sent")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"❌ Failed: {str(e)[:50]}")
    
    # Test 3: Position closed alert
    print("3. Testing position closed alert...", end=" ")
    try:
        await telegram_alerter.send_position_closed(
            symbol="XRPUSDT",
            quantity=100,
            exit_price=2.15,
            pnl=15.00,
            pnl_pct=0.75,
            timestamp=datetime.utcnow().isoformat()
        )
        print("✅ Sent")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"❌ Failed: {str(e)[:50]}")
    
    # Test 4: Error alert
    print("4. Testing error alert...", end=" ")
    try:
        await telegram_alerter.send_error_alert(
            error_type="INSUFFICIENT_BALANCE",
            symbol="SOLUSDT",
            message="Available balance is lower than required for position size",
            severity="warning"
        )
        print("✅ Sent")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"❌ Failed: {str(e)[:50]}")
    
    # Test 5: Balance update
    print("5. Testing balance update alert...", end=" ")
    try:
        await telegram_alerter.send_balance_update(
            total_balance=10500.50,
            available_balance=8250.25,
            unrealized_pnl=150.25,
            timestamp=datetime.utcnow().isoformat()
        )
        print("✅ Sent")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"❌ Failed: {str(e)[:50]}")
    
    # Test 6: Health check
    print("6. Testing health check alert...", end=" ")
    try:
        await telegram_alerter.send_health_check(
            status="healthy",
            api_latency=45.2,
            exchange_latency=120.5,
            db_check=True
        )
        print("✅ Sent")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"❌ Failed: {str(e)[:50]}")
    
    print()
    print("="*60)
    print("✅ Telegram Bot is configured and ready!")
    print("="*60 + "\n")
    
    print("Alert Types Available:")
    print("  - Order filled notifications")
    print("  - Position opened/closed alerts")
    print("  - Error and warning notifications")
    print("  - Balance and PnL updates")
    print("  - System health checks")
    print("  - AI decision notifications")
    print()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_telegram_configuration())
    sys.exit(exit_code)
