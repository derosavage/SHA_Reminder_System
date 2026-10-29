"""
Database Configuration Module
Uses SQLite for zero-install local development (no PostgreSQL needed).
Production: PostgreSQL with asyncpg.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


def normalize_database_url(url: str) -> str:
    """Accept URLs as pasted from Neon/Supabase/Render and make them asyncpg-ready.

    - postgres:// and postgresql:// -> postgresql+asyncpg://
    - sslmode=require  -> ssl=require (asyncpg's spelling)
    - drop libpq-only params asyncpg rejects (channel_binding)
    """
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    if not url.startswith("postgresql+asyncpg://"):
        return url

    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "channel_binding":
            continue
        if key == "sslmode":
            key = "ssl"
        query.append((key, value))
    return urlunsplit(parts._replace(query=urlencode(query)))


# Use SQLite for local dev (no install needed). Set DATABASE_URL=postgresql://...
# (e.g. a Neon connection string) for production.
DATABASE_URL = normalize_database_url(
    os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sha_pay.db")
)

connect_args = {}
engine_kwargs = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}
else:
    # Serverless Postgres (Neon) suspends idle compute: reconnect transparently.
    engine_kwargs = {"pool_pre_ping": True, "pool_recycle": 300}
    if "-pooler" in DATABASE_URL or "pooler.supabase.com" in DATABASE_URL:
        # PgBouncer (transaction mode) can't use prepared-statement caching.
        connect_args = {"statement_cache_size": 0}

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    **engine_kwargs,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency that provides a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def close_db():
    """Close the database connection pool."""
    await engine.dispose()