"""Trend Analyst — scores and ranks opportunities from market research."""

from __future__ import annotations

import logging

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.state import ResearchState

logger = logging.getLogger(__name__)


class TrendAnalyst(BaseAgent):
    def __init__(self):
        soul = get_soul("researcher")
        soul.name = "Iris-Trends"
        settings = get_settings()
        super().__init__(soul=soul, model=settings.research_model)
        self.bus = get_bus()

    async def score_opportunity(self, state: ResearchState) -> ResearchState:
        """Score the research findings and build a ranked strategy."""
        department = state["department"]
        analysis = state.get("analysis", "")
        raw_strategy = state.get("strategy", {})

        await self.emit_thought(
            f"Scoring the {department} opportunity. Let me quantify this properly.", self.bus
        )

        prompt = f"""
You are a trend analyst scoring a business opportunity.

Department: {department}
Market Analysis: {analysis}
Raw Data: {raw_strategy}

Score this opportunity across dimensions and build a 30-day execution strategy.

Respond in JSON:
{{
  "scores": {{
    "market_size": 8,
    "competition_level": 6,
    "barrier_to_entry": 7,
    "revenue_potential": 9,
    "time_to_first_revenue": 8,
    "scalability": 9,
    "ai_leverage_potential": 10
  }},
  "weighted_score": 8.2,
  "30_day_milestones": [
    {{"week": 1, "goal": "...", "metric": "..."}},
    {{"week": 2, "goal": "...", "metric": "..."}},
    {{"week": 3, "goal": "...", "metric": "..."}},
    {{"week": 4, "goal": "...", "metric": "..."}}
  ],
  "tactics": [
    "tactic1",
    "tactic2"
  ],
  "estimated_monthly_revenue_usd": 2500,
  "trend_direction": "rising|stable|declining",
  "saturation_level": "low|medium|high",
  "analyst_note": "string"
}}
"""
        response = await self.think(prompt, temperature=0.4)
        data = response.as_json()

        # Merge into state strategy
        updated_strategy = {
            **raw_strategy,
            "department": department,
            "title": f"{department.replace('_', ' ').title()} Revenue Strategy",
            "scores": data.get("scores", {}),
            "weighted_score": data.get("weighted_score", 7.0),
            "milestones": data.get("30_day_milestones", []),
            "tactics": data.get("tactics", []),
            "estimated_monthly_revenue_usd": data.get("estimated_monthly_revenue_usd", 1000),
            "trend_direction": data.get("trend_direction", "stable"),
            "saturation_level": data.get("saturation_level", "medium"),
            "analyst_note": data.get("analyst_note", ""),
        }

        logger.info(
            "Trend score for %s: %.1f/10 | Est. monthly: $%.0f",
            department,
            data.get("weighted_score", 0),
            data.get("estimated_monthly_revenue_usd", 0),
        )

        return {**state, "strategy": updated_strategy}
