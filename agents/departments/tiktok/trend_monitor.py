"""TikTok trend monitor — discovers what's going viral right now."""

from __future__ import annotations

import logging
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.soul import get_soul
from core.tools.web_search import multi_search

logger = logging.getLogger(__name__)


class TikTokTrendMonitor(BaseAgent):
    def __init__(self):
        soul = get_soul("tiktok_head")
        soul.name = "Kai-Trends"
        super().__init__(soul=soul, model=get_settings().worker_model)

    async def get_trending_topics(self) -> list[dict[str, Any]]:
        """Discover currently trending TikTok topics and formats."""
        await self.emit_thought("Scanning TikTok for what's exploding right now...")

        queries = [
            "trending TikTok hashtags today 2025",
            "viral TikTok video formats this week",
            "TikTok AI character videos trending",
            "most viewed TikTok videos this month",
        ]
        results_map = await multi_search(queries, max_results_per_query=3)

        all_content = "\n\n".join([
            f"[{r.get('title', '')}] {r.get('content', '')[:300]}"
            for results in results_map.values()
            for r in results
        ])

        prompt = f"""
You are the TikTok trend monitor for an AI content company.

Here is the latest data on trending TikTok content:
{all_content[:5000]}

Extract and rank the TOP 10 trending topics/formats right now.
Focus on formats that AI can reproduce at scale (no real human face needed).

Especially look for:
- AI character story videos (fruits, food, animals, objects with personalities)
- Satisfying/ASMR content AI can generate
- Trending audio formats
- Educational/list-style content

Respond in JSON:
{{
  "trending_topics": [
    {{
      "topic": "AI fruit love stories",
      "format": "character drama with narration",
      "viral_potential": 9,
      "ai_feasibility": 10,
      "example_hook": "She was a strawberry. He was a mango. But society said they could never be together...",
      "hashtags": ["#AIstory", "#fruitlove", "#viral"],
      "estimated_views_per_video": "50k-500k"
    }}
  ],
  "top_pick": "string",
  "trend_summary": "string"
}}
"""
        response = await self.think(prompt, temperature=0.8)
        data = response.as_json()
        topics = data.get("trending_topics", [])
        logger.info("Found %d trending TikTok topics", len(topics))
        return topics
