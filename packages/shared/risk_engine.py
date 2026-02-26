"""
Risk Engine - Hard guardrails for AI decisions
Deterministic risk validation to protect capital
"""
from datetime import datetime, timedelta
from typing import List
from packages.shared.schemas import Decision, RiskConfig, RiskValidationResult
from packages.shared.enums import RiskResult, ActionType
from packages.shared.logger import logger


class RiskEngine:
    """
    Deterministic risk engine that validates AI trading decisions
    Acts as hard guardrails - AI cannot bypass these limits
    """

    def __init__(self, risk_config: RiskConfig):
        self.config = risk_config
        self.recent_orders: List[datetime] = []
        self.last_loss_time: datetime | None = None
        logger.info("risk_engine_initialized", config=risk_config.model_dump())

    async def validate_decision(
        self,
        decision: Decision,
        current_positions: List[dict],
        balance: float,
        current_price: float,
    ) -> RiskValidationResult:
        """
        Validate trading decision against risk rules
        
        Args:
            decision: AI trading decision
            current_positions: List of current positions
            balance: Current account balance
            current_price: Current market price

        Returns:
            RiskValidationResult with approval status
        """
        # HOLD action always passes
        if decision.action == ActionType.HOLD:
            return RiskValidationResult(
                approved=True,
                result=RiskResult.APPROVED,
                reason="HOLD action - no risk",
            )

        # CLOSE action - validate we have position
        if decision.action == ActionType.CLOSE:
            has_position = any(p["symbol"] == decision.symbol for p in current_positions)
            if not has_position:
                return RiskValidationResult(
                    approved=False,
                    result=RiskResult.REJECTED,
                    reason="Cannot close - no position exists",
                )
            return RiskValidationResult(
                approved=True,
                result=RiskResult.APPROVED,
                reason="Close position approved",
            )

        # OPEN action - full risk validation
        checks = []

        # Check 1: Mandatory SL/TP
        if self.config.mandatory_sl_tp:
            if decision.stop_loss is None or decision.take_profit is None:
                return RiskValidationResult(
                    approved=False,
                    result=RiskResult.REJECTED,
                    reason="TỪ CHỐI: Thiếu điểm Cắt lỗ (SL) hoặc Chốt lời (TP) bắt buộc",
                )
            checks.append("SL/TP hiện diện")

        # Check 2: Max leverage
        if decision.leverage > self.config.max_leverage:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason=f"TỪ CHỐI: Đòn bẩy {decision.leverage}x vượt mức tối đa {self.config.max_leverage}x",
            )
        checks.append(f"Đòn bẩy {decision.leverage}x OK")

        # Check 3: Max position size
        if decision.size_pct > self.config.max_position_pct:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason=f"TỪ CHỐI: Kích thước vị thế {decision.size_pct:.1%} vượt mức tối đa {self.config.max_position_pct:.1%}",
            )
        checks.append(f"Kích thước {decision.size_pct:.1%} OK")

        # Check 4: Risk per trade
        if decision.stop_loss:
            entry_price = decision.entry_price or current_price
            risk_per_unit = abs(entry_price - decision.stop_loss)
            quantity = (balance * decision.size_pct * decision.leverage) / entry_price
            total_risk = risk_per_unit * quantity
            risk_pct = total_risk / balance if balance > 0 else 1.0

            if risk_pct > self.config.max_risk_per_trade_pct:
                return RiskValidationResult(
                    approved=False,
                    result=RiskResult.REJECTED,
                    reason=f"TỪ CHỐI: Rủi ro {risk_pct:.2%} vượt mức tối đa cho phép {self.config.max_risk_per_trade_pct:.2%}",
                )
            checks.append(f"Rủi ro {risk_pct:.2%} OK")

        # Check 5: Max concurrent positions
        if len(current_positions) >= self.config.max_concurrent_positions:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason=f"TỪ CHỐI: Đã đạt giới hạn {self.config.max_concurrent_positions} vị thế cùng lúc",
            )
        checks.append(f"Số vị thế {len(current_positions)}/{self.config.max_concurrent_positions}")

        # Check 6: Orders per hour
        self._clean_old_orders()
        if len(self.recent_orders) >= self.config.max_orders_per_hour:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason=f"TỪ CHỐI: Vượt quá giới hạn {self.config.max_orders_per_hour} lệnh/giờ",
            )
        checks.append(f"Số lệnh trong giờ OK")

        # Check 7: Cooldown after loss
        if self.last_loss_time:
            cooldown_until = self.last_loss_time + timedelta(seconds=self.config.cooldown_after_loss)
            if datetime.utcnow() < cooldown_until:
                remaining = (cooldown_until - datetime.utcnow()).seconds
                return RiskValidationResult(
                    approved=False,
                    result=RiskResult.REJECTED,
                    reason=f"TỪ CHỐI: Đang trong thời gian chờ sau lỗ ({remaining} giây còn lại)",
                )
        checks.append("Không có cooldown")

        # All checks passed
        self.recent_orders.append(datetime.utcnow())
        logger.info(
            "risk_validation_approved",
            symbol=decision.symbol,
            action=decision.action.value,
            checks=checks,
        )

        return RiskValidationResult(
            approved=True,
            result=RiskResult.APPROVED,
            reason=f"ĐÃ DUYỆT - Tất cả kiểm tra an toàn đều đạt: {', '.join(checks)}",
        )

    def _clean_old_orders(self) -> None:
        """Remove orders older than 1 hour"""
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.recent_orders = [t for t in self.recent_orders if t > cutoff]

    def record_loss(self) -> None:
        """Record a losing trade to trigger cooldown"""
        self.last_loss_time = datetime.utcnow()
        logger.warning("loss_recorded", cooldown_sec=self.config.cooldown_after_loss)

    def record_win(self) -> None:
        """Record a winning trade (clears cooldown)"""
        self.last_loss_time = None
        logger.info("win_recorded", cooldown_cleared=True)
