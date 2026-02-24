"""
Phase 6 Tests - Learning Agent and Trade Journal
"""
import pytest
from datetime import datetime, timedelta
from packages.shared.trade_journal import (
    TradeJournalEntry, ExitReason, TradeJournalStats, 
    PatternsDiscovered, ConfidenceMetrics
)
from packages.shared.learning_agent import (
    LearningAgent, SuggestedAdaptations, LearningReport
)


class TestTradeJournalEntry:
    """Test trade journal entry schema"""

    def test_create_winning_trade(self):
        """Test creating a winning trade entry"""
        trade = TradeJournalEntry(
            trade_id="trade_001",
            symbol="BTCUSDT",
            side="LONG",
            entry_time=datetime.utcnow(),
            exit_time=datetime.utcnow() + timedelta(hours=1),
            entry_price=50000.0,
            exit_price=51000.0,
            position_size=1.0,
            entry_reason="volatility_breakout",
            exit_reason=ExitReason.TAKE_PROFIT,
            pnl=1000.0,
            pnl_pct=0.02,
            max_profit=1500.0,
            max_loss=200.0,
            market_regime="trending_up",
            volatility_percentile=75,
            spread_avg=5.5,
            funding_rate=0.001,
            leverage=1.0,
            ai_model="claude-3",
            confidence=0.85,
            decision_json={"logic": "breakout"},
            is_winner=True,
            is_breakeven=False,
            prompt_pack_version="v1.0",
            trace_id="trace_001"
        )

        assert trade.trade_id == "trade_001"
        assert trade.symbol == "BTCUSDT"
        assert trade.is_winner is True
        assert trade.pnl_pct == 0.02
        assert trade.confidence == 0.85

    def test_create_losing_trade(self):
        """Test creating a losing trade entry"""
        trade = TradeJournalEntry(
            trade_id="trade_002",
            symbol="ETHUSDT",
            side="SHORT",
            entry_time=datetime.utcnow(),
            exit_time=datetime.utcnow() + timedelta(minutes=30),
            entry_price=3000.0,
            exit_price=3050.0,
            position_size=1.0,
            entry_reason="support_confluence",
            exit_reason=ExitReason.STOP_LOSS,
            pnl=-150.0,
            pnl_pct=-0.05,
            max_profit=50.0,
            max_loss=150.0,
            market_regime="choppy",
            volatility_percentile=25,
            spread_avg=2.5,
            funding_rate=-0.0002,
            leverage=2.0,
            ai_model="gpt-4",
            confidence=0.65,
            decision_json={"logic": "support"},
            is_winner=False,
            is_breakeven=False,
            prompt_pack_version="v1.0",
            trace_id="trace_002"
        )

        assert trade.is_winner is False
        assert trade.pnl < 0
        assert trade.exit_reason == ExitReason.STOP_LOSS


class TestLearningAgent:
    """Test learning agent analysis"""

    def create_sample_trades(self, count: int = 10):
        """Create sample trades for testing"""
        trades = []
        base_time = datetime.utcnow()

        for i in range(count):
            is_winner = i % 3 != 0  # 66% win rate
            is_breakeven = False
            
            if i == 5:
                is_winner = False
                is_breakeven = False

            trade = TradeJournalEntry(
                trade_id=f"trade_{i:03d}",
                symbol="BTCUSDT",
                side="LONG" if i % 2 == 0 else "SHORT",
                entry_time=base_time + timedelta(hours=i),
                exit_time=base_time + timedelta(hours=i, minutes=30),
                entry_price=50000.0 + i * 100,
                exit_price=50000.0 + i * 100 + (500 if is_winner else -300),
                position_size=1.0,
                entry_reason="volatility_breakout",
                exit_reason=ExitReason.TAKE_PROFIT if is_winner else ExitReason.STOP_LOSS,
                pnl=500.0 if is_winner else -300.0,
                pnl_pct=0.01 if is_winner else -0.006,
                max_profit=600.0 if is_winner else 100.0,
                max_loss=100.0 if is_winner else 300.0,
                market_regime="trending_up" if i < 5 else "choppy",
                volatility_percentile=75 if i < 5 else 30,
                spread_avg=5.5,
                funding_rate=0.001,
                leverage=1.0 + (i % 3),  # 1x, 2x, 3x mix
                ai_model="claude-3",
                confidence=0.75 + (0.1 if is_winner else -0.1),
                decision_json={"logic": "breakout"},
                is_winner=is_winner,
                is_breakeven=is_breakeven,
                prompt_pack_version="v1.0",
                trace_id=f"trace_{i:03d}"
            )
            trades.append(trade)

        return trades

    def test_add_trades(self):
        """Test adding trades to agent"""
        agent = LearningAgent()
        trades = self.create_sample_trades(5)

        for trade in trades:
            agent.add_trade(trade)

        assert len(agent.trades) == 5

    def test_insufficient_trades(self):
        """Test that analysis fails with fewer than 5 trades"""
        agent = LearningAgent()
        agent.add_trade(self.create_sample_trades(1)[0])

        with pytest.raises(ValueError, match="at least 5 trades"):
            agent.analyze()

    def test_calculate_win_rate(self):
        """Test win rate calculation"""
        agent = LearningAgent()
        trades = self.create_sample_trades(10)

        for trade in trades:
            agent.add_trade(trade)

        report = agent.analyze()
        stats = report.stats

        # Should be 66% win rate (2 out of 3)
        assert 0.6 < stats.win_rate < 0.8
        assert stats.total_trades == 10

    def test_profit_factor(self):
        """Test profit factor calculation"""
        agent = LearningAgent()
        trades = self.create_sample_trades(10)

        for trade in trades:
            agent.add_trade(trade)

        report = agent.analyze()
        stats = report.stats

        # Profit factor = gross profit / gross loss
        assert stats.profit_factor > 0

    def test_max_drawdown(self):
        """Test maximum drawdown calculation"""
        agent = LearningAgent()
        trades = self.create_sample_trades(10)

        for trade in trades:
            agent.add_trade(trade)

        report = agent.analyze()
        stats = report.stats

        # Max DD should be positive (expressed as % loss from peak)
        assert stats.max_drawdown >= 0

    def test_consecutive_losses(self):
        """Test consecutive losses tracking"""
        agent = LearningAgent()

        # Create 5 consecutive losses
        base_time = datetime.utcnow()
        for i in range(5):
            trade = TradeJournalEntry(
                trade_id=f"loss_{i}",
                symbol="BTCUSDT",
                side="LONG",
                entry_time=base_time + timedelta(hours=i),
                exit_time=base_time + timedelta(hours=i, minutes=30),
                entry_price=50000.0,
                exit_price=49800.0,
                position_size=1.0,
                entry_reason="test",
                exit_reason=ExitReason.STOP_LOSS,
                pnl=-200.0,
                pnl_pct=-0.004,
                max_profit=100.0,
                max_loss=200.0,
                market_regime="choppy",
                volatility_percentile=20,
                spread_avg=5.0,
                funding_rate=0.0,
                leverage=1.0,
                ai_model="test",
                confidence=0.5,
                decision_json={},
                is_winner=False,
                is_breakeven=False,
                prompt_pack_version="v1.0",
                trace_id=f"trace_loss_{i}"
            )
            agent.add_trade(trade)

        report = agent.analyze()
        stats = report.stats

        assert stats.consecutive_losses == 5

    def test_performance_by_regime(self):
        """Test performance segmentation by market regime"""
        agent = LearningAgent()
        trades = self.create_sample_trades(12)

        for trade in trades:
            agent.add_trade(trade)

        report = agent.analyze()
        stats = report.stats

        assert "trending_up" in stats.performance_by_regime
        assert "choppy" in stats.performance_by_regime

        trending_data = stats.performance_by_regime["trending_up"]
        assert trending_data.total_trades > 0
        assert 0 <= trending_data.win_rate <= 1

    def test_performance_by_volatility(self):
        """Test performance segmentation by volatility"""
        agent = LearningAgent()
        trades = self.create_sample_trades(10)

        for trade in trades:
            agent.add_trade(trade)

        report = agent.analyze()
        stats = report.stats

        # Should have volatility buckets
        assert stats.performance_by_volatility is not None
        assert isinstance(stats.performance_by_volatility, dict)

    def test_performance_by_leverage(self):
        """Test performance segmentation by leverage"""
        agent = LearningAgent()
        trades = self.create_sample_trades(12)

        for trade in trades:
            agent.add_trade(trade)

        report = agent.analyze()
        stats = report.stats

        # Should have leverage segments
        assert stats.performance_by_leverage is not None
        assert len(stats.performance_by_leverage) > 0


class TestPatternDiscovery:
    """Test losing pattern detection"""

    def test_low_volatility_pattern(self):
        """Test detection of low volatility losses"""
        agent = LearningAgent()
        base_time = datetime.utcnow()

        # Create trades that lose in low volatility
        for i in range(5):
            trade = TradeJournalEntry(
                trade_id=f"lowvol_{i}",
                symbol="BTCUSDT",
                side="LONG",
                entry_time=base_time + timedelta(hours=i),
                exit_time=base_time + timedelta(hours=i, minutes=30),
                entry_price=50000.0,
                exit_price=49700.0,  # Loss
                position_size=1.0,
                entry_reason="range_break",
                exit_reason=ExitReason.STOP_LOSS,
                pnl=-300.0,
                pnl_pct=-0.006,
                max_profit=50.0,
                max_loss=300.0,
                market_regime="choppy",
                volatility_percentile=15,  # Low volatility
                spread_avg=5.0,
                funding_rate=0.0,
                leverage=1.0,
                ai_model="test",
                confidence=0.7,
                decision_json={},
                is_winner=False,
                is_breakeven=False,
                prompt_pack_version="v1.0",
                trace_id=f"trace_lowvol_{i}"
            )
            agent.add_trade(trade)

        # Add some winning trades to make it valid
        for i in range(5):
            trade = TradeJournalEntry(
                trade_id=f"win_{i}",
                symbol="ETHUSDT",
                side="SHORT",
                entry_time=base_time + timedelta(days=1, hours=i),
                exit_time=base_time + timedelta(days=1, hours=i, minutes=30),
                entry_price=3000.0,
                exit_price=3100.0,
                position_size=1.0,
                entry_reason="support",
                exit_reason=ExitReason.TAKE_PROFIT,
                pnl=100.0,
                pnl_pct=0.033,
                max_profit=200.0,
                max_loss=100.0,
                market_regime="trending_up",
                volatility_percentile=75,
                spread_avg=5.0,
                funding_rate=0.001,
                leverage=1.0,
                ai_model="test",
                confidence=0.8,
                decision_json={},
                is_winner=True,
                is_breakeven=False,
                prompt_pack_version="v1.0",
                trace_id=f"trace_win_{i}"
            )
            agent.add_trade(trade)

        report = agent.analyze()

        # Should detect low volatility pattern
        low_vol_patterns = [
            p for p in report.losing_patterns
            if "volatility" in p.pattern_name.lower()
        ]
        assert len(low_vol_patterns) > 0

    def test_high_leverage_pattern(self):
        """Test detection of high leverage losses"""
        agent = LearningAgent()
        base_time = datetime.utcnow()

        # Create high leverage losing trades
        for i in range(3):
            trade = TradeJournalEntry(
                trade_id=f"highlev_{i}",
                symbol="BTCUSDT",
                side="LONG",
                entry_time=base_time + timedelta(hours=i),
                exit_time=base_time + timedelta(hours=i, minutes=30),
                entry_price=50000.0,
                exit_price=49500.0,
                position_size=3.0,
                entry_reason="breakout",
                exit_reason=ExitReason.STOP_LOSS,
                pnl=-1500.0,
                pnl_pct=-0.01,
                max_profit=500.0,
                max_loss=1500.0,
                market_regime="trending_up",
                volatility_percentile=70,
                spread_avg=5.0,
                funding_rate=0.005,
                leverage=5.0,  # High leverage
                ai_model="test",
                confidence=0.6,
                decision_json={},
                is_winner=False,
                is_breakeven=False,
                prompt_pack_version="v1.0",
                trace_id=f"trace_highlev_{i}"
            )
            agent.add_trade(trade)

        # Add wins to make valid
        for i in range(7):
            trade = TradeJournalEntry(
                trade_id=f"lowlev_{i}",
                symbol="ETHUSDT",
                side="SHORT",
                entry_time=base_time + timedelta(days=1, hours=i),
                exit_time=base_time + timedelta(days=1, hours=i, minutes=30),
                entry_price=3000.0,
                exit_price=3100.0,
                position_size=1.0,
                entry_reason="support",
                exit_reason=ExitReason.TAKE_PROFIT,
                pnl=100.0,
                pnl_pct=0.033,
                max_profit=200.0,
                max_loss=100.0,
                market_regime="choppy",
                volatility_percentile=30,
                spread_avg=5.0,
                funding_rate=0.0,
                leverage=1.0,
                ai_model="test",
                confidence=0.8,
                decision_json={},
                is_winner=True,
                is_breakeven=False,
                prompt_pack_version="v1.0",
                trace_id=f"trace_lowlev_{i}"
            )
            agent.add_trade(trade)

        report = agent.analyze()

        # Should detect high leverage pattern
        leverage_patterns = [
            p for p in report.losing_patterns
            if "leverage" in p.pattern_name.lower()
        ]
        assert len(leverage_patterns) > 0


class TestAutoAdaptations:
    """Test auto-adapt constraint safety"""

    def test_size_multiplier_constraints(self):
        """Test that size multiplier respects ±20% constraint"""
        agent = LearningAgent()
        trades = self.create_losing_trades_for_agent(agent)

        report = agent.analyze()

        if report.suggested_adaptations.enabled:
            multiplier = report.suggested_adaptations.size_multiplier
            assert abs(multiplier - 1.0) <= 0.20, "Size multiplier must be within ±20%"

    def test_confidence_scaling_constraints(self):
        """Test that confidence scaling respects ±20% constraint"""
        agent = LearningAgent()
        trades = self.create_losing_trades_for_agent(agent)

        report = agent.analyze()

        if report.suggested_adaptations.enabled:
            scaling = report.suggested_adaptations.confidence_scaling
            assert abs(scaling - 1.0) <= 0.20, "Confidence scaling must be within ±20%"

    def test_three_variable_constraint(self):
        """Test that only 3 variables can be adapted"""
        agent = LearningAgent()
        trades = self.create_losing_trades_for_agent(agent)

        report = agent.analyze()

        adaptations = report.suggested_adaptations

        # Verify only these 3 can change
        assert hasattr(adaptations, 'size_multiplier')
        assert hasattr(adaptations, 'confidence_scaling')
        assert hasattr(adaptations, 'cooldown_after_loss_minutes')

        # Verify no other fields
        assert not hasattr(adaptations, 'max_leverage')
        assert not hasattr(adaptations, 'stop_loss_pct')

    def test_apply_to_config(self):
        """Test applying adaptations to config"""
        current_config = {
            "max_position_pct": 5.0,
            "min_confidence": 0.7,
            "cooldown_after_loss_minutes": 0
        }

        adaptations = SuggestedAdaptations(
            size_multiplier=1.1,
            size_multiplier_reason="winning trades need more size",
            confidence_scaling=0.95,
            confidence_scaling_reason="lower confidence improved win rate",
            cooldown_after_loss_minutes=5
        )

        new_config = adaptations.apply_to_config(current_config)

        assert new_config["max_position_pct"] == pytest.approx(5.5, rel=0.01)
        assert new_config["min_confidence"] == pytest.approx(0.665, rel=0.01)
        assert new_config["cooldown_after_loss_minutes"] == 5

    def test_audit_trail(self):
        """Test that audit trail is generated"""
        adaptations = SuggestedAdaptations(
            size_multiplier=1.15,
            size_multiplier_reason="increase winning trade size",
            confidence_scaling=0.9,
            confidence_scaling_reason="reduce false signals",
            cooldown_after_loss_minutes=10
        )

        audit = adaptations.to_dict()

        assert "size_multiplier" in audit
        assert "size_multiplier_reason" in audit
        assert adaptations.size_multiplier == 1.15

    @staticmethod
    def create_losing_trades_for_agent(agent: LearningAgent):
        """Helper to create trades with some losing pattern"""
        base_time = datetime.utcnow()

        # Create mix of wins and losses
        for i in range(12):
            is_winner = i < 8  # 67% win rate

            trade = TradeJournalEntry(
                trade_id=f"adapt_test_{i}",
                symbol="BTCUSDT",
                side="LONG",
                entry_time=base_time + timedelta(hours=i),
                exit_time=base_time + timedelta(hours=i, minutes=30),
                entry_price=50000.0,
                exit_price=50500.0 if is_winner else 49700.0,
                position_size=1.0,
                entry_reason="test",
                exit_reason=ExitReason.TAKE_PROFIT if is_winner else ExitReason.STOP_LOSS,
                pnl=500.0 if is_winner else -300.0,
                pnl_pct=0.01 if is_winner else -0.006,
                max_profit=600.0 if is_winner else 100.0,
                max_loss=100.0 if is_winner else 300.0,
                market_regime="trending_up",
                volatility_percentile=70,
                spread_avg=5.0,
                funding_rate=0.001,
                leverage=1.0,
                ai_model="test",
                confidence=0.75,
                decision_json={},
                is_winner=is_winner,
                is_breakeven=False,
                prompt_pack_version="v1.0",
                trace_id=f"trace_adapt_{i}"
            )
            agent.add_trade(trade)

        return agent.trades


class TestLearningReport:
    """Test learning report generation and serialization"""

    def test_report_dict_serialization(self):
        """Test converting report to dict"""
        agent = LearningAgent()

        # Add trades
        base_time = datetime.utcnow()
        for i in range(7):
            trade = TradeJournalEntry(
                trade_id=f"ser_{i}",
                symbol="BTCUSDT",
                side="LONG",
                entry_time=base_time + timedelta(hours=i),
                exit_time=base_time + timedelta(hours=i, minutes=30),
                entry_price=50000.0,
                exit_price=50400.0 if i % 2 == 0 else 49800.0,
                position_size=1.0,
                entry_reason="test",
                exit_reason=ExitReason.TAKE_PROFIT if i % 2 == 0 else ExitReason.STOP_LOSS,
                pnl=400.0 if i % 2 == 0 else -200.0,
                pnl_pct=0.008 if i % 2 == 0 else -0.004,
                max_profit=500.0,
                max_loss=200.0,
                market_regime="trending_up",
                volatility_percentile=70,
                spread_avg=5.0,
                funding_rate=0.001,
                leverage=1.0,
                ai_model="test",
                confidence=0.8,
                decision_json={},
                is_winner=i % 2 == 0,
                is_breakeven=False,
                prompt_pack_version="v1.0",
                trace_id=f"trace_ser_{i}"
            )
            agent.add_trade(trade)

        report = agent.analyze()
        report_dict = report.to_dict()

        assert "analysis_time" in report_dict
        assert "trades_analyzed" in report_dict
        assert "stats" in report_dict
        assert "losing_patterns" in report_dict
        assert "recommendations" in report_dict

    def test_report_json_serialization(self):
        """Test converting report to JSON string"""
        agent = LearningAgent()

        # Add trades
        base_time = datetime.utcnow()
        for i in range(6):
            trade = TradeJournalEntry(
                trade_id=f"json_{i}",
                symbol="BTCUSDT",
                side="LONG",
                entry_time=base_time + timedelta(hours=i),
                exit_time=base_time + timedelta(hours=i, minutes=30),
                entry_price=50000.0,
                exit_price=50400.0 if i < 4 else 49900.0,
                position_size=1.0,
                entry_reason="test",
                exit_reason=ExitReason.TAKE_PROFIT if i < 4 else ExitReason.STOP_LOSS,
                pnl=400.0 if i < 4 else -100.0,
                pnl_pct=0.008 if i < 4 else -0.002,
                max_profit=500.0,
                max_loss=200.0,
                market_regime="trending_up",
                volatility_percentile=70,
                spread_avg=5.0,
                funding_rate=0.001,
                leverage=1.0,
                ai_model="test",
                confidence=0.8,
                decision_json={},
                is_winner=i < 4,
                is_breakeven=False,
                prompt_pack_version="v1.0",
                trace_id=f"trace_json_{i}"
            )
            agent.add_trade(trade)

        report = agent.analyze()
        report_json = report.to_json()

        assert isinstance(report_json, str)
        assert "analysis_time" in report_json
        assert "stats" in report_json


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
