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
    UniqueConstraint
)
import uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models"""

    pass


class User(Base):
    """Real user accounts for SaaS model"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="trader")  # admin, trader, viewer
    
    # Security & Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_whitelisted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Phase 8: Session Management for 24h token expiry handling
    bot_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_session_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_session_refresh_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    session_expiry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    auto_close_on_logout: Mapped[bool] = mapped_column(Boolean, default=True)
    grace_period_minutes: Mapped[int] = mapped_column(Integer, default=15)
    graceful_exit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_bot_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bot_paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bot_pause_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Metadata
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_session_expiry", "session_expiry_at"),
        Index("ix_last_activity", "last_bot_activity_at"),
    )


class UserLoginLog(Base):
    """Detailed logs for user logins (IP, Geo, OS, Browser)"""

    __tablename__ = "user_login_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Parsed Client Data
    os: Mapped[str | None] = mapped_column(String(50), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(50), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # mobile, tablet, desktop
    
    # Geo Data
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class SystemNotification(Base):
    """Global or targeted notifications sent by Admin/Web Mẹ"""

    __tablename__ = "system_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_user_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id"), nullable=True, index=True) # NULL means global
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="info")  # info, warning, error, success
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


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
    approval_mode: Mapped[bool] = mapped_column(Boolean, default=False)  # If True, requires manual approval for trades
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)
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
    
    # Approval tracking
    approved_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)


class Signal(Base):
    """AI potential trading signals (Watchlist)"""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_zone: Mapped[str] = mapped_column(String(50), nullable=False)  # "65000-65200"
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE, TRIGGERED, EXPIRED, CANCELLED
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)



class RiskLog(Base):
    """Risk engine validation logs"""

    __tablename__ = "risk_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False)  # approved|rejected|modified
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OrderIntent(Base):
    """Order intent before execution (idempotency tracking)"""

    __tablename__ = "order_intents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    client_order_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending|executed|failed
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)
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
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)
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
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)
    
    # Stop-loss and Take-profit order IDs
    sl_order_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tp_order_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    
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
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)
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
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)
    data_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AuditLog(Base):
    """Audit trail for critical actions"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)  # system|user|api
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class LearningReport(Base):
    """Learning agent analysis reports"""

    __tablename__ = "learning_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    analysis_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)
    recommendations_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class TraderContext(Base):
    """Historical context imported from human traders"""

    __tablename__ = "trader_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    trader_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[str] = mapped_column(String(50), default="admin", index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)


class NewsSource(Base):
    """Custom intelligence sources (RSS, Telegram, Web)"""

    __tablename__ = "news_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # rss|telegram|web
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NewsLog(Base):
    """Scraped news content for AI analysis"""

    __tablename__ = "news_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_sources.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
class ChatMessage(Base):
    """Dialogue history between user and AI agent"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user|assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True) # Unified field name

class UserCredential(Base):
    """Encrypted per-user credentials and custom AI settings"""

    __tablename__ = "user_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), unique=True, index=True)
    
    # Binance (Encrypted)
    binance_api_key: Mapped[str | None] = mapped_column(Text, nullable=True) # AES-256 Encrypted
    binance_api_secret: Mapped[str | None] = mapped_column(Text, nullable=True) # AES-256 Encrypted
    use_testnet: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Encryption Metadata
    encryption_version: Mapped[int] = mapped_column(Integer, default=1)
    key_v: Mapped[str | None] = mapped_column(String(50), nullable=True) # Key version or hint
    
    # AI / LLM Preference
    ai_provider: Mapped[str] = mapped_column(String(20), default="openai")  # openai, anthropic, gemini, manual
    ai_api_key: Mapped[str | None] = mapped_column(Text, nullable=True) # Encrypted
    ai_model: Mapped[str] = mapped_column(String(50), default="gpt-4")
    ai_custom_endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SessionLog(Base):
    """Session tracking for 24h token expiry management"""

    __tablename__ = "session_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), index=True, nullable=False)
    session_token: Mapped[str] = mapped_column(String(500), nullable=False)
    login_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    logout_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)  # ACTIVE, EXPIRED, CLOSED
    positions_at_logout: Mapped[int] = mapped_column(Integer, default=0)
    action_taken: Mapped[str | None] = mapped_column(String(50), nullable=True)  # GRACEFUL_CLOSE, FORCE_CLOSE, PAUSE
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_session_user_status", "user_id", "status"),
    )


class QuotaLog(Base):
    """Track API quota usage per user per provider"""

    __tablename__ = "quota_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # openai, anthropic, gemini, groq
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)  # decision, analysis, recommendation
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        Index("ix_quota_user_provider", "user_id", "provider"),
    )


class RecommendationApprovalLog(Base):
    """Track Learning Agent recommendations and approvals"""

    __tablename__ = "recommendation_approval_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), index=True, nullable=False)
    recommendation_type: Mapped[str] = mapped_column(String(100), nullable=False)  # reduce_position_size, increase_leverage, etc
    safety_category: Mapped[str] = mapped_column(String(20), nullable=False)  # SAFE, MODERATE, RISKY
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    previous_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    current_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)  # PENDING, APPROVED, APPLIED, REJECTED
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_recommend_user_status", "user_id", "status"),
    )
