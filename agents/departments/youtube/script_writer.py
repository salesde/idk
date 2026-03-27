"""YouTube script writer — Sage produces long-form and Shorts scripts."""

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


class YouTubeScriptWriter(BaseAgent):
    def __init__(self):
        soul = get_soul("youtube_head")
        super().__init__(soul=soul, model=get_settings().worker_model)
        self.bus = get_bus()

    async def write_longform_script(self, topic: dict[str, Any]) -> dict[str, Any]:
        """Write a full long-form YouTube video script (8-15 minutes)."""
        niche = topic.get("niche", "General")
        example_titles = topic.get("example_titles", [])
        keywords = topic.get("keywords", [])

        await self.emit_thought(
            f"Writing long-form script for {niche}. This one needs to be keeper quality.", self.bus
        )
        self.soul.set_mood("focused")

        # First, choose the best title
        title = example_titles[0] if example_titles else f"The Ultimate Guide to {niche}"

        prompt = f"""
Write a complete YouTube video script for a faceless AI channel.

Niche: {niche}
Title: {title}
Target keywords: {', '.join(keywords)}
Target duration: 10-12 minutes (approximately 1500-1800 words of spoken content)
Format: Educational/informational with AI voiceover (no human face)

Structure:
1. Hook (0:00-0:30) — grab attention immediately, tease value
2. Introduction (0:30-1:00) — who this is for, what they'll learn
3. Main content (1:00-9:30) — 5-7 sections with clear value
4. Recap (9:30-10:30) — summarize key points
5. CTA (10:30-11:00) — subscribe, comment, watch next

Requirements:
- Write the FULL spoken narration word for word
- Include [VISUAL: description] tags for B-roll/graphics
- Include [PAUSE] tags for natural breaks
- Optimize for watch time (keep it engaging throughout)
- Include 3 pattern interrupts to prevent drop-off
- End with a cliffhanger or question to boost comments

Respond in JSON:
{{
  "title": "...",
  "description": "Full YouTube description with keywords (300 words)",
  "tags": ["tag1", "tag2"],
  "thumbnail_concept": "Description of thumbnail design",
  "script": "Full script text with [VISUAL] and [PAUSE] tags",
  "duration_estimate": "10:30",
  "sections": [{{"title": "section title", "start_time": "0:00", "word_count": 200}}],
  "seo_keywords": ["kw1", "kw2"]
}}
"""
        response = await self.think(prompt, temperature=0.7, max_tokens=6000)
        script_data = response.as_json()

        file_path = save_content(
            department="youtube",
            content_type="longform_script",
            title=title,
            content=json.dumps(script_data, indent=2),
            metadata={"niche": niche, "type": "longform"},
            extension="json",
        )

        return {
            "output_type": "script",
            "subtype": "longform",
            "title": title,
            "content": script_data.get("script", ""),
            "description": script_data.get("description", ""),
            "tags": script_data.get("tags", []),
            "thumbnail_concept": script_data.get("thumbnail_concept", ""),
            "file_path": str(file_path),
            "platform": "youtube",
            "duration": script_data.get("duration_estimate", "10:00"),
        }

    async def write_shorts_script(self, topic: dict[str, Any]) -> dict[str, Any]:
        """Write a YouTube Shorts script (45-60 seconds)."""
        niche = topic.get("niche", "General")
        await self.emit_thought(f"Shorts script for {niche}. 60 seconds to hook, educate, retain.", self.bus)

        prompt = f"""
Write a YouTube Shorts script (60 seconds max).

Niche: {niche}
Keywords: {', '.join(topic.get('keywords', []))}

Requirements:
- Hook in first 3 words (must stop the scroll)
- Deliver ONE clear, valuable piece of information
- Fast paced — no wasted words
- End with a reason to subscribe or watch more
- Perfect for AI text-to-speech voiceover

Respond in JSON:
{{
  "title": "...",
  "hook": "Opening 3-5 words",
  "script": "Full 60-second script",
  "key_points": ["point1"],
  "call_to_action": "...",
  "thumbnail_text": "Bold text for thumbnail",
  "hashtags": ["#Shorts", "#niche"]
}}
"""
        response = await self.think(prompt, temperature=0.8, max_tokens=1000)
        data = response.as_json()

        file_path = save_content(
            department="youtube",
            content_type="shorts_script",
            title=data.get("title", f"Short — {niche}"),
            content=json.dumps(data, indent=2),
            metadata={"niche": niche, "type": "shorts"},
            extension="json",
        )

        return {
            "output_type": "script",
            "subtype": "shorts",
            "title": data.get("title", "YouTube Short"),
            "content": data.get("script", ""),
            "hook": data.get("hook", ""),
            "thumbnail_text": data.get("thumbnail_text", ""),
            "hashtags": data.get("hashtags", []),
            "file_path": str(file_path),
            "platform": "youtube",
        }
