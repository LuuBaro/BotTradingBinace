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
        self.consecutive_losses: int = 0
        self.daily_loss_pct: float = 0.0
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
            target_symbol = str(decision.symbol).upper()
            has_position = any(
                str(p.get("symbol", "")).upper() == target_symbol
                and float(p.get("qty", 0) or 0) > 0
                for p in current_positions
            )
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

        # Check 1: Trading is enabled
        if not self.config.enabled:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason="TỪ CHỐI: Trading hiện bị vô hiệu hóa",
            )
        checks.append("Trading bật")

        # Check 2: Minimum balance threshold
        if balance < self.config.min_balance_threshold:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason=f"TỪ CHỐI: Số dư {balance:.2f} USDT dưới mức tối thiểu {self.config.min_balance_threshold:.2f} USDT",
            )
        checks.append(f"Số dư {balance:.2f} OK")

        # Check 3: Mandatory SL/TP
        if self.config.mandatory_sl_tp:
            if decision.stop_loss is None or decision.take_profit is None:
                return RiskValidationResult(
                    approved=False,
                    result=RiskResult.REJECTED,
                    reason="TỪ CHỐI: Thiếu điểm Cắt lỗ (SL) hoặc Chốt lời (TP) bắt buộc",
                )
            checks.append("SL/TP hiện diện")

        # Check 4: Max leverage
        if decision.leverage > self.config.max_leverage:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason=f"TỪ CHỐI: Đòn bẩy {decision.leverage}x vượt mức tối đa {self.config.max_leverage}x",
            )
        checks.append(f"Đòn bẩy {decision.leverage}x OK")

        # Check 5: Max position size (overall)
        if decision.size_pct > self.config.max_position_pct:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason=f"TỪ CHỐI: Kích thước vị thế {decision.size_pct:.1%} vượt mức tối đa {self.config.max_position_pct:.1%}",
            )
        checks.append(f"Kích thước {decision.size_pct:.1%} OK")

        # Check 6: Max position per symbol
        symbol_position = sum(
            float(p.get("qty", 0) or 0)
            for p in current_positions
            if str(p.get("symbol", "")).upper() == str(decision.symbol).upper()
        )
        symbol_position_pct = (symbol_position * current_price / balance) if balance > 0 else 0
        if symbol_position_pct > self.config.max_position_per_symbol:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason=f"TỪ CHỐI: Vị thế {decision.symbol} đạt {symbol_position_pct:.1%} vượt mức {self.config.max_position_per_symbol:.1%}",
            )
        checks.append(f"Vị thế {decision.symbol} {symbol_position_pct:.1%} OK")

        # Check 7: Risk per trade
        if decision.stop_loss:
            entry_price = decision.entry_price or current_price
            risk_per_unit = abs(entry_price - decision.stop_loss)
            quantity = (balance * decision.size_pct * decision.leverage) / entry_price
            total_risk = risk_per_unit * quantity
            risk_pct = total_risk / balance if balance > 0 else 1.0

            logger.debug(
                f"🔍 RISK CALCULATION DEBUG:\n"
                f"  Entry: ${entry_price:.5f}\n"
                f"  Stop Loss: ${decision.stop_loss:.5f}\n"
                f"  Risk per unit: ${risk_per_unit:.5f}\n"
                f"  Size PCT: {decision.size_pct:.4f} ({decision.size_pct*100:.2f}%)\n"
                f"  Leverage: {decision.leverage}x\n"
                f"  Balance: ${balance:.2f}\n"
                f"  Quantity: {quantity:.4f}\n"
                f"  Total Risk: ${total_risk:.2f}\n"
                f"  Risk PCT: {risk_pct:.4f} ({risk_pct*100:.2f}%)\n"
                f"  Max Allowed: {self.config.max_risk_per_trade_pct:.4f} ({self.config.max_risk_per_trade_pct*100:.2f}%)"
            )

            if risk_pct > self.config.max_risk_per_trade_pct:
                return RiskValidationResult(
                    approved=False,
                    result=RiskResult.REJECTED,
                    reason=f"TỪ CHỐI: Rủi ro {risk_pct:.2%} vượt mức tối đa cho phép {self.config.max_risk_per_trade_pct:.2%}",
                )
            checks.append(f"Rủi ro {risk_pct:.2%} OK")

        # Check 8: Risk/Reward Ratio
        if decision.stop_loss and decision.take_profit:
            entry_price = decision.entry_price or current_price
            risk = abs(entry_price - decision.stop_loss)
            reward = abs(decision.take_profit - entry_price)
            if risk > 0:
                risk_reward_ratio = reward / risk
                if risk_reward_ratio < self.config.min_risk_reward_ratio:
                    return RiskValidationResult(
                        approved=False,
                        result=RiskResult.REJECTED,
                        reason=f"TỪ CHỐI: Tỉ lệ R/R {risk_reward_ratio:.2f} dưới mức tối thiểu {self.config.min_risk_reward_ratio:.2f}",
                    )
                checks.append(f"R/R {risk_reward_ratio:.2f} OK")

        # Check 9: Max concurrent positions
        if len(current_positions) >= self.config.max_concurrent_positions:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason=f"TỪ CHỐI: Đã đạt giới hạn {self.config.max_concurrent_positions} vị thế cùng lúc",
            )
        checks.append(f"Số vị thế {len(current_positions)}/{self.config.max_concurrent_positions}")

        # Check 10: Orders per hour
        self._clean_old_orders()
        if len(self.recent_orders) >= self.config.max_orders_per_hour:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason=f"TỪ CHỐI: Vượt quá giới hạn {self.config.max_orders_per_hour} lệnh/giờ",
            )
        checks.append(f"Số lệnh trong giờ OK")

        # Check 11: Consecutive losses
        if hasattr(self, 'consecutive_losses') and self.consecutive_losses >= self.config.max_consecutive_losses:
            return RiskValidationResult(
                approved=False,
                result=RiskResult.REJECTED,
                reason=f"TỪ CHỐI: {self.consecutive_losses} losses liên tiếp, tạm dừng trading",
            )
        checks.append(f"Losses liên tiếp OK")

        # Check 12: Cooldown after loss
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

    def record_loss(self, loss_amount: float = 0, balance: float = 1) -> None:
        """Record a losing trade to trigger cooldown"""
        self.last_loss_time = datetime.utcnow()
        self.consecutive_losses += 1
        if balance > 0:
            self.daily_loss_pct += (loss_amount / balance)
        logger.warning(
            "loss_recorded",
            consecutive_losses=self.consecutive_losses,
            daily_loss_pct=self.daily_loss_pct,
            cooldown_sec=self.config.cooldown_after_loss
        )

    def record_win(self) -> None:
        """Record a winning trade (clears consecutive loss counter)"""
        self.consecutive_losses = 0
        logger.info("win_recorded", consecutive_losses_reset=True)
