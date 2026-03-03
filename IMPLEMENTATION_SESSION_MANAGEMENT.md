# IMPLEMENTATION: Session Management for Token 24h Logout Handling

This file contains the actual code to implement graceful bot shutdown when user session expires.

## STEP 1: Add Session Fields to User Model

File: `packages/shared/models.py`

```python
# Add these fields to the User class:

from datetime import datetime, timedelta

class User(Base):
    """Real user accounts for SaaS model"""
    __tablename__ = "users"
    
    # Existing fields...
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="trader")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # NEW SESSION MANAGEMENT FIELDS
    bot_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Session tracking (24h token management)
    last_session_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_session_refresh_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    session_expiry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    
    # Graceful logout handling
    auto_close_on_logout: Mapped[bool] = mapped_column(Boolean, default=True)
    grace_period_minutes: Mapped[int] = mapped_column(Integer, default=15)  # Allow 15 min to recover
    graceful_exit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Tracking
    last_bot_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bot_paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bot_pause_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_session_expiry", "session_expiry_at"),
        Index("ix_last_activity", "last_bot_activity_at"),
    )


# NEW TABLE: Session Logs
class SessionLog(Base):
    """Track all session activities and closes"""
    __tablename__ = "session_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), index=True)
    session_token: Mapped[str] = mapped_column(String(500), nullable=False)  # Partial JWT
    login_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    logout_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")  # ACTIVE, EXPIRED, CLOSED, GRACE_PERIOD
    positions_at_logout: Mapped[int] = mapped_column(Integer, default=0)
    action_taken: Mapped[str | None] = mapped_column(String(50), nullable=True)  # CLOSED_ALL, KEPT_OPEN, PAUSED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
```

## STEP 2: Create Alembic Migration

File: `alembic/versions/0002_session_management.py`

```python
"""add session management fields"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


def upgrade():
    # Add columns to users table
    op.add_column('users', sa.Column('last_session_token', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('last_session_refresh_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('session_expiry_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('auto_close_on_logout', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('grace_period_minutes', sa.Integer(), nullable=False, server_default='15'))
    op.add_column('users', sa.Column('graceful_exit_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_bot_activity_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('bot_paused_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('bot_pause_reason', sa.String(255), nullable=True))
    
    # Create indices
    op.create_index('ix_session_expiry', 'users', ['session_expiry_at'])
    op.create_index('ix_last_activity', 'users', ['last_bot_activity_at'])
    
    # Create session_logs table
    op.create_table(
        'session_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('session_token', sa.String(500), nullable=False),
        sa.Column('login_at', sa.DateTime(), nullable=False),
        sa.Column('logout_at', sa.DateTime(), nullable=True),
        sa.Column('expired_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='ACTIVE'),
        sa.Column('positions_at_logout', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('action_taken', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_user_id', 'user_id'),
        sa.Index('ix_expired_at', 'expired_at')
    )


def downgrade():
    op.drop_table('session_logs')
    op.drop_index('ix_last_activity', table_name='users')
    op.drop_index('ix_session_expiry', table_name='users')
    op.drop_column('users', 'bot_pause_reason')
    op.drop_column('users', 'bot_paused_at')
    op.drop_column('users', 'last_bot_activity_at')
    op.drop_column('users', 'graceful_exit_at')
    op.drop_column('users', 'grace_period_minutes')
    op.drop_column('users', 'auto_close_on_logout')
    op.drop_column('users', 'session_expiry_at')
    op.drop_column('users', 'last_session_refresh_at')
    op.drop_column('users', 'last_session_token')
```

Run migration:
```bash
alembic upgrade head
```

## STEP 3: Update JWT Handler for Session Management

File: `apps/api/auth.py`

```python
# Modify existing JWTHandler and add SessionManager

class JWTHandler:
    """JWT token management with session tracking"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_hours = 24  # Changed from minutes
    
    def create_access_token(self, user: User) -> Token:
        """Create JWT access token and register session"""
        expire_delta = timedelta(hours=self.access_token_expire_hours)
        expire = datetime.now(timezone.utc) + expire_delta
        
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "session_id": str(uuid.uuid4()),  # Track session
        }
        
        encoded_jwt = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return Token(
            access_token=encoded_jwt,
            expires_in=int(expire_delta.total_seconds()),
        )
    
    async def register_session(
        self,
        session: AsyncSession,
        user: User,
        token: str
    ) -> None:
        """Register new session for user"""
        
        expiry = datetime.utcnow() + timedelta(hours=self.access_token_expire_hours)
        
        user.last_session_token = token[:100]  # Store partial token
        user.last_session_refresh_at = datetime.utcnow()
        user.session_expiry_at = expiry
        user.graceful_exit_at = None  # Clear grace period
        user.bot_enabled = True  # Enable bot on login
        
        # Log session
        log = SessionLog(
            user_id=user.id,
            session_token=token[:100],
            login_at=datetime.utcnow(),
            expired_at=expiry,
            status="ACTIVE"
        )
        session.add(log)
        await session.commit()
        
        logger.info(f"Session registered for {user.username}, expires at {expiry}")
    
    async def refresh_session(
        self,
        session: AsyncSession,
        user: User
    ) -> Token:
        """Extend session for another 24 hours"""
        
        new_token = self.create_access_token(user)
        
        # Update session
        expiry = datetime.utcnow() + timedelta(hours=self.access_token_expire_hours)
        user.session_expiry_at = expiry
        user.last_session_refresh_at = datetime.utcnow()
        user.graceful_exit_at = None  # Clear grace period
        user.bot_enabled = True  # Re-enable if was paused
        
        await session.commit()
        
        logger.info(f"Session refreshed for {user.username}, expires at {expiry}")
        return new_token


class SessionManager:
    """Manage user session lifecycle"""
    
    @staticmethod
    async def check_session_valid(
        session: AsyncSession,
        user: User
    ) -> Dict[str, Any]:
        """
        Check if user's session is still valid
        Returns: {valid: bool, status: str, time_remaining_minutes: int}
        """
        
        if not user.session_expiry_at:
            return {
                "valid": True,
                "status": "no_session_tracking",
                "time_remaining_minutes": None
            }
        
        now = datetime.utcnow()
        time_remaining = user.session_expiry_at - now
        
        # Session expired?
        if now > user.session_expiry_at:
            # In grace period?
            grace_end = user.session_expiry_at + timedelta(minutes=user.grace_period_minutes)
            if now > grace_end:
                return {
                    "valid": False,
                    "status": "grace_period_ended",
                    "time_remaining_minutes": 0,
                    "action_required": "force_close"
                }
            else:
                grace_remaining = (grace_end - now).total_seconds() / 60
                return {
                    "valid": False,
                    "status": "grace_period",
                    "grace_remaining_minutes": int(grace_remaining),
                    "time_remaining_minutes": 0
                }
        
        return {
            "valid": True,
            "status": "active",
            "time_remaining_minutes": int(time_remaining.total_seconds() / 60)
        }
    
    @staticmethod
    async def logout_user(
        session: AsyncSession,
        user: User,
        close_positions: bool = True
    ) -> None:
        """User-initiated logout"""
        
        user.session_expiry_at = datetime.utcnow()
        user.bot_enabled = False
        
        if close_positions:
            # Mark all positions for closure
            positions = await session.execute(
                select(Position).where(
                    Position.user_id == user.id,
                    Position.status == "OPEN"
                )
            )
            for pos in positions.scalars():
                pos.status = "CLOSING_REQUESTED"
                pos.close_reason = "User logout - position close requested"
        
        # Log logout
        log = SessionLog(
            user_id=user.id,
            session_token=user.last_session_token or "unknown",
            logout_at=datetime.utcnow(),
            expired_at=datetime.utcnow(),
            status="CLOSED",
            action_taken="CLOSED_ALL" if close_positions else "BOT_PAUSED"
        )
        session.add(log)
        await session.commit()
        
        logger.info(f"User {user.username} logged out, positions: {'closed' if close_positions else 'kept'}")


# Update login endpoint
@router.post("/login")
async def login(request: LoginRequest):
    """Login endpoint with session registration"""
    
    user_manager = DatabaseUserManager()
    user = await user_manager.verify_password(request.username, request.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = jwt_handler.create_access_token(user)
    
    # Register session in database
    async with AsyncSessionFactory() as db_session:
        db_user = await db_session.get(User, user.id)
        await jwt_handler.register_session(db_session, db_user, token.access_token)
    
    return {
        "access_token": token.access_token,
        "token_type": token.token_type,
        "expires_in": token.expires_in,
        "session_expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }
```

## STEP 4: Update Worker to Check Session Validity

File: `apps/worker/main.py`

```python
# Modify the main worker loop:

async def run(self) -> None:
    """Main dispatcher loop - now with session checking"""
    self.running = True
    logger.info("worker_started")
    
    last_heartbeat = 0
    
    while self.running:
        try:
            # Heartbeat
            now_ts = datetime.now(timezone.utc).timestamp()
            if now_ts - last_heartbeat > 60:
                async with AsyncSessionFactory() as session:
                    session.add(Event(
                        timestamp=datetime.now(timezone.utc),
                        level="INFO",
                        code="WORKER_HEARTBEAT",
                        message="Worker active, checking sessions...",
                    ))
                    await session.commit()
                last_heartbeat = now_ts

            # Get active users WITH VALID SESSIONS
            async with AsyncSessionFactory() as session:
                users_res = await session.execute(
                    select(User)
                    .join(BotConfig, User.id == BotConfig.user_id)
                    .where(
                        BotConfig.is_active == True,
                        User.is_active == True,
                        User.bot_enabled == True  # NEW: Check bot_enabled
                    )
                    .distinct()
                )
                all_users = users_res.scalars().all()
                
                # Filter by valid sessions
                active_users = []
                for user in all_users:
                    session_status = await SessionManager.check_session_valid(session, user)
                    
                    if session_status["status"] == "grace_period_ended":
                        # Force close all positions
                        logger.warning(f"Session grace period ended for {user.username}, force closing")
                        await self._force_close_all_positions(session, user, reason="Session expired - grace period ended")
                        user.bot_enabled = False
                        await session.commit()
                        
                    elif session_status["status"] == "grace_period":
                        # In grace period - alert user but continue trading
                        logger.warning(f"Grace period for {user.username}: {session_status.get('grace_remaining_minutes')} min left")
                        # Continue to trade but log the status
                        active_users.append(user)
                        
                    elif session_status["valid"]:
                        # Normal trading
                        active_users.append(user)
                        # Update last activity
                        user.last_bot_activity_at = datetime.now(timezone.utc).replace(tzinfo=None)
                
                await session.commit()
            
            # Process active users
            for user in active_users:
                if not self.running:
                    break
                try:
                    async with AsyncSessionFactory() as user_session:
                        await self._process_user_trading(user_session, user)
                except Exception as user_err:
                    logger.error("user_trading_failed", user=user.username, error=str(user_err))

            self.loop_count += 1
            await asyncio.sleep(settings.worker_loop_interval_sec)
            
        except Exception as e:
            logger.error("worker_main_loop_error", error=str(e))
            await asyncio.sleep(10)

async def _force_close_all_positions(self, session: AsyncSession, user: User, reason: str):
    """Force close all positions immediately (market order)"""
    
    positions = await session.execute(
        select(Position).where(
            Position.user_id == user.id,
            Position.status == "OPEN"
        )
    )
    
    for pos in positions.scalars():
        try:
            # Use market order for instant closure
            order = await self.execution_engine.place_order(
                symbol=pos.symbol,
                side="SELL" if pos.side == "LONG" else "BUY",
                order_type="MARKET",
                quantity=pos.qty,
                reduce_only=True
            )
            
            pos.status = "CLOSED"
            pos.close_reason = reason
            
            # Log closure
            await self._log_user_event(
                session, user.id, "POSITION_FORCE_CLOSED",
                f"Force closed {pos.symbol} ({pos.side}) due to: {reason}",
                {"position_id": pos.id, "reason": reason},
                level="WARNING"
            )
            
        except Exception as e:
            logger.error(f"Failed to force close position {pos.id}: {str(e)}")
    
    await session.commit()

async def _graceful_close_positions(self, session: AsyncSession, user: User):
    """Close positions using limit orders (safer, less slippage)"""
    
    positions = await session.execute(
        select(Position).where(
            Position.user_id == user.id,
            Position.status == "OPEN"
        )
    )
    
    for pos in positions.scalars():
        try:
            # Get current price
            snapshot = await self.exchange.fetch_mark_price(pos.symbol)
            current_price = snapshot.close
            
            # Place limit order slightly favorable
            if pos.side == "LONG":
                close_price = current_price * 1.001  # 0.1% above
            else:
                close_price = current_price * 0.999  # 0.1% below
            
            order = await self.execution_engine.place_order(
                symbol=pos.symbol,
                side="SELL" if pos.side == "LONG" else "BUY",
                order_type="LIMIT",
                quantity=pos.qty,
                price=close_price,
                reduce_only=True,
                time_in_force="GTC"
            )
            
            pos.status = "CLOSING"
            pos.close_reason = "Session expired - graceful limit close"
            
            await self._log_user_event(
                session, user.id, "POSITION_GRACEFUL_CLOSING",
                f"Gracefully closing {pos.symbol}: limit order at {close_price}",
                {"position_id": pos.id, "limit_price": close_price}
            )
            
        except Exception as e:
            logger.error(f"Graceful close failed for {pos.id}, forcing market close: {str(e)}")
            # Fallback to market close
            await self._force_close_all_positions(session, user, "Graceful close failed")
    
    await session.commit()
```

## STEP 5: API Endpoints for Session Management

File: `apps/api/phase4_routes.py` (add these endpoints)

```python
from apps.api.auth import SessionManager

@router.get("/session/status")
async def get_session_status(
    credentials = Depends(security)
):
    """Get current session status with timeline"""
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        # Re-fetch user to get latest session data
        db_user = await session.get(User, user.id)
        session_status = await SessionManager.check_session_valid(session, db_user)
        
        # Get open positions
        positions = await session.execute(
            select(Position).where(
                Position.user_id == user.id,
                Position.status == "OPEN"
            )
        )
        open_count = len(positions.scalars().all())
    
    time_remaining = db_user.session_expiry_at - datetime.utcnow() if db_user.session_expiry_at else None
    
    return {
        "user_id": user.id,
        "username": user.username,
        "session_valid": session_status["valid"],
        "session_status": session_status["status"],
        "logged_in_at": db_user.last_session_refresh_at.isoformat() if db_user.last_session_refresh_at else None,
        "session_expires_at": db_user.session_expiry_at.isoformat() if db_user.session_expiry_at else None,
        "time_remaining_minutes": time_remaining.total_seconds() / 60 if time_remaining else None,
        "time_remaining_hours": time_remaining.total_seconds() / 3600 if time_remaining else None,
        "grace_period_minutes": db_user.grace_period_minutes,
        "auto_close_on_logout": db_user.auto_close_on_logout,
        "open_positions": open_count,
        "urgent_refresh_needed": (
            time_remaining and 
            time_remaining.total_seconds() < 3600 and
            open_count > 0
        ),
        "bot_enabled": db_user.bot_enabled
    }


@router.post("/session/refresh")
async def refresh_session(
    credentials = Depends(security)
):
    """Extend session for another 24 hours"""
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        db_user = await session.get(User, user.id)
        new_token = jwt_handler.create_access_token(db_user)
        await jwt_handler.register_session(session, db_user, new_token.access_token)
    
    return {
        "message": "✅ Session extended for 24 hours",
        "access_token": new_token.access_token,
        "expires_in": new_token.expires_in,
        "session_expires_at": db_user.session_expiry_at.isoformat()
    }


@router.post("/session/logout")
async def logout_endpoint(
    close_positions: bool = True,
    credentials = Depends(security)
):
    """User-initiated logout"""
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        db_user = await session.get(User, user.id)
        await SessionManager.logout_user(session, db_user, close_positions=close_positions)
    
    return {
        "message": "✅ Logout successful",
        "positions_closed": close_positions
    }


@router.put("/session/auto-close-settings")
async def configure_auto_close(
    auto_close: bool = True,
    grace_period: int = 15,  # minutes
    credentials = Depends(security)
):
    """Configure auto-close behavior on logout"""
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        db_user = await session.get(User, user.id)
        db_user.auto_close_on_logout = auto_close
        db_user.grace_period_minutes = max(5, min(grace_period, 60))  # 5-60 min
        await session.commit()
    
    return {
        "message": "✅ Settings updated",
        "auto_close_on_logout": auto_close,
        "grace_period_minutes": db_user.grace_period_minutes
    }


@router.get("/session/logs")
async def get_session_logs(
    limit: int = 20,
    credentials = Depends(security)
):
    """Get user's session history"""
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        logs = await session.execute(
            select(SessionLog)
            .where(SessionLog.user_id == user.id)
            .order_by(desc(SessionLog.expired_at))
            .limit(limit)
        )
        
        return [
            {
                "id": log.id,
                "login_at": log.login_at.isoformat(),
                "logout_at": log.logout_at.isoformat() if log.logout_at else None,
                "expired_at": log.expired_at.isoformat(),
                "duration_hours": ((log.logout_at or datetime.utcnow()) - log.login_at).total_seconds() / 3600,
                "status": log.status,
                "positions_at_logout": log.positions_at_logout,
                "action_taken": log.action_taken
            }
            for log in logs.scalars().all()
        ]
```

## STEP 6: React Dashboard Component for Session Warning

File: `apps/dashboard/src/components/SessionWarning.tsx`

```typescript
import React, { useEffect, useState } from 'react'
import { api } from '../api/client'

interface SessionStatus {
  session_valid: boolean
  session_status: string
  time_remaining_hours: number
  time_remaining_minutes: number
  open_positions: number
  auto_close_on_logout: boolean
  grace_period_minutes: number
  urgent_refresh_needed: boolean
}

export const SessionWarning: React.FC = () => {
  const [status, setStatus] = useState<SessionStatus | null>(null)
  const [showWarning, setShowWarning] = useState(false)
  const [showGraceWarning, setShowGraceWarning] = useState(false)

  useEffect(() => {
    checkSession()
    const interval = setInterval(checkSession, 60000) // Check every minute
    return () => clearInterval(interval)
  }, [])

  const checkSession = async () => {
    try {
      const response = await api.get('/session/status')
      setStatus(response.data)

      // Show warning if less than 1 hour remaining and has open positions
      if (response.data.time_remaining_hours < 1 && response.data.open_positions > 0) {
        setShowWarning(true)
      }

      // Show grace period warning
      if (response.data.session_status === 'grace_period') {
        setShowGraceWarning(true)
      }
    } catch (error) {
      console.error('Failed to check session:', error)
    }
  }

  const handleRefresh = async () => {
    try {
      await api.post('/session/refresh')
      setShowWarning(false)
      setShowGraceWarning(false)
      checkSession()
    } catch (error) {
      console.error('Failed to refresh session:', error)
    }
  }

  if (!status) return null

  return (
    <>
      {/* 1 Hour Warning */}
      {showWarning && !showGraceWarning && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-yellow-800">⏰ Session Expiring Soon</h3>
              <p className="text-sm text-yellow-700">
                {status.time_remaining_hours.toFixed(1)} hours remaining
              </p>
              {status.open_positions > 0 && (
                <p className="text-sm text-red-600 font-semibold">
                  ⚠️ {status.open_positions} open position(s)
                </p>
              )}
              {status.auto_close_on_logout ? (
                <p className="text-xs text-gray-600 mt-2">
                  ✅ Positions will close gracefully on logout (using limit orders)
                </p>
              ) : (
                <p className="text-xs text-red-600 mt-2">
                  ⚠️ Positions will REMAIN OPEN - You must login to close them!
                </p>
              )}
            </div>
            <button
              onClick={handleRefresh}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
            >
              Extend (24h)
            </button>
          </div>
        </div>
      )}

      {/* Grace Period Warning */}
      {showGraceWarning && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-red-800">🚨 Grace Period Active</h3>
              <p className="text-sm text-red-700">
                Session expired. {status.grace_period_minutes} minute grace period active.
              </p>
              <p className="text-xs text-red-600 mt-2">
                Login now or positions will close automatically!
              </p>
            </div>
            <button
              onClick={handleRefresh}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
            >
              Login Now
            </button>
          </div>
        </div>
      )}
    </>
  )
}

// Add to main App.tsx above rest of content:
export const App = () => {
  return (
    <div>
      <SessionWarning />
      {/* ... rest of app ... */}
    </div>
  )
}
```

## Summary

This implementation provides:

✅ **24h Token Management**
- JWT tokens expire after 24 hours
- Users get warning 1 hour before expiry
- Refresh endpoint extends session another 24 hours

✅ **Graceful Shutdown**
- If `auto_close_on_logout = true`: Positions close using limit orders (better prices)
- If `auto_close_on_logout = false`: Positions stay open, bot pauses, user must login to close

✅ **Grace Period**
- After logout, user has 15 minutes to login again
- If login within grace period, bot resumes trading
- If grace period expires, positions are force-closed with market orders

✅ **Session Tracking**
- All logins/logouts logged in `session_logs` table
- Dashboard shows session status and remaining time
- Alerts user about expiring sessions proactively

✅ **Safety**
- No silent position closures
- User chooses whether positions auto-close
- Clear warnings and notifications
- All actions logged for audit trail
