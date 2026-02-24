"""
SQLAlchemy async database models for AI Trading Bot
"""
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    JSON,
    Index,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models"""

    pass


class BotConfig(Base):
    """Bot configuration with versioning"""

    __tablename__ = "bot_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    env: Mapped[str] = mapped_column(String(10), nullable=False)  # demo|live
    symbols_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    risk_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    execution_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    active_prompt_pack_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_bot_config_is_active", "is_active"),)


class PromptPack(Base):
    """LLM prompt templates with versioning"""

    __tablename__ = "prompt_packs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketSnapshot(Base):
    """Market data snapshot"""

    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    data_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    __table_args__ = (Index("ix_market_snapshots_symbol_timestamp", "symbol", "timestamp"),)


class Decision(Base):
    """AI trading decisions"""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, unique=True)
    decision_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    regime: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Phase 5: AI enhancement fields
    decision_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ENTRY, EXIT, MODIFY, NO_TRADE
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING, VALIDATED, APPROVED, REJECTED, EXECUTED
    prompt_pack_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeframe_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    checklist_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    risk_assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    order_spec: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    market_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    current_positions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Risk approval tracking
    risk_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    risk_approval_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_modifications: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Execution tracking
    order_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    position_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    execution_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    execution_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Validation
    is_valid_json: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class RiskLog(Base):
    """Risk engine validation logs"""

    __tablename__ = "risk_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False)  # approved|rejected|modified
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OrderIntent(Base):
    """Order intent before execution (idempotency tracking)"""

    __tablename__ = "order_intents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    client_order_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending|executed|failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Order(Base):
    """Exchange orders"""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_order_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    exchange_order_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    filled_qty: Mapped[float] = mapped_column(Float, default=0.0)
    avg_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Position(Base):
    """Current positions"""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Stop-loss and Take-profit order IDs
    sl_order_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tp_order_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Binance-specific fields (Phase 2+)
    leverage: Mapped[int] = mapped_column(Integer, default=1)
    margin_type: Mapped[str] = mapped_column(String(10), default="CROSSED")  # CROSSED or ISOLATED
    liquidation_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class TradeJournal(Base):
    """Closed trades for analysis"""

    __tablename__ = "trade_journal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float] = mapped_column(Float, nullable=False)
    pnl: Mapped[float] = mapped_column(Float, nullable=False)
    rr: Mapped[float | None] = mapped_column(Float, nullable=True)  # risk-reward ratio
    holding_time: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds
    regime: Mapped[str] = mapped_column(String(20), nullable=False)
    features_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decision_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    exit_reason: Mapped[str] = mapped_column(String(50), nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Event(Base):
    """System events log"""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    data_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AuditLog(Base):
    """Audit trail for critical actions"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)  # system|user|api
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class LearningReport(Base):
    """Learning agent analysis reports"""

    __tablename__ = "learning_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    analysis_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendations_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
