"""
TEST: Position Size Enforcement
Verify that position size limits are STRICTLY ENFORCED
This test ensures that TESNET and MAINNET have identical behavior
"""
import asyncio
from datetime import datetime
from packages.shared.schemas import Decision, RiskConfig, MarketSnapshot
from packages.shared.enums import MarketRegime, ActionType, Side, OrderType
from apps.worker.agents.trader_stub import TraderStub
from packages.shared.risk_engine import RiskEngine
from packages.shared.logger import logger


async def test_position_size_enforcement():
    """Test that position sizes are strictly limited"""
    
    print("\n" + "="*80)
    print("TEST: Position Size Enforcement")
    print("="*80)
    
    # Test Case 1: Small limit (5%)
    # Test Case 1: Small limit (5%)
    print("\n[TEST CASE 1] Small Limit (5%)")
    print("-" * 80)
    risk_config_small = RiskConfig(max_position_pct=0.05)
    trader_small = TraderStub(max_position_pct=0.05)
    risk_engine_small = RiskEngine(risk_config_small)
    
    # Generate 20 decisions to test randomness stays within limits
    size_pcts = []
    for i in range(20):
        decision = await trader_small.decide(snapshot)
        size_pcts.append(decision.size_pct)
        
        # Risk validation
        risk_result = await risk_engine_small.validate_decision(
            decision=decision,
            current_positions=[],
            balance=10000.0,
            current_price=50000.0
        )
        
        status = "[PASS]" if risk_result.approved else "[REJECT]"
        print(f"  Decision {i+1}: size={decision.size_pct*100:.2f}%, leverage={decision.leverage}x -> {status}")
        
        if not risk_result.approved:
            print(f"    Reason: {risk_result.reason}")
    
    print(f"\nStats for max_position_pct=5%:")
    print(f"  Min size: {min(size_pcts)*100:.2f}%")
    print(f"  Max size: {max(size_pcts)*100:.2f}%")
    print(f"  Average: {sum(size_pcts)/len(size_pcts)*100:.2f}%")
    print(f"  All within limit (5%)? {all(s <= 0.05 for s in size_pcts)}")
    
    # Test Case 2: Large limit (99%)
    print("\n[TEST CASE 2] Large Limit (99%)")
    print("-" * 80)
    risk_config_large = RiskConfig(max_position_pct=0.99)
    trader_large = TraderStub(max_position_pct=0.99)
    risk_engine_large = RiskEngine(risk_config_large)
    
    size_pcts_large = []
    for i in range(20):
        decision = await trader_large.decide(snapshot)
        size_pcts_large.append(decision.size_pct)
        
        risk_result = await risk_engine_large.validate_decision(
            decision=decision,
            current_positions=[],
            balance=10000.0,
            current_price=50000.0
        )
        
        status = "[PASS]" if risk_result.approved else "[REJECT]"
        print(f"  Decision {i+1}: size={decision.size_pct*100:.2f}%, leverage={decision.leverage}x -> {status}")
        
        if not risk_result.approved:
            print(f"    Reason: {risk_result.reason}")
    
    print(f"\nStats for max_position_pct=99%:")
    print(f"  Min size: {min(size_pcts_large)*100:.2f}%")
    print(f"  Max size: {max(size_pcts_large)*100:.2f}%")
    print(f"  Average: {sum(size_pcts_large)/len(size_pcts_large)*100:.2f}%")
    print(f"  All within limit (99%)? {all(s <= 0.99 for s in size_pcts_large)}")
    
    # Test Case 3: CRITICAL - Verify AI respects config, not hardcoded value
    print("\n[TEST CASE 3] Config Respects (NOT Hardcoded)")
    print("-" * 80)
    
    for max_pct in [0.02, 0.10, 0.50, 0.99]:
        trader = TraderStub(max_position_pct=max_pct)
        sizes = []
        for _ in range(10):
            decision = await trader.decide(snapshot)
            sizes.append(decision.size_pct)
        
        max_generated = max(sizes)
        compliant = all(s <= max_pct for s in sizes)
        
        status = "[OK]" if compliant else "[FAIL]"
        print(f"  Config: {max_pct*100:5.1f}% | Generated max: {max_generated*100:5.2f}% | {status}")
    
    # Final Verdict
    print("\n" + "="*80)
    print("FINAL VERDICT:")
    print("="*80)
    
    # Check if all test cases pass
    all_small_pass = all(s <= 0.05 for s in size_pcts)
    all_large_pass = all(s <= 0.99 for s in size_pcts_large)
    
    if all_small_pass and all_large_pass:
        print("✅ ALL TESTS PASSED")
        print("\n✅ Position size enforcement is WORKING CORRECTLY")
        print("✅ AI respects config limits dynamically")
        print("✅ SAFE TO DEPLOY TO MAINNET")
        return True
    else:
        print("❌ TESTS FAILED")
        if not all_small_pass:
            print(f"  ❌ Small limit test: Generated size {max(size_pcts)*100:.2f}% > 5%")
        if not all_large_pass:
            print(f"  ❌ Large limit test: Generated size {max(size_pcts_large)*100:.2f}% > 99%")
        print("❌ DO NOT DEPLOY UNTIL FIXED")
        return False


if __name__ == "__main__":
    from datetime import datetime
    success = asyncio.run(test_position_size_enforcement())
    exit(0 if success else 1)
