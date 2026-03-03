"""
Quota Manager: Track LLM API usage per provider and alert users.

Prevents surprise 429 quota exceeded errors by:
1. Tracking usage in real-time
2. Estimating remaining quota
3. Alerting at thresholds (70%, 85%, 95%, 100%)
4. Suggesting fallback models
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from packages.shared.models import QuotaLog
from packages.shared.logger import logger


@dataclass
class QuotaLimit:
    """API quota limits for a provider"""
    provider: str
    rpm: int = 500
    tpm: int = 10000
    daily_limit: int = 1000000


@dataclass
class QuotaUsage:
    """Current quota usage tracking"""
    provider: str
    timestamp: datetime
    requests_this_minute: int = 0
    tokens_this_minute: int = 0
    tokens_today: int = 0
    last_request_time: datetime | None = None


class QuotaStatus:
    """Status of single provider's quota"""
    
    def __init__(self, provider: str, usage: QuotaUsage, limit: QuotaLimit):
        self.provider = provider
        self.usage = usage
        self.limit = limit
    
    @property
    def rpm_percent(self) -> float:
        """Current RPM as percentage of limit"""
        if self.limit.rpm == 0:
            return 0.0
        return (self.usage.requests_this_minute / self.limit.rpm) * 100
    
    @property
    def tpm_percent(self) -> float:
        """Current TPM as percentage of limit"""
        if self.limit.tpm == 0:
            return 0.0
        return (self.usage.tokens_this_minute / self.limit.tpm) * 100
    
    @property
    def daily_percent(self) -> float:
        """Daily usage as percentage of limit"""
        if self.limit.daily_limit == 0:
            return 0.0
        return (self.usage.tokens_today / self.limit.daily_limit) * 100
    
    @property
    def alert_level(self) -> str:
        """Determine alert level based on usage"""
        
        daily = self.daily_percent
        
        if daily >= 100:
            return "CRITICAL"
        elif daily >= 95:
            return "DANGER"
        elif daily >= 85:
            return "WARNING"
        elif daily >= 70:
            return "CAUTION"
        else:
            return "HEALTHY"
    
    def to_dict(self) -> Dict:
        """Convert to API response format"""
        return {
            "provider": self.provider,
            "rpm_usage": self.usage.requests_this_minute,
            "rpm_limit": self.limit.rpm,
            "rpm_percent": self.rpm_percent,
            "tpm_usage": self.usage.tokens_this_minute,
            "tpm_limit": self.limit.tpm,
            "tpm_percent": self.tpm_percent,
            "daily_usage_tokens": self.usage.tokens_today,
            "daily_limit_tokens": self.limit.daily_limit,
            "daily_percent": self.daily_percent,
            "alert_level": self.alert_level,
            "last_request_time": self.usage.last_request_time.isoformat() if self.usage.last_request_time else None
        }


class QuotaManager:
    """Manage quota tracking and alerting"""
    
    DEFAULT_LIMITS = {
        "openai": QuotaLimit(provider="openai", rpm=500, tpm=90000, daily_limit=2000000),
        "gemini": QuotaLimit(provider="gemini", rpm=300, tpm=100000, daily_limit=1000000),
        "groq": QuotaLimit(provider="groq", rpm=1000, tpm=200000, daily_limit=5000000),
        "claude": QuotaLimit(provider="claude", rpm=600, tpm=160000, daily_limit=2000000),
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.usage_cache: Dict[str, QuotaUsage] = {}
        self.limits = self.DEFAULT_LIMITS.copy()
    
    async def log_request(
        self,
        user_id: str,
        provider: str,
        request_type: str,
        tokens_used: int,
        response_time_ms: int,
        success: bool = True,
        error_code: str | None = None
    ) -> None:
        """Log an API request for quota tracking"""
        
        log = QuotaLog(
            user_id=user_id,
            provider=provider,
            timestamp=datetime.utcnow(),
            request_type=request_type,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            success=success,
            error_code=error_code
        )
        
        self.session.add(log)
        
        if provider not in self.usage_cache:
            self.usage_cache[provider] = QuotaUsage(provider=provider, timestamp=datetime.utcnow())
        
        usage = self.usage_cache[provider]
        usage.tokens_today += tokens_used
        usage.requests_this_minute += 1
        usage.last_request_time = datetime.utcnow()
        
        status = QuotaStatus(provider, usage, self.limits.get(provider, QuotaLimit(provider)))
        if status.alert_level in ["DANGER", "CRITICAL", "WARNING"]:
            await self._send_quota_alert(user_id, status)
        
        await self.session.commit()
    
    async def get_status(self, user_id: str, provider: str | None = None) -> Dict[str, QuotaStatus]:
        """Get quota status for provider(s)"""
        
        providers = [provider] if provider else list(self.DEFAULT_LIMITS.keys())
        status_by_provider = {}
        
        for prov in providers:
            cutoff = datetime.utcnow() - timedelta(hours=24)
            
            result = await self.session.execute(
                select(func.sum(QuotaLog.tokens_used))
                .where(
                    QuotaLog.user_id == user_id,
                    QuotaLog.provider == prov,
                    QuotaLog.timestamp >= cutoff,
                    QuotaLog.success == True
                )
            )
            
            tokens_today = result.scalar() or 0
            
            usage = QuotaUsage(
                provider=prov,
                timestamp=datetime.utcnow(),
                tokens_today=tokens_today
            )
            
            status_by_provider[prov] = QuotaStatus(
                prov,
                usage,
                self.limits.get(prov, QuotaLimit(prov))
            )
        
        return status_by_provider
    
    async def _send_quota_alert(
        self,
        user_id: str,
        status: QuotaStatus
    ) -> None:
        """Send alert notification to user"""
        
        alert_messages = {
            "HEALTHY": None,
            "CAUTION": f"⚠️ {status.provider}: {status.daily_percent:.1f}% quota used (70% threshold)",
            "WARNING": f"🟠 {status.provider}: {status.daily_percent:.1f}% quota used (85% threshold)",
            "DANGER": f"🔴 {status.provider}: {status.daily_percent:.1f}% quota used (95% threshold)",
            "CRITICAL": f"🚨 {status.provider}: {status.daily_percent:.1f}% quota EXCEEDED"
        }
        
        message = alert_messages.get(status.alert_level)
        if message:
            logger.warning(f"QUOTA_ALERT user={user_id} {message}")
            await self._notify_user(user_id, message, status.alert_level)
    
    async def _notify_user(
        self,
        user_id: str,
        message: str,
        level: str
    ) -> None:
        """Send notification to user"""
        logger.info(f"Sending notification to {user_id}: {message} (level={level})")
    
    def get_fallback_chain(self, blocked_provider: str) -> List[str]:
        """Get ordered list of fallback providers"""
        
        fallback_order = {
            "openai": ["groq", "claude", "gemini"],
            "gemini": ["groq", "openai", "claude"],
            "groq": ["openai", "claude", "gemini"],
            "claude": ["openai", "groq", "gemini"],
        }
        
        return fallback_order.get(blocked_provider, list(self.DEFAULT_LIMITS.keys()))


class QuotaAwareAdapter:
    """LLM Adapter wrapper that respects quotas"""
    
    def __init__(self, base_adapter, quota_manager: QuotaManager, user_id: str):
        self.base_adapter = base_adapter
        self.quota_manager = quota_manager
        self.user_id = user_id
        self.provider = base_adapter.provider if hasattr(base_adapter, 'provider') else 'unknown'
    
    async def make_decision(
        self,
        market_snapshot: Dict,
        prompt_pack,
        fallback_on_quota: bool = True
    ):
        """Make decision with quota awareness"""
        
        try:
            status = await self.quota_manager.get_status(self.user_id, self.provider)
            provider_status = status.get(self.provider)
            
            if provider_status and provider_status.alert_level == "CRITICAL" and fallback_on_quota:
                logger.warning(f"Quota critical for {self.provider}, using fallback")
                return None
            
            start_time = datetime.utcnow()
            decision = await self.base_adapter.make_decision(market_snapshot, prompt_pack)
            
            elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await self.quota_manager.log_request(
                user_id=self.user_id,
                provider=self.provider,
                request_type="decision",
                tokens_used=estimate_tokens(decision),
                response_time_ms=elapsed_ms,
                success=True
            )
            
            return decision
            
        except Exception as e:
            await self.quota_manager.log_request(
                user_id=self.user_id,
                provider=self.provider,
                request_type="decision",
                tokens_used=0,
                response_time_ms=0,
                success=False,
                error_code="error"
            )
            
            logger.error(f"Decision failed: {str(e)}")
            if fallback_on_quota:
                return None
            else:
                raise


def estimate_tokens(output) -> int:
    """Rough estimate of tokens used in response"""
    text_length = len(str(output)) if output else 0
    return max(10, text_length // 4)
