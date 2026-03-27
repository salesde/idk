"""Top-level company graph — the master orchestrator of the entire AI company."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from agents.executives.ceo import CEO
from agents.executives.cfo import CFO
from agents.executives.cmo import CMO
from agents.executives.cto import CTO
from core.config import get_settings
from core.message_bus import get_bus
from core.state import CompanyState
from graphs.research_graph import run_research
from graphs.department_graph import run_department_cycle

logger = logging.getLogger(__name__)


def build_company_graph(checkpointer=None):
    """Build and compile the top-level company LangGraph."""

    ceo = CEO()
    cto = CTO()
    cmo = CMO()
    cfo = CFO()
    settings = get_settings()
    bus = get_bus()

    # ── Nodes ─────────────────────────────────────────────────────────────────

    async def startup(state: CompanyState) -> CompanyState:
        """Boot the company: CEO sets goals and mission."""
        logger.info("=== %s STARTING UP ===", settings.company_name)
        await bus.publish("company_event", {"type": "startup", "company": settings.company_name})

        # Start heartbeats for all executives
        for agent in [ceo, cto, cmo, cfo]:
            agent.soul.start_heartbeat(settings.heartbeat_interval)

        return await ceo.initialize_company(state)

    async def dispatch_research(state: CompanyState) -> CompanyState:
        """CTO dispatches research agents for all departments."""
        return await cto.dispatch_research(state)

    async def run_all_research(state: CompanyState) -> CompanyState:
        """Run research for all 4 departments in parallel."""
        departments = ["tiktok", "youtube", "website_seo", "dropshipping"]
        logger.info("Running parallel research for %d departments...", len(departments))

        # Run all research in parallel
        tasks = [run_research(dept) for dept in departments]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        research_results = {}
        for dept, result in zip(departments, results):
            if isinstance(result, Exception):
                logger.error("Research failed for %s: %s", dept, result)
                research_results[dept] = {"department": dept, "confidence": 0.0, "approved": False, "error": str(result)}
            else:
                strategy = result.get("strategy", {})
                strategy["confidence"] = result.get("confidence", 0.0)
                strategy["approved"] = result.get("approved", False)
                strategy["summary"] = result.get("analysis", "")
                research_results[dept] = strategy

        return {**state, "research_results": research_results}

    async def ceo_review_research(state: CompanyState) -> CompanyState:
        """CEO reviews all research and decides which departments to activate."""
        state = await cmo.set_content_strategy(state)
        return await ceo.review_research(state)

    async def run_active_departments(state: CompanyState) -> CompanyState:
        """Run all active departments in parallel for one cycle."""
        active = state.get("active_departments", [])
        research = state.get("research_results", {})

        logger.info("Running %d active departments in parallel: %s", len(active), active)
        await bus.publish("company_event", {"type": "cycle_start", "departments": active})

        tasks = []
        for dept in active:
            strategy = research.get(dept, {})
            tasks.append(run_department_cycle(dept, strategy))

        dept_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate all revenue events
        all_revenue_events = list(state.get("revenue_events", []))
        for dept, result in zip(active, dept_results):
            if isinstance(result, Exception):
                logger.error("Department %s failed: %s", dept, result)
                continue
            dept_events = result.get("revenue_events", [])
            for event in dept_events:
                all_revenue_events.append(event)
                cfo.record_event(type("E", (), event)())  # log to CFO ledger

        return {
            **state,
            "revenue_events": all_revenue_events,
            "cycle_count": state.get("cycle_count", 0) + 1,
        }

    async def cfo_reporting(state: CompanyState) -> CompanyState:
        """CFO produces financial summary for this cycle."""
        report = await cfo.produce_report(state)
        return {**state, "cfo_report": report}

    async def ceo_cycle_review(state: CompanyState) -> CompanyState:
        """CEO reviews cycle results and adjusts strategy."""
        return await ceo.review_cycle(state)

    async def wait_for_next_cycle(state: CompanyState) -> CompanyState:
        """Sleep until the next cycle (respects CYCLE_INTERVAL_MINUTES)."""
        from datetime import datetime
        interval = settings.cycle_interval_minutes * 60
        logger.info("Cycle #%d complete. Waiting %d minutes for next cycle...",
                    state.get("cycle_count", 0), settings.cycle_interval_minutes)
        await bus.publish("company_event", {
            "type": "cycle_complete",
            "cycle": state.get("cycle_count"),
            "revenue_events": len(state.get("revenue_events", [])),
        })
        await asyncio.sleep(interval)
        return {**state, "last_cycle_at": datetime.utcnow().isoformat()}

    def should_continue(state: CompanyState) -> str:
        """Always continue unless paused."""
        if state.get("phase") == "paused":
            return "stop"
        return "continue"

    # ── Build graph ───────────────────────────────────────────────────────────

    workflow = StateGraph(CompanyState)

    workflow.add_node("startup", startup)
    workflow.add_node("dispatch_research", dispatch_research)
    workflow.add_node("run_all_research", run_all_research)
    workflow.add_node("ceo_review_research", ceo_review_research)
    workflow.add_node("run_active_departments", run_active_departments)
    workflow.add_node("cfo_reporting", cfo_reporting)
    workflow.add_node("ceo_cycle_review", ceo_cycle_review)
    workflow.add_node("wait_for_next_cycle", wait_for_next_cycle)

    workflow.add_edge(START, "startup")
    workflow.add_edge("startup", "dispatch_research")
    workflow.add_edge("dispatch_research", "run_all_research")
    workflow.add_edge("run_all_research", "ceo_review_research")
    workflow.add_edge("ceo_review_research", "run_active_departments")
    workflow.add_edge("run_active_departments", "cfo_reporting")
    workflow.add_edge("cfo_reporting", "ceo_cycle_review")
    workflow.add_edge("ceo_cycle_review", "wait_for_next_cycle")

    workflow.add_conditional_edges(
        "wait_for_next_cycle",
        should_continue,
        {
            "continue": "run_active_departments",
            "stop": END,
        },
    )

    return workflow.compile(checkpointer=checkpointer)


async def run_company(dry_run: bool = False) -> None:
    """Bootstrap and run the company indefinitely."""
    import os
    from core.config import get_settings

    settings = get_settings()
    if dry_run:
        os.environ["DRY_RUN"] = "true"

    # Initialize DB
    from db.database import init_db
    await init_db()

    # Set up SQLite checkpointer for graph state persistence
    async with AsyncSqliteSaver.from_conn_string("output/company_state.db") as checkpointer:
        graph = build_company_graph(checkpointer=checkpointer)

        initial_state: CompanyState = {
            "phase": "startup",
            "goals": [],
            "active_departments": [],
            "budget_remaining": 1000.0,
            "messages": [],
            "research_results": {},
            "revenue_events": [],
            "cycle_count": 0,
            "last_cycle_at": None,
            "cfo_report": {},
        }

        config = {"configurable": {"thread_id": "main_company"}}

        logger.info("Launching %s...", settings.company_name)
        async for event in graph.astream(initial_state, config=config):
            node_name = list(event.keys())[0]
            logger.debug("Graph node completed: %s", node_name)
