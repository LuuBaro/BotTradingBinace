"""
JWT Authentication for dashboard
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from pydantic import BaseModel

from packages.shared.config import settings
from packages.shared.logger import logger


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class User(BaseModel):
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

    def verify_token(self, token: str) -> Optional[User]:
        """Verify token and return user"""
        payload = self.decode_token(token)
        if not payload:
            return None

        try:
            return User(
                id=payload.get("sub", ""),
                username=payload.get("username", ""),
                role=payload.get("role", "viewer"),
            )
        except Exception as e:
            logger.error("jwt_verification_error", error=str(e))
            return None


class DemoUserManager:
    """Demo user database (for testing)"""

    def __init__(self):
        self.users = {
            "admin": {
                "password": "admin",
                "id": "user_admin_001",
                "email": "admin@trading.bot",
                "role": "admin",
            },
            "trader": {
                "password": "trader",
                "id": "user_trader_001",
                "email": "trader@trading.bot",
                "role": "trader",
            },
            "viewer": {
                "password": "viewer",
                "id": "user_viewer_001",
                "email": "viewer@trading.bot",
                "role": "viewer",
            },
        }

    def get_user(self, username: str) -> Optional[User]:
        """Get user by username"""
        user_data = self.users.get(username)
        if not user_data:
            return None

        return User(
            id=user_data["id"],
            username=username,
            email=user_data["email"],
            role=user_data["role"],
        )

    def verify_password(self, username: str, password: str) -> bool:
        """Verify user credentials"""
        user_data = self.users.get(username)
        if not user_data:
            return False

        # Demo: plain text comparison (use proper hashing in production)
        return user_data["password"] == password


# Global instances
jwt_handler = JWTHandler(
    secret_key=settings.jwt_secret or "demo-secret-key-change-in-production"
)
user_manager = DemoUserManager()
