"""Tavily web search tool for research agents."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import get_settings

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def web_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",   # "basic" | "advanced"
    include_answer: bool = True,
) -> list[dict[str, Any]]:
    """Search the web using Tavily and return structured results."""
    settings = get_settings()

    if settings.dry_run or not settings.tavily_api_key:
        logger.info("[DRY RUN] Search: %s", query)
        return [
            {
                "title": f"Mock result for: {query}",
                "url": "https://example.com/mock",
                "content": f"This is a mock search result for the query: {query}. "
                           "In production this would contain real web content.",
                "score": 0.9,
            }
        ]

    try:
        from tavily import AsyncTavilyClient
        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        response = await client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=include_answer,
        )
        results = response.get("results", [])
        logger.info("Search '%s' → %d results", query, len(results))
        return results
    except Exception as e:
        logger.error("Search failed for '%s': %s", query, e)
        raise


async def multi_search(
    queries: list[str],
    max_results_per_query: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    """Run multiple searches in parallel and return results keyed by query."""
    tasks = {q: web_search(q, max_results=max_results_per_query) for q in queries}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    return {
        q: (r if not isinstance(r, Exception) else [])
        for q, r in zip(tasks.keys(), results)
    }
