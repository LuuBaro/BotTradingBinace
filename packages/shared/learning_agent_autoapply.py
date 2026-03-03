"""
Learning Agent Auto-Apply: Automatically apply safe recommendations from analysis.

Balances automation, safety, and user control.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import json

from packages.shared.models import RecommendationApprovalLog, BotConfig
from packages.shared.logger import logger


class RecommendationCategory(str, Enum):
    """Classify recommendations by safety level"""
    SAFE = "safe"
    MODERATE = "moderate"
    RISKY = "risky"


class RecommendationSafety:
    """Determine if recommendation is safe to auto-apply"""
    
    SAFE_RECOMMENDATIONS = [
        "increase_win_rate_threshold",
        "reduce_position_size",
        "widen_stop_loss",
        "tighten_take_profit",
        "reduce_leverage",
        "add_regime_filter",
        "increase_entry_quality_requirement",
        "skip_trades_on_high_volatility",
    ]
    
    RISKY_RECOMMENDATIONS = [
        "increase_leverage",
        "increase_position_size",
        "disable_stop_loss",
        "remove_daily_loss_limit",
        "disable_regime_filter",
        "reduce_win_rate_threshold",
        "tighten_stop_loss",
        "widen_take_profit",
    ]
    
    @staticmethod
    def categorize(recommendation_type: str) -> RecommendationCategory:
        """Determine safety level of a recommendation"""
        
        if recommendation_type in RecommendationSafety.SAFE_RECOMMENDATIONS:
            return RecommendationCategory.SAFE
        elif recommendation_type in RecommendationSafety.RISKY_RECOMMENDATIONS:
            return RecommendationCategory.RISKY
        else:
            return RecommendationCategory.MODERATE
    
    @staticmethod
    def can_auto_apply(
        recommendation_type: str,
        confidence: float,
        safety_category: RecommendationCategory
    ) -> bool:
        """Determine if recommendation can be auto-applied"""
        
        if safety_category == RecommendationCategory.SAFE:
            return confidence > 0.7
        elif safety_category == RecommendationCategory.MODERATE:
            return confidence > 0.9
        else:
            return False


@dataclass
class AppliedRecommendation:
    """Record of recommendation that was applied"""
    id: int
    user_id: str
    recommendation_type: str
    safety_category: RecommendationCategory
    confidence: float
    applied_at: datetime
    applied_automatically: bool
    approved_by: str | None
    previous_config: Dict
    current_config: Dict
    result_metric: str | None = None
    result_change_percent: float | None = None


@dataclass
class LearningRecommendation:
    """Recommendation from Learning Agent"""
    type: str
    confidence: float
    reason: str
    proposed_change: Dict


class LearningAgentAutoApply:
    """Auto-apply safe recommendations from learning agent"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def apply_recommendation(
        self,
        user_id: str,
        recommendation: LearningRecommendation,
        user_approval: bool | None = None
    ) -> AppliedRecommendation | None:
        """
        Apply a recommendation if safe to do so.
        
        Args:
            user_id: User to apply to
            recommendation: LearningAgent recommendation
            user_approval: True = user approved, False = user denied, None = check auto-apply
        
        Returns: AppliedRecommendation if applied, None if not applied
        """
        
        safety = RecommendationSafety.categorize(recommendation.type)
        current_config = await self._get_user_config(user_id)
        
        should_auto_apply = (
            user_approval is None and
            RecommendationSafety.can_auto_apply(
                recommendation.type,
                recommendation.confidence,
                safety
            )
        )
        
        if user_approval is False:
            logger.info(f"Recommendation {recommendation.type} denied by user {user_id}")
            return None
        
        if user_approval is None and not should_auto_apply:
            logger.info(f"Recommendation {recommendation.type} requires user approval (confidence={recommendation.confidence})")
            return None
        
        try:
            new_config = await self._apply_config_change(
                user_id,
                current_config,
                recommendation
            )
            
            log_entry = RecommendationApprovalLog(
                user_id=user_id,
                recommendation_type=recommendation.type,
                safety_category=safety.value,
                confidence=recommendation.confidence,
                applied_at=datetime.utcnow(),
                status="APPLIED",
                previous_config=current_config,
                current_config=new_config
            )
            
            self.session.add(log_entry)
            await self.session.commit()
            
            logger.info(
                f"Recommendation applied: user={user_id}, type={recommendation.type}, "
                f"auto={should_auto_apply}, confidence={recommendation.confidence}"
            )
            
            return AppliedRecommendation(
                id=log_entry.id,
                user_id=user_id,
                recommendation_type=recommendation.type,
                safety_category=safety,
                confidence=recommendation.confidence,
                applied_at=log_entry.applied_at,
                applied_automatically=should_auto_apply,
                approved_by=None if should_auto_apply else user_id,
                previous_config=current_config,
                current_config=new_config,
                result_metric=None,
                result_change_percent=None
            )
            
        except Exception as e:
            logger.error(f"Failed to apply recommendation {recommendation.type}: {str(e)}")
            return None
    
    async def _get_user_config(self, user_id: str) -> Dict:
        """Get current trading config for user"""
        
        result = await self.session.execute(
            select(BotConfig).where(BotConfig.user_id == user_id).order_by(desc(BotConfig.id))
        )
        db_config = result.scalar_one_or_none()
        
        if not db_config:
            return {
                "position_size": 1.0,
                "leverage": 1.0,
                "stop_loss_percent": 2.0,
                "take_profit_percent": 5.0,
                "max_daily_loss_percent": 10.0,
                "win_rate_threshold": 0.55,
                "regime_filter_enabled": True,
                "volatility_filter_enabled": True,
            }
        
        return {
            "position_size": getattr(db_config, 'position_size', 1.0),
            "leverage": getattr(db_config, 'leverage', 1.0),
            "stop_loss_percent": getattr(db_config, 'stop_loss_percent', 2.0),
            "take_profit_percent": getattr(db_config, 'take_profit_percent', 5.0),
            "max_daily_loss_percent": getattr(db_config, 'max_daily_loss_percent', 10.0),
            "win_rate_threshold": getattr(db_config, 'win_rate_threshold', 0.55),
            "regime_filter_enabled": getattr(db_config, 'regime_filter_enabled', True),
            "volatility_filter_enabled": getattr(db_config, 'volatility_filter_enabled', True),
        }
    
    async def _apply_config_change(
        self,
        user_id: str,
        current_config: Dict,
        recommendation: LearningRecommendation
    ) -> Dict:
        """Apply configuration change based on recommendation"""
        
        new_config = current_config.copy()
        
        adjustments = {
            "reduce_position_size": lambda: self._reduce_position(new_config),
            "increase_position_size": lambda: self._increase_position(new_config),
            "widen_stop_loss": lambda: self._widen_stop(new_config),
            "tighten_stop_loss": lambda: self._tighten_stop(new_config),
            "increase_win_rate_threshold": lambda: self._increase_wr(new_config),
            "reduce_win_rate_threshold": lambda: self._reduce_wr(new_config),
            "reduce_leverage": lambda: self._reduce_leverage(new_config),
            "increase_leverage": lambda: self._increase_leverage(new_config),
            "enable_regime_filter": lambda: self._enable_regime_filter(new_config),
            "disable_regime_filter": lambda: self._disable_regime_filter(new_config),
        }
        
        if recommendation.type in adjustments:
            adjustments[recommendation.type]()
        
        result = await self.session.execute(
            select(BotConfig).where(BotConfig.user_id == user_id).order_by(desc(BotConfig.id))
        )
        db_config = result.scalar_one_or_none()
        
        if db_config:
            for key, value in new_config.items():
                if hasattr(db_config, key):
                    setattr(db_config, key, value)
            
            await self.session.commit()
        
        return new_config
    
    def _reduce_position(self, config: Dict) -> None:
        config['position_size'] *= 0.8
        config['position_size'] = max(0.1, min(5.0, config['position_size']))
    
    def _increase_position(self, config: Dict) -> None:
        config['position_size'] *= 1.2
        config['position_size'] = max(0.1, min(5.0, config['position_size']))
    
    def _widen_stop(self, config: Dict) -> None:
        config['stop_loss_percent'] *= 1.25
        config['stop_loss_percent'] = min(10.0, config['stop_loss_percent'])
    
    def _tighten_stop(self, config: Dict) -> None:
        config['stop_loss_percent'] *= 0.8
        config['stop_loss_percent'] = max(0.5, config['stop_loss_percent'])
    
    def _increase_wr(self, config: Dict) -> None:
        config['win_rate_threshold'] = min(0.95, config['win_rate_threshold'] + 0.05)
    
    def _reduce_wr(self, config: Dict) -> None:
        config['win_rate_threshold'] = max(0.40, config['win_rate_threshold'] - 0.05)
    
    def _reduce_leverage(self, config: Dict) -> None:
        config['leverage'] *= 0.9
        config['leverage'] = max(1.0, config['leverage'])
    
    def _increase_leverage(self, config: Dict) -> None:
        config['leverage'] *= 1.1
        config['leverage'] = min(20.0, config['leverage'])
    
    def _enable_regime_filter(self, config: Dict) -> None:
        config['regime_filter_enabled'] = True
    
    def _disable_regime_filter(self, config: Dict) -> None:
        config['regime_filter_enabled'] = False
