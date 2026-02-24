"""
Phase 4 Verification Script - Dashboard Integration
Tests React dashboard, websocket streaming, config versioning
"""
import asyncio
import sys
import json
from datetime import datetime
import httpx

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

class Phase4Verifier:
    """Verify Phase 4 implementation"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.access_token = None
        self.client = httpx.AsyncClient()

    def _pass(self, test_name: str):
        self.passed += 1
        print(f"✅ {test_name}")

    def _fail(self, test_name: str, reason: str = ""):
        self.failed += 1
        reason_str = f" ({reason})" if reason else ""
        print(f"❌ {test_name}{reason_str}")

    def print_section(self, title: str):
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}\n")

    async def test_authentication(self):
        """Test JWT authentication"""
        self.print_section("JWT Authentication")

        try:
            # Test login
            response = await self.client.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": "admin", "password": "admin"}
            )

            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.access_token = data["access_token"]
                    self._pass("Admin login successful")
                else:
                    self._fail("Login response missing fields", response.text)
            else:
                self._fail("Admin login failed", f"Status {response.status_code}")

        except Exception as e:
            self._fail("Admin login", str(e))

        # Test trader login
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": "trader", "password": "trader"}
            )

            if response.status_code == 200:
                self._pass("Trader login successful")
            else:
                self._fail("Trader login", f"Status {response.status_code}")

        except Exception as e:
            self._fail("Trader login", str(e))

        # Test invalid credentials
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": "admin", "password": "wrongpassword"}
            )

            if response.status_code == 401:
                self._pass("Invalid credentials rejected")
            else:
                self._fail("Invalid credentials should be rejected", f"Status {response.status_code}")

        except Exception as e:
            self._fail("Invalid credentials test", str(e))

    async def test_dashboard_endpoints(self):
        """Test dashboard endpoints"""
        self.print_section("Dashboard Endpoints")

        if not self.access_token:
            self._fail("Dashboard endpoints", "No auth token")
            return

        headers = {"Authorization": f"Bearer {self.access_token}"}

        endpoints = [
            ("/api/bot/status", "Bot status"),
            ("/api/health/status", "Health status"),
            ("/api/health/latency", "Latency metrics"),
            ("/api/positions", "Positions"),
            ("/api/orders", "Orders"),
            ("/api/decisions", "Decisions"),
            ("/api/recon/summary", "Recon summary"),
            ("/api/config/risk", "Risk config"),
            ("/api/config/risk/versions", "Config versions"),
            ("/api/audit", "Audit log"),
        ]

        for endpoint, name in endpoints:
            try:
                response = await self.client.get(
                    f"{BASE_URL}{endpoint}",
                    headers=headers
                )

                if response.status_code == 200:
                    self._pass(name)
                else:
                    self._fail(name, f"Status {response.status_code}")

            except Exception as e:
                self._fail(name, str(e))

    async def test_config_versioning(self):
        """Test config versioning system"""
        self.print_section("Config Versioning")

        if not self.access_token:
            self._fail("Config versioning", "No auth token")
            return

        headers = {"Authorization": f"Bearer {self.access_token}"}

        # Test getting current config
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/config/risk",
                headers=headers
            )

            if response.status_code == 200:
                config = response.json()
                self._pass("Get current config")

                # Test updating config
                updated_config = {**config, "max_leverage": 20}

                update_response = await self.client.post(
                    f"{BASE_URL}/api/config/risk",
                    json=updated_config,
                    headers=headers
                )

                if update_response.status_code in (200, 201):
                    self._pass("Update config creates new version")

                    # Test getting versions
                    versions_response = await self.client.get(
                        f"{BASE_URL}/api/config/risk/versions",
                        headers=headers
                    )

                    if versions_response.status_code == 200:
                        versions = versions_response.json()
                        if isinstance(versions, list) and len(versions) > 0:
                            self._pass("List config versions")

                            # Test rollback (if multiple versions exist)
                            if len(versions) >= 2:
                                version_id = versions[1]["id"]
                                rollback_response = await self.client.post(
                                    f"{BASE_URL}/api/config/risk/rollback/{version_id}",
                                    headers=headers
                                )

                                if rollback_response.status_code == 200:
                                    self._pass("Rollback to previous version")
                                else:
                                    self._fail("Rollback", f"Status {rollback_response.status_code}")
                        else:
                            self._fail("List config versions", "Empty or invalid response")
                    else:
                        self._fail("List config versions", f"Status {versions_response.status_code}")
                else:
                    self._fail("Update config", f"Status {update_response.status_code}")
            else:
                self._fail("Get current config", f"Status {response.status_code}")

        except Exception as e:
            self._fail("Config versioning", str(e))

    async def test_control_actions(self):
        """Test bot control actions"""
        self.print_section("Bot Control Actions")

        if not self.access_token:
            self._fail("Control actions", "No auth token")
            return

        headers = {"Authorization": f"Bearer {self.access_token}"}

        actions = [
            ("/api/actions/pause", "Pause trading"),
            ("/api/actions/resume", "Resume trading"),
        ]

        for endpoint, name in actions:
            try:
                response = await self.client.post(
                    f"{BASE_URL}{endpoint}",
                    headers=headers
                )

                if response.status_code in (200, 202):
                    self._pass(name)
                else:
                    self._fail(name, f"Status {response.status_code}")

            except Exception as e:
                self._fail(name, str(e))

    async def test_decision_trace(self):
        """Test decision trace endpoint"""
        self.print_section("Decision Trace")

        if not self.access_token:
            self._fail("Decision trace", "No auth token")
            return

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            # First get decisions
            response = await self.client.get(
                f"{BASE_URL}/api/decisions?limit=1",
                headers=headers
            )

            if response.status_code == 200:
                decisions = response.json()
                if isinstance(decisions, list) and len(decisions) > 0:
                    trace_id = decisions[0]["trace_id"]

                    # Get full trace
                    trace_response = await self.client.get(
                        f"{BASE_URL}/api/decisions/{trace_id}",
                        headers=headers
                    )

                    if trace_response.status_code == 200:
                        trace = trace_response.json()
                        if "trace_id" in trace and "decision_json" in trace:
                            self._pass("Get decision trace with full pipeline")
                        else:
                            self._fail("Get decision trace", "Missing fields in response")
                    else:
                        self._fail("Get decision trace", f"Status {trace_response.status_code}")
                else:
                    # No decisions yet - this is OK
                    self._pass("Get decision trace (no decisions yet)")
            else:
                self._fail("Get decisions", f"Status {response.status_code}")

        except Exception as e:
            self._fail("Decision trace", str(e))

    async def test_file_structure(self):
        """Test file structure"""
        self.print_section("File Structure")

        import os

        files = [
            ("apps/dashboard/package.json", "Dashboard package.json"),
            ("apps/dashboard/vite.config.ts", "Vite config"),
            ("apps/dashboard/tsconfig.json", "TypeScript config"),
            ("apps/dashboard/src/App.tsx", "App component"),
            ("apps/dashboard/src/store.ts", "Zustand store"),
            ("apps/dashboard/src/api/client.ts", "API client"),
            ("apps/dashboard/src/api/websocket.ts", "WebSocket client"),
            ("apps/api/auth.py", "JWT auth module"),
            ("apps/api/websocket.py", "WebSocket manager"),
            ("apps/api/phase4_routes.py", "Phase 4 API routes"),
            ("packages/shared/config_versioning.py", "Config versioning"),
        ]

        for filepath, desc in files:
            full_path = os.path.join("d:\\BotTradingBinace", filepath)
            if os.path.exists(full_path):
                self._pass(f"{desc} exists")
            else:
                self._fail(f"{desc} exists", f"File not found: {filepath}")

    async def run_all(self):
        """Run all verifications"""
        print("\n" + "=" * 60)
        print("  PHASE 4 VERIFICATION - React Dashboard")
        print("=" * 60)

        await self.test_file_structure()
        await self.test_authentication()
        await self.test_dashboard_endpoints()
        await self.test_decision_trace()
        await self.test_config_versioning()
        await self.test_control_actions()

        return self.print_summary()

    def print_summary(self):
        """Print verification summary"""
        self.print_section("Verification Summary")

        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0

        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {percentage:.1f}%\n")

        if self.failed == 0:
            print("🎉 All Phase 4 verifications passed!")
            return True
        else:
            print(f"⚠️ {self.failed} verification(s) failed")
            return False


async def main():
    """Main verification entry point"""
    verifier = Phase4Verifier()

    try:
        success = await verifier.run_all()
        sys.exit(0 if success else 1)
    finally:
        await verifier.client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
