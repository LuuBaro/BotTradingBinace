"""
Learning Agent - Analyzes trade history and suggests improvements
Auto-adapt with strict constraints (only 3 variables allowed to change)
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from statistics import mean, stdev
from collections import defaultdict

from packages.shared.trade_journal import (
    TradeJournalEntry,
    TradeJournalStats,
    PatternsDiscovered,
    ConfidenceMetrics
)

logger = logging.getLogger(__name__)


class LearningAgent:
    """Analyzes trades and discovers patterns"""

    def __init__(self):
        self.trades: List[TradeJournalEntry] = []

    def add_trade(self, trade: TradeJournalEntry):
        """Add trade to analysis"""
        self.trades.append(trade)

    def analyze(self) -> "LearningReport":
        """Analyze all trades and generate report"""
        if len(self.trades) < 5:
            return self._empty_report("Insufficient trades for analysis (< 5)")

        try:
            # Calculate stats
            stats = self._calculate_stats()

            # Discover patterns
            losing_patterns = self._discover_losing_patterns()

            # Calibrate confidence
            confidence_analysis = self._analyze_confidence_calibration()

            # Generate recommendations
            recommendations = self._generate_recommendations(stats, losing_patterns)

            report = LearningReport(
                analysis_time=datetime.utcnow(),
                trades_analyzed=len(self.trades),
                stats=stats,
                losing_patterns=losing_patterns,
                confidence_calibration=confidence_analysis,
                recommendations=recommendations,
                suggested_adaptations=self._suggest_adaptations(stats, confidence_analysis)
            )

            logger.info(f"✅ Learning report generated: {len(self.trades)} trades analyzed")
            return report

        except Exception as e:
            logger.error(f"❌ Learning analysis failed: {str(e)}")
            return self._empty_report(f"Analysis error: {str(e)}")

    def _calculate_stats(self) -> TradeJournalStats:
        """Calculate comprehensive trade statistics"""
        winners = [t for t in self.trades if t.is_winner]
        losers = [t for t in self.trades if not t.is_winner and not t.is_breakeven]
        breakeven = [t for t in self.trades if t.is_breakeven]

        total_pnl = sum(t.pnl for t in self.trades)
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))

        # Win rate by regime
        win_rate_by_regime = self._win_rate_by_regime()

        # Performance by conditions
        perf_by_vol = self._performance_by_volatility()
        perf_by_spread = self._performance_by_spread()
        perf_by_leverage = self._performance_by_leverage()
        perf_by_time = self._performance_by_time_of_day()

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        # Max drawdown calculation (simplified - consecutive losses)
        max_dd = self._calculate_max_drawdown()

        return TradeJournalStats(
            total_trades=len(self.trades),
            winning_trades=len(winners),
            losing_trades=len(losers),
            breakeven_trades=len(breakeven),
            win_rate=len(winners) / len(self.trades),
            win_rate_by_regime=win_rate_by_regime,
            total_pnl=total_pnl,
            avg_win=mean(t.pnl for t in winners) if winners else 0.0,
            avg_loss=mean(t.pnl for t in losers) if losers else 0.0,
            largest_win=max(t.pnl for t in winners) if winners else 0.0,
            largest_loss=min(t.pnl for t in losers) if losers else 0.0,
            profit_factor=profit_factor,
            max_drawdown=max_dd,
            max_consecutive_losses=self._max_consecutive_losses(),
            max_consecutive_wins=self._max_consecutive_wins(),
            avg_holding_time_minutes=mean(t.holding_time_minutes for t in self.trades),
            avg_rr_ratio=mean(t.risk_reward_ratio for t in self.trades),
            best_regime=max(win_rate_by_regime, key=win_rate_by_regime.get) if win_rate_by_regime else None,
            worst_regime=min(win_rate_by_regime, key=win_rate_by_regime.get) if win_rate_by_regime else None,
            performance_by_volatility=perf_by_vol,
            performance_by_spread=perf_by_spread,
            performance_by_leverage=perf_by_leverage,
            performance_by_time_of_day=perf_by_time
        )

    def _win_rate_by_regime(self) -> Dict[str, float]:
        """Calculate win rate for each regime"""
        by_regime = defaultdict(list)
        for trade in self.trades:
            by_regime[trade.market_regime].append(trade.is_winner)

        return {
            regime: sum(wins) / len(wins) if wins else 0.0
            for regime, wins in by_regime.items()
        }

    def _performance_by_volatility(self) -> Dict[str, Dict[str, Any]]:
        """Analyze performance at different volatility levels"""
        ranges = [
            ("Very Low", 0, 25),
            ("Low", 25, 50),
            ("Medium", 50, 75),
            ("High", 75, 100)
        ]

        results = {}
        for name, low, high in ranges:
            trades_in_range = [
                t for t in self.trades
                if low <= t.volatility_percentile < high
            ]
            if trades_in_range:
                winners = sum(1 for t in trades_in_range if t.is_winner)
                results[name] = {
                    "count": len(trades_in_range),
                    "win_rate": winners / len(trades_in_range),
                    "avg_pnl": mean(t.pnl for t in trades_in_range)
                }

        return results

    def _performance_by_spread(self) -> Dict[str, Dict[str, Any]]:
        """Analyze performance at different spread levels"""
        # Group by spread ranges
        low_spread = [t for t in self.trades if t.bid_ask_spread_pips < 1]
        med_spread = [t for t in self.trades if 1 <= t.bid_ask_spread_pips < 5]
        high_spread = [t for t in self.trades if t.bid_ask_spread_pips >= 5]

        results = {}
        for name, group in [("Tight (<1)", low_spread), ("Medium (1-5)", med_spread), ("Wide (>=5)", high_spread)]:
            if group:
                winners = sum(1 for t in group if t.is_winner)
                results[name] = {
                    "count": len(group),
                    "win_rate": winners / len(group),
                    "avg_pnl": mean(t.pnl for t in group)
                }

        return results

    def _performance_by_leverage(self) -> Dict[str, Dict[str, Any]]:
        """Analyze performance at different leverage levels"""
        by_leverage = defaultdict(list)
        for trade in self.trades:
            key = f"{int(trade.entry_leverage)}x"
            by_leverage[key].append(trade)

        results = {}
        for leverage, trades_at_lev in sorted(by_leverage.items()):
            winners = sum(1 for t in trades_at_lev if t.is_winner)
            results[leverage] = {
                "count": len(trades_at_lev),
                "win_rate": winners / len(trades_at_lev),
                "avg_pnl": mean(t.pnl for t in trades_at_lev)
            }

        return results

    def _performance_by_time_of_day(self) -> Dict[str, Dict[str, Any]]:
        """Analyze performance by hour of day"""
        by_hour = defaultdict(list)
        for trade in self.trades:
            hour = trade.entry_time.hour
            by_hour[hour].append(trade)

        results = {}
        for hour in range(24):
            if hour in by_hour:
                trades = by_hour[hour]
                winners = sum(1 for t in trades if t.is_winner)
                results[f"{hour:02d}:00"] = {
                    "count": len(trades),
                    "win_rate": winners / len(trades),
                    "avg_pnl": mean(t.pnl for t in trades)
                }

        return results

    def _max_consecutive_losses(self) -> int:
        """Calculate longest losing streak"""
        max_streak = 0
        current_streak = 0

        for trade in sorted(self.trades, key=lambda t: t.entry_time):
            if not trade.is_winner and not trade.is_breakeven:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    def _max_consecutive_wins(self) -> int:
        """Calculate longest winning streak"""
        max_streak = 0
        current_streak = 0

        for trade in sorted(self.trades, key=lambda t: t.entry_time):
            if trade.is_winner:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown %"""
        if not self.trades:
            return 0.0

        cumulative_pnl = 0.0
        peak = 0.0
        max_dd = 0.0

        for trade in sorted(self.trades, key=lambda t: t.entry_time):
            cumulative_pnl += trade.pnl
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = ((peak - cumulative_pnl) / abs(peak)) * 100 if peak != 0 else 0
            max_dd = max(max_dd, drawdown)

        return max_dd

    def _discover_losing_patterns(self) -> List[PatternsDiscovered]:
        """Discover patterns in losing trades"""
        losers = [t for t in self.trades if not t.is_winner and not t.is_breakeven]
        if not losers:
            return []

        patterns = []

        # Pattern 1: High volatility trades
        high_vol_losers = [t for t in losers if t.volatility_percentile < 40]
        if len(high_vol_losers) >= 3:
            patterns.append(PatternsDiscovered(
                pattern_name="bien_dong_thap",
                description="Thua lỗ tập trung khi biến động thị trường thấp (< 40th percentile)",
                occurrences=len(high_vol_losers),
                avg_loss_when_triggered=mean(t.pnl for t in high_vol_losers),
                conditions={"volatility_percentile": "<40"},
                recommendation="Tránh hoặc giảm khối lượng giao dịch khi biến động thấp"
            ))

        # Pattern 2: Wide spreads
        wide_spread_losers = [t for t in losers if t.bid_ask_spread_pips >= 5]
        if len(wide_spread_losers) >= 3:
            patterns.append(PatternsDiscovered(
                pattern_name="spread_rong",
                description="Thua lỗ tập trung khi mức chênh lệch giá (spread) lớn (>= 5 pips)",
                occurrences=len(wide_spread_losers),
                avg_loss_when_triggered=mean(t.pnl for t in wide_spread_losers),
                conditions={"bid_ask_spread_pips": ">=5"},
                recommendation="Bỏ qua giao dịch khi spread > 5 pips để tránh trượt giá"
            ))

        # Pattern 3: High leverage
        high_lev_losers = [t for t in losers if t.entry_leverage > 5]
        if len(high_lev_losers) >= 3:
            win_rate_high_lev = sum(1 for t in [tr for tr in self.trades if tr.entry_leverage > 5] if tr.is_winner) / len([t for t in self.trades if t.entry_leverage > 5])
            patterns.append(PatternsDiscovered(
                pattern_name="rui_ro_don_bay_cao",
                description="Tỷ lệ thắng thấp hơn khi sử dụng đòn bẩy cao (> 5x)",
                occurrences=len(high_lev_losers),
                avg_loss_when_triggered=mean(t.pnl for t in high_lev_losers),
                conditions={"entry_leverage": ">5"},
                recommendation="Giảm đòn bẩy hoặc siết chặt điểm dừng lỗ (SL) khi dùng đòn bẩy > 5x"
            ))

        # Pattern 4: Certain regimes
        by_regime_losers = defaultdict(list)
        for trade in losers:
            by_regime_losers[trade.market_regime].append(trade)

        for regime, regime_losers in by_regime_losers.items():
            regime_losses = [t for t in self.trades if t.market_regime == regime]
            if len(regime_losers) >= 3 and len(regime_losses) >= 5:
                win_rate = sum(1 for t in regime_losses if t.is_winner) / len(regime_losses)
                if win_rate < 0.4:
                    patterns.append(PatternsDiscovered(
                        pattern_name=f"hieu_suat_kem_{regime}",
                        description=f"Tỷ lệ thắng chỉ đạt {win_rate:.1%} trong trạng thái thị trường '{regime}'",
                        occurrences=len(regime_losers),
                        avg_loss_when_triggered=mean(t.pnl for t in regime_losers),
                        conditions={"market_regime": regime},
                        recommendation=f"Cẩn trọng hơn hoặc tạm dừng giao dịch khi thị trường ở trạng thái '{regime}'"
                    ))

        # Pattern 5: Time of day
        by_hour_losers = defaultdict(list)
        for trade in losers:
            by_hour_losers[trade.entry_time.hour].append(trade)

        for hour, hour_losers in by_hour_losers.items():
            hour_trades = [t for t in self.trades if t.entry_time.hour == hour]
            if len(hour_losers) >= 2 and len(hour_trades) >= 5:
                win_rate = sum(1 for t in hour_trades if t.is_winner) / len(hour_trades)
                if win_rate < 0.35:
                    patterns.append(PatternsDiscovered(
                        pattern_name=f"hieu_suat_kem_gio_{hour:02d}",
                        description=f"Hieu suất kém vào lúc {hour:02d}:00 UTC (Tỷ lệ thắng {win_rate:.1%})",
                        occurrences=len(hour_losers),
                        avg_loss_when_triggered=mean(t.pnl for t in hour_losers),
                        conditions={"entry_hour": hour},
                        recommendation=f"Tránh giao dịch quanh khung giờ {hour:02d}:00 UTC"
                    ))

        return patterns[:5]  # Return top 5 patterns

    def _analyze_confidence_calibration(self) -> List[ConfidenceMetrics]:
        """Analyze how well AI confidence predicts actual results"""
        buckets = [
            ("0.5-0.6", 0.5, 0.6),
            ("0.6-0.7", 0.6, 0.7),
            ("0.7-0.8", 0.7, 0.8),
            ("0.8-0.9", 0.8, 0.9),
            ("0.9-1.0", 0.9, 1.0)
        ]

        metrics = []
        for bucket_name, low, high in buckets:
            trades_in_bucket = [
                t for t in self.trades
                if low <= t.confidence < high
            ]
            if trades_in_bucket:
                winners = sum(1 for t in trades_in_bucket if t.is_winner)
                metrics.append(ConfidenceMetrics(
                    confidence_bucket=bucket_name,
                    count=len(trades_in_bucket),
                    win_rate_in_bucket=winners / len(trades_in_bucket),
                    avg_pnl_in_bucket=mean(t.pnl for t in trades_in_bucket)
                ))

        return metrics

    def _generate_recommendations(
        self,
        stats: TradeJournalStats,
        patterns: List[PatternsDiscovered]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Win rate too low
        if stats.win_rate < 0.5:
            recommendations.append(f"Tỷ lệ thắng đang thấp ({stats.win_rate:.1%}). Cần xem lại logic vào lệnh.")

        # Profile factor poor
        if stats.profit_factor < 1.5:
            recommendations.append(f"Hệ số lợi nhuận {stats.profit_factor:.2f} cho thấy nhiều lệnh lỗ nhỏ. Hãy siết chặt quy tắc entry.")

        # Too many consecutive losses
        if stats.max_consecutive_losses > 5:
            recommendations.append(f"Phát hiện chuỗi {stats.max_consecutive_losses} lệnh lỗ liên tiếp. Xem xét tạm nghỉ (cooldown).")

        # Large drawdown
        if stats.max_drawdown > 10.0:
            recommendations.append(f"Mức sụt giảm vốn {stats.max_drawdown:.1f}% khá cao. Giảm khối lượng hoặc siết chặt rủi ro.")

        # Add pattern-based recommendations
        for pattern in patterns[:3]:
            recommendations.append(f"Tín hiệu: {pattern.recommendation}")

        return recommendations

    def _suggest_adaptations(self, stats: TradeJournalStats, confidence_calibration: List[ConfidenceMetrics]) -> "SuggestedAdaptations":
        """Suggest safe auto-adapt changes (only 3 allowed variables)"""
        adaptations = SuggestedAdaptations()

        # 1. Size multiplier: reduce if drawdown high, increase if win rate good
        if stats.max_drawdown > 15.0:
            adaptations.size_multiplier = 0.8  # Reduce positions by 20%
            adaptations.size_multiplier_reason = f"Mức sụt giảm vốn {stats.max_drawdown:.1f}% quá cao"
        elif stats.win_rate > 0.65 and stats.profit_factor > 2.0:
            adaptations.size_multiplier = 1.1  # Increase positions by 10%
            adaptations.size_multiplier_reason = "Tỷ lệ thắng và Profit Factor mạnh"

        # 2. Confidence scaling: lower if actual results don't match confidence levels
        if confidence_calibration:
            # Look for high confidence bucket performance
            high_conf_metric = next((m for m in confidence_calibration if m.confidence_bucket in ["0.8-0.9", "0.9-1.0"]), None)
            high_conf_wr = high_conf_metric.win_rate_in_bucket if high_conf_metric else 0.5
            
            if high_conf_wr < 0.55:
                adaptations.confidence_scaling = 0.9  # Require 10% higher confidence
                adaptations.confidence_scaling_reason = "Các lệnh độ tin cậy cao có hiệu suất thấp"
            elif high_conf_wr > 0.75:
                adaptations.confidence_scaling = 1.1  # Allow 10% lower confidence
                adaptations.confidence_scaling_reason = "Các lệnh độ tin cậy cao có hiệu suất tốt"

        # 3. Cooldown after loss: add if many consecutive losses
        if stats.max_consecutive_losses > 3:
            adaptations.cooldown_after_loss_minutes = 30 * stats.max_consecutive_losses
            adaptations.cooldown_after_loss_reason = f"Phát hiện chuỗi {stats.max_consecutive_losses} lệnh lỗ liên tiếp"

        adaptations.enabled = bool(
            adaptations.size_multiplier != 1.0 or
            adaptations.confidence_scaling != 1.0 or
            adaptations.cooldown_after_loss_minutes > 0
        )

        return adaptations

    def _empty_report(self, reason: str) -> "LearningReport":
        """Generate empty report with reason"""
        return LearningReport(
            analysis_time=datetime.utcnow(),
            trades_analyzed=len(self.trades),
            stats=None,
            losing_patterns=[],
            confidence_calibration=[],
            recommendations=[reason],
            suggested_adaptations=SuggestedAdaptations(),
            error=reason
        )


class SuggestedAdaptations:
    """Safe auto-adapt suggestions (only 3 allowed variables)"""

    def __init__(self):
        # Only these 3 can be changed
        self.size_multiplier: float = 1.0  # 0.8 = 20% smaller, 1.2 = 20% larger
        self.size_multiplier_reason: str = ""

        self.confidence_scaling: float = 1.0  # 0.9 = require 10% higher confidence, 1.1 = allow 10% lower
        self.confidence_scaling_reason: str = ""

        self.cooldown_after_loss_minutes: int = 0  # Minutes to wait after loss
        self.cooldown_after_loss_reason: str = ""

        # These are NEVER changed by auto-adapt
        # - max_leverage
        # - stop_loss_logic
        # - symbols
        # - entry_conditions

        self.enabled: bool = False
        self.last_updated: Optional[datetime] = None

        # Audit trail
        self.previous_values: Dict[str, Any] = {}
        self.applied_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage/API"""
        strategies = []
        if self.size_multiplier != 1.0:
            strategies.append({
                "title": f"Điều chỉnh khối lượng ({int(self.size_multiplier * 100)}%)",
                "detail": self.size_multiplier_reason or "Tối ưu hóa quy mô vị thế dựa trên tỷ lệ thắng gần đây."
            })
        if self.confidence_scaling != 1.0:
            strategies.append({
                "title": f"Siết chặt lọc tín hiệu (x{self.confidence_scaling})",
                "detail": self.confidence_scaling_reason or "Nâng cao tiêu chuẩn vào lệnh để tránh các tín hiệu gây nhiễu."
            })
        if self.cooldown_after_loss_minutes > 0:
            strategies.append({
                "title": f"Thời gian chờ sau lỗ ({self.cooldown_after_loss_minutes}p)",
                "detail": self.cooldown_after_loss_reason or "Tạm dừng để tránh giao dịch theo cảm xúc và bình ổn tâm lý hệ thống."
            })

        return {
            "size_multiplier": self.size_multiplier,
            "size_multiplier_reason": self.size_multiplier_reason,
            "confidence_scaling": self.confidence_scaling,
            "confidence_scaling_reason": self.confidence_scaling_reason,
            "cooldown_after_loss_minutes": self.cooldown_after_loss_minutes,
            "cooldown_after_loss_reason": self.cooldown_after_loss_reason,
            "enabled": self.enabled,
            "strategies": strategies,
            "previous_values": self.previous_values,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None
        }

    def apply_to_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply adaptations to current config"""
        if not self.enabled:
            return config

        adapted = config.copy()

        # Apply size multiplier
        if self.size_multiplier != 1.0:
            self.previous_values["max_position_pct"] = adapted.get("max_position_pct", 5.0)
            adapted["max_position_pct"] = adapted.get("max_position_pct", 5.0) * self.size_multiplier

        # Apply confidence scaling
        if self.confidence_scaling != 1.0:
            self.previous_values["min_confidence"] = adapted.get("min_confidence", 0.7)
            adapted["min_confidence"] = adapted.get("min_confidence", 0.7) * self.confidence_scaling

        # Apply cooldown
        if self.cooldown_after_loss_minutes > 0:
            self.previous_values["cooldown_after_loss"] = 0
            adapted["cooldown_after_loss_minutes"] = self.cooldown_after_loss_minutes

        self.applied_at = datetime.utcnow()
        return adapted


class LearningReport:
    """Complete learning analysis report"""

    def __init__(
        self,
        analysis_time: datetime,
        trades_analyzed: int,
        stats: Optional[TradeJournalStats],
        losing_patterns: List[PatternsDiscovered],
        confidence_calibration: List[ConfidenceMetrics],
        recommendations: List[str],
        suggested_adaptations: SuggestedAdaptations,
        error: Optional[str] = None
    ):
        self.analysis_time = analysis_time
        self.trades_analyzed = trades_analyzed
        self.stats = stats
        self.losing_patterns = losing_patterns
        self.confidence_calibration = confidence_calibration
        self.recommendations = recommendations
        self.suggested_adaptations = suggested_adaptations
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict"""
        return {
            "analysis_time": self.analysis_time.isoformat() + "Z",
            "trades_analyzed": self.trades_analyzed,
            "stats": self.stats.dict() if self.stats else None,
            "losing_patterns": [p.dict() for p in self.losing_patterns],
            "confidence_calibration": [c.dict() for c in self.confidence_calibration],
            "recommendations": self.recommendations,
            "suggested_adaptations": self.suggested_adaptations.to_dict(),
            "error": self.error
        }

    def to_json(self) -> str:
        """Serialize to JSON"""
        import json
        return json.dumps(
            self.to_dict(),
            indent=2,
            default=str
        )
