"""
JWT Authentication for dashboard
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from pathlib import Path
import json
import jwt
from pydantic import BaseModel
from google.auth.transport import requests
from google.oauth2 import id_token
import pyotp
import qrcode
import bcrypt
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

    def get_totp_qrcode(self, secret: str, username: str, issuer: str | None = None) -> str:
        """Generate QR code for TOTP setup"""
        issuer_name = issuer or settings.app_name or "TiznDBot"
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=username, issuer_name=issuer_name)
        
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
    """User database with security: password hashing, rate limiting, setup system"""

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 180  # 3 hours

    def __init__(self):
        # Persist auth state to disk so restart does not wipe users/2FA setup
        self.state_file = Path("data/auth_state.json")

        # Setup system - only allow first-time setup
        self.setup_complete = False
        self.system_2fa_locked = False

        # Empty users - populated via first-time setup
        self.users: Dict[str, Dict[str, Any]] = {}

        # Track failed login attempts: {username: {attempts: int, locked_until: datetime}}
        self.failed_attempts: Dict[str, Dict[str, Any]] = {}

        self._load_state()

    def _load_state(self):
        try:
            if not self.state_file.exists():
                return
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
            self.setup_complete = bool(raw.get("setup_complete", False))
            self.system_2fa_locked = bool(raw.get("system_2fa_locked", False))
            self.users = raw.get("users", {}) or {}
            # failed attempts is runtime-volatile; do not persist lockouts across restarts
            self.failed_attempts = {}
            logger.info("auth_state_loaded", users=len(self.users), setup_complete=self.setup_complete)
        except Exception as e:
            logger.error("auth_state_load_failed", error=str(e))

    def _save_state(self):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "setup_complete": self.setup_complete,
                "system_2fa_locked": self.system_2fa_locked,
                "users": self.users,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("auth_state_save_failed", error=str(e))

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, username: str, password: str) -> tuple[bool, str]:
        """
        Verify user credentials with rate limiting
        Returns: (success: bool, message: str)
        """
        user_data = self.users.get(username)
        if not user_data:
            self._record_failed_attempt(username)
            return False, "User not found"

        # Check if account is locked
        is_locked, unlock_time = self._is_account_locked(username)
        if is_locked:
            minutes_left = int((unlock_time - datetime.now(timezone.utc)).total_seconds() / 60)
            logger.warning("login_attempt_locked", username=username, minutes_left=minutes_left)
            return False, f"Account locked. Try again in {minutes_left} minutes"

        # Verify password hash
        try:
            password_hash = user_data.get("password_hash")
            if not password_hash:
                return False, "Invalid credentials"
            
            if not bcrypt.checkpw(password.encode(), password_hash.encode()):
                self._record_failed_attempt(username)
                attempts_left = self.MAX_LOGIN_ATTEMPTS - (self.failed_attempts.get(username, {}).get("attempts", 0))
                logger.warning("login_failed", username=username, attempts_left=attempts_left)
                return False, f"Invalid password. {attempts_left} attempts remaining"
            
            # Clear failed attempts on successful login
            if username in self.failed_attempts:
                del self.failed_attempts[username]
            
            logger.info("login_success", username=username)
            return True, "Login successful"
        except Exception as e:
            logger.error("password_verification_error", error=str(e))
            return False, "Authentication error"

    def _record_failed_attempt(self, username: str):
        """Track failed login attempt"""
        if username not in self.failed_attempts:
            self.failed_attempts[username] = {"attempts": 0, "locked_until": None}
        
        self.failed_attempts[username]["attempts"] += 1
        
        # Lock account if max attempts reached
        if self.failed_attempts[username]["attempts"] >= self.MAX_LOGIN_ATTEMPTS:
            lockout_until = datetime.now(timezone.utc) + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
            self.failed_attempts[username]["locked_until"] = lockout_until
            logger.warning("account_locked_max_attempts", username=username)

    def _is_account_locked(self, username: str) -> tuple[bool, Optional[datetime]]:
        """Check if account is locked"""
        if username not in self.failed_attempts:
            return False, None
        
        locked_until = self.failed_attempts[username].get("locked_until")
        if not locked_until:
            return False, None
        
        # Check if lockout period has expired
        if datetime.now(timezone.utc) > locked_until:
            # Unlock account
            del self.failed_attempts[username]
            return False, None
        
        return True, locked_until

    def create_first_user(self, username: str, password: str, email: str) -> tuple[bool, str]:
        """Create first admin user during setup"""
        if self.setup_complete:
            return False, "Setup already completed"
        
        if not username or not password or not email:
            return False, "Username, password, and email are required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        
        if username in self.users:
            return False, "Username already exists"
        
        # Create the first user
        password_hash = self.hash_password(password)
        self.users[username] = {
            "password_hash": password_hash,
            "id": f"user_{username}_{secrets.token_hex(4)}",
            "email": email,
            "role": "admin",  # First user is always admin
            "totp_secret": None,
            "totp_enabled": False,
            "backup_codes": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Mark setup as complete
        self.setup_complete = True
        self._save_state()

        logger.info("first_user_created", username=username, email=email)
        return True, "Admin user created successfully"

    def is_setup_complete(self) -> bool:
        """Check if first-time setup is complete"""
        return self.setup_complete

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

    def get_username_by_email(self, email: str) -> Optional[str]:
        """Find username by email"""
        email_normalized = (email or "").strip().lower()
        for username, user_data in self.users.items():
            if (user_data.get("email") or "").strip().lower() == email_normalized:
                return username
        return None

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change user password"""
        if username not in self.users:
            return False
        
        if len(new_password) < 8:
            return False
        
        # Verify old password
        success, _ = self.verify_password(username, old_password)
        if not success:
            return False
        
        # Hash and store new password
        password_hash = self.hash_password(new_password)
        self.users[username]["password_hash"] = password_hash
        self._save_state()
        logger.info("password_changed", username=username)
        return True

    def reset_password(self, username: str) -> Optional[str]:
        """Reset password to temporary one (admin only)"""
        if username not in self.users:
            return None
        
        # Generate temp password
        temp_password = secrets.token_urlsafe(12)
        password_hash = self.hash_password(temp_password)
        self.users[username]["password_hash"] = password_hash
        self._save_state()

        logger.info("password_reset_admin", username=username)
        return temp_password

    def set_password(self, username: str, new_password: str) -> bool:
        """Set new password directly (used for verified email reset flow)"""
        if username not in self.users:
            return False
        if len((new_password or "").strip()) < 8:
            return False

        password_hash = self.hash_password(new_password.strip())
        self.users[username]["password_hash"] = password_hash
        self._save_state()
        logger.info("password_set_via_verified_reset", username=username)
        return True

    def get_or_create_user(self, email: str, name: str, google_id: str) -> User:
        """Get or create user from Google OAuth"""
        # Use email as username for Google users
        username = email.split('@')[0]
        
        # If user already exists, return it
        if username in self.users:
            user_data = self.users[username]
            return User(
                id=user_data["id"],
                username=username,
                email=user_data["email"],
                role=user_data["role"],
            )
        
        # Create new user from Google OAuth
        user_id = f"user_google_{google_id[:10]}"
        self.users[username] = {
            "password_hash": None,
            "id": user_id,
            "email": email,
            "role": "admin" if not self.users else "trader",
            "oauth_provider": "google",
            "oauth_id": google_id,
            "totp_secret": None,
            "totp_enabled": False,
            "backup_codes": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_state()

        logger.info("user_created_from_google", username=username, email=email)
        
        return User(
            id=user_id,
            username=username,
            email=email,
            role=self.users[username]["role"],
        )

    def setup_totp(self, username: str, secret: str, backup_codes: list[dict]) -> bool:
        """Set up TOTP for user"""
        if username not in self.users:
            return False
        
        self.users[username]["totp_secret"] = secret
        self.users[username]["totp_enabled"] = True
        self.users[username]["backup_codes"] = backup_codes
        self.system_2fa_locked = True
        self._save_state()

        logger.info("totp_setup_completed", username=username)
        return True

    def is_2fa_setup_allowed(self, username: str) -> bool:
        """Check if 2FA setup is allowed for this user"""
        if self.system_2fa_locked:
            user_data = self.users.get(username)
            if user_data and user_data.get("totp_enabled"):
                return True
            return False
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
                self._save_state()
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
        self._save_state()

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
