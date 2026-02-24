"""
Test Risk Engine validation rules
"""
import pytest
from packages.shared.schemas import Decision, RiskConfig, ChecklistItem
from packages.shared.enums import MarketRegime, ActionType, Side, OrderType, RiskResult
from packages.shared.risk_engine import RiskEngine


@pytest.fixture
def strict_risk_config():
    """Risk config with strict limits"""
    return RiskConfig(
        max_drawdown_day_pct=0.05,
        max_position_pct=0.2,
        max_leverage=3,
        max_risk_per_trade_pct=0.01,
        max_orders_per_hour=5,
        max_concurrent_positions=2,
        cooldown_after_loss=300,
        mandatory_sl_tp=True,
    )


@pytest.fixture
def valid_decision():
    """Valid trading decision"""
    return Decision(
        regime=MarketRegime.TREND,
        action=ActionType.OPEN,
        symbol="BTCUSDT",
        side=Side.LONG,
        entry_type=OrderType.MARKET,
        entry_price=50000.0,
        size_pct=0.1,
        leverage=2,
        stop_loss=49000.0,
        take_profit=52000.0,
        confidence=0.8,
        rationale="Test decision",
        checklist=[],
    )


@pytest.mark.asyncio
async def test_reject_missing_sl(strict_risk_config):
    """Test rejection when stop loss is missing"""
    engine = RiskEngine(strict_risk_config)
    
    decision = Decision(
        regime=MarketRegime.TREND,
        action=ActionType.OPEN,
        symbol="BTCUSDT",
        side=Side.LONG,
        entry_type=OrderType.MARKET,
        entry_price=50000.0,
        size_pct=0.1,
        leverage=2,
        stop_loss=None,  # Missing SL!
        take_profit=52000.0,
        confidence=0.8,
        rationale="Test",
        checklist=[],
    )
    
    result = await engine.validate_decision(
        decision=decision,
        current_positions=[],
        balance=10000.0,
        current_price=50000.0,
    )
    
    assert not result.approved
    assert result.result == RiskResult.REJECTED
    assert "SL/TP" in result.reason


@pytest.mark.asyncio
async def test_reject_excessive_leverage(strict_risk_config):
    """Test rejection when leverage exceeds limit"""
    engine = RiskEngine(strict_risk_config)
    
    decision = Decision(
        regime=MarketRegime.TREND,
        action=ActionType.OPEN,
        symbol="BTCUSDT",
        side=Side.LONG,
        entry_type=OrderType.MARKET,
        entry_price=50000.0,
        size_pct=0.1,
        leverage=10,  # Exceeds max_leverage=3
        stop_loss=49000.0,
        take_profit=52000.0,
        confidence=0.8,
        rationale="Test",
        checklist=[],
    )
    
    result = await engine.validate_decision(
        decision=decision,
        current_positions=[],
        balance=10000.0,
        current_price=50000.0,
    )
    
    assert not result.approved
    assert result.result == RiskResult.REJECTED
    assert "Leverage" in result.reason


@pytest.mark.asyncio
async def test_reject_excessive_position_size(strict_risk_config):
    """Test rejection when position size is too large"""
    engine = RiskEngine(strict_risk_config)
    
    decision = Decision(
        regime=MarketRegime.TREND,
        action=ActionType.OPEN,
        symbol="BTCUSDT",
        side=Side.LONG,
        entry_type=OrderType.MARKET,
        entry_price=50000.0,
        size_pct=0.5,  # 50% exceeds max_position_pct=20%
        leverage=2,
        stop_loss=49000.0,
        take_profit=52000.0,
        confidence=0.8,
        rationale="Test",
        checklist=[],
    )
    
    result = await engine.validate_decision(
        decision=decision,
        current_positions=[],
        balance=10000.0,
        current_price=50000.0,
    )
    
    assert not result.approved
    assert result.result == RiskResult.REJECTED
    assert "Position size" in result.reason


@pytest.mark.asyncio
async def test_reject_too_many_positions(strict_risk_config):
    """Test rejection when max concurrent positions reached"""
    engine = RiskEngine(strict_risk_config)
    
    # Already have 2 positions (max is 2)
    current_positions = [
        {"symbol": "BTCUSDT", "side": "long", "qty": 0.1},
        {"symbol": "ETHUSDT", "side": "short", "qty": 1.0},
    ]
    
    decision = Decision(
        regime=MarketRegime.TREND,
        action=ActionType.OPEN,
        symbol="BNBUSDT",
        side=Side.LONG,
        entry_type=OrderType.MARKET,
        entry_price=400.0,
        size_pct=0.1,
        leverage=2,
        stop_loss=390.0,
        take_profit=420.0,
        confidence=0.8,
        rationale="Test",
        checklist=[],
    )
    
    result = await engine.validate_decision(
        decision=decision,
        current_positions=current_positions,
        balance=10000.0,
        current_price=400.0,
    )
    
    assert not result.approved
    assert result.result == RiskResult.REJECTED
    assert "concurrent positions" in result.reason


@pytest.mark.asyncio
async def test_approve_valid_decision(strict_risk_config, valid_decision):
    """Test approval of valid decision"""
    engine = RiskEngine(strict_risk_config)
    
    result = await engine.validate_decision(
        decision=valid_decision,
        current_positions=[],
        balance=10000.0,
        current_price=50000.0,
    )
    
    assert result.approved
    assert result.result == RiskResult.APPROVED


@pytest.mark.asyncio
async def test_hold_always_approved(strict_risk_config):
    """Test that HOLD action is always approved"""
    engine = RiskEngine(strict_risk_config)
    
    decision = Decision(
        regime=MarketRegime.RANGE,
        action=ActionType.HOLD,
        symbol="BTCUSDT",
        side=None,
        size_pct=0.0,
        leverage=1,
        stop_loss=None,
        take_profit=None,
        confidence=0.6,
        rationale="Not favorable",
        checklist=[],
    )
    
    result = await engine.validate_decision(
        decision=decision,
        current_positions=[],
        balance=10000.0,
        current_price=50000.0,
    )
    
    assert result.approved
    assert result.result == RiskResult.APPROVED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
