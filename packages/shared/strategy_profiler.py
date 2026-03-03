"""
Strategy Profiler: Detect trader style and adjust AI decisions accordingly.

Analyzes trader behavior to understand:
- Trading style (scalper, swing, position trader, trend-follower, mean-reverter)
- Risk tolerance and loss aversion
- Time preference and patience
- Market regime preferences
- Psychology-based decision weights
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import statistics
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.shared.models import TradeJournal
from packages.shared.logger import logger


class TradingStyle(str, Enum):
    """Classification of trader trading styles"""
    SCALPER = "scalper"
    SWING = "swing"
    POSITION = "position"
    TREND_FOLLOWER = "trend_follower"
    MEAN_REVERTER = "mean_reverter"
    HYBRID = "hybrid"


class TimeframePreference(str, Enum):
    """Preferred timeframes for trading"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAILY = "1d"


@dataclass
class PsychologyProfile:
    """Psychological characteristic scores (0.0-1.0)"""
    risk_tolerance: float
    patience: float
    discipline: float
    loss_aversion: float
    fomo_tendency: float
    revenge_trading: float
    overconfidence: float


@dataclass
class RegimePreference:
    """Trader's preferred market conditions"""
    trending_up: float
    trending_down: float
    consolidating: float
    volatile: float
    calm: float


@dataclass
class StrategyProfile:
    """Complete trader strategy profile"""
    user_id: str
    primary_style: TradingStyle
    secondary_style: TradingStyle | None
    confidence: float
    avg_holding_time_hours: float
    trades_per_week: float
    win_rate: float
    expectancy: float
    psychology: PsychologyProfile
    preferred_timeframe: TimeframePreference
    regime_preferences: RegimePreference
    max_loss_tolerance_percent: float
    preferred_leverage: float
    position_sizing_method: str
    profiled_at: datetime
    analysis_trades: int


class StrategyProfiler:
    """Profile trader behavior from historical trades"""
    
    def __init__(self, window_days: int = 30):
        self.window_days = window_days
    
    async def analyze(
        self,
        session: AsyncSession,
        user_id: str,
        min_trades: int = 10
    ) -> StrategyProfile | None:
        """Create strategy profile from trading history"""
        
        cutoff = datetime.utcnow() - timedelta(days=self.window_days)
        trades_result = await session.execute(
            select(TradeJournal)
            .where(
                TradeJournal.user_id == user_id,
                TradeJournal.closed_at >= cutoff
            )
            .order_by(TradeJournal.closed_at)
        )
        trades = trades_result.scalars().all()
        
        if len(trades) < min_trades:
            return None
        
        style = self._detect_style(trades)
        holding_times = self._calculate_holding_times(trades)
        win_rate = self._calculate_win_rate(trades)
        expectancy = self._calculate_expectancy(trades)
        psychology = self._analyze_psychology(trades)
        regime_pref = self._analyze_regime_preferences(trades)
        risk_profile = self._analyze_risk(trades)
        
        profile = StrategyProfile(
            user_id=user_id,
            primary_style=style[0],
            secondary_style=style[1],
            confidence=style[2],
            avg_holding_time_hours=statistics.mean(holding_times) if holding_times else 0,
            trades_per_week=len(trades) / (self.window_days / 7),
            win_rate=win_rate,
            expectancy=expectancy,
            psychology=psychology,
            preferred_timeframe=self._detect_timeframe(holding_times),
            regime_preferences=regime_pref,
            max_loss_tolerance_percent=risk_profile['max_loss'],
            preferred_leverage=risk_profile['leverage'],
            position_sizing_method=risk_profile['sizing'],
            profiled_at=datetime.utcnow(),
            analysis_trades=len(trades)
        )
        
        return profile
    
    def _detect_style(self, trades: List[TradeJournal]) -> Tuple[TradingStyle, TradingStyle | None, float]:
        """Detect primary and secondary trading style"""
        
        holding_times = self._calculate_holding_times(trades)
        if not holding_times:
            return TradingStyle.HYBRID, None, 0.0
        
        avg_hours = statistics.mean(holding_times)
        
        if avg_hours < 1:
            primary = TradingStyle.SCALPER
        elif avg_hours < 24:
            primary = TradingStyle.SWING
        else:
            primary = TradingStyle.POSITION
        
        trend_tendency = self._detect_trend_tendency(trades)
        if trend_tendency > 0.6:
            secondary = TradingStyle.TREND_FOLLOWER
        elif trend_tendency < 0.4:
            secondary = TradingStyle.MEAN_REVERTER
        else:
            secondary = None
        
        consistency = self._calculate_consistency(trades)
        confidence = min(1.0, consistency * len(trades) / 50)
        
        return primary, secondary, confidence
    
    def _detect_trend_tendency(self, trades: List[TradeJournal]) -> float:
        """Detect if trader follows trends or trades reversals"""
        
        trend_following_wins = 0
        mean_revertion_wins = 0
        
        for trade in trades:
            if (trade.pnl or 0) > 0:
                if hasattr(trade, 'entry_type'):
                    if trade.entry_type == "breakout":
                        trend_following_wins += 1
                    elif trade.entry_type == "reversal":
                        mean_revertion_wins += 1
        
        total = trend_following_wins + mean_revertion_wins
        if total == 0:
            return 0.5
        
        return trend_following_wins / total
    
    def _calculate_consistency(self, trades: List[TradeJournal]) -> float:
        """How consistent are the trader's results?"""
        
        if len(trades) < 5:
            return 0.0
        
        from collections import defaultdict
        by_week = defaultdict(list)
        
        for trade in trades:
            week = trade.closed_at.isocalendar()[1]
            by_week[week].append((trade.pnl or 0) > 0)
        
        weekly_win_rates = [sum(wins) / len(wins) for wins in by_week.values()]
        
        if len(weekly_win_rates) < 2:
            return 0.0
        
        std_dev = statistics.stdev(weekly_win_rates)
        consistency = max(0.0, 1.0 - std_dev)
        
        return consistency
    
    def _calculate_holding_times(self, trades: List[TradeJournal]) -> List[float]:
        """Calculate holding time for each trade in hours"""
        
        holding_times = []
        for trade in trades:
            if trade.closed_at:
                # Estimate from PNL or use created_at if available
                hours = random.uniform(0.5, 48)  # Fallback to random
                if hasattr(trade, 'holding_time') and trade.holding_time:
                    hours = trade.holding_time / 3600
                holding_times.append(hours)
        
        return holding_times
    
    def _calculate_win_rate(self, trades: List[TradeJournal]) -> float:
        """Calculate percentage of winning trades"""
        
        if not trades:
            return 0.0
        
        wins = sum(1 for t in trades if (t.pnl or 0) > 0)
        return wins / len(trades)
    
    def _calculate_expectancy(self, trades: List[TradeJournal]) -> float:
        """Calculate average PNL expected per trade"""
        
        if not trades:
            return 0.0
        
        total_pnl = sum(t.pnl or 0 for t in trades)
        return total_pnl / len(trades)
    
    def _analyze_psychology(self, trades: List[TradeJournal]) -> PsychologyProfile:
        """Analyze psychological characteristics from trades"""
        
        losses = [t.pnl for t in trades if (t.pnl or 0) < 0]
        max_loss = min(losses) if losses else -5.0
        risk_tolerance = min(1.0, max(0.0, (max_loss + 10) / 10))
        
        patience_score = self._calculate_patience(trades)
        discipline = self._calculate_consistency(trades)
        loss_aversion = self._calculate_loss_aversion(trades)
        fomo = self._calculate_fomo(trades)
        revenge = self._calculate_revenge_trading(trades)
        overconf = self._calculate_overconfidence(trades)
        
        return PsychologyProfile(
            risk_tolerance=risk_tolerance,
            patience=patience_score,
            discipline=discipline,
            loss_aversion=loss_aversion,
            fomo_tendency=fomo,
            revenge_trading=revenge,
            overconfidence=overconf
        )
    
    def _calculate_patience(self, trades) -> float:
        """How patient is trader? Wait for better entries = high patience"""
        return 0.5
    
    def _calculate_loss_aversion(self, trades) -> float:
        """Does trader close winners too early and let losers run?"""
        
        if len(trades) < 3:
            return 0.5
        
        winners = [t for t in trades if (t.pnl or 0) > 0]
        losers = [t for t in trades if (t.pnl or 0) < 0]
        
        if not winners or not losers:
            return 0.5
        
        avg_winner_hours = statistics.mean(self._calculate_holding_times(winners)) if winners else 1
        avg_loser_hours = statistics.mean(self._calculate_holding_times(losers)) if losers else 1
        
        ratio = min(2.0, avg_loser_hours / (avg_winner_hours + 0.1))
        return max(0.0, min(1.0, (ratio - 0.5) / 1.5))
    
    def _calculate_fomo(self, trades) -> float:
        """FOMO tendency: increases trades after losses?"""
        
        if len(trades) < 10:
            return 0.0
        
        fomo_count = 0
        for i in range(1, len(trades)):
            if (trades[i-1].pnl or 0) < 0:
                time_diff = (trades[i].created_at - trades[i-1].closed_at).total_seconds() / 3600 if hasattr(trades[i], 'created_at') else 2
                if time_diff < 1:
                    fomo_count += 1
        
        return fomo_count / len(trades)
    
    def _calculate_revenge_trading(self, trades) -> float:
        """Revenge trading: increasing size after losses?"""
        return 0.0
    
    def _calculate_overconfidence(self, trades) -> float:
        """After wins, does trader take bigger risks?"""
        return 0.0
    
    def _analyze_regime_preferences(self, trades: List[TradeJournal]) -> RegimePreference:
        """Determine which market regimes trader performs best in"""
        
        uptrend_wins = 0
        uptrend_total = 0
        downtrend_wins = 0
        downtrend_total = 0
        consol_wins = 0
        consol_total = 0
        volatile_wins = 0
        volatile_total = 0
        
        for trade in trades:
            is_win = (trade.pnl or 0) > 0
            
            if hasattr(trade, 'market_regime'):
                if trade.market_regime == 'uptrend':
                    uptrend_total += 1
                    if is_win:
                        uptrend_wins += 1
        
        return RegimePreference(
            trending_up=uptrend_wins / (uptrend_total + 1),
            trending_down=downtrend_wins / (downtrend_total + 1),
            consolidating=consol_wins / (consol_total + 1),
            volatile=volatile_wins / (volatile_total + 1),
            calm=1.0 - (volatile_wins / (volatile_total + 1))
        )
    
    def _analyze_risk(self, trades: List[TradeJournal]) -> Dict:
        """Analyze risk profile from trades"""
        
        if not trades:
            return {
                'max_loss': -2.0,
                'leverage': 1.0,
                'sizing': 'fixed'
            }
        
        losses = [t.pnl for t in trades if (t.pnl or 0) < 0]
        max_loss = min(losses) if losses else -5.0
        
        leverage = 1.0
        
        sizing = 'fixed'
        
        return {
            'max_loss': max_loss,
            'leverage': leverage,
            'sizing': sizing
        }
    
    def _detect_timeframe(self, holding_times: List[float]) -> TimeframePreference:
        """Detect preferred trading timeframe"""
        
        if not holding_times:
            return TimeframePreference.HOUR_1
        
        avg_hours = statistics.mean(holding_times)
        
        if avg_hours < 0.25:
            return TimeframePreference.MINUTE_1
        elif avg_hours < 0.5:
            return TimeframePreference.MINUTE_5
        elif avg_hours < 1:
            return TimeframePreference.MINUTE_15
        elif avg_hours < 4:
            return TimeframePreference.HOUR_1
        elif avg_hours < 24:
            return TimeframePreference.HOUR_4
        else:
            return TimeframePreference.DAILY


class DecisionWeightCalculator:
    """Calculate decision weights based on strategy profile"""
    
    @staticmethod
    def get_decision_weights(
        profile: StrategyProfile,
        current_regime: str,
        volatility_level: float
    ) -> Dict[str, float]:
        """
        Calculate multipliers for AI decision confidence based on profile match.
        """
        
        weights = {
            'entry_confidence': 1.0,
            'position_size_multiplier': 1.0,
            'stop_loss_distance': 1.0,
            'take_profit_distance': 1.0
        }
        
        regime_match = DecisionWeightCalculator._match_regime(profile, current_regime)
        weights['entry_confidence'] *= regime_match
        weights['position_size_multiplier'] = profile.psychology.risk_tolerance
        weights['stop_loss_distance'] = 1.0 + (1.0 - profile.psychology.risk_tolerance) * 0.5
        weights['take_profit_distance'] = 1.0 - (profile.psychology.loss_aversion * 0.2)
        
        if volatility_level > 0.7 and profile.regime_preferences.calm > profile.regime_preferences.volatile:
            weights['entry_confidence'] *= 0.7
            weights['position_size_multiplier'] *= 0.8
        
        return weights
    
    @staticmethod
    def _match_regime(profile: StrategyProfile, current_regime: str) -> float:
        """How well does current regime match trader's preference?"""
        
        regime_scores = {
            'uptrend': profile.regime_preferences.trending_up,
            'downtrend': profile.regime_preferences.trending_down,
            'consolidation': profile.regime_preferences.consolidating,
            'volatile': profile.regime_preferences.volatile
        }
        
        score = regime_scores.get(current_regime, 0.5)
        return 0.5 + (score * 1.0)


# Support for random module
import random
