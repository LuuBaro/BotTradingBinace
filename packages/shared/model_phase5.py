"""
Phase 5 Database Models - PromptPack versioning and AI Decision storage
"""
from sqlalchemy import Column, String, Integer, JSON, DateTime, Boolean, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class PromptPack(Base):
    """Versioned prompt packs provided by traders"""
    __tablename__ = "prompt_packs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    # Prompt pack content (full schema as JSON)
    config = Column(JSON, nullable=False)

    # Metadata
    created_by = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Version tracking
    parent_pack_id = Column(String(36), ForeignKey("prompt_packs.id"), nullable=True)
    parent_pack = relationship("PromptPack", remote_side=[id], foreign_keys=[parent_pack_id])

    # Symbols this pack applies to (stored as JSON array)
    symbols = Column(JSON, nullable=False, default=[])

    # Use this pack for these symbols
    is_default = Column(Boolean, nullable=False, default=False)

    # Relationships
    decisions = relationship("AIDecision", back_populates="prompt_pack")

    __table_args__ = (
        UniqueConstraint('name', 'version', name='uq_pack_name_version'),
    )

    def __repr__(self):
        return f"<PromptPack {self.name} v{self.version} ({'active' if self.active else 'inactive'})>"


class AIDecision(Base):
    """AI trading decisions with full pipeline tracking"""
    __tablename__ = "ai_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id = Column(String(100), nullable=False, unique=True, index=True)

    # Reference to prompt pack used
    prompt_pack_id = Column(String(36), ForeignKey("prompt_packs.id"), nullable=False, index=True)
    prompt_pack = relationship("PromptPack", back_populates="decisions")

    # Decision details
    decision_type = Column(String(20), nullable=False)  # ENTRY, EXIT, MODIFY, NO_TRADE
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, VALIDATED, APPROVED, REJECTED, EXECUTED, FAILED

    # AI output
    confidence = Column(Float, nullable=False)
    rationale = Column(Text, nullable=False)
    market_regime = Column(String(100), nullable=True)

    # Full decision JSON from AI (all details)
    decision_json = Column(JSON, nullable=False)

    # Timeframe analysis
    timeframe_analysis = Column(JSON, nullable=True)

    # Order specification if applicable
    order_spec = Column(JSON, nullable=True)

    # Checklist results
    checklist_results = Column(JSON, nullable=True, default=[])

    # Risk assessment
    risk_assessment = Column(JSON, nullable=True)

    # Current market snapshot used for decision
    market_snapshot = Column(JSON, nullable=True)

    # Current positions at decision time
    current_positions = Column(JSON, nullable=True, default=[])

    # Risk approval details
    risk_passed = Column(Boolean, nullable=True)
    risk_approval_reason = Column(Text, nullable=True)
    risk_modifications = Column(JSON, nullable=True)

    # Execution tracking
    order_id = Column(String(100), nullable=True, index=True)
    position_id = Column(String(100), nullable=True, index=True)
    execution_price = Column(Float, nullable=True)
    execution_status = Column(String(50), nullable=True)
    execution_error = Column(Text, nullable=True)

    # Validation status
    is_valid_json = Column(Boolean, nullable=False, default=False)
    validation_errors = Column(JSON, nullable=True, default=[])

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AIDecision {self.trace_id} {self.decision_type} ({self.status})>"


class DecisionEvent(Base):
    """Events in decision pipeline (PENDING→VALIDATED→APPROVED→EXECUTED)"""
    __tablename__ = "decision_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id = Column(String(100), nullable=False, index=True)
    
    # Reference to decision
    decision_id = Column(String(36), ForeignKey("ai_decisions.id"), nullable=False, index=True)

    # Event details
    event_type = Column(String(50), nullable=False)  # AI_GENERATED, VALIDATION_PASSED, RISK_APPROVED, RISK_REJECTED, EXECUTED, ERROR
    status = Column(String(20), nullable=False)  # SUCCESS, FAILED, REJECTED
    message = Column(Text, nullable=False)

    # Additional context
    context = Column(JSON, nullable=True)

    # Created at
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<DecisionEvent {self.trace_id} {self.event_type}>"


class AIMetrics(Base):
    """Track AI performance metrics"""
    __tablename__ = "ai_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Decision statistics
    total_decisions = Column(Integer, nullable=False, default=0)
    valid_decisions = Column(Integer, nullable=False, default=0)
    invalid_decisions = Column(Integer, nullable=False, default=0)
    risk_approved = Column(Integer, nullable=False, default=0)
    risk_rejected = Column(Integer, nullable=False, default=0)
    executed = Column(Integer, nullable=False, default=0)

    # Performance
    avg_confidence = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    total_pnl = Column(Float, nullable=True)

    # Errors
    json_parse_errors = Column(Integer, nullable=False, default=0)
    validation_errors = Column(Integer, nullable=False, default=0)
    llm_errors = Column(Integer, nullable=False, default=0)

    # Time-based metrics
    avg_decision_time_ms = Column(Float, nullable=True)
    avg_llm_response_time_ms = Column(Float, nullable=True)

    # Model info
    model = Column(String(100), nullable=False)
    prompt_pack_id = Column(String(36), nullable=True)

    # Timestamp
    date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AIMetrics {self.model} - decisions: {self.total_decisions}>"
