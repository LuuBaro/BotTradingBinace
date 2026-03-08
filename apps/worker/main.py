"""
Worker Main Loop - Trading engine orchestrator
Coordinates AI decision making, risk validation, and execution
"""
# *** CRITICAL: Clean environment BEFORE any packages.shared imports ***
# (because packages.shared.__init__.py imports settings)
import os
openai_key = os.environ.get("OPENAI_API_KEY", "")
if openai_key.startswith("gsk_"):
    print("[CLEANUP] Removing contaminated Groq API key from os.environ...")
    del os.environ["OPENAI_API_KEY"]
    print("[CLEANUP] Removed. Pydantic will load from .env file instead.")

import asyncio
import signal
import sys
import uuid
import random
from datetime import datetime, timedelta
from sqlalchemy import select, desc, update
from packages.shared.config import settings
from packages.shared.database import AsyncSessionFactory, init_db, close_db
from packages.shared.models import (
    BotConfig, 
    Decision as DecisionModel, 
    RiskLog, 
    Position, 
    Signal as SignalModel,
    Event,
    Event as EventModel,
    PromptPack,
)
from packages.shared.schemas import RiskConfig, MarketSnapshot, Decision as DecisionSchema
from packages.shared.enums import ActionType, Side, MarketRegime
from packages.shared.exchange.mock import MockExchange
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from packages.shared.risk_engine import RiskEngine
from packages.shared.logger import logger
from apps.worker.engine.execution import ExecutionEngine
from apps.worker.engine.reconciler import ReconcilerEngine
from packages.shared.ai_orchestrator import AIOrchestrator
from packages.shared.ai_scout import AIScout, ScoutSignal
from packages.shared.llm_adapter import get_llm_adapter
from packages.shared.prompt_pack import PromptPackSchema, RegimeDefinition, EntryPlaybook, ExitPlaybook, TimeFrame
from packages.shared.models import TraderContext

class TradingWorker:
    """
    Main trading worker orchestrator
    Runs the decision → validation → execution loop
    """

    def __init__(self):
        self.running = False
        # Choose exchange based on configuration
        if settings.binance_api_key and settings.binance_api_secret:
            self.exchange = BinanceFuturesClient()
            self.is_binance = True
            logger.info(
                "exchange_initialized",
                type="binance",
                testnet=settings.binance_testnet,
            )
        else:
            self.exchange = MockExchange()
            self.is_binance = False
            logger.info("exchange_initialized", type="mock")
        
        self.trader = None # Will be initialized in initialize()
        self.execution_engine = ExecutionEngine(self.exchange)
        self.reconciler = ReconcilerEngine(self.exchange)
        self.risk_engine: RiskEngine | None = None
        self.orchestrator: AIOrchestrator | None = None
        self.scout: AIScout | None = None  # Lightweight scanner (2-tier mode)
        self.prompt_pack: PromptPackSchema | None = None
        self.trader_context: str | None = None
        self.loop_count = 0
        self.binance_session = None  # For Binance async client
        self.symbols_to_monitor = [
            "BTCUSDT", "ETHUSDT", "LINKUSDT", "XRPUSDT", 
            "DOTUSDT", "UNIUSDT", "DOGEUSDT", "SOLUSDT", 
            "ADAUSDT", "MATICUSDT", "AVAXUSDT"
        ]
        # AI call hardening state (anti-429 / token control)
        self._ai_round_robin_index = 0
        self._ai_last_call_at: datetime | None = None
        self._ai_rate_limit_streak = 0
        self._ai_global_cooldown_until: datetime | None = None
        self._ai_symbol_cooldown_until: dict[str, datetime] = {}

        # Symbol universe cache for ALL-mode (avoid heavy exchangeInfo calls each loop)
        self._symbol_universe_cache: list[str] = []
        self._symbol_universe_cached_at: datetime | None = None

    async def initialize(self) -> None:
        """Initialize worker"""
        logger.info("worker_initializing")
        
        # Initialize database
        await init_db()
        
        # Initialize Binance client session if using Binance
        if self.is_binance and not self.exchange.session:
            import aiohttp
            # Force ThreadedResolver to avoid DNS issues with aiodns on Windows
            connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
            self.binance_session = aiohttp.ClientSession(connector=connector)
            self.exchange.session = self.binance_session
            await self.exchange.sync_server_time()
            logger.info("binance_session_initialized")
        
        # Load risk config and prompt pack from database
        async with AsyncSessionFactory() as session:
            # 1. Load Risk Config
            result = await session.execute(
                select(BotConfig).where(BotConfig.is_active == True).order_by(BotConfig.id.desc()).limit(1)
            )
            bot_config = result.scalars().first()
            
            if not bot_config:
                logger.warning("no_active_bot_config_using_default")
                risk_config = RiskConfig()
            else:
                risk_config = RiskConfig(**bot_config.risk_json)
                logger.info("risk_config_loaded", version=bot_config.version)

                # Load symbols from active bot config to avoid out-of-strategy scans
                try:
                    import json as _json
                    raw = bot_config.symbols_json
                    if isinstance(raw, str):
                        parsed = _json.loads(raw)
                    elif isinstance(raw, dict):
                        parsed = raw
                    else:
                        parsed = {}
                    cfg_symbols = parsed.get("symbols", []) if isinstance(parsed, dict) else []
                    cfg_symbols = [s.upper() for s in cfg_symbols if isinstance(s, str) and s.upper().endswith("USDT")]
                    if cfg_symbols:
                        self.symbols_to_monitor = cfg_symbols
                        logger.info("symbols_loaded_from_bot_config", symbols=self.symbols_to_monitor)
                except Exception as e:
                    logger.warning("symbols_config_parse_failed", error=str(e))

            self.risk_engine = RiskEngine(risk_config)

            # 2. Load latest Trader Context (Human Expertise)
            context_result = await session.execute(
                select(TraderContext).order_by(TraderContext.timestamp.desc())
            )
            latest_context = context_result.scalars().first()
            if latest_context:
                self.trader_context = latest_context.prompt
                logger.info("trader_context_loaded", trader=latest_context.trader_name)

            # 3. Load Prompt Pack from DB if configured, else use default
            self.prompt_pack = None
            try:
                if bot_config and bot_config.active_prompt_pack_id:
                    pp_result = await session.execute(
                        select(PromptPack).where(PromptPack.id == bot_config.active_prompt_pack_id)
                    )
                    active_pack = pp_result.scalar_one_or_none()
                    if active_pack and active_pack.content_json:
                        self.prompt_pack = PromptPackSchema.model_validate(active_pack.content_json)
                        logger.info("prompt_pack_loaded_from_db", prompt_pack_id=active_pack.id, name=active_pack.name)
            except Exception as e:
                logger.warning("prompt_pack_load_failed_fallback_default", error=str(e))

            if self.prompt_pack is None:
                self.prompt_pack = PromptPackSchema(
                    name="Neural Default Strategy",
                    symbols=self.symbols_to_monitor,
                    timeframe=TimeFrame.HOUR_1,
                    regimes=[
                        RegimeDefinition(name="Trending Up", indicators={"EMA_20 > EMA_50": True}, description="Price trending upwards"),
                        RegimeDefinition(name="Range Bound", indicators={"RSI": "between 40 and 60"}, description="Market consolidates"),
                        RegimeDefinition(name="Trending Down", indicators={"EMA_20 < EMA_50": True}, description="Price trending downwards")
                    ],
                    entry_playbooks=[
                        EntryPlaybook(side="LONG", regime="Trending Up", conditions=["Price > EMA_20", "RSI > 50"], target_ratio=1.7),
                        EntryPlaybook(side="SHORT", regime="Trending Down", conditions=["Price < EMA_20", "RSI < 45"], target_ratio=1.7)
                    ],
                    exit_playbooks=[
                        ExitPlaybook(side="LONG", profit_target="RR >= 1.7 or momentum weakens", stop_loss="Below recent swing low"),
                        ExitPlaybook(side="SHORT", profit_target="RR >= 1.7 or momentum weakens", stop_loss="Above recent swing high")
                    ],
                    min_analysis_confidence=0.55,
                    risk_params={
                        "max_position_pct": risk_config.max_position_pct * 100, # PromptPack uses % (1-100)
                        "max_leverage": risk_config.max_leverage,
                        "min_risk_ratio": 1.5,
                        "max_concurrent_positions": risk_config.max_concurrent_positions
                    }
                )
            
            # Initialize LLM Adapters
            ai_mode = settings.worker_ai_mode or "two_tier_hybrid"
            
            if ai_mode == "two_tier_hybrid":
                # 2-Tier Hybrid Mode: Scout (cloud) + Verifier (cloud)
                def _get_api_key(provider: str) -> str | None:
                    """Get correct API key based on provider type"""
                    if provider == 'openai':
                        return settings.openai_api_key
                    elif provider == 'groq':
                        return settings.groq_api_key
                    elif provider in ('claude', 'anthropic'):
                        return settings.anthropic_api_key
                    return None
                
                self.scout_llm = get_llm_adapter(
                    provider=settings.worker_ai_scout_provider,
                    api_key=_get_api_key(settings.worker_ai_scout_provider),
                    model=settings.worker_ai_scout_model
                )
                verifier_llm = get_llm_adapter(
                    provider=settings.worker_ai_verifier_provider,
                    api_key=_get_api_key(settings.worker_ai_verifier_provider),
                    model=settings.worker_ai_verifier_model
                )
                self.scout = AIScout(self.scout_llm)
                self.orchestrator = AIOrchestrator(verifier_llm)
                logger.info(
                    "ai_two_tier_hybrid_linked",
                    scout_provider=settings.worker_ai_scout_provider,
                    scout_model=settings.worker_ai_scout_model,
                    verifier_provider=settings.worker_ai_verifier_provider,
                    verifier_model=settings.worker_ai_verifier_model,
                )
            elif ai_mode == "two_tier_same":
                # 2-Tier Same Mode: Scout (local) + Verifier (local)
                local_provider = settings.selected_llm or "local"
                if local_provider in ('openai', 'groq'):
                    local_model = settings.openai_model
                elif local_provider in ('claude', 'anthropic'):
                    local_model = settings.anthropic_model
                elif local_provider == 'gemini':
                    local_model = settings.gemini_model
                elif local_provider == 'local':
                    local_model = settings.custom_provider_model or 'local-model'
                else:
                    local_model = settings.custom_provider_model or 'local-model'
                
                def _get_api_key_for_provider(provider: str) -> str | None:
                    if provider == 'openai':
                        return settings.openai_api_key
                    elif provider == 'groq':
                        return settings.groq_api_key
                    elif provider in ('claude', 'anthropic'):
                        return settings.anthropic_api_key
                    return None
                
                api_key = _get_api_key_for_provider(local_provider)
                self.scout_llm = get_llm_adapter(
                    provider=local_provider,
                    api_key=api_key,
                    model=local_model
                )
                verifier_llm = get_llm_adapter(
                    provider=local_provider,
                    api_key=api_key,
                    model=local_model
                )
                self.scout = AIScout(self.scout_llm)
                self.orchestrator = AIOrchestrator(verifier_llm)
                logger.info(
                    "ai_two_tier_same_linked",
                    provider=local_provider,
                    model=local_model,
                    mode="two_tier_same"
                )
            elif ai_mode == "single_tier":
                # Single-Tier Mode: Use selected LLM for everything
                llm_provider = settings.selected_llm
                
                def _get_single_tier_api_key(provider: str) -> str | None:
                    if provider == 'openai':
                        return settings.openai_api_key
                    elif provider == 'groq':
                        return settings.groq_api_key
                    elif provider in ('claude', 'anthropic'):
                        return settings.anthropic_api_key
                    return None
                
                if settings.selected_llm in ('openai', 'groq'):
                    single_tier_model = settings.openai_model
                elif settings.selected_llm in ('claude', 'anthropic'):
                    single_tier_model = settings.anthropic_model
                elif settings.selected_llm == 'gemini':
                    single_tier_model = settings.gemini_model
                elif settings.selected_llm == 'local':
                    single_tier_model = settings.custom_provider_model or 'local-model'
                else:
                    single_tier_model = settings.custom_provider_model or 'local-model'

                llm = get_llm_adapter(
                    provider=settings.selected_llm,
                    api_key=_get_single_tier_api_key(settings.selected_llm),
                    model=single_tier_model
                )
                self.orchestrator = AIOrchestrator(llm)
                logger.info("ai_single_tier_linked", provider=llm_provider, model=llm.model)
            else:
                # Fallback to two_tier_hybrid
                logger.warning("ai_mode_invalid", mode=ai_mode, fallback="two_tier_hybrid")
                self.scout_llm = get_llm_adapter(
                    provider=settings.worker_ai_scout_provider,
                    api_key=settings.openai_api_key if settings.worker_ai_scout_provider in ('openai', 'groq') else settings.anthropic_api_key,
                    model=settings.worker_ai_scout_model
                )
                verifier_llm = get_llm_adapter(
                    provider=settings.worker_ai_verifier_provider,
                    api_key=settings.openai_api_key if settings.worker_ai_verifier_provider in ('openai', 'groq') else settings.anthropic_api_key,
                    model=settings.worker_ai_verifier_model
                )
                self.scout = AIScout(self.scout_llm)
                self.orchestrator = AIOrchestrator(verifier_llm)

        logger.info("worker_initialized")

    async def run(self) -> None:
        """Main worker loop"""
        self.running = True
        logger.info("worker_started", loop_interval_sec=settings.worker_loop_interval_sec)
        
        last_heartbeat = datetime.utcnow() # Initialize heartbeat timer
        
        while self.running:
            try:
                # Send heartbeat every 30 seconds
                if (datetime.utcnow() - last_heartbeat).total_seconds() > 30:
                    async with AsyncSessionFactory() as session:
                        heartbeat = Event(
                            timestamp=datetime.utcnow(),
                            level="INFO",
                            code="WORKER_HEARTBEAT",
                            message=f"Worker active. Monitoring {len(self.symbols_to_monitor)} symbols.",
                            data_json={"symbols_count": len(self.symbols_to_monitor)}
                        )
                        session.add(heartbeat)
                        await session.commit()
                    last_heartbeat = datetime.utcnow()
                    logger.debug("worker_heartbeat_sent")
                    
                self.loop_count += 1
                await self._execute_loop_iteration()
                await self._process_pending_approvals()  # Process manual approvals
                await asyncio.sleep(settings.worker_loop_interval_sec)
            except asyncio.CancelledError:
                logger.info("worker_loop_cancelled")
                break
            except Exception as e:
                logger.error("worker_loop_error", error=str(e), exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

    async def _execute_loop_iteration(self) -> None:
        """Execute one iteration of the trading loop for all configured symbols"""
        symbols = await self._resolve_symbols_for_loop()
        
        async with AsyncSessionFactory() as session:
            try:
                # Local serializer helper (used by both proactive close and normal AI decisions)
                import json as _json

                def _serialize(obj):
                    return _json.loads(
                        _json.dumps(obj, default=lambda o: o.isoformat() if hasattr(o, 'isoformat') else str(o))
                    )

                # Keep prompt-pack symbol universe aligned with active runtime symbols
                if self.prompt_pack is not None:
                    self.prompt_pack.symbols = symbols

                # Reconcile exchange positions with database
                await self.reconciler.sync_positions(session)

                # Expire old signals before generating new watchlist entries
                await self._expire_stale_signals(session)
                
                # Get current positions from DB to share with AI
                positions_result = await session.execute(select(Position))
                db_positions = {p.symbol: p for p in positions_result.scalars().all()}

                # Build AI budget for this loop (prioritize open positions, then round-robin others)
                ai_symbols_this_loop = self._build_ai_symbol_plan(symbols, db_positions)
                ai_symbols_set = set(ai_symbols_this_loop)

                for symbol in symbols:
                    trace_id = str(uuid.uuid4())
                    
                    # Step 1: Get market snapshot
                    if self.is_binance:
                        snapshot = await self._fetch_binance_snapshot(symbol)
                        if not snapshot:
                            snapshot = self._generate_mock_snapshot(symbol)
                    else:
                        snapshot = self._generate_mock_snapshot(symbol)
                    
                    if not snapshot:
                        continue

                    # Update PNL for this specific symbol if position exists
                    if symbol in db_positions:
                        pos = db_positions[symbol]
                        current_price = snapshot.close
                        entry_price = float(pos.entry_price)
                        qty = float(pos.qty)
                        
                        if pos.side.lower() == "long":
                            pos.unrealized_pnl = (current_price - entry_price) * qty
                        else:
                            pos.unrealized_pnl = (entry_price - current_price) * qty
                        pos.updated_at = datetime.utcnow()

                    # ═══════════════════════════════════════════════════════════
                    # ✅ PROACTIVE TP/SL MONITORING
                    # Uses dynamically parsed trader intent - no hardcoded values
                    # The AI reads the trader's prompt and extracts profit targets
                    # ═══════════════════════════════════════════════════════════
                    active_pos = db_positions.get(symbol)
                    if active_pos and active_pos.unrealized_pnl is not None:
                        current_pnl = float(active_pos.unrealized_pnl)
                        current_price = snapshot.close
                        pos_tp = float(active_pos.take_profit) if active_pos.take_profit else None
                        pos_sl = float(active_pos.stop_loss) if active_pos.stop_loss else None
                        pos_side = active_pos.side.lower()

                        # Get dynamic thresholds from cached trader intent
                        # This is what the trader wrote in their prompt - AI parsed it
                        trader_intent = self.orchestrator._cached_intent or {}
                        profit_target_usd = trader_intent.get("profit_target_usd")  # e.g. 2.0
                        max_loss_usd = trader_intent.get("max_loss_usd")             # e.g. -5.0
                        max_hold_mins = trader_intent.get("max_hold_minutes")        # e.g. 60
                        
                        # Fallback to system risk limits if trader didn't specify SL
                        # This prevents the AI from exiting too early or staying too long without a plan
                        if max_loss_usd is None and self.risk_engine.config.max_risk_per_trade_pct:
                            # Estimate dollar loss based on account balance and risk %
                            try:
                                balance_info = await self.exchange.get_account_balance() if self.is_binance else await self.exchange.get_balance()
                                balance = float(balance_info[0]["balance"]) if self.is_binance and isinstance(balance_info, list) else float(balance_info.get("balance", 0))
                                risk_pct = self.risk_engine.config.max_risk_per_trade_pct / 100.0
                                max_loss_usd = balance * risk_pct
                            except:
                                pass

                        should_close = False
                        close_reason = ""

                        # Check TP hit via price
                        if pos_tp:
                            if pos_side == "long" and current_price >= pos_tp:
                                should_close = True
                                close_reason = f"Take Profit chạm đích: giá {current_price:.4f} >= TP {pos_tp:.4f}"
                            elif pos_side == "short" and current_price <= pos_tp:
                                should_close = True
                                close_reason = f"Take Profit chạm đích: giá {current_price:.4f} <= TP {pos_tp:.4f}"

                        # Check SL hit via price
                        if pos_sl and not should_close:
                            if pos_side == "long" and current_price <= pos_sl:
                                should_close = True
                                close_reason = f"Stop Loss bị kích hoạt: giá {current_price:.4f} <= SL {pos_sl:.4f}"
                            elif pos_side == "short" and current_price >= pos_sl:
                                should_close = True
                                close_reason = f"Stop Loss bị kích hoạt: giá {current_price:.4f} >= SL {pos_sl:.4f}"

                        # Check profit target (from trader's own prompt - dynamically parsed)
                        if not should_close and profit_target_usd is not None and current_pnl >= profit_target_usd:
                            should_close = True
                            close_reason = (
                                f"Đạt mục tiêu lợi nhuận từ chiến lược trader: "
                                f"PnL ${current_pnl:.2f} >= mục tiêu ${profit_target_usd:.2f}. Chốt lời."
                            )

                        # Check max loss (from trader's own prompt)
                        if not should_close and max_loss_usd is not None and current_pnl <= -abs(max_loss_usd):
                            should_close = True
                            close_reason = (
                                f"Vượt ngưỡng lỗ tối đa: PnL ${current_pnl:.2f} <= -${abs(max_loss_usd):.2f}. Cắt lỗ."
                            )

                        # Check max hold time (from trader's own prompt)
                        if not should_close and max_hold_mins is not None and active_pos.opened_at:
                            hold_time = (datetime.utcnow() - active_pos.opened_at).total_seconds() / 60
                            if hold_time >= max_hold_mins:
                                should_close = True
                                close_reason = (
                                    f"Đã giữ lệnh {hold_time:.0f} phút >= giới hạn {max_hold_mins} phút. Đóng lệnh."
                                )

                        if should_close:
                            logger.info(
                                "proactive_tp_sl_triggered",
                                symbol=symbol,
                                pnl=current_pnl,
                                reason=close_reason
                            )
                            close_side = Side.SHORT if pos_side == "long" else Side.LONG
                            # Create unique trace_id for this proactive close (avoid duplicates)
                            exit_trace_id = f"{trace_id}_close_{symbol}"
                            exit_decision = DecisionSchema(
                                regime=MarketRegime.RANGE,
                                action=ActionType.CLOSE,
                                symbol=symbol,
                                side=close_side,
                                size_pct=0.01,
                                leverage=1,
                                entry_price=current_price,
                                confidence=1.0,
                                rationale=close_reason,
                                checklist=[]
                            )
                            # Create Decision record for proactive closure
                            exit_decision_model = DecisionModel(
                                timestamp=datetime.utcnow(),
                                trace_id=exit_trace_id,
                                decision_json=_serialize(exit_decision.model_dump()),
                                confidence=1.0,
                                regime=MarketRegime.RANGE.value,
                                rationale=close_reason,
                                status="PENDING",
                                decision_type="EXIT"
                            )
                            session.add(exit_decision_model)
                            await session.flush()

                            try:
                                close_result = await self.execution_engine.execute_decision(
                                    decision=exit_decision,
                                    trace_id=exit_trace_id,
                                    session=session
                                )
                                if close_result.get("status") == "success":
                                    logger.info("proactive_close_success", symbol=symbol, pnl=current_pnl)
                                    
                                    # Update Decision record with resulting order_id
                                    exit_decision_model.status = "EXECUTED"
                                    exit_decision_model.order_id = str(close_result.get("order_id"))
                                    
                                    close_event = EventModel(
                                        timestamp=datetime.utcnow(),
                                        level="INFO",
                                        code="AUTO_CLOSE_TP",
                                        message=f"[AUTO-CLOSE] {symbol}: {close_reason} | PnL: ${current_pnl:+.2f}",
                                        trace_id=exit_trace_id,
                                        data_json={"symbol": symbol, "pnl": current_pnl, "reason": close_reason}
                                    )
                                    session.add(close_event)
                                    await session.flush()
                                    continue  # Skip AI decision for this symbol this cycle
                                else:
                                    exit_decision_model.status = "FAILED"
                            except Exception as close_err:
                                logger.error("proactive_close_failed", symbol=symbol, error=str(close_err))
                                exit_decision_model.status = "FAILED"
                                exit_decision_model.execution_error = str(close_err)

                    # AI budgeting / cooldown gate (we still run proactive TP/SL above for all symbols)
                    if symbol not in ai_symbols_set:
                        continue

                    now_utc = datetime.utcnow()
                    if self._ai_global_cooldown_until and now_utc < self._ai_global_cooldown_until:
                        continue

                    symbol_cd = self._ai_symbol_cooldown_until.get(symbol)
                    if symbol_cd and now_utc < symbol_cd:
                        continue

                    # === OPTIONAL: 2-tier Scout → Verifier Cascade ===
                    # If enabled, scout scans symbol cheaply first. Only proceed to expensive verifier if signal strong.
                    should_analyze_with_verifier = True
                    if settings.worker_ai_use_two_tier and self.scout:
                        try:
                            # Build minimal context for scout
                            has_position = symbol in db_positions
                            current_pnl = None
                            if has_position:
                                p = db_positions[symbol]
                                current_pnl = float(p.unrealized_pnl) if p.unrealized_pnl else 0.0
                            
                            scout_market_snapshot = {
                                "symbol": symbol,
                                "close": snapshot.close,
                                "volume": snapshot.volume or 0,
                                "spread": snapshot.spread or (snapshot.high - snapshot.low) if snapshot.high and snapshot.low else 0,
                                "high": snapshot.high,
                                "low": snapshot.low,
                            }
                            
                            await self._respect_ai_pacing()
                            scout_signal = await self.scout.scan_symbol(
                                symbol=symbol,
                                market_snapshot=scout_market_snapshot,
                                has_open_position=has_position,
                                current_pnl=current_pnl
                            )
                            
                            if scout_signal:
                                threshold = settings.worker_ai_scout_confidence_threshold
                                # Always analyze if: has position OR high confidence signal
                                if has_position or scout_signal.confidence >= threshold or scout_signal.priority_score >= 7:
                                    logger.info(
                                        "scout_signal_strong",
                                        symbol=symbol,
                                        confidence=scout_signal.confidence,
                                        action_hint=scout_signal.action_hint,
                                        priority=scout_signal.priority_score,
                                        has_position=has_position
                                    )
                                    should_analyze_with_verifier = True
                                else:
                                    # Weak signal, no position → skip verifier to save tokens
                                    logger.info(
                                        "scout_filtered_low_priority",
                                        symbol=symbol,
                                        confidence=scout_signal.confidence,
                                        action_hint=scout_signal.action_hint,
                                        priority=scout_signal.priority_score
                                    )
                                    should_analyze_with_verifier = False
                            else:
                                # Scout failed → fallback to verifier (safety)
                                logger.warning(f"scout_failed_fallback_verifier symbol={symbol}")
                                should_analyze_with_verifier = True
                                
                        except Exception as scout_err:
                            logger.error(f"scout_error symbol={symbol}: {scout_err}", exc_info=True)
                            should_analyze_with_verifier = True  # Fallback to verifier on error
                    
                    if not should_analyze_with_verifier:
                        continue  # Skip expensive verifier call

                    # Step 2: Get real AI decision from Orchestrator (Verifier in 2-tier mode)
                    # Build ENRICHED position data for AI (includes entry_price, tp, sl, pnl%)
                    current_positions_list = []
                    for p in db_positions.values():
                        p_entry = float(p.entry_price) if p.entry_price else 0
                        p_qty = float(p.qty) if p.qty else 0
                        p_pnl = float(p.unrealized_pnl) if p.unrealized_pnl else 0
                        p_tp = float(p.take_profit) if p.take_profit else None
                        p_sl = float(p.stop_loss) if p.stop_loss else None
                        current_positions_list.append({
                            "symbol": p.symbol,
                            "side": p.side,
                            "qty": p_qty,
                            "entry_price": p_entry,
                            "take_profit": p_tp,
                            "stop_loss": p_sl,
                            "unrealized_pnl_usd": round(p_pnl, 4),
                            "opened_at": p.opened_at.isoformat() if p.opened_at else None,
                        })
                    
                    # Convert MarketSnapshot to dict for AI
                    # Serialize datetimes to strings to avoid DB JSON serialization error
                    _raw = snapshot.model_dump()
                    snapshot_dict = _json.loads(
                        _json.dumps(_raw, default=lambda o: o.isoformat() if hasattr(o, 'isoformat') else str(o))
                    )

                    await self._respect_ai_pacing()
                    
                    # Call Real AI Orchestrator
                    result = await self.orchestrator.make_decision(
                        market_snapshot=snapshot_dict,
                        prompt_pack=self.prompt_pack,
                        current_positions=current_positions_list,
                        trader_context=self.trader_context
                    )
                    
                    if not result["valid"]:
                        error_text = self._extract_error_text(result)
                        if self._is_rate_limited(error_text):
                            self._on_rate_limited(symbol, error_text)
                            logger.warning(
                                "ai_rate_limited",
                                symbol=symbol,
                                cooldown_until=self._ai_global_cooldown_until.isoformat() if self._ai_global_cooldown_until else None,
                                detail=error_text[:220],
                            )
                        else:
                            # Reset streak on non-rate-limit validation errors
                            self._ai_rate_limit_streak = 0
                            logger.error(f"AI Decision failed for {symbol}: {result['errors']}")
                        continue

                    # Successful model response resets rate-limit streak
                    self._ai_rate_limit_streak = 0
                    if symbol in self._ai_symbol_cooldown_until:
                        self._ai_symbol_cooldown_until.pop(symbol, None)
                    
                    ai_decision = result["decision"] # This is AIDecisionOutput
                    
                    # Mapper AIDecisionOutput to Decisions Schema (ActionType/Side)
                    # AIDecisionOutput usage: decision_type (ENTRY, EXIT, NO_TRADE)
                    # action mapping
                    action_map = {
                        "ENTRY": ActionType.OPEN,
                        "EXIT": ActionType.CLOSE,
                        "MODIFY": ActionType.HOLD, # Assuming modify is like hold for now
                        "NO_TRADE": ActionType.HOLD
                    }
                    
                    # regime mapping
                    regime_map = {
                        "Trending Up": MarketRegime.TREND,
                        "Trending Down": MarketRegime.TREND,
                        "Range Bound": MarketRegime.RANGE,
                        "Volatile": MarketRegime.VOLATILITY_SPIKE,
                        "Sideways": MarketRegime.RANGE,
                        "breakout": MarketRegime.BREAKOUT,
                        "trend": MarketRegime.TREND,
                        "range": MarketRegime.RANGE,
                    }
                    
                    # side mapping
                    side_val = None
                    if ai_decision.order_spec:
                        side_val = Side.LONG if ai_decision.order_spec.side.upper() == "BUY" else Side.SHORT
                    
                    # Create Decision Schema for local systems
                    decision = DecisionSchema(
                        regime=regime_map.get(ai_decision.market_regime, MarketRegime.RANGE),
                        action=action_map.get(ai_decision.decision_type.value, ActionType.HOLD),
                        symbol=symbol,
                        side=side_val,
                        size_pct=(ai_decision.risk_assessment.get("position_pct", 5.0) / 100.0) if ai_decision.decision_type.value == "ENTRY" else 0.1,
                        leverage=int(ai_decision.order_spec.leverage) if ai_decision.order_spec else 1,
                        entry_price=ai_decision.order_spec.entry_price if ai_decision.order_spec else snapshot.close,
                        stop_loss=ai_decision.order_spec.stop_loss_price if ai_decision.order_spec else None,
                        take_profit=ai_decision.order_spec.take_profit_prices[0] if (ai_decision.order_spec and ai_decision.order_spec.take_profit_prices) else None,
                        confidence=ai_decision.confidence,
                        rationale=ai_decision.rationale,
                        checklist=[] # Can be populated from ai_decision.checklist_results if needed
                    )

                    # Promote overly-passive HOLD to cautious ENTRY when confidence/regime are strong
                    if (
                        decision.action == ActionType.HOLD
                        and decision.confidence >= 0.6
                        and decision.regime in (MarketRegime.TREND, MarketRegime.BREAKOUT)
                        and symbol not in db_positions
                    ):
                        decision.action = ActionType.OPEN
                        decision.side = Side.LONG if decision.regime == MarketRegime.TREND else Side.SHORT
                        decision.entry_price = snapshot.close
                        if decision.side == Side.LONG:
                            decision.stop_loss = snapshot.close * 0.995
                            decision.take_profit = snapshot.close * 1.009
                        else:
                            decision.stop_loss = snapshot.close * 1.005
                            decision.take_profit = snapshot.close * 0.991
                        decision.rationale = f"{decision.rationale} | auto-entry policy applied"

                    # Deterministic fallback when local AI is too conservative (NO_TRADE loops)
                    if decision.action == ActionType.HOLD and symbol not in db_positions:
                        ind = getattr(snapshot, "indicators", None) or {}
                        ema20 = ind.get("ema_20") or ind.get("EMA_20") or ind.get("ema20")
                        ema50 = ind.get("ema_50") or ind.get("EMA_50") or ind.get("ema50")
                        rsi = ind.get("rsi") or ind.get("RSI")
                        try:
                            ema20 = float(ema20) if ema20 is not None else None
                            ema50 = float(ema50) if ema50 is not None else None
                            rsi = float(rsi) if rsi is not None else None
                        except Exception:
                            ema20 = ema50 = rsi = None

                        if ema20 and ema50 and rsi is not None:
                            long_ok = snapshot.close > ema20 > ema50 and rsi >= 52
                            short_ok = snapshot.close < ema20 < ema50 and rsi <= 48

                            if long_ok or short_ok:
                                decision.action = ActionType.OPEN
                                decision.side = Side.LONG if long_ok else Side.SHORT
                                decision.confidence = max(float(decision.confidence or 0.0), 0.56)
                                decision.entry_price = snapshot.close
                                if decision.side == Side.LONG:
                                    decision.stop_loss = snapshot.close * 0.995
                                    decision.take_profit = snapshot.close * 1.008
                                else:
                                    decision.stop_loss = snapshot.close * 1.005
                                    decision.take_profit = snapshot.close * 0.992
                                decision.rationale = (
                                    f"Fallback entry: EMA20/EMA50 trend + RSI confirm ({'LONG' if long_ok else 'SHORT'})"
                                )

                    # Step 3: Save decision to database
                    decision_record = DecisionModel(
                        timestamp=datetime.utcnow(),
                        trace_id=trace_id,
                        decision_json=_serialize(ai_decision.model_dump()),
                        confidence=decision.confidence,
                        regime=decision.regime.value if hasattr(decision.regime, 'value') else str(decision.regime),
                        decision_type=("ENTRY" if decision.action == ActionType.OPEN else "EXIT" if decision.action == ActionType.CLOSE else "NO_TRADE"),
                        rationale=decision.rationale,
                        market_snapshot=snapshot_dict,
                        checklist_results=_serialize([c.model_dump() for c in ai_decision.checklist_results]),
                        status="PENDING",
                        tokens_used=result.get("tokens_used", 0),
                    )
                    session.add(decision_record)
                    await session.flush()

                    # Persist/refresh Neural Watchlist signal for actionable decisions
                    if decision.action != ActionType.HOLD:
                        signal_side = "LONG"
                        if decision.side == Side.SHORT:
                            signal_side = "SHORT"
                        elif decision.side == Side.LONG:
                            signal_side = "LONG"
                        elif symbol in db_positions:
                            # Fallback to current position side when AI omits explicit side
                            signal_side = str(db_positions[symbol].side).upper()

                        entry_price_val = decision.entry_price or snapshot.close
                        if entry_price_val and entry_price_val > 0:
                            low = entry_price_val * 0.999
                            high = entry_price_val * 1.001
                            entry_zone = f"{low:.4f}-{high:.4f}"
                        else:
                            entry_zone = f"{snapshot.close:.4f}-{snapshot.close:.4f}"

                        await self._upsert_active_signal(
                            session,
                            symbol=symbol,
                            side=signal_side,
                            probability=float(decision.confidence or 0.5),
                            rationale=decision.rationale or "AI signal",
                            entry_zone=entry_zone,
                            ttl_minutes=30,
                        )

                    if decision.action != ActionType.HOLD:
                        # Fetch balance and current positions for risk validation
                        balance_info = await self.exchange.get_account_balance() if self.is_binance else await self.exchange.get_balance()
                        balance = float(balance_info[0]["balance"]) if self.is_binance and isinstance(balance_info, list) else float(balance_info.get("balance", 0))

                        # Refresh positions from DB to avoid stale in-memory map
                        latest_positions_result = await session.execute(select(Position))
                        latest_positions = latest_positions_result.scalars().all()
                        current_positions = [
                            {"symbol": p.symbol, "side": p.side, "qty": p.qty}
                            for p in latest_positions
                        ]

                        # Normalize position size to configured cap before risk validation
                        try:
                            max_pos = float(getattr(self.risk_engine.config, "max_position_pct", 0.08))
                            if decision.size_pct is None or decision.size_pct <= 0:
                                decision.size_pct = min(0.02, max_pos)
                            elif decision.size_pct > max_pos:
                                decision.size_pct = max_pos
                        except Exception:
                            pass

                        # Risk Validation
                        risk_result = await self.risk_engine.validate_decision(
                            decision=decision,
                            current_positions=current_positions,
                            balance=balance,
                            current_price=snapshot.close,
                        )

                        decision_record.risk_passed = risk_result.approved
                        decision_record.risk_approval_reason = risk_result.reason
                        await session.flush()

                        if risk_result.approved:
                            try:
                                execution_result = await self.execution_engine.execute_decision(
                                    decision=decision,
                                    trace_id=trace_id,
                                    session=session
                                )
                                
                                if execution_result.get("status") == "success":
                                    decision_record.status = "EXECUTED"
                                    decision_record.order_id = str(execution_result.get("order_id"))
                                    await self._mark_active_signals_triggered(session, symbol)
                                    logger.info(f"Executed {decision.action} for {symbol}", trace_id=trace_id)
                                else:
                                    decision_record.status = "FAILED"
                            except Exception as exec_err:
                                logger.error(f"❌ Execution failed for {symbol}: {str(exec_err)}")
                                decision_record.status = "FAILED"
                        else:
                            decision_record.status = "REJECTED"
                            logger.warning(f"Risk REJECTED {decision.action} for {symbol}: {risk_result.reason}")
                    else:
                        # For HOLD actions, mark as passing risk (implicitly) and status as OBSERVING
                        decision_record.risk_passed = True
                        decision_record.risk_approval_reason = "Lệnh quan sát - Không vi phạm quy tắc rủi ro"
                        decision_record.status = "OBSERVING"

                await session.commit()
                logger.info(f"loop_iteration_complete", loop_count=self.loop_count)

            except Exception as e:
                logger.error("worker_loop_iteration_error", error=str(e), exc_info=True)
                await session.rollback()

    async def _upsert_active_signal(
        self,
        session,
        *,
        symbol: str,
        side: str,
        probability: float,
        rationale: str,
        entry_zone: str,
        ttl_minutes: int = 30,
    ) -> None:
        """Create or refresh one ACTIVE signal per symbol for Neural Watchlist."""
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=ttl_minutes)

        existing_res = await session.execute(
            select(SignalModel)
            .where(SignalModel.symbol == symbol)
            .where(SignalModel.status == "ACTIVE")
            .order_by(desc(SignalModel.timestamp))
            .limit(1)
        )
        existing = existing_res.scalar_one_or_none()

        if existing:
            existing.timestamp = now
            existing.side = side
            existing.probability = max(0.0, min(1.0, float(probability)))
            existing.rationale = rationale[:1000]
            existing.entry_zone = entry_zone[:50]
            existing.expires_at = expires_at
        else:
            session.add(
                SignalModel(
                    timestamp=now,
                    symbol=symbol,
                    side=side,
                    probability=max(0.0, min(1.0, float(probability))),
                    rationale=rationale[:1000],
                    entry_zone=entry_zone[:50],
                    status="ACTIVE",
                    expires_at=expires_at,
                )
            )

    async def _mark_active_signals_triggered(self, session, symbol: str) -> None:
        """Mark ACTIVE signals as TRIGGERED once execution succeeds."""
        await session.execute(
            update(SignalModel)
            .where(SignalModel.symbol == symbol)
            .where(SignalModel.status == "ACTIVE")
            .values(status="TRIGGERED")
        )

    async def _expire_stale_signals(self, session) -> None:
        """Expire stale active signals by TTL."""
        await session.execute(
            update(SignalModel)
            .where(SignalModel.status == "ACTIVE")
            .where(SignalModel.expires_at.is_not(None))
            .where(SignalModel.expires_at < datetime.utcnow())
            .values(status="EXPIRED")
        )

    async def _resolve_symbols_for_loop(self) -> list[str]:
        """Resolve symbol universe. Supports ALL-mode with cached Binance futures symbols."""
        symbols = [s.upper() for s in self.symbols_to_monitor]
        if "ALL" not in symbols:
            return symbols

        now = datetime.utcnow()
        if self._symbol_universe_cache and self._symbol_universe_cached_at:
            if (now - self._symbol_universe_cached_at).total_seconds() < 1800:
                return self._symbol_universe_cache

        try:
            info = await self.exchange.get_exchange_info() if self.is_binance else None
            ex_symbols = []
            if isinstance(info, dict):
                for s in info.get("symbols", []):
                    if (
                        s.get("contractType") == "PERPETUAL"
                        and s.get("quoteAsset") == "USDT"
                        and s.get("status") == "TRADING"
                    ):
                        ex_symbols.append(str(s.get("symbol", "")).upper())

            ex_symbols = [s for s in ex_symbols if s]
            ex_symbols = sorted(set(ex_symbols))

            # Keep bounded universe for CPU/GPU stability
            # Tie ALL-universe size to ai loop capacity (avoid overloading local runner)
            max_universe = max(8, settings.worker_ai_max_symbols_per_loop * 4)
            resolved = ex_symbols[:max_universe] if ex_symbols else [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"
            ]

            self._symbol_universe_cache = resolved
            self._symbol_universe_cached_at = now
            logger.info("symbol_universe_resolved", mode="ALL", count=len(resolved))
            return resolved
        except Exception as e:
            logger.warning("symbol_universe_resolve_failed", error=str(e))
            return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    def _build_ai_symbol_plan(self, symbols: list[str], db_positions: dict[str, Position]) -> list[str]:
        """Build symbol list for full AI analysis in this loop.

        Strategy:
        - Always prioritize symbols with open positions (for risk-aware exits)
        - Limit total AI calls per loop to control tokens/rate-limit
        - Rotate remaining symbols in round-robin for fairness
        """
        max_symbols = max(1, settings.worker_ai_max_symbols_per_loop)

        open_symbols = [s for s in symbols if s in db_positions]
        selected: list[str] = []

        if settings.worker_ai_prioritize_open_positions:
            selected.extend(open_symbols)

        remaining = [s for s in symbols if s not in selected]

        # Round-robin rotation for fairness across loops
        if remaining:
            start = self._ai_round_robin_index % len(remaining)
            rotated = remaining[start:] + remaining[:start]
            self._ai_round_robin_index = (self._ai_round_robin_index + 1) % len(remaining)
        else:
            rotated = []

        slots = max_symbols - len(selected)
        if slots > 0:
            selected.extend(rotated[:slots])

        # If all slots were consumed by open positions, still keep those positions
        # (we prefer safe exits over strict budget)
        return selected

    async def _respect_ai_pacing(self) -> None:
        """Apply minimum interval between AI calls to smooth request bursts."""
        min_interval_sec = max(0.0, settings.worker_ai_min_interval_ms / 1000.0)
        if min_interval_sec <= 0:
            return

        now = datetime.utcnow()
        if self._ai_last_call_at is None:
            self._ai_last_call_at = now
            return

        elapsed = (now - self._ai_last_call_at).total_seconds()
        if elapsed < min_interval_sec:
            await asyncio.sleep(min_interval_sec - elapsed)

        self._ai_last_call_at = datetime.utcnow()

    def _extract_error_text(self, result: dict) -> str:
        """Flatten orchestrator error payload to a single lowercase string."""
        errors = result.get("errors") if isinstance(result, dict) else None
        if not errors:
            return ""
        try:
            if isinstance(errors, list):
                parts = []
                for e in errors:
                    if isinstance(e, dict):
                        parts.append(str(e.get("error") or e))
                    else:
                        parts.append(str(e))
                return " | ".join(parts).lower()
            return str(errors).lower()
        except Exception:
            return str(errors).lower()

    def _is_rate_limited(self, error_text: str) -> bool:
        """Detect rate limit responses across providers."""
        msg = (error_text or "").lower()
        return (
            "429" in msg
            or "rate limit" in msg
            or "rate_limit" in msg
            or "too many requests" in msg
            or "tokens per minute" in msg
        )

    def _on_rate_limited(self, symbol: str, error_text: str) -> None:
        """Apply adaptive cooldown on 429 to reduce burn and stabilize worker."""
        self._ai_rate_limit_streak += 1
        base = max(0.1, float(settings.worker_ai_backoff_base_sec))
        cap = max(base, float(settings.worker_ai_backoff_max_sec))
        # Exponential backoff with cap
        delay = min(cap, base * (2 ** max(0, self._ai_rate_limit_streak - 1)))

        now = datetime.utcnow()
        cooldown_until = now + timedelta(seconds=delay)
        self._ai_global_cooldown_until = cooldown_until
        self._ai_symbol_cooldown_until[symbol] = cooldown_until

        logger.warning(
            "ai_backoff_applied",
            symbol=symbol,
            streak=self._ai_rate_limit_streak,
            delay_sec=round(delay, 2),
            reason=(error_text or "")[:220],
        )

    async def _update_positions_pnl(self, snapshot: MarketSnapshot) -> None:
        """Legacy method - now integrated into the main loop for efficiency"""
        pass


    async def _process_pending_approvals(self) -> None:
        """Fetch and execute decisions that were manually approved"""
        async with AsyncSessionFactory() as session:
            try:
                # Find decisions set to APPROVED_MANUALLY by API
                result = await session.execute(
                    select(DecisionModel).where(DecisionModel.status == "APPROVED_MANUALLY")
                )
                pending = result.scalars().all()
                
                if not pending:
                    return

                logger.info("processing_manual_approvals", count=len(pending))
                
                for decision_record in pending:
                    try:
                        trace_id = decision_record.trace_id
                        logger.info("executing_manually_approved_decision", trace_id=trace_id)
                        
                        # Reconstruct decision schema
                        decision_data = decision_record.decision_json
                        # Fix for potential string JSON
                        if isinstance(decision_data, str):
                            import json
                            decision_data = json.loads(decision_data)
                            
                        decision = DecisionSchema.model_validate(decision_data)
                        
                        # Execute
                        execution_result = await self.execution_engine.execute_decision(
                            decision=decision,
                            trace_id=trace_id,
                            session=session,
                        )
                        
                        if execution_result.get("status") == "success":
                            decision_record.status = "EXECUTED"
                            decision_record.order_id = str(execution_result.get("order_id"))
                        else:
                            decision_record.status = "FAILED"
                        
                        decision_record.execution_status = execution_result.get("status")
                        if execution_result.get("status") == "error" or execution_result.get("status") == "failed":
                            decision_record.execution_error = execution_result.get("reason") or execution_result.get("error")
                            
                        await session.commit()
                        logger.info("manual_execution_completed", trace_id=trace_id, status=decision_record.status)
                        
                    except Exception as ex:
                        logger.error("manual_execution_failed", trace_id=decision_record.trace_id, error=str(ex))
                        decision_record.status = "FAILED"
                        decision_record.execution_error = str(ex)
                        await session.commit()
                        
            except Exception as e:
                logger.error("failed_to_process_pending_approvals", error=str(e))

    def _generate_mock_snapshot(self, symbol: str) -> MarketSnapshot:
        """Generate mock market data for any symbol"""
        # Mock price ranges based on symbol
        prices = {
            "BTCUSDT": 68000.0,
            "ETHUSDT": 3500.0,
            "LINKUSDT": 18.0,
            "XRPUSDT": 0.6,
            "DOTUSDT": 7.5,
            "UNIUSDT": 10.0,
            "DOGEUSDT": 0.15
        }
        base_price = prices.get(symbol, 100.0)
        variation = random.uniform(-base_price * 0.02, base_price * 0.02)
        close = base_price + variation
        high = close + random.uniform(0, base_price * 0.01)
        low = close - random.uniform(0, base_price * 0.01)
        open_price = close + random.uniform(-base_price * 0.005, base_price * 0.005)
        volume = random.uniform(1000000, 5000000)

        return MarketSnapshot(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            spread=random.uniform(0.01, 0.5),
        )

    async def _fetch_binance_snapshot(self, symbol: str) -> MarketSnapshot | None:
        """Fetch real market data from Binance Testnet for a specific symbol"""
        try:
            # Get 1-minute klines
            klines = await self.exchange.get_klines(
                symbol=symbol,
                interval="1m",
                limit=1
            )
            
            if not klines or len(klines) == 0:
                logger.warning(f"no_klines_data_from_binance_for_{symbol}")
                return None
            
            # Parse latest kline
            latest_kline = klines[-1]
            open_price = float(latest_kline[1])
            high_price = float(latest_kline[2])
            low_price = float(latest_kline[3])
            close_price = float(latest_kline[4])
            volume = float(latest_kline[7])
            timestamp = int(latest_kline[0])
            
            # Get bid-ask spread
            ticker = await self.exchange.get_ticker_price(symbol)
            bid = float(ticker.get("bidPrice", close_price))
            ask = float(ticker.get("askPrice", close_price))
            spread = ask - bid if ask > bid else 0.01
            
            snapshot = MarketSnapshot(
                symbol=symbol,
                timestamp=datetime.utcfromtimestamp(timestamp / 1000),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                spread=spread,
            )
            
            logger.debug(f"binance_snapshot_fetched_{symbol}", close=close_price)
            return snapshot
            
        except Exception as e:
            logger.warning(f"binance_snapshot_fetch_failed_{symbol}", error=str(e), exc_info=True)
            return None

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("worker_shutting_down")
        self.running = False
        
        # Close Binance session if it was created
        if self.binance_session:
            await self.binance_session.close()
            logger.info("binance_session_closed")
        
        await close_db()
        logger.info("worker_shutdown_complete")


async def main():
    """Main entry point"""
    worker = TradingWorker()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig):
        logger.info("signal_received", signal=sig)
        asyncio.create_task(worker.shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        except NotImplementedError:
            signal.signal(sig, lambda s, f: asyncio.create_task(worker.shutdown()))

    try:
        await worker.initialize()
        await worker.run()
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
