"""Store manager — manages Shopify store via Admin API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.config import get_settings
from core.message_bus import get_bus

logger = logging.getLogger(__name__)


class ShopifyStoreManager:
    """Shopify Admin API integration for product and store management."""

    def __init__(self):
        self.settings = get_settings()
        self.bus = get_bus()

    def _api_url(self, path: str) -> str:
        shop = self.settings.shopify_shop_url
        return f"https://{shop}/admin/api/2024-01/{path}"

    def _headers(self) -> dict:
        return {
            "X-Shopify-Access-Token": self.settings.shopify_access_token,
            "Content-Type": "application/json",
        }

    async def create_product(self, product_data: dict[str, Any], description_html: str) -> dict:
        """Create a new product listing in Shopify."""
        if self.settings.dry_run or not self.settings.shopify_access_token:
            logger.info("[DRY RUN] Would create Shopify product: %s", product_data.get("name"))
            return {
                "success": True,
                "product_id": f"mock_{product_data.get('name', 'product').replace(' ', '_')}",
                "url": f"https://{self.settings.shopify_shop_url}/products/mock",
                "dry_run": True,
            }

        try:
            async with httpx.AsyncClient() as client:
                body = {
                    "product": {
                        "title": product_data.get("name"),
                        "body_html": description_html,
                        "vendor": self.settings.company_name,
                        "product_type": product_data.get("category", ""),
                        "tags": product_data.get("target_audience", ""),
                        "variants": [
                            {
                                "price": str(product_data.get("recommended_price_usd", 29.99)),
                                "inventory_management": "shopify",
                                "fulfillment_service": "manual",
                            }
                        ],
                        "status": "active",
                    }
                }
                response = await client.post(
                    self._api_url("products.json"),
                    headers=self._headers(),
                    json=body,
                )
                result = response.json()
                product_id = result.get("product", {}).get("id", "")
                logger.info("Created Shopify product: %s (ID: %s)", product_data.get("name"), product_id)
                return {"success": True, "product_id": str(product_id)}

        except Exception as e:
            logger.error("Shopify product creation failed: %s", e)
            return {"success": False, "error": str(e)}

    async def get_store_metrics(self) -> dict:
        """Fetch basic store analytics."""
        if self.settings.dry_run or not self.settings.shopify_access_token:
            return {"total_products": 0, "dry_run": True}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self._api_url("products/count.json"),
                    headers=self._headers(),
                )
                count = resp.json().get("count", 0)
                return {"total_products": count}
        except Exception as e:
            logger.error("Shopify metrics failed: %s", e)
            return {"error": str(e)}
