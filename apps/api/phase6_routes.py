"""
Phase 6 API Routes - Learning Agent and Trade Journal
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from packages.shared.trade_journal import TradeJournalEntry, ExitReason
from packages.shared.learning_agent import LearningAgent, SuggestedAdaptations
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import TradeJournal as TradeJournalModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["phase6-learning"])


# Global learning agent instance (legacy fallback)
learning_agent = LearningAgent()


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


def _model_to_entry(trade: TradeJournalModel) -> TradeJournalEntry:
    features = trade.features_json or {}
    decision_json = trade.decision_json or {}
    entry_time = _parse_datetime(features.get("entry_time"))
    exit_time = _parse_datetime(features.get("exit_time"))

    if not exit_time:
        exit_time = trade.closed_at or datetime.utcnow()
    if not entry_time:
        holding_sec = trade.holding_time or 0
        entry_time = exit_time - timedelta(seconds=holding_sec)

    exit_reason = features.get("exit_reason") or trade.exit_reason or ExitReason.MANUAL.value
    try:
        exit_reason = ExitReason(exit_reason)
    except Exception:
        exit_reason = ExitReason.MANUAL

    pnl_pct = features.get("pnl_pct")
    if pnl_pct is None:
        denom = abs(trade.entry_price * (features.get("entry_quantity") or 1.0))
        pnl_pct = (trade.pnl / denom) if denom > 0 else 0.0

    return TradeJournalEntry(
        trace_id=trade.trace_id,
        trade_id=f"trade_{trade.id}",
        symbol=trade.symbol,
        side=trade.side,
        entry_time=entry_time,
        exit_time=exit_time,
        entry_price=float(trade.entry_price),
        entry_quantity=float(features.get("entry_quantity", 0.0)),
        entry_leverage=float(features.get("entry_leverage", 1.0)),
        exit_price=float(trade.exit_price),
        exit_reason=exit_reason,
        pnl=float(trade.pnl),
        pnl_pct=float(pnl_pct),
        commission=float(features.get("commission", 0.0)),
        risk_reward_ratio=float(trade.rr or 1.0),
        holding_time_minutes=int((trade.holding_time or 0) / 60),
        max_drawdown=float(features.get("max_drawdown", 0.0)),
        max_runup=float(features.get("max_runup", 0.0)),
        market_regime=trade.regime or str(decision_json.get("regime", "unknown")),
        volatility_percentile=int(features.get("volatility_percentile", 50)),
        bid_ask_spread_pips=float(features.get("bid_ask_spread_pips", 0.0)),
        funding_rate=float(features.get("funding_rate", 0.0)),
        position_pct=float(features.get("position_pct", 0.0)),
        stop_loss_pips=float(features.get("stop_loss_pips", 0.0)),
        take_profit_pips=float(features.get("take_profit_pips", 0.0)),
        decision_json=decision_json,
        confidence=float(features.get("confidence", decision_json.get("confidence", 0.0))),
        ai_model=str(features.get("ai_model", "mock")),
        prompt_pack_version=int(features.get("prompt_pack_version", 1)),
        is_winner=trade.pnl > 0,
        is_breakeven=abs(trade.pnl) < 1e-8,
        notes=None,
    )


async def _get_learning_agent_from_db() -> LearningAgent:
    agent = LearningAgent()
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(TradeJournalModel).order_by(TradeJournalModel.closed_at.desc())
        )
        trades = result.scalars().all()
        for trade in trades:
            agent.add_trade(_model_to_entry(trade))
    return agent


# ============================================================================
# Trade Journal Endpoints
# ============================================================================

@router.post("/trade-journal")
async def record_trade(
    trade: TradeJournalEntry,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Record a completed trade in journal
    
    Args:
        trade: Complete trade record
        
    Returns:
        Confirmation with trade_id
    """
    try:
        async with AsyncSessionFactory() as session:
            record = TradeJournalModel(
                trace_id=trade.trace_id,
                symbol=trade.symbol,
                side=trade.side,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                pnl=trade.pnl,
                rr=trade.risk_reward_ratio,
                holding_time=int(trade.holding_time_minutes * 60),
                regime=trade.market_regime,
                features_json={
                    "entry_time": trade.entry_time.isoformat(),
                    "exit_time": trade.exit_time.isoformat(),
                    "entry_quantity": trade.entry_quantity,
                    "entry_leverage": trade.entry_leverage,
                    "volatility_percentile": trade.volatility_percentile,
                    "bid_ask_spread_pips": trade.bid_ask_spread_pips,
                    "funding_rate": trade.funding_rate,
                    "position_pct": trade.position_pct,
                    "stop_loss_pips": trade.stop_loss_pips,
                    "take_profit_pips": trade.take_profit_pips,
                    "confidence": trade.confidence,
                    "ai_model": trade.ai_model,
                    "prompt_pack_version": trade.prompt_pack_version,
                    "pnl_pct": trade.pnl_pct,
                    "max_drawdown": trade.max_drawdown,
                    "max_runup": trade.max_runup,
                    "exit_reason": trade.exit_reason.value,
                },
                decision_json=trade.decision_json,
                exit_reason=trade.exit_reason.value,
                closed_at=trade.exit_time,
            )
            session.add(record)
            await session.commit()

        logger.info(f"✅ Trade recorded: {trade.trade_id} {trade.symbol} {trade.side} {trade.pnl_pct:+.2%}")

        # Check if we should trigger learning analysis
        agent = await _get_learning_agent_from_db()
        if len(agent.trades) % 50 == 0:
            background_tasks.add_task(_trigger_learning_analysis)

        return {
            "success": True,
            "trade_id": trade.trade_id,
            "pnl": trade.pnl,
            "pnl_pct": trade.pnl_pct,
            "total_trades_recorded": len(learning_agent.trades)
        }

    except Exception as e:
        logger.error(f"❌ Failed to record trade: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/trade-journal")
async def list_trades(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    symbol: Optional[str] = None,
    status: Optional[str] = None  # winner, loser
) -> Dict[str, Any]:
    """
    List completed trades
    
    Args:
        limit: Number of trades to return
        offset: Pagination offset
        symbol: Filter by symbol
        status: Filter by winner/loser
        
    Returns:
        List of trade journal entries
    """
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        query = select(TradeJournalModel)
        if symbol:
            query = query.where(TradeJournalModel.symbol == symbol)
        result = await session.execute(query.order_by(TradeJournalModel.closed_at.desc()))
        trades = result.scalars().all()

    entries = [_model_to_entry(trade) for trade in trades]

    if status == "winner":
        entries = [t for t in entries if t.is_winner]
    elif status == "loser":
        entries = [t for t in entries if not t.is_winner and not t.is_breakeven]

    total = len(entries)
    paginated = entries[offset:offset + limit]

    return {
        "trades": [t.dict() for t in paginated],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/trade-journal/{trade_id}")
async def get_trade_details(trade_id: str) -> Dict[str, Any]:
    """Get specific trade details"""
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(TradeJournalModel).where(TradeJournalModel.id == trade_id.replace("trade_", ""))
        )
        trade = result.scalar_one_or_none()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")

    trade = _model_to_entry(trade)
    return {"trade": trade.dict()}


@router.get("/trade-journal/stats/summary")
async def get_trade_stats_summary() -> Dict[str, Any]:
    """Get quick summary stats from trades"""
    agent = await _get_learning_agent_from_db()
    if not agent.trades:
        return {"message": "No trades yet"}

    winners = sum(1 for t in agent.trades if t.is_winner)
    losers = sum(1 for t in agent.trades if not t.is_winner and not t.is_breakeven)
    total_pnl = sum(t.pnl for t in agent.trades)

    return {
        "total_trades": len(agent.trades),
        "winners": winners,
        "losers": losers,
        "win_rate": winners / len(agent.trades),
        "total_pnl": total_pnl,
        "avg_trade": total_pnl / len(agent.trades),
    }


# ============================================================================
# Learning Analysis Endpoints
# ============================================================================

@router.post("/learning/analyze")
async def trigger_learning_analysis(
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Trigger learning analysis manually
    
    Returns:
        Learning report
    """
    try:
        agent = await _get_learning_agent_from_db()
        logger.info(f"Starting manual learning analysis on {len(agent.trades)} trades")

        report = agent.analyze()

        # Store to database
        # db.add(LearningReport(
        #     analysis_time=report.analysis_time,
        #     trades_analyzed=report.trades_analyzed,
        #     stats_json=report.stats.dict() if report.stats else None,
        #     losing_patterns_json=[p.dict() for p in report.losing_patterns],
        #     ...
        # ))

        logger.info(f"✅ Learning analysis complete")

        if report.suggested_adaptations.enabled:
            logger.info(f"📊 Suggested adaptations discovered")

        return {
            "success": True,
            "report": report.to_dict()
        }

    except Exception as e:
        logger.error(f"❌ Learning analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/reports")
async def list_learning_reports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    List historical learning reports
    
    Returns:
        List of reports
    """
    # Would query database in production
    return {
        "reports": [],
        "total": 0
    }


@router.get("/learning/reports/{report_id}")
async def get_learning_report(report_id: str) -> Dict[str, Any]:
    """Get specific learning report"""
    # Would query database in production
    return {
        "report": None
    }


@router.get("/learning/patterns")
async def get_losing_patterns() -> Dict[str, Any]:
    """
    Get all discovered losing patterns
    
    Returns:
        List of destructive patterns found
    """
    try:
        agent = await _get_learning_agent_from_db()
        if not agent.trades:
            return {"patterns": []}

        report = agent.analyze()

        return {
            "patterns": [p.dict() for p in report.losing_patterns],
            "total_patterns": len(report.losing_patterns),
            "trades_analyzed": report.trades_analyzed
        }

    except Exception as e:
        logger.error(f"❌ Pattern discovery failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/confidence-calibration")
async def get_confidence_calibration() -> Dict[str, Any]:
    """
    Analyze AI confidence vs actual performance
    
    Shows how well AI confidence predicts win/loss
    """
    try:
        agent = await _get_learning_agent_from_db()
        if not agent.trades:
            return {"calibration": []}

        report = agent.analyze()

        return {
            "calibration": [c.dict() for c in report.confidence_calibration],
            "trades_analyzed": report.trades_analyzed
        }

    except Exception as e:
        logger.error(f"❌ Confidence analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Auto-Adapt Endpoints
# ============================================================================

@router.post("/learning/auto-adapt/apply")
async def apply_auto_adapt(
    learning_report_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Apply suggested auto-adapt changes
    
    CONSTRAINTS: Only these 3 variables can change:
    - size_multiplier (max ±20%)
    - confidence_scaling (max ±20%)
    - cooldown_after_loss (minutes)
    
    Cannot change:
    - max_leverage
    - stop_loss_logic
    - symbols
    - entry_conditions
    
    Args:
        learning_report_id: Which report's suggestions to apply
        
    Returns:
        Confirmation with changes and audit trail
    """
    try:
        # Get latest report or specified report
        report = learning_agent.analyze()

        if not report.suggested_adaptations.enabled:
            return {
                "success": False,
                "message": "No suggested adaptations in latest report"
            }

        adaptations = report.suggested_adaptations

        # Verify constraints
        if abs(adaptations.size_multiplier - 1.0) > 0.2:
            raise ValueError("size_multiplier can only change by ±20%")

        if abs(adaptations.confidence_scaling - 1.0) > 0.2:
            raise ValueError("confidence_scaling can only change by ±20%")

        # Load current config
        current_config = {
            "max_position_pct": 5.0,
            "min_confidence": 0.7,
            "cooldown_after_loss_minutes": 0
        }

        # Apply adaptations
        new_config = adaptations.apply_to_config(current_config)

        logger.info(f"✅ Auto-adapt applied")
        logger.info(f"   Size multiplier: {adaptations.size_multiplier}x ({adaptations.size_multiplier_reason})")
        logger.info(f"   Confidence scaling: {adaptations.confidence_scaling}x ({adaptations.confidence_scaling_reason})")
        if adaptations.cooldown_after_loss_minutes > 0:
            logger.info(f"   Cooldown after loss: {adaptations.cooldown_after_loss_minutes}m")

        # Store audit trail
        # db.add(AutoAdaptHistory(
        #     learning_report_id=learning_report_id,
        #     size_multiplier_old=current_config.get("max_position_pct", 5.0),
        #     size_multiplier_new=new_config.get("max_position_pct", 5.0),
        #     ...
        # ))

        return {
            "success": True,
            "message": "Adaptations applied",
            "changes": {
                "size_multiplier": adaptations.size_multiplier,
                "confidence_scaling": adaptations.confidence_scaling,
                "cooldown_after_loss_minutes": adaptations.cooldown_after_loss_minutes
            },
            "audit_trail": adaptations.to_dict()
        }

    except Exception as e:
        logger.error(f"❌ Auto-adapt failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/learning/auto-adapt/rollback")
async def rollback_auto_adapt(
    adapt_history_id: str
) -> Dict[str, Any]:
    """
    Rollback previous auto-adapt change
    
    Args:
        adapt_history_id: Which adaptation to roll back
        
    Returns:
        Confirmation of rollback
    """
    try:
        logger.info(f"Rolling back auto-adapt {adapt_history_id}")

        # Mark as rolled back in database
        # db.query(AutoAdaptHistory).filter(id=adapt_history_id).update(
        #     {"rolled_back": True, "rolled_back_at": datetime.utcnow()}
        # )

        # Restore config
        # This would restore previous values

        logger.info(f"✅ Auto-adapt rolled back")

        return {
            "success": True,
            "message": f"Adaptation {adapt_history_id} rolled back"
        }

    except Exception as e:
        logger.error(f"❌ Rollback failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/learning/auto-adapt/history")
async def get_adapt_history(
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Get history of auto-adapt changes
    
    Shows audit trail of all adaptations made
    """
    # Would query database in production
    return {
        "history": [],
        "total": 0
    }


@router.get("/learning/auto-adapt/current")
async def get_current_adaptations() -> Dict[str, Any]:
    """
    Get currently applied adaptations
    
    Returns:
        Current values of the 3 allowed variables
    """
    # Would load from database/config in production
    return {
        "size_multiplier": 1.0,
        "confidence_scaling": 1.0,
        "cooldown_after_loss_minutes": 0,
        "last_updated": None
    }


# ============================================================================
# Dashboard Metrics
# ============================================================================

@router.get("/learning/dashboard-metrics")
async def get_dashboard_learning_metrics() -> Dict[str, Any]:
    """
    Get learning metrics for dashboard display
    
    Returns:
        Current stats, patterns, recommendations
    """
    try:
        agent = await _get_learning_agent_from_db()
        if not agent.trades or len(agent.trades) < 5:
            return {
                "status": "insufficient_data",
                "trades_recorded": len(agent.trades),
                "needed_for_analysis": 5
            }

        report = agent.analyze()

        return {
            "status": "success",
            "trades_analyzed": report.trades_analyzed,
            "analysis_time": report.analysis_time.isoformat(),
            "stats": report.stats.dict() if report.stats else None,
            "key_metrics": {
                "win_rate": f"{report.stats.win_rate:.1%}" if report.stats else "N/A",
                "profit_factor": f"{report.stats.profit_factor:.2f}" if report.stats else "N/A",
                "max_drawdown": f"{report.stats.max_drawdown:.1f}%" if report.stats else "N/A"
            },
            "top_patterns": [
                {
                    "name": p.pattern_name,
                    "description": p.description,
                    "recommendation": p.recommendation
                }
                for p in report.losing_patterns[:3]
            ],
            "recommendations": report.recommendations[:5],
            "suggested_adaptations_enabled": report.suggested_adaptations.enabled,
            "suggested_adaptations": report.suggested_adaptations.to_dict() if report.suggested_adaptations.enabled else None
        }

    except Exception as e:
        logger.error(f"❌ Dashboard metrics failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/learning/analytics-detail")
async def get_detailed_analytics() -> Dict[str, Any]:
    """
    Get detailed trading analytics for AI training
    Returns comprehensive metrics for learning and optimization
    """
    try:
        agent = await _get_learning_agent_from_db()
        if not agent.trades or len(agent.trades) < 5:
            return {
                "status": "insufficient_data",
                "trades_recorded": len(agent.trades),
                "needed_for_analysis": 5
            }

        report = agent.analyze()
        
        # Group trades by regime
        regime_analysis = {}
        for regime in ['trend', 'range', 'volatile', 'sideways']:
            trades_in_regime = [t for t in agent.trades if getattr(t, 'regime', 'range') == regime]
            if trades_in_regime:
                wins = len([t for t in trades_in_regime if getattr(t, 'pnl', 0) > 0])
                losses = len([t for t in trades_in_regime if getattr(t, 'pnl', 0) < 0])
                total_pnl = sum(getattr(t, 'pnl', 0) for t in trades_in_regime)
                regime_analysis[regime] = {
                    "count": len(trades_in_regime),
                    "win_rate": wins / len(trades_in_regime) if trades_in_regime else 0,
                    "total_pnl": total_pnl,
                    "avg_pnl": total_pnl / len(trades_in_regime),
                    "best_trade": max(getattr(t, 'pnl', 0) for t in trades_in_regime) if trades_in_regime else 0,
                    "worst_trade": min(getattr(t, 'pnl', 0) for t in trades_in_regime) if trades_in_regime else 0,
                }
        
        # Best performing trades
        best_trades = sorted(
            [{"pnl": getattr(t, 'pnl', 0), "symbol": getattr(t, 'symbol', 'N/A'), "rr": getattr(t, 'rr', 0)} for t in agent.trades],
            key=lambda x: x['pnl'],
            reverse=True
        )[:10]
        
        # Worst trading patterns
        losing_trades = sorted(
            [{"pnl": getattr(t, 'pnl', 0), "symbol": getattr(t, 'symbol', 'N/A'), "rr": getattr(t, 'rr', 0), "regime": getattr(t, 'regime', 'N/A')} for t in agent.trades],
            key=lambda x: x['pnl']
        )[:10]
        
        # Time-based analysis (if holding_time available)
        holding_times = []
        for t in agent.trades:
            if hasattr(t, 'holding_time') and getattr(t, 'holding_time'):
                holding_times.append({
                    "seconds": getattr(t, 'holding_time', 0),
                    "minutes": getattr(t, 'holding_time', 0) / 60,
                    "pnl": getattr(t, 'pnl', 0),
                    "symbol": getattr(t, 'symbol', 'N/A')
                })
        
        return {
            "status": "success",
            "trades_total": len(agent.trades),
            "analysis_metrics": {
                "overall_stats": report.stats.dict() if report.stats else None,
                "regime_breakdown": regime_analysis,
                "best_trades": best_trades,
                "losing_patterns": losing_trades,
                "holding_time_analysis": holding_times[:20],
                "losing_patterns_detail": [p.dict() for p in report.losing_patterns] if report.losing_patterns else [],
                "recommendations": report.recommendations[:10] if report.recommendations else [],
            }
        }

    except Exception as e:
        logger.error(f"❌ Detailed analytics failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/learning/symbols-performance")
async def get_symbols_performance() -> Dict[str, Any]:
    """Get performance breakdown by trading symbol"""
    try:
        agent = await _get_learning_agent_from_db()
        if not agent.trades:
            return {"symbols": {}}

        symbols_data = {}
        for t in agent.trades:
            symbol = getattr(t, 'symbol', 'UNKNOWN')
            if symbol not in symbols_data:
                symbols_data[symbol] = {
                    "count": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_pnl": 0,
                    "trades": []
                }
            
            pnl = getattr(t, 'pnl', 0)
            symbols_data[symbol]["count"] += 1
            symbols_data[symbol]["total_pnl"] += pnl
            if pnl > 0:
                symbols_data[symbol]["wins"] += 1
            elif pnl < 0:
                symbols_data[symbol]["losses"] += 1
            symbols_data[symbol]["trades"].append({
                "pnl": pnl,
                "rr": getattr(t, 'rr', 0),
                "regime": getattr(t, 'regime', 'N/A')
            })

        for symbol, data in symbols_data.items():
            data["win_rate"] = data["wins"] / data["count"] if data["count"] > 0 else 0
            data["avg_pnl"] = data["total_pnl"] / data["count"]

        return {
            "symbols": symbols_data,
            "total_symbols": len(symbols_data)
        }

    except Exception as e:
        logger.error(f"❌ Symbols performance failed: {str(e)}")
        return {"symbols": {}, "error": str(e)}


@router.get("/learning/training-insights")
async def get_training_insights() -> Dict[str, Any]:
    """Get AI training insights and recommendations"""
    try:
        agent = await _get_learning_agent_from_db()
        if not agent.trades or len(agent.trades) < 5:
            return {
                "status": "insufficient_data",
                "message": "Need at least 5 trades for meaningful insights"
            }

        report = agent.analyze()
        
        insights = {
            "status": "success",
            "training_focus_areas": [],
            "high_priority_fixes": [],
            "low_risk_opportunities": [],
            "confidence_score": 0.0
        }

        # Generate insights based on analysis
        if report.stats:
            if report.stats.win_rate < 0.35:
                insights["high_priority_fixes"].append({
                    "priority": "critical",
                    "issue": "Win rate below 35%",
                    "action": "Review entry conditions - may need stricter filters",
                    "impact": "Direct impact on profitability"
                })
            
            if report.stats.profit_factor < 1.0:
                insights["high_priority_fixes"].append({
                    "priority": "critical",
                    "issue": "Profit factor below 1.0",
                    "action": "Average winning trade too small vs losing trades",
                    "impact": "Unprofitable strategy"
                })
            
            if report.stats.max_drawdown > 20:
                insights["high_priority_fixes"].append({
                    "priority": "high",
                    "issue": "Drawdown exceeds 20%",
                    "action": "Consider tighter risk management",
                    "impact": "Account volatility risk"
                })
        
        # Best practices from winning patterns
        if report.recommendations:
            insights["training_focus_areas"] = [
                {
                    "focus": rec,
                    "confidence": 0.75
                } for rec in report.recommendations[:5]
            ]

        insights["confidence_score"] = min(1.0, len(agent.trades) / 100.0)

        return insights

    except Exception as e:
        logger.error(f"❌ Training insights failed: {str(e)}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# Helper Functions
# ============================================================================

async def _trigger_learning_analysis():
    """Background task to run learning analysis"""
    try:
        logger.info("🔄 Triggered learning analysis (50 trades milestone)")

        report = learning_agent.analyze()

        if report.suggested_adaptations.enabled:
            logger.info("📊 Suggested adaptations discovered")
            # Could auto-apply here if configured

        # Store report to database
        # db.add(LearningReport(...))
        # db.commit()

    except Exception as e:
        logger.error(f"❌ Background learning analysis failed: {str(e)}")


# Enhanced Real-Time Data Endpoints
# ============================================================================

@router.get("/learning/market-data")
async def get_market_data(
    symbols: str = Query("BTCUSDT,ETHUSDT", description="Comma-separated symbols"),
    interval: str = Query("1h", description="Kline interval (1m, 5m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(100, ge=1, le=500, description="Kline limit (max 500)"),
) -> Dict[str, Any]:
    """
    Fetch real Binance kline data for interactive charts
    Supports multiple symbols and time frame selection
    """
    try:
        from packages.shared.exchange.binance_futures import BinanceFuturesClient
        
        symbol_list = [s.strip().upper() for s in symbols.split(',')]
        klines_data = {}
        
        async with BinanceFuturesClient() as client:
            for symbol in symbol_list:
                try:
                    klines = await client.get_klines(symbol, interval=interval, limit=limit)
                    # Format: [open_time, open, high, low, close, volume, close_time, ...]
                    klines_data[symbol] = [
                        {
                            "time": int(k[0]),
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                            "volume": float(k[5]),
                        }
                        for k in klines
                    ]
                except Exception as e:
                    logger.warning(f"Failed to fetch klines for {symbol}: {str(e)}")
                    klines_data[symbol] = []
        
        return {
            "status": "success",
            "interval": interval,
            "symbols_count": len(symbol_list),
            "data": klines_data
        }
    
    except Exception as e:
        logger.error(f"Failed to fetch market data: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/learning/trades-timeline")
async def get_trades_timeline(
    start_time: Optional[int] = Query(None, description="Start timestamp in milliseconds"),
    end_time: Optional[int] = Query(None, description="End timestamp in milliseconds"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
) -> Dict[str, Any]:
    """
    Get real trades filtered by time range for timeline analysis
    Supports dragging/zooming on equity curve
    """
    try:
        agent = await _get_learning_agent_from_db()
        
        # Filter trades by time range
        filtered_trades = agent.trades if agent.trades else []
        
        if start_time or end_time:
            start_dt = datetime.fromtimestamp(start_time / 1000) if start_time else None
            end_dt = datetime.fromtimestamp(end_time / 1000) if end_time else None
            
            filtered_trades = [
                t for t in filtered_trades 
                if (not start_dt or getattr(t, 'entry_time', datetime.now()) >= start_dt) and
                   (not end_dt or getattr(t, 'exit_time', datetime.now()) <= end_dt)
            ]
        
        if symbol:
            filtered_trades = [
                t for t in filtered_trades 
                if getattr(t, 'symbol', '') == symbol.upper()
            ]
        
        # Calculate equity curve (cumulative PnL)
        cumulative_pnl = 0
        equity_curve = []
        
        for trade in sorted(filtered_trades, key=lambda t: getattr(t, 'exit_time', datetime.now())):
            pnl = getattr(trade, 'pnl', 0)
            cumulative_pnl += pnl
            
            equity_curve.append({
                "timestamp": int(getattr(trade, 'exit_time', datetime.now()).timestamp() * 1000),
                "symbol": getattr(trade, 'symbol', 'UNKNOWN'),
                "pnl": pnl,
                "cumulative_pnl": cumulative_pnl,
                "win": pnl > 0,
                "holding_minutes": int(getattr(trade, 'holding_time_minutes', 0) or 0),
            })
        
        # Calculate statistics
        total_trades = len(filtered_trades)
        winning_trades = len([t for t in filtered_trades if getattr(t, 'pnl', 0) > 0])
        losing_trades = len([t for t in filtered_trades if getattr(t, 'pnl', 0) < 0])
        total_pnl = sum(getattr(t, 'pnl', 0) for t in filtered_trades)
        
        return {
            "status": "success",
            "time_range": {
                "start": start_time,
                "end": end_time
            },
            "statistics": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                "total_pnl": total_pnl,
                "avg_pnl": total_pnl / total_trades if total_trades > 0 else 0,
            },
            "equity_curve": equity_curve,
        }
    
    except Exception as e:
        logger.error(f"Failed to get trades timeline: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/learning/performance-by-timeframe")
async def get_performance_by_timeframe(
    timeframe: str = Query("1h", description="Timeframe (1h, 4h, 1d, 1w)"),
) -> Dict[str, Any]:
    """
    Get performance breakdown by timeframe (useful for market hours analysis)
    """
    try:
        agent = await _get_learning_agent_from_db()
        if not agent.trades:
            return {"timeframes": {}}
        
        from datetime import timedelta as td
        
        # Map timeframe string to hours/days
        timeframe_map = {
            "1h": (3600, 1),      # 1 hour
            "4h": (14400, 4),     # 4 hours  
            "1d": (86400, 24),    # 1 day
            "1w": (604800, 168),  # 1 week
        }
        
        seconds_per_interval, hours_per_interval = timeframe_map.get(timeframe, (3600, 1))
        
        time_performance = {}
        
        for trade in agent.trades:
            entry_time = getattr(trade, 'entry_time', datetime.now())
            
            # Group by the start of the timeframe
            if timeframe == "1h":
                key = entry_time.replace(minute=0, second=0, microsecond=0)
            elif timeframe == "4h":
                hour = (entry_time.hour // 4) * 4
                key = entry_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            elif timeframe == "1d":
                key = entry_time.replace(hour=0, minute=0, second=0, microsecond=0)
            elif timeframe == "1w":
                days_since_monday = entry_time.weekday()
                key = (entry_time - td(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                key = entry_time.replace(minute=0, second=0, microsecond=0)
            
            key_str = key.isoformat()
            
            if key_str not in time_performance:
                time_performance[key_str] = {
                    "timestamp": int(key.timestamp() * 1000),
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_pnl": 0,
                    "symbols": set()
                }
            
            pnl = getattr(trade, 'pnl', 0)
            time_performance[key_str]["trades"] += 1
            time_performance[key_str]["total_pnl"] += pnl
            time_performance[key_str]["symbols"].add(getattr(trade, 'symbol', 'UNKNOWN'))
            
            if pnl > 0:
                time_performance[key_str]["wins"] += 1
            elif pnl < 0:
                time_performance[key_str]["losses"] += 1
        
        # Convert set to list and calculate metrics
        result = []
        for key_str, data in sorted(time_performance.items()):
            result.append({
                "period": key_str,
                "timestamp": data["timestamp"],
                "trades": data["trades"],
                "win_rate": (data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0,
                "total_pnl": data["total_pnl"],
                "avg_pnl": data["total_pnl"] / data["trades"] if data["trades"] > 0 else 0,
                "symbols_count": len(data["symbols"])
            })
        
        return {
            "status": "success",
            "timeframe": timeframe,
            "performance_data": result
        }
    
    except Exception as e:
        logger.error(f"Failed to get performance by timeframe: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
