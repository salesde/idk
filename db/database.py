"""SQLite async database engine and session factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base

logger = logging.getLogger(__name__)

DB_PATH = "output/company.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

_engine = None
_session_factory: async_sessionmaker | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session_factory() -> async_sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables if they don't exist."""
    import os
    os.makedirs("output", exist_ok=True)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized at %s", DB_PATH)


async def save_heartbeat(pulse) -> None:
    """Persist a heartbeat pulse to the DB."""
    from db.models import HeartbeatRecord
    async with get_session() as session:
        record = HeartbeatRecord(
            agent_name=pulse.agent_name,
            role=pulse.role,
            mood=pulse.mood,
            current_task=pulse.current_task,
            inner_thought=pulse.inner_thought,
            timestamp=pulse.timestamp,
        )
        session.add(record)


async def log_revenue_event(event) -> None:
    """Persist a revenue event."""
    from db.models import RevenueRecord
    async with get_session() as session:
        record = RevenueRecord(
            department=event.department,
            event_type=event.event_type,
            description=event.description,
            estimated_value_usd=event.estimated_value_usd,
            metadata=event.metadata,
            timestamp=event.timestamp,
        )
        session.add(record)


async def log_content_item(item_data: dict) -> None:
    """Persist a content item record."""
    from db.models import ContentItem
    async with get_session() as session:
        record = ContentItem(**item_data)
        session.add(record)
