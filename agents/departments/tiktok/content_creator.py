"""TikTok content creator — Kai generates viral scripts and video prompts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.tools.file_manager import save_content

logger = logging.getLogger(__name__)


class TikTokContentCreator(BaseAgent):
    def __init__(self):
        soul = get_soul("tiktok_head")
        super().__init__(soul=soul, model=get_settings().worker_model)
        self.bus = get_bus()

    async def create_ai_character_story(
        self, topic: dict[str, Any], series_number: int = 1
    ) -> dict[str, Any]:
        """Generate a complete AI character story video script (TikTok format)."""
        await self.emit_thought(
            f"Writing episode {series_number} of the {topic.get('topic', 'AI story')} series. Let's make it hit.", self.bus
        )
        self.soul.set_mood("excited")

        prompt = f"""
Create a VIRAL TikTok video script for this trending format:

Topic: {topic.get('topic', 'AI character story')}
Format: {topic.get('format', 'character drama')}
Example hook: {topic.get('example_hook', '')}
Hashtags: {', '.join(topic.get('hashtags', []))}
Episode: #{series_number}

Requirements:
- Duration: 45-60 seconds (perfect TikTok length)
- Start with a HOOK in the first 2 seconds that stops the scroll
- Use AI-generated characters (fruits, food, objects, or fantasy creatures — no real humans)
- Include narration text (for text-to-speech AI voice)
- Include scene descriptions for AI video generation (what to show visually)
- End with a CLIFFHANGER or call-to-action to follow for part 2
- Use emotional storytelling: love, betrayal, redemption, jealousy, sacrifice
- Keep it dramatic and binge-worthy

Respond in JSON:
{{
  "title": "Episode title",
  "hook": "First 2-second hook line",
  "duration_seconds": 55,
  "characters": [
    {{"name": "Strawberry", "personality": "sweet but insecure", "visual": "bright red strawberry with sad eyes"}}
  ],
  "scenes": [
    {{
      "timestamp": "0:00-0:05",
      "narration": "Text that appears / TTS reads aloud",
      "visual_prompt": "AI image/video generation prompt",
      "background_music": "sad piano / upbeat pop / dramatic strings"
    }}
  ],
  "call_to_action": "string",
  "hashtags": ["#tag1", "#tag2"],
  "caption": "Full TikTok caption with emojis",
  "series_setup": "What happens next (for part 2 teaser)"
}}
"""
        response = await self.think(prompt, temperature=0.9, max_tokens=3000)
        script_data = response.as_json()

        title = script_data.get("title", f"Episode {series_number}")
        file_path = save_content(
            department="tiktok",
            content_type="script",
            title=title,
            content=json.dumps(script_data, indent=2),
            metadata={"topic": topic.get("topic"), "episode": series_number},
            extension="json",
        )

        return {
            "output_type": "script",
            "title": title,
            "content": json.dumps(script_data),
            "file_path": str(file_path),
            "platform": "tiktok",
            "hashtags": script_data.get("hashtags", []),
            "caption": script_data.get("caption", ""),
            "hook": script_data.get("hook", ""),
            "duration": script_data.get("duration_seconds", 55),
        }

    async def create_content_batch(self, strategy: dict, batch_size: int = 5) -> list[dict]:
        """Generate a batch of content pieces based on strategy."""
        await self.emit_thought(f"Generating batch of {batch_size} TikTok scripts. Speed run.", self.bus)

        tactics = strategy.get("tactics", [])
        trending_formats = strategy.get("tiktok_strategy", {}).get("top_formats", ["AI character story"])

        prompt = f"""
Plan a batch of {batch_size} TikTok videos to create right now.

Strategy tactics: {tactics}
Proven formats: {trending_formats}

For each video provide a brief content plan.

Respond in JSON:
{{
  "batch": [
    {{
      "title": "Video title",
      "format": "format type",
      "topic": {{"topic": "...", "format": "...", "hashtags": [], "example_hook": "..."}},
      "priority": 1
    }}
  ]
}}
"""
        response = await self.think(prompt, temperature=0.8)
        data = response.as_json()
        batch_plan = data.get("batch", [])

        outputs = []
        for i, plan in enumerate(batch_plan[:batch_size], 1):
            topic_data = plan.get("topic", {"topic": plan.get("title", "AI story"), "format": "character drama", "hashtags": []})
            output = await self.create_ai_character_story(topic_data, series_number=i)
            outputs.append(output)

        logger.info("Created batch of %d TikTok scripts", len(outputs))
        return outputs
