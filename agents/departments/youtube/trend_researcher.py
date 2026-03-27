"""YouTube trend researcher — finds high-value content opportunities."""

from __future__ import annotations

import logging
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.tools.web_search import multi_search

logger = logging.getLogger(__name__)


class YouTubeTrendResearcher(BaseAgent):
    def __init__(self):
        soul = get_soul("youtube_head")
        soul.name = "Sage-Research"
        super().__init__(soul=soul, model=get_settings().worker_model)
        self.bus = get_bus()

    async def find_video_opportunities(self) -> list[dict[str, Any]]:
        """Find low-competition, high-RPM video topics."""
        await self.emit_thought("Searching for YouTube topics with high RPM and low competition.", self.bus)

        queries = [
            "YouTube faceless channel niche high RPM 2025",
            "AI voiceover YouTube shorts viral topics 2025",
            "YouTube automation channel ideas without showing face",
            "high paying YouTube niches finance health tech 2025",
            "YouTube shorts viral topics this month",
        ]
        results_map = await multi_search(queries, max_results_per_query=4)
        content = "\n\n".join([
            f"[{r.get('title', '')}] {r.get('content', '')[:400]}"
            for results in results_map.values()
            for r in results
        ])

        prompt = f"""
You research YouTube content opportunities for a faceless AI channel.

Research data:
{content[:6000]}

Identify the TOP 8 content opportunities ranked by:
1. Estimated RPM (revenue per 1000 views)
2. Search volume / audience size
3. AI feasibility (can be made without human face or voice)
4. Competition level (prefer low competition)

Respond in JSON:
{{
  "opportunities": [
    {{
      "niche": "Personal Finance Tips",
      "format": "list/educational",
      "estimated_rpm_usd": 12.50,
      "competition": "medium",
      "ai_feasibility": 9,
      "example_titles": ["5 Money Mistakes You're Making in 2025", "How I Saved $10k in 6 Months"],
      "keywords": ["personal finance", "saving money", "budgeting"],
      "shorts_potential": true,
      "longform_potential": true,
      "monthly_audience_estimate": "2M searches"
    }}
  ],
  "top_pick": "niche name",
  "researcher_note": "string"
}}
"""
        response = await self.think(prompt, temperature=0.5)
        data = response.as_json()
        opportunities = data.get("opportunities", [])
        logger.info("Found %d YouTube opportunities", len(opportunities))
        return opportunities
