"""
PromptPack Schema - Standardized configuration for trader-defined trading rules
Enables trader to define regimes, playbooks, no-trade conditions, and checklists
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
import json


class TimeFrame(str, Enum):
    """Supported timeframes"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"


class Side(str, Enum):
    """Trade side"""
    LONG = "LONG"
    SHORT = "SHORT"


class RegimeDefinition(BaseModel):
    """Define market regime"""
    name: str = Field(..., description="Regime name (e.g., 'Trending Up', 'Range Bound')")
    indicators: Dict[str, Any] = Field(
        ...,
        description="Indicator conditions (e.g., {'RSI': '>50', 'MACD': 'positive'})"
    )
    description: str = Field(default="", description="Regime description")

    class Config:
        schema_extra = {
            "example": {
                "name": "Trending Up",
                "indicators": {
                    "RSI": ">50",
                    "MACD": "positive",
                    "EMA_20_above_EMA_50": True
                },
                "description": "Strong uptrend conditions"
            }
        }


class EntryPlaybook(BaseModel):
    """Define entry conditions for a specific side"""
    side: Side = Field(..., description="Trade side")
    regime: str = Field(..., description="Target regime name")
    conditions: List[str] = Field(
        ...,
        description="List of entry conditions (all must be true)"
    )
    target_ratio: float = Field(
        default=2.0,
        ge=1.0,
        description="Risk/reward ratio target (e.g., 2.0 = 2:1)"
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum AI confidence required (0.0-1.0)"
    )
    description: str = Field(default="", description="Playbook description")

    class Config:
        schema_extra = {
            "example": {
                "side": "LONG",
                "regime": "Trending Up",
                "conditions": [
                    "price > EMA_20",
                    "RSI > 50",
                    "volume > 20MA volume",
                    "trend confirmation"
                ],
                "target_ratio": 2.5,
                "confidence_threshold": 0.75,
                "description": "Buy on pullback in uptrend"
            }
        }


class ExitPlaybook(BaseModel):
    """Define exit conditions"""
    side: Side = Field(..., description="Trade side to exit")
    profit_target: str = Field(
        ...,
        description="Profit target logic (e.g., 'price crosses 2xR', 'RSI >70')"
    )
    stop_loss: str = Field(
        ...,
        description="Stop loss logic (e.g., 'price breaks EMA_20', 'recent swing low')"
    )
    partial_take_profit: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Partial profit levels (e.g., [{'at': '1.5R', 'close_pct': 0.5}])"
    )
    trailing_stop: Optional[bool] = Field(
        default=False,
        description="Use trailing stop after first partial profit"
    )
    description: str = Field(default="", description="Exit strategy description")

    class Config:
        schema_extra = {
            "example": {
                "side": "LONG",
                "profit_target": "price crosses 2xR",
                "stop_loss": "price breaks recent swing low",
                "partial_take_profit": [
                    {"at": "1.5R", "close_pct": 0.5},
                    {"at": "2.5R", "close_pct": 1.0}
                ],
                "trailing_stop": True,
                "description": "Take profits in tiers, trail after first TP"
            }
        }


class NoTradeCondition(BaseModel):
    """Define when AI should NOT trade"""
    name: str = Field(..., description="Condition name")
    triggers: List[str] = Field(
        ...,
        description="List of triggers (if ANY true, no trading)"
    )
    duration_minutes: Optional[int] = Field(
        default=None,
        description="How long to avoid trading after trigger (minutes)"
    )

    class Config:
        schema_extra = {
            "example": {
                "name": "Pre-news black-out",
                "triggers": [
                    "is_before_us_economic_news",
                    "implied_volatility > 80th percentile",
                    "recent_system_error"
                ],
                "duration_minutes": 30
            }
        }


class ChecklistItem(BaseModel):
    """Pre-trade checklist item for AI to verify"""
    name: str = Field(..., description="Checklist item name")
    description: str = Field(default="", description="What to check")
    required: bool = Field(default=True, description="Must pass to trade")

    class Config:
        schema_extra = {
            "example": {
                "name": "Position size check",
                "description": "Ensure position size < max_position_pct",
                "required": True
            }
        }


class RiskParameters(BaseModel):
    """Risk configuration baked into prompt pack"""
    max_position_pct: float = Field(
        default=5.0,
        ge=0.1,
        le=100.0,
        description="Max position size as % of account"
    )
    max_leverage: float = Field(
        default=10.0,
        ge=1.0,
        description="Max allowable leverage"
    )
    min_risk_ratio: float = Field(
        default=1.0,
        ge=0.1,
        description="Minimum risk:reward ratio"
    )
    max_daily_loss_pct: float = Field(
        default=2.0,
        ge=0.1,
        description="Stop trading if daily loss exceeds this %"
    )
    max_concurrent_positions: int = Field(
        default=3,
        ge=1,
        description="Max number of open positions"
    )

    class Config:
        schema_extra = {
            "example": {
                "max_position_pct": 5.0,
                "max_leverage": 10.0,
                "min_risk_ratio": 1.5,
                "max_daily_loss_pct": 2.0,
                "max_concurrent_positions": 3
            }
        }


class PromptPackSchema(BaseModel):
    """Complete PromptPack - trader-provided configuration for AI"""
    name: str = Field(..., description="Prompt pack name")
    version: int = Field(default=1, ge=1, description="Version number")
    description: str = Field(default="", description="Pack description")
    active: bool = Field(default=True, description="Is this pack active?")
    
    # Core components
    timeframe: TimeFrame = Field(default=TimeFrame.HOUR_1, description="Primary analysis timeframe")
    multi_timeframes: List[TimeFrame] = Field(
        default=[TimeFrame.MINUTE_15, TimeFrame.HOUR_1, TimeFrame.HOUR_4],
        description="Secondary timeframes for context"
    )
    
    regimes: List[RegimeDefinition] = Field(
        ...,
        description="Market regime definitions"
    )
    entry_playbooks: List[EntryPlaybook] = Field(
        ...,
        description="Entry rules by side"
    )
    exit_playbooks: List[ExitPlaybook] = Field(
        ...,
        description="Exit rules by side"
    )
    no_trade_conditions: List[NoTradeCondition] = Field(
        default=[],
        description="When NOT to trade"
    )
    checklist: List[ChecklistItem] = Field(
        default=[],
        description="Pre-trade verification checklist"
    )
    
    # Risk and parameters
    risk_params: RiskParameters = Field(
        default=RiskParameters(),
        description="Risk parameters"
    )
    
    # AI configuration
    ai_model: str = Field(
        default="gpt-4-turbo",
        description="LLM model to use (gpt-4-turbo, claude-3-opus, etc.)"
    )
    ai_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Temperature for LLM (lower = more deterministic)"
    )
    ai_max_tokens: int = Field(
        default=2000,
        ge=500,
        description="Max tokens for LLM response"
    )
    
    # Metadata
    symbols: List[str] = Field(
        ...,
        description="List of symbols this pack applies to (e.g., ['ETHUSDT', 'BTCUSDT'])"
    )
    min_analysis_confidence: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum AI confidence to propose trade"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "name": "ETH Trend Following",
                "version": 1,
                "description": "Follow major trends on ETH/USDT 1h timeframe",
                "active": True,
                "timeframe": "1h",
                "multi_timeframes": ["15m", "1h", "4h"],
                "regimes": [
                    {
                        "name": "Trending Up",
                        "indicators": {"RSI": ">50", "MACD": "positive"}
                    }
                ],
                "entry_playbooks": [
                    {
                        "side": "LONG",
                        "regime": "Trending Up",
                        "conditions": ["price > EMA_20", "RSI > 50"],
                        "target_ratio": 2.0
                    }
                ],
                "exit_playbooks": [
                    {
                        "side": "LONG",
                        "profit_target": "2xR",
                        "stop_loss": "EMA_20 break"
                    }
                ],
                "risk_params": {
                    "max_position_pct": 5.0,
                    "max_leverage": 10.0,
                    "min_risk_ratio": 1.5
                },
                "symbols": ["ETHUSDT"],
                "ai_model": "gpt-4-turbo"
            }
        }

    @validator('entry_playbooks')
    def validate_entry_playbooks(cls, v):
        """Ensure at least one entry playbook"""
        if not v or len(v) == 0:
            raise ValueError("At least one entry playbook required")
        return v

    @validator('exit_playbooks')
    def validate_exit_playbooks(cls, v):
        """Ensure at least one exit playbook"""
        if not v or len(v) == 0:
            raise ValueError("At least one exit playbook required")
        return v

    @validator('regimes')
    def validate_regimes(cls, v):
        """Ensure at least one regime"""
        if not v or len(v) == 0:
            raise ValueError("At least one regime definition required")
        return v

    def to_json(self) -> str:
        """Serialize to JSON for LLM prompt"""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "PromptPackSchema":
        """Deserialize from JSON"""
        return cls.model_validate_json(json_str)


class PromptPackSummary(BaseModel):
    """Summary for LLM - concise version of prompt pack"""
    regimes: str = Field(..., description="Regime definitions as markdown")
    entry_rules: str = Field(..., description="Entry playbooks as markdown")
    exit_rules: str = Field(..., description="Exit playbooks as markdown")
    no_trade_rules: str = Field(..., description="No-trade conditions")
    risk_limits: Dict[str, Any] = Field(..., description="Risk parameters")
    symbols: List[str] = Field(..., description="Valid symbols")

    def to_prompt(self) -> str:
        """Format for inclusion in LLM prompt"""
        return f"""
# Trading Rules

## Market Regimes
{self.regimes}

## Entry Rules
{self.entry_rules}

## Exit Rules
{self.exit_rules}

## No-Trade Conditions
{self.no_trade_rules}

## Risk Limits
{json.dumps(self.risk_limits, indent=2)}

## Valid Symbols
{', '.join(self.symbols)}
"""
