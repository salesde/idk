"""Base department class — shared task queue, execution loop, and reporting."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from core.base_agent import BaseAgent
from core.message_bus import get_bus
from core.state import DepartmentState, Output, RevenueEvent, Task

logger = logging.getLogger(__name__)


class BaseDepartment(ABC):
    """All department heads inherit from this class."""

    def __init__(self, agent: BaseAgent, department_name: str):
        self.agent = agent
        self.department_name = department_name
        self.bus = get_bus()
        self._output_count = 0

    # ── Task management ───────────────────────────────────────────────────────

    def create_task(self, task_type: str, description: str, priority: int = 5, metadata: dict | None = None) -> dict:
        return {
            "id": str(uuid.uuid4())[:8],
            "department": self.department_name,
            "task_type": task_type,
            "description": description,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "output_path": None,
            "metadata": metadata or {},
        }

    def create_revenue_event(self, event_type: str, description: str, value: float = 0.0, metadata: dict | None = None) -> dict:
        return {
            "department": self.department_name,
            "event_type": event_type,
            "description": description,
            "estimated_value_usd": value,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

    # ── Core execution steps (LangGraph nodes) ────────────────────────────────

    async def select_task(self, state: DepartmentState) -> DepartmentState:
        """Pick the next task from the queue or generate a new one."""
        queue = list(state.get("task_queue", []))
        strategy = state.get("strategy", {})

        if not queue:
            # Generate initial task set from strategy
            new_tasks = await self.generate_tasks(strategy)
            queue.extend(new_tasks)
            await self.agent.emit_thought(
                f"No tasks in queue. Generated {len(new_tasks)} new tasks from strategy.", self.bus
            )

        # Pick highest priority pending task
        pending = [t for t in queue if t.get("status") == "pending"]
        if not pending:
            # Reset completed tasks for next cycle
            for t in queue:
                t["status"] = "pending"
            pending = queue

        pending.sort(key=lambda t: t.get("priority", 5))
        current = pending[0]
        current["status"] = "in_progress"

        self.agent.soul.set_task(current["description"])
        logger.info("[%s] Selected task: %s", self.department_name, current["description"][:60])

        return {**state, "current_task": current, "task_queue": queue, "status": "working"}

    async def complete_task(self, state: DepartmentState, output: dict, revenue_value: float = 0.0) -> DepartmentState:
        """Mark current task complete, save output, optionally log revenue."""
        current = state.get("current_task", {})
        if current:
            current["status"] = "completed"
            current["completed_at"] = datetime.utcnow().isoformat()

        outputs = list(state.get("completed_outputs", []))
        outputs.append(output)
        self._output_count += 1

        revenue_events = list(state.get("revenue_events", []))
        if revenue_value > 0:
            event = self.create_revenue_event(
                event_type=output.get("output_type", "content"),
                description=output.get("title", "Output generated"),
                value=revenue_value,
            )
            revenue_events.append(event)
            await self.bus.publish("revenue_event", event)

        await self.bus.publish("output_ready", {
            "department": self.department_name,
            "output": output,
        })

        return {
            **state,
            "current_task": None,
            "completed_outputs": outputs,
            "revenue_events": revenue_events,
            "cycle_count": state.get("cycle_count", 0) + 1,
        }

    @abstractmethod
    async def generate_tasks(self, strategy: dict) -> list[dict]:
        """Generate the initial task queue from a strategy."""
        ...

    @abstractmethod
    async def execute_task(self, state: DepartmentState) -> DepartmentState:
        """Execute the current task and return updated state with output."""
        ...

    @abstractmethod
    async def quality_check(self, output: dict) -> bool:
        """Check if output meets quality standards."""
        ...
