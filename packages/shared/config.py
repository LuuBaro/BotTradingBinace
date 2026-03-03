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
    api_port: int = Field(default=8001, description="API server port")

    # Worker
    worker_loop_interval_sec: int = Field(
        default=10, description="Worker main loop interval in seconds"
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

    # LLM Providers (Phase 5+)
    selected_llm: str = Field(default="mock", description="Selected LLM provider")
    bot_openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model")
    bot_anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3.5-sonnet", description="Anthropic model")
    bot_gemini_api_key: str | None = Field(default=None, description="Gemini API key")
    gemini_model: str = Field(default="gemini-2.0-flash", description="Gemini model")
    bot_groq_api_key: str | None = Field(default=None, description="Groq API key")
    groq_model: str = Field(default="llama3-70b-8192", description="Groq model")
    use_local_llm: bool = Field(default=False, description="Use local LLM")

    # Telegram Bot (Phase 3+)
    telegram_bot_token: str = Field(default="", description="Telegram bot token")
    telegram_admin_ids: str = Field(
        default="", description="Comma-separated Telegram admin chat IDs"
    )
    telegram_trader_ids: str = Field(
        default="", description="Comma-separated Telegram trader chat IDs"
    )

    # Security / Database (Phase 1 SaaS)
    master_encryption_key: str = Field(
        default="cHOxn73dIyfP4J3z5kHezj7s8irAZE8HEeIGumkwl9M=", 
        description="AES-256 key for sensitive credentials"
    )

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
