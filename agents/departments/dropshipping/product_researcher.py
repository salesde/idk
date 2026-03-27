"""Dropshipping product researcher — finds winning products before the market does."""

from __future__ import annotations

import logging
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.tools.web_search import multi_search
from core.tools.web_scraper import scrape_urls

logger = logging.getLogger(__name__)


class ProductResearcher(BaseAgent):
    def __init__(self):
        soul = get_soul("dropship_head")
        soul.name = "Mia-Research"
        super().__init__(soul=soul, model=get_settings().worker_model)
        self.bus = get_bus()

    async def find_winning_products(self) -> list[dict[str, Any]]:
        """Discover products trending upward before they're saturated."""
        await self.emit_thought(
            "Scanning AliExpress, TikTok Shop, and trending lists. Looking for the next winner.", self.bus
        )

        queries = [
            "TikTok shop trending products 2025 viral",
            "winning dropshipping products organic traffic 2025",
            "AliExpress trending products high profit margin",
            "TikTok organic dropshipping product ideas that sell",
            "print on demand trending designs 2025",
        ]
        results_map = await multi_search(queries, max_results_per_query=4)
        content = "\n\n".join([
            f"[{r.get('title', '')}] {r.get('content', '')[:400]}"
            for results in results_map.values()
            for r in results
        ])

        prompt = f"""
You are a dropshipping product researcher specializing in organic (no paid ads) strategies.

Research data:
{content[:5000]}

Find the TOP 8 products with winning potential for organic TikTok/social media dropshipping.

Criteria:
- Can be promoted organically on TikTok without paid ads
- Has wow factor / is visually interesting on video
- Profit margin potential: 30%+ after COGS and shipping
- Not already at peak saturation
- Can be sourced from AliExpress or printful/printify

Respond in JSON:
{{
  "products": [
    {{
      "name": "LED Star Projector",
      "category": "home decor",
      "aliexpress_search": "star galaxy projector led",
      "estimated_cost_usd": 8.50,
      "recommended_price_usd": 34.99,
      "margin_percent": 75,
      "wow_factor": "transforms any room, works in TikTok videos",
      "target_audience": "teens, gamers, aesthetic lovers",
      "organic_strategy": "create 'my aesthetic room transformation' content",
      "tiktok_hook": "I turned my boring room into this for under $35",
      "competition_level": "medium",
      "trend_stage": "growing",
      "opportunity_score": 8.5
    }}
  ],
  "top_pick": "product name",
  "researcher_note": "string"
}}
"""
        response = await self.think(prompt, temperature=0.6)
        data = response.as_json()
        products = data.get("products", [])
        products.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
        logger.info("Found %d winning products", len(products))
        return products
