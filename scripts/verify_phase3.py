"""
Phase 3 Verification Script - Telegram Bot Integration
Tests all Telegram commands, RBAC, audit logging
"""
import asyncio
import sys
from datetime import datetime

from packages.shared.logger import logger
from apps.telegram.rbac import RBAC, UserRole, Permission


def print_section(title: str):
    """Print test section header"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_test(name: str, status: str):
    """Print single test result"""
    symbol = "✅" if status == "PASS" else "❌"
    print(f"{symbol} {name}: {status}")


class Phase3Verifier:
    """Verify Phase 3 implementation"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.rbac = RBAC(admin_ids=[111, 222], trader_ids=[333, 444])

    def _pass(self, test_name: str):
        """Mark test as passed"""
        self.passed += 1
        print_test(test_name, "PASS")

    def _fail(self, test_name: str, reason: str = ""):
        """Mark test as failed"""
        self.failed += 1
        reason_str = f" ({reason})" if reason else ""
        print_test(test_name, f"FAIL{reason_str}")

    # === RBAC Tests ===

    def verify_rbac(self):
        """Verify RBAC system"""
        print_section("RBAC System Verification")

        # Test 1: User Registration
        try:
            self.rbac.register_user(111, UserRole.ADMIN)
            self.rbac.register_user(333, UserRole.TRADER)
            self.rbac.register_user(555, UserRole.VIEWER)
            self._pass("User registration")
        except Exception as e:
            self._fail("User registration", str(e))

        # Test 2: Admin Retrieval
        try:
            user = self.rbac.get_user(111)
            assert user is not None
            assert user.role == UserRole.ADMIN
            self._pass("Admin user retrieval")
        except Exception as e:
            self._fail("Admin user retrieval", str(e))

        # Test 3: Trader Role
        try:
            user = self.rbac.get_user(333)
            assert user.role == UserRole.TRADER
            self._pass("Trader role verification")
        except Exception as e:
            self._fail("Trader role verification", str(e))

        # Test 4: Viewer Role
        try:
            user = self.rbac.get_user(555)
            assert user.role == UserRole.VIEWER
            self._pass("Viewer role verification")
        except Exception as e:
            self._fail("Viewer role verification", str(e))

        # Test 5: Is Registered
        try:
            assert self.rbac.is_registered(111) is True
            assert self.rbac.is_registered(999) is False
            self._pass("Is registered check")
        except Exception as e:
            self._fail("Is registered check", str(e))

        # Test 6: Is Admin Check
        try:
            assert self.rbac.is_admin(111) is True
            assert self.rbac.is_admin(333) is False
            self._pass("Is admin check")
        except Exception as e:
            self._fail("Is admin check", str(e))

    def verify_permissions(self):
        """Verify permission matrix"""
        print_section("Permission Matrix Verification")

        # Register users
        self.rbac.register_user(111, UserRole.ADMIN)
        self.rbac.register_user(333, UserRole.TRADER)
        self.rbac.register_user(555, UserRole.VIEWER)

        # Test 1: Admin All Permissions
        try:
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

            failed_perms = []
            for perm in admin_perms:
                if not self.rbac.is_authorized(111, perm):
                    failed_perms.append(perm.name)

            if failed_perms:
                self._fail("Admin all permissions", f"Missing: {failed_perms}")
            else:
                self._pass("Admin all permissions")
        except Exception as e:
            self._fail("Admin all permissions", str(e))

        # Test 2: Trader Can Control
        try:
            assert self.rbac.is_authorized(333, Permission.PAUSE_RESUME)
            assert self.rbac.is_authorized(333, Permission.CLOSE_POSITION)
            assert self.rbac.is_authorized(333, Permission.CLOSE_ALL)
            self._pass("Trader control permissions")
        except Exception as e:
            self._fail("Trader control permissions", str(e))

        # Test 3: Trader Cannot Sync
        try:
            assert not self.rbac.is_authorized(333, Permission.SYNC_NOW)
            self._pass("Trader restricted from sync")
        except Exception as e:
            self._fail("Trader restricted from sync", str(e))

        # Test 4: Viewer View Only
        try:
            view_perms = [
                Permission.VIEW_TIME,
                Permission.VIEW_POSITIONS,
                Permission.VIEW_ORDERS,
            ]
            for perm in view_perms:
                assert self.rbac.is_authorized(555, perm)
            self._pass("Viewer view permissions")
        except Exception as e:
            self._fail("Viewer view permissions", str(e))

        # Test 5: Viewer Cannot Control
        try:
            assert not self.rbac.is_authorized(555, Permission.PAUSE_RESUME)
            assert not self.rbac.is_authorized(555, Permission.CLOSE_POSITION)
            assert not self.rbac.is_authorized(555, Permission.CLOSE_ALL)
            self._pass("Viewer restricted from control")
        except Exception as e:
            self._fail("Viewer restricted from control", str(e))

        # Test 6: Unregistered No Access
        try:
            assert not self.rbac.is_authorized(999, Permission.VIEW_TIME)
            self._pass("Unregistered no access")
        except Exception as e:
            self._fail("Unregistered no access", str(e))

    # === Configuration Verification ===

    def verify_config(self):
        """Verify Telegram configuration"""
        print_section("Configuration Verification")

        try:
            from packages.shared.config import settings

            # Test 1: Telegram Bot Token
            try:
                # Should be set or have example
                assert hasattr(settings, 'telegram_bot_token')
                self._pass("Telegram bot token configured")
            except Exception as e:
                self._fail("Telegram bot token configured", str(e))

            # Test 2: Admin IDs
            try:
                assert hasattr(settings, 'telegram_admin_list')
                assert isinstance(settings.telegram_admin_list, list)
                self._pass("Admin IDs configured")
            except Exception as e:
                self._fail("Admin IDs configured", str(e))

            # Test 3: Trader IDs
            try:
                assert hasattr(settings, 'telegram_trader_list')
                assert isinstance(settings.telegram_trader_list, list)
                self._pass("Trader IDs configured")
            except Exception as e:
                self._fail("Trader IDs configured", str(e))

        except ImportError as e:
            self._fail("Configuration import", str(e))

    # === File Structure Verification ===

    def verify_files(self):
        """Verify all Phase 3 files exist"""
        print_section("File Structure Verification")

        import os

        files = [
            ("apps/telegram/__init__.py", "Telegram package init"),
            ("apps/telegram/bot.py", "Telegram bot implementation"),
            ("apps/telegram/rbac.py", "RBAC system"),
            ("apps/telegram/main.py", "Telegram worker main"),
            ("tests/test_telegram.py", "Telegram tests"),
        ]

        for filepath, desc in files:
            full_path = os.path.join("d:\\BotTradingBinace", filepath)
            if os.path.exists(full_path):
                self._pass(f"{desc} exists")
            else:
                self._fail(f"{desc} exists", f"File not found: {filepath}")

    # === Bot Command Structure Verification ===

    def verify_bot_commands(self):
        """Verify bot has all required commands"""
        print_section("Bot Commands Verification")

        try:
            from apps.telegram.bot import TelegramBot

            bot = TelegramBot()
            
            required_commands = [
                "cmd_start",
                "cmd_help",
                "cmd_time",
                "cmd_latency",
                "cmd_health",
                "cmd_price",
                "cmd_spread",
                "cmd_kline",
                "cmd_status",
                "cmd_positions",
                "cmd_orders",
                "cmd_recon",
                "cmd_decision",
                "cmd_trace",
                "cmd_pause",
                "cmd_resume",
                "cmd_close_position",
                "cmd_close_all",
                "handle_confirmation",
            ]

            for cmd in required_commands:
                if hasattr(bot, cmd):
                    self._pass(f"Command {cmd} exists")
                else:
                    self._fail(f"Command {cmd} exists", "Method not found")

        except Exception as e:
            self._fail("Bot command verification", str(e))

    # === Database Integration Verification ===

    async def verify_database_integration(self):
        """Verify database tables for audit logging"""
        print_section("Database Integration Verification")

        try:
            from packages.shared.database import AsyncSessionFactory
            from packages.shared.models import AuditLog
            from sqlalchemy import select

            async with AsyncSessionFactory() as session:
                # Check if AuditLog table exists
                result = await session.execute(
                    select(AuditLog).limit(1)
                )
                self._pass("AuditLog table accessible")

        except Exception as e:
            self._fail("AuditLog table accessible", str(e))

    # === Summary ===

    def print_summary(self):
        """Print verification summary"""
        print_section("Verification Summary")

        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0

        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {percentage:.1f}%\n")

        if self.failed == 0:
            print("🎉 All Phase 3 verifications passed!")
            return True
        else:
            print(f"⚠️ {self.failed} verification(s) failed")
            return False

    async def run_all(self):
        """Run all verifications"""
        print("\n" + "=" * 60)
        print("  PHASE 3 VERIFICATION - Telegram Bot Integration")
        print("=" * 60)

        self.verify_files()
        self.verify_config()
        self.verify_rbac()
        self.verify_permissions()
        self.verify_bot_commands()
        await self.verify_database_integration()

        return self.print_summary()


async def main():
    """Main verification entry point"""
    verifier = Phase3Verifier()
    success = await verifier.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
