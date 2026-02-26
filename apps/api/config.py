"""
Production Configuration & Secrets Management
Handles environment-specific settings and secret management
"""
import os
from typing import Optional
from pydantic import BaseSettings, validator, Field
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Production settings with validation"""

    # Environment
    ENVIRONMENT: str = Field("production", description="Environment (development, staging, production)")
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    API_WORKERS: int = 4
    API_TIMEOUT: int = 30
    CORS_ORIGINS: str = "http://localhost:3000"

    # Database - PostgreSQL (production)
    DB_USER: str = "bottrading"
    DB_PASSWORD: str = Field(..., description="Database password")  # Required
    DB_HOST: str = "db"
    DB_PORT: int = 5432
    DB_NAME: str = "bottrading"

    # Redis Cache & Job Queue
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = Field(..., description="Redis password")  # Required
    REDIS_DB: int = 0

    # JWT & Security
    JWT_SECRET: str = Field(..., description="JWT signing secret")  # Required
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    PASSWORD_MIN_LENGTH: int = 12
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_ATTEMPT_WINDOW_MINUTES: int = 15

    # LLM Configuration (Phase 5)
    SELECTED_LLM: str = "mock"  # mock, openai, claude
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-sonnet"

    # Logging & Monitoring
    LOG_FILE: str = "/app/logs/api.log"
    ENABLE_SLOWLOG: bool = True
    SLOW_QUERY_THRESHOLD_MS: int = 1000

    # Backup Configuration
    BACKUP_DIR: str = "/app/backups"
    BACKUP_SCHEDULE: str = "0 2 * * *"  # Daily at 2 AM UTC
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_MIN_COPIES: int = 5

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 1000
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Feature Flags
    ENABLE_LEARNING_AGENT: bool = True
    ENABLE_AUTO_ADAPT: bool = False
    ENABLE_MONITORING: bool = True

    class Config:
        env_file = ".env.production"
        case_sensitive = True

    @property
    def DATABASE_URL(self) -> str:
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Construct async PostgreSQL connection URL"""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def REDIS_URL(self) -> str:
        """Construct Redis connection URL"""
        return (
            f"redis://:{self.REDIS_PASSWORD}@"
            f"{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        )

    @property
    def CELERY_BROKER_URL(self) -> str:
        """Celery broker URL"""
        return self.REDIS_URL

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        """Celery result backend URL"""
        return (
            f"redis://:{self.REDIS_PASSWORD}@"
            f"{self.REDIS_HOST}:{self.REDIS_PORT}/1"
        )

    @validator('ENVIRONMENT')
    def validate_environment(cls, v):
        """Validate environment setting"""
        if v not in ['development', 'staging', 'production']:
            raise ValueError(f"Invalid environment: {v}")
        return v

    @validator('JWT_SECRET')
    def validate_jwt_secret(cls, v, values):
        """Validate JWT secret is secure"""
        if not v or len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    @validator('DB_PASSWORD')
    def validate_db_password(cls, v, values):
        """Validate database password"""
        if not v or len(v) < 12:
            raise ValueError("DB_PASSWORD must be at least 12 characters")
        return v

    def to_dict(self, exclude_secrets: bool = True) -> dict:
        """Convert settings to dictionary"""
        data = self.dict()

        if exclude_secrets:
            # Don't expose sensitive values in logs/API
            secrets = [
                'JWT_SECRET', 'DB_PASSWORD', 'REDIS_PASSWORD',
                'OPENAI_API_KEY', 'CLAUDE_API_KEY'
            ]
            for secret in secrets:
                if secret in data:
                    data[secret] = '***REDACTED***'

        return data


# Load settings from environment
def load_settings() -> Settings:
    """Load settings from environment variables"""
    try:
        settings = Settings()

        # Log loaded settings (without secrets)
        logger.info("Configuration loaded successfully")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        logger.info(f"LLM: {settings.SELECTED_LLM}")

        return settings

    except Exception as e:
        logger.error(f"Failed to load settings: {str(e)}")
        raise


# Global settings instance
settings = load_settings()


# Secrets management (for Docker/Kubernetes)
class SecretsManager:
    """Manage secrets from files or environment"""

    @staticmethod
    def read_secret(secret_name: str, default: Optional[str] = None) -> str:
        """
        Read secret from /run/secrets/{name} (Docker) or environment
        Docker stores secrets in /run/secrets/
        """
        secret_paths = [
            f"/run/secrets/{secret_name}",  # Docker secrets
            f"/var/run/secrets/kubernetes.io/serviceaccount/{secret_name}",  # K8s
        ]

        for path in secret_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        return f.read().strip()
                except IOError:
                    continue

        # Fallback to environment variable
        return os.getenv(secret_name, default)

    @staticmethod
    def validate_secrets() -> bool:
        """Validate all required secrets are available"""
        required_secrets = [
            'JWT_SECRET',
            'DB_PASSWORD',
            'REDIS_PASSWORD'
        ]

        missing = []
        for secret in required_secrets:
            value = SecretsManager.read_secret(secret)
            if not value:
                missing.append(secret)

        if missing:
            logger.error(f"Missing required secrets: {', '.join(missing)}")
            return False

        logger.info("✅ All required secrets validated")
        return True


def get_settings() -> Settings:
    """Get global settings instance"""
    return settings


# Configuration presets for different environments
ENVIRONMENT_CONFIGS = {
    'development': {
        'DEBUG': True,
        'LOG_LEVEL': 'DEBUG',
        'CORS_ORIGINS': 'http://localhost:3000,http://localhost:3001',
        'ENABLE_MONITORING': False,
        'API_WORKERS': 1
    },
    'staging': {
        'DEBUG': False,
        'LOG_LEVEL': 'INFO',
        'CORS_ORIGINS': 'https://staging.bottrading.com',
        'ENABLE_MONITORING': True,
        'API_WORKERS': 2
    },
    'production': {
        'DEBUG': False,
        'LOG_LEVEL': 'INFO',
        'CORS_ORIGINS': 'https://bottrading.com,https://www.bottrading.com',
        'ENABLE_MONITORING': True,
        'ENABLE_AUTO_ADAPT': False,  # Manual approval required
        'API_WORKERS': 4
    }
}
