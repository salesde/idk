"""Deploy manager — deploys sites to Netlify via their API."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Any

import httpx

from core.config import get_settings
from core.message_bus import get_bus

logger = logging.getLogger(__name__)


class NetlifyDeployManager:
    """Deploys static sites to Netlify via the Netlify API."""

    API_BASE = "https://api.netlify.com/api/v1"

    def __init__(self):
        self.settings = get_settings()
        self.bus = get_bus()

    async def deploy_site(self, site_data: dict[str, Any]) -> dict:
        """Deploy a site directory to Netlify."""
        site_dir = site_data.get("site_dir", "")
        site_name = site_data.get("site_name", "ai-company-site")

        if self.settings.dry_run or not self.settings.netlify_auth_token:
            logger.info("[DRY RUN] Would deploy to Netlify: %s", site_name)
            return {
                "success": True,
                "url": f"https://{site_name}.netlify.app",
                "site_id": f"mock_{site_name}",
                "dry_run": True,
            }

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.settings.netlify_auth_token}",
                    "Content-Type": "application/json",
                }

                # Step 1: Create or get site
                sites_response = await client.get(f"{self.API_BASE}/sites", headers=headers)
                sites_response.raise_for_status()
                existing = {s["name"]: s["id"] for s in sites_response.json()}

                if site_name in existing:
                    site_id = existing[site_name]
                    logger.info("Updating existing Netlify site: %s", site_id)
                else:
                    create_response = await client.post(
                        f"{self.API_BASE}/sites",
                        headers=headers,
                        json={"name": site_name},
                    )
                    site_id = create_response.json().get("id", "")
                    logger.info("Created new Netlify site: %s", site_id)

                # Step 2: Zip the site directory
                zip_path = Path(site_dir).parent / f"{site_name}.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for file in Path(site_dir).rglob("*"):
                        if file.is_file():
                            zf.write(file, file.relative_to(site_dir))

                # Step 3: Upload zip
                with open(zip_path, "rb") as f:
                    deploy_response = await client.post(
                        f"{self.API_BASE}/sites/{site_id}/deploys",
                        headers={
                            "Authorization": f"Bearer {self.settings.netlify_auth_token}",
                            "Content-Type": "application/zip",
                        },
                        content=f.read(),
                    )

                deploy_data = deploy_response.json()
                url = deploy_data.get("ssl_url") or deploy_data.get("url", "")

                await self.bus.publish("site_deployed", {"url": url, "site_name": site_name})
                logger.info("Deployed to Netlify: %s", url)

                zip_path.unlink(missing_ok=True)

                return {"success": True, "url": url, "site_id": site_id, "site_name": site_name}

        except Exception as e:
            logger.error("Netlify deployment failed: %s", e)
            return {"success": False, "error": str(e)}
