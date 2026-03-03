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
from packages.shared.models import User, UserLoginLog
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
    """JWT token management"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = 1440  # 24 hours

    def create_access_token(self, user: User) -> Token:
        """Create JWT access token"""
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self.access_token_expire_minutes
        )

        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }

        encoded_jwt = jwt.encode(
            payload, self.secret_key, algorithm=self.algorithm
        )

        return Token(
            access_token=encoded_jwt,
            expires_in=self.access_token_expire_minutes * 60,
        )

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
