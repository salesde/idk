"""TikTok posting manager — schedules and uploads content via TikTok API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from core.config import get_settings
from core.message_bus import get_bus

logger = logging.getLogger(__name__)


class TikTokPostingManager:
    """Handles TikTok Content Posting API integration."""

    BASE_URL = "https://open.tiktokapis.com/v2"

    def __init__(self):
        self.settings = get_settings()
        self.bus = get_bus()

    async def post_video(self, script_data: dict[str, Any], video_path: str | None = None) -> dict:
        """
        Post a video to TikTok.

        NOTE: Full video upload requires the TikTok Content Posting API
        (requires app approval from TikTok). This method handles the API call
        structure; actual video file generation requires a video generation service.
        """
        if self.settings.dry_run or not self.settings.tiktok_access_token:
            logger.info("[DRY RUN] Would post TikTok: %s", script_data.get("title", "Unknown"))
            return {
                "success": True,
                "platform_id": f"mock_tiktok_{datetime.utcnow().timestamp():.0f}",
                "dry_run": True,
                "title": script_data.get("title"),
            }

        caption = script_data.get("caption", "")
        hashtags = " ".join(script_data.get("hashtags", []))
        full_caption = f"{caption}\n\n{hashtags}"[:2200]  # TikTok caption limit

        try:
            async with httpx.AsyncClient() as client:
                # Initialize upload
                init_response = await client.post(
                    f"{self.BASE_URL}/post/publish/video/init/",
                    headers={
                        "Authorization": f"Bearer {self.settings.tiktok_access_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "post_info": {
                            "title": full_caption,
                            "privacy_level": "PUBLIC_TO_EVERYONE",
                            "disable_duet": False,
                            "disable_comment": False,
                            "disable_stitch": False,
                        },
                        "source_info": {
                            "source": "PULL_FROM_URL",
                            "video_url": video_path or "",
                        },
                    },
                )
                result = init_response.json()
                publish_id = result.get("data", {}).get("publish_id", "")
                logger.info("TikTok post initiated: %s", publish_id)
                return {"success": True, "platform_id": publish_id, "title": script_data.get("title")}

        except Exception as e:
            logger.error("TikTok post failed: %s", e)
            return {"success": False, "error": str(e)}

    def schedule_posts(self, scripts: list[dict], posts_per_day: int = 3) -> list[dict]:
        """Create a posting schedule for a batch of scripts."""
        schedule = []
        now = datetime.utcnow()
        # Spread posts throughout the day at peak hours (9am, 2pm, 8pm UTC)
        peak_hours = [9, 14, 20]

        for i, script in enumerate(scripts):
            day_offset = i // posts_per_day
            hour = peak_hours[i % len(peak_hours)]
            scheduled_time = (now + timedelta(days=day_offset)).replace(
                hour=hour, minute=0, second=0
            )
            schedule.append({
                "script": script,
                "scheduled_at": scheduled_time.isoformat(),
                "status": "scheduled",
            })

        logger.info("Scheduled %d TikTok posts", len(schedule))
        return schedule
