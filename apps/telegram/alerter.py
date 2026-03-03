"""
Telegram Alert System for Trading Events
Sends real-time alerts for order fills, errors, and important events
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging

try:
    from telegram import Bot
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

from packages.shared.logger import logger
from packages.shared.config import settings


class TelegramAlerter:
    """Send trading alerts via Telegram"""

    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.admin_ids = settings.telegram_admin_list
        self.trader_ids = settings.telegram_trader_list
        self.bot: Optional[Bot] = None
        
        if not self.bot_token:
            logger.warning("telegram_bot_token not configured")
            return
        
        if HAS_TELEGRAM:
            self.bot = Bot(token=self.bot_token)
            logger.info(
                "telegram_alerter_initialized",
                admins=len(self.admin_ids),
                traders=len(self.trader_ids)
            )
    
    async def send_order_filled(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        timestamp: str
    ):
        """Alert when order is filled"""
        message = f"""
🎯 **ORDER FILLED**
━━━━━━━━━━━━━━━━
Symbol: {symbol}
Side: {'📈 BUY' if side.upper() == 'BUY' else '📉 SELL'}
Quantity: {quantity}
Price: ${price:,.2f}
Time: {timestamp}
"""
        await self._send_to_traders(message)
    
    async def send_position_opened(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        timestamp: str
    ):
        """Alert when position is opened"""
        message = f"""
✅ **POSITION OPENED**
━━━━━━━━━━━━━━━━
Symbol: {symbol}
Direction: {'📈 LONG' if side.upper() == 'BUY' else '📉 SHORT'}
Size: {quantity}
Entry: ${entry_price:,.2f}
Time: {timestamp}
"""
        await self._send_to_traders(message)
    
    async def send_position_closed(
        self,
        symbol: str,
        quantity: float,
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        timestamp: str
    ):
        """Alert when position is closed"""
        pnl_emoji = "💰" if pnl > 0 else "🔴"
        message = f"""
🏁 **POSITION CLOSED**
━━━━━━━━━━━━━━━━
Symbol: {symbol}
Size: {quantity}
Exit: ${exit_price:,.2f}
P&L: {pnl_emoji} ${pnl:,.2f} ({pnl_pct:,.1f}%)
Time: {timestamp}
"""
        await self._send_to_traders(message)
    
    async def send_error_alert(
        self,
        error_type: str,
        symbol: Optional[str],
        message: str,
        severity: str = "warning"
    ):
        """Alert on trading error"""
        emoji = "🚨" if severity == "critical" else "⚠️"
        message = f"""
{emoji} **ERROR ALERT**
━━━━━━━━━━━━━━━━
Type: {error_type}
Symbol: {symbol or 'N/A'}
Severity: {severity.upper()}
Details: {message}
Time: {datetime.utcnow().isoformat()}
"""
        
        if severity == "critical":
            await self._send_to_admins(message)
        else:
            await self._send_to_traders(message)
    
    async def send_balance_update(
        self,
        total_balance: float,
        available_balance: float,
        unrealized_pnl: float,
        timestamp: str
    ):
        """Send account balance update"""
        message = f"""
💵 **BALANCE UPDATE**
━━━━━━━━━━━━━━━━
Total: ${total_balance:,.2f}
Available: ${available_balance:,.2f}
Unrealized P&L: ${unrealized_pnl:,.2f}
Time: {timestamp}
"""
        await self._send_to_traders(message)
    
    async def send_decision_notification(
        self,
        symbol: str,
        decision: str,
        confidence: float,
        rationale: str
    ):
        """Send AI decision notification"""
        message = f"""
🤖 **AI DECISION**
━━━━━━━━━━━━━━━━
Symbol: {symbol}
Decision: {decision.upper()}
Confidence: {confidence:.1%}
Rationale: {rationale[:100]}...
Time: {datetime.utcnow().isoformat()}
"""
        await self._send_to_traders(message)
    
    async def send_health_check(
        self,
        status: str,
        api_latency: float,
        exchange_latency: float,
        db_check: bool
    ):
        """Send system health check"""
        status_emoji = "✅" if status == "healthy" else "⚠️"
        message = f"""
{status_emoji} **SYSTEM HEALTH**
━━━━━━━━━━━━━━━━
Status: {status.upper()}
API Latency: {api_latency:.0f}ms
Exchange Latency: {exchange_latency:.0f}ms
Database: {'✅' if db_check else '❌'}
Time: {datetime.utcnow().isoformat()}
"""
        await self._send_to_admins(message)
    
    async def _send_to_traders(self, message: str):
        """Send message to trader group"""
        if not self.bot or not self.trader_ids:
            return
        
        tasks = []
        for chat_id in self.trader_ids:
            try:
                tasks.append(
                    self.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="Markdown"
                    )
                )
            except Exception as e:
                logger.error("telegram_send_failed", chat_id=chat_id, error=str(e))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_to_admins(self, message: str):
        """Send message to admin group"""
        if not self.bot or not self.admin_ids:
            return
        
        tasks = []
        for chat_id in self.admin_ids:
            try:
                tasks.append(
                    self.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="Markdown"
                    )
                )
            except Exception as e:
                logger.error("telegram_send_failed", chat_id=chat_id, error=str(e))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# Global telegram alerter instance
telegram_alerter = TelegramAlerter()


async def notify_order_filled(symbol: str, side: str, quantity: float, price: float):
    """Helper to notify order fill"""
    await telegram_alerter.send_order_filled(
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        timestamp=datetime.utcnow().isoformat()
    )


async def notify_error(error_type: str, message: str, symbol: Optional[str] = None, critical: bool = False):
    """Helper to notify error"""
    await telegram_alerter.send_error_alert(
        error_type=error_type,
        message=message,
        symbol=symbol,
        severity="critical" if critical else "warning"
    )
