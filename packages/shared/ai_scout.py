"""
AI Scout - Lightweight market scanner for 2-tier LLM cascade
Scans many symbols quickly with minimal tokens, returns simple signals
"""
import json
from typing import Dict, Any, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from packages.shared.logger import logger

if TYPE_CHECKING:
    from packages.shared.llm_adapter import LLMAdapter


class ScoutSignal(BaseModel):
    """Lightweight signal output from scout (much smaller than full AIDecisionOutput)"""
    symbol: str
    regime: str = Field(description="Market regime (Trending Up/Down, Range Bound, Volatile)")
    action_hint: str = Field(description="ENTRY, EXIT, HOLD, or OBSERVE")
    confidence: float = Field(ge=0.0, le=1.0, description="Signal confidence 0-1")
    priority_score: float = Field(ge=0.0, le=10.0, description="How urgently this needs attention (0-10)")
    risk_flags: list[str] = Field(default_factory=list, description="Quick risk warnings")
    reasoning: str = Field(max_length=200, description="Brief 1-2 sentence rationale")


class AIScout:
    """
    Lightweight AI scanner that quickly evaluates many symbols
    Uses minimal tokens per symbol to identify high-value opportunities
    """

    def __init__(self, llm_adapter: "LLMAdapter"):
        self.llm = llm_adapter
        self.scan_count = 0
        self.error_count = 0

    async def scan_symbol(
        self,
        symbol: str,
        market_snapshot: Dict[str, Any],
        has_open_position: bool = False,
        current_pnl: Optional[float] = None,
    ) -> Optional[ScoutSignal]:
        """
        Quick scan of one symbol - minimal token usage
        
        Returns:
            ScoutSignal if valid, None if error
        """
        self.scan_count += 1

        try:
            # Build ultra-compact prompt (no verbose instructions)
            prompt = self._build_compact_prompt(
                symbol, market_snapshot, has_open_position, current_pnl
            )

            # Call LLM
            raw_response, tokens_used = await self.llm.generate(prompt)
            
            logger.debug(f"scout_tokens symbol={symbol} tokens={tokens_used}")

            # Parse response
            signal_dict = self._parse_response(raw_response)
            if not signal_dict:
                logger.warning(f"scout_parse_failed symbol={symbol}")
                return None

            signal = ScoutSignal(**signal_dict)
            return signal

        except Exception as e:
            self.error_count += 1
            logger.error(f"scout_scan_failed symbol={symbol} error={str(e)}")
            return None

    def _build_compact_prompt(
        self,
        symbol: str,
        snapshot: Dict[str, Any],
        has_position: bool,
        pnl: Optional[float],
    ) -> str:
        """Build minimal prompt to reduce tokens"""
        close = snapshot.get("close", 0)
        volume = snapshot.get("volume", 0)
        spread = snapshot.get("spread", 0)

        position_ctx = ""
        if has_position:
            position_ctx = f"\n🔴 OPEN POSITION | PnL: ${pnl:.2f}"

        prompt = f"""Market Scanner - Quick Analysis

Symbol: {symbol}
Price: {close}
Volume: {volume}
Spread: {spread}{position_ctx}

Task: Rapid assessment for this symbol.
Output JSON only (no markdown):
{{
  "symbol": "{symbol}",
  "regime": "Trending Up" | "Trending Down" | "Range Bound" | "Volatile",
  "action_hint": "ENTRY" | "EXIT" | "HOLD" | "OBSERVE",
  "confidence": 0.0-1.0,
  "priority_score": 0-10 (higher = more urgent),
  "risk_flags": ["flag1", "flag2"],
  "reasoning": "1-2 sentence reason"
}}

Rules:
- If position open + losing: action_hint=EXIT, priority_score high
- If position open + profit target near: action_hint=EXIT, priority_score high
- If strong trend + no position: action_hint=ENTRY, confidence reflects strength
- If sideways/low volume: action_hint=OBSERVE, priority_score low

Respond:"""

        return prompt

    def _parse_response(self, raw: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response"""
        try:
            # Remove markdown if present
            text = raw.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            # Parse
            data = json.loads(text.strip())
            return data

        except Exception as e:
            logger.warning(f"scout_json_parse_error: {e} | raw: {raw[:200]}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Scout statistics"""
        return {
            "total_scans": self.scan_count,
            "errors": self.error_count,
            "success_rate": (self.scan_count - self.error_count) / max(self.scan_count, 1),
            "model": self.llm.model,
        }
