"""
AI Orchestrator - Manages AI trading decisions
Fetches market snapshot, loads prompt pack, calls LLM, validates output
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from packages.shared.prompt_pack import PromptPackSchema, PromptPackSummary
from packages.shared.ai_decision import AIDecisionOutput, DecisionValidationResult, DecisionValidationError
from packages.shared.llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """Orchestrates AI trading decision process"""

    def __init__(self, llm_adapter: LLMAdapter):
        """
        Initialize orchestrator
        
        Args:
            llm_adapter: LLM provider adapter
        """
        self.llm = llm_adapter
        self.decision_count = 0
        self.error_count = 0
        # Cache parsed trader intent so we don't re-parse every loop
        self._cached_intent: Optional[Dict[str, Any]] = None
        self._cached_intent_hash: Optional[str] = None

    async def parse_trader_intent(self, trader_context: str) -> Dict[str, Any]:
        """
        Use LLM to intelligently parse the trader's natural language prompt
        and extract structured trading parameters that the system can act on.
        
        This is the core intelligence layer - AI reads the trader's intent
        just like two humans talking, then converts it into structured rules
        the system can use for proactive monitoring and decision-making.
        
        Returns a dict with extracted parameters, e.g.:
        {
          "profit_target_usd": 2.0,
          "max_loss_usd": null,
          "max_loss_pct": 0.75,
          "max_hold_minutes": null,
          "min_win_rate_pct": 80,
          "preferred_timeframes": ["5m", "15m"],
          "capital_usd": 200,
          "strategy_summary": "Short-term mean reversion, fixed $2 profit target per trade",
          "exit_conditions": ["profit >= $2", "stop loss hit", "trend reversal"],
          "notes": "Fee-aware: use STOP_LIMIT for cheaper fees"
        }
        """
        import hashlib
        context_hash = hashlib.md5(trader_context.encode()).hexdigest()
        
        # Return cached result if same context
        if self._cached_intent and self._cached_intent_hash == context_hash:
            return self._cached_intent
        
        parse_prompt = f"""You are a trading strategy analyst. A trader has written their trading strategy in natural language.
Your job is to READ and UNDERSTAND exactly what the trader wants, then extract structured parameters.

Think like you are having a conversation with the trader and understanding their goals.
Extract the key trading parameters from their description.

## Trader's Strategy Description:
---
{trader_context}
---

Extract the following parameters from the trader's description. 
IMPORTANT: 
- "Lợi nhuận 2$/lệnh" means profit_target_usd = 2.0. 
- "Cắt lỗ 5$/lệnh" means max_loss_usd = 5.0.
- If a parameter is not mentioned, set it to null.
- Think carefully about implied meaning from the trader's context.

Respond with ONLY valid JSON (no markdown):
{{
  "profit_target_usd": <number or null>,
  "profit_target_pct": <number or null, e.g. 0.02 = 2%>,
  "max_loss_usd": <number or null>,
  "max_loss_pct": <number or null>,
  "capital_usd": <number or null>,
  "leverage_min": <number or null>,
  "leverage_max": <number or null>,
  "max_hold_minutes": <number or null>,
  "min_win_rate_pct": <number or null, e.g. 80 means 80% win rate target>,
  "preferred_timeframes": <list of strings like ["5m","15m"] or null>,
  "entry_style": <"scalp"|"swing"|"mean_reversion"|"breakout" or null>,
  "exit_style": <"fixed_profit"|"trailing"|"tp_sl"|"time_based" or null>,
  "fee_aware": <true|false>,
  "strategy_summary": "<one sentence summary of the trader's strategy>",
  "exit_conditions": ["<condition 1>", "<condition 2>"],
  "key_rules": ["<rule 1>", "<rule 2>"]
}}
"""
        try:
            raw = await self.llm.generate(parse_prompt)
            # Parse response
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            intent = json.loads(raw)
            self._cached_intent = intent
            self._cached_intent_hash = context_hash
            logger.info(
                "trader_intent_parsed",
                profit_target_usd=intent.get("profit_target_usd"),
                strategy=intent.get("strategy_summary", "unknown")
            )
            return intent
        except Exception as e:
            logger.warning(f"Failed to parse trader intent: {e}. Using empty intent.")
            return {}

    async def make_decision(
        self,
        market_snapshot: Dict[str, Any],
        prompt_pack: PromptPackSchema,
        current_positions: Optional[List[Dict[str, Any]]] = None,
        trader_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make trading decision based on market snapshot and prompt pack
        
        Args:
            market_snapshot: Current market data (ohlcv, indicators, spreads, funding)
            prompt_pack: Trader-defined trading rules
            current_positions: List of current open positions
            trader_context: Optional historical context/expertise from trader
            
        Returns:
            {
                "valid": bool,
                "decision": AIDecisionOutput or None,
                "errors": List[Dict] or [],
                "raw_response": str,
                "timestamp": datetime
            }
        """
        self.decision_count += 1

        try:
            # Step 1: Validate inputs
            if not market_snapshot:
                return self._error_response("Market snapshot is empty")

            if not prompt_pack or not prompt_pack.active:
                return self._error_response("Prompt pack not active or invalid")

            # Step 2: Parse trader intent from their natural language context
            # This is the core intelligence: AI reads the trader's words and understands what they want
            parsed_intent: Dict[str, Any] = {}
            if trader_context:
                parsed_intent = await self.parse_trader_intent(trader_context)

            # Step 3: Check no-trade conditions
            no_trade_reason = self._check_no_trade_conditions(prompt_pack, market_snapshot)
            if no_trade_reason:
                return {
                    "valid": True,
                    "decision": AIDecisionOutput(
                        decision_type="NO_TRADE",
                        confidence=1.0,
                        rationale=no_trade_reason,
                        market_regime="Unknown",
                        order_spec=None
                    ),
                    "errors": [],
                    "raw_response": no_trade_reason,
                    "timestamp": datetime.utcnow(),
                    "parsed_intent": parsed_intent,
                    "tokens_used": 0
                }

            # Step 4: Build LLM prompt - inject parsed trader intent for dynamic behavior
            prompt = self._build_prompt(
                market_snapshot, prompt_pack, current_positions, trader_context, parsed_intent
            )

            # Step 5: Call LLM
            logger.info(f"Calling LLM ({self.llm.model}) for decision")
            raw_response, tokens_used = await self.llm.generate(prompt)

            # Step 6: Parse response
            decision_dict = self._parse_llm_response(raw_response)
            if not decision_dict:
                return self._error_response(f"Failed to parse LLM response: {raw_response[:200]}")

            # Step 7: Validate against schema
            validation_result = self._validate_decision(decision_dict, prompt_pack)
            if not validation_result.valid:
                errors = [
                    {"field": e.field, "error": e.error, "value": str(e.value)}
                    for e in validation_result.errors
                ]
                return {
                    "valid": False,
                    "decision": None,
                    "errors": errors,
                    "raw_response": raw_response[:500],
                    "timestamp": datetime.utcnow(),
                    "parsed_intent": parsed_intent,
                    "tokens_used": tokens_used
                }

            # Step 8: Create AIDecisionOutput
            decision = AIDecisionOutput(**decision_dict)

            # Step 9: Additional business logic validation
            business_errors = self._validate_business_logic(decision, prompt_pack, current_positions)
            if business_errors:
                return {
                    "valid": False,
                    "decision": None,
                    "errors": business_errors,
                    "raw_response": raw_response[:500],
                    "timestamp": datetime.utcnow(),
                    "parsed_intent": parsed_intent,
                    "tokens_used": tokens_used
                }

            logger.info(f"✅ Valid decision generated: {decision.decision_type} ({decision.confidence:.2%} confidence)")

            return {
                "valid": True,
                "decision": decision,
                "errors": [],
                "raw_response": raw_response,
                "timestamp": datetime.utcnow(),
                "parsed_intent": parsed_intent,  # Worker uses this for proactive monitoring
                "tokens_used": tokens_used
            }

        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ Decision generation failed: {str(e)}")
            return self._error_response(f"Exception: {str(e)}")


    def _check_no_trade_conditions(
        self,
        prompt_pack: PromptPackSchema,
        market_snapshot: Dict[str, Any]
    ) -> Optional[str]:
        """Check if any no-trade conditions are triggered"""
        for condition in prompt_pack.no_trade_conditions:
            # Parse condition triggers against snapshot
            # This is simplified - real implementation would check actual conditions
            for trigger in condition.triggers:
                # Check if trigger is present in market conditions
                market_conditions = market_snapshot.get("conditions", {})
                if trigger in market_conditions and market_conditions[trigger]:
                    return f"No trade: {condition.name} triggered ({trigger})"
        return None

    def _build_prompt(
        self,
        market_snapshot: Dict[str, Any],
        prompt_pack: PromptPackSchema,
        current_positions: Optional[List[Dict[str, Any]]] = None,
        trader_context: Optional[str] = None,
        parsed_intent: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build LLM prompt with market snapshot, trading rules and dynamically parsed trader intent"""

        # Build summary from prompt pack
        summary = self._build_prompt_pack_summary(prompt_pack)

        # Format market snapshot
        market_str = self._serialize_json(market_snapshot)

        # Format current positions if any
        positions_str = "No open positions"
        if current_positions:
            positions_str = self._serialize_json(current_positions)

        # Build dynamic exit rules section from parsed trader intent
        intent_section = ""
        if parsed_intent:
            profit_target = parsed_intent.get("profit_target_usd")
            exit_conditions = parsed_intent.get("exit_conditions", [])
            key_rules = parsed_intent.get("key_rules", [])
            strategy_summary = parsed_intent.get("strategy_summary", "")
            max_hold = parsed_intent.get("max_hold_minutes")
            max_loss = parsed_intent.get("max_loss_usd")
            capital = parsed_intent.get("capital_usd")

            intent_lines = []
            if strategy_summary:
                intent_lines.append(f"**Strategy understood:** {strategy_summary}")
            if capital:
                intent_lines.append(f"**Trading capital:** ${capital}")
            if profit_target is not None:
                intent_lines.append(f"**Profit target per trade:** ${profit_target} USD → EXIT immediately when reached")
            if max_loss is not None:
                intent_lines.append(f"**Max loss per trade:** ${max_loss} USD → EXIT immediately if loss exceeds this")
            if max_hold is not None:
                intent_lines.append(f"**Max hold time:** {max_hold} minutes → EXIT if position open longer")
            if exit_conditions:
                intent_lines.append("**Trader-defined exit conditions:**")
                for cond in exit_conditions:
                    intent_lines.append(f"  - {cond}")
            if key_rules:
                intent_lines.append("**Key trading rules:**")
                for rule in key_rules:
                    intent_lines.append(f"  - {rule}")

            if intent_lines:
                intent_section = "## ⚡ PARSED TRADER INTENT (extracted from trader's own words)\n" + "\n".join(intent_lines) + "\n"

        # Build dynamic exit rule for the STRICT RULES section
        profit_target_rule = ""
        if parsed_intent and parsed_intent.get("profit_target_usd") is not None:
            pt = parsed_intent["profit_target_usd"]
            profit_target_rule = f"2. **EXIT MANDATORY if unrealized_pnl_usd >= {pt} (trader's profit target)**"
        else:
            profit_target_rule = "2. **EXIT if profit target from trader's strategy is reached (check strategy context)**"

        prompt = f"""You are a professional trading AI executing a trader's strategy in real-time.
Your job is to UNDERSTAND the trader's strategy (written below in their own words) and act exactly as they intended.

{f"## Trader's Full Strategy Context" if trader_context else ""}
{trader_context if trader_context else ""}

{intent_section}
## HOW TO THINK (priority order - ALWAYS follow this):

### 🔴 PRIORITY 1 — MANAGE OPEN POSITIONS FIRST
If there are open positions below, YOU MUST evaluate them BEFORE anything else:
- Compare `unrealized_pnl_usd` against the trader's profit target
- Compare current price against `take_profit` and `stop_loss` levels  
- Consider how long the position has been open (`opened_at`)
- **If the trader's profit target is met → EXIT NOW. Do not hesitate.**
- **If stop loss hit → EXIT NOW.**
- Do NOT open more positions for the same symbol if one is already open.

### 🟡 PRIORITY 2 — NEW ENTRY (only if no position for this symbol)
Only propose a new ENTRY if there is no open position for this symbol AND market conditions match the trader's strategy.  
Calculate exact entry_price, stop_loss_price, take_profit_prices that would meet the trader's profit target (accounting for fees if fee_aware is true).

### 🟢 PRIORITY 3 — NO_TRADE  
Return NO_TRADE if conditions are unclear, risky, or don't match the strategy.

## Trading Ruleset (Prompt Pack)
{summary.to_prompt()}

## Current Market Data
```json
{market_str}
```

## Open Positions — CHECK THESE FIRST
```json
{positions_str}
```

## Response Format (valid JSON only, no markdown):
{{
  "decision_type": "ENTRY|EXIT|MODIFY|NO_TRADE",
  "confidence": 0.0-1.0,
  "rationale": "Explain your decision. If position open, mention its current PnL vs target.",
  "market_regime": "Trending Up|Trending Down|Range Bound|Sideways|Volatile",
  "timeframe_analysis": {{"5m": "...", "15m": "...", "1h": "..."}},
  "order_spec": {{
    "symbol": "BTCUSDT",
    "side": "BUY|SELL",
    "quantity": 0.001,
    "entry_price": 65000.0,
    "stop_loss_price": 64500.0,
    "take_profit_prices": [65200.0],
    "leverage": 5.0
  }},
  "checklist_results": [
    {{"name": "Profit target check", "passed": true, "reason": "PnL $2.3 >= target $2.0"}}
  ],
  "risk_assessment": {{
    "risk_reward_ratio": 2.0,
    "position_pct": 5.0,
    "expected_profit_usd": 2.0
  }}
}}

STRICT EXECUTION RULES:
1. Respond with ONLY valid JSON — no explanations, no markdown
{profit_target_rule}
3. **EXIT MANDATORY if price crossed take_profit level**
4. **EXIT MANDATORY if price crossed stop_loss level**
5. For ENTRY: calculate TP price that achieves trader's exact profit target (after fees)
6. Confidence >= {prompt_pack.min_analysis_confidence} required for ENTRY
7. Risk/reward >= {prompt_pack.risk_params.min_risk_ratio}
8. Position size <= {prompt_pack.risk_params.max_position_pct}%
9. Leverage <= {prompt_pack.risk_params.max_leverage}x
10. For EXIT, order_spec can be null (system handles execution)
"""

        return prompt


    def _build_prompt_pack_summary(self, prompt_pack: PromptPackSchema) -> PromptPackSummary:
        """Convert prompt pack to concise summary for LLM"""

        # Format regimes
        regimes_md = "\n".join([
            f"- **{r.name}**: {r.indicators} - {r.description}"
            for r in prompt_pack.regimes
        ])

        # Format entry rules
        entry_md = "\n".join([
            f"- **{e.side}** in {e.regime}: {', '.join(e.conditions)} (ratio {e.target_ratio}:1, conf >= {e.confidence_threshold})"
            for e in prompt_pack.entry_playbooks
        ])

        # Format exit rules
        exit_md = "\n".join([
            f"- **{e.side}** exit: TP={e.profit_target}, SL={e.stop_loss}"
            for e in prompt_pack.exit_playbooks
        ])

        # Format no-trade rules
        no_trade_md = "\n".join([
            f"- {c.name}: {', '.join(c.triggers)} (avoid for {c.duration_minutes}m if triggered)"
            for c in prompt_pack.no_trade_conditions
        ]) or "None"

        return PromptPackSummary(
            regimes=regimes_md,
            entry_rules=entry_md,
            exit_rules=exit_md,
            no_trade_rules=no_trade_md,
            risk_limits=prompt_pack.risk_params.dict(),
            symbols=prompt_pack.symbols
        )

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response as JSON"""
        try:
            # Try to extract JSON from response
            # LLM might return markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected parsing error: {e}")
            return None

    def _validate_decision(
        self,
        decision_dict: Dict[str, Any],
        prompt_pack: PromptPackSchema
    ) -> DecisionValidationResult:
        """Validate decision against schema"""
        errors: List[DecisionValidationError] = []

        # Required fields
        required_fields = ["decision_type", "confidence", "rationale", "market_regime"]
        for field in required_fields:
            if field not in decision_dict or decision_dict[field] is None:
                errors.append(DecisionValidationError(
                    field=field,
                    error=f"Required field missing",
                    value=None
                ))

        # Validate confidence
        if "confidence" in decision_dict:
            conf = decision_dict["confidence"]
            if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
                errors.append(DecisionValidationError(
                    field="confidence",
                    error="Must be number between 0.0 and 1.0",
                    value=conf
                ))

        # Validate decision type
        if "decision_type" in decision_dict:
            valid_types = ["ENTRY", "EXIT", "MODIFY", "NO_TRADE"]
            if decision_dict["decision_type"] not in valid_types:
                errors.append(DecisionValidationError(
                    field="decision_type",
                    error=f"Must be one of {valid_types}",
                    value=decision_dict["decision_type"]
                ))

        # For ENTRY/MODIFY, validate order_spec
        if decision_dict.get("decision_type") in ["ENTRY", "MODIFY"]:
            if not decision_dict.get("order_spec"):
                errors.append(DecisionValidationError(
                    field="order_spec",
                    error="Required for ENTRY/MODIFY decisions",
                    value=None
                ))
            else:
                # Validate order spec
                order_spec = decision_dict["order_spec"]
                required_order_fields = ["symbol", "side", "quantity", "entry_price", "stop_loss_price"]
                for field in required_order_fields:
                    if field not in order_spec:
                        errors.append(DecisionValidationError(
                            field=f"order_spec.{field}",
                            error="Required field in order specification",
                            value=None
                        ))

                # Validate leverage
                if "leverage" in order_spec:
                    leverage = order_spec["leverage"]
                    if leverage > prompt_pack.risk_params.max_leverage:
                        errors.append(DecisionValidationError(
                            field="order_spec.leverage",
                            error=f"Exceeds max {prompt_pack.risk_params.max_leverage}x",
                            value=leverage
                        ))

        # Validate confidence threshold
        if decision_dict.get("decision_type") == "ENTRY":
            conf = decision_dict.get("confidence", 0)
            if conf < prompt_pack.min_analysis_confidence:
                errors.append(DecisionValidationError(
                    field="confidence",
                    error=f"Below minimum threshold {prompt_pack.min_analysis_confidence}",
                    value=conf
                ))

        return DecisionValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )

    def _validate_business_logic(
        self,
        decision: AIDecisionOutput,
        prompt_pack: PromptPackSchema,
        current_positions: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Validate business logic constraints"""
        errors: List[Dict[str, Any]] = []

        if decision.decision_type == "ENTRY" and decision.order_spec:
            order = decision.order_spec

            # Check risk/reward ratio
            if order.stop_loss_price and order.take_profit_prices:
                risk = abs(order.entry_price - order.stop_loss_price)
                reward = abs(order.take_profit_prices[0] - order.entry_price) if order.take_profit_prices else risk
                if reward > 0:
                    ratio = reward / risk
                    if ratio < prompt_pack.risk_params.min_risk_ratio:
                        errors.append({
                            "field": "risk_reward_ratio",
                            "error": f"Ratio {ratio:.2f} below minimum {prompt_pack.risk_params.min_risk_ratio}",
                            "value": ratio
                        })

            # Check position size
            if decision.risk_assessment and "position_pct" in decision.risk_assessment:
                pos_pct = decision.risk_assessment["position_pct"]
                if pos_pct > prompt_pack.risk_params.max_position_pct:
                    errors.append({
                        "field": "position_size",
                        "error": f"Position {pos_pct}% exceeds max {prompt_pack.risk_params.max_position_pct}%",
                        "value": pos_pct
                    })

            # Check max concurrent positions
            if current_positions:
                if len(current_positions) >= prompt_pack.risk_params.max_concurrent_positions:
                    errors.append({
                        "field": "max_positions",
                        "error": f"Already at max {prompt_pack.risk_params.max_concurrent_positions} positions",
                        "value": len(current_positions)
                    })

        return errors

    def _error_response(self, reason: str) -> Dict[str, Any]:
        """Generate error response"""
        self.error_count += 1
        return {
            "valid": False,
            "decision": None,
            "errors": [{"error": reason}],
            "raw_response": "",
            "timestamp": datetime.utcnow(),
            "tokens_used": 0
        }

    def _serialize_json(self, data: Any) -> str:
        """Helper to serialize dict with datetime and other complex types"""
        def default(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)
            
        return json.dumps(data, indent=2, default=default)

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            "total_decisions": self.decision_count,
            "errors": self.error_count,
            "success_rate": (self.decision_count - self.error_count) / max(self.decision_count, 1),
            "model": self.llm.model
        }
