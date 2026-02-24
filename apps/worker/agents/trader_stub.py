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
            decision = Decision(
                regime=regime,
                action=action,
                symbol=snapshot.symbol,
                side=None,
                size_pct=0.0,
                leverage=1,
                stop_loss=None,
                take_profit=None,
                confidence=random.uniform(0.5, 0.7),
                rationale="Mock HOLD decision - market conditions not favorable",
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
                confidence=random.uniform(0.65, 0.85),
                rationale=f"Mock {action.value} decision for testing - {regime.value} regime detected",
                checklist=[
                    ChecklistItem(
                        condition="Trend confirmed on 4H",
                        pass_=random.choice([True, False])
                    ),
                    ChecklistItem(
                        condition="Volume above average",
                        pass_=random.choice([True, True, False])  # 67% pass
                    ),
                    ChecklistItem(
                        condition="RSI not overbought/oversold",
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
