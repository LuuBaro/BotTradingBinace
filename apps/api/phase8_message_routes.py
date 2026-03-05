"""
Phase 8 API Routes - Trader Message Center
Operational Q&A grounded on real trading system data.
Now with AI-powered response generation!
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from typing import Any, Optional, cast
import os
import httpx

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth import jwt_handler
from packages.shared.config import settings
from packages.shared.logger import logger
from packages.shared.llm_adapter import get_llm_adapter
from packages.shared.models import (
    TraderConversation,
    TraderMessage,
    TradeJournal,
    Decision,
    RiskLog,
    Signal,
    Position,
    BotConfig,
)
from packages.shared.worker_state import worker_state


router = APIRouter(tags=["message-center"])
security = HTTPBearer()

VN_TZ = timezone(timedelta(hours=7))


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    conversation_id: Optional[int] = None
    timezone_name: str = "Asia/Ho_Chi_Minh"


class AskResponse(BaseModel):
    success: bool
    conversation_id: int
    user_message_id: int
    assistant_message_id: int
    intent: str
    confidence: float
    answer: str
    timestamp: str


def _require_user(credentials: Any):
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def _vn_now() -> datetime:
    return datetime.now(VN_TZ)


def _local_day_utc_range(day_offset: int = 0) -> tuple[datetime, datetime, str]:
    """
    Return UTC range for VN local day (00:00 -> 23:59:59.999999)
    with day_offset: 0=today, 1=yesterday, 2=two days ago
    """
    now_local = _vn_now()
    local_day = (now_local - timedelta(days=day_offset)).date()
    start_local = datetime.combine(local_day, datetime.min.time(), tzinfo=VN_TZ)
    end_local = datetime.combine(local_day, datetime.max.time(), tzinfo=VN_TZ)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        end_local.astimezone(timezone.utc).replace(tzinfo=None),
        local_day.isoformat(),
    )


def _detect_intent(question: str) -> tuple[str, float]:
    q = question.lower().strip()

    # Date/time questions must not be routed to trading performance
    if any(k in q for k in [
        "hôm nay thứ mấy", "hom nay thu may", "thứ mấy", "thu may",
        "hôm nay ngày mấy", "hom nay ngay may", "ngày mấy", "ngay may",
        "mấy giờ", "may gio", "bây giờ", "bay gio", "hiện tại mấy giờ", "hien tai may gio"
    ]):
        return "datetime_info", 0.98

    # Model/provider switch requests should not fall into performance
    if any(k in q for k in [
        "chuyển model", "chuyen model", "đổi model", "doi model", "switch model",
        "sang local", "qua local", "dùng local", "dung local", "local model",
        "chuyển llm", "chuyen llm", "đổi llm", "doi llm"
    ]):
        return "model_switch_request", 0.97

    # Check "why_no_trade" FIRST (higher priority) - includes "sao + hôm nay" patterns
    if any(k in q for k in ["không trade", "khong trade", "không vào", "khong vao", 
                             "không vào lệnh", "khong vao lenh", "sao không", "sao khong",
                             "tại sao", "tai sao", "sao mà", "sao hôm nay", "sao hom nay",
                             "sao lại", "sao lai", "chưa vào", "chua vao", "ít vào", "it vao"]):
        return "why_no_trade", 0.95

    # Check performance metrics intent early (win rate / % / pnl / lời lỗ)
    if any(k in q for k in [
        "thắng bao nhiêu", "thang bao nhieu", "tỷ lệ thắng", "ty le thang", "win rate", "winrate",
        "%", "bao nhiêu %", "bao nhieu %", "lãi", "lỗ", "thua lỗ", "thua lo", "lỗ lãi", "lo lai", "pnl",
        "hôm nay", "hom nay", "today", "bao nhiêu lệnh", "bao nhieu lenh", "giao dịch", "giao dich"
    ]):
        return "performance_today", 0.93
    
    # Check "ai_system_explain" - chiến lược, prompt, logic
    if any(k in q for k in ["prompt", "propmt", "chiến lược", "chien luoc", "strategy", "logic", "model", "llm", "local",
                             "luồng", "luong", "bạn đang chạy", "ban dang chay",
                             "hệ thống", "he thong", "mô hình", "mo hinh", 
                             "ai đang", "ai dang", "cách hoạt động", "cach hoat dong"]):
        return "ai_system_explain", 0.90
    
    # Check market_status - thị trường, xu hướng
    if any(k in q for k in ["thị trường", "thi truong", "market", "xu hướng", "xu huong",
                             "bias", "trend", "regime", "signals", "tín hiệu", "tin hieu"]):
        return "market_status", 0.90
    
    # Check recent days
    if any(k in q for k in ["hôm qua", "hom qua", "hôm kia", "hom kia", "yesterday", 
                             "2 ngày", "2 ngay", "3 ngày", "3 ngay", "so sánh", "so sanh"]):
        return "performance_recent_days", 0.91
    
    # Default fallback
    return "general_trade_ops", 0.75


async def _generate_answer_with_llm(
    question: str,
    intent: str,
    context: dict[str, Any],
    llm_provider: str
) -> str:
    """Generate answer using AI based on detected intent and actual trading context"""
    
    # Build context summary from trading data
    today_stats = context.get("today_stats", {})
    market_context = context.get("market_context", {})
    system_context = context.get("system_context", {})
    no_trade_context = context.get("no_trade_context", {})
    
    # Build structured context for the LLM
    context_str = f"""
Ngữ cảnh giao dịch hiện tại (Vietnam time):

📊 THỐNG KÊ HÔM NAY:
- Tổng lệnh: {today_stats.get('total', 0)}
- Thắng/Thua: {today_stats.get('win', 0)}/{today_stats.get('loss', 0)}
- Win rate: {today_stats.get('winrate', 0):.1f}%
- PnL: ${today_stats.get('pnl', 0):,.2f}

📈 ĐIỀU KIỆN THỊ TRƯỜNG:
- Bias: {market_context.get('bias', 'unknown')}
- Tín hiệu: {market_context.get('signals_total', 0)} (Long {market_context.get('long_count', 0)}, Short {market_context.get('short_count', 0)})
- Xác suất TB: {market_context.get('avg_probability', 0)*100:.1f}%
- Regime: {market_context.get('latest_regime', 'unknown')}
- Vị thế mở: {market_context.get('open_positions', 0)} | PnL: ${market_context.get('open_unrealized_pnl', 0):,.2f}

🤖 HỆ THỐNG:
- Env: {system_context.get('env', 'unknown')}
- LLM: {system_context.get('llm_provider', 'unknown')}
- Model: {system_context.get('llm_model', 'unknown')}
- Worker: {'RUN' if not system_context.get('worker_paused') else 'PAUSE'}
- Approval mode: {'ON' if system_context.get('approval_mode') else 'OFF'}
- AI mode: {system_context.get('worker_ai_mode', 'unknown')}
- Prompt level: {system_context.get('worker_ai_prompt_level', 'unknown')}
- Scout/Verifier: {system_context.get('worker_ai_scout_provider', 'unknown')}/{system_context.get('worker_ai_scout_model', 'unknown')} -> {system_context.get('worker_ai_verifier_provider', 'unknown')}/{system_context.get('worker_ai_verifier_model', 'unknown')}

🚀 QUYẾT ĐỊNH HÔM NAY:
- Total: {no_trade_context.get('decisions_total', 0)}
- NO_TRADE: {no_trade_context.get('no_trade_count', 0)}
- REJECTED: {no_trade_context.get('rejected_count', 0)}
- Risk rejected: {no_trade_context.get('risk_rejected_count', 0)}
"""
    
    # Deterministic answers for date/time questions
    if intent == "datetime_info":
        now = _vn_now()
        weekdays = {
            0: "Thứ Hai",
            1: "Thứ Ba",
            2: "Thứ Tư",
            3: "Thứ Năm",
            4: "Thứ Sáu",
            5: "Thứ Bảy",
            6: "Chủ Nhật",
        }
        return (
            f"Hiện tại theo giờ Việt Nam là {now.strftime('%H:%M:%S')} - "
            f"{weekdays[now.weekday()]}, ngày {now.strftime('%d/%m/%Y')}."
        )

    if intent == "model_switch_request":
        sy = system_context
        return (
            "Mình hiểu bạn muốn chuyển sang Local AI. "
            f"Hiện tại bot đang chạy {sy.get('llm_provider')} ({sy.get('llm_model')}).\n\n"
            "Để chuyển local ổn định, cần đổi các cấu hình: SELECTED_LLM=local, "
            "USE_LOCAL_LLM=true, WORKER_AI_SCOUT_PROVIDER=local, WORKER_AI_VERIFIER_PROVIDER=local "
            "và trỏ LOCAL_LLM_BASE_URL tới endpoint local (vd: http://localhost:1234/v1)."
        )

    # Build intent-specific prompt
    if intent == "why_no_trade":
        prompt = f"""Nhân viên giao dịch hỏi: "{question}"

{context_str}

Hãy phân tích và giải thích bằng tiếng Việt:
1. Tại sao hôm nay lệnh giao dịch ít hoặc không có?
2. Những yếu tố nào đang ảnh hưởng (điều kiện thị trường, risk, tín hiệu)?
3. Chiến lược của bot đang chờ gì?

Trả lời ngắn gọn (3-4 câu), chuyên nghiệp, dựa vào dữ liệu thực tế không phải giả định."""

    elif intent == "ai_system_explain":
        sy = system_context
        if any(k in question.lower() for k in ["prompt", "propmt", "chiến lược", "chien luoc"]):
            prompt = f"""Nhân viên giao dịch hỏi: "{question}"

{context_str}

Trả lời đúng trọng tâm câu hỏi về "prompt trade hiện tại" bằng tiếng Việt tự nhiên.
Yêu cầu bắt buộc:
- Nêu rõ cấu hình đang chạy hiện tại: env, llm provider, model, worker_ai_mode, worker_ai_prompt_level.
- Nếu đang bật two-tier thì nêu scout provider/model và verifier provider/model.
- Giải thích ngắn gọn prompt hiện tại đang ưu tiên điều gì (kỷ luật risk, chọn lọc tín hiệu, hay tối ưu tốc độ).
- Không viết kiểu giáo trình, không trả JSON, không mở đầu xã giao.

Dữ liệu cấu hình hiện tại:
- env: {sy.get('env')}
- llm_provider: {sy.get('llm_provider')}
- llm_model: {sy.get('llm_model')}
- worker_ai_mode: {sy.get('worker_ai_mode')}
- worker_ai_prompt_level: {sy.get('worker_ai_prompt_level')}
- scout: {sy.get('worker_ai_scout_provider')} / {sy.get('worker_ai_scout_model')}
- verifier: {sy.get('worker_ai_verifier_provider')} / {sy.get('worker_ai_verifier_model')}
"""
        else:
            prompt = f"""Nhân viên giao dịch hỏi: "{question}"

{context_str}

Hãy giải thích ngắn gọn cách bot vận hành bằng tiếng Việt tự nhiên.
Tập trung vào điều đang chạy thực tế, tránh lý thuyết chung chung.
Không JSON, không code block, không mở đầu xã giao dài dòng."""

    elif intent == "market_status":
        prompt = f"""Nhân viên giao dịch hỏi: "{question}"

{context_str}

Hãy phân tích tình thế thị trường bằng tiếng Việt:
1. Xu hướng hiện tại (bias, regime)?
2. Mức độ tin cậy của tín hiệu?
3. Có phải cơ hội entry tốt không hay nên chờ?

Trả lời dựa vào dữ liệu, không dài quá 5 câu."""

    elif intent == "performance_today":
        prompt = f"""Nhân viên giao dịch hỏi: "{question}"

{context_str}

Hãy đánh giá hiệu suất hôm nay bằng tiếng Việt:
1. Kết quả giao dịch như thế nào?
2. So với điều kiện thị trường, đó có phải lựa chọn tối ưu không?
3. Ý kiến gì về hiệu suất?

Trả lời chuyên nghiệp, dựa vào dữ liệu thực tế."""

    elif intent == "performance_recent_days":
        prompt = f"""Nhân viên giao dịch hỏi: "{question}"

{context_str}

Hãy so sánh hiệu suất các ngày gần đây bằng tiếng Việt:
1. Xu hướng có tốt lên hay xấu đi?
2. Win rate và PnL thay đổi ra sao?
3. Nhận xét chung về phong cách giao dịch?

Trả lời ngắn gọn, dựa vào dữ liệu."""

    else:  # general_trade_ops
        prompt = f"""Nhân viên giao dịch hỏi: "{question}"

{context_str}

Hãy trả lời câu hỏi của nhân viên bằng tiếng Việt có dấu, tự nhiên như người tư vấn thật.
Không trả về JSON, không code block, không key-value machine format.
Giọng điệu thân thiện, rõ ràng, chuyên nghiệp."""
    
    try:
        # Fallback to template only for mock provider
        if llm_provider == "mock" or not llm_provider:
            logger.info("Using mock LLM provider for message center")
            return _build_answer_template(intent, question, context)

        content, tokens_used = await _generate_freeform_answer(prompt, llm_provider)
        logger.info(f"LLM generated answer ({llm_provider}): {tokens_used} tokens used")
        normalized = _normalize_llm_answer(content)

        if _looks_like_machine_output(normalized):
            rewrite_prompt = (
                "Viết lại nội dung sau thành một câu trả lời tự nhiên bằng tiếng Việt có dấu, "
                "thân thiện, ngắn gọn 4-6 câu. Không JSON, không gạch đầu dòng key-value.\n\n"
                f"Nội dung gốc:\n{normalized}"
            )
            rewritten, _ = await _generate_freeform_answer(rewrite_prompt, llm_provider)
            polished = _normalize_llm_answer(rewritten)
            if polished and not _looks_like_machine_output(polished):
                return polished

        if normalized:
            return normalized
        return _build_answer_template(intent, question, context)
        
    except Exception as e:
        logger.error(f"LLM generation failed: {e}, falling back to template response")
        return _build_answer_template(intent, question, context)


async def _generate_freeform_answer(prompt: str, llm_provider: str) -> tuple[str, int]:
    """Call provider directly for natural-language answer (no JSON-only system prompt)."""
    provider = (llm_provider or "").lower().strip()

    system_prompt = (
        "Bạn là AI trợ lý vận hành trading. "
        "Luôn trả lời bằng tiếng Việt có dấu, tự nhiên như tư vấn viên chuyên nghiệp. "
        "Ưu tiên rõ ràng, ngắn gọn, bám sát dữ liệu. "
        "Tuyệt đối không trả về JSON, không code block."
    )

    if provider in ("openai", "groq", "local"):
        if provider == "openai":
            api_key = settings.openai_api_key
            model = settings.openai_model or "gpt-4o-mini"
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        elif provider == "groq":
            api_key = settings.groq_api_key
            model = settings.groq_model or "llama-3.1-8b-instant"
            base_url = "https://api.groq.com/openai/v1"
        else:
            api_key = settings.custom_provider_key or "not-needed"
            model = settings.custom_provider_model or "local-model"
            base_url = settings.custom_provider_url or "http://localhost:1234/v1"

        if provider != "local" and not api_key:
            raise ValueError(f"Missing API key for provider: {provider}")

        headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.35,
            "max_tokens": 900,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            tokens = int(data.get("usage", {}).get("total_tokens", 0))
            return content, tokens

    if provider in ("claude", "anthropic"):
        api_key = settings.anthropic_api_key
        model = settings.anthropic_model or "claude-3-sonnet"
        if not api_key:
            raise ValueError("Missing ANTHROPIC_API_KEY")

        headers: dict[str, str] = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 900,
            "temperature": 0.35,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"].strip()
            tokens = int(data.get("usage", {}).get("output_tokens", 0))
            return content, tokens

    # Fallback for unsupported providers in message center
    adapter = get_llm_adapter(provider=provider, temperature=0.35, max_tokens=900)
    content, tokens = await adapter.generate(prompt)
    return content, tokens


async def _trade_stats_between(db: AsyncSession, start_utc: datetime, end_utc: datetime) -> dict[str, Any]:
    result = await db.execute(
        select(TradeJournal).where(
            TradeJournal.closed_at >= start_utc,
            TradeJournal.closed_at <= end_utc,
        )
    )
    trades = result.scalars().all()

    total = len(trades)
    win = sum(1 for t in trades if t.pnl > 0)
    loss = sum(1 for t in trades if t.pnl < 0)
    breakeven = total - win - loss
    pnl = float(sum(t.pnl for t in trades))
    winrate = (win / total * 100.0) if total > 0 else 0.0

    return {
        "total": total,
        "win": win,
        "loss": loss,
        "breakeven": breakeven,
        "pnl": pnl,
        "winrate": winrate,
    }


async def _today_no_trade_context(db: AsyncSession) -> dict[str, Any]:
    start_utc, end_utc, _ = _local_day_utc_range(0)

    decisions_result = await db.execute(
        select(Decision).where(
            Decision.timestamp >= start_utc,
            Decision.timestamp <= end_utc,
        )
    )
    decisions = decisions_result.scalars().all()

    risk_result = await db.execute(
        select(RiskLog).where(
            RiskLog.timestamp >= start_utc,
            RiskLog.timestamp <= end_utc,
        )
    )
    risk_logs = risk_result.scalars().all()

    no_trade_count = sum(1 for d in decisions if (d.decision_type or "").upper() == "NO_TRADE")
    rejected_count = sum(1 for d in decisions if (d.status or "").upper() == "REJECTED")
    approved_count = sum(1 for d in decisions if (d.status or "").upper() in ["APPROVED", "EXECUTED"])

    top_risk_reasons = Counter(
        (r.reason or "Không rõ").strip()[:120]
        for r in risk_logs
        if (r.result or "").lower() == "rejected"
    ).most_common(3)

    return {
        "decisions_total": len(decisions),
        "no_trade_count": no_trade_count,
        "rejected_count": rejected_count,
        "approved_count": approved_count,
        "risk_rejected_count": sum(1 for r in risk_logs if (r.result or "").lower() == "rejected"),
        "top_risk_reasons": top_risk_reasons,
    }


async def _market_context(db: AsyncSession) -> dict[str, Any]:
    signal_result = await db.execute(select(Signal).order_by(desc(Signal.timestamp)).limit(20))
    signals = signal_result.scalars().all()

    position_result = await db.execute(select(Position))
    positions = position_result.scalars().all()

    decision_result = await db.execute(select(Decision).order_by(desc(Decision.timestamp)).limit(1))
    latest_decision = decision_result.scalar_one_or_none()

    total_signals = len(signals)
    long_count = sum(1 for s in signals if (s.side or "").upper() == "LONG")
    avg_prob = (sum(float(s.probability) for s in signals) / total_signals) if total_signals else 0.0
    bias = "TRUNG TÍNH"
    if total_signals > 0:
        ratio = long_count / total_signals
        if ratio >= 0.65:
            bias = "NGHIÊNG LONG"
        elif ratio <= 0.35:
            bias = "NGHIÊNG SHORT"

    return {
        "signals_total": total_signals,
        "long_count": long_count,
        "short_count": total_signals - long_count,
        "avg_probability": avg_prob,
        "bias": bias,
        "open_positions": len(positions),
        "open_unrealized_pnl": float(sum(p.unrealized_pnl for p in positions)),
        "latest_regime": latest_decision.regime if latest_decision else "unknown",
    }


async def _system_context(db: AsyncSession) -> dict[str, Any]:
    cfg_result = await db.execute(
        select(BotConfig).where(BotConfig.is_active == True).order_by(desc(BotConfig.created_at)).limit(1)
    )
    cfg = cfg_result.scalar_one_or_none()

    approval_mode = cfg.approval_mode if cfg else False
    env_mode = cfg.env if cfg else settings.env
    llm_provider = settings.selected_llm

    llm_model_map = {
        "openai": settings.openai_model,
        "groq": settings.groq_model,
        "anthropic": settings.anthropic_model,
        "claude": settings.anthropic_model,
        "gemini": settings.gemini_model,
        "local": settings.custom_provider_model or "local-model",
    }
    llm_model = llm_model_map.get((llm_provider or "").lower(), "unknown")

    return {
        "env": env_mode,
        "approval_mode": approval_mode,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "worker_ai_mode": settings.worker_ai_mode,
        "worker_ai_prompt_level": settings.worker_ai_prompt_level,
        "worker_ai_scout_provider": settings.worker_ai_scout_provider,
        "worker_ai_scout_model": settings.worker_ai_scout_model,
        "worker_ai_verifier_provider": settings.worker_ai_verifier_provider,
        "worker_ai_verifier_model": settings.worker_ai_verifier_model,
        "worker_paused": bool(worker_state.get("is_paused", False)),
        "pause_reason": worker_state.get("pause_reason"),
    }


def _fmt_currency(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}${v:,.2f}"


def _to_readable_text(data: Any, indent: int = 0) -> list[str]:
    prefix = "  " * indent
    lines: list[str] = []
    if isinstance(data, dict):
        data_dict = cast(dict[str, Any], data)
        for k, v in data_dict.items():
            key = str(k).replace("_", " ").strip()
            if isinstance(v, (dict, list)):
                lines.append(f"{prefix}• {key}:")
                lines.extend(_to_readable_text(v, indent + 1))
            else:
                lines.append(f"{prefix}• {key}: {v}")
    elif isinstance(data, list):
        data_list = cast(list[Any], data)
        for item in data_list:
            if isinstance(item, (dict, list)):
                lines.extend(_to_readable_text(item, indent))
            else:
                lines.append(f"{prefix}• {item}")
    else:
        lines.append(f"{prefix}{data}")
    return lines


def _extract_text_fragments(data: Any) -> list[str]:
    fragments: list[str] = []
    if isinstance(data, dict):
        data_dict = cast(dict[str, Any], data)
        for v in data_dict.values():
            fragments.extend(_extract_text_fragments(v))
    elif isinstance(data, list):
        data_list = cast(list[Any], data)
        for item in data_list:
            fragments.extend(_extract_text_fragments(item))
    elif isinstance(data, str):
        t = data.strip()
        if t:
            fragments.append(t)
    return fragments


def _looks_like_machine_output(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    if t.startswith("{") or t.startswith("[") or "```" in t:
        return True
    key_value_lines = sum(1 for line in t.splitlines() if ":" in line and len(line) < 90)
    return key_value_lines >= 4


def _normalize_llm_answer(raw: str) -> str:
    """Normalize LLM output so UI gets readable plain text instead of raw JSON/code fences."""
    text = (raw or "").strip()
    if not text:
        return "Không có nội dung phản hồi từ AI."

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        parsed = json.loads(text)
    except Exception:
        return text

    parsed_obj = cast(dict[str, Any] | list[Any] | str | int | float | bool | None, parsed)

    if isinstance(parsed_obj, dict):
        for key in ("answer", "response", "message", "content"):
            v = parsed_obj.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()

    fragments = _extract_text_fragments(parsed_obj)
    if fragments:
        sentence = " ".join(fragments[:6]).strip()
        return sentence

    lines = _to_readable_text(parsed_obj)
    return "\n".join(lines).strip()


def _build_answer_template(intent: str, question: str, facts: dict[str, Any]) -> str:
    """Fallback template-based answer (use only if LLM unavailable)"""
    now_str = _vn_now().strftime("%H:%M:%S %d/%m/%Y")

    if intent == "datetime_info":
        now = _vn_now()
        weekdays = {
            0: "Thứ Hai",
            1: "Thứ Ba",
            2: "Thứ Tư",
            3: "Thứ Năm",
            4: "Thứ Sáu",
            5: "Thứ Bảy",
            6: "Chủ Nhật",
        }
        return (
            f"Hiện tại theo giờ Việt Nam là {now.strftime('%H:%M:%S')} - "
            f"{weekdays[now.weekday()]}, ngày {now.strftime('%d/%m/%Y')}."
        )

    if intent == "performance_today":
        s = facts["today_stats"]
        m = facts["market_context"]
        
        if s['total'] == 0:
            return (
                f"[{now_str}] Hôm nay chưa có giao dịch.\n\n"
                f"Nguyên nhân:\n"
                f"• Thị trường: Bias {m['bias']} (Signals: {m['signals_total']})\n"
                f"• Xác suất tín hiệu TB: {m['avg_probability']*100:.1f}%\n"
                f"→ Nếu vào lệnh với điều kiện này, khả năng lỗ sẽ cao.\n"
                f"• Chiến lược của bạn đang chờ setup tối ưu.\n"
                f"PnL: {_fmt_currency(s['pnl'])}"
            )
        
        return (
            f"[{now_str}] Hiệu suất hôm nay:\n\n"
            f"Kết quả giao dịch:\n"
            f"• Tổng lệnh: {s['total']} | Thắng: {s['win']} | Thua: {s['loss']}\n"
            f"• Win rate: {s['winrate']:.1f}%\n"
            f"• PnL: {_fmt_currency(s['pnl'])}\n\n"
            f"Bối cảnh thị trường:\n"
            f"• Bias: {m['bias']} | Signals: {m['signals_total']}\n"
            f"• Xác suất TB: {m['avg_probability']*100:.1f}%"
        )

    if intent == "performance_recent_days":
        y = facts["yesterday_stats"]
        d2 = facts["two_days_ago_stats"]
        today = facts["today_stats"]
        
        lines = [f"[{now_str}] So sánh 3 ngày:"]
        
        # Hôm nay
        today_text = f"• Hôm nay: {today['total']} lệnh | {today['winrate']:.1f}% | {_fmt_currency(today['pnl'])}"
        lines.append(today_text)
        
        # Hôm qua
        y_text = f"• Hôm qua: {y['total']} lệnh | {y['winrate']:.1f}% | {_fmt_currency(y['pnl'])}"
        lines.append(y_text)
        
        # Hôm kia
        d2_text = f"• Hôm kia: {d2['total']} lệnh | {d2['winrate']:.1f}% | {_fmt_currency(d2['pnl'])}"
        lines.append(d2_text)
        
        return "\n".join(lines)

    if intent == "why_no_trade":
        nt = facts["no_trade_context"]
        m = facts["market_context"]
        sy = facts["system_context"]
        
        if sy["worker_paused"]:
            return (
                f"[{now_str}] Worker đang PAUSE.\n"
                f"Lý do: {sy.get('pause_reason') or 'Tạm dừng'}"
            )
        
        # Analyze why no trades
        explanation_lines = [f"[{now_str}] Vì sao ít/không vào lệnh hôm nay:"]
        
        # Market conditions analysis
        explanation_lines.append(f"\n📊 Điều kiện thị trường:")
        explanation_lines.append(f"• Bias: {m['bias']} (tín hiệu không rõ ràng)")
        explanation_lines.append(f"• Signals: {m['signals_total']} | XS TB: {m['avg_probability']*100:.1f}%")
        
        if m['signals_total'] == 0 or m['avg_probability'] < 0.5:
            explanation_lines.append(f"→ Thị trường không có tín hiệu mạnh → Bot chờ điều kiện tốt hơn")
        
        # Risk analysis
        if nt['risk_rejected_count'] > 0:
            explanation_lines.append(f"\n🚨 Risk Filter:")
            explanation_lines.append(f"• Lệnh bị chặn: {nt['risk_rejected_count']}")
            if nt["top_risk_reasons"]:
                for reason, count in nt["top_risk_reasons"][:2]:
                    explanation_lines.append(f"  - {reason} ({count}x)")
        
        # Decision stats
        explanation_lines.append(f"\n🤖 Quyết định hôm nay:")
        explanation_lines.append(f"• Total: {nt['decisions_total']} | NO_TRADE: {nt['no_trade_count']} | REJECTED: {nt['rejected_count']}")
        
        # Conclusion
        explanation_lines.append(f"\n✓ Kết luận:")
        if m['signals_total'] < 3:
            explanation_lines.append(f"Thị trường yên tĩnh, chiến lược của bạn đang chờ setup tối ưu.")
        if nt['risk_rejected_count'] > nt['decisions_total'] * 0.5:
            explanation_lines.append(f"Risk filter đang giữ kỷ luật, bảo vệ vốn của bạn.")
        
        return "\n".join(explanation_lines)

    if intent == "market_status":
        m = facts["market_context"]
        
        lines = [f"[{now_str}] Snapshot thị trường:"]
        
        lines.append(f"\n📈 Xu hướng:")
        lines.append(f"• Bias: {m['bias']}")
        lines.append(f"• Regime: {m['latest_regime']}")
        
        lines.append(f"\n📊 Tín hiệu:")
        lines.append(f"• Signals: {m['signals_total']} (Long {m['long_count']} / Short {m['short_count']})")
        lines.append(f"• XS trung bình: {m['avg_probability']*100:.1f}%")
        
        lines.append(f"\n💼 Vị thế:")
        lines.append(f"• Mở: {m['open_positions']} | PnL: {_fmt_currency(m['open_unrealized_pnl'])}")
        
        # Smart interpretation
        lines.append(f"\n✓ Nhận xét:")
        if m['signals_total'] > 10 and m['avg_probability'] > 0.7:
            lines.append(f"Thị trường rõ ràng, cơ hội tốt cho entry.")
        elif m['signals_total'] < 5 or m['avg_probability'] < 0.5:
            lines.append(f"Thị trường mơ hồ, cần chờ tín hiệu mạnh hơn.")
        elif m['bias'] == "TRUNG TÍNH":
            lines.append(f"Thị trường không có xu hướng rõ, nguy cơ whipsaw cao.")
        
        return "\n".join(lines)

    if intent == "ai_system_explain":
        sy = facts["system_context"]
        
        lines = [f"[{now_str}] Luồng hoạt động:"]
        
        lines.append(f"\n🔄 Pipeline:")
        lines.append(f"Signals → Decisions → Risk filter → Orders → Positions → Trade journal")
        
        lines.append(f"\n⚙️ Cấu hình:")
        lines.append(f"• Env: {sy['env']}")
        lines.append(f"• LLM: {sy['llm_provider']}")
        lines.append(f"• Approval mode: {'ON' if sy['approval_mode'] else 'OFF'}")
        lines.append(f"• Worker: {'RUN' if not sy['worker_paused'] else 'PAUSE'}")
        
        lines.append(f"\n💡 Chiến lược của bạn:")
        lines.append(f"• Bot tự động quét tín hiệu từ thị trường")
        lines.append(f"• Khi tín hiệu đạt mức tin cậy cao, bot sẽ entry")
        lines.append(f"• Risk filter đảm bảo không vào khi điều kiện không tối ưu")
        lines.append(f"• Learning module tối ưu hóa chiến lược từ lịch sử trades")
        
        return "\n".join(lines)

    # Fallback for generic questions
    t = facts["today_stats"]
    m = facts["market_context"]
    
    lines = [f"[{now_str}] Thông tin hệ thống:"]
    lines.append(f"• Hôm nay: {t['total']} lệnh | PnL {_fmt_currency(t['pnl'])}")
    lines.append(f"• Thị trường: Bias {m['bias']} | {m['signals_total']} signals")
    lines.append(f"• Vị thế: {m['open_positions']} open")
    lines.append(f"\nBạn có thể hỏi cụ thể hơn như:")
    lines.append(f"• 'Hôm nay lỗ/lãi bao nhiêu?'")
    lines.append(f"• 'Tại sao không vào lệnh?'")
    lines.append(f"• 'Thị trường hiện tại thế nào?'")
    lines.append(f"• 'Chiến lược của tôi là gì?'")
    
    return "\n".join(lines)


@router.post("/message-center/conversations", response_model=dict)
async def create_conversation(
    request: ConversationCreateRequest,
    credentials: Any = Depends(security),
) -> dict[str, Any]:
    # NOTE: keep signature stable with existing style; open session manually below
    user = _require_user(credentials)

    from packages.shared.database import AsyncSessionFactory
    async with AsyncSessionFactory() as session:
        title = (request.title or "Phiên trao đổi vận hành").strip()[:255]
        conv = TraderConversation(user_id=user.id, title=title)
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        return {
            "success": True,
            "conversation": {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "last_message_at": conv.last_message_at.isoformat(),
            },
        }


@router.get("/message-center/conversations", response_model=dict)
async def list_conversations(credentials: Any = Depends(security)) -> dict[str, Any]:
    user = _require_user(credentials)

    from packages.shared.database import AsyncSessionFactory
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(TraderConversation)
            .where(TraderConversation.user_id == user.id)
            .order_by(desc(TraderConversation.last_message_at))
            .limit(100)
        )
        conversations = result.scalars().all()

        return {
            "success": True,
            "conversations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                    "last_message_at": c.last_message_at.isoformat(),
                }
                for c in conversations
            ],
        }


@router.get("/message-center/conversations/{conversation_id}/messages", response_model=dict)
async def list_messages(conversation_id: int, credentials: Any = Depends(security)) -> dict[str, Any]:
    user = _require_user(credentials)

    from packages.shared.database import AsyncSessionFactory
    async with AsyncSessionFactory() as session:
        conv = await session.get(TraderConversation, conversation_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")

        result = await session.execute(
            select(TraderMessage)
            .where(TraderMessage.conversation_id == conversation_id)
            .order_by(TraderMessage.created_at.desc())
            .limit(1000)
        )
        messages = result.scalars().all()

        return {
            "success": True,
            "conversation": {
                "id": conv.id,
                "title": conv.title,
                "last_message_at": conv.last_message_at.isoformat(),
            },
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "intent": m.intent,
                    "confidence": m.confidence,
                    "status": m.status,
                    "processing_ms": m.processing_ms,
                    "created_at": m.created_at.isoformat(),
                }
                for m in messages
            ],
        }


@router.get("/message-center/suggested-questions", response_model=dict)
async def suggested_questions(credentials: Any = Depends(security)) -> dict[str, Any]:
    _ = _require_user(credentials)
    return {
        "success": True,
        "questions": [
            "Hôm nay bot trade thế nào rồi, lời lỗ bao nhiêu?",
            "Sao hôm nay chưa vào lệnh?",
            "Hôm qua và hôm kia mỗi ngày lời lỗ bao nhiêu?",
            "Thị trường hiện tại bot đang nhìn bias gì?",
            "AI đang chạy logic gì và có bị risk chặn không?",
        ],
    }


@router.post("/message-center/ask", response_model=AskResponse)
async def ask_message_center(request: AskRequest, credentials: Any = Depends(security)):
    start = datetime.now(timezone.utc)
    user = _require_user(credentials)

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    intent, confidence = _detect_intent(question)

    from packages.shared.database import AsyncSessionFactory
    async with AsyncSessionFactory() as session:
        # Resolve / create conversation
        if request.conversation_id:
            conv = await session.get(TraderConversation, request.conversation_id)
            if not conv or conv.user_id != user.id:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            title = question[:120]
            conv = TraderConversation(user_id=user.id, title=title)
            session.add(conv)
            await session.flush()

        # Store user message first
        user_msg = TraderMessage(
            conversation_id=conv.id,
            role="user",
            content=question,
            intent=intent,
            confidence=confidence,
            status="ok",
        )
        session.add(user_msg)
        await session.flush()

        # Gather factual context
        today_start, today_end, _ = _local_day_utc_range(0)
        y_start, y_end, _ = _local_day_utc_range(1)
        d2_start, d2_end, _ = _local_day_utc_range(2)

        today_stats = await _trade_stats_between(session, today_start, today_end)
        y_stats = await _trade_stats_between(session, y_start, y_end)
        d2_stats = await _trade_stats_between(session, d2_start, d2_end)
        no_trade_context = await _today_no_trade_context(session)
        market_context = await _market_context(session)
        system_context = await _system_context(session)

        facts = {
            "today_stats": today_stats,
            "yesterday_stats": y_stats,
            "two_days_ago_stats": d2_stats,
            "no_trade_context": no_trade_context,
            "market_context": market_context,
            "system_context": system_context,
        }

        # Use AI-powered response generation
        answer = await _generate_answer_with_llm(
            question=question,
            intent=intent,
            context=facts,
            llm_provider=system_context["llm_provider"]
        )
        processing_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

        assistant_msg = TraderMessage(
            conversation_id=conv.id,
            role="assistant",
            content=answer,
            intent=intent,
            confidence=confidence,
            status="ok",
            processing_ms=processing_ms,
            context_json=facts,
        )
        session.add(assistant_msg)

        conv.last_message_at = datetime.now(timezone.utc).replace(tzinfo=None)
        conv.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        await session.commit()
        await session.refresh(user_msg)
        await session.refresh(assistant_msg)
        await session.refresh(conv)

        logger.info(
            "message_center_answered",
            user_id=user.id,
            conversation_id=conv.id,
            intent=intent,
            processing_ms=processing_ms,
        )

        return AskResponse(
            success=True,
            conversation_id=conv.id,
            user_message_id=user_msg.id,
            assistant_message_id=assistant_msg.id,
            intent=intent,
            confidence=confidence,
            answer=answer,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
