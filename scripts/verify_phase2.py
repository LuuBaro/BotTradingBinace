"""
Phase 2 Verification Script
Validates that all Phase 2 requirements are met
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from packages.shared.config import settings
from packages.shared.database import init_db, close_db, AsyncSessionFactory
from packages.shared.exchange.binance_futures import BinanceFuturesClient, get_binance_client
from packages.shared.exchange.binance_ws import BinanceFuturesWebSocket, get_binance_ws
from apps.worker.engine.execution import ExecutionEngine
from apps.worker.engine.reconciler import ReconcilerEngine
from apps.worker.engine.circuit_breaker import CircuitBreaker, CircuitBreakerState


class Phase2Verifier:
    """Verify Phase 2 implementation"""

    def __init__(self):
        self.results = {
            "binance_rest": False,
            "binance_ws": False,
            "db_models": False,
            "execution_engine": False,
            "reconciler": False,
            "circuit_breaker": False,
            "api_endpoints": False,
            "worker_phase2": False,
        }
        self.errors = []

    async def verify_all(self) -> bool:
        """Run all verifications"""
        print("\n" + "="*60)
        print("PHASE 2 VERIFICATION SUITE")
        print("="*60 + "\n")
        
        await self.verify_binance_rest()
        await self.verify_binance_ws()
        await self.verify_db_models()
        await self.verify_execution_engine()
        await self.verify_reconciler()
        await self.verify_circuit_breaker()
        await self.verify_api_endpoints()
        await self.verify_worker_phase2()
        
        self._print_results()
        return all(self.results.values())

    async def verify_binance_rest(self):
        """Verify Binance REST API client"""
        print("\n[1/8] Verifying Binance REST Client...")
        try:
            client = BinanceFuturesClient()
            
            # Check required methods exist
            required_methods = [
                "get_account_balance",
                "get_account_info",
                "get_position_risk",
                "place_order",
                "cancel_order",
                "get_order",
                "get_open_orders",
                "get_ticker_price",
                "get_mark_price",
                "get_klines",
                "set_leverage",
                "set_margin_type",
            ]
            
            for method_name in required_methods:
                if not hasattr(client, method_name):
                    self.errors.append(f"Missing method: {method_name}")
                    return
            
            # Check attributes
            assert hasattr(client, "api_key"), "Missing api_key"
            assert hasattr(client, "api_secret"), "Missing api_secret"
            assert hasattr(client, "base_url"), "Missing base_url"
            assert hasattr(client, "server_time_offset"), "Missing server_time_offset"
            
            self.results["binance_rest"] = True
            print("✓ Binance REST Client verified")
        
        except Exception as e:
            self.errors.append(f"Binance REST verification failed: {str(e)}")
            print(f"✗ Binance REST Client failed: {str(e)}")

    async def verify_binance_ws(self):
        """Verify Binance WebSocket client"""
        print("\n[2/8] Verifying Binance WebSocket...")
        try:
            ws = BinanceFuturesWebSocket()
            
            # Check required methods
            required_methods = [
                "connect",
                "disconnect",
                "subscribe",
                "unsubscribe",
            ]
            
            for method_name in required_methods:
                if not hasattr(ws, method_name):
                    self.errors.append(f"Missing WS method: {method_name}")
                    return
            
            # Check attributes
            assert hasattr(ws, "ws_url"), "Missing ws_url"
            assert hasattr(ws, "is_connected"), "Missing is_connected"
            assert hasattr(ws, "streams"), "Missing streams"
            
            self.results["binance_ws"] = True
            print("✓ Binance WebSocket verified")
        
        except Exception as e:
            self.errors.append(f"Binance WS verification failed: {str(e)}")
            print(f"✗ Binance WebSocket failed: {str(e)}")

    async def verify_db_models(self):
        """Verify database models have new Binance fields"""
        print("\n[3/8] Verifying Database Models...")
        try:
            await init_db()
            
            async with AsyncSessionFactory() as session:
                from sqlalchemy import inspect
                from packages.shared.models import Position
                
                # Inspect Position model
                mapper = inspect(Position)
                columns = {c.name for c in mapper.columns}
                
                # Check for new Binance fields (Phase 2)
                required_columns = {
                    "leverage",
                    "margin_type",
                    "liquidation_price",
                }
                
                for col in required_columns:
                    if col not in columns:
                        self.errors.append(f"Missing column in Position: {col}")
                        return
            
            self.results["db_models"] = True
            print("✓ Database Models verified")
        
        except Exception as e:
            self.errors.append(f"DB models verification failed: {str(e)}")
            print(f"✗ Database Models failed: {str(e)}")
        
        finally:
            await close_db()

    async def verify_execution_engine(self):
        """Verify ExecutionEngine supports both MockExchange and Binance"""
        print("\n[4/8] Verifying Execution Engine...")
        try:
            from packages.shared.exchange.mock import MockExchange
            
            # Test with Mock
            mock_exchange = MockExchange()
            engine_mock = ExecutionEngine(mock_exchange)
            assert engine_mock.is_binance == False, "Mock should not be Binance"
            
            # Test with Binance (if configured)
            if settings.binance_api_key and settings.binance_api_secret:
                binance = BinanceFuturesClient()
                engine_binance = ExecutionEngine(binance)
                assert engine_binance.is_binance == True, "Binance should be detected"
            
            # Check methods
            required_methods = [
                "execute_decision",
                "_open_position",
                "_close_position",
                "_create_sl_order",
                "_create_tp_order",
            ]
            
            for method_name in required_methods:
                if not hasattr(engine_mock, method_name):
                    self.errors.append(f"Missing method: {method_name}")
                    return
            
            self.results["execution_engine"] = True
            print("✓ Execution Engine verified")
        
        except Exception as e:
            self.errors.append(f"Execution Engine verification failed: {str(e)}")
            print(f"✗ Execution Engine failed: {str(e)}")

    async def verify_reconciler(self):
        """Verify Reconciler engine"""
        print("\n[5/8] Verifying Reconciler Engine...")
        try:
            from packages.shared.exchange.mock import MockExchange
            
            exchange = MockExchange()
            reconciler = ReconcilerEngine(exchange)
            
            # Check required methods
            required_methods = [
                "reconcile",
                "_get_db_positions",
                "_get_exchange_positions",
                "sync_positions",
            ]
            
            for method_name in required_methods:
                if not hasattr(reconciler, method_name):
                    self.errors.append(f"Missing reconciler method: {method_name}")
                    return
            
            self.results["reconciler"] = True
            print("✓ Reconciler Engine verified")
        
        except Exception as e:
            self.errors.append(f"Reconciler verification failed: {str(e)}")
            print(f"✗ Reconciler Engine failed: {str(e)}")

    async def verify_circuit_breaker(self):
        """Verify CircuitBreaker"""
        print("\n[6/8] Verifying Circuit Breaker...")
        try:
            cb = CircuitBreaker()
            
            # Check initial state
            assert cb.state == CircuitBreakerState.CLOSED, "Should start CLOSED"
            
            # Check required methods
            required_methods = [
                "record_ws_message",
                "record_rest_request",
                "check_ws_health",
                "is_safe_for_trading",
                "get_status",
            ]
            
            for method_name in required_methods:
                if not hasattr(cb, method_name):
                    self.errors.append(f"Missing CB method: {method_name}")
                    return
            
            # Test basic functionality
            cb.record_ws_message()
            assert cb.is_safe_for_trading(), "Should be safe after WS message"
            
            status = cb.get_status()
            assert "state" in status, "Status missing state"
            assert "is_safe_for_trading" in status, "Status missing is_safe_for_trading"
            
            self.results["circuit_breaker"] = True
            print("✓ Circuit Breaker verified")
        
        except Exception as e:
            self.errors.append(f"Circuit Breaker verification failed: {str(e)}")
            print(f"✗ Circuit Breaker failed: {str(e)}")

    async def verify_api_endpoints(self):
        """Verify new API endpoints exist"""
        print("\n[7/8] Verifying API Endpoints...")
        try:
            from apps.api.main import app
            
            # Get all routes
            routes = {route.path for route in app.routes}
            
            # Check for new Phase 2 endpoints
            required_endpoints = {
                "/actions/pause",
                "/actions/resume",
                "/actions/status",
                "/actions/sync_now",
                "/recon/summary",
                "/circuit-breaker/status",
            }
            
            missing_endpoints = required_endpoints - routes
            if missing_endpoints:
                self.errors.append(f"Missing endpoints: {missing_endpoints}")
                return
            
            self.results["api_endpoints"] = True
            print("✓ API Endpoints verified")
        
        except Exception as e:
            self.errors.append(f"API endpoints verification failed: {str(e)}")
            print(f"✗ API Endpoints failed: {str(e)}")

    async def verify_worker_phase2(self):
        """Verify Phase 2 worker exists"""
        print("\n[8/8] Verifying Phase 2 Worker...")
        try:
            from apps.worker.main_phase2 import Phase2TradingWorker
            
            # Check class exists and has required methods
            worker = Phase2TradingWorker()
            
            required_methods = [
                "initialize",
                "run",
                "shutdown",
                "_execute_loop_iteration",
                "_reconciliation_loop",
                "set_paused",
            ]
            
            for method_name in required_methods:
                if not hasattr(worker, method_name):
                    self.errors.append(f"Missing worker method: {method_name}")
                    return
            
            # Check components
            assert hasattr(worker, "execution_engine"), "Missing execution_engine"
            assert hasattr(worker, "reconciler"), "Missing reconciler"
            assert hasattr(worker, "circuit_breaker"), "Missing circuit_breaker"
            
            self.results["worker_phase2"] = True
            print("✓ Phase 2 Worker verified")
        
        except Exception as e:
            self.errors.append(f"Phase 2 Worker verification failed: {str(e)}")
            print(f"✗ Phase 2 Worker failed: {str(e)}")

    def _print_results(self):
        """Print verification results"""
        print("\n" + "="*60)
        print("VERIFICATION RESULTS")
        print("="*60 + "\n")
        
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        
        for name, result in self.results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {name}")
        
        print(f"\nTotal: {passed}/{total} checks passed")
        
        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")
        
        if passed == total:
            print("\n✓ ALL PHASE 2 REQUIREMENTS MET")
            return True
        else:
            print(f"\n✗ {total - passed} REQUIREMENTS FAILED")
            return False


async def main():
    """Run verification"""
    verifier = Phase2Verifier()
    success = await verifier.verify_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
