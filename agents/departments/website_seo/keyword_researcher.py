"""SEO keyword researcher — Rex finds low-competition, high-traffic opportunities."""

from __future__ import annotations

import logging
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.tools.web_search import multi_search

logger = logging.getLogger(__name__)


class KeywordResearcher(BaseAgent):
    def __init__(self):
        soul = get_soul("seo_head")
        soul.name = "Rex-Keywords"
        super().__init__(soul=soul, model=get_settings().worker_model)
        self.bus = get_bus()

    async def find_keyword_opportunities(self, niche: str | None = None) -> list[dict[str, Any]]:
        """Find keyword clusters with high CPC and manageable competition."""
        await self.emit_thought(
            f"Finding keyword gaps in {niche or 'general market'}. Looking for the ones others missed.", self.bus
        )

        queries = [
            f"high CPC keywords {niche or 'best niches'} low competition 2025",
            "programmatic SEO site content ideas low competition",
            f"affiliate marketing keywords {niche or 'high paying'} site 2025",
            "best AdSense niches CPC rates comparison",
        ]
        results_map = await multi_search(queries, max_results_per_query=4)
        content = "\n\n".join([
            f"[{r.get('title', '')}] {r.get('content', '')[:400]}"
            for results in results_map.values()
            for r in results
        ])

        prompt = f"""
You are an SEO expert finding keyword opportunities for programmatic content sites.

Research data:
{content[:5000]}

Find 10 keyword clusters suitable for:
- Programmatic SEO (hundreds of similar pages)
- AdSense monetization (high CPC niches)
- Or affiliate marketing (buyer intent keywords)

Prefer:
- CPC above $2
- Monthly search volume 1k-50k (not saturated by big brands)
- Informational or comparison intent
- AI-writable content

Respond in JSON:
{{
  "keyword_clusters": [
    {{
      "seed_keyword": "best travel insurance",
      "cluster_theme": "travel insurance comparisons",
      "estimated_cpc_usd": 8.50,
      "monthly_searches": 22000,
      "competition": "medium",
      "monetization": "AdSense + affiliate",
      "content_template": "Best [TYPE] Travel Insurance for [DESTINATION/TRIP]",
      "page_count_potential": 200,
      "top_affiliate_programs": ["program1"],
      "opportunity_score": 8.5
    }}
  ],
  "top_pick": "string",
  "researcher_note": "string"
}}
"""
        response = await self.think(prompt, temperature=0.4)
        data = response.as_json()
        clusters = data.get("keyword_clusters", [])
        clusters.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
        logger.info("Found %d keyword clusters", len(clusters))
        return clusters
