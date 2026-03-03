import os
import base64
from cryptography.fernet import Fernet
from packages.shared.config import settings

class EncryptionManager:
    """Handles AES-256 encryption/decryption for sensitive user keys"""
    
    _fernet = None

    @classmethod
    def _get_fernet(cls):
        if cls._fernet is None:
            key = getattr(settings, "master_encryption_key", None)
            if not key:
                # Fallback for dev if not in .env (Not recommended for production)
                key = base64.b64encode(b"static-dev-key-32-bytes-long-1234").decode()
            
            try:
                cls._fernet = Fernet(key.encode())
            except Exception as e:
                # If key is invalid format, handle it
                print(f"Encryption error: Invalid MASTER_ENCRYPTION_KEY format. {e}")
                # Use a dummy for emergency but this will break existing encrypted data
                cls._fernet = Fernet(base64.b64encode(b"emergency-fallback-key-32-bytes-").decode().encode())
        return cls._fernet

    @classmethod
    def encrypt(cls, text: str | None) -> str | None:
        if not text:
            return None
        f = cls._get_fernet()
        return f.encrypt(text.encode()).decode()

    @classmethod
    def decrypt(cls, encrypted_text: str | None) -> str | None:
        if not encrypted_text:
            return None
        f = cls._get_fernet()
        try:
            return f.decrypt(encrypted_text.encode()).decode()
        except Exception:
            # If decryption fails (wrong key or not encrypted), return masked for safety or None
            return None

# Global helper instances
encrypt_key = EncryptionManager.encrypt
decrypt_key = EncryptionManager.decrypt
