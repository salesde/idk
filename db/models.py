"""SQLAlchemy ORM models for the AI company database."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer,
    JSON, String, Text, ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class AgentRecord(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    role = Column(String(64), nullable=False)
    model = Column(String(64), nullable=False)
    department = Column(String(64), nullable=True)
    status = Column(String(32), default="idle")   # idle | working | stopped
    mood = Column(String(32), default="focused")
    last_active = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class TaskRecord(Base):
    __tablename__ = "tasks"

    id = Column(String(64), primary_key=True)
    department = Column(String(64), nullable=False)
    task_type = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(Integer, default=5)
    status = Column(String(32), default="pending")
    output_path = Column(String(256), nullable=True)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class MessageRecord(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_agent = Column(String(64), nullable=False)
    to_agent = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(32), default="info")
    extra_data = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)


class RevenueRecord(Base):
    __tablename__ = "revenue_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department = Column(String(64), nullable=False)
    event_type = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    estimated_value_usd = Column(Float, default=0.0)
    extra_data = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department = Column(String(64), nullable=False)
    title = Column(String(256), nullable=False)
    summary = Column(Text, nullable=False)
    strategy_json = Column(JSON, nullable=False)
    confidence = Column(Float, default=0.0)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department = Column(String(64), nullable=False)
    content_type = Column(String(32), nullable=False)   # script | article | site | product
    title = Column(String(256), nullable=False)
    file_path = Column(String(256), nullable=True)
    platform_id = Column(String(128), nullable=True)    # ID on TikTok / YouTube / etc.
    posted = Column(Boolean, default=False)
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class HeartbeatRecord(Base):
    __tablename__ = "heartbeats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(64), nullable=False)
    role = Column(String(64), nullable=False)
    mood = Column(String(32), nullable=False)
    current_task = Column(String(256), nullable=False)
    inner_thought = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
