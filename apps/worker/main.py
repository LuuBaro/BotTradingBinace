"""
Worker Main Loop - Trading engine orchestrator
Multi-tenant (SaaS) version
Coordinates AI decision making, risk validation, and execution for all active users
"""
import asyncio
import signal
import sys
import uuid
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from packages.shared.config import settings
from packages.shared.database import AsyncSessionFactory, init_db, close_db
from packages.shared.models import (
    User,
    UserCredential,
    BotConfig, 
    Decision as DecisionModel, 
    RiskLog, 
    Position, 
    Signal as SignalModel,
    Event,
    Event as EventModel,
    TraderContext,
    PromptPack
)
from packages.shared.schemas import RiskConfig, MarketSnapshot, Decision as DecisionSchema
from packages.shared.prompt_pack import PromptPackSchema
from packages.shared.enums import ActionType, Side, MarketRegime
from packages.shared.exchange.mock import MockExchange
from packages.shared.exchange.binance_futures import BinanceFuturesClient
from packages.shared.risk_engine import RiskEngine
from packages.shared.logger import logger
from apps.worker.engine.execution import ExecutionEngine
from apps.worker.engine.reconciler import ReconcilerEngine
from packages.shared.ai_orchestrator import AIOrchestrator
from packages.shared.llm_adapter import get_llm_adapter
from packages.shared.encryption import decrypt_key

class TradingWorker:
    """
    Multi-tenant trading worker orchestrator
    Iterates through all active users and executes their trading strategy
    """

    def __init__(self):
        self.running = False
        self.binance_session = None
        self.loop_count = 0
        # Keep per-user AI runtime to avoid recreating adapter/orchestrator every loop
        self._ai_runtime_by_user: dict[str, dict] = {}
        self.symbols_to_monitor = [
            "BTCUSDT", "ETHUSDT", "LINKUSDT", "XRPUSDT", 
            "DOTUSDT", "UNIUSDT", "DOGEUSDT", "SOLUSDT", 
            "ADAUSDT", "MATICUSDT", "AVAXUSDT"
        ]

    async def initialize(self) -> None:
        """Initialize worker shared resources"""
        logger.info("worker_initializing")
        await init_db()

        # Initialize SHARED Binance client session
        import aiohttp
        connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
        self.binance_session = aiohttp.ClientSession(connector=connector)
        logger.info("binance_session_initialized")

    async def _fetch_all_symbols(self, client: BinanceFuturesClient) -> list[str]:
        """Fetch all tradable USDT symbols from Binance"""
        try:
            info = await client.get_exchange_info()
            symbols = [
                s["symbol"] for s in info["symbols"] 
                if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
                and not s["symbol"].endswith("_ANT") # Skip custom pairs
            ]
            # Sort and pick top liquid ones (here just alphabetical for now)
            # or limit to a reasonable number to avoid long loop times
            return sorted(list(set(symbols)))[:30] 
        except Exception as e:
            logger.error(f"failed_to_fetch_symbols", error=str(e))
            return self.symbols_to_monitor
        
    async def _get_user_credentials(self, session: AsyncSession, user: User):
        """Fetch user-specific credentials with fallback for Admin"""
        res = await session.execute(select(UserCredential).where(UserCredential.user_id == user.id))
        cred = res.scalar_one_or_none()
        
        binance_keys = None
        if cred and cred.binance_api_key:
            binance_keys = {
                "api_key": decrypt_key(cred.binance_api_key),
                "api_secret": decrypt_key(cred.binance_api_secret),
                "testnet": cred.use_testnet
            }
        elif user.role == "admin":
            binance_keys = {
                "api_key": settings.binance_api_key,
                "api_secret": settings.binance_api_secret,
                "testnet": settings.binance_testnet
            }
            
        llm_config = None
        if cred and cred.ai_api_key:
            llm_config = {
                "provider": cred.ai_provider,
                "api_key": decrypt_key(cred.ai_api_key),
                "model": cred.ai_model,
                "custom_endpoint": cred.ai_custom_endpoint,
            }
        elif user.role == "admin":
            provider = (settings.selected_llm or "openai").lower()
            if provider == "openai":
                api_key = settings.bot_openai_api_key
                model = settings.openai_model
            elif provider in ("claude", "anthropic"):
                api_key = settings.bot_anthropic_api_key
                model = settings.anthropic_model
            elif provider in ("gemini", "google"):
                api_key = settings.bot_gemini_api_key
                model = settings.gemini_model
            elif provider == "groq":
                api_key = settings.bot_groq_api_key
                model = settings.groq_model
            elif provider == "mock":
                api_key = "mock"
                model = "mock-model"
            else:
                # Fallback for OpenAI-compatible providers (e.g. local)
                api_key = settings.bot_openai_api_key
                model = settings.openai_model

            llm_config = {
                "provider": provider,
                "api_key": api_key,
                "model": model,
                "custom_endpoint": None,
            }
            
        return binance_keys, llm_config

    def _get_or_create_orchestrator(self, user_id: str, llm_conf: dict) -> AIOrchestrator:
        """Reuse AI orchestrator per-user unless provider/model/key/endpoint changed."""
        fingerprint = (
            llm_conf.get("provider"),
            llm_conf.get("model"),
            llm_conf.get("api_key"),
            llm_conf.get("custom_endpoint"),
        )

        runtime = self._ai_runtime_by_user.get(user_id)
        if runtime and runtime.get("fingerprint") == fingerprint:
            return runtime["orchestrator"]

        llm = get_llm_adapter(
            provider=llm_conf["provider"],
            api_key=llm_conf["api_key"],
            model=llm_conf["model"],
            custom_endpoint=llm_conf.get("custom_endpoint"),
        )
        orchestrator = AIOrchestrator(llm)
        self._ai_runtime_by_user[user_id] = {
            "fingerprint": fingerprint,
            "orchestrator": orchestrator,
        }
        return orchestrator

    async def run(self) -> None:
        """Main dispatcher loop"""
        self.running = True
        logger.info("worker_started", loop_interval_sec=settings.worker_loop_interval_sec)
        
        last_heartbeat = 0
        
        while self.running:
            try:
                # 1. Heartbeat
                now_ts = datetime.now(timezone.utc).timestamp()
                if now_ts - last_heartbeat > 60:
                    async with AsyncSessionFactory() as session:
                        session.add(Event(
                            timestamp=datetime.now(timezone.utc),
                            level="INFO",
                            code="WORKER_HEARTBEAT",
                            message="Multi-tenant worker dispatcher active.",
                        ))
                        await session.commit()
                    last_heartbeat = now_ts

                # 2. Process all users
                async with AsyncSessionFactory() as session: # This session is for fetching users
                    users_res = await session.execute(
                        select(User).join(BotConfig, User.id == BotConfig.user_id).where(BotConfig.is_active == True).distinct()
                    )
                    active_users = users_res.scalars().all()
                    
                    for user in active_users:
                        if not self.running: break
                        try:
                            # Use a new session for each user's trading process
                            async with AsyncSessionFactory() as user_session:
                                await self._process_user_trading(user_session, user)
                        except Exception as user_err:
                            logger.error("user_trading_failed", user=user.username, error=str(user_err))
                            # No need to rollback the outer session, as user_session is isolated
                            # If user_session failed, it would have rolled back itself or committed what it could.

                self.loop_count += 1
                await asyncio.sleep(settings.worker_loop_interval_sec)
                
            except Exception as e:
                logger.error("worker_main_loop_error", error=str(e))
                await asyncio.sleep(10)

    async def _process_user_trading(self, session: AsyncSession, user: User) -> None:
        """Execute one full trading iteration for a single user"""
        # Fetch config
        cfg_res = await session.execute(
            select(BotConfig).where(BotConfig.user_id == user.id, BotConfig.is_active == True).order_by(desc(BotConfig.id))
        )
        bot_config = cfg_res.scalar_one_or_none()

        # Fetch Credentials
        bin_keys, llm_conf = await self._get_user_credentials(session, user)
        if not bin_keys or not llm_conf:
            logger.debug(f"Skipping user {user.username}: No credentials")
            return

        # Initialize Engines
        exchange = BinanceFuturesClient(
            api_key=bin_keys["api_key"], 
            api_secret=bin_keys["api_secret"], 
            testnet=bin_keys["testnet"]
        )
        exchange.session = self.binance_session
        await exchange.sync_server_time()

        orchestrator = self._get_or_create_orchestrator(user.id, llm_conf)

        if not bot_config:
            logger.warning(f"No active BotConfig for user {user.id}, using defaults")
            risk_config = RiskConfig()
            symbols = self.symbols_to_monitor
        else:
            risk_config = RiskConfig(**bot_config.risk_json)
            # Handle list, string or special 'ALL' keyword
            raw_symbols = bot_config.symbols_json
            if isinstance(raw_symbols, list):
                if raw_symbols == ["ALL"]:
                    symbols = await self._fetch_all_symbols(exchange)
                else:
                    symbols = raw_symbols
            elif isinstance(raw_symbols, str) and raw_symbols.upper() == "ALL":
                symbols = await self._fetch_all_symbols(exchange)
            else:
                symbols = self.symbols_to_monitor

        # Sync Mark Price cache
        try:
            # We skip full exchange mark price fetch due to time, 
            # each loop will fetch per-symbol
            pass
        except Exception:
            pass
        
        risk_engine = RiskEngine(risk_config)
        execution_engine = ExecutionEngine(exchange)
        reconciler = ReconcilerEngine(exchange)

        # 1. Sync State
        await reconciler.sync_positions(session, user_id=user.id)
        
        # 2. Dashboard Logic (PnL update for open positions)
        pos_res = await session.execute(select(Position).where(Position.user_id == user.id))
        db_positions = {p.symbol: p for p in pos_res.scalars().all()}
        
        # 0. User Heartbeat
        await self._log_user_event(session, user.id, "ENGINE_HEARTBEAT", f"Khởi động chu kỳ quét cho sếp {user.username}", {"symbols": len(symbols)})
        
        logger.info(f"Processing {len(symbols)} symbols for {user.username}")

        for symbol in symbols:
            trace_id = str(uuid.uuid4())
            
            # Detailed Scan Event
            await self._log_user_event(session, user.id, "SCAN_START", f"Đang quét dữ liệu thị trường {symbol}...", {"symbol": symbol})

            snapshot = await self._fetch_user_market_snapshot(exchange, symbol)
            if not snapshot:
                await self._log_user_event(session, user.id, "SCAN_FAILED", f"Không lấy được dữ liệu {symbol} (có thể sàn đang lag)", {"symbol": symbol}, level="WARNING")
                continue

            # Update PNL display
            if symbol in db_positions:
                pos = db_positions[symbol]
                p_close = snapshot.close
                p_entry = float(pos.entry_price)
                p_qty = float(pos.qty)
                pos.unrealized_pnl = (p_close - p_entry) * p_qty if pos.side == "LONG" else (p_entry - p_close) * p_qty
                pos.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await session.commit()

            # 3. AI Analysis
            # Build position list for AI
            ai_positions = []
            for p in db_positions.values():
                ai_positions.append({
                    "symbol": p.symbol, "side": p.side, "qty": p.qty, 
                    "entry_price": p.entry_price, "unrealized_pnl_usd": p.unrealized_pnl
                })

            import json as _json
            snap_dict = _json.loads(_json.dumps(snapshot.model_dump(), default=str))
            
            # Fetch user-specific trader expertise/context
            context_res = await session.execute(
                select(TraderContext)
                .where(TraderContext.user_id == user.id)
                .order_by(desc(TraderContext.timestamp))
                .limit(1)
            )
            trader_context_model = context_res.scalar_one_or_none()
            trader_prompt = trader_context_model.prompt if trader_context_model else None

            # Load user's actual PromptPack
            prompt_pack_model = None
            if bot_config.active_prompt_pack_id:
                pack_res = await session.execute(
                    select(PromptPack).where(PromptPack.id == bot_config.active_prompt_pack_id)
                )
                prompt_pack_model = pack_res.scalar_one_or_none()
            
            # Use AI to decide
            try:
                # Convert prompt pack content to schema
                prompt_pack_schema = None
                if prompt_pack_model:
                    import json
                    pack_data = prompt_pack_model.content_json if isinstance(prompt_pack_model.content_json, dict) else json.loads(prompt_pack_model.content_json)
                    try:
                        # Try to create PromptPackSchema from database content
                        prompt_pack_schema = PromptPackSchema(**pack_data)
                    except Exception as e:
                        logger.warning(f"Failed to load PromptPackSchema from DB: {e}. Will use default fallback.")
                
                # If no valid pack schema, create default
                if not prompt_pack_schema:
                    from packages.shared.prompt_pack import RegimeDefinition, EntryPlaybook, ExitPlaybook, Side, NoTradeCondition, RiskParameters
                    prompt_pack_schema = PromptPackSchema(
                        name="default_v1", 
                        version=1, 
                        active=True,
                        symbols=["BTCUSDT", "ETHUSDT", symbol],
                        regimes=[
                            RegimeDefinition(name="Strong Uptrend", indicators={"rsi": ">50", "price": "above ema20"}),
                            RegimeDefinition(name="Strong Downtrend", indicators={"rsi": "<50", "price": "below ema20"}),
                            RegimeDefinition(name="Consolidation", indicators={"atr": "low", "rsi": "40-60"})
                        ],
                        entry_playbooks=[
                            EntryPlaybook(side=Side.LONG, regime="Strong Uptrend", conditions=["rsi > 50", "price above ema20"], target_ratio=2.0),
                            EntryPlaybook(side=Side.SHORT, regime="Strong Downtrend", conditions=["rsi < 50", "price below ema20"], target_ratio=2.0)
                        ],
                        exit_playbooks=[
                            ExitPlaybook(side=Side.LONG, profit_target="2xR", stop_loss="entry - 1 ATR"),
                            ExitPlaybook(side=Side.SHORT, profit_target="2xR", stop_loss="entry + 1 ATR")
                        ],
                        no_trade_conditions=[],
                        risk_params=RiskParameters()
                    )
                    logger.info(f"Using default PromptPackSchema for symbol {symbol}")
                
                # Call AI orchestrator with real prompt pack + trader context
                ai_result = await orchestrator.make_decision(
                    market_snapshot=snap_dict,
                    prompt_pack=prompt_pack_schema,
                    current_positions=ai_positions,
                    trader_context=trader_prompt  # Pass the trader's natural language prompt
                )
                
                # Convert result to Decision schema
                if not ai_result["valid"] or not ai_result["decision"]:
                    decision = DecisionSchema(
                        regime=MarketRegime.RANGE,
                        action=ActionType.NONE,
                        symbol=symbol,
                        size_pct=0.01,
                        leverage=1,
                        confidence=0.0,
                        rationale=ai_result.get("errors", [{"error": "AI validation failed"}])[0].get("error", "Unknown error")
                    )
                else:
                    ai_out = ai_result["decision"]
                    # Convert DecisionType to ActionType
                    decision_type_map = {
                        "ENTRY": ActionType.OPEN,
                        "EXIT": ActionType.CLOSE,
                        "MODIFY": ActionType.HOLD,
                        "NO_TRADE": ActionType.NONE
                    }
                    action = decision_type_map.get(ai_out.decision_type, ActionType.NONE)
                    
                    # Extract stop loss and take profit from order spec
                    stop_loss = None
                    take_profit = None
                    side = None
                    entry_price = None
                    
                    if ai_out.order_spec:
                        stop_loss = ai_out.order_spec.stop_loss_price
                        # Take profit is the first TP price if multiple exist
                        if ai_out.order_spec.take_profit_prices:
                            take_profit = ai_out.order_spec.take_profit_prices[0]
                        # Convert BUY/SELL to long/short
                        order_side = ai_out.order_spec.side.upper() if ai_out.order_spec.side else None
                        if order_side == "BUY":
                            side = "long"
                        elif order_side == "SELL":
                            side = "short"
                        entry_price = ai_out.order_spec.entry_price
                    
                    # Convert AIDecisionOutput to Decision schema
                    decision = DecisionSchema(
                        regime=MarketRegime(ai_out.market_regime) if ai_out.market_regime else MarketRegime.RANGE,
                        action=action,
                        symbol=symbol,
                        side=side,
                        entry_price=entry_price,
                        size_pct=0.01,  # Default 1% position size
                        leverage=int(ai_out.order_spec.leverage) if ai_out.order_spec else 1,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        confidence=ai_out.confidence,
                        rationale=ai_out.rationale
                    )
            except Exception as e:
                # Record error as NO_TRADE decision for audit trail
                await self._log_user_event(session, user.id, "AI_ERROR", f"Lỗi phân tích AI cho {symbol}: {str(e)}", {"symbol": symbol}, level="ERROR")
                logger.error(f"AI decision error for {symbol}: {str(e)}")
                
                # Create NO_TRADE decision for failed AI analysis
                decision = DecisionSchema(
                    regime=MarketRegime.RANGE,
                    action=ActionType.NONE,
                    symbol=symbol,
                    size_pct=0.01,
                    leverage=1,
                    confidence=0.0,
                    rationale=f"AI analysis failed: {str(e)[:100]}"
                )

            if not decision or decision.action == ActionType.NONE:
                # Log that AI checked but found no signal
                rationale = getattr(decision, 'rationale', 'Không có tín hiệu rõ ràng')
                await self._log_user_event(session, user.id, "SCAN_NEUTRAL", f"AI đã soi {symbol} nhưng chưa trade: {rationale}", {"symbol": symbol, "regime": getattr(decision, 'market_regime', 'unknown')})
                
                # Record NO_TRADE decision for audit trail
                no_trade_decision = DecisionModel(
                    user_id=user.id,
                    trace_id=trace_id,
                    status="EXECUTED",
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                    decision_json=decision.model_dump() if decision else {},
                    confidence=decision.confidence if decision else 0.0,
                    regime=str(decision.regime) if decision and hasattr(decision, 'regime') else "UNKNOWN",
                    decision_type="NO_TRADE",
                    rationale=rationale
                )
                session.add(no_trade_decision)
                await session.commit()
                continue
            
            await self._log_user_event(session, user.id, "SIGNAL_DETECTED", f"🔥 AI phát hiện tín hiệu {decision.action} {symbol}!", {"symbol": symbol, "confidence": decision.confidence})

            # Create Signal for Neural Watchlist (shows opportunity before execution)
            entry_price = decision.entry_price or 0.0
            price_range = abs(entry_price * 0.003)  # ±0.3% range
            entry_zone = f"{entry_price - price_range:.2f}-{entry_price + price_range:.2f}"
            
            signal_side = str(decision.side) if decision.side else ("LONG" if "BUY" in str(decision.action).upper() else "SHORT")
            
            new_signal = SignalModel(
                user_id=user.id,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                symbol=symbol,
                side=signal_side,
                entry_zone=entry_zone,
                probability=decision.confidence,
                rationale=decision.rationale,
                status="ACTIVE",
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
            )
            session.add(new_signal)
            await session.commit()

            # Record valid decision for audit trail
            valid_decision = DecisionModel(
                user_id=user.id,
                trace_id=trace_id,
                status="PENDING_VALIDATION",
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                decision_json=decision.model_dump(),
                confidence=decision.confidence,
                regime=str(decision.regime) if hasattr(decision, 'regime') else "UNKNOWN",
                decision_type=str(decision.action) if hasattr(decision, 'action') else "UNKNOWN",
                rationale=decision.rationale
            )
            session.add(valid_decision)
            await session.commit()

            # 4. Risk Check
            # Use current price from snapshot and default balance
            current_price = snapshot.close if snapshot else 0.0
            account_balance = 1000.0  # Default balance for risk engine (can be updated with actual account balance)
            
            risk_result = await risk_engine.validate_decision(
                decision, 
                list(db_positions.values()), 
                account_balance,
                current_price
            )
            
            # Update decision status based on risk check
            valid_decision.status = "APPROVED" if risk_result.approved else "REJECTED"
            session.add(valid_decision)
            await session.commit()
            
            # 5. Execution
            if risk_result.approved:
                valid_decision.status = "EXECUTED"
                session.add(valid_decision)
                await session.commit()
                
                # Mark Signal as TRIGGERED in watchlist
                signal_result = await session.execute(
                    select(SignalModel)
                    .where(SignalModel.user_id == user.id)
                    .where(SignalModel.symbol == symbol)
                    .where(SignalModel.status == "ACTIVE")
                    .order_by(desc(SignalModel.timestamp))
                    .limit(1)
                )
                triggered_signal = signal_result.scalar_one_or_none()
                if triggered_signal:
                    triggered_signal.status = "TRIGGERED"
                    session.add(triggered_signal)
                    await session.commit()
                
                if bot_config.approval_mode:
                    await self._record_order_intent(session, user.id, decision, risk_result, trace_id)
                else:
                    await execution_engine.execute_decision(session, user.id, decision, trace_id)
            else:
                await self._log_risk_failure(session, user.id, symbol, decision, risk_result, trace_id)

    async def _fetch_user_market_snapshot(self, exchange, symbol: str) -> MarketSnapshot | None:
        """Fetch market snapshot using specific exchange client"""
        try:
            klines = await exchange.get_klines(symbol, "15m", limit=20)
            if not klines or len(klines) == 0:
                 return None
            
            last_k = klines[-1]
            return MarketSnapshot(
                symbol=symbol,
                timestamp=datetime.now(timezone.utc),
                open=float(last_k[1]),
                high=float(last_k[2]),
                low=float(last_k[3]),
                close=float(last_k[4]),
                volume=float(last_k[5]),
                interval="15m"
            )
        except Exception as e:
            logger.error(f"Snapshot failed for {symbol}: {e}")
            return None

    async def _log_user_event(self, session: AsyncSession, user_id: str, code: str, message: str, data: dict = None, level: str = "INFO"):
        """Save a user-specific system event for the UI/Chat to consume"""
        from packages.shared.models import Event
        event = Event(
            user_id=user_id,
            code=code,
            message=message,
            level=level,
            data_json=data or {}
        )
        session.add(event)
        await session.commit()
        # Note: Broadcaster in apps/api/main.py will pick this up automatically via polling

    async def _record_order_intent(self, session, user_id, decision, risk_result, trace_id):
        intent = DecisionModel(
            user_id=user_id,
            trace_id=trace_id,
            status="PENDING_APPROVAL",
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            decision_json=decision.model_dump(),
            confidence=decision.confidence,
            regime="SIDEWAYS",
            rationale=decision.rationale or "Manual approval required"
        )
        session.add(intent)
        await session.commit()

    async def _log_risk_failure(self, session, user_id, symbol, decision, risk_result, trace_id):
        log = RiskLog(
            trace_id=trace_id,
            result="rejected",
            reason=risk_result.reason,
            user_id=user_id
        )
        session.add(log)
        session.add(Event(
            user_id=user_id,
            level="WARNING",
            code="RISK_REJECTED",
            message=f"Risk engine rejected {decision.action} on {symbol}: {risk_result.reason}",
            trace_id=trace_id
        ))
        await session.commit()

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("worker_shutting_down")
        self.running = False
        if self.binance_session:
            await self.binance_session.close()
        self._ai_runtime_by_user.clear()
        await close_db()
        logger.info("worker_shutdown_complete")

async def main():
    worker = TradingWorker()
    loop = asyncio.get_event_loop()
    def signal_handler(sig):
        asyncio.create_task(worker.shutdown())
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        except NotImplementedError:
            pass

    try:
        await worker.initialize()
        await worker.run()
    except Exception as e:
        logger.critical(f"Fatal worker error: {str(e)}")
    finally:
        await worker.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
