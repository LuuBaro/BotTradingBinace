"""
Configuration management using Pydantic Settings
Loads from environment variables and .env file
"""
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    env: Literal["demo", "live"] = Field(default="demo", description="Trading environment")

    # Database
    db_url: str = Field(
        default="sqlite+aiosqlite:///./data/trading.db",
        description="Async database URL",
    )

    # Mock Exchange (Phase 1)
    mock_initial_balance: float = Field(
        default=10000.0, description="Initial mock balance in USDT"
    )
    initial_account_balance: float = Field(
        default=5000.0, description="Initial account balance for PnL calculation"
    )
    mock_fill_latency_ms: int = Field(
        default=200, description="Mock order fill latency in milliseconds"
    )

    # API Server
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")

    # Worker
    worker_loop_interval_sec: int = Field(
        default=10, description="Worker main loop interval in seconds"
    )
    worker_ai_max_symbols_per_loop: int = Field(
        default=2,
        description="Maximum number of symbols to run full AI analysis per loop",
    )
    worker_ai_min_interval_ms: int = Field(
        default=350,
        description="Minimum delay between consecutive AI calls in milliseconds",
    )
    worker_ai_backoff_base_sec: float = Field(
        default=2.0,
        description="Base cooldown seconds after a 429/rate-limit error",
    )
    worker_ai_backoff_max_sec: float = Field(
        default=60.0,
        description="Maximum cooldown seconds after repeated 429/rate-limit errors",
    )
    worker_ai_prioritize_open_positions: bool = Field(
        default=True,
        description="Prioritize AI analysis for symbols with active positions",
    )

    # 2-Tier LLM Cascade (Scout → Verifier)
    worker_ai_use_two_tier: bool = Field(
        default=False,
        description="Enable 2-tier cascade: scout scans many symbols, verifier processes high-value signals",
    )
    worker_ai_scout_provider: str = Field(
        default="groq",
        description="Scout LLM provider (cheap/fast for scanning)",
    )
    worker_ai_scout_model: str = Field(
        default="llama-3.1-8b-instant",
        description="Scout LLM model",
    )
    worker_ai_verifier_provider: str = Field(
        default="openai",
        description="Verifier LLM provider (accurate for final decisions)",
    )
    worker_ai_verifier_model: str = Field(
        default="gpt-4-turbo",
        description="Verifier LLM model",
    )
    worker_ai_scout_confidence_threshold: float = Field(
        default=0.6,
        description="Minimum scout confidence to trigger verifier (0.0-1.0)",
    )
    
    # Worker AI Mode & Prompt Level (Phase 7+)
    worker_ai_mode: str = Field(
        default="two_tier_hybrid",
        description="AI mode: two_tier_hybrid (2 cloud), two_tier_same (1 local x2), single_tier (1 model)",
    )
    worker_ai_prompt_level: str = Field(
        default="standard",
        description="Prompt level: lightweight (token-saving), standard (balanced), heavyweight (no limit)",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_to_db: bool = Field(default=True, description="Log events to database")

    # Security / JWT (Dashboard Auth)
    jwt_secret: str | None = Field(default=None, description="JWT secret key")

    # Binance API (Phase 2+)
    binance_api_key: str = Field(default="", description="Binance API key")
    binance_api_secret: str = Field(default="", description="Binance API secret")
    binance_testnet: bool = Field(default=True, description="Use Binance testnet")
    binance_base_url: str = Field(
        default="",
        description="Binance Futures base URL (Leave empty to use testnet flag logic)",
    )
    binance_timestamp_offset: int = Field(
        default=0,
        description="Manual timestamp offset in milliseconds (for system clock drift). Set via w32tm /resync when > 1000ms"
    )

    # LLM Providers (Phase 5+)
    selected_llm: str = Field(default="mock", description="Selected LLM provider")
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet", description="Anthropic model")
    groq_api_key: str | None = Field(default=None, description="Groq API key")
    groq_model: str = Field(default="llama-3.1-8b-instant", description="Groq model")
    gemini_api_key: str | None = Field(default=None, description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-1.5-pro", description="Google Gemini model")
    use_local_llm: bool = Field(default=False, description="Use local LLM")
    
    # Custom LLM Provider
    custom_provider_name: str | None = Field(default=None, description="Custom provider name")
    custom_provider_url: str | None = Field(default=None, description="Custom provider API URL")
    custom_provider_key: str | None = Field(default=None, description="Custom provider API key")
    custom_provider_model: str | None = Field(default=None, description="Custom provider model name")

    # Telegram Bot (Phase 3+)
    telegram_bot_token: str = Field(default="", description="Telegram bot token")
    telegram_admin_ids: str = Field(
        default="", description="Comma-separated Telegram admin chat IDs"
    )
    telegram_trader_ids: str = Field(
        default="", description="Comma-separated Telegram trader chat IDs"
    )

    # Google OAuth
    google_client_id: str | None = Field(default=None, description="Google OAuth2 Client ID")

    # Auth / Branding
    app_name: str = Field(default="TiznDBot", description="Application display name")
    frontend_base_url: str = Field(
        default="http://localhost:3000",
        description="Frontend base URL for auth-related links and messaging",
    )

    # Email / SMTP (for OTP + password reset)
    smtp_enabled: bool = Field(default=False, description="Enable SMTP email sending")
    smtp_host: str | None = Field(default=None, description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_username: str | None = Field(default=None, description="SMTP username")
    smtp_password: str | None = Field(default=None, description="SMTP password")
    smtp_from_email: str | None = Field(default=None, description="Sender email address")
    smtp_use_tls: bool = Field(default=True, description="Use STARTTLS for SMTP")

    @property
    def is_demo(self) -> bool:
        """Check if running in demo environment"""
        return self.env == "demo"

    @property
    def is_live(self) -> bool:
        """Check if running in live environment"""
        return self.env == "live"

    @property
    def telegram_admin_list(self) -> list[int]:
        """Get list of admin Telegram chat IDs"""
        if not self.telegram_admin_ids:
            return []
        return [int(cid.strip()) for cid in self.telegram_admin_ids.split(",")]

    @property
    def telegram_trader_list(self) -> list[int]:
        """Get list of trader Telegram chat IDs"""
        if not self.telegram_trader_ids:
            return []
        return [int(cid.strip()) for cid in self.telegram_trader_ids.split(",")]


# Global settings instance
settings = Settings()
