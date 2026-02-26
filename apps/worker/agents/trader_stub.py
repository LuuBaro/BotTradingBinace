"""
Trader Agent Stub - Mock AI decision maker for Phase 1 testing
Generates random but valid trading decisions
"""
import random
import uuid
from datetime import datetime
from packages.shared.schemas import Decision, MarketSnapshot, ChecklistItem
from packages.shared.enums import MarketRegime, ActionType, Side, OrderType
from packages.shared.logger import logger


class TraderStub:
    """
    Mock trader agent for testing
    Generates random but structurally valid decisions
    """

    def __init__(self, max_position_pct: float = 0.05):
        self.decision_count = 0
        self.position_peaks = {}  # Track highest price for trailing stop
        self.max_position_pct = max_position_pct  # Store limit for validation
        logger.info("trader_stub_initialized", max_position_pct=max_position_pct)
    
    def calculate_dynamic_targets(self, entry_price: float, side: Side, volatility: float = 0.02) -> tuple[float, float]:
        """
        Calculate SL/TP with randomization to avoid Binance anti-bot detection
        
        Args:
            entry_price: Entry price
            side: LONG or SHORT
            volatility: Market volatility (0-1)
            
        Returns:
            (stop_loss, take_profit) with randomization applied
        """
        # Base percentages với randomization để tránh pattern
        sl_pct = random.uniform(0.018, 0.025)  # 1.8% - 2.5%
        tp_pct = random.uniform(0.035, 0.055)  # 3.5% - 5.5%
        
        # Adjust based on volatility
        if volatility > 0.03:  # High volatility
            tp_pct *= 1.5
            sl_pct *= 1.2
        
        if side == Side.LONG:
            stop_loss = entry_price * (1 - sl_pct)
            take_profit = entry_price * (1 + tp_pct)
        else:
            stop_loss = entry_price * (1 + sl_pct)
            take_profit = entry_price * (1 - tp_pct)
        
        # Add slight randomness to avoid round numbers (anti-bot)
        stop_loss += random.uniform(-3, 3)
        take_profit += random.uniform(-5, 5)
        
        return round(stop_loss, 2), round(take_profit, 2)
    
    def should_close_with_trailing_stop(
        self, 
        position_id: str,
        entry_price: float, 
        current_price: float, 
        side: Side,
        trailing_activation_pct: float = 0.04,  # Activate at +4% profit
        trailing_distance_pct: float = 0.02     # Trail at -2% from peak
    ) -> tuple[bool, str]:
        """
        Check if position should be closed with trailing stop
        
        Args:
            position_id: Unique position identifier
            entry_price: Original entry price
            current_price: Current market price
            side: LONG or SHORT
            trailing_activation_pct: Profit % to activate trailing (default 4%)
            trailing_distance_pct: Distance % from peak to trigger close (default 2%)
            
        Returns:
            (should_close, reason)
        """
        if side == Side.LONG:
            profit_pct = (current_price - entry_price) / entry_price
            
            # Track highest price for this position
            if position_id not in self.position_peaks:
                self.position_peaks[position_id] = entry_price
            
            highest_price = self.position_peaks[position_id]
            
            # Update highest price if current is higher
            if current_price > highest_price:
                highest_price = current_price
                self.position_peaks[position_id] = highest_price
                logger.info(
                    "trailing_stop_peak_updated",
                    position_id=position_id,
                    new_peak=highest_price,
                    profit_pct=f"{profit_pct*100:.2f}%"
                )
            
            # Check if trailing stop should activate
            if profit_pct > trailing_activation_pct:
                drawdown_from_peak = (highest_price - current_price) / highest_price
                
                if drawdown_from_peak > trailing_distance_pct:
                    # Clean up tracking
                    del self.position_peaks[position_id]
                    
                    reason = f"TRAILING STOP: Giá giảm {drawdown_from_peak*100:.2f}% từ đỉnh ${highest_price:.2f}. Bảo vệ profit ${current_price - entry_price:.2f} (+{profit_pct*100:.2f}%)"
                    logger.warning(
                        "trailing_stop_triggered",
                        position_id=position_id,
                        entry=entry_price,
                        peak=highest_price,
                        current=current_price,
                        profit_protected=f"{profit_pct*100:.2f}%"
                    )
                    return True, reason
        
        else:  # SHORT
            profit_pct = (entry_price - current_price) / entry_price
            
            # Track lowest price for SHORT
            if position_id not in self.position_peaks:
                self.position_peaks[position_id] = entry_price
            
            lowest_price = self.position_peaks[position_id]
            
            if current_price < lowest_price:
                lowest_price = current_price
                self.position_peaks[position_id] = lowest_price
                logger.info(
                    "trailing_stop_peak_updated_short",
                    position_id=position_id,
                    new_low=lowest_price,
                    profit_pct=f"{profit_pct*100:.2f}%"
                )
            
            if profit_pct > trailing_activation_pct:
                drawup_from_low = (current_price - lowest_price) / lowest_price
                
                if drawup_from_low > trailing_distance_pct:
                    del self.position_peaks[position_id]
                    
                    reason = f"TRAILING STOP: Giá tăng {drawup_from_low*100:.2f}% từ đáy ${lowest_price:.2f}. Bảo vệ profit ${entry_price - current_price:.2f} (+{profit_pct*100:.2f}%)"
                    logger.warning(
                        "trailing_stop_triggered_short",
                        position_id=position_id,
                        entry=entry_price,
                        low=lowest_price,
                        current=current_price,
                        profit_protected=f"{profit_pct*100:.2f}%"
                    )
                    return True, reason
        
        return False, ""

    async def decide(self, snapshot: MarketSnapshot) -> Decision:
        """
        Generate a mock trading decision
        
        60% HOLD, 30% OPEN, 10% CLOSE
        """
        self.decision_count += 1

        # Random regime
        regime = random.choice(list(MarketRegime))

        # Random action with weighted probability
        action_rand = random.random()
        if action_rand < 0.6:
            action = ActionType.HOLD
        elif action_rand < 0.9:
            action = ActionType.OPEN
        else:
            action = ActionType.CLOSE

        # If HOLD, return minimal decision
        if action == ActionType.HOLD:
            hold_reasons = [
                "Độ biến động thấp, chưa có xu hướng rõ ràng.",
                "RSI đang ở vùng trung tính, không có tín hiệu quá mua/quá bán.",
                "Giá đang đi ngang (sideways) tích lũy, đứng ngoài quan sát.",
                "EMA-20 và EMA-50 chưa có dấu hiệu giao cắt.",
                "Khối lượng giao dịch yếu, rủi ro thanh khoản nếu vào lệnh."
            ]
            decision = Decision(
                regime=regime,
                action=action,
                symbol=snapshot.symbol,
                side=None,
                size_pct=0.01,
                leverage=1,
                stop_loss=None,
                take_profit=None,
                confidence=random.uniform(0.5, 0.7),
                rationale=f"PHÂN TÍCH: {random.choice(hold_reasons)} Hệ thống AI quyết định đứng ngoài để bảo toàn vốn.",
                checklist=[
                    ChecklistItem(condition="Trend not confirmed", pass_=False),
                    ChecklistItem(condition="Volume below threshold", pass_=False),
                ],
            )
        else:
            # OPEN or CLOSE
            side = random.choice([Side.LONG, Side.SHORT])
            entry_price = snapshot.close
            
            # CRITICAL: Generate size within STRICT limit
            # Size = 30% to 100% of max_position_pct (safety margin)
            min_size = self.max_position_pct * 0.3
            max_size = self.max_position_pct * 0.95  # Stay 5% below limit
            size_pct = random.uniform(min_size, max_size)
            
            # Validation: MUST NOT EXCEED MAX (hard constraint)
            if size_pct > self.max_position_pct:
                logger.error(
                    "CRITICAL_SIZE_VALIDATION_FAILED",
                    generated_size=size_pct,
                    max_allowed=self.max_position_pct,
                    status="THIS_SHOULD_NEVER_HAPPEN"
                )
                size_pct = self.max_position_pct * 0.9  # Force to safe level
            
            logger.debug(
                "position_size_generated",
                size_pct=f"{size_pct*100:.1f}%",
                max_limit=f"{self.max_position_pct*100:.1f}%",
                buffer_remaining=f"{(self.max_position_pct - size_pct)*100:.1f}%"
            )
            
            # Use dynamic SL/TP calculation with randomization (anti-bot)
            volatility = abs(snapshot.volume) / 1000000 if snapshot.volume else 0.02
            stop_loss, take_profit = self.calculate_dynamic_targets(entry_price, side, volatility)

            confidence_val = random.uniform(0.65, 0.85)
            action_desc = "Vào lệnh (Open)" if action == ActionType.OPEN else "Đóng vị thế (Close)"
            
            target_profit = (take_profit - entry_price) / entry_price * 100 if side == Side.LONG else (entry_price - take_profit) / entry_price * 100
            
            # Map regime to Vietnamese
            regime_vn = {
                MarketRegime.TREND: "XU HƯỚNG MẠNH",
                MarketRegime.RANGE: "BIÊN ĐỘ HẸP",
                MarketRegime.VOLATILITY_SPIKE: "BIẾN ĐỘNG CAO",
                MarketRegime.BREAKOUT: "PHÁ VỠ MỨC CẢN"
            }.get(regime, regime.value)

            decision = Decision(
                regime=regime,
                action=action,
                symbol=snapshot.symbol,
                side=side,
                entry_type=OrderType.MARKET,
                entry_price=entry_price if action == ActionType.OPEN else None,
                size_pct=size_pct,  # ✅ Uses validated size from above
                leverage=random.randint(2, 5),  # 2-5x leverage
                stop_loss=stop_loss if action == ActionType.OPEN else None,
                take_profit=take_profit if action == ActionType.OPEN else None,
                confidence=confidence_val,
                rationale=f"CHIẾN LƯỢC {action_desc}: Thị trường đang trong trạng thái {regime_vn}. " + 
                f"Dòng tiền (Delta Profile) cho thấy áp lực bán đã bị hấp thụ hoàn toàn tại các vùng hỗ trợ cục bộ. " +
                f"Kỳ vọng tăng trưởng: {target_profit:.1f}%. Điểm chốt lời dự kiến: ${take_profit:.2f}.",
                checklist=[
                    ChecklistItem(
                        condition="Xác nhận xu hướng khung 4H",
                        pass_=True
                    ),
                    ChecklistItem(
                        condition="Khối lượng giao dịch đạt chuẩn",
                        pass_=random.choice([True, True, False])
                    ),
                    ChecklistItem(
                        condition="Tỷ lệ Risk/Reward > 2.0",
                        pass_=True
                    ),
                ],
            )

        logger.info(
            "trader_decision_generated",
            decision_count=self.decision_count,
            regime=regime.value,
            action=action.value,
            confidence=decision.confidence,
        )

        return decision

    async def get_analysis(self, snapshot: MarketSnapshot) -> dict:
        """
        Generate mock market analysis insights
        """
        bias = random.choice(["Bullish", "Bearish", "Neutral"])
        target = snapshot.close * (1.05 if bias == "Bullish" else 0.95 if bias == "Bearish" else 1.0)
        
        return {
            "bias": bias,
            "target_price": round(target, 2),
            "expected_move": "Breakout" if random.random() > 0.5 else "Consolidation",
            "support": round(snapshot.close * 0.97, 2),
            "resistance": round(snapshot.close * 1.03, 2),
            "volatility": "High" if random.random() > 0.7 else "Medium",
            "timeframe": "1H",
            "upcoming_signals": [
                {
                    "symbol": snapshot.symbol,
                    "side": "LONG" if bias == "Bullish" else "SHORT",
                    "entry_zone": f"{round(target*0.99, 1)}-{round(target*1.01, 1)}",
                    "probability": random.uniform(0.6, 0.85),
                    "rationale": f"Anticipating {bias} reversal near support"
                }
            ]
        }

