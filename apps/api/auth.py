"""
JWT Authentication for dashboard
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from pydantic import BaseModel
from google.auth.transport import requests
from google.oauth2 import id_token
import pyotp
import qrcode
from io import BytesIO
import base64
import secrets
import string

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

    def verify_google_token(self, id_token_str: str, client_id: str) -> Optional[Dict[str, Any]]:
        """Verify Google ID token and return claims"""
        try:
            # Verify the token signature and get claims
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                requests.Request(),
                client_id
            )
            
            # Check if token is valid
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                logger.warning("google_auth_invalid_issuer", issuer=idinfo.get('iss'))
                return None
            
            logger.info(
                "google_token_verified",
                email=idinfo.get('email'),
                name=idinfo.get('name')
            )
            return idinfo
        except ValueError as e:
            logger.error("google_token_verification_failed", error=str(e))
            return None

    def generate_totp_secret(self) -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()

    def get_totp_qrcode(self, secret: str, username: str, issuer: str = "BotTrading") -> str:
        """Generate QR code for TOTP setup"""
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=username, issuer_name=issuer)
        
        # Generate QR code and return as base64
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{qr_base64}"

    def verify_totp(self, secret: str, code: str) -> bool:
        """Verify TOTP code (allows 30-second window)"""
        try:
            totp = pyotp.TOTP(secret)
            # Allow 1 time window before and after current time
            return totp.verify(code, valid_window=1)
        except Exception as e:
            logger.error("totp_verification_error", error=str(e))
            return False

    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """Generate backup codes for account recovery"""
        codes = []
        for _ in range(count):
            # Generate code: XXXX-XXXX-XXXX-XXXX
            code_parts = []
            for _ in range(4):
                code_parts.append(''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)))
            code = '-'.join(code_parts)
            codes.append({
                "code": code,
                "used": False,
                "used_at": None
            })
        return codes


class DemoUserManager:
    """Demo user database (for testing)"""

    def __init__(self):
        # System lock - only allow 1 user to setup 2FA on first initialization
        self.system_2fa_locked = False
        
        self.users = {
            "admin": {
                "password": "admin",
                "id": "user_admin_001",
                "email": "admin@trading.bot",
                "role": "admin",
                "totp_secret": None,
                "totp_enabled": False,
                "backup_codes": [],
            },
            "trader": {
                "password": "trader",
                "id": "user_trader_001",
                "email": "trader@trading.bot",
                "role": "trader",
                "totp_secret": None,
                "totp_enabled": False,
                "backup_codes": [],
            },
            "viewer": {
                "password": "viewer",
                "id": "user_viewer_001",
                "email": "viewer@trading.bot",
                "role": "viewer",
                "totp_secret": None,
                "totp_enabled": False,
                "backup_codes": [],
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

    def change_password(self, username: str, new_password: str) -> bool:
        """Change user password"""
        if username not in self.users:
            return False
        
        if len(new_password) < 4:
            return False
        
        self.users[username]["password"] = new_password
        logger.info("password_changed", username=username)
        return True

    def reset_password(self, username: str) -> Optional[str]:
        """Reset password to default (username)"""
        if username not in self.users:
            return None
        
        # Reset to username as default (or generate temp password)
        temp_password = username
        self.users[username]["password"] = temp_password
        logger.info("password_reset", username=username)
        return temp_password

    def get_or_create_user(self, email: str, name: str, google_id: str) -> User:
        """Get or create user from Google OAuth"""
        # Use email as username for Google users
        username = email.split('@')[0]  # Extract username from email
        
        # If user already exists, return it
        if username in self.users:
            user_data = self.users[username]
            return User(
                id=user_data["id"],
                username=username,
                email=user_data["email"],
                role=user_data["role"],
            )
        
        # Create new user from Google
        user_id = f"user_google_{google_id[:10]}"
        self.users[username] = {
            "password": None,  # No password for OAuth users
            "id": user_id,
            "email": email,
            "role": "admin",  # Auto-admin for first Google user (personal bot)
            "oauth_provider": "google",
            "oauth_id": google_id,
            "totp_secret": None,
            "totp_enabled": False,
            "backup_codes": [],
        }
        
        logger.info(
            "user_created_from_google",
            username=username,
            email=email,
            role="admin"
        )
        
        return User(
            id=user_id,
            username=username,
            email=email,
            role="admin",
        )

    def setup_totp(self, username: str, secret: str, backup_codes: list[dict]) -> bool:
        """Set up TOTP for user"""
        if username not in self.users:
            return False
        
        self.users[username]["totp_secret"] = secret
        self.users[username]["totp_enabled"] = True
        self.users[username]["backup_codes"] = backup_codes
        
        # Lock system for future 2FA setups (only 1 user can setup)
        self.system_2fa_locked = True
        
        logger.info("totp_setup_completed", username=username)
        return True

    def is_2fa_setup_allowed(self, username: str) -> bool:
        """Check if 2FA setup is allowed for this user"""
        # Allow if system not locked, or if user already has 2FA enabled
        if self.system_2fa_locked:
            user_data = self.users.get(username)
            if user_data and user_data.get("totp_enabled"):
                # User already has 2FA, allow to update
                return True
            # System locked and user doesn't have 2FA
            return False
        # System not locked, allow setup
        return True

    def verify_backup_code(self, username: str, code: str) -> bool:
        """Verify and use a backup code (one-time use)"""
        if username not in self.users:
            return False
        
        backup_codes = self.users[username].get("backup_codes", [])
        
        for backup_code in backup_codes:
            if backup_code["code"] == code and not backup_code["used"]:
                backup_code["used"] = True
                backup_code["used_at"] = datetime.now(timezone.utc).isoformat()
                logger.info("backup_code_used", username=username)
                return True
        
        return False

    def reset_totp(self, username: str) -> bool:
        """Reset TOTP (disable 2FA)"""
        if username not in self.users:
            return False
        
        self.users[username]["totp_secret"] = None
        self.users[username]["totp_enabled"] = False
        self.users[username]["backup_codes"] = []
        
        logger.info("totp_reset", username=username)
        return True

    def get_remaining_backup_codes(self, username: str) -> int:
        """Get count of remaining backup codes"""
        if username not in self.users:
            return 0
        
        backup_codes = self.users[username].get("backup_codes", [])
        return len([code for code in backup_codes if not code["used"]])


# Global instances
jwt_handler = JWTHandler(
    secret_key=settings.jwt_secret or "demo-secret-key-change-in-production"
)
user_manager = DemoUserManager()
