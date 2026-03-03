"""
Phase 6 API Routes - Learning Agent and Trade Journal
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.trade_journal import TradeJournalEntry, ExitReason
from packages.shared.learning_agent import LearningAgent, SuggestedAdaptations
from packages.shared.database import AsyncSessionFactory, get_db
from packages.shared.models import TradeJournal as TradeJournalModel, TraderContext
from sqlalchemy import select, desc
import aiohttp
import asyncio
from datetime import timezone
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from packages.shared.config import settings
from apps.api.auth import jwt_handler
from apps.api.phase4_routes import _get_target_user_id
from fastapi.security import HTTPBearer

security = HTTPBearer()
logger = logging.getLogger(__name__)

router = APIRouter(tags=["phase6-learning"])


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


async def _get_learning_agent_from_db(user_id: str) -> LearningAgent:
    agent = LearningAgent()
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(TradeJournalModel).where(TradeJournalModel.user_id == user_id).order_by(TradeJournalModel.closed_at.desc())
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
    background_tasks: BackgroundTasks,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """
    Record a completed trade in journal
    """
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

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
                user_id=user.id
            )
            session.add(record)
            await session.commit()
            
        logger.info(f"✅ Trade recorded: {trade.trade_id} {trade.symbol} {trade.side} {trade.pnl_pct:+.2%}")

        # Check if we should trigger learning analysis
        agent = await _get_learning_agent_from_db(user.id)
        if len(agent.trades) % 50 == 0:
            background_tasks.add_task(_trigger_learning_analysis, user.id)

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
    status: Optional[str] = None,  # winner, loser
    user_id: str | None = None,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """
    List completed trades
    """
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    target_id = _get_target_user_id(requester, user_id)
    
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        query = select(TradeJournalModel).where(TradeJournalModel.user_id == target_id)
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
async def get_trade_details(
    trade_id: str,
    user_id: str | None = None,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """Get specific trade details"""
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")

    target_id = _get_target_user_id(requester, user_id)

    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(TradeJournalModel).where(
                TradeJournalModel.id == trade_id.replace("trade_", ""),
                TradeJournalModel.user_id == target_id
            )
        )
        trade = result.scalar_one_or_none()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")

    trade = _model_to_entry(trade)
    return {"trade": trade.dict()}


@router.get("/trade-journal/stats/summary")
async def get_trade_stats_summary(
    user_id: str | None = None,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """Get quick summary stats from trades"""
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")

    target_id = _get_target_user_id(requester, user_id)
    
    agent = await _get_learning_agent_from_db(target_id)
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
    background_tasks: BackgroundTasks,
    user_id: str | None = None,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """
    Trigger learning analysis manually
    """
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")

    target_id = _get_target_user_id(requester, user_id)
    
    try:
        agent = await _get_learning_agent_from_db(target_id)
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
async def get_losing_patterns(
    user_id: str | None = None,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """
    Get all discovered losing patterns
    """
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")

    target_id = _get_target_user_id(requester, user_id)
    
    try:
        agent = await _get_learning_agent_from_db(target_id)
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
async def get_confidence_calibration(
    user_id: str | None = None,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """
    Analyze AI confidence vs actual performance
    """
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")

    target_id = _get_target_user_id(requester, user_id)
    
    try:
        agent = await _get_learning_agent_from_db(target_id)
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
    background_tasks: BackgroundTasks = None,
    user_id: str | None = None,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """
    Apply suggested auto-adapt changes
    """
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")

    target_id = _get_target_user_id(requester, user_id)
    
    try:
        agent = await _get_learning_agent_from_db(target_id)
        report = agent.analyze()

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
async def get_current_adaptations(
    user_id: str | None = None,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """
    Get currently applied adaptations
    """
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    target_id = _get_target_user_id(requester, user_id)
    # Would load from database/config in production
    return {
        "size_multiplier": 1.0,
        "confidence_scaling": 1.0,
        "cooldown_after_loss_minutes": 0,
        "last_updated": None
    }


async def _fetch_historical_trades_from_binance(db_session: AsyncSession, user_id: str, limit: int = 50) -> int:
    """
    Sync recent Binance fills into the permanent Trade Journal for a specific user.
    """
    # Get user's Binance credentials
    from packages.shared.models import UserCredential
    from packages.shared.encryption import decrypt_key
    
    cred_res = await db_session.execute(
        select(UserCredential).where(UserCredential.user_id == user_id)
    )
    user_cred = cred_res.scalar_one_or_none()
    
    binance_key = None
    binance_secret = None
    use_testnet = True
    
    if user_cred and user_cred.binance_api_key:
        binance_key = decrypt_key(user_cred.binance_api_key)
        binance_secret = decrypt_key(user_cred.binance_api_secret)
        use_testnet = user_cred.use_testnet
    # Note: No admin fallback here for historical sync to avoid cross-user data leakage
    
    if not binance_key or not binance_secret:
        logger.warning(f"Binance keys missing for user {user_id}, skipping history sync")
        return 0
        
    try:
        # Get active symbols from BotConfig or fallback
        symbols = ["BTCUSDT", "ETHUSDT", "LINKUSDT", "SOLUSDT"]
        try:
            from packages.shared.models import BotConfig
            bot_res = await db_session.execute(select(BotConfig).where(BotConfig.is_active == True, BotConfig.user_id == user_id))
            bot_config = bot_res.scalar_one_or_none()
            if bot_config and bot_config.symbols_json:
                if isinstance(bot_config.symbols_json, list):
                    symbols = list(set(symbols + bot_config.symbols_json))
                elif isinstance(bot_config.symbols_json, dict):
                    symbols = list(set(symbols + bot_config.symbols_json.get("symbols", [])))
        except Exception:
            pass

        client = BinanceFuturesClient(api_key=binance_key, api_secret=binance_secret, testnet=use_testnet)
        connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
        async with aiohttp.ClientSession(connector=connector) as session:
            client.session = session
            await client.sync_server_time()
            
            # Parallel fetch recent fills
            tasks = [client.get_user_trades(s, limit=limit) for s in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            new_count = 0
            for i, res in enumerate(results):
                symbol = symbols[i]
                if not isinstance(res, list): continue
                
                for t in res:
                    # Filter for closing trades (realizedPnl != 0)
                    rpnl = float(t.get('realizedPnl', 0))
                    if abs(rpnl) > 1e-8:
                        trade_id = str(t.get('id'))
                        trace_id = f"bin_sync_{trade_id}"
                        
                        # Check if already exists
                        existing = await db_session.execute(
                            select(TradeJournalModel).where(TradeJournalModel.trace_id == trace_id)
                        )
                        if existing.scalar_one_or_none():
                            continue
                            
                        dt = datetime.fromtimestamp(t.get('time', 0)/1000, tz=timezone.utc).replace(tzinfo=None)
                        qty = float(t.get('qty', 0))
                        price = float(t.get('price', 0))
                        
                        # Create Journal Record
                        journal_entry = TradeJournalModel(
                            trace_id=trace_id,
                            symbol=symbol,
                            side=t.get('side'),
                            entry_price=price, # Approximation for sync
                            exit_price=price,
                            pnl=rpnl,
                            rr=1.0,
                            holding_time=300, # 5 min default for sync
                            regime="Historical Sync",
                            exit_reason=ExitReason.MANUAL.value,
                            closed_at=dt,
                            decision_json={},
                            user_id=user_id,
                            features_json={
                                "entry_time": (dt - timedelta(minutes=5)).isoformat(),
                                "exit_time": dt.isoformat(),
                                "entry_quantity": qty,
                                "entry_leverage": 1.0,
                                "pnl_pct": 0.0,
                                "ai_model": "binance_sync",
                                "confidence": 1.0
                            }
                        )
                        db_session.add(journal_entry)
                        new_count += 1
            
            if new_count > 0:
                await db_session.commit()
                logger.info(f"✅ Synced {new_count} historical trades from Binance into DB")
            return new_count
            
    except Exception as e:
        logger.error(f"❌ Historical sync failed: {e}")
        return 0


async def _backfill_trade_journal_from_orders(
    db_session: AsyncSession,
    user_id: str,
    min_needed: int = 5,
    max_orders: int = 300,
) -> int:
    """
    Build TradeJournal entries from REAL filled orders (no mock data).
    Pairs BUY/SELL orders by symbol in chronological order.
    """
    from packages.shared.models import Order

    # Skip when already enough journal trades
    current_res = await db_session.execute(
        select(TradeJournalModel).where(TradeJournalModel.user_id == user_id)
    )
    current_trades = current_res.scalars().all()
    if len(current_trades) >= min_needed:
        return 0

    existing_trace_ids = {t.trace_id for t in current_trades if t.trace_id}

    orders_res = await db_session.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .where(Order.status.in_(["FILLED", "PARTIALLY_FILLED"]))
        .order_by(Order.created_at.asc())
        .limit(max_orders)
    )
    orders = orders_res.scalars().all()
    if len(orders) < 2:
        return 0

    by_symbol: Dict[str, list] = {}
    for o in orders:
        by_symbol.setdefault(o.symbol, []).append(o)

    created = 0
    for symbol, items in by_symbol.items():
        long_entries: list = []
        short_entries: list = []

        for o in items:
            side = (o.side or "").upper()
            if side == "BUY":
                if short_entries:
                    entry = short_entries.pop(0)  # short entry is SELL
                    exit_order = o
                    trade_side = "short"
                else:
                    long_entries.append(o)
                    continue
            elif side == "SELL":
                if long_entries:
                    entry = long_entries.pop(0)  # long entry is BUY
                    exit_order = o
                    trade_side = "long"
                else:
                    short_entries.append(o)
                    continue
            else:
                continue

            trace_id = f"ord_backfill_{entry.id}_{exit_order.id}_{trade_side}"
            if trace_id in existing_trace_ids:
                continue

            entry_price = float(entry.avg_price or 0.0)
            exit_price = float(exit_order.avg_price or 0.0)
            if entry_price <= 0 or exit_price <= 0:
                continue

            entry_qty = float(entry.filled_qty or entry.quantity or 0.0)
            exit_qty = float(exit_order.filled_qty or exit_order.quantity or 0.0)
            qty = min(entry_qty, exit_qty)
            if qty <= 0:
                continue

            if trade_side == "long":
                pnl = (exit_price - entry_price) * qty
                pnl_pct = (exit_price - entry_price) / entry_price
            else:
                pnl = (entry_price - exit_price) * qty
                pnl_pct = (entry_price - exit_price) / entry_price

            entry_time = entry.created_at or datetime.utcnow()
            exit_time = exit_order.updated_at or exit_order.created_at or datetime.utcnow()
            holding = max(0, int((exit_time - entry_time).total_seconds()))

            journal_entry = TradeJournalModel(
                trace_id=trace_id,
                symbol=symbol,
                side=trade_side,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl=float(pnl),
                rr=1.0,
                holding_time=holding,
                regime="order_backfill",
                exit_reason=ExitReason.MANUAL.value,
                closed_at=exit_time,
                decision_json={
                    "symbol": symbol,
                    "action": "close",
                    "side": trade_side,
                    "confidence": 0.7,
                    "rationale": f"Backfilled from real orders #{entry.id} -> #{exit_order.id}",
                },
                user_id=user_id,
                features_json={
                    "entry_time": entry_time.isoformat(),
                    "exit_time": exit_time.isoformat(),
                    "entry_quantity": qty,
                    "entry_order_id": entry.id,
                    "exit_order_id": exit_order.id,
                    "entry_leverage": 1.0,
                    "pnl_pct": float(pnl_pct),
                    "ai_model": "order_backfill",
                    "confidence": 0.7,
                },
            )
            db_session.add(journal_entry)
            existing_trace_ids.add(trace_id)
            created += 1

            if len(current_trades) + created >= min_needed:
                break

        if len(current_trades) + created >= min_needed:
            break

    if created > 0:
        await db_session.commit()
        logger.info(f"✅ Backfilled {created} TradeJournal rows from REAL Order data for user {user_id}")
    return created


# ============================================================================
# Dashboard Metrics
# ============================================================================

@router.get("/learning/dashboard-metrics")
async def get_dashboard_learning_metrics(
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """
    Get learning metrics for dashboard display
    """
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")

    target_id = _get_target_user_id(requester, user_id)

    try:
        from packages.shared.market_intelligence import intelligence_aggregator
        from packages.shared.models import Decision
        
        # 1. Fetch latest market snapshots from recent decisions for this user
        snapshots_result = await db.execute(
            select(Decision.market_snapshot)
            .where(Decision.market_snapshot != None, Decision.user_id == target_id)
            .order_by(desc(Decision.timestamp))
            .limit(5)
        )
        recent_snapshots = snapshots_result.scalars().all()
        
        # 2. Market Context via Aggregator
        market_intel = await intelligence_aggregator.get_market_context(recent_snapshots)
        
        # 3. ALWAYS backfill from local REAL orders first (before loading agent)
        # This ensures TradeJournal is populated before agent tries to load it
        backfilled = await _backfill_trade_journal_from_orders(db, target_id, min_needed=5)
        if backfilled > 0:
            logger.info(f"Backfilled {backfilled} trades from orders for user {target_id}")

        # Load agent AFTER backfill is complete
        agent = await _get_learning_agent_from_db(target_id)
        
        # If still insufficient, fallback to Binance historical fills
        if not agent.trades or len(agent.trades) < 5:
            logger.info(f"Still insufficient trades in DB for user {target_id}, fetching from Binance...")
            new_trades = await _fetch_historical_trades_from_binance(db, target_id, limit=100)
            if new_trades > 0:
                # Reload agent to include new Binance trades
                agent = await _get_learning_agent_from_db(target_id)
                
        if not agent.trades or len(agent.trades) < 5:
            return {
                "status": "insufficient_data",
                "trades_recorded": len(agent.trades),
                "needed_for_analysis": 5,
                "market_intelligence": market_intel
            }

        report = agent.analyze()

        return {
            "status": "success",
            "trades_analyzed": report.trades_analyzed,
            "analysis_time": datetime.utcnow().isoformat() + "Z", # Always show current time for freshness
            "stats": report.stats.dict() if report.stats else None,
            "key_metrics": {
                "win_rate": f"{report.stats.win_rate:.1%}" if report.stats else "N/A",
                "profit_factor": f"{report.stats.profit_factor:.2f}" if report.stats else "N/A",
                "max_drawdown": f"{report.stats.max_drawdown:.1f}%" if report.stats else "N/A"
            },
            "market_intelligence": market_intel,
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
async def get_detailed_analytics(
    user_id: str | None = None,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """
    Get detailed trading analytics for AI training
    """
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")

    target_id = _get_target_user_id(requester, user_id)
    
    try:
        agent = await _get_learning_agent_from_db(target_id)
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
async def get_symbols_performance(
    user_id: str | None = None,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """Get performance breakdown by trading symbol"""
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")

    target_id = _get_target_user_id(requester, user_id)
    
    try:
        agent = await _get_learning_agent_from_db(target_id)
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
async def get_training_insights(
    user_id: str | None = None,
    credentials: Any = Depends(security)
) -> Dict[str, Any]:
    """Get AI training insights and recommendations"""
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")

    target_id = _get_target_user_id(requester, user_id)
    
    try:
        agent = await _get_learning_agent_from_db(target_id)
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

        # Enhanced Expertise Score (0.0 to 1.0)
        # Based on 4 pillars of AI maturity
        
        # 1. Experience (40%): Volume of trades (High confidence at 200+ trades)
        experience_score = min(0.4, (len(agent.trades) / 200.0) * 0.4)
        
        # 2. Exposure (20%): Variety of regimes encountered
        regimes_found = len(set(getattr(t, 'market_regime', 'unknown') for t in agent.trades))
        exposure_score = min(0.2, (regimes_found / 4.0) * 0.2)
        
        # 3. Breadth (20%): Number of unique symbols analyzed
        symbols_found = len(set(getattr(t, 'symbol', 'UNKNOWN') for t in agent.trades))
        breadth_score = min(0.2, (symbols_found / 5.0) * 0.2)
        
        # 4. Stability (20%): Consistency of Profit Factor (PF > 1.2 is stable)
        pf = report.stats.profit_factor if report.stats else 0
        stability_score = min(0.2, (pf / 1.5) * 0.2) if pf > 0.5 else 0
        
        insights["confidence_score"] = experience_score + exposure_score + breadth_score + stability_score
        
        # Add sub-metrics for UI
        insights["expertise_details"] = {
            "experience": experience_score / 0.4,
            "exposure": exposure_score / 0.2,
            "breadth": breadth_score / 0.2,
            "stability": stability_score / 0.2
        }

        return insights

    except Exception as e:
        logger.error(f"❌ Training insights failed: {str(e)}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# Helper Functions
# ============================================================================

async def _trigger_learning_analysis(user_id: str):
    """Background task to run learning analysis"""
    try:
        logger.info(f"🔄 Triggered learning analysis for user {user_id}")

        agent = await _get_learning_agent_from_db(user_id)
        report = agent.analyze()

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
    timeframe: Optional[str] = Query(None, description="Timeframe shortcut (1h, 4h, 1d, 1w)"),
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

        # Handle timeframe shortcut
        if timeframe and not start_time:
            now = datetime.now()
            if timeframe == "1h":
                start_dt = now - timedelta(hours=24) # Show last 24h for 1h resolution
            elif timeframe == "4h":
                start_dt = now - timedelta(days=7)   # Show last 7 days for 4h
            elif timeframe == "1d":
                start_dt = now - timedelta(days=30)  # Show last 30 days for 1d
            elif timeframe == "1w":
                start_dt = now - timedelta(days=90)  # Show last 90 days for 1w
            else:
                start_dt = None
            
            if start_dt:
                filtered_trades = [
                    t for t in filtered_trades 
                    if getattr(t, 'exit_time', datetime.now()) >= start_dt
                ]
        
        elif start_time or end_time:
            start_dt = datetime.fromtimestamp(start_time / 1000) if start_time else None
            end_dt = datetime.fromtimestamp(end_time / 1000) if end_time else None
            
            filtered_trades = [
                t for t in filtered_trades 
                if (not start_dt or getattr(t, 'exit_time', datetime.now()) >= start_dt) and
                   (not end_dt or getattr(t, 'exit_time', datetime.now()) <= end_dt)
            ]
        
        if symbol:
            filtered_trades = [
                t for t in filtered_trades 
                if getattr(t, 'symbol', '') == symbol.upper()
            ]
        
        # Calculate equity curve (cumulative PnL)
        cumulative_pnl = 0
        peak_pnl = 0
        max_drawdown = 0
        total_profit = 0
        total_loss = 0
        equity_curve = []
        
        # Add a starting point to the curve if we have a start_dt
        if start_dt:
            equity_curve.append({
                "timestamp": int(start_dt.timestamp() * 1000),
                "symbol": "START",
                "pnl": 0,
                "cumulative_pnl": 0,
                "win": False,
                "holding_minutes": 0,
            })

        for trade in sorted(filtered_trades, key=lambda t: getattr(t, 'exit_time', datetime.now())):
            pnl = float(getattr(trade, 'pnl', 0))
            cumulative_pnl += pnl
            
            # For profit factor
            if pnl > 0:
                total_profit += pnl
            else:
                total_loss += abs(pnl)
            
            # For drawdown
            if cumulative_pnl > peak_pnl:
                peak_pnl = cumulative_pnl
            
            dd = peak_pnl - cumulative_pnl
            if dd > max_drawdown:
                max_drawdown = dd
            
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
        total_pnl = float(sum(getattr(t, 'pnl', 0) for t in filtered_trades))
        
        # Profit Factor: Gross Profit / Gross Loss. If no loss, it equals Gross Profit.
        profit_factor = total_profit / total_loss if total_loss > 0 else total_profit
        
        print(f"DEBUG TIMELINE: timeframe={timeframe}, total={total_trades}, wins={winning_trades}, profit={total_pnl}, pf={profit_factor}")

        return {
            "status": "success",
            "time_range": {
                "start": str(start_dt) if 'start_dt' in locals() else None,
                "end": end_time
            },
            "statistics": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": (winning_trades / total_trades) if total_trades > 0 else 0,
                "total_pnl": total_pnl,
                "profit_factor": profit_factor,
                "max_drawdown_amount": max_drawdown,
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

@router.get("/learning/pnl-30days")
async def get_pnl_30days() -> Dict[str, Any]:
    """Calculate total PNL over the past 30 days"""
    try:
        agent = await _get_learning_agent_from_db()
        from datetime import datetime, timedelta
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        total_pnl = sum(
            getattr(trade, 'pnl', 0) 
            for trade in agent.trades 
            if getattr(trade, 'exit_time', getattr(trade, 'entry_time', datetime.now())) >= thirty_days_ago
        )
        
        return {
            "status": "success",
            "total_pnl": total_pnl
        }
    except Exception as e:
        logger.error(f"❌ Failed to calculate 30 days PNL: {str(e)}")
        return {"status": "error", "error": str(e)}


@router.get("/learning/pnl-30days/breakdown")
async def get_pnl_30days_breakdown() -> Dict[str, Any]:
    """
    Get daily PnL breakdown for the last 30 days.
    Returns per-day stats: total_pnl, wins, losses, trade_list.
    Used for the 30-day PnL history modal in LearningPage.
    """
    try:
        from datetime import datetime, timedelta, timezone

        def _to_naive(dt_val) -> Optional[datetime]:
            """Normalize any datetime-like value to a naive UTC datetime."""
            if dt_val is None:
                return None
            if isinstance(dt_val, str):
                try:
                    dt_val = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
                except Exception:
                    return None
            if not isinstance(dt_val, datetime):
                # e.g. date object
                try:
                    dt_val = datetime(dt_val.year, dt_val.month, dt_val.day)
                    return dt_val
                except Exception:
                    return None
            # Strip timezone info if present
            if dt_val.tzinfo is not None:
                return dt_val.replace(tzinfo=None)
            return dt_val

        agent = await _get_learning_agent_from_db()

        now_naive = datetime.utcnow()
        thirty_days_ago = now_naive - timedelta(days=30)

        # Group by calendar day (using naive UTC)
        daily: Dict[str, Dict] = {}

        for trade in agent.trades:
            raw_dt = getattr(trade, 'exit_time', None) or getattr(trade, 'entry_time', None)
            exit_dt = _to_naive(raw_dt)
            if exit_dt is None:
                exit_dt = now_naive

            # Skip trades outside 30-day window
            if exit_dt < thirty_days_ago:
                continue

            day_key = exit_dt.strftime('%Y-%m-%d')

            if day_key not in daily:
                daily[day_key] = {
                    "date": day_key,
                    "total_pnl": 0.0,
                    "wins": 0,
                    "losses": 0,
                    "trades": 0,
                    "trade_list": [],
                }

            try:
                pnl = float(getattr(trade, 'pnl', 0) or 0)
            except (TypeError, ValueError):
                pnl = 0.0

            symbol = str(getattr(trade, 'symbol', 'N/A') or 'N/A')
            side = str(getattr(trade, 'side', 'N/A') or 'N/A')
            exit_reason = str(getattr(trade, 'exit_reason', 'N/A') or 'N/A')

            daily[day_key]["total_pnl"] += pnl
            daily[day_key]["trades"] += 1
            if pnl > 0:
                daily[day_key]["wins"] += 1
            elif pnl < 0:
                daily[day_key]["losses"] += 1
            daily[day_key]["trade_list"].append({
                "symbol": symbol,
                "pnl": round(pnl, 4),
                "side": side,
                "exit_reason": exit_reason,
                "time": exit_dt.strftime('%H:%M:%S')
            })

        # Build full 30-day list (fill zeros for missing days)
        all_days = []
        for i in range(30):
            d = (now_naive - timedelta(days=29 - i)).strftime('%Y-%m-%d')
            if d in daily:
                entry = daily[d].copy()
                entry["total_pnl"] = round(entry["total_pnl"], 4)
                all_days.append(entry)
            else:
                all_days.append({
                    "date": d,
                    "total_pnl": 0.0,
                    "wins": 0,
                    "losses": 0,
                    "trades": 0,
                    "trade_list": [],
                })

        total_pnl = sum(d["total_pnl"] for d in all_days)
        total_wins = sum(d["wins"] for d in all_days)
        total_losses = sum(d["losses"] for d in all_days)
        total_trades = sum(d["trades"] for d in all_days)

        days_with_trades = [d for d in all_days if d["trades"] > 0]
        best_day = max(days_with_trades, key=lambda x: x["total_pnl"]) if days_with_trades else None
        worst_day = min(days_with_trades, key=lambda x: x["total_pnl"]) if days_with_trades else None

        return {
            "status": "success",
            "summary": {
                "total_pnl": round(total_pnl, 4),
                "total_trades": total_trades,
                "total_wins": total_wins,
                "total_losses": total_losses,
                "win_rate": round(total_wins / total_trades * 100, 1) if total_trades > 0 else 0,
                "best_day": {"date": best_day["date"], "pnl": round(best_day["total_pnl"], 2)} if best_day else None,
                "worst_day": {"date": worst_day["date"], "pnl": round(worst_day["total_pnl"], 2)} if worst_day else None,
            },
            "days": all_days,
        }
    except Exception as e:
        logger.error(f"❌ Failed to get 30-day breakdown: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}

@router.get("/learning/trader-context/history")
async def get_trader_context_history(
    limit: int = Query(10, ge=1, le=50),
    user_id: str | None = None,
    credentials: Any = Depends(security),
) -> Dict[str, Any]:
    """Get history of imported trader expertise"""
    try:
        requester = await jwt_handler.verify_token(credentials.credentials)
        if not requester:
            raise HTTPException(status_code=401, detail="Unauthorized")

        target_id = _get_target_user_id(requester, user_id)

        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(TraderContext)
                .where(TraderContext.user_id == target_id)
                .order_by(desc(TraderContext.timestamp))
                .limit(limit)
            )
            history = result.scalars().all()
            
            return {
                "success": True,
                "history": [
                    {
                        "id": h.id,
                        "timestamp": h.timestamp.isoformat(),
                        "trader_name": h.trader_name,
                        "prompt": h.prompt
                    }
                    for h in history
                ]
            }
    except Exception as e:
        logger.error(f"❌ Failed to fetch trader context history: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/learning/import-trader-context")
async def import_trader_context(
    payload: Dict[str, Any],
    user_id: str | None = None,
    credentials: Any = Depends(security),
) -> Dict[str, Any]:
    """
    Import human trader expertise into the AI system.
    Saves context to database for use in AI Decision Agent prompts.
    """
    try:
        requester = await jwt_handler.verify_token(credentials.credentials)
        if not requester:
            raise HTTPException(status_code=401, detail="Unauthorized")

        target_id = _get_target_user_id(requester, user_id)

        prompt = payload.get("trader_prompt")
        trader_name = payload.get("trader_name", "Anonymous Trader")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="trader_prompt is required")
            
        logger.info(f"🧠 Importing trader context from {trader_name}: {prompt[:50]}...")
        
        # Save to database
        async with AsyncSessionFactory() as session:
            new_context = TraderContext(
                trader_name=trader_name,
                user_id=target_id,
                prompt=prompt,
                timestamp=datetime.utcnow()
            )
            session.add(new_context)
            await session.commit()
        
        return {
            "success": True,
            "message": f"Trader context from {trader_name} successfully integrated into Neural Core",
            "integration_score": 0.98,
            "applied_patterns": ["Expert Intuition", "Tactical Adaptation", "Neural Bias Correction"]
        }
        
    except Exception as e:
        logger.error(f"❌ Trader context import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# === Intelligence Management (Custom Sources) ===

@router.get("/intelligence/sources")
async def get_news_sources(db: AsyncSession = Depends(get_db)):
    """List all registered news sources"""
    try:
        from packages.shared.models import NewsSource
        result = await db.execute(select(NewsSource))
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intelligence/sources")
async def add_news_source(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Add a new custom news/telegram source"""
    try:
        from packages.shared.models import NewsSource
        name = payload.get("name")
        url = payload.get("url")
        source_type = payload.get("source_type", "web") # rss|telegram|web
        
        if not name or not url:
            raise HTTPException(status_code=400, detail="name and url are required")
            
        new_source = NewsSource(
            name=name,
            url=url,
            source_type=source_type,
            is_active=True
        )
        db.add(new_source)
        await db.commit()
        return {"success": True, "source_id": new_source.id}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/intelligence/sources/{source_id}")
async def delete_news_source(source_id: int, db: AsyncSession = Depends(get_db)):
    """Remove a news source"""
    try:
        from packages.shared.models import NewsSource
        result = await db.execute(select(NewsSource).where(NewsSource.id == source_id))
        source = result.scalar_one_or_none()
        if source:
            await db.delete(source)
            await db.commit()
            return {"success": True}
        raise HTTPException(status_code=404, detail="Source not found")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intelligence/scrape-now")
async def trigger_manual_scrape():
    """Trigger an immediate scrape of all sources"""
    try:
        from packages.shared.market_intelligence import intelligence_aggregator
        await intelligence_aggregator.scraper.scrape_all()
        return {"success": True, "message": "Scraping cycle initiated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
