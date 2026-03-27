"""Research pipeline graph — runs full market research for one department."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.research.market_researcher import MarketResearcher
from agents.research.strategy_validator import StrategyValidator
from agents.research.trend_analyst import TrendAnalyst
from core.state import ResearchState

logger = logging.getLogger(__name__)


def build_research_graph():
    """Build and compile the research LangGraph for a single department."""

    researcher = MarketResearcher()
    analyst = TrendAnalyst()
    validator = StrategyValidator()

    # ── Node functions ────────────────────────────────────────────────────────

    async def gather_data(state: ResearchState) -> ResearchState:
        """Run web searches and scrape top URLs."""
        logger.info("Research graph: gathering data for %s", state["department"])
        return await researcher.research_department(state)

    async def synthesize(state: ResearchState) -> ResearchState:
        """Analyze gathered data and produce findings."""
        logger.info("Research graph: synthesizing findings for %s", state["department"])
        return await researcher.synthesize_findings(state)

    async def score_trends(state: ResearchState) -> ResearchState:
        """Score opportunity and build execution strategy."""
        logger.info("Research graph: scoring trends for %s", state["department"])
        return await analyst.score_opportunity(state)

    async def validate(state: ResearchState) -> ResearchState:
        """Final validation — approve or reject strategy."""
        logger.info("Research graph: validating strategy for %s", state["department"])
        return await validator.validate(state)

    def should_retry(state: ResearchState) -> str:
        """Route based on validation result."""
        if state.get("approved"):
            return "approved"
        confidence = state.get("confidence", 0)
        if confidence > 0.5:
            return "low_confidence"   # Approved with caveats
        return "rejected"

    # ── Build graph ───────────────────────────────────────────────────────────

    workflow = StateGraph(ResearchState)

    workflow.add_node("gather_data", gather_data)
    workflow.add_node("synthesize", synthesize)
    workflow.add_node("score_trends", score_trends)
    workflow.add_node("validate", validate)

    workflow.add_edge(START, "gather_data")
    workflow.add_edge("gather_data", "synthesize")
    workflow.add_edge("synthesize", "score_trends")
    workflow.add_edge("score_trends", "validate")

    workflow.add_conditional_edges(
        "validate",
        should_retry,
        {
            "approved": END,
            "low_confidence": END,   # Still return result, CEO decides
            "rejected": END,
        },
    )

    return workflow.compile()


async def run_research(department: str) -> dict[str, Any]:
    """Run the full research pipeline for a department and return results."""
    initial_state: ResearchState = {
        "department": department,
        "soul_key": "researcher",
        "queries": [],
        "search_results": [],
        "scraped_content": [],
        "analysis": "",
        "strategy": {},
        "confidence": 0.0,
        "approved": False,
        "error": None,
    }

    graph = build_research_graph()
    try:
        final_state = await graph.ainvoke(initial_state)
        logger.info(
            "Research complete for %s: confidence=%.0f%%, approved=%s",
            department,
            final_state.get("confidence", 0) * 100,
            final_state.get("approved"),
        )
        return final_state
    except Exception as e:
        logger.error("Research failed for %s: %s", department, e)
        return {**initial_state, "error": str(e)}
