"""Database utilities shared across all AURA services.

Provides SQLAlchemy async engine and session factory builders,
plus a common declarative base for ORM models.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy ORM models in AURA."""
    pass

def build_engine(dsn: str) -> AsyncEngine:
    """Creates an async SQLAlchemy engine.

    Args:
        dsn: PostgreSQL connection string in asyncpg format,
             e.g. ``postgresql+asyncpg://user:pass@host:5432/db``.

    Returns:
        An AsyncEngine instance with pool_pre_ping enabled.
    """
    return create_async_engine(dsn, echo=False, pool_pre_ping=True)

def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Creates an async session factory bound to the given engine.

    Args:
        engine: An AsyncEngine returned by build_engine.

    Returns:
        An async_sessionmaker that produces AsyncSession instances.
    """
    return async_sessionmaker(engine, expire_on_commit=False)
