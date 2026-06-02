"""
Database utilities shared across all AURA services.

Provides SQLAlchemy async engine and session factory builders,
plus a common declarative base for ORM models.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy ORM models in AURA."""
    pass


def build_engine(dsn: str):
    """Create an async SQLAlchemy engine.

    Args:
        dsn: PostgreSQL connection string in asyncpg format,
             e.g. ``postgresql+asyncpg://user:pass@host:5432/db``.

    Returns:
        An :class:`AsyncEngine` instance with ``pool_pre_ping`` enabled.
    """
    return create_async_engine(dsn, echo=False, pool_pre_ping=True)


def build_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine.

    Args:
        engine: An :class:`AsyncEngine` returned by :func:`build_engine`.

    Returns:
        An :class:`async_sessionmaker` that produces :class:`AsyncSession`
        instances with ``expire_on_commit=False``.
    """
    return async_sessionmaker(engine, expire_on_commit=False)
