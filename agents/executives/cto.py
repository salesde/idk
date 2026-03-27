"""Aiden — CTO Agent.

Responsibilities:
- Oversee all technical departments (Website/SEO, Dropshipping)
- Dispatch and manage Research agents
- Monitor system health and tool performance
- Technical risk assessment
"""

from __future__ import annotations

import logging

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.state import CompanyState

logger = logging.getLogger(__name__)


class CTO(BaseAgent):
    def __init__(self):
        soul = get_soul("cto")
        settings = get_settings()
        super().__init__(soul=soul, model=settings.executive_model)
        self.bus = get_bus()

    async def dispatch_research(self, state: CompanyState) -> CompanyState:
        """Tell the research department what to investigate for each active or planned department."""
        await self.emit_thought("Dispatching Iris and the research team. Need solid intel before we build.", self.bus)
        self.soul.set_mood("focused")

        departments = ["tiktok", "youtube", "website_seo", "dropshipping"]

        prompt = f"""
You are CTO. You need to brief the research team on what to investigate for each department.

Departments to research: {departments}
Company mission: {get_settings().company_mission}

For each department, write a specific research brief with:
- Key questions to answer
- What metrics determine success
- What competitors/examples to analyze
- What tools/APIs to explore for implementation

Respond in JSON:
{{
  "research_briefs": {{
    "tiktok": {{"focus": "...", "questions": [...], "success_metrics": [...]}},
    "youtube": {{"focus": "...", "questions": [...], "success_metrics": [...]}},
    "website_seo": {{"focus": "...", "questions": [...], "success_metrics": [...]}},
    "dropshipping": {{"focus": "...", "questions": [...], "success_metrics": [...]}}
  }},
  "priority_order": ["tiktok", "youtube", "website_seo", "dropshipping"],
  "cto_note": "string"
}}
"""
        response = await self.think(prompt)
        data = response.as_json()

        briefs = data.get("research_briefs", {})
        await self.bus.send(
            "Aiden (CTO)", "Iris (Researcher)",
            f"Research briefs ready for {len(briefs)} departments. Priorities set. Execute thoroughly.",
            message_type="task",
            metadata={"briefs": briefs},
        )

        logger.info("CTO dispatched research for %d departments", len(briefs))
        return {**state, "phase": "research"}

    async def technical_review(self, department: str, output_summary: str) -> dict:
        """Review technical output quality from a department."""
        await self.emit_thought(f"Reviewing {department} technical output. Does it meet standards?", self.bus)

        prompt = f"""
Technical review for {department} department output:

{output_summary}

Assess:
1. Technical quality (1-10)
2. Implementation completeness
3. Any technical debt or risks
4. Recommended improvements

Respond in JSON:
{{
  "quality_score": 8,
  "complete": true,
  "risks": [],
  "improvements": [],
  "approved": true,
  "cto_note": "string"
}}
"""
        response = await self.think(prompt)
        return response.as_json()
