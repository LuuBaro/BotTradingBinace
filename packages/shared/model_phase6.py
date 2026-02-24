"""
Phase 6 Database Models - Trade journal and learning reports
"""
from sqlalchemy import Column, String, Integer, JSON, DateTime, Boolean, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TradeJournal(Base):
    """Record of every closed trade for analysis"""
    __tablename__ = "trade_journal"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id = Column(String(100), unique=True, index=True, nullable=False)
    trade_id = Column(String(100), unique=True, index=True, nullable=False)

    # Trade info
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # LONG or SHORT
    entry_time = Column(DateTime, nullable=False, index=True)
    exit_time = Column(DateTime, nullable=False)

    # Entry/Exit details
    entry_price = Column(Float, nullable=False)
    entry_quantity = Column(Float, nullable=False)
    entry_leverage = Column(Float, nullable=False, default=1.0)
    exit_price = Column(Float, nullable=False)
    exit_reason = Column(String(20), nullable=False)  # TAKE_PROFIT, STOP_LOSS, MANUAL, etc.

    # PnL
    pnl = Column(Float, nullable=False)
    pnl_pct = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)

    # Risk metrics
    risk_reward_ratio = Column(Float, nullable=False)
    holding_time_minutes = Column(Integer, nullable=False)
    max_drawdown = Column(Float, nullable=False)
    max_runup = Column(Float, nullable=False)

    # Market conditions
    market_regime = Column(String(100), nullable=False)
    volatility_percentile = Column(Integer, default=50)
    bid_ask_spread_pips = Column(Float, default=0.0)
    funding_rate = Column(Float, default=0.0)

    # Risk metrics
    position_pct = Column(Float, nullable=False)
    stop_loss_pips = Column(Float, nullable=False)
    take_profit_pips = Column(Float, nullable=False)

    # Decision info
    decision_json = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False)
    ai_model = Column(String(100), nullable=False)
    prompt_pack_version = Column(Integer, nullable=False)

    # Classification
    is_winner = Column(Boolean, nullable=False)
    is_breakeven = Column(Boolean, default=False)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<TradeJournal {self.trade_id} {self.symbol} {self.side}>"


class LearningReport(Base):
    """AI learning analysis report"""
    __tablename__ = "learning_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Metadata
    analysis_time = Column(DateTime, nullable=False, index=True)
    trades_analyzed = Column(Integer, nullable=False)

    # Analysis results (full JSON)
    stats_json = Column(JSON, nullable=True)
    losing_patterns_json = Column(JSON, nullable=True)
    confidence_calibration_json = Column(JSON, nullable=True)
    recommendations_json = Column(JSON, nullable=True)

    # Suggested adaptations (auditable)
    suggested_adaptations_json = Column(JSON, nullable=True)
    adaptations_enabled = Column(Boolean, default=False)

    # If empty/error
    error_message = Column(Text, nullable=True)

    # For filtering
    period_start = Column(DateTime, nullable=True, index=True)
    period_end = Column(DateTime, nullable=True)
    trigger = Column(String(50), default="daily")  # daily, 50trades, manual

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<LearningReport {self.analysis_time.date()} {self.trades_analyzed} trades>"


class AutoAdaptHistory(Base):
    """Audit trail of auto-adapt changes"""
    __tablename__ = "auto_adapt_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Reference to learning report that triggered it
    learning_report_id = Column(String(36), ForeignKey("learning_reports.id"), nullable=False, index=True)

    # What was changed
    size_multiplier_old = Column(Float, nullable=True)
    size_multiplier_new = Column(Float, nullable=True)
    size_multiplier_enabled = Column(Boolean, default=False)

    confidence_scaling_old = Column(Float, nullable=True)
    confidence_scaling_new = Column(Float, nullable=True)
    confidence_scaling_enabled = Column(Boolean, default=False)

    cooldown_old = Column(Integer, nullable=True)
    cooldown_new = Column(Integer, nullable=True)
    cooldown_enabled = Column(Boolean, default=False)

    # Why (from learning report)
    reason = Column(Text, nullable=False)

    # Reverse operation (if rolled back)
    rolled_back = Column(Boolean, default=False)
    rolled_back_at = Column(DateTime, nullable=True)
    rollback_reason = Column(Text, nullable=True)

    # Timestamps
    applied_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<AutoAdaptHistory {self.id[:8]} applied {self.applied_at.date()}>"


class LearningMetrics(Base):
    """Aggregated learning metrics for trending"""
    __tablename__ = "learning_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Time period
    analysis_date = Column(DateTime, nullable=False, unique=True, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Key metrics
    total_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    profit_factor = Column(Float, nullable=False)
    total_pnl = Column(Float, nullable=False)
    max_drawdown = Column(Float, nullable=False)

    # Adaptations
    adaptations_applied = Column(Boolean, default=False)
    adaptation_changes = Column(JSON, nullable=True)

    # Patterns discovered
    pattern_count = Column(Integer, default=0)
    top_patterns = Column(JSON, nullable=True)

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<LearningMetrics {self.analysis_date.date()} WR={self.win_rate:.1%}>"
