"""
JWT Authentication for dashboard
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from pydantic import BaseModel

from packages.shared.config import settings
from packages.shared.logger import logger
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import User, UserLoginLog, SessionLog, Position
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import uuid
import asyncio


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserAuth(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    role: str  # admin, trader, viewer


class JWTHandler:
    """JWT token management with session tracking"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_hours = 24

    def create_access_token(self, user: User) -> Token:
        """Create JWT access token with session tracking"""
        expire_delta = timedelta(hours=self.access_token_expire_hours)
        expire = datetime.now(timezone.utc) + expire_delta

        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "session_id": str(uuid.uuid4()),
        }

        encoded_jwt = jwt.encode(
            payload, self.secret_key, algorithm=self.algorithm
        )

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
        
        user.last_session_token = token[:100] if token else None
        user.last_session_refresh_at = datetime.utcnow()
        user.session_expiry_at = expiry
        user.graceful_exit_at = None
        user.bot_enabled = True
        
        # Log session
        log = SessionLog(
            user_id=user.id,
            session_token=token[:100] if token else "unknown",
            login_at=datetime.utcnow(),
            expired_at=expiry,
            status="ACTIVE"
        )
        session.add(log)
        await session.commit()

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.error("jwt_error", error="Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error("jwt_error", error=str(e))
            return None

    async def verify_token(self, token: str) -> Optional[User]:
        """Verify token and return user from DB"""
        payload = self.decode_token(token)
        if not payload:
            return None

        user_id = payload.get("sub", "")
        async with AsyncSessionFactory() as session:
            from sqlalchemy import select
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            return user


class SessionManager:
    """Manage user session lifecycle and 24h token expiry"""
    
    @staticmethod
    async def check_session_valid(
        session: AsyncSession,
        user: User
    ) -> Dict[str, Any]:
        """Check if user's session is still valid"""
        
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
        
        # Log logout
        log = SessionLog(
            user_id=user.id,
            session_token=user.last_session_token or "unknown",
            login_at=datetime.utcnow(),
            logout_at=datetime.utcnow(),
            expired_at=datetime.utcnow(),
            status="CLOSED",
            action_taken="CLOSED_ALL" if close_positions else "BOT_PAUSED"
        )
        session.add(log)
        await session.commit()


class DatabaseUserManager:
    """Production DB-backed user manager"""

    def _hash_password(self, password: str) -> str:
        # Phase 1: SHA-256 (Simple but sufficient for Beta, upgrade to bcrypt in Ph2)
        return hashlib.sha256(password.encode()).hexdigest()

    async def get_user(self, username: str) -> Optional[User]:
        """Get user by username from DB"""
        async with AsyncSessionFactory() as session:
            from sqlalchemy import select
            result = await session.execute(select(User).where(User.username == username))
            return result.scalar_one_or_none()

    async def verify_password(self, username: str, password: str) -> Optional[User]:
        """Verify user credentials and return user object"""
        user = await self.get_user(username)
        if not user:
            return None

        # Compare hash
        if user.password_hash == password or user.password_hash == self._hash_password(password):
             return user
        return None

    async def log_login(self, user_id: str, client_info: dict):
        """Record login session with IP, OS, Browser, etc."""
        async with AsyncSessionFactory() as session:
            log = UserLoginLog(
                user_id=user_id,
                ip_address=client_info.get("ip", "0.0.0.0"),
                user_agent=client_info.get("user_agent", ""),
                os=client_info.get("os"),
                browser=client_info.get("browser"),
                device_type=client_info.get("device_type"),
                country=client_info.get("country"),
                region=client_info.get("region"),
                city=client_info.get("city")
            )
            session.add(log)
            # Update last login
            from sqlalchemy import update
            await session.execute(
                update(User).where(User.id == user_id).values(last_login_at=datetime.utcnow())
            )
            await session.commit()


# Global instances
jwt_handler = JWTHandler(
    secret_key=settings.jwt_secret or "demo-secret-key-change-in-production"
)
user_manager = DatabaseUserManager()
