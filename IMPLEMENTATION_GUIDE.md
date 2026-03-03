# IMPLEMENTATION GUIDE: Bot Lifecycle + External AI Integration

## 🔴 PART A: CRITICAL FIX - Bot On/Off Control

### Step 1: Database Migration

Create file: `alembic/versions/0001_add_bot_controls.py`

```python
# Migration to add bot control fields to users table
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', 
        sa.Column('bot_enabled', sa.Boolean(), nullable=False, server_default='true')
    )
    op.add_column('users',
        sa.Column('bot_paused_at', sa.DateTime(), nullable=True)
    )
    op.add_column('users',
        sa.Column('bot_pause_reason', sa.String(255), nullable=True)
    )
    op.create_index('ix_users_bot_enabled', 'users', ['bot_enabled'])

def downgrade():
    op.drop_index('ix_users_bot_enabled', table_name='users')
    op.drop_column('users', 'bot_pause_reason')
    op.drop_column('users', 'bot_paused_at')
    op.drop_column('users', 'bot_enabled')
```

**Run migration:**
```bash
alembic upgrade head
```

---

### Step 2: Update User Model

File: `packages/shared/models.py` (add to User class)

```python
class User(Base):
    """Real user accounts for SaaS model"""
    __tablename__ = "users"
    
    # Existing fields...
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    # ... other fields ...
    
    # NEW: Bot Control Fields
    bot_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    bot_paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bot_pause_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Status tracking (can be extended)
    last_bot_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_bot_enabled", "bot_enabled"),
        Index("ix_bot_paused_at", "bot_paused_at"),
    )
```

---

### Step 3: Update Worker to Check bot_enabled

File: `apps/worker/main.py` (modify `run()` method around line 166)

**OLD CODE:**
```python
users_res = await session.execute(
    select(User).join(BotConfig, User.id == BotConfig.user_id)
    .where(BotConfig.is_active == True)
    .distinct()
)
```

**NEW CODE:**
```python
users_res = await session.execute(
    select(User)
    .join(BotConfig, User.id == BotConfig.user_id)
    .where(
        BotConfig.is_active == True,
        User.is_active == True,  # Account not disabled
        User.bot_enabled == True  # NEW: Bot trading enabled
    )
    .distinct()
)
active_users = users_res.scalars().all()

# Also log bot activity
for user in active_users:
    user.last_bot_activity_at = datetime.now(timezone.utc).replace(tzinfo=None)
await session.commit()
```

---

### Step 4: Add API Endpoints

File: `apps/api/phase4_routes.py` (add new route group)

```python
# === Bot Control Endpoints ===

@router.post("/bot/enable")
async def enable_bot(
    credentials: Any = Depends(security)
):
    """Enable bot trading for current user"""
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        db_user = await session.get(User, user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db_user.bot_enabled = True
        db_user.bot_paused_at = None
        db_user.bot_pause_reason = None
        await session.commit()
        
        # Log event
        event = Event(
            timestamp=datetime.utcnow(),
            level="INFO",
            code="BOT_ENABLED",
            message=f"Bot trading enabled for {user.username}",
            user_id=user.id
        )
        session.add(event)
        await session.commit()
    
    return {
        "status": "success",
        "message": "Bot enabled",
        "bot_enabled": True,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/bot/disable")
async def disable_bot(
    reason: str = "Manual pause",
    close_positions: bool = True,
    credentials: Any = Depends(security)
):
    """Disable bot trading for current user"""
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        db_user = await session.get(User, user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db_user.bot_enabled = False
        db_user.bot_paused_at = datetime.utcnow()
        db_user.bot_pause_reason = reason
        
        # Optionally close open positions
        if close_positions:
            positions = await session.execute(
                select(Position).where(
                    Position.user_id == user.id,
                    Position.status == "OPEN"
                )
            )
            for pos in positions.scalars():
                pos.status = "CLOSING_REQUESTED"
            logger.info(f"Marked {len(positions)} positions for closing")
        
        await session.commit()
        
        # Log event
        event = Event(
            timestamp=datetime.utcnow(),
            level="WARNING",
            code="BOT_DISABLED",
            message=f"Bot trading disabled for {user.username}: {reason}",
            user_id=user.id
        )
        session.add(event)
        await session.commit()
    
    return {
        "status": "success",
        "message": "Bot disabled",
        "bot_enabled": False,
        "timestamp": datetime.utcnow().isoformat(),
        "positions_closing": close_positions
    }


@router.get("/bot/status")
async def get_bot_status(
    user_id: str | None = None,
    credentials: Any = Depends(security)
):
    """Get bot status for current or specified user (admin only)"""
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Admin can check other users, traders see only themselves
    target_id = user_id if user_id and requester.role == "admin" else requester.id
    
    async with AsyncSessionFactory() as session:
        target_user = await session.get(User, target_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get bot config status
        bot_config = await session.execute(
            select(BotConfig)
            .where(BotConfig.user_id == target_id, BotConfig.is_active == True)
            .order_by(desc(BotConfig.id))
            .limit(1)
        )
        config = bot_config.scalar_one_or_none()
        
        # Get position count
        positions = await session.execute(
            select(Position).where(
                Position.user_id == target_id,
                Position.status == "OPEN"
            )
        )
        open_positions_count = len(positions.scalars().all())
    
    return {
        "user_id": target_id,
        "username": target_user.username,
        "bot_enabled": target_user.bot_enabled,
        "user_active": target_user.is_active,
        "paused_at": target_user.bot_paused_at.isoformat() if target_user.bot_paused_at else None,
        "pause_reason": target_user.bot_pause_reason,
        "last_activity": target_user.last_bot_activity_at.isoformat() if target_user.last_bot_activity_at else None,
        "config_active": config.is_active if config else False,
        "open_positions": open_positions_count,
        "can_trade": target_user.is_active and target_user.bot_enabled and (config and config.is_active or False)
    }
```

---

### Step 5: Add Telegram Commands

File: `apps/telegram/main.py` (assuming telegram bot exists)

```python
# Add bot enable/disable commands

async def cmd_boton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable trading bot: /boton"""
    try:
        # Get user from database
        user_id = str(update.effective_user.id)
        async with AsyncSessionFactory() as session:
            db_user = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = db_user.scalar_one_or_none()
            
            if not user:
                await update.message.reply_text("❌ User not found")
                return
            
            if user.bot_enabled:
                await update.message.reply_text("✅ Bot đã bật rồi!")
                return
            
            user.bot_enabled = True
            user.bot_paused_at = None
            user.bot_pause_reason = None
            await session.commit()
            
            await update.message.reply_text(
                "✅ Bot trading **ENABLED**\n\n"
                "🤖 Bot sẽ bắt đầu quét và trade từ bây giờ",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def cmd_botoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable trading bot: /botoff"""
    try:
        user_id = str(update.effective_user.id)
        async with AsyncSessionFactory() as session:
            db_user = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = db_user.scalar_one_or_none()
            
            if not user:
                await update.message.reply_text("❌ User not found")
                return
            
            if not user.bot_enabled:
                await update.message.reply_text("⚠️ Bot đã tắt rồi!")
                return
            
            user.bot_enabled = False
            user.bot_paused_at = datetime.utcnow()
            user.bot_pause_reason = "Manual pause via Telegram"
            await session.commit()
            
            await update.message.reply_text(
                "⏸️ Bot trading **DISABLED**\n\n"
                "🔒 Bot sẽ KHÔNG trade nữa cho đến khi bạn enable lại\n"
                "📍 Vị thế hiện tại vẫn được theo dõi",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
```

---

## 🟡 PART B: External AI Agents Integration

### Step 1: Create ExternalAIAgentAdapter

File: `packages/shared/external_agent_adapter.py` (NEW FILE)

```python
"""
External AI Agents Adapter
Integrates custom AI agents model from external VPS
"""
import asyncio
import json
import logging
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from packages.shared.llm_adapter import LLMAdapter, MockLLMAdapter

logger = logging.getLogger(__name__)


class ExternalAIAgentAdapter(LLMAdapter):
    """
    Wrapper for custom AI agents model running on external VPS
    
    Typical VPS endpoint: http://your-vps-ip:5000/api/generate
    """
    
    def __init__(
        self,
        api_endpoint: str,
        api_key: Optional[str] = None,
        model: str = "trading-agents-v1",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: int = 30,
        fallback_to_mock: bool = True
    ):
        """
        Initialize external agent adapter
        
        Args:
            api_endpoint: VPS endpoint URL (http://ip:port)
            api_key: API key for billing/auth
            model: Model name
            temperature: Response randomness (0.0-1.0)
            max_tokens: Max response length
            timeout: Request timeout in seconds
            fallback_to_mock: Use Mock adapter if external fails
        """
        super().__init__(api_key or "external-agent", model, temperature, max_tokens)
        self.api_endpoint = api_endpoint.rstrip('/')
        self.timeout = timeout
        self.fallback_to_mock = fallback_to_mock
        self.health_check_interval = 300  # Check health every 5 min
        self.last_health_check = None
        self.is_healthy = False
        
        logger.info(f"ExternalAIAgentAdapter initialized: {api_endpoint}")
    
    async def generate(self, prompt: str) -> str:
        """
        Generate trading decision from external AI agents
        
        Args:
            prompt: Trading decision prompt
            
        Returns:
            JSON string with decision
            
        Handles:
            - Quota exceeded (429) → fallback to Mock
            - Timeout → fallback to Mock
            - Invalid response → fallback to Mock
        """
        try:
            # Prepare request
            headers = {
                "Authorization": f"Bearer {self.api_key}" if self.api_key and self.api_key != "external-agent" else None,
                "Content-Type": "application/json",
                "User-Agent": "TradingBot/1.0"
            }
            # Remove None auth header
            if headers["Authorization"] is None:
                del headers["Authorization"]
            
            payload = {
                "prompt": prompt,
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.debug(f"External agent request: {self.api_endpoint}/api/generate")
            
            # Make request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_endpoint}/api/generate",
                    headers=headers,
                    json=payload
                )
            
            # Handle quota exceeded
            if response.status_code == 429:
                logger.warning("⚠️ External agent: quota exceeded (429)")
                if self.fallback_to_mock:
                    logger.info("Falling back to Mock LLM")
                    return await MockLLMAdapter().generate(prompt)
                raise Exception("External agent quota exceeded")
            
            # Handle other errors
            if response.status_code != 200:
                error_msg = response.text[:200] if response.text else "Unknown error"
                raise Exception(f"External agent error: {response.status_code} - {error_msg}")
            
            # Parse response
            result = response.json()
            
            # Extract generated text (adapt format to your VPS response)
            if "text" in result:
                decision_text = result.get("text", "{}")
            elif "response" in result:
                decision_text = result.get("response", "{}")
            elif "decision" in result:
                decision_text = result.get("decision", "{}")
            else:
                # Assume entire result is the decision
                decision_text = json.dumps(result)
            
            # Validate it's valid JSON
            try:
                json.loads(decision_text)
            except json.JSONDecodeError:
                logger.error(f"External agent returned invalid JSON: {decision_text[:100]}")
                if self.fallback_to_mock:
                    return await MockLLMAdapter().generate(prompt)
                raise Exception("Invalid JSON from external agent")
            
            logger.info("✅ External agent decision generated successfully")
            self.is_healthy = True
            return decision_text
            
        except asyncio.TimeoutError:
            logger.error(f"External agent: request timeout after {self.timeout}s")
            if self.fallback_to_mock:
                logger.info("Switching to Mock LLM due to timeout")
                return await MockLLMAdapter().generate(prompt)
            raise Exception("External agent timeout")
            
        except Exception as e:
            logger.error(f"External agent error: {str(e)}")
            self.is_healthy = False
            if self.fallback_to_mock:
                logger.warning(f"Falling back to Mock LLM: {str(e)}")
                return await MockLLMAdapter().generate(prompt)
            raise Exception(f"External agent failed: {str(e)}")
    
    async def validate_connection(self) -> bool:
        """Test connection to external agent"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.api_endpoint}/health",
                    headers={"User-Agent": "TradingBot/1.0"}
                )
            
            self.is_healthy = response.status_code == 200
            logger.info(f"External agent health check: {'✅ OK' if self.is_healthy else '❌ Down'}")
            return self.is_healthy
            
        except Exception as e:
            logger.error(f"External agent health check failed: {str(e)}")
            self.is_healthy = False
            return False
```

---

### Step 2: Update LLMAdapter Factory

File: `packages/shared/llm_adapter.py` (modify `get_llm_adapter()` function)

```python
def get_llm_adapter(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    external_endpoint: Optional[str] = None
) -> LLMAdapter:
    """
    Factory function to get LLM adapter based on provider
    
    Args:
        provider: "openai" | "anthropic" | "gemini" | "groq" | "local" | "mock" | "external_agent"
        api_key: API key for the provider
        model: Model name
        external_endpoint: For external_agent provider, the VPS endpoint URL
    """
    
    provider = (provider or "openai").lower().strip()
    
    if provider == "openai":
        return OpenAIAdapter(
            api_key=api_key,
            model=model or "gpt-4-turbo"
        )
    
    elif provider in ("anthropic", "claude"):
        return ClaudeAdapter(
            api_key=api_key,
            model=model or "claude-3-opus-20240229"
        )
    
    elif provider in ("gemini", "google"):
        return GeminiAdapter(
            api_key=api_key,
            model=model or "gemini-2.5-flash"
        )
    
    elif provider == "groq":
        return GroqAdapter(
            api_key=api_key,
            model=model or "llama-3.1-8b-instant"
        )
    
    elif provider == "local":
        return LocalLLMAdapter(
            api_key=api_key or "not-needed",
            model=model or "local-model"
        )
    
    elif provider == "external_agent":
        # NEW: Handle external AI agents
        if not external_endpoint:
            raise ValueError("external_endpoint required for external_agent provider")
        
        from packages.shared.external_agent_adapter import ExternalAIAgentAdapter
        return ExternalAIAgentAdapter(
            api_endpoint=external_endpoint,
            api_key=api_key,
            model=model or "trading-agents-v1"
        )
    
    elif provider == "mock":
        return MockLLMAdapter()
    
    else:
        logger.warning(f"Unknown provider '{provider}', using Mock")
        return MockLLMAdapter()
```

---

### Step 3: Add External Agent Config to UserCredential

File: `packages/shared/models.py` (add to UserCredential class)

```python
class UserCredential(Base):
    """Encrypted per-user credentials and custom AI settings"""
    __tablename__ = "user_credentials"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), unique=True)
    
    # Existing fields...
    binance_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[str] = mapped_column(String(20), default="openai")
    ai_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_model: Mapped[str] = mapped_column(String(50), default="gpt-4")
    
    # NEW: External AI Agent Settings
    external_agent_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    external_agent_endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)  # VPS URL
    external_agent_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)  # Billing key
    external_agent_model: Mapped[str | None] = mapped_column(String(50), default="trading-agents-v1")
    external_agent_last_health_check: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    external_agent_is_healthy: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Quota tracking
    monthly_api_calls: Mapped[int] = mapped_column(Integer, default=0)
    monthly_quota_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = unlimited
    quota_reset_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # First of month
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=datetime.utcnow)
```

---

### Step 4: Add Quota Tracking

File: `packages/shared/quota_tracker.py` (NEW FILE)

```python
"""
API Quota Tracking - Monitor LLM usage per user and provider
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from packages.shared.models import UserCredential

logger = logging.getLogger(__name__)


class QuotaTracker:
    """Track API usage and quota per user per provider"""
    
    @staticmethod
    async def record_api_call(
        session: AsyncSession,
        user_id: str,
        provider: str,
        tokens_used: int = 1,
        success: bool = True
    ) -> Dict[str, Any]:
        """
        Record API call for quota tracking
        
        Args:
            session: Database session
            user_id: User ID
            provider: LLM provider (openai, gemini, etc.)
            tokens_used: Approx tokens used
            success: Whether call succeeded
            
        Returns:
            Quota status dict
        """
        cred = await session.execute(
            select(UserCredential).where(UserCredential.user_id == user_id)
        )
        credential = cred.scalar_one_or_none()
        
        if not credential:
            return {"error": "No credentials found"}
        
        # Check if quota reset needed (new month)
        now = datetime.utcnow()
        if credential.quota_reset_date is None or now > credential.quota_reset_date:
            # Reset monthly quota on first of month
            credential.monthly_api_calls = 0
            credential.quota_reset_date = datetime(now.year, now.month, 1) + timedelta(days=32)
            credential.quota_reset_date = datetime(
                credential.quota_reset_date.year,
                credential.quota_reset_date.month,
                1
            )
        
        # Record this call
        if success:
            credential.monthly_api_calls += 1
        
        await session.commit()
        
        # Calculate quota status
        limit = credential.monthly_quota_limit
        used = credential.monthly_api_calls
        remaining = limit - used if limit else None
        percentage = (used / limit * 100) if limit else 0
        
        status = {
            "provider": provider,
            "month": credential.quota_reset_date.strftime("%Y-%m") if credential.quota_reset_date else "unknown",
            "api_calls_used": used,
            "quota_limit": limit,
            "remaining": remaining,
            "percentage_used": round(percentage, 1),
            "status": (
                "⚠️ Critical" if percentage > 90 else
                "🟡 Warning" if percentage > 70 else
                "✅ Healthy"
            )
        }
        
        logger.info(f"Quota tracked for {user_id}: {status}")
        return status
    
    @staticmethod
    async def get_quota_status(
        session: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Get current quota status for user"""
        cred = await session.execute(
            select(UserCredential).where(UserCredential.user_id == user_id)
        )
        credential = cred.scalar_one_or_none()
        
        if not credential:
            return {"error": "No credentials found"}
        
        limit = credential.monthly_quota_limit
        used = credential.monthly_api_calls
        remaining = limit - used if limit else None
        percentage = (used / limit * 100) if limit else 0
        
        return {
            "ai_provider": credential.ai_provider,
            "api_calls_used": used,
            "quota_limit": limit,
            "remaining": remaining,
            "percentage_used": round(percentage, 1),
            "status": (
                "Critical" if percentage > 90 else
                "Warning" if percentage > 70 else
                "Healthy"
            ),
            "external_agent_enabled": credential.external_agent_enabled,
            "external_agent_is_healthy": credential.external_agent_is_healthy,
            "quota_reset_date": credential.quota_reset_date.isoformat() if credential.quota_reset_date else None
        }
    
    @staticmethod
    async def set_quota_limit(
        session: AsyncSession,
        user_id: str,
        monthly_limit: int
    ):
        """Set monthly API quota limit for user"""
        await session.execute(
            update(UserCredential)
            .where(UserCredential.user_id == user_id)
            .values(monthly_quota_limit=monthly_limit)
        )
        await session.commit()
        logger.info(f"Quota limit set for {user_id}: {monthly_limit} calls/month")
```

---

### Step 5: Add API Endpoints for Quota Management

File: `apps/api/phase6_routes.py` (add new endpoints)

```python
# === External AI Agent & Quota Management Endpoints ===

@router.get("/quota/status")
async def get_quota_status(
    user_id: str | None = None,
    credentials = Depends(security)
):
    """Get API quota status for user"""
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    target_id = _get_target_user_id(requester, user_id)  # Admin can check others
    
    from packages.shared.quota_tracker import QuotaTracker
    async with AsyncSessionFactory() as session:
        status = await QuotaTracker.get_quota_status(session, target_id)
    
    return {
        "user_id": target_id,
        "quota": status
    }


@router.post("/external-agent/configure")
async def configure_external_agent(
    endpoint: str,
    api_key: str | None = None,
    model: str = "trading-agents-v1",
    monthly_quota: int | None = None,
    credentials = Depends(security)
):
    """Configure external AI agents model for user"""
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Only admin or self can configure
    if requester.id != requester.id and requester.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    async with AsyncSessionFactory() as session:
        from packages.shared.models import UserCredential
        from packages.shared.encryption import encrypt_key
        
        cred = await session.execute(
            select(UserCredential).where(UserCredential.user_id == requester.id)
        )
        credential = cred.scalar_one_or_none()
        
        if not credential:
            raise HTTPException(status_code=404, detail="Credentials not found")
        
        credential.external_agent_endpoint = endpoint
        if api_key:
            credential.external_agent_api_key = encrypt_key(api_key)
        credential.external_agent_model = model
        if monthly_quota:
            credential.monthly_quota_limit = monthly_quota
        credential.external_agent_enabled = True
        
        await session.commit()
        
        # Test connection
        from packages.shared.external_agent_adapter import ExternalAIAgentAdapter
        adapter = ExternalAIAgentAdapter(
            api_endpoint=endpoint,
            api_key=api_key,
            model=model
        )
        is_healthy = await adapter.validate_connection()
        credential.external_agent_is_healthy = is_healthy
        await session.commit()
    
    return {
        "status": "success",
        "message": "External agent configured",
        "endpoint": endpoint,
        "model": model,
        "connection_status": "✅ Healthy" if is_healthy else "❌ Failed",
        "monthly_quota": monthly_quota
    }


@router.get("/external-agent/health")
async def check_external_agent_health(
    credentials = Depends(security)
):
    """Check health of configured external agent"""
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        from packages.shared.models import UserCredential
        from packages.shared.encryption import decrypt_key
        
        cred = await session.execute(
            select(UserCredential).where(UserCredential.user_id == requester.id)
        )
        credential = cred.scalar_one_or_none()
        
        if not credential or not credential.external_agent_endpoint:
            raise HTTPException(status_code=404, detail="External agent not configured")
        
        from packages.shared.external_agent_adapter import ExternalAIAgentAdapter
        
        adapter = ExternalAIAgentAdapter(
            api_endpoint=credential.external_agent_endpoint,
            api_key=decrypt_key(credential.external_agent_api_key) if credential.external_agent_api_key else None,
            model=credential.external_agent_model
        )
        
        is_healthy = await adapter.validate_connection()
        credential.external_agent_is_healthy = is_healthy
        credential.external_agent_last_health_check = datetime.utcnow()
        await session.commit()
    
    return {
        "external_agent_configured": True,
        "endpoint": credential.external_agent_endpoint,
        "model": credential.external_agent_model,
        "status": "✅ Healthy" if is_healthy else "❌ Down",
        "last_check": credential.external_agent_last_health_check.isoformat(),
        "fallback_available": "✅ Mock LLM" if is_healthy else "⚠️ Low quality decisions"
    }
```

---

## 📋 Testing Checklist

### Unit Tests

File: `tests/test_external_agent.py`

```python
import pytest
from packages.shared.external_agent_adapter import ExternalAIAgentAdapter
from packages.shared.llm_adapter import MockLLMAdapter


@pytest.mark.asyncio
async def test_external_agent_adapter_initialization():
    """Test adapter initialization"""
    adapter = ExternalAIAgentAdapter(
        api_endpoint="http://localhost:5000"
    )
    assert adapter.is_healthy is False
    assert adapter.fallback_to_mock is True


@pytest.mark.asyncio
async def test_external_agent_fallback_on_timeout():
    """Test fallback to Mock when external agent times out"""
    adapter = ExternalAIAgentAdapter(
        api_endpoint="http://invalid-endpoint:9999",
        timeout=1,
        fallback_to_mock=True
    )
    
    prompt = "Test prompt"
    result = await adapter.generate(prompt)
    
    # Should fall back to Mock and return valid JSON
    import json
    decision = json.loads(result)
    assert "decision_type" in decision


@pytest.mark.asyncio
async def test_quota_tracking():
    """Test quota tracking system"""
    from packages.shared.quota_tracker import QuotaTracker
    from packages.shared.database import AsyncSessionFactory
    
    async with AsyncSessionFactory() as session:
        # Create test user with quota limit
        status = await QuotaTracker.record_api_call(
            session,
            user_id="test_user",
            provider="external_agent",
            tokens_used=100,
            success=True
        )
        
        assert status["api_calls_used"] >= 1
        assert "percentage_used" in status
```

---

## 🚀 Deployment Checklist

- [ ] Database migration created and tested
- [ ] User model updated with bot control fields
- [ ] Worker updated to check bot_enabled
- [ ] API endpoints created and tested
- [ ] Telegram commands added
- [ ] ExternalAIAgentAdapter implemented
- [ ] LLM adapter factory updated
- [ ] UserCredential model extended
- [ ] Quota tracking system implemented
- [ ] Health check endpoints added
- [ ] Dashboard UI updated
- [ ] Logging configured
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Staging deployment
- [ ] Production deployment

---

**Configuration Template for Your VPS Integration:**

```yaml
# .env additions for external agent
EXTERNAL_AGENT_ENDPOINT=http://your-vps-ip:5000
EXTERNAL_AGENT_API_KEY=your-billing-key-here
EXTERNAL_AGENT_MODEL=trading-agents-v1
EXTERNAL_AGENT_TIMEOUT=30

# Quota settings
USER_MONTHLY_API_QUOTA=10000  # Calls per month per user
QUOTA_WARNING_THRESHOLD=0.7   # Alert at 70% usage
QUOTA_CRITICAL_THRESHOLD=0.9  # Critical at 90% usage
```

