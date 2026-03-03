"""
Enums for AI Trading Bot
"""
from enum import Enum


class MarketRegime(str, Enum):
    """Market regime classification"""

    TREND = "trend"
    RANGE = "range"
    BREAKOUT = "breakout"
    VOLATILITY_SPIKE = "volatility_spike"


class ActionType(str, Enum):
    """Trading action type"""

    OPEN = "open"
    CLOSE = "close"
    HOLD = "hold"
    NONE = "none"


class Side(str, Enum):
    """Position/Order side"""

    LONG = "long"
    SHORT = "short"


class PositionSide(str, Enum):
    """Binance position side (for hedge mode)"""

    BOTH = "BOTH"  # One-way mode
    LONG = "LONG"  # Hedge mode long
    SHORT = "SHORT"  # Hedge mode short


class OrderType(str, Enum):
    """Order type"""

    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    TAKE_PROFIT_MARKET = "take_profit_market"


class OrderStatus(str, Enum):
    """Order status"""

    PENDING = "pending"
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


class EventLevel(str, Enum):
    """Event log level"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class RiskResult(str, Enum):
    """Risk engine validation result"""

    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class IntentStatus(str, Enum):
    """Order intent status"""

    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
