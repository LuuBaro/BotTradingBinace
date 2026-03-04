"""
Prompt Management System - Tối ưu hóa prompts cho các chế độ khác nhau
Hỗ trợ 3 mức độ chi tiết: lightweight, standard, heavyweight
Flexible cho 2-tier hybrid, 2-tier same, hoặc single-tier
"""

from typing import Literal, Dict, Any
from pydantic import BaseModel, Field

PromptLevel = Literal["lightweight", "standard", "heavyweight"]
WorkerMode = Literal["two_tier_hybrid", "two_tier_same", "single_tier"]


class PromptConfig(BaseModel):
    """Cấu hình prompts dựa trên mode và level"""

    mode: WorkerMode = Field(
        default="two_tier_hybrid",
        description="two_tier_hybrid (2 cloud LLM), two_tier_same (1 local x2), single_tier (1 model)"
    )
    prompt_level: PromptLevel = Field(
        default="standard",
        description="lightweight (tiết kiệm token), standard (cân bằng), heavyweight (tối ưu chất lượng)"
    )

    def get_scout_prompt_builder(self):
        """Trả về hàm build SCOUT prompt phù hợp"""
        if self.prompt_level == "lightweight":
            return ScoutPrompts.lightweight_compact
        elif self.prompt_level == "standard":
            return ScoutPrompts.standard
        else:  # heavyweight
            return ScoutPrompts.heavyweight_detailed

    def get_verifier_prompt_builder(self):
        """Trả về hàm build VERIFIER prompt phù hợp"""
        if self.prompt_level == "lightweight":
            return VerifierPrompts.lightweight_quick
        elif self.prompt_level == "standard":
            return VerifierPrompts.standard_full
        else:  # heavyweight
            return VerifierPrompts.heavyweight_deep


# ============================================================================
# SCOUT PROMPTS - Quét symbol nhanh chóng
# ============================================================================
class ScoutPrompts:
    """Scout prompts với 3 mức độ chi tiết"""

    @staticmethod
    def lightweight_compact(
        symbol: str,
        snapshot: Dict[str, Any],
        has_position: bool,
        pnl: float | None,
    ) -> str:
        """
        ⚡ LIGHTWEIGHT - Rất nhẹ, tối thiểu token
        - Input: 4 dòng dữ liệu (giá, volume, spread, vị thế)
        - Output: JSON ngắn gọn
        - Dùng cho: Scan 20-30 symbols mỗi lần
        """
        close = snapshot.get("close", 0)
        volume = snapshot.get("volume", 0)
        spread = snapshot.get("spread", 0)

        position_ctx = ""
        if has_position:
            pnl_str = f"${pnl:.2f}" if pnl is not None else "?"
            position_ctx = f"\n🔴 OPEN: PnL={pnl_str}"

        return f"""Scan:{symbol}|Price:{close}|Vol:{volume}|Spread:{spread}{position_ctx}

Action: ENTRY|EXIT|HOLD|OBSERVE
Confidence: 0-1
Priority: 0-10"""

    @staticmethod
    def standard(
        symbol: str,
        snapshot: Dict[str, Any],
        has_position: bool,
        pnl: float | None,
    ) -> str:
        """
        📊 STANDARD - Cân bằng tốt token và chất lượng
        - Input: Dữ liệu cơ bản + context vị thế
        - Output: JSON với reasoning điểm
        - Dùng cho: Scan 10-15 symbols mỗi lần
        """
        close = snapshot.get("close", 0)
        volume = snapshot.get("volume", 0)
        spread = snapshot.get("spread", 0)
        high = snapshot.get("high", 0)
        low = snapshot.get("low", 0)

        position_ctx = ""
        if has_position:
            pnl_str = f"${pnl:.2f}" if pnl is not None else "?"
            position_ctx = f"\n🔴 OPEN POSITION | PnL: {pnl_str}"

        prompt = f"""Market Scanner - Quick Analysis

Symbol: {symbol}
Price: {close} | High: {high} | Low: {low}
Volume: {volume} | Spread: {spread}{position_ctx}

Task: Rapid assessment for trading opportunity.
Output JSON only:
{{
  "symbol": "{symbol}",
  "regime": "Trending Up" | "Trending Down" | "Range Bound" | "Volatile",
  "action_hint": "ENTRY" | "EXIT" | "HOLD" | "OBSERVE",
  "confidence": 0.0-1.0,
  "priority_score": 0-10,
  "risk_flags": ["flag1", "flag2"],
  "reasoning": "1-2 sentences"
}}

Rules:
- Position + losing: EXIT, high priority
- Position + near target: EXIT, high priority  
- Strong trend + no position: ENTRY, high confidence
- Sideways/low volume: OBSERVE, low priority

Respond:"""

        return prompt

    @staticmethod
    def heavyweight_detailed(
        symbol: str,
        snapshot: Dict[str, Any],
        has_position: bool,
        pnl: float | None,
    ) -> str:
        """
        🔥 HEAVYWEIGHT - Chi tiết cao, full context
        - Input: Đầy đủ dữ liệu market
        - Output: Detailed analysis + ranking nhiều yếu tố
        - Dùng cho: Scan 3-5 symbols, phân tích sâu
        """
        close = snapshot.get("close", 0)
        volume = snapshot.get("volume", 0)
        spread = snapshot.get("spread", 0)
        high = snapshot.get("high", 0)
        low = snapshot.get("low", 0)

        position_ctx = ""
        if has_position:
            pnl_str = f"${pnl:.2f}" if pnl is not None else "?"
            position_ctx = f"""
🔴 OPEN POSITION
   - Current PnL: {pnl_str}
   - Price Range: {low} to {high}"""

        prompt = f"""═══════════════════════════════════════════════════════
ADVANCED MARKET SCANNER - Detailed Analysis
═══════════════════════════════════════════════════════

SYMBOL: {symbol}
MARKET DATA:
  • Current Price: {close}
  • 24h High: {high} | 24h Low: {low}
  • Trading Volume: {volume}
  • Bid-Ask Spread: {spread}{position_ctx}

ANALYSIS FRAMEWORK:
1. Market Regime Assessment:
   - Is price in uptrend, downtrend, or consolidation?
   - Volatility level (low/medium/high)?
   
2. Entry Opportunity Evaluation:
   - Risk/Reward ratio estimation
   - Entry signal strength (technical + sentiment)
   
3. Position Management (if open):
   - Take profit proximity
   - Stop loss distance
   - Risk allocation
   
4. Risk Factors:
   - Liquidation risk
   - Slippage risk
   - Time-based risk

OUTPUT: Valid JSON only (no markdown)
{{
  "symbol": "{symbol}",
  "regime": "Trending Up" | "Trending Down" | "Range Bound" | "Volatile",
  "action_hint": "ENTRY" | "EXIT" | "HOLD" | "OBSERVE",
  "confidence": 0.0-1.0,
  "priority_score": 0-10,
  "risk_flags": ["flag1", "flag2", "flag3"],
  "reasoning": "Detailed reasoning (2-3 sentences)",
  "analysis_depth": "Technical patterns, volume profile, volatility metrics"
}}

DECISION RULES:
- ENTRY: Confidence ≥ 0.7 + clear trend + low spread
- EXIT: Position underwater OR TP within 2% OR SL breached
- EXIT: High risk flags (liquidation risk, extreme volatility)
- HOLD: Position profitable but no immediate TP
- OBSERVE: Weak signals, wait for confirmation

Respond:"""

        return prompt


# ============================================================================
# VERIFIER PROMPTS - Phân tích sâu + Quyết định cuối cùng
# ============================================================================
class VerifierPrompts:
    """Verifier prompts với 3 mức độ chi tiết (dựa trên prompt_level)"""

    @staticmethod
    def lightweight_quick(
        symbol: str,
        market_data: Dict[str, Any],
        positions: list,
        trader_context: str,
        prompt_pack: str,
    ) -> str:
        """
        ⚡ LIGHTWEIGHT VERIFIER - Nhanh nhất
        Dùng khi: 1 AI local, vẫn cần quick decisions
        """
        return f"""Quick Decision: {symbol}

Market: {market_data.get('close', '?')}
Position: Open={len(positions) > 0}
Context: {trader_context[:100] if trader_context else 'None'}

Output JSON:
{{
  "intent": "ENTRY|EXIT|HOLD",
  "side": "LONG|SHORT",
  "confidence": 0-1,
  "rationale": "1 sentence"
}}

Config: {prompt_pack[:200] if prompt_pack else 'default'}

Respond:"""

    @staticmethod
    def standard_full(
        symbol: str,
        market_data: Dict[str, Any],
        positions: list,
        trader_context: str,
        prompt_pack: str,
    ) -> str:
        """
        📊 STANDARD VERIFIER - Cân bằng
        Dùng khi: Single-tier OpenAI hoặc 1 AI local với medium overhead
        """
        return f"""═══════════════════════════════════════════════════════
TRADING DECISION - {symbol}
═══════════════════════════════════════════════════════

MARKET:
  Price: {market_data.get('close', '?')}
  Position: {len(positions) > 0}
  Movement: {market_data.get('movement', 'unknown')}

TRADER CONTEXT:
{trader_context if trader_context else 'None provided'}

TRADING RULES:
{prompt_pack if prompt_pack else 'Default rules'}

DECISION REQUIRED:
1. Intent (ENTRY/EXIT/HOLD)
2. Side (LONG/SHORT/CLOSE)
3. Confidence
4. Risk Assessment
5. Stop Loss & Take Profit

Output JSON:
{{
  "intent": "ENTRY|EXIT|HOLD",
  "side": "LONG|SHORT",
  "confidence": 0-1,
  "rationale": "2-3 sentences explaining decision"
}}

Respond:"""

    @staticmethod
    def heavyweight_deep(
        symbol: str,
        market_data: Dict[str, Any],
        positions: list,
        trader_context: str,
        prompt_pack: str,
    ) -> str:
        """
        🔥 HEAVYWEIGHT VERIFIER - Full Deep Analysis
        Dùng khi: No token limit, 1 powerful AI local, maximum quality
        """
        return f"""╔════════════════════════════════════════════════════════════════╗
║                    ADVANCED TRADING ANALYSIS                   ║
║                         {symbol}                                 ║
╚════════════════════════════════════════════════════════════════╝

═══ MARKET CONTEXT ═══════════════════════════════════════════════
Current Price: {market_data.get('close', '?')}
High/Low: {market_data.get('high', '?')}/{market_data.get('low', '?')}
Volume: {market_data.get('volume', '?')}
Volatility: {market_data.get('volatility', 'unknown')}
Movement: {market_data.get('movement', 'unknown')}

═══ POSITIONS ════════════════════════════════════════════════════
Active Positions: {len(positions)}
{chr(10).join([f"  • {p.get('symbol', '?')}: {p.get('side')} @ {p.get('entry', '?')}" for p in positions[:3]]) if positions else "  • None"}

═══ TRADER CONTEXT & RULES ═══════════════════════════════════════
{trader_context if trader_context else 'No specific context'}

TRADING RULES & CONSTRAINTS:
{prompt_pack if prompt_pack else 'Default rules apply'}

═══ MULTI-FACTOR DECISION ANALYSIS ═══════════════════════════════

Your task: Provide comprehensive trading decision with:

1. MARKET ANALYSIS
   - Trend direction (up/down/sideways)
   - Momentum assessment
   - Support/Resistance levels
   
2. OPPORTUNITY ASSESSMENT
   - Entry signal strength (0-1)
   - Risk/Reward ratio
   - Position sizing
   
3. RISK EVALUATION
   - Liquidation risk
   - Stop Loss placement
   - Maximum acceptable loss
   
4. TAKE PROFIT STRATEGY
   - Target levels
   - Scale out points
   - Profit protection
   
5. CONFIDENCE SCORE
   - Overall decision confidence (0-1)
   - Uncertainty factors

═══ OUTPUT FORMAT ═══════════════════════════════════════════════════
Valid JSON ONLY (no markdown):
{{
  "intent": "ENTRY|EXIT|HOLD",
  "side": "LONG|SHORT|CLOSE",
  "confidence": 0.0-1.0,
  "reasoning": "Paragraph explaining full analysis and decision",
  "entry_price": number_or_null,
  "stop_loss": number_or_null,
  "take_profit": number_or_null,
  "position_size_ratio": 0.0-1.0,
  "risk_score": 0-10
}}

DECISION RULES (STRICT):
- ENTRY: confidence ≥ 0.65 AND risk_score ≤ 7
- EXIT: position underwater ≥ 2% OR TP within reach
- HOLD: Keeping profit, wait for next signal
- AVOID: Uncertain signals (confidence < 0.5)

Respond with JSON only:"""

        return prompt


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def get_prompt_config() -> PromptConfig:
    """Load từ settings"""
    from packages.shared.config import settings

    return PromptConfig(
        mode=settings.worker_ai_mode,  # type: ignore
        prompt_level=settings.worker_ai_prompt_level,  # type: ignore
    )


def describe_configuration() -> str:
    """Mô tả cấu hình hiện tại dễ hiểu"""
    config = get_prompt_config()

    mode_desc = {
        "two_tier_hybrid": "🌐 2-Tier Hybrid (Scout: Cloud + Verifier: Cloud)",
        "two_tier_same": "🖥️ 2-Tier Same (Scout: Local + Verifier: Local)",
        "single_tier": "⚙️ Single-Tier (1 Model for Everything)",
    }

    level_desc = {
        "lightweight": "⚡ Lightweight (Tiết kiệm token, phù hợp scan nhanh)",
        "standard": "📊 Standard (Cân bằng quality ↔ token)",
        "heavyweight": "🔥 Heavyweight (No limit, full analysis)",
    }

    return f"""
╔═══════════════════════════════════════════════════════════╗
║          AI WORKER CONFIGURATION STATUS                   ║
╚═══════════════════════════════════════════════════════════╝

Mode: {mode_desc.get(config.mode, config.mode)}
Level: {level_desc.get(config.prompt_level, config.prompt_level)}

"""
