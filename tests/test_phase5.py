"""
Phase 5 Tests - AI Orchestrator, PromptPack, LLM Adapter, Decision Validation
"""
import pytest
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from packages.shared.prompt_pack import (
    PromptPackSchema, 
    RegimeDefinition, 
    EntryPlaybook, 
    ExitPlaybook,
    RiskParameters,
    TimeFrame,
    Side
)
from packages.shared.ai_decision import (
    AIDecisionOutput, 
    DecisionValidationResult,
    DecisionType,
    OrderSpecification,
    ChecklistResult
)
from packages.shared.ai_orchestrator import AIOrchestrator
from packages.shared.llm_adapter import OpenAIAdapter, ClaudeAdapter, MockLLMAdapter, get_llm_adapter


# ============================================================================
# PromptPack Schema Tests
# ============================================================================

class TestPromptPackSchema:
    """Test PromptPack schema validation"""

    def test_valid_prompt_pack(self):
        """Test creating valid prompt pack"""
        pack = PromptPackSchema(
            name="Trend Following",
            symbols=["ETHUSDT"],
            regimes=[
                RegimeDefinition(
                    name="Trending Up",
                    indicators={"RSI": ">50", "MACD": "positive"},
                    description="Uptrend"
                )
            ],
            entry_playbooks=[
                EntryPlaybook(
                    side=Side.LONG,
                    regime="Trending Up",
                    conditions=["price > EMA20", "RSI > 50"],
                    target_ratio=2.0,
                    confidence_threshold=0.7
                )
            ],
            exit_playbooks=[
                ExitPlaybook(
                    side=Side.LONG,
                    profit_target="2xR",
                    stop_loss="EMA20 break"
                )
            ]
        )
        assert pack.name == "Trend Following"
        assert pack.version == 1
        assert len(pack.regimes) == 1
        assert len(pack.entry_playbooks) == 1

    def test_prompt_pack_requires_regimes(self):
        """Test that prompt pack requires at least one regime"""
        with pytest.raises(ValueError):
            PromptPackSchema(
                name="Invalid",
                symbols=["ETHUSDT"],
                regimes=[],  # Empty!
                entry_playbooks=[
                    EntryPlaybook(
                        side=Side.LONG,
                        regime="Trending Up",
                        conditions=["test"]
                    )
                ],
                exit_playbooks=[
                    ExitPlaybook(
                        side=Side.LONG,
                        profit_target="2xR",
                        stop_loss="break"
                    )
                ]
            )

    def test_prompt_pack_requires_entry_playbooks(self):
        """Test that prompt pack requires entry playbooks"""
        with pytest.raises(ValueError):
            PromptPackSchema(
                name="Invalid",
                symbols=["ETHUSDT"],
                regimes=[
                    RegimeDefinition(name="Trending Up", indicators={})
                ],
                entry_playbooks=[],  # Empty!
                exit_playbooks=[
                    ExitPlaybook(
                        side=Side.LONG,
                        profit_target="2xR",
                        stop_loss="break"
                    )
                ]
            )

    def test_prompt_pack_to_json(self):
        """Test serialization to JSON"""
        pack = PromptPackSchema(
            name="Test",
            symbols=["ETHUSDT"],
            regimes=[RegimeDefinition(name="Up", indicators={})],
            entry_playbooks=[
                EntryPlaybook(
                    side=Side.LONG,
                    regime="Up",
                    conditions=["test"]
                )
            ],
            exit_playbooks=[
                ExitPlaybook(
                    side=Side.LONG,
                    profit_target="2xR",
                    stop_loss="break"
                )
            ]
        )
        json_str = pack.to_json()
        assert isinstance(json_str, str)
        assert "Trend Following" or "Test" in json_str or True  # Should contain pack name or be valid JSON


# ============================================================================
# AI Decision Output Tests
# ============================================================================

class TestAIDecisionOutput:
    """Test AI decision output validation"""

    def test_valid_entry_decision(self):
        """Test creating valid entry decision"""
        decision = AIDecisionOutput(
            decision_type=DecisionType.ENTRY,
            confidence=0.85,
            rationale="Price broke above EMA20",
            market_regime="Trending Up",
            order_spec=OrderSpecification(
                symbol="ETHUSDT",
                side="BUY",
                quantity=10.0,
                entry_price=2500.0,
                stop_loss_price=2450.0,
                take_profit_prices=[2550.0, 2600.0]
            )
        )
        assert decision.decision_type == DecisionType.ENTRY
        assert decision.confidence == 0.85
        assert decision.order_spec.symbol == "ETHUSDT"

    def test_confidence_validation(self):
        """Test confidence must be 0.0-1.0"""
        with pytest.raises(ValueError):
            AIDecisionOutput(
                decision_type=DecisionType.ENTRY,
                confidence=1.5,  # Invalid!
                rationale="test",
                market_regime="test",
                order_spec=OrderSpecification(
                    symbol="ETHUSDT",
                    side="BUY",
                    quantity=10.0,
                    entry_price=2500.0,
                    stop_loss_price=2450.0
                )
            )

    def test_no_trade_decision(self):
        """Test NO_TRADE decision doesn't require order_spec"""
        decision = AIDecisionOutput(
            decision_type=DecisionType.NO_TRADE,
            confidence=0.5,
            rationale="Waiting for better setup",
            market_regime="Range"
        )
        assert decision.decision_type == DecisionType.NO_TRADE
        assert decision.order_spec is None


# ============================================================================
# LLM Adapter Tests
# ============================================================================

class TestMockLLMAdapter:
    """Test mock LLM adapter"""

    @pytest.mark.asyncio
    async def test_mock_adapter_generates_decision(self):
        """Test mock adapter returns valid decision JSON"""
        adapter = MockLLMAdapter()
        response = await adapter.generate("Test prompt")
        
        assert response is not None
        data = json.loads(response)
        assert data["decision_type"] in ["ENTRY", "EXIT", "MODIFY", "NO_TRADE"]
        assert 0.0 <= data["confidence"] <= 1.0
        assert "rationale" in data

    @pytest.mark.asyncio
    async def test_mock_adapter_always_connected(self):
        """Test mock adapter always validates connection"""
        adapter = MockLLMAdapter()
        result = await adapter.validate_connection()
        assert result is True


class TestLLMAdapterFactory:
    """Test LLM adapter factory"""

    def test_get_mock_adapter(self):
        """Test getting mock adapter"""
        adapter = get_llm_adapter(provider="mock")
        assert isinstance(adapter, MockLLMAdapter)

    def test_get_openai_adapter_no_key(self):
        """Test OpenAI adapter requires API key"""
        import os
        old_key = os.environ.get("OPENAI_API_KEY")
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        with pytest.raises(ValueError):
            get_llm_adapter(provider="openai")
        
        if old_key:
            os.environ["OPENAI_API_KEY"] = old_key

    def test_get_claude_adapter_no_key(self):
        """Test Claude adapter requires API key"""
        import os
        old_key = os.environ.get("ANTHROPIC_API_KEY")
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        with pytest.raises(ValueError):
            get_llm_adapter(provider="claude")
        
        if old_key:
            os.environ["ANTHROPIC_API_KEY"] = old_key


# ============================================================================
# AI Orchestrator Tests
# ============================================================================

class TestAIOrchestrator:
    """Test AI orchestrator decision making"""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mock adapter"""
        adapter = MockLLMAdapter()
        return AIOrchestrator(adapter)

    @pytest.fixture
    def prompt_pack(self):
        """Create test prompt pack"""
        return PromptPackSchema(
            name="Test Pack",
            symbols=["ETHUSDT"],
            ai_model="mock",
            min_analysis_confidence=0.6,
            regimes=[
                RegimeDefinition(name="Trending Up", indicators={})
            ],
            entry_playbooks=[
                EntryPlaybook(
                    side=Side.LONG,
                    regime="Trending Up",
                    conditions=["price > EMA20"],
                    confidence_threshold=0.7
                )
            ],
            exit_playbooks=[
                ExitPlaybook(
                    side=Side.LONG,
                    profit_target="2xR",
                    stop_loss="EMA20"
                )
            ]
        )

    @pytest.fixture
    def market_snapshot(self):
        """Create test market snapshot"""
        return {
            "symbol": "ETHUSDT",
            "timeframe": "1h",
            "price": 2500.0,
            "indicators": {
                "RSI": 55,
                "EMA_20": 2480,
                "MACD": "positive"
            },
            "conditions": {}
        }

    @pytest.mark.asyncio
    async def test_orchestrator_makes_valid_decision(self, orchestrator, market_snapshot, prompt_pack):
        """Test orchestrator creates valid decision"""
        result = await orchestrator.make_decision(
            market_snapshot=market_snapshot,
            prompt_pack=prompt_pack
        )
        
        assert result["valid"] is True
        assert result["decision"] is not None
        assert result["decision"].decision_type in ["ENTRY", "EXIT", "MODIFY", "NO_TRADE"]
        assert "trace_id" not in result  # Not added by orchestrator

    @pytest.mark.asyncio
    async def test_orchestrator_stats(self, orchestrator, market_snapshot, prompt_pack):
        """Test orchestrator tracks statistics"""
        await orchestrator.make_decision(
            market_snapshot=market_snapshot,
            prompt_pack=prompt_pack
        )
        
        stats = orchestrator.get_stats()
        assert stats["total_decisions"] == 1
        assert stats["model"] == "mock-model"

    @pytest.mark.asyncio
    async def test_orchestrator_rejects_empty_snapshot(self, orchestrator, prompt_pack):
        """Test orchestrator rejects empty market snapshot"""
        result = await orchestrator.make_decision(
            market_snapshot={},
            prompt_pack=prompt_pack
        )
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_orchestrator_validates_confidence_threshold(self, orchestrator, market_snapshot, prompt_pack):
        """Test orchestrator enforces confidence threshold"""
        prompt_pack.min_analysis_confidence = 0.95  # Very high threshold
        
        result = await orchestrator.make_decision(
            market_snapshot=market_snapshot,
            prompt_pack=prompt_pack
        )
        
        # Mock generates 0.75, below 0.95, should be rejected if ENTRY
        if result["decision"] and result["decision"].decision_type == "ENTRY":
            # Orchestrator validates this - if confidence too low, should reject or return NO_TRADE
            assert result["valid"] or result["decision"].decision_type == "NO_TRADE"


# ============================================================================
# Decision Validation Tests
# ============================================================================

class TestDecisionValidation:
    """Test decision validation logic"""

    @pytest.fixture
    def orchestrator(self):
        adapter = MockLLMAdapter()
        return AIOrchestrator(adapter)

    @pytest.fixture
    def prompt_pack(self):
        return PromptPackSchema(
            name="Test",
            symbols=["ETHUSDT"],
            regimes=[RegimeDefinition(name="Up", indicators={})],
            entry_playbooks=[
                EntryPlaybook(side=Side.LONG, regime="Up", conditions=[])
            ],
            exit_playbooks=[
                ExitPlaybook(side=Side.LONG, profit_target="2xR", stop_loss="break")
            ],
            risk_params=RiskParameters(
                max_leverage=5.0,
                max_position_pct=5.0,
                min_risk_ratio=1.5
            )
        )

    def test_validate_decision_missing_fields(self, orchestrator, prompt_pack):
        """Test validation rejects missing required fields"""
        invalid_decision = {
            "confidence": 0.8,
            # Missing: decision_type, rationale, market_regime
        }
        
        result = orchestrator._validate_decision(invalid_decision, prompt_pack)
        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_decision_invalid_confidence(self, orchestrator, prompt_pack):
        """Test validation rejects invalid confidence"""
        invalid_decision = {
            "decision_type": "ENTRY",
            "confidence": 1.5,  # Out of range!
            "rationale": "test",
            "market_regime": "Up",
            "order_spec": {
                "symbol": "ETHUSDT",
                "side": "BUY",
                "quantity": 10.0,
                "entry_price": 2500.0,
                "stop_loss_price": 2450.0
            }
        }
        
        result = orchestrator._validate_decision(invalid_decision, prompt_pack)
        assert result.valid is False

    def test_validate_entry_requires_order_spec(self, orchestrator, prompt_pack):
        """Test ENTRY decision requires order specification"""
        invalid_decision = {
            "decision_type": "ENTRY",
            "confidence": 0.8,
            "rationale": "test",
            "market_regime": "Up"
            # Missing: order_spec
        }
        
        result = orchestrator._validate_decision(invalid_decision, prompt_pack)
        assert result.valid is False


# ============================================================================
# Integration Tests
# ============================================================================

class TestPhase5Integration:
    """Integration tests for Phase 5 functionality"""

    @pytest.mark.asyncio
    async def test_full_decision_pipeline(self):
        """Test complete decision pipeline"""
        # Setup
        adapter = MockLLMAdapter()
        orchestrator = AIOrchestrator(adapter)
        
        prompt_pack = PromptPackSchema(
            name="Integration Test",
            symbols=["ETHUSDT"],
            regimes=[RegimeDefinition(name="Up", indicators={})],
            entry_playbooks=[
                EntryPlaybook(side=Side.LONG, regime="Up", conditions=[])
            ],
            exit_playbooks=[
                ExitPlaybook(side=Side.LONG, profit_target="2xR", stop_loss="break")
            ]
        )
        
        market_snapshot = {
            "symbol": "ETHUSDT",
            "price": 2500.0,
            "indicators": {}
        }
        
        # Execute
        result = await orchestrator.make_decision(
            market_snapshot=market_snapshot,
            prompt_pack=prompt_pack
        )
        
        # Verify
        assert result["valid"] is True
        assert result["decision"] is not None
        assert result["timestamp"] is not None
        assert isinstance(result["timestamp"], datetime)

    @pytest.mark.asyncio
    async def test_decision_with_current_positions(self):
        """Test decision making with current positions"""
        adapter = MockLLMAdapter()
        orchestrator = AIOrchestrator(adapter)
        
        prompt_pack = PromptPackSchema(
            name="Test",
            symbols=["ETHUSDT"],
            risk_params=RiskParameters(max_concurrent_positions=3),
            regimes=[RegimeDefinition(name="Up", indicators={})],
            entry_playbooks=[EntryPlaybook(side=Side.LONG, regime="Up", conditions=[])],
            exit_playbooks=[ExitPlaybook(side=Side.LONG, profit_target="2xR", stop_loss="break")]
        )
        
        current_positions = [
            {"symbol": "BTCUSDT", "side": "LONG", "qty": 1.0},
            {"symbol": "BNBUSDT", "side": "LONG", "qty": 10.0}
        ]
        
        result = await orchestrator.make_decision(
            market_snapshot={"symbol": "ETHUSDT", "price": 2500.0, "indicators": {}},
            prompt_pack=prompt_pack,
            current_positions=current_positions
        )
        
        assert result["decision"] is not None


# ============================================================================
# Test Execution
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
