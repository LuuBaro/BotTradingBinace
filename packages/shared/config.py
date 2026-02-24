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

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_to_db: bool = Field(default=True, description="Log events to database")

    # Binance API (Phase 2+)
    binance_api_key: str = Field(default="", description="Binance API key")
    binance_api_secret: str = Field(default="", description="Binance API secret")
    binance_testnet: bool = Field(default=True, description="Use Binance testnet")
    binance_base_url: str = Field(
        default="https://testnet.binancefuture.com",
        description="Binance Futures base URL",
    )

    # LLM Providers (Phase 5+)
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    use_local_llm: bool = Field(default=False, description="Use local LLM")

    # Telegram Bot (Phase 3+)
    telegram_bot_token: str = Field(default="", description="Telegram bot token")
    telegram_admin_ids: str = Field(
        default="", description="Comma-separated Telegram admin chat IDs"
    )
    telegram_trader_ids: str = Field(
        default="", description="Comma-separated Telegram trader chat IDs"
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
