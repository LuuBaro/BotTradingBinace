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

    def __init__(self):
        self.decision_count = 0
        logger.info("trader_stub_initialized")

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
            
            # Calculate SL/TP based on side
            if side == Side.LONG:
                stop_loss = entry_price * 0.98  # 2% below
                take_profit = entry_price * 1.04  # 4% above
            else:
                stop_loss = entry_price * 1.02  # 2% above
                take_profit = entry_price * 0.96  # 4% below

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
                size_pct=random.uniform(0.05, 0.15),  # 5-15% of balance
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

