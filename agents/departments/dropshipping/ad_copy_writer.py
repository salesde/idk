"""Ad copy writer — creates UGC-style scripts and product descriptions."""

from __future__ import annotations

import json
import logging
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.tools.file_manager import save_content

logger = logging.getLogger(__name__)


class AdCopyWriter(BaseAgent):
    def __init__(self):
        soul = get_soul("dropship_head")
        super().__init__(soul=soul, model=get_settings().worker_model)
        self.bus = get_bus()

    async def create_ugc_tiktok_script(self, product: dict[str, Any]) -> dict[str, Any]:
        """Write a UGC-style TikTok video script to organically promote the product."""
        await self.emit_thought(
            f"Writing organic TikTok script for {product.get('name', 'product')}. Authentic, not salesy.", self.bus
        )

        prompt = f"""
Write a UGC (User Generated Content) style TikTok organic script for this product.
The video should feel authentic, NOT like an ad.

Product: {product.get('name')}
Category: {product.get('category')}
Target audience: {product.get('target_audience')}
Organic strategy: {product.get('organic_strategy')}
Hook idea: {product.get('tiktok_hook')}
Price: ${product.get('recommended_price_usd', 29.99)}
Wow factor: {product.get('wow_factor')}

Create a script for a 30-45 second TikTok that:
1. Opens with a scroll-stopping hook (NOT "check out this product")
2. Shows problem → product as solution
3. Demonstrates the wow factor visually
4. Subtly reveals price and where to get it
5. Ends with engagement-driving CTA ("comment what color you want")

Respond in JSON:
{{
  "title": "script title",
  "hook": "opening line",
  "script": "full narration",
  "scenes": [
    {{"timestamp": "0:00-0:05", "visual": "...", "narration": "..."}}
  ],
  "caption": "TikTok caption with emojis",
  "hashtags": ["#fyp", "#product"],
  "cta": "...",
  "link_placement": "bio link / TikTok shop"
}}
"""
        response = await self.think(prompt, temperature=0.8)
        data = response.as_json()

        file_path = save_content(
            department="dropshipping",
            content_type="ugc_script",
            title=data.get("title", product.get("name", "product")),
            content=json.dumps(data, indent=2),
            metadata={"product": product.get("name"), "type": "tiktok_ugc"},
            extension="json",
        )

        return {
            "output_type": "ugc_script",
            "product": product.get("name"),
            "title": data.get("title", "TikTok Script"),
            "hook": data.get("hook", ""),
            "content": data.get("script", ""),
            "caption": data.get("caption", ""),
            "hashtags": data.get("hashtags", []),
            "file_path": str(file_path),
        }

    async def write_product_description(self, product: dict[str, Any]) -> str:
        """Write a compelling Shopify product description."""
        prompt = f"""
Write a Shopify product description for:

Product: {product.get('name')}
Category: {product.get('category')}
Target audience: {product.get('target_audience')}
Wow factor: {product.get('wow_factor')}
Price: ${product.get('recommended_price_usd', 29.99)}

Requirements:
- 150-250 words
- Lead with the transformation/benefit, not features
- Include bullet points for key features
- Social proof language ("thousands of customers love this")
- Urgency element
- SEO keyword included naturally
- No fake claims or illegal language

Return as plain text in HTML format (h2, p, ul tags).
"""
        response = await self.think(prompt, temperature=0.7)
        return response.text
