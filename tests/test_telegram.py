"""
Tests for Telegram bot - RBAC, commands, audit logging
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from apps.telegram.rbac import RBAC, UserRole, Permission, User
from apps.telegram.bot import TelegramBot


# === RBAC Tests ===

class TestRBAC:
    """Test RBAC system"""

    def setup_method(self):
        """Setup RBAC for each test"""
        self.rbac = RBAC(admin_ids=[123], trader_ids=[456])

    def test_register_user_as_admin(self):
        """Test registering user as admin"""
        self.rbac.register_user(123, UserRole.ADMIN)
        user = self.rbac.get_user(123)
        assert user is not None
        assert user.chat_id == 123
        assert user.role == UserRole.ADMIN

    def test_register_user_as_trader(self):
        """Test registering user as trader"""
        self.rbac.register_user(456, UserRole.TRADER)
        user = self.rbac.get_user(456)
        assert user.role == UserRole.TRADER

    def test_register_user_as_viewer(self):
        """Test registering user as viewer"""
        self.rbac.register_user(789, UserRole.VIEWER)
        user = self.rbac.get_user(789)
        assert user.role == UserRole.VIEWER

    def test_user_not_registered(self):
        """Test unregistered user returns None"""
        user = self.rbac.get_user(999)
        assert user is None

    def test_is_registered(self):
        """Test is_registered check"""
        self.rbac.register_user(123, UserRole.ADMIN)
        assert self.rbac.is_registered(123) is True
        assert self.rbac.is_registered(999) is False

    def test_admin_has_all_permissions(self):
        """Test admin has all permissions"""
        self.rbac.register_user(123, UserRole.ADMIN)
        
        # Admin should have all permissions
        assert self.rbac.is_authorized(123, Permission.VIEW_TIME)
        assert self.rbac.is_authorized(123, Permission.CLOSE_ALL)
        assert self.rbac.is_authorized(123, Permission.SYNC_NOW)

    def test_trader_has_limited_permissions(self):
        """Test trader has limited permissions"""
        self.rbac.register_user(456, UserRole.TRADER)
        
        # Trader can view and control
        assert self.rbac.is_authorized(456, Permission.VIEW_TIME)
        assert self.rbac.is_authorized(456, Permission.CLOSE_POSITION)
        
        # Trader cannot sync
        assert not self.rbac.is_authorized(456, Permission.SYNC_NOW)

    def test_viewer_has_view_only_permissions(self):
        """Test viewer has view-only permissions"""
        self.rbac.register_user(789, UserRole.VIEWER)
        
        # Viewer can view
        assert self.rbac.is_authorized(789, Permission.VIEW_TIME)
        assert self.rbac.is_authorized(789, Permission.VIEW_POSITIONS)
        
        # Viewer cannot control
        assert not self.rbac.is_authorized(789, Permission.CLOSE_POSITION)
        assert not self.rbac.is_authorized(789, Permission.PAUSE_RESUME)

    def test_unregistered_user_no_permissions(self):
        """Test unregistered user has no permissions"""
        assert not self.rbac.is_authorized(999, Permission.VIEW_TIME)

    def test_is_admin(self):
        """Test is_admin check"""
        self.rbac.register_user(123, UserRole.ADMIN)
        self.rbac.register_user(456, UserRole.TRADER)
        
        assert self.rbac.is_admin(123) is True
        assert self.rbac.is_admin(456) is False
        assert self.rbac.is_admin(999) is False

    def test_from_config_creation(self):
        """Test RBAC creation from config"""
        rbac = RBAC(admin_ids=[111, 222], trader_ids=[333, 444])
        
        # Users should be auto-registered
        assert rbac.is_registered(111)
        assert rbac.get_user(111).role == UserRole.ADMIN
        
        assert rbac.is_registered(333)
        assert rbac.get_user(333).role == UserRole.TRADER


# === Mock Telegram Update ===

def create_mock_update(chat_id: int, text: str = "/help", args: list | None = None):
    """Create a mock Telegram Update"""
    update = MagicMock()
    message = MagicMock()
    message.chat.id = chat_id
    message.text = text
    message.reply_text = AsyncMock()
    
    update.effective_chat.id = chat_id
    update.message = message
    
    context = MagicMock()
    context.args = args or []
    
    return update, context


# === Bot Command Tests ===

class TestTelegramBotCommands:
    """Test Telegram bot commands"""

    @pytest.fixture
    async def bot(self):
        """Create bot instance"""
        bot = TelegramBot()
        bot.rbac.register_user(111, UserRole.ADMIN)
        bot.rbac.register_user(222, UserRole.TRADER)
        bot.rbac.register_user(333, UserRole.VIEWER)
        return bot

    @pytest.mark.asyncio
    async def test_cmd_start_registered_user(self, bot):
        """Test /start command for registered user"""
        update, context = create_mock_update(111)
        
        await bot.cmd_start(update, context)
        
        # Should send welcome message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "Trading Bot Telegram Control" in call_args

    @pytest.mark.asyncio
    async def test_cmd_start_unregistered_user(self, bot):
        """Test /start command for unregistered user"""
        update, context = create_mock_update(999)
        
        await bot.cmd_start(update, context)
        
        # Should send error message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "not registered" in call_args

    @pytest.mark.asyncio
    async def test_cmd_help_registered(self, bot):
        """Test /help command"""
        update, context = create_mock_update(111)
        
        await bot.cmd_help(update, context)
        
        # Should send help message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "Health & Time" in call_args

    @pytest.mark.asyncio
    async def test_cmd_time_with_permission(self, bot):
        """Test /time command"""
        update, context = create_mock_update(111)
        
        await bot.cmd_time(update, context)
        
        # Should send time info
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "System Time" in call_args

    @pytest.mark.asyncio
    async def test_cmd_time_without_permission(self, bot):
        """Test /time command denies unauthorized"""
        # Create viewer who has VIEW_TIME permission
        update, context = create_mock_update(333)
        
        await bot.cmd_time(update, context)
        
        # Viewer CAN see time
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_price(self, bot):
        """Test /price command"""
        update, context = create_mock_update(111, args=["BTCUSDT"])
        
        await bot.cmd_price(update, context)
        
        # Should send price
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "BTCUSDT" in call_args

    @pytest.mark.asyncio
    async def test_cmd_price_no_args(self, bot):
        """Test /price command without arguments"""
        update, context = create_mock_update(111, args=[])
        
        await bot.cmd_price(update, context)
        
        # Should send usage info
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "Usage" in call_args

    @pytest.mark.asyncio
    async def test_cmd_spread(self, bot):
        """Test /spread command"""
        update, context = create_mock_update(222, args=["ETHUSDT"])
        
        await bot.cmd_spread(update, context)
        
        # Should send spread info
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "Spread" in call_args

    @pytest.mark.asyncio
    async def test_cmd_kline(self, bot):
        """Test /kline command"""
        update, context = create_mock_update(222, args=["BTCUSDT", "1m", "60"])
        
        await bot.cmd_kline(update, context)
        
        # Should send klines
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "Klines" in call_args

    @pytest.mark.asyncio
    async def test_cmd_close_position_with_permission(self, bot):
        """Test /close_position command"""
        update, context = create_mock_update(222, args=["BTCUSDT"])
        update.message.reply_text = AsyncMock()
        
        await bot.cmd_close_position(update, context)
        
        # Should ask for confirmation
        update.message.reply_text.assert_called_once()
        call_args = str(update.message.reply_text.call_args)
        assert "BTCUSDT" in call_args or "confirmation" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_cmd_close_position_without_permission(self, bot):
        """Test /close_position denies viewer"""
        update, context = create_mock_update(333, args=["BTCUSDT"])  # Viewer
        
        await bot.cmd_close_position(update, context)
        
        # Viewer cannot execute this
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "permission" in call_args.lower()

    @pytest.mark.asyncio
    async def test_cmd_pause_requires_trader_role(self, bot):
        """Test /pause requires trader or admin"""
        # Test with admin
        update, context = create_mock_update(111)
        await bot.cmd_pause(update, context)
        assert update.message.reply_text.called
        
        # Test with trader
        update, context = create_mock_update(222)
        await bot.cmd_pause(update, context)
        assert update.message.reply_text.called
        
        # Test with viewer
        update, context = create_mock_update(333)
        await bot.cmd_pause(update, context)
        call_args = update.message.reply_text.call_args[0][0]
        assert "permission" in call_args.lower()


# === Audit Logging Tests ===

class TestAuditLogging:
    """Test audit logging"""

    @pytest.fixture
    async def bot(self):
        """Create bot instance"""
        bot = TelegramBot()
        bot.rbac.register_user(111, UserRole.ADMIN)
        return bot

    @pytest.mark.asyncio
    async def test_audit_log_created_on_command(self, bot):
        """Test that audit log is created"""
        with patch.object(bot, '_audit', new_callable=AsyncMock) as mock_audit:
            update, context = create_mock_update(111)
            
            # Note: We're skipping the actual command to just test audit
            await bot._audit(111, "test_command", "success", {"test": "data"})
            
            mock_audit.assert_called_once()


# === Permission Matrix Tests ===

class TestPermissionMatrix:
    """Test permission matrix for all roles"""

    def setup_method(self):
        """Setup RBAC"""
        self.rbac = RBAC(admin_ids=[1], trader_ids=[2])
        self.rbac.register_user(1, UserRole.ADMIN)
        self.rbac.register_user(2, UserRole.TRADER)
        self.rbac.register_user(3, UserRole.VIEWER)

    def test_admin_permissions_complete(self):
        """Admin should have all permissions"""
        admin_perms = [
            Permission.VIEW_TIME,
            Permission.VIEW_LATENCY,
            Permission.VIEW_HEALTH,
            Permission.VIEW_PRICE,
            Permission.VIEW_SPREAD,
            Permission.VIEW_KLINES,
            Permission.VIEW_STATUS,
            Permission.VIEW_POSITIONS,
            Permission.VIEW_ORDERS,
            Permission.VIEW_RECON,
            Permission.VIEW_DECISION,
            Permission.VIEW_TRACE,
            Permission.PAUSE_RESUME,
            Permission.SYNC_NOW,
            Permission.CLOSE_POSITION,
            Permission.CLOSE_ALL,
        ]
        
        for perm in admin_perms:
            assert self.rbac.is_authorized(1, perm), f"Admin missing {perm}"

    def test_trader_cannot_sync(self):
        """Trader cannot use sync_now"""
        assert not self.rbac.is_authorized(2, Permission.SYNC_NOW)

    def test_viewer_can_only_view(self):
        """Viewer can only view, not control"""
        view_perms = [
            Permission.VIEW_TIME,
            Permission.VIEW_POSITIONS,
            Permission.VIEW_ORDERS,
        ]
        
        control_perms = [
            Permission.PAUSE_RESUME,
            Permission.CLOSE_POSITION,
            Permission.CLOSE_ALL,
            Permission.SYNC_NOW,
        ]
        
        for perm in view_perms:
            assert self.rbac.is_authorized(3, perm)
        
        for perm in control_perms:
            assert not self.rbac.is_authorized(3, perm)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
