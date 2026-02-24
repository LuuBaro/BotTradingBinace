"""
Trade Journal Schema - Record every completed trade for analysis
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class ExitReason(str, Enum):
    """Why trade was exited"""
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    MANUAL = "MANUAL"
    TIMEOUT = "TIMEOUT"
    LIQUIDATION = "LIQUIDATION"


class TradeJournalEntry(BaseModel):
    """Complete record of a closed trade"""
    
    # Identifiers
    trace_id: str = Field(..., description="Original decision trace_id")
    trade_id: str = Field(..., description="Unique trade identifier")
    
    # Trade basic info
    symbol: str = Field(..., description="Trading pair (e.g., 'ETHUSDT')")
    side: str = Field(..., description="LONG or SHORT")
    entry_time: datetime = Field(..., description="Entry trade time")
    exit_time: datetime = Field(..., description="Exit trade time")
    
    # Entry details
    entry_price: float = Field(..., description="Price at entry")
    entry_quantity: float = Field(..., description="Quantity entered")
    entry_leverage: float = Field(default=1.0, description="Leverage used")
    
    # Exit details
    exit_price: float = Field(..., description="Price at exit")
    exit_reason: ExitReason = Field(..., description="Why trade was exited")
    
    # Profit/Loss
    pnl: float = Field(..., description="Profit/loss in quote currency")
    pnl_pct: float = Field(..., description="Profit/loss percentage")
    commission: float = Field(default=0.0, description="Trading fees")
    
    # Risk management metrics
    risk_reward_ratio: float = Field(..., description="Actual RR ratio achieved")
    holding_time_minutes: int = Field(..., description="How long position held")
    max_drawdown: float = Field(..., description="Max intra-trade drawdown %")
    max_runup: float = Field(..., description="Max intra-trade profit %")
    
    # Market conditions at entry
    market_regime: str = Field(..., description="Regime at entry (Trending Up, Ranging, etc)")
    volatility_percentile: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Volatility rank (0-100)"
    )
    bid_ask_spread_pips: float = Field(default=0.0, description="Spread in pips")
    funding_rate: float = Field(default=0.0, description="Funding rate at entry")
    
    # Risk metrics
    position_pct: float = Field(..., description="Position size as % of account")
    stop_loss_pips: float = Field(..., description="Distance to SL in pips")
    take_profit_pips: float = Field(..., description="Distance to TP in pips")
    
    # Decision info
    decision_json: Dict[str, Any] = Field(..., description="AI decision that led to trade")
    confidence: float = Field(..., description="AI confidence in decision")
    ai_model: str = Field(..., description="Which model made decision")
    prompt_pack_version: int = Field(..., description="Which rule set was used")
    
    # Outcome classification
    is_winner: bool = Field(..., description="Trade profitable?")
    is_breakeven: bool = Field(default=False, description="Trade at breakeven?")
    
    # Notes
    notes: Optional[str] = Field(default=None, description="Trader notes")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "trace_id": "trace_2024_01_15_10_30_42_eth_001",
                "trade_id": "trade_20240115_eth_001",
                "symbol": "ETHUSDT",
                "side": "LONG",
                "entry_time": "2024-01-15T10:30:42Z",
                "exit_time": "2024-01-15T13:45:22Z",
                "entry_price": 2500.0,
                "entry_quantity": 10.0,
                "entry_leverage": 5.0,
                "exit_price": 2550.0,
                "exit_reason": "TAKE_PROFIT",
                "pnl": 2450.0,
                "pnl_pct": 1.96,
                "risk_reward_ratio": 2.5,
                "holding_time_minutes": 195,
                "market_regime": "Trending Up",
                "volatility_percentile": 60,
                "bid_ask_spread_pips": 0.5,
                "position_pct": 3.5,
                "stop_loss_pips": 50,
                "take_profit_pips": 500,
                "confidence": 0.85,
                "is_winner": True
            }
        }


class TradeJournalStats(BaseModel):
    """Statistics calculated from trade journal"""
    
    total_trades: int = Field(..., description="Total trades analyzed")
    winning_trades: int = Field(..., description="Number of profitable trades")
    losing_trades: int = Field(..., description="Number of losing trades")
    breakeven_trades: int = Field(..., description="Number of breakeven trades")
    
    # Win rates
    win_rate: float = Field(..., ge=0.0, le=1.0, description="Win rate (0.0-1.0)")
    win_rate_by_regime: Dict[str, float] = Field(..., description="Win rate per regime")
    
    # PnL metrics
    total_pnl: float = Field(..., description="Total profit/loss")
    avg_win: float = Field(..., description="Average winning trade")
    avg_loss: float = Field(..., description="Average losing trade")
    largest_win: float = Field(..., description="Biggest winning trade")
    largest_loss: float = Field(..., description="Biggest losing trade")
    
    # Risk metrics
    profit_factor: float = Field(..., description="Gross profit / Gross loss")
    max_drawdown: float = Field(..., description="Maximum drawdown %")
    max_consecutive_losses: int = Field(..., description="Longest losing streak")
    max_consecutive_wins: int = Field(..., description="Longest winning streak")
    
    # Time metrics
    avg_holding_time_minutes: float = Field(..., description="Average hold time")
    avg_rr_ratio: float = Field(..., description="Average risk/reward ratio")
    
    # Regime performance
    best_regime: Optional[str] = Field(default=None, description="Best performing regime")
    worst_regime: Optional[str] = Field(default=None, description="Worst performing regime")
    
    # Conditions analysis
    performance_by_volatility: Dict[str, Dict[str, Any]] = Field(
        default={},
        description="Performance in different volatility ranges"
    )
    performance_by_spread: Dict[str, Dict[str, Any]] = Field(
        default={},
        description="Performance at different spread levels"
    )
    performance_by_leverage: Dict[str, Dict[str, Any]] = Field(
        default={},
        description="Performance at different leverage levels"
    )
    performance_by_time_of_day: Dict[str, Dict[str, Any]] = Field(
        default={},
        description="Performance by hour of day"
    )

    class Config:
        schema_extra = {
            "example": {
                "total_trades": 50,
                "winning_trades": 32,
                "losing_trades": 18,
                "win_rate": 0.64,
                "total_pnl": 15000.0,
                "avg_win": 800.0,
                "avg_loss": -250.0,
                "profit_factor": 3.2,
                "max_drawdown": 5.5,
                "best_regime": "Trending Up",
                "worst_regime": "Ranging"
            }
        }


class PatternsDiscovered(BaseModel):
    """Losing patterns detected"""
    
    pattern_name: str = Field(..., description="Pattern identifier")
    description: str = Field(..., description="Human-readable description")
    occurrences: int = Field(..., description="How many times seen")
    avg_loss_when_triggered: float = Field(..., description="Average loss when pattern occurs")
    
    # Trigger conditions
    conditions: Dict[str, Any] = Field(
        ...,
        description="Conditions that trigger pattern"
    )
    
    # Example triggers
    recommendation: str = Field(..., description="Recommended action")

    class Config:
        schema_extra = {
            "example": {
                "pattern_name": "low_volatility_entries",
                "description": "Trading when volatility < 40th percentile",
                "occurrences": 8,
                "avg_loss_when_triggered": -450.0,
                "conditions": {
                    "volatility_percentile": "<40",
                    "win_rate_when_triggered": 0.25
                },
                "recommendation": "Avoid trading when volatility < 40th percentile"
            }
        }


class ConfidenceMetrics(BaseModel):
    """AI confidence calibration analysis"""
    
    confidence_bucket: str = Field(
        ...,
        description="Confidence range (e.g., '0.8-0.9')"
    )
    count: int = Field(..., description="Number of trades in this bucket")
    win_rate_in_bucket: float = Field(..., description="Actual win rate in this bucket")
    avg_pnl_in_bucket: float = Field(..., description="Average PnL in this bucket")
    
    class Config:
        schema_extra = {
            "example": {
                "confidence_bucket": "0.8-0.9",
                "count": 15,
                "win_rate_in_bucket": 0.8,
                "avg_pnl_in_bucket": 650.0
            }
        }
