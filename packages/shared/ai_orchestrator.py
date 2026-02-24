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

    async def make_decision(
        self,
        market_snapshot: Dict[str, Any],
        prompt_pack: PromptPackSchema,
        current_positions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Make trading decision based on market snapshot and prompt pack
        
        Args:
            market_snapshot: Current market data (ohlcv, indicators, spreads, funding)
            prompt_pack: Trader-defined trading rules
            current_positions: List of current open positions
            
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

            # Step 2: Check no-trade conditions
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
                    "timestamp": datetime.utcnow()
                }

            # Step 3: Build LLM prompt
            prompt = self._build_prompt(market_snapshot, prompt_pack, current_positions)

            # Step 4: Call LLM
            logger.info(f"Calling LLM ({self.llm.model}) for decision")
            raw_response = await self.llm.generate(prompt)

            # Step 5: Parse response
            decision_dict = self._parse_llm_response(raw_response)
            if not decision_dict:
                return self._error_response(f"Failed to parse LLM response: {raw_response[:200]}")

            # Step 6: Validate against schema
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
                    "timestamp": datetime.utcnow()
                }

            # Step 7: Create AIDecisionOutput
            decision = AIDecisionOutput(**decision_dict)

            # Step 8: Additional business logic validation
            business_errors = self._validate_business_logic(decision, prompt_pack, current_positions)
            if business_errors:
                return {
                    "valid": False,
                    "decision": None,
                    "errors": business_errors,
                    "raw_response": raw_response[:500],
                    "timestamp": datetime.utcnow()
                }

            logger.info(f"✅ Valid decision generated: {decision.decision_type} ({decision.confidence:.2%} confidence)")

            return {
                "valid": True,
                "decision": decision,
                "errors": [],
                "raw_response": raw_response,
                "timestamp": datetime.utcnow()
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
        current_positions: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Build LLM prompt with market snapshot and trading rules"""

        # Build summary from prompt pack
        summary = self._build_prompt_pack_summary(prompt_pack)

        # Format market snapshot
        market_str = json.dumps(market_snapshot, indent=2)

        # Format current positions if any
        positions_str = "No open positions"
        if current_positions:
            positions_str = json.dumps(current_positions, indent=2)

        prompt = f"""You are a professional trading AI making real-time trading decisions.

## Your Task
Analyze the market and decide whether to:
1. ENTRY: Open a new position
2. EXIT: Close an existing position
3. MODIFY: Adjust an existing position
4. NO_TRADE: Wait for better setup

ALL responses must be valid JSON matching the schema below.

## Trading Rules (from Prompt Pack)
{summary.to_prompt()}

## Current Market Snapshot
```json
{market_str}
```

## Current Open Positions
```json
{positions_str}
```

## Decision Schema (respond with ONLY valid JSON)
{{
  "decision_type": "ENTRY|EXIT|MODIFY|NO_TRADE",
  "confidence": 0.0-1.0,
  "rationale": "explanation",
  "market_regime": "identified regime name",
  "timeframe_analysis": {{"15m": "...", "1h": "...", "4h": "..."}},
  "order_spec": {{
    "symbol": "ETHUSDT",
    "side": "BUY|SELL",
    "quantity": 10.0,
    "entry_price": 2500.0,
    "stop_loss_price": 2450.0,
    "take_profit_prices": [2550.0, 2600.0],
    "leverage": 1.0-{prompt_pack.risk_params.max_leverage}
  }},
  "checklist_results": [
    {{"name": "...", "passed": true|false, "reason": "..."}}
  ],
  "risk_assessment": {{
    "risk_reward_ratio": 2.0,
    "position_pct": 5.0,
    "daily_loss_pct": 0.5
  }}
}}

IMPORTANT RULES:
1. Respond ONLY with valid JSON, no markdown or explanations
2. Confidence must be >= {prompt_pack.min_analysis_confidence} to propose trade
3. Risk/reward ratio must be >= {prompt_pack.risk_params.min_risk_ratio}
4. Position size must be <= {prompt_pack.risk_params.max_position_pct}%
5. Leverage must be <= {prompt_pack.risk_params.max_leverage}x
6. All checklist items must pass if marked required
7. If uncertain, return NO_TRADE
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
            "timestamp": datetime.utcnow()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            "total_decisions": self.decision_count,
            "errors": self.error_count,
            "success_rate": (self.decision_count - self.error_count) / max(self.decision_count, 1),
            "model": self.llm.model
        }
