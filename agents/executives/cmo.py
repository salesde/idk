"""Zara — CMO Agent.

Responsibilities:
- Content strategy across TikTok and YouTube
- Brand voice and creative direction
- Campaign planning and trend exploitation
- Audience growth strategy
"""

from __future__ import annotations

import logging

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.state import CompanyState

logger = logging.getLogger(__name__)


class CMO(BaseAgent):
    def __init__(self):
        soul = get_soul("cmo")
        settings = get_settings()
        super().__init__(soul=soul, model=settings.executive_model)
        self.bus = get_bus()

    async def set_content_strategy(self, state: CompanyState) -> dict:
        """Define the overall content strategy for all content departments."""
        await self.emit_thought("Time to dominate every feed. Setting the content strategy.", self.bus)
        self.soul.set_mood("excited")

        research = state.get("research_results", {})
        tiktok_strategy = research.get("tiktok", {})
        youtube_strategy = research.get("youtube", {})

        prompt = f"""
You are CMO. Set the content strategy for TikTok and YouTube departments.

TikTok Research Findings: {tiktok_strategy.get('summary', 'No data yet')}
YouTube Research Findings: {youtube_strategy.get('summary', 'No data yet')}

Define:
1. Brand persona and voice across platforms
2. Content pillars (3-5 recurring themes/formats)
3. Posting cadence for each platform
4. Hook formulas that work best for each platform
5. Trending formats to leverage immediately

Respond in JSON:
{{
  "brand_persona": "string",
  "content_pillars": ["pillar1", "pillar2", ...],
  "tiktok_strategy": {{
    "posting_frequency": "X per day",
    "top_formats": [...],
    "hook_templates": [...],
    "trending_themes": [...]
  }},
  "youtube_strategy": {{
    "shorts_frequency": "X per day",
    "longform_frequency": "X per week",
    "top_formats": [...],
    "seo_themes": [...]
  }},
  "cmo_directive": "string"
}}
"""
        response = await self.think(prompt)
        data = response.as_json()

        await self.bus.send(
            "Zara (CMO)", "Kai (TikTok Head)",
            f"Strategy set. Go: {data.get('tiktok_strategy', {}).get('posting_frequency', '3x/day')}. "
            f"Focus on: {', '.join(data.get('tiktok_strategy', {}).get('trending_themes', [])[:3])}",
            message_type="directive",
        )
        await self.bus.send(
            "Zara (CMO)", "Sage (YouTube Head)",
            f"Strategy set. Shorts: {data.get('youtube_strategy', {}).get('shorts_frequency', '2x/day')}. "
            f"Longform: {data.get('youtube_strategy', {}).get('longform_frequency', '3x/week')}.",
            message_type="directive",
        )

        logger.info("CMO content strategy set across %d platforms", 2)
        return data

    async def review_content_performance(self, metrics: dict) -> dict:
        """Analyze content performance and adjust strategy."""
        await self.emit_thought("Looking at the numbers. What's hitting, what's flopping.", self.bus)

        prompt = f"""
Content performance review:

Metrics: {metrics}

Analyze:
1. What content formats are performing best?
2. What should we do more of?
3. What should we stop?
4. Any new trends to chase?

Respond in JSON:
{{
  "top_performers": [],
  "stop_doing": [],
  "increase": [],
  "new_opportunities": [],
  "revised_directive": "string"
}}
"""
        response = await self.think(prompt)
        return response.as_json()
