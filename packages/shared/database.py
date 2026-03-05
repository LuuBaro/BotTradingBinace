"""
Async database connection and session management
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import event
from sqlalchemy.pool import NullPool
from packages.shared.config import settings
from packages.shared.models import Base


# Create async engine
is_sqlite = settings.db_url.startswith("sqlite")
engine_kwargs: dict[str, Any] = {
    "echo": False,  # Set to True for SQL logging
    "pool_pre_ping": True,
}

if is_sqlite:
    engine_kwargs.update(
        {
            "connect_args": {"timeout": 30},
            "poolclass": NullPool,
        }
    )
else:
    engine_kwargs.update(
        {
            "pool_size": 5,
            "max_overflow": 10,
        }
    )

engine = create_async_engine(settings.db_url, **engine_kwargs)

if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:  # type: ignore[unused-function]
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA foreign_keys=ON")
        except sqlite3.OperationalError:
            # Database may be locked during startup; skip PRAGMA and continue
            pass
        finally:
            cursor.close()

# Create async session factory
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def init_db() -> None:
    """Initialize database (create all tables)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """Drop all tables (use with caution!)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session"""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Close database connection pool"""
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI routes"""
    async with AsyncSessionFactory() as session:
        yield session
