"""LangGraph state type definitions for the entire agent company."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypedDict


# ── Shared primitives ─────────────────────────────────────────────────────────

@dataclass
class AgentMessage:
    from_agent: str
    to_agent: str
    content: str
    message_type: str = "info"   # info | task | report | alert
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    id: str
    department: str
    task_type: str
    description: str
    priority: int = 5           # 1 (highest) – 10 (lowest)
    status: str = "pending"     # pending | in_progress | completed | failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    output_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Output:
    task_id: str
    department: str
    output_type: str    # script | article | site | product | report
    title: str
    content: str
    file_path: str | None = None
    posted: bool = False
    platform_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RevenueEvent:
    department: str
    event_type: str       # content_posted | product_listed | site_deployed | affiliate_click
    description: str
    estimated_value_usd: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Strategy:
    department: str
    title: str
    summary: str
    tactics: list[str]
    milestones: list[dict[str, Any]]
    estimated_monthly_revenue_usd: float
    confidence: float
    research_sources: list[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


# ── LangGraph TypedDicts ──────────────────────────────────────────────────────

class CompanyState(TypedDict):
    """Top-level company graph state."""
    phase: str                          # startup | research | active | reporting | paused
    goals: list[str]
    active_departments: list[str]
    budget_remaining: float
    messages: list[AgentMessage]
    research_results: dict[str, Strategy]
    revenue_events: list[RevenueEvent]
    cycle_count: int
    last_cycle_at: str | None
    cfo_report: dict[str, Any]


class ResearchState(TypedDict):
    """Per-department research pipeline state."""
    department: str
    soul_key: str
    queries: list[str]
    search_results: list[dict[str, Any]]
    scraped_content: list[str]
    analysis: str
    strategy: dict[str, Any]    # serialized Strategy
    confidence: float
    approved: bool
    error: str | None


class DepartmentState(TypedDict):
    """Per-department execution loop state."""
    department_name: str
    soul_key: str
    task_queue: list[dict[str, Any]]    # serialized Tasks
    current_task: dict[str, Any] | None
    completed_outputs: list[dict[str, Any]]
    revenue_events: list[dict[str, Any]]
    status: str                          # idle | working | blocked | stopped
    cycle_count: int
    strategy: dict[str, Any]
    error: str | None
