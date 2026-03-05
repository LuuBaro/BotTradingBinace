"""
Structured logging with automatic event storage
"""
import sys
import structlog
from datetime import datetime
from typing import Any
import re
from packages.shared.config import settings


def redact_sensitive_data(data: str | dict) -> str | dict:
    """
    Redact sensitive information (API keys, tokens, secrets)
    Prevents accidental exposure in logs
    """
    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            if any(
                sensitive in key.lower()
                for sensitive in [
                    'api_key', 'secret', 'token', 'password',
                    'key', 'credential', 'auth', 'jwt'
                ]
            ):
                redacted[key] = '***REDACTED***'
            elif isinstance(value, str):
                redacted[key] = redact_sensitive_data(value)
            else:
                redacted[key] = value
        return redacted
    
    if not isinstance(data, str):
        return data
    
    # Redact common API key patterns
    patterns = [
        (r'sk-proj-[A-Za-z0-9_-]{20,}', '***OPENAI_KEY***'),  # OpenAI
        (r'sk-ant-[A-Za-z0-9_-]{20,}', '***ANTHROPIC_KEY***'),  # Anthropic
        (r'gsk_[A-Za-z0-9_-]{20,}', '***GROQ_KEY***'),  # Groq
        (r'Bearer [A-Za-z0-9_.-]+', '***BEARER_TOKEN***'),
        (r'Authorization: Bearer [A-Za-z0-9_.-]+', '***BEARER_AUTH***'),
        (r'[A-Za-z0-9]{64}(?:[A-Za-z0-9]{64})?', '***API_KEY***'),  # Generic long keys
    ]
    
    redacted = data
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted)
    
    return redacted


def add_timestamp(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Add timestamp to log event and redact sensitive data"""
    event_dict["timestamp"] = datetime.utcnow().isoformat()
    # Redact sensitive keys from all log events
    event_dict = redact_sensitive_data(event_dict)
    return event_dict


def configure_logging() -> None:
    """Configure structlog with appropriate processors"""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            add_timestamp,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionRenderer(),
            structlog.processors.JSONRenderer() if settings.log_level == "DEBUG"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            settings.log_level
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


# Global logger instance
logger = structlog.get_logger()


class DBLogHandler:
    """Handler to log events to database"""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def log_event(
        self,
        level: str,
        code: str,
        message: str,
        trace_id: str | None = None,
        data: dict | None = None,
    ) -> None:
        """Log event to database"""
        if not settings.log_to_db:
            return

        from packages.shared.models import Event

        async with self.session_factory() as session:
            event = Event(
                timestamp=datetime.utcnow(),
                level=level,
                code=code,
                message=message,
                trace_id=trace_id,
                data_json=data,
            )
            session.add(event)
            await session.commit()


# Initialize logging on module import
configure_logging()
