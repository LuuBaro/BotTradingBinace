"""
Phase 6 API Routes - Learning Agent and Trade Journal
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from packages.shared.trade_journal import TradeJournalEntry
from packages.shared.learning_agent import LearningAgent, SuggestedAdaptations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["phase6-learning"])


# Global learning agent instance (in production: use database)
learning_agent = LearningAgent()


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
        # Store to database
        # db.add(TradeJournal(**trade.dict()))
        # db.commit()

        # Add to learning agent
        learning_agent.add_trade(trade)

        logger.info(f"✅ Trade recorded: {trade.trade_id} {trade.symbol} {trade.side} {trade.pnl_pct:+.2%}")

        # Check if we should trigger learning analysis
        if len(learning_agent.trades) % 50 == 0:
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
    # Would query database in production
    trades = learning_agent.trades

    if symbol:
        trades = [t for t in trades if t.symbol == symbol]

    if status == "winner":
        trades = [t for t in trades if t.is_winner]
    elif status == "loser":
        trades = [t for t in trades if not t.is_winner and not t.is_breakeven]

    # Sort by entry time descending
    trades = sorted(trades, key=lambda t: t.entry_time, reverse=True)

    total = len(trades)
    paginated = trades[offset:offset+limit]

    return {
        "trades": [t.dict() for t in paginated],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/trade-journal/{trade_id}")
async def get_trade_details(trade_id: str) -> Dict[str, Any]:
    """Get specific trade details"""
    trade = next((t for t in learning_agent.trades if t.trade_id == trade_id), None)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    return {
        "trade": trade.dict()
    }


@router.get("/trade-journal/stats/summary")
async def get_trade_stats_summary() -> Dict[str, Any]:
    """Get quick summary stats from trades"""
    if not learning_agent.trades:
        return {"message": "No trades yet"}

    winners = sum(1 for t in learning_agent.trades if t.is_winner)
    losers = sum(1 for t in learning_agent.trades if not t.is_winner and not t.is_breakeven)
    total_pnl = sum(t.pnl for t in learning_agent.trades)

    return {
        "total_trades": len(learning_agent.trades),
        "winners": winners,
        "losers": losers,
        "win_rate": winners / len(learning_agent.trades),
        "total_pnl": total_pnl,
        "avg_trade": total_pnl / len(learning_agent.trades)
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
        logger.info(f"Starting manual learning analysis on {len(learning_agent.trades)} trades")

        report = learning_agent.analyze()

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
        if not learning_agent.trades:
            return {"patterns": []}

        report = learning_agent.analyze()

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
        if not learning_agent.trades:
            return {"calibration": []}

        report = learning_agent.analyze()

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
        if not learning_agent.trades or len(learning_agent.trades) < 5:
            return {
                "status": "insufficient_data",
                "trades_recorded": len(learning_agent.trades),
                "needed_for_analysis": 5
            }

        report = learning_agent.analyze()

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
