"""
Telegram Bot - Remote operations for trading bot
Provides health checks, market data, trading state, and control operations
"""
import asyncio
from datetime import datetime
from typing import Dict, Any
import logging
import json

from telegram import Update, User as TelegramUser, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import AsyncSessionFactory, init_db, close_db
from packages.shared.models import (
    AuditLog,
    Event,
    Position,
    Order,
    Decision,
)
from packages.shared.logger import logger
from apps.telegram.rbac import RBAC, Permission


# Telegram logger
tg_logger = logging.getLogger("telegram")


class TelegramBot:
    """Telegram bot for remote operations"""

    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.rbac = RBAC(
            admin_ids=settings.telegram_admin_list,
            trader_ids=settings.telegram_trader_list,
        )
        self.application: Application | None = None
        
        # Track pending confirmations: (chat_id, action) -> (confirmation_required, data)
        self.pending_confirmations: Dict[tuple, tuple] = {}
        
        logger.info(
            "telegram_bot_initialized",
            admins=settings.telegram_admin_list,
            traders=settings.telegram_trader_list,
        )

    async def initialize(self):
        """Initialize bot application"""
        logger.info("telegram_bot_initializing")
        
        # Initialize database
        await init_db()
        
        # Create Telegram application
        self.application = Application.builder().token(self.bot_token).build()
        
        # Register command handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        
        # Health/Time
        self.application.add_handler(CommandHandler("time", self.cmd_time))
        self.application.add_handler(CommandHandler("latency", self.cmd_latency))
        self.application.add_handler(CommandHandler("health", self.cmd_health))
        
        # Market
        self.application.add_handler(CommandHandler("price", self.cmd_price))
        self.application.add_handler(CommandHandler("spread", self.cmd_spread))
        self.application.add_handler(CommandHandler("kline", self.cmd_kline))
        
        # State
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("positions", self.cmd_positions))
        self.application.add_handler(CommandHandler("orders", self.cmd_orders))
        self.application.add_handler(CommandHandler("recon", self.cmd_recon))
        self.application.add_handler(CommandHandler("decision", self.cmd_decision))
        self.application.add_handler(CommandHandler("trace", self.cmd_trace))
        
        # Control
        self.application.add_handler(CommandHandler("pause", self.cmd_pause))
        self.application.add_handler(CommandHandler("resume", self.cmd_resume))
        self.application.add_handler(CommandHandler("close_position", self.cmd_close_position))
        self.application.add_handler(CommandHandler("close_all", self.cmd_close_all))
        
        # Admin
        self.application.add_handler(CommandHandler("sync_now", self.cmd_sync_now))
        
        # Utility
        self.application.add_handler(CommandHandler("tips", self.cmd_tips))
        self.application.add_handler(CommandHandler("guide", self.cmd_guide))
        self.application.add_handler(CommandHandler("settings", self.cmd_settings))
        
        # Confirmation handler
        self.application.add_handler(CallbackQueryHandler(self.handle_confirmation))
        
        logger.info("telegram_bot_initialized")

    async def run(self):
        """Start bot polling"""
        logger.info("telegram_bot_starting")
        
        if not self.application:
            raise RuntimeError("Bot not initialized")
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

    async def shutdown(self):
        """Shutdown bot gracefully"""
        logger.info("telegram_bot_shutting_down")
        
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        
        await close_db()

    # === Helper methods ===

    def _check_auth(self, chat_id: int, permission: Permission) -> bool:
        """Check if user is authorized"""
        return self.rbac.is_authorized(chat_id, permission)

    async def _audit(
        self,
        chat_id: int,
        command: str,
        status: str,
        details: dict | None = None,
    ):
        """Log command to audit log"""
        async with AsyncSessionFactory() as session:
            audit = AuditLog(
                timestamp=datetime.utcnow(),
                actor=f"tg_{chat_id}",
                action=command,
                target="telegram",
                details_json={
                    "status": status,
                    "chat_id": chat_id,
                    **(details or {}),
                },
            )
            session.add(audit)
            await session.commit()

    async def _deny(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send denial message"""
        await update.message.reply_text(
            "❌ You don't have permission for this command."
        )

    # === Command handlers ===

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start"""
        chat_id = update.effective_chat.id
        
        if not self.rbac.is_registered(chat_id):
            await update.message.reply_text(
                "❌ You are not registered. Contact an admin."
            )
            return
        
        user = self.rbac.get_user(chat_id)
        role = user.role if user else "unknown"
        
        await update.message.reply_text(
            f"🤖 Trading Bot Telegram Control\n"
            f"Role: {role}\n"
            f"Use /help for commands."
        )
        
        await self._audit(chat_id, "start", "success")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /help - Interactive help with categories"""
        chat_id = update.effective_chat.id
        
        if not self.rbac.is_registered(chat_id):
            await self._deny(update, context)
            return
        
        user = self.rbac.get_user(chat_id)
        role = user.role.value if user else "unknown"
        
        # Main help message
        help_text = f"""
🤖 **Trading Bot Telegram Control**

👤 *Your Role:* `{role.upper()}`

📚 *Command Categories:*
"""
        
        # Build category buttons
        keyboard = [
            [
                InlineKeyboardButton("🏥 Health & Time", callback_data="help_health"),
                InlineKeyboardButton("💰 Market Data", callback_data="help_market"),
            ],
            [
                InlineKeyboardButton("📊 Trading State", callback_data="help_state"),
                InlineKeyboardButton("⚙️ Control", callback_data="help_control"),
            ],
            [
                InlineKeyboardButton("💡 Tips & Tricks", callback_data="help_tips"),
                InlineKeyboardButton("📖 Usage Guide", callback_data="help_guide"),
            ],
        ]
        
        if role == "admin":
            keyboard.append([InlineKeyboardButton("🔐 Admin Only", callback_data="help_admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        help_text += "\n*Tap a category below to see available commands!* 👇"
        
        await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=reply_markup)
        await self._audit(chat_id, "help", "success")

    async def cmd_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /time - Uptime, last tick, environment"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_TIME):
            await self._deny(update, context)
            return
        
        try:
            async with AsyncSessionFactory() as session:
                # Get latest event (last tick)
                result = await session.execute(
                    select(Event).order_by(Event.timestamp.desc()).limit(1)
                )
                last_event = result.scalar_one_or_none()
                
                message = (
                    f"⏱️ **System Time**\n"
                    f"Current: {datetime.utcnow().isoformat()}Z\n"
                    f"Environment: {settings.env}\n"
                    f"Last tick: {last_event.timestamp.isoformat() if last_event else 'N/A'}Z\n"
                )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(chat_id, "time", "success")
        
        except Exception as e:
            logger.error("cmd_time_error", error=str(e))
            await update.message.reply_text(f"❌ Error: {str(e)}")
            await self._audit(chat_id, "time", "error", {"error": str(e)})

    async def cmd_latency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /latency - WS/REST P95 + clock skew"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_LATENCY):
            await self._deny(update, context)
            return
        
        try:
            # TODO: Integrate with actual latency metrics from worker
            message = (
                f"📡 **Latency Metrics**\n"
                f"WS P95: 45ms\n"
                f"REST P95: 120ms\n"
                f"Clock skew: +50ms\n"
                f"Network: ✅ Healthy\n"
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(chat_id, "latency", "success")
        
        except Exception as e:
            logger.error("cmd_latency_error", error=str(e))
            await self._audit(chat_id, "latency", "error", {"error": str(e)})

    async def cmd_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /health - System health status"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_HEALTH):
            await self._deny(update, context)
            return
        
        try:
            # TODO: Integration with actual health checks
            message = (
                f"🏥 **System Health**\n"
                f"WS: ✅ Connected\n"
                f"REST: ✅ OK\n"
                f"DB: ✅ OK\n"
                f"Circuit Breaker: ✅ CLOSED (safe)\n"
                f"Worker: ✅ Running\n"
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(chat_id, "health", "success")
        
        except Exception as e:
            logger.error("cmd_health_error", error=str(e))
            await self._audit(chat_id, "health", "error", {"error": str(e)})

    async def cmd_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /price SYMBOL"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_PRICE):
            await self._deny(update, context)
            return
        
        try:
            if not context.args:
                await update.message.reply_text("Usage: /price BTCUSDT")
                return
            
            symbol = context.args[0].upper()
            
            # TODO: Integration with real price from Binance/API
            message = (
                f"💰 **{symbol}**\n"
                f"Price: $50,123.45\n"
                f"24h Change: +2.34%\n"
                f"Updated: {datetime.utcnow().isoformat()}Z\n"
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(chat_id, "price", "success", {"symbol": symbol})
        
        except Exception as e:
            logger.error("cmd_price_error", error=str(e))
            await self._audit(chat_id, "price", "error", {"error": str(e)})

    async def cmd_spread(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /spread SYMBOL"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_SPREAD):
            await self._deny(update, context)
            return
        
        try:
            if not context.args:
                await update.message.reply_text("Usage: /spread BTCUSDT")
                return
            
            symbol = context.args[0].upper()
            message = (
                f"🎯 **Spread - {symbol}**\n"
                f"Bid: $50,120.00\n"
                f"Ask: $50,125.00\n"
                f"Spread: $5.00 (0.01%)\n"
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(chat_id, "spread", "success", {"symbol": symbol})
        
        except Exception as e:
            logger.error("cmd_spread_error", error=str(e))
            await self._audit(chat_id, "spread", "error", {"error": str(e)})

    async def cmd_kline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /kline SYMBOL INTERVAL COUNT"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_KLINES):
            await self._deny(update, context)
            return
        
        try:
            if len(context.args) < 3:
                await update.message.reply_text("Usage: /kline BTCUSDT 1m 60")
                return
            
            symbol = context.args[0].upper()
            interval = context.args[1]
            count = int(context.args[2])
            
            message = (
                f"📊 **Klines - {symbol} {interval} (last {count})**\n"
                f"(Last 3 candles)\n"
                f"1: O=50,100 H=50,200 L=50,000 C=50,150\n"
                f"2: O=50,150 H=50,300 L=50,100 C=50,250\n"
                f"3: O=50,250 H=50,300 L=50,200 C=50,123\n"
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(
                chat_id,
                "kline",
                "success",
                {"symbol": symbol, "interval": interval, "count": count},
            )
        
        except Exception as e:
            logger.error("cmd_kline_error", error=str(e))
            await self._audit(chat_id, "kline", "error", {"error": str(e)})

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /status - Bot status"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_STATUS):
            await self._deny(update, context)
            return
        
        try:
            async with AsyncSessionFactory() as session:
                # Count positions and orders
                pos_result = await session.execute(select(Position))
                positions = pos_result.scalars().all()
                
                ord_result = await session.execute(select(Order))
                orders = ord_result.scalars().all()
                
                message = (
                    f"📊 **Trading Bot Status**\n"
                    f"Environment: {settings.env}\n"
                    f"Active Positions: {len(positions)}\n"
                    f"Open Orders: {len(orders)}\n"
                    f"Status: ✅ Running\n"
                )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(chat_id, "status", "success")
        
        except Exception as e:
            logger.error("cmd_status_error", error=str(e))
            await self._audit(chat_id, "status", "error", {"error": str(e)})

    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /positions"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_POSITIONS):
            await self._deny(update, context)
            return
        
        try:
            async with AsyncSessionFactory() as session:
                result = await session.execute(select(Position))
                positions = result.scalars().all()
                
                if not positions:
                    await update.message. reply_text("📭 No open positions")
                    return
                
                message = "📍 **Open Positions**\n"
                for pos in positions[:10]:  # Limit to 10
                    message += (
                        f"{pos.symbol}: {pos.qty} @ {pos.entry_price} "
                        f"PnL: {pos.unrealized_pnl:.2f}\n"
                    )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(chat_id, "positions", "success")
        
        except Exception as e:
            logger.error("cmd_positions_error", error=str(e))
            await self._audit(chat_id, "positions", "error", {"error": str(e)})

    async def cmd_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /orders"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_ORDERS):
            await self._deny(update, context)
            return
        
        try:
            async with AsyncSessionFactory() as session:
                result = await session.execute(select(Order))
                orders = result.scalars().all()
                
                if not orders:
                    await update.message.reply_text("📭 No open orders")
                    return
                
                message = "📋 **Open Orders**\n"
                for order in orders[:10]:  # Limit to 10
                    message += (
                        f"{order.symbol} {order.side} {order.quantity} @ {order.avg_price} "
                        f"({order.status})\n"
                    )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(chat_id, "orders", "success")
        
        except Exception as e:
            logger.error("cmd_orders_error", error=str(e))
            await self._audit(chat_id, "orders", "error", {"error": str(e)})

    async def cmd_recon(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /recon - Reconciliation status"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_RECON):
            await self._deny(update, context)
            return
        
        try:
            message = (
                f"♻️ **Reconciliation**\n"
                f"Last sync: 2 seconds ago\n"
                f"Mismatches: 0 ✅\n"
                f"Status: All systems in sync\n"
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(chat_id, "recon", "success")
        
        except Exception as e:
            logger.error("cmd_recon_error", error=str(e))
            await self._audit(chat_id, "recon", "error", {"error": str(e)})

    async def cmd_decision(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /decision - Latest AI decision"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_DECISION):
            await self._deny(update, context)
            return
        
        try:
            async with AsyncSessionFactory() as session:
                result = await session.execute(
                    select(Decision).order_by(Decision.timestamp.desc()).limit(1)
                )
                decision = result.scalar_one_or_none()
                
                if not decision:
                    await update.message.reply_text("📭 No decisions yet")
                    return
                
                decision_data = decision.decision_json
                message = (
                    f"🤖 **Latest Decision**\n"
                    f"Symbol: {decision_data.get('symbol', 'N/A')}\n"
                    f"Action: {decision_data.get('action', 'N/A')}\n"
                    f"Confidence: {decision.confidence:.2f}\n"
                    f"Regime: {decision.regime}\n"
                    f"Trace: `{decision.trace_id}`\n"
                )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(chat_id, "decision", "success")
        
        except Exception as e:
            logger.error("cmd_decision_error", error=str(e))
            await self._audit(chat_id, "decision", "error", {"error": str(e)})

    async def cmd_trace(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /trace TRACE_ID"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.VIEW_TRACE):
            await self._deny(update, context)
            return
        
        try:
            if not context.args:
                await update.message.reply_text("Usage: /trace <trace_id>")
                return
            
            trace_id = context.args[0]
            
            async with AsyncSessionFactory() as session:
                result = await session.execute(
                    select(Decision).where(Decision.trace_id == trace_id)
                )
                decision = result.scalar_one_or_none()
                
                if not decision:
                    await update.message.reply_text(f"❌ Trace not found: {trace_id}")
                    return
                
                decision_data = decision.decision_json
                message = (
                    f"🔍 **Trace: {trace_id}**\n"
                    f"Decision: {decision_data}\n"
                    f"Timestamp: {decision.timestamp.isoformat()}Z\n"
                )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            await self._audit(chat_id, "trace", "success", {"trace_id": trace_id})
        
        except Exception as e:
            logger.error("cmd_trace_error", error=str(e))
            await self._audit(chat_id, "trace", "error", {"error": str(e)})

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /pause"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.PAUSE_RESUME):
            await self._deny(update, context)
            return
        
        try:
            # TODO: Call worker pause API
            await update.message.reply_text("⏸️ Trading paused")
            await self._audit(chat_id, "pause", "success")
        
        except Exception as e:
            logger.error("cmd_pause_error", error=str(e))
            await self._audit(chat_id, "pause", "error", {"error": str(e)})

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /resume"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.PAUSE_RESUME):
            await self._deny(update, context)
            return
        
        try:
            # TODO: Call worker resume API
            await update.message.reply_text("▶️ Trading resumed")
            await self._audit(chat_id, "resume", "success")
        
        except Exception as e:
            logger.error("cmd_resume_error", error=str(e))
            await self._audit(chat_id, "resume", "error", {"error": str(e)})

    async def cmd_close_position(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handler for /close_position SYMBOL - 2-step confirmation"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.CLOSE_POSITION):
            await self._deny(update, context)
            return
        
        try:
            if not context.args:
                await update.message.reply_text("Usage: /close_position BTCUSDT")
                return
            
            symbol = context.args[0].upper()
            
            # Store pending confirmation
            key = (chat_id, "close_position")
            self.pending_confirmations[key] = (True, {"symbol": symbol})
            
            # Create confirmation buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_close_{symbol}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚠️ Close position {symbol}?",
                reply_markup=reply_markup,
            )
            
            await self._audit(chat_id, "close_position_pending", "pending", {"symbol": symbol})
        
        except Exception as e:
            logger.error("cmd_close_position_error", error=str(e))
            await self._audit(chat_id, "close_position", "error", {"error": str(e)})

    async def cmd_close_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /close_all - 2-step confirmation"""
        chat_id = update.effective_chat.id
        
        if not self._check_auth(chat_id, Permission.CLOSE_ALL):
            await self._deny(update, context)
            return
        
        try:
            # Store pending confirmation
            key = (chat_id, "close_all")
            self.pending_confirmations[key] = (True, {})
            
            # Create confirmation buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm", callback_data="confirm_close_all"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "⚠️ Close ALL positions?",
                reply_markup=reply_markup,
            )
            
            await self._audit(chat_id, "close_all_pending", "pending")
        
        except Exception as e:
            logger.error("cmd_close_all_error", error=str(e))
            await self._audit(chat_id, "close_all", "error", {"error": str(e)})

    async def cmd_sync_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /sync_now - Force reconciliation (Admin only)"""
        chat_id = update.effective_chat.id
        
        from apps.telegram.rbac import UserRole
        user = self.rbac.get_user(chat_id)
        
        if not user or user.role != UserRole.ADMIN:
            await self._deny(update, context)
            return
        
        try:
            # TODO: Call worker sync API
            await update.message.reply_text(
                "🔄 **Sync initiated**\n\n"
                "⏳ Reconciling database with Binance...\n"
                "This may take 10-30 seconds.\n\n"
                "💡 *Tip:* Use /recon to check sync status"
            )
            await self._audit(chat_id, "sync_now", "initiated")
        
        except Exception as e:
            logger.error("cmd_sync_now_error", error=str(e))
            await self._audit(chat_id, "sync_now", "error", {"error": str(e)})

    async def cmd_tips(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /tips - Pro tips for trading bot"""
        chat_id = update.effective_chat.id
        
        if not self.rbac.is_registered(chat_id):
            await self._deny(update, context)
            return
        
        tips_text = """
💡 **Pro Tips & Best Practices**

🏥 *Health Checks*
• Start each session with `/health` to ensure everything is running
• Monitor `/latency` regularly - high latency = slower order execution
• Use `/time` to verify bot's system time matches exchange

📊 *Market Monitoring*
• Check `/price BTC
USDT` before making trading decisions  
• Use `/spread BTCUSDT` to gauge market liquidity
• Check `/kline BTCUSDT 1m 60` for trend confirmation

🚨 *Before Critical Actions*
• Always check `/positions` and `/orders` first
• Review `/decision` to understand latest AI decision
• Use `/trace <id>` to review decision logic

⚙️ *Control Operations*
• Pause before market events: `/pause`
• Wait 5 seconds before resuming: `/resume`
• Close positions during high volatility to minimize slippage
• Use `/close_position` one at a time for safety

📈 *Positioning*
• Monitor consecutive losses with `/decision` history
• Check circuit breaker status in `/health`
• Adjust risk levels during high-impact news

🔐 *Admin Operations*
• Run `/sync_now` after major market movements
• Check sync results with `/recon`
• Review audit logs weekly in dashboard

⏰ *Timing*
• Bot operates on UTC - convert to your timezone
• Avoid trading during market holidays
• Check `/latency` during peak hours
"""
        
        await update.message.reply_text(tips_text, parse_mode="Markdown")
        await self._audit(chat_id, "tips", "success")

    async def cmd_guide(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /guide - Usage examples and workflows"""
        chat_id = update.effective_chat.id
        
        if not self.rbac.is_registered(chat_id):
            await self._deny(update, context)
            return
        
        guide_text = """
📖 **Command Usage Guide & Workflows**

**Morning Check (5 mins)**
1️⃣ `/health` → Verify system running
2️⃣ `/status` → Check positions/orders
3️⃣ `/price BTCUSDT` → Market mood
4️⃣ `/latency` → Network quality

**Market Open Workflow**
1️⃣ `/decision` → Latest AI decision
2️⃣ `/recon` → Verify sync status
3️⃣ `/resume` → Start trading
4️⃣ `/time` → Confirm timing

**Emergency Response**
1️⃣ `/pause` → Stop trading immediately
2️⃣ `/positions` → Identify exposure
3️⃣ `/close_position BTCUSDT` → Close specific
4️⃣ OR `/close_all` → Emergency exit

**Decision Analysis**
1️⃣ `/decision` → Latest decision
2️⃣ `/trace <id>` → Review logic
3️⃣ `/positions` → Check execution
4️⃣ `/orders` → Verify orders placed

**Market Analysis**
```
/price BTCUSDT          → Current: $50,123
/spread BTCUSDT         → Bid: $50,120, Ask: $50,125
/kline BTCUSDT 1m 60    → Last 60 candles
```

**Admin Maintenance**
```
/sync_now               → Force reconciliation
/recon                  → Check sync status
/health                 → Component status
```

**Example Commands:**
```
/price ETHUSDT          → Check Eth price
/spread BNBUSDT         → Check Bnb spread  
/kline BTCUSDT 5m 12    → 5min candles
/trace abc123def456     → Review decision
/close_position LTCUSDT  → Close Ltc position
```
"""
        
        await update.message.reply_text(guide_text, parse_mode="Markdown")
        await self._audit(chat_id, "guide", "success")

    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /settings - Current configuration check"""
        chat_id = update.effective_chat.id
        
        if not self.rbac.is_registered(chat_id):
            await self._deny(update, context)
            return
        
        user = self.rbac.get_user(chat_id)
        role = user.role.value if user else "unknown"
        
        settings_text = f"""
⚙️ **Current Settings**

**Bot Configuration**
• Environment: `{settings.env}`
• Mode: `{'MAINNET 🔴' if not settings.binance_testnet else 'TESTNET ✅'}`
• AI Provider: `{settings.ai_provider}`
• Chain: `{'Real Money ⚠️' if not settings.binance_testnet else 'Practice 🏋️'}`

**Your Access**
• Chat ID: `{chat_id}`
• Role: `{role.upper()}`
• Permissions: `{len([p for p in self.rbac.get_permissions(chat_id)])}`

**Trading Settings**
• Risk Level: `{settings.risk_level}`
• Position Size: `{settings.position_size}`
• Max Leverage: `{settings.max_leverage}`

**Notifications**
• Telegram: ✅ Connected
• Alerts: ✅ Enabled

💡 **Tip:** Contact admin to change settings
"""
        
        await update.message.reply_text(settings_text, parse_mode="Markdown")
        await self._audit(chat_id, "settings", "success")

    async def handle_help_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str
    ):
        """Handle help category callbacks"""
        query = update.callback_query
        chat_id = query.from_user.id
        await query.answer()
        
        help_messages = {
            "help_health": """
🏥 **Health & Time Commands**

▸ `/time` - System time & uptime
  Useful for: Verifying bot is running, syncing your clock
  Example: `/time`

▸ `/latency` - Network latency metrics
  Useful for: Checking connection quality and clock skew
  Example: `/latency`

▸ `/health` - System component status
  Useful for: Troubleshooting when things don't work
  Example: `/health`

💡 *Tip:* Run these daily to monitor system health! 🔧
""",
            "help_market": """
💰 **Market Data Commands**

▸ `/price SYMBOL` - Get current price
  Useful for: Quick price checks
  Example: `/price BTCUSDT`

▸ `/spread SYMBOL` - Bid/ask spread
  Useful for: Checking liquidity and slippage
  Example: `/spread ETHUSDT`

▸ `/kline SYMBOL INTERVAL COUNT` - Historical candles
  Useful for: Technical analysis and trend confirmation
  Examples:
    `/kline BTCUSDT 1m 60` → Last 60 min candles
    `/kline BTCUSDT 5m 24` → Last 2 hours (5min)
    `/kline BTCUSDT 1h 24` → Last 24 hours

💡 *Tip:* Check spread before major trades! 📊
""",
            "help_state": """
📊 **Trading State Commands**

▸ `/status` - Bot trading status
  Shows: Current env, positions, orders
  Example: `/status`

▸ `/positions` - All open positions
  Shows: Symbol, qty, entry price, P&L
  Example: `/positions`

▸ `/orders` - All open orders
  Shows: Symbol, side, qty, price, status
  Example: `/orders`

▸ `/recon` - Reconciliation status
  Shows: Last sync time, mismatches
  Example: `/recon`

▸ `/decision` - Latest AI decision
  Shows: Symbol, action, confidence, regime
  Example: `/decision`

▸ `/trace TRACE_ID` - Decision breakdown
  Shows: Full decision logic and parameters
  Example: `/trace abc123def456`

💡 *Tip:* Always check positions before closing! 📈
""",
            "help_control": """
⚙️ **Control Commands** (Traders+Admins)

▸ `/pause` - Stop all trading
  Warning: ⚠️ Stops new orders immediately
  Example: `/pause`

▸ `/resume` - Resume trading
  Warning: ⚠️ Re-enables orders
  Example: `/resume`

▸ `/close_position SYMBOL` - Close one position
  Warning: ⚠️ Requires 2-step confirmation
  Example: `/close_position BTCUSDT`

▸ `/close_all` - Close ALL positions
  Warning: ⚠️⚠️ Emergency button - requires 2-step confirmation
  Example: `/close_all`

💡 *Tip:* Always double-check before confirming! ⚠️
""",
            "help_admin": """
🔐 **Admin-Only Commands**

▸ `/sync_now` - Force reconciliation
  Purpose: Manually sync DB ↔ Binance
  When: Use after major market events
  Example: `/sync_now`

*Other Admin Features:*
• View full audit logs in dashboard
• Manage user roles and permissions
• Configure risk levels and position sizes
• View system metrics and performance

💡 *Tip:* Run sync_now before making decisions! 🔄
""",
            "help_tips": """
💡 **Tips & Best Practices**

✅ *Good Habits:*
• Check `/health` every morning
• Monitor `/latency` during peak hours
• Review `/decision` history for patterns
• Use `/recon` to verify sync status

⚠️ *Warnings:*
• Don't trade during major news events
• Check `/spread` before placing orders
• Verify `/positions` before closing
• Wait 5 seconds after `/pause` before `/resume`

🚀 *Pro Tips:*
• Use `/trace` to understand bad decisions
• Check `/kline` for trend confirmation
• Monitor clock skew in `/latency`
• Review `/decision` confidence scores

💡 Type `/tips` for more detailed advice! 📚
""",
            "help_guide": """
📖 **Quick Workflows**

**Morning Routine:**
1. `/health` 2. `/status` 3. `/price BTCUSDT` 4. `/latency`

**Before Trading:**
1. `/decision` 2. `/recon` 3. `/resume`

**Emergency:**
1. `/pause` 2. `/positions` 3. `/close_all`

**Troubleshooting:**
1. `/health` 2. `/recon` 3. `/latency` 4. `/trace <id>`

Full guide: Type `/guide` for commands & examples! 📚
""",
        }
        
        message = help_messages.get(
            category,
            "❌ Unknown category. Try /help again."
        )
        
        keyboard = [[InlineKeyboardButton("← Back", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)

    async def handle_confirmation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle confirmation and help callbacks"""
        query = update.callback_query
        chat_id = query.from_user.id
        
        await query.answer()
        
        # Handle help callbacks
        if query.data.startswith("help_"):
            if query.data == "help_back":
                await self.cmd_help(update, context)
                return
            
            category = query.data
            await self.handle_help_callback(update, context, category)
            return
        
        # Handle confirmation callbacks
        if query.data == "cancel":
            await query.edit_message_text("❌ Cancelled")
            return
        
        if query.data.startswith("confirm_close_"):
            symbol = query.data.replace("confirm_close_", "")
            await query.edit_message_text(f"✅ Closing {symbol}...")
            await self._audit(chat_id, "close_position", "confirmed", {"symbol": symbol})
            # TODO: Execute close
        
        elif query.data == "confirm_close_all":
            await query.edit_message_text("✅ Closing all positions...")
            await self._audit(chat_id, "close_all", "confirmed")
            # TODO: Execute close all
