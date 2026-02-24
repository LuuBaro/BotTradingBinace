"""
Structured logging with automatic event storage
"""
import sys
import structlog
from datetime import datetime
from typing import Any
from packages.shared.config import settings


def add_timestamp(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Add timestamp to log event"""
    event_dict["timestamp"] = datetime.utcnow().isoformat()
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
