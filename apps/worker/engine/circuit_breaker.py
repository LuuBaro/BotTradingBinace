"""
Circuit Breaker - Safe mode when system health degrades
Prevents new orders when WS is down or REST errors are high
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from enum import Enum
from packages.shared.logger import logger


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Triggered - no new orders
    HALF_OPEN = "half_open"  # Recovery attempt


class CircuitBreaker:
    """
    Circuit breaker for safe mode
    - Monitors WebSocket connection: if down > 10s → OPEN
    - Monitors REST error rate: if > 10% of last 100 requests → OPEN
    - Auto-recovers after cooldown (60s)
    """

    def __init__(self):
        self.state = CircuitBreakerState.CLOSED
        self.last_error_time: Optional[datetime] = None
        self.error_count = 0
        self.request_count = 0
        self.max_error_rate = 0.10  # 10%
        self.cooldown_seconds = 60
        self.ws_down_threshold = 10  # seconds
        self.ws_last_message_time: Optional[datetime] = None
        
        logger.info("circuit_breaker_initialized")

    def record_ws_message(self) -> None:
        """Record WebSocket message received"""
        self.ws_last_message_time = datetime.utcnow()
        
        # Try to recover if in OPEN state
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("circuit_breaker_attempting_recovery")

    def record_rest_request(self, success: bool) -> None:
        """Record REST API request result"""
        self.request_count += 1
        if not success:
            self.error_count += 1
            self.last_error_time = datetime.utcnow()
        
        # Check if error rate exceeded
        if self.request_count >= 100:
            error_rate = self.error_count / self.request_count
            if error_rate > self.max_error_rate:
                if self.state == CircuitBreakerState.CLOSED:
                    logger.warning(
                        "circuit_breaker_opened",
                        error_rate=error_rate,
                        threshold=self.max_error_rate,
                    )
                self.state = CircuitBreakerState.OPEN
            else:
                # Reset if recovered
                if self.state == CircuitBreakerState.HALF_OPEN:
                    logger.info("circuit_breaker_closed_recovered")
                    self.state = CircuitBreakerState.CLOSED
                    self.error_count = 0
                    self.request_count = 0
            
            # Reset counters every 100 requests
            if self.request_count >= 100:
                self.error_count = 0
                self.request_count = 0

    def check_ws_health(self) -> bool:
        """Check if WebSocket is healthy"""
        if self.ws_last_message_time is None:
            return False
        
        time_since_message = (
            datetime.utcnow() - self.ws_last_message_time
        ).total_seconds()
        
        if time_since_message > self.ws_down_threshold:
            if self.state == CircuitBreakerState.CLOSED:
                logger.warning(
                    "circuit_breaker_opened",
                    reason="ws_down",
                    duration_sec=time_since_message,
                )
                self.state = CircuitBreakerState.OPEN
            return False
        
        return True

    def is_safe_for_trading(self) -> bool:
        """Check if system is safe for new orders"""
        # Health checks
        if not self.check_ws_health():
            return False
        
        # State checks
        return self.state != CircuitBreakerState.OPEN

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "state": self.state.value,
            "is_safe_for_trading": self.is_safe_for_trading(),
            "error_count": self.error_count,
            "request_count": self.request_count,
            "error_rate": (
                self.error_count / self.request_count
                if self.request_count > 0
                else 0
            ),
            "ws_last_message": (
                self.ws_last_message_time.isoformat()
                if self.ws_last_message_time
                else None
            ),
            "last_error_time": (
                self.last_error_time.isoformat()
                if self.last_error_time
                else None
            ),
        }

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if not self.last_error_time:
            return True
        
        time_since_error = (
            datetime.utcnow() - self.last_error_time
        ).total_seconds()
        
        return time_since_error >= self.cooldown_seconds
