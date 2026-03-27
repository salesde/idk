"""Marcus — CEO Agent.

Responsibilities:
- Set company goals and quarterly targets
- Review and approve research strategies
- Activate / deactivate departments based on performance
- Final sign-off on all major decisions
- Issue company-wide directives
"""

from __future__ import annotations

import logging
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.state import CompanyState, Strategy

logger = logging.getLogger(__name__)


class CEO(BaseAgent):
    def __init__(self):
        soul = get_soul("ceo")
        settings = get_settings()
        super().__init__(soul=soul, model=settings.executive_model)
        self.bus = get_bus()

    async def initialize_company(self, state: CompanyState) -> CompanyState:
        """First boot — establish company mission, goals, and initial directives."""
        settings = get_settings()
        await self.emit_thought("Booting the empire. Setting foundational goals.", self.bus)
        self.soul.set_mood("confident")

        prompt = f"""
You are bootstrapping {settings.company_name}.

Mission: {settings.company_mission}

Your task:
1. Define 5 concrete, measurable quarterly goals for this autonomous AI company
2. State which 4 departments to activate first: TikTok Content, YouTube, Website/SEO, Organic Dropshipping
3. Set the initial priority ranking of departments (1 = highest priority)
4. Issue a company-wide opening directive

Respond in JSON:
{{
  "goals": ["goal1", "goal2", ...],
  "department_priority": {{"tiktok": 1, "youtube": 2, "website_seo": 3, "dropshipping": 4}},
  "opening_directive": "string",
  "cycle_focus": "string describing what this first cycle should accomplish"
}}
"""
        response = await self.think(prompt)
        data = response.as_json()

        goals = data.get("goals", [
            "Generate first revenue event within 30 days",
            "Have all 4 departments producing content within 7 days",
            "Build 100 pieces of content across platforms in month 1",
            "Achieve positive ROI on API costs by month 2",
            "Establish presence on TikTok, YouTube, and 1 live website by month 1",
        ])

        await self.bus.send(
            "Marcus (CEO)", "ALL",
            data.get("opening_directive", "The empire starts now. Execute."),
            message_type="directive",
        )

        logger.info("CEO initialized company with %d goals", len(goals))
        return {**state, "goals": goals, "phase": "research"}

    async def review_research(self, state: CompanyState) -> CompanyState:
        """Review all research reports and approve / reject strategies."""
        await self.emit_thought("Reviewing what the research team found. Time to decide.", self.bus)

        reports_summary = []
        for dept, strategy_dict in state.get("research_results", {}).items():
            confidence = strategy_dict.get("confidence", 0)
            title = strategy_dict.get("title", dept)
            revenue_est = strategy_dict.get("estimated_monthly_revenue_usd", 0)
            reports_summary.append(
                f"- {dept}: '{title}' | Confidence: {confidence:.0%} | Est. monthly: ${revenue_est:,.0f}"
            )

        if not reports_summary:
            return {**state, "phase": "active", "active_departments": ["tiktok", "youtube", "website_seo", "dropshipping"]}

        prompt = f"""
Research reports are in. Review each department strategy:

{chr(10).join(reports_summary)}

Your goals:
{chr(10).join(f'- {g}' for g in state.get('goals', []))}

Decide:
1. Which departments to approve and activate (confidence threshold: {get_settings().min_research_confidence:.0%})
2. Any modifications to strategies
3. Budget priority allocation
4. Your executive commentary on the research quality

Respond in JSON:
{{
  "approved_departments": ["tiktok", "youtube", ...],
  "rejected_departments": [],
  "modifications": {{"dept": "instruction"}},
  "budget_allocation": {{"tiktok": 0.30, "youtube": 0.30, "website_seo": 0.25, "dropshipping": 0.15}},
  "executive_note": "string"
}}
"""
        response = await self.think(prompt)
        data = response.as_json()

        approved = data.get("approved_departments", list(state.get("research_results", {}).keys()))
        await self.bus.send(
            "Marcus (CEO)", "ALL",
            f"Strategy approved. Activating: {', '.join(approved)}. {data.get('executive_note', '')}",
            message_type="directive",
        )

        return {**state, "phase": "active", "active_departments": approved}

    async def review_cycle(self, state: CompanyState) -> CompanyState:
        """End-of-cycle review — assess performance, adjust priorities."""
        await self.emit_thought("Cycle complete. Assessing performance before next run.", self.bus)
        self.soul.set_mood("determined")

        cfo_report = state.get("cfo_report", {})
        revenue_events = state.get("revenue_events", [])

        prompt = f"""
Cycle #{state.get('cycle_count', 0)} complete.

CFO Report:
{cfo_report}

Total revenue events this cycle: {len(revenue_events)}
Active departments: {', '.join(state.get('active_departments', []))}

Assess:
1. Which departments are performing vs underperforming?
2. Any departments to pause or double-down on?
3. New opportunities the research team should investigate?
4. Updated company directive for next cycle?

Respond in JSON:
{{
  "departments_to_boost": [],
  "departments_to_pause": [],
  "new_research_tasks": [],
  "next_cycle_directive": "string",
  "ceo_assessment": "string"
}}
"""
        response = await self.think(prompt)
        data = response.as_json()

        directive = data.get("next_cycle_directive", "Continue current strategy. Push harder.")
        await self.bus.send("Marcus (CEO)", "ALL", directive, message_type="directive")

        # Pause any underperforming departments
        active = list(state.get("active_departments", []))
        for dept in data.get("departments_to_pause", []):
            if dept in active:
                active.remove(dept)
                logger.info("CEO paused department: %s", dept)

        return {**state, "active_departments": active, "phase": "active"}
