"""SEO content writer — generates high-quality, optimized articles at scale."""

from __future__ import annotations

import logging
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.tools.file_manager import save_content

logger = logging.getLogger(__name__)


class SEOContentWriter(BaseAgent):
    def __init__(self):
        soul = get_soul("seo_head")
        super().__init__(soul=soul, model=get_settings().worker_model)
        self.bus = get_bus()

    async def write_article(self, keyword_cluster: dict[str, Any], specific_keyword: str | None = None) -> dict[str, Any]:
        """Write a full SEO-optimized article (1500-2500 words)."""
        seed = specific_keyword or keyword_cluster.get("seed_keyword", "general topic")
        theme = keyword_cluster.get("cluster_theme", seed)
        template = keyword_cluster.get("content_template", "Guide to {seed}")
        title = template.replace("{seed}", seed).replace("[TYPE]", "Best").replace("[DESTINATION/TRIP]", "2025")

        await self.emit_thought(f"Writing SEO article: '{title}'", self.bus)

        prompt = f"""
Write a comprehensive SEO-optimized article.

Target keyword: {seed}
Article title: {title}
Theme: {theme}
Monetization: {keyword_cluster.get('monetization', 'AdSense')}
Affiliate programs: {', '.join(keyword_cluster.get('top_affiliate_programs', []))}

Requirements:
- 1800-2200 words
- Include target keyword in H1, first paragraph, and naturally throughout
- Use H2 and H3 subheadings
- Include a comparison table if relevant
- Include a FAQ section (5-7 questions)
- Natural affiliate link placeholders: [AFFILIATE_LINK: product name]
- AdSense-friendly: informational, original, valuable
- Meta description (155 characters max)
- Opening hook that makes the reader want to read
- Do NOT use fluff — every sentence must add value

Write in markdown format. Include:
1. Meta description
2. Full article in markdown
3. Internal linking suggestions
"""
        response = await self.think(prompt, temperature=0.6, max_tokens=5000)

        article_text = response.text
        # Extract meta description if present
        meta_desc = ""
        if "Meta description:" in article_text:
            lines = article_text.split("\n")
            for line in lines:
                if "Meta description:" in line:
                    meta_desc = line.replace("Meta description:", "").strip()
                    break

        file_path = save_content(
            department="website_seo",
            content_type="article",
            title=title,
            content=article_text,
            metadata={"keyword": seed, "cluster": theme, "meta_desc": meta_desc},
            extension="md",
        )

        logger.info("Article written: %s (%d chars)", title, len(article_text))

        return {
            "output_type": "article",
            "title": title,
            "content": article_text,
            "keyword": seed,
            "meta_description": meta_desc,
            "word_count": len(article_text.split()),
            "file_path": str(file_path),
        }

    async def write_article_batch(self, keyword_cluster: dict, count: int = 5) -> list[dict]:
        """Generate multiple articles from the same keyword cluster."""
        template = keyword_cluster.get("content_template", "{seed}")
        seed = keyword_cluster.get("seed_keyword", "topic")

        # Generate variations
        prompt = f"""
Generate {count} specific article titles/keywords based on:
Seed: {seed}
Template: {template}
Theme: {keyword_cluster.get('cluster_theme', seed)}

Return variations that are all rankable, slightly different, and cover different sub-angles.
JSON: {{"keywords": ["kw1", "kw2", ...]}}
"""
        response = await self.think(prompt, temperature=0.8, max_tokens=500)
        data = response.as_json()
        keywords = data.get("keywords", [seed] * count)[:count]

        articles = []
        for kw in keywords:
            article = await self.write_article(keyword_cluster, specific_keyword=kw)
            articles.append(article)

        logger.info("Wrote batch of %d articles for cluster: %s", len(articles), seed)
        return articles
