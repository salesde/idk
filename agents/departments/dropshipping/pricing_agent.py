"""Pricing agent — calculates optimal margins and competitive pricing."""

from __future__ import annotations

import logging
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.soul import get_soul

logger = logging.getLogger(__name__)

SHOPIFY_TRANSACTION_FEE = 0.029   # 2.9% + $0.30
SHOPIFY_FIXED_FEE = 0.30
SHIPPING_ESTIMATE = 4.00          # avg ePacket shipping


class PricingAgent(BaseAgent):
    def __init__(self):
        soul = get_soul("dropship_head")
        soul.name = "Mia-Pricing"
        super().__init__(soul=soul, model=get_settings().worker_model)

    def calculate_margins(self, product: dict[str, Any]) -> dict[str, Any]:
        """Calculate real margins accounting for all costs."""
        cogs = float(product.get("estimated_cost_usd", 0))
        selling_price = float(product.get("recommended_price_usd", 0))

        if selling_price == 0:
            return {}

        processing_fee = (selling_price * SHOPIFY_TRANSACTION_FEE) + SHOPIFY_FIXED_FEE
        total_cost = cogs + SHIPPING_ESTIMATE + processing_fee
        gross_profit = selling_price - total_cost
        margin_pct = (gross_profit / selling_price) * 100

        return {
            "cogs_usd": cogs,
            "shipping_usd": SHIPPING_ESTIMATE,
            "processing_fee_usd": round(processing_fee, 2),
            "total_cost_usd": round(total_cost, 2),
            "selling_price_usd": selling_price,
            "gross_profit_usd": round(gross_profit, 2),
            "margin_percent": round(margin_pct, 1),
            "viable": margin_pct >= 30,
        }

    async def optimize_price(self, product: dict[str, Any], competitor_prices: list[float] | None = None) -> dict[str, Any]:
        """Use LLM to find the optimal price point."""
        margins = self.calculate_margins(product)

        prompt = f"""
Optimize the selling price for this dropshipping product.

Product: {product.get('name')}
COGS: ${product.get('estimated_cost_usd', 0)}
Current price: ${product.get('recommended_price_usd', 0)}
Current margin: {margins.get('margin_percent', 0):.1f}%
Competitor prices: {competitor_prices or 'Not available'}
Target audience: {product.get('target_audience', 'general')}

Requirements:
- Minimum 40% margin after all fees
- Price must feel like a good deal to the target audience
- Consider psychological pricing ($X.99)
- Factor in perceived value vs actual cost

Respond in JSON:
{{
  "recommended_price": 34.99,
  "price_rationale": "string",
  "margin_at_price": 45.2,
  "pricing_tier": "value|mid|premium",
  "bundle_opportunity": "optional bundle idea"
}}
"""
        response = await self.think(prompt, temperature=0.3)
        data = response.as_json()
        return {**margins, **data}
