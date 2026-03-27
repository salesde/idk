"""Iris — Market Researcher Agent.

Conducts deep web research to discover revenue opportunities for each department.
Uses Gemini 2.5 Pro for thorough analysis and Tavily for web search.
"""

from __future__ import annotations

import logging
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.state import ResearchState
from core.tools.web_search import multi_search, web_search
from core.tools.web_scraper import scrape_urls

logger = logging.getLogger(__name__)

DEPARTMENT_CONTEXTS = {
    "tiktok": {
        "focus": "viral TikTok content creation and monetization",
        "base_queries": [
            "viral TikTok AI generated content 2025 trending formats",
            "TikTok AI fruit characters love story viral videos monetization",
            "best TikTok niches for views and revenue 2025",
            "TikTok creator fund RPM rates 2025",
            "faceless TikTok channel revenue strategies",
        ],
    },
    "youtube": {
        "focus": "YouTube channel growth and monetization through AI content",
        "base_queries": [
            "best AI generated YouTube content ideas 2025",
            "faceless YouTube channel niches high RPM 2025",
            "YouTube shorts monetization strategy 2025",
            "AI voiceover YouTube channel revenue examples",
            "YouTube automation channel best niches earnings",
        ],
    },
    "website_seo": {
        "focus": "programmatic SEO and niche content site monetization",
        "base_queries": [
            "programmatic SEO content site revenue 2025",
            "best AdSense niches high CPC 2025",
            "affiliate marketing niche site income 2025",
            "AI content website monetization strategies",
            "niche site flipping income potential",
        ],
    },
    "dropshipping": {
        "focus": "organic dropshipping without paid ads",
        "base_queries": [
            "organic TikTok dropshipping winning products 2025",
            "dropshipping without paid ads strategy 2025",
            "TikTok shop best selling products",
            "AliExpress trending products 2025",
            "print on demand vs dropshipping profitability",
        ],
    },
}


class MarketResearcher(BaseAgent):
    def __init__(self):
        soul = get_soul("researcher")
        settings = get_settings()
        super().__init__(soul=soul, model=settings.research_model)
        self.bus = get_bus()

    async def research_department(self, state: ResearchState) -> ResearchState:
        """Full research pipeline for one department."""
        department = state["department"]
        await self.emit_thought(
            f"Starting deep research on {department}. Going down every rabbit hole.", self.bus
        )
        self.soul.set_mood("curious")

        ctx = DEPARTMENT_CONTEXTS.get(department, {})
        base_queries = ctx.get("base_queries", [f"{department} revenue strategies 2025"])

        # Step 1: Generate additional targeted queries via LLM
        refined = await self._generate_queries(department, base_queries, ctx.get("focus", ""))
        all_queries = list(set(base_queries + refined))[:8]

        await self.emit_thought(f"Running {len(all_queries)} search queries for {department}...", self.bus)

        # Step 2: Run all searches
        search_results_map = await multi_search(all_queries, max_results_per_query=4)
        all_results = []
        top_urls = []
        for query, results in search_results_map.items():
            for r in results:
                all_results.append(r)
                if r.get("url"):
                    top_urls.append(r["url"])

        # Step 3: Scrape top URLs for deeper content
        await self.emit_thought(f"Scraping top {min(6, len(top_urls))} pages for in-depth data...", self.bus)
        scraped = await scrape_urls(top_urls[:6])
        scraped_content = [s for s in scraped if s]

        return {
            **state,
            "queries": all_queries,
            "search_results": all_results,
            "scraped_content": scraped_content,
        }

    async def _generate_queries(self, department: str, base_queries: list[str], focus: str) -> list[str]:
        """Use LLM to generate additional precise search queries."""
        prompt = f"""
You are researching {department} ({focus}) to build an autonomous revenue strategy.

Existing queries: {base_queries}

Generate 4 additional HIGHLY SPECIFIC search queries that would uncover:
- Exact revenue figures and case studies
- Specific tools and methods used by top performers
- Common mistakes to avoid
- Emerging trends not yet saturated

Return as JSON: {{"queries": ["query1", "query2", ...]}}
"""
        response = await self.think(prompt, temperature=0.8)
        data = response.as_json()
        return data.get("queries", [])

    async def synthesize_findings(self, state: ResearchState) -> ResearchState:
        """Analyze all gathered data and produce findings report."""
        department = state["department"]
        await self.emit_thought(f"Synthesizing everything I found on {department}. This is where it gets interesting.", self.bus)
        self.soul.set_mood("excited")

        search_snippets = "\n\n".join([
            f"[{r.get('title', 'Unknown')}]\n{r.get('content', '')[:500]}"
            for r in state.get("search_results", [])[:10]
        ])

        scraped_summary = "\n\n---\n\n".join(state.get("scraped_content", [])[:3])

        prompt = f"""
Analyze all research for the {department} department.

SEARCH RESULTS:
{search_snippets}

SCRAPED CONTENT:
{scraped_summary[:4000]}

Produce a comprehensive analysis including:
1. Market opportunity size and viability
2. Proven revenue generation methods in this space
3. Estimated monthly revenue for a new entrant (realistic, conservative, optimistic)
4. Key success factors
5. Major risks and how to mitigate them
6. Top 3 competitors/examples to model after
7. Specific action items to get started immediately

Be specific with numbers, timeframes, and methods. This analysis will drive real business decisions.

Respond in JSON:
{{
  "opportunity_score": 8.5,
  "market_size": "string",
  "revenue_methods": ["method1", ...],
  "revenue_estimates": {{
    "conservative_monthly": 500,
    "realistic_monthly": 2000,
    "optimistic_monthly": 8000
  }},
  "success_factors": ["factor1", ...],
  "risks": [{{"risk": "...", "mitigation": "..."}}],
  "competitors": [{{"name": "...", "url": "...", "revenue": "..."}}],
  "immediate_actions": ["action1", ...],
  "analysis_summary": "string"
}}
"""
        response = await self.think(prompt, temperature=0.5, max_tokens=6000)
        analysis_data = response.as_json()

        # Format human-readable summary
        summary = analysis_data.get("analysis_summary", "Research complete.")

        return {
            **state,
            "analysis": summary,
            "strategy": {
                **analysis_data,
                "department": department,
            }
        }
