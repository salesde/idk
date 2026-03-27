"""HTML scraping tool — fetches and cleans web page content."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


async def scrape_url(url: str, timeout: int = 15) -> str:
    """Fetch a URL and return cleaned text content."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # Remove clutter
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]):
                tag.decompose()

            # Extract meaningful text
            main = soup.find("main") or soup.find("article") or soup.body
            if main:
                text = main.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)

            # Collapse whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines)[:8000]   # cap at 8k chars

    except Exception as e:
        logger.warning("Scrape failed for %s: %s", url, e)
        return ""


async def scrape_urls(urls: list[str]) -> list[str]:
    """Scrape multiple URLs concurrently."""
    tasks = [scrape_url(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r if isinstance(r, str) else "" for r in results]


def extract_structured(html: str, selectors: dict[str, str]) -> dict[str, Any]:
    """Extract specific elements using CSS selectors."""
    soup = BeautifulSoup(html, "lxml")
    result = {}
    for key, selector in selectors.items():
        elements = soup.select(selector)
        result[key] = [el.get_text(strip=True) for el in elements]
    return result
