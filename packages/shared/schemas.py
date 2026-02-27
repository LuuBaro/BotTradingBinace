"""
Pydantic schemas for data validation and serialization
"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator
from packages.shared.enums import (
    MarketRegime,
    ActionType,
    Side,
    OrderType,
    OrderStatus,
    RiskResult,
)


class ChecklistItem(BaseModel):
    """Single checklist item in a decision"""

    condition: str
    pass_: bool = Field(alias="pass")

    class Config:
        populate_by_name = True


class Decision(BaseModel):
    """AI Trading decision schema"""

    regime: MarketRegime
    action: ActionType
    symbol: str
    side: Side | None = None
    entry_type: OrderType = OrderType.MARKET
    entry_price: float | None = None
    size_pct: float = Field(gt=0, le=1.0, description="Position size as % of balance")
    leverage: int = Field(ge=1, le=125)
    stop_loss: float | None = None
    take_profit: float | None = None
    confidence: float = Field(ge=0, le=1.0)
    rationale: str
    checklist: list[ChecklistItem] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format"""
        return v.upper()

    @field_validator("stop_loss", "take_profit")
    @classmethod
    def validate_prices(cls, v: float | None) -> float | None:
        """Validate price is positive"""
        if v is not None and v <= 0:
            raise ValueError("Price must be positive")
        return v


class RiskConfig(BaseModel):
    """Risk management configuration"""

    max_drawdown_day_pct: float = Field(
        default=0.05, description="Max daily drawdown as % of balance"
    )
    max_position_pct: float = Field(
        default=0.3, description="Max position size as % of balance"
    )
    max_leverage: int = Field(default=5, description="Maximum leverage allowed")
    max_risk_per_trade_pct: float = Field(
        default=0.02, description="Max risk per trade as % of balance"
    )
    max_orders_per_hour: int = Field(default=10, description="Max orders per hour")
    max_concurrent_positions: int = Field(default=3, description="Max concurrent positions")
    cooldown_after_loss: int = Field(
        default=300, description="Cooldown seconds after a loss"
    )
    mandatory_sl_tp: bool = Field(default=True, description="Require SL/TP on all trades")

    @field_validator(
        "max_drawdown_day_pct",
        "max_position_pct",
        "max_risk_per_trade_pct",
    )
    @classmethod
    def validate_pct(cls, v: float) -> float:
        """Ensure percentage is decimal (e.g. 0.1 rather than 10)"""
        if v > 1.0:
            # If user provides 10.0 meaning 10%, convert to 0.1
            return v / 100.0
        return v



class RiskValidationResult(BaseModel):
    """Result of risk engine validation"""

    approved: bool
    result: RiskResult
    reason: str
    modified_decision: Decision | None = None


class MarketSnapshot(BaseModel):
    """Market data snapshot"""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread: float | None = None
    mark_price: float | None = None
    funding_rate: float | None = None


class OrderIntent(BaseModel):
    """Order intent before execution"""

    trace_id: str
    client_order_id: str
    symbol: str
    side: Side
    order_type: OrderType
    quantity: float
    price: float | None = None
    stop_price: float | None = None
    decision_json: dict[str, Any]


class Position(BaseModel):
    """Current position"""

    symbol: str
    side: Side
    quantity: float
    entry_price: float
    unrealized_pnl: float = 0.0
    sl_order_id: str | None = None
    tp_order_id: str | None = None
    opened_at: datetime


class Event(BaseModel):
    """System event"""

    timestamp: datetime
    level: str
    code: str
    message: str
    trace_id: str | None = None
    data: dict[str, Any] | None = None
