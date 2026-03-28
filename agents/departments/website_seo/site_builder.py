"""Site builder — generates complete HTML/CSS static sites ready for deployment."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.tools.file_manager import save_code

logger = logging.getLogger(__name__)


class SiteBuilder(BaseAgent):
    def __init__(self):
        soul = get_soul("seo_head")
        soul.name = "Rex-Builder"
        super().__init__(soul=soul, model=get_settings().worker_model)
        self.bus = get_bus()

    async def build_niche_site(self, keyword_cluster: dict[str, Any], articles: list[dict]) -> dict[str, Any]:
        """Generate a complete static site ready for Netlify deployment."""
        theme = keyword_cluster.get("cluster_theme", "niche site")
        await self.emit_thought(f"Building the {theme} site. Clean, fast, AdSense-ready.", self.bus)

        site_name = theme.lower().replace(" ", "-").replace("/", "-")[:30]

        prompt = f"""
Generate a complete static HTML website for an AdSense/affiliate niche site.

Site theme: {theme}
Target keyword: {keyword_cluster.get('seed_keyword', theme)}
Pages to create: homepage + {len(articles)} article pages
Monetization: {keyword_cluster.get('monetization', 'AdSense + affiliate')}

Generate:
1. index.html — homepage with AdSense placeholders, navigation, featured articles
2. style.css — clean, fast-loading CSS (mobile-first, AdSense-friendly layout)
3. netlify.toml — Netlify config

Requirements:
- Professional, clean design (not spammy)
- Google AdSense placeholder: <!-- ADSENSE_SLOT -->
- Fast loading: minimal JS, optimized CSS
- Mobile responsive
- Include schema markup for articles

Return as JSON with file contents:
{{
  "files": {{
    "index.html": "full HTML",
    "style.css": "full CSS",
    "netlify.toml": "full toml"
  }},
  "site_name": "{site_name}",
  "description": "string"
}}
"""
        response = await self.think(prompt, temperature=0.4, max_tokens=8000)
        data = response.as_json()

        files = data.get("files", {})
        site_dir = Path("output") / "code" / "sites" / site_name
        site_dir.mkdir(parents=True, exist_ok=True)

        created_files = []
        for filename, content in files.items():
            file_path = site_dir / filename
            file_path.write_text(content if isinstance(content, str) else json.dumps(content, indent=2))
            created_files.append(str(file_path))
            logger.info("Created site file: %s", file_path)

        # Generate article pages
        for article in articles[:10]:  # cap at 10 per site build
            article_html = self._article_to_html(article, theme)
            slug = article["title"].lower().replace(" ", "-")[:50]
            article_path = site_dir / f"{slug}.html"
            article_path.write_text(article_html)
            created_files.append(str(article_path))

        logger.info("Built site '%s' with %d files", site_name, len(created_files))

        return {
            "output_type": "site",
            "title": f"{theme} Site",
            "site_name": site_name,
            "site_dir": str(site_dir),
            "files": created_files,
            "description": data.get("description", theme),
            "page_count": len(created_files),
        }

    def _article_to_html(self, article: dict, site_theme: str) -> str:
        """Wrap a markdown article in a basic HTML template."""
        title = article.get("title", "Article")
        content = article.get("content", "")
        meta_desc = article.get("meta_description", "")

        # Basic markdown to HTML conversion (headings and paragraphs)
        html_content = content
        for i in range(6, 0, -1):
            html_content = re.sub(
                rf"^{'#' * i} (.+)$",
                rf"<h{i}>\1</h{i}>",
                html_content,
                flags=re.MULTILINE,
            )
        html_content = re.sub(r"\n\n+", "</p><p>", html_content)
        html_content = f"<p>{html_content}</p>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | {site_theme}</title>
<meta name="description" content="{meta_desc}">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<header><a href="../index.html">{site_theme}</a></header>
<main>
<article>
<h1>{title}</h1>
<!-- ADSENSE_SLOT -->
{html_content}
<!-- ADSENSE_SLOT -->
</article>
</main>
<footer><p>&copy; 2025 {site_theme}</p></footer>
</body>
</html>"""
