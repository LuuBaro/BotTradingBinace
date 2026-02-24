"""
AI Decision Schema - AI output with validation
Includes confidence, rationale, checklist results
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime
import json


class DecisionStatus(str, Enum):
    """Decision status in pipeline"""
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class DecisionType(str, Enum):
    """Type of decision"""
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    MODIFY = "MODIFY"
    NO_TRADE = "NO_TRADE"


class ChecklistResult(BaseModel):
    """Result of one checklist item"""
    name: str = Field(..., description="Checklist item name")
    passed: bool = Field(..., description="Did it pass?")
    reason: str = Field(default="", description="Why passed/failed")

    class Config:
        schema_extra = {
            "example": {
                "name": "Position size check",
                "passed": True,
                "reason": "Position size 3.5% < max 5%"
            }
        }


class OrderSpecification(BaseModel):
    """Order specification from AI decision"""
    symbol: str = Field(..., description="Trading pair (e.g., 'ETHUSDT')")
    side: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., gt=0, description="Order quantity")
    entry_price: float = Field(..., gt=0, description="Entry price")
    stop_loss_price: float = Field(..., gt=0, description="Stop loss price")
    take_profit_prices: List[float] = Field(
        default=[],
        description="List of take profit prices (for partial closes)"
    )
    leverage: float = Field(default=1.0, ge=1.0, description="Leverage for margin trading")
    time_in_force: str = Field(default="GTC", description="Time in force (GTC, IOC, FOK)")
    order_type: str = Field(default="LIMIT", description="Order type (LIMIT, MARKET)")
    use_trailing_stop: bool = Field(default=False, description="Use trailing stop")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "ETHUSDT",
                "side": "BUY",
                "quantity": 10.0,
                "entry_price": 2500.0,
                "stop_loss_price": 2450.0,
                "take_profit_prices": [2550.0, 2600.0],
                "leverage": 5.0,
                "use_trailing_stop": True
            }
        }


class AIDecisionOutput(BaseModel):
    """Output schema for AI decision (what AI returns)"""
    decision_type: DecisionType = Field(
        ...,
        description="Type of decision"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI confidence in this decision (0.0-1.0)"
    )
    rationale: str = Field(
        ...,
        description="Detailed explanation of why this decision was made"
    )
    market_regime: str = Field(
        ...,
        description="Current identified market regime"
    )
    timeframe_analysis: Dict[str, str] = Field(
        default={},
        description="Analysis at each timeframe"
    )
    order_spec: Optional[OrderSpecification] = Field(
        default=None,
        description="Order specification if trading"
    )
    checklist_results: List[ChecklistResult] = Field(
        default=[],
        description="Results of pre-trade checklist"
    )
    risk_assessment: Dict[str, Any] = Field(
        default={},
        description="Risk assessment details"
    )
    next_review_time: Optional[datetime] = Field(
        default=None,
        description="When to review this decision (if no-trade)"
    )

    class Config:
        schema_extra = {
            "example": {
                "decision_type": "ENTRY",
                "confidence": 0.85,
                "rationale": "Price broke above EMA20 in strong uptrend with volume confirmation",
                "market_regime": "Trending Up",
                "timeframe_analysis": {
                    "15m": "Entry signal on pullback",
                    "1h": "Strong uptrend",
                    "4h": "Higher low pattern"
                },
                "order_spec": {
                    "symbol": "ETHUSDT",
                    "side": "BUY",
                    "quantity": 10.0,
                    "entry_price": 2500.0,
                    "stop_loss_price": 2450.0,
                    "take_profit_prices": [2550.0, 2600.0]
                },
                "checklist_results": [
                    {"name": "Position size check", "passed": True},
                    {"name": "Risk ratio check", "passed": True}
                ],
                "risk_assessment": {
                    "risk_reward_ratio": 2.5,
                    "position_pct": 3.5,
                    "daily_loss_pct": 0.8
                }
            }
        }

    @validator('confidence')
    def validate_confidence(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    def to_json(self) -> str:
        """Serialize to JSON"""
        return self.json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "AIDecisionOutput":
        """Deserialize from JSON"""
        return cls.parse_raw(json_str)


class DecisionValidationError(BaseModel):
    """Validation error details"""
    field: str = Field(..., description="Field with error")
    error: str = Field(..., description="Error message")
    value: Optional[Any] = Field(default=None, description="Invalid value")

    class Config:
        schema_extra = {
            "example": {
                "field": "confidence",
                "error": "Confidence must be between 0.0 and 1.0",
                "value": 1.5
            }
        }


class DecisionValidationResult(BaseModel):
    """Result of decision validation"""
    valid: bool = Field(..., description="Is decision valid?")
    errors: List[DecisionValidationError] = Field(
        default=[],
        description="Validation errors"
    )

    class Config:
        schema_extra = {
            "example": {
                "valid": False,
                "errors": [
                    {
                        "field": "confidence",
                        "error": "Confidence must be between 0.0 and 1.0",
                        "value": 1.5
                    }
                ]
            }
        }


class RiskApprovalRequest(BaseModel):
    """Request for risk module to approve decision"""
    decision_json: Dict[str, Any] = Field(
        ...,
        description="AI decision output"
    )
    current_position: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Current position if exists"
    )

    class Config:
        schema_extra = {
            "example": {
                "decision_json": {
                    "decision_type": "ENTRY",
                    "confidence": 0.85,
                    "order_spec": {
                        "symbol": "ETHUSDT",
                        "side": "BUY",
                        "quantity": 10.0,
                        "entry_price": 2500.0,
                        "stop_loss_price": 2450.0,
                        "take_profit_prices": [2550.0, 2600.0]
                    }
                }
            }
        }


class RiskApprovalResponse(BaseModel):
    """Risk approval decision"""
    approved: bool = Field(..., description="Is decision approved by risk module?")
    risk_passed: bool = Field(..., description="Did it pass all risk checks?")
    reason: str = Field(default="", description="Why approved/rejected")
    modifications: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Modified values (e.g., reduced position size)"
    )

    class Config:
        schema_extra = {
            "example": {
                "approved": True,
                "risk_passed": True,
                "reason": "All risk checks passed"
            }
        }
