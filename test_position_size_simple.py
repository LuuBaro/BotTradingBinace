"""
TEST: Position Size Enforcement
Verify that AI respects position size limits dynamically
"""
import asyncio
from datetime import datetime
from packages.shared.schemas import RiskConfig, MarketSnapshot
from apps.worker.agents.trader_stub import TraderStub
from packages.shared.risk_engine import RiskEngine


async def test_position_size_enforcement():
    """Test position sizes are strictly limited per config"""
    
    print("\n" + "="*80)
    print("TEST: Position Size Enforcement")
    print("="*80)
    
    # Create snapshot
    snapshot = MarketSnapshot(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=49900.0,
        high=51000.0,
        low=49000.0,
        close=50000.0,
        volume=100000.0
    )
    
    # Test with multiple limits
    test_limits = [0.05, 0.10, 0.50, 0.99]
    all_pass = True
    
    for max_limit in test_limits:
        print(f"\n[TEST] max_position_pct = {max_limit*100:.1f}%")
        print("-" * 80)
        
        trader = TraderStub(max_position_pct=max_limit)
        risk_engine = RiskEngine(RiskConfig(max_position_pct=max_limit))
        
        sizes = []
        for i in range(15):
            decision = await trader.decide(snapshot)
            sizes.append(decision.size_pct)
            
            risk_result = await risk_engine.validate_decision(
                decision=decision,
                current_positions=[],
                balance=10000.0,
                current_price=50000.0
            )
            
            status = "[PASS]" if risk_result.approved else "[REJECT]"
            print(f"  {i+1:2d}. size={decision.size_pct*100:5.2f}%, leverage={decision.leverage}x -> {status}")
        
        min_size = min(sizes) * 100
        max_size = max(sizes) * 100
        compliant = all(s <= max_limit for s in sizes)
        
        print(f"\n  Stats:")
        print(f"    Min: {min_size:6.2f}% | Max: {max_size:6.2f}% | Limit: {max_limit*100:5.1f}%")
        print(f"    Compliant: {compliant}")
        
        if not compliant:
            print(f"  [FAIL] Generated {max_size:5.2f}% exceeds limit {max_limit*100:.1f}%")
            all_pass = False
        else:
            print(f"  [OK] All sizes within limit")
    
    # Final result
    print("\n" + "="*80)
    if all_pass:
        print("✓ ALL TESTS PASSED")
        print("✓ Position size enforcement is WORKING")
        print("✓ SAFE TO DEPLOY")
        print("="*80)
        return True
    else:
        print("X TESTS FAILED")
        print("X DO NOT DEPLOY")
        print("="*80)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_position_size_enforcement())
    exit(0 if success else 1)
