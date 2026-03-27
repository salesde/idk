"""Nova — CFO Agent.

Responsibilities:
- Track all revenue events and cost estimates
- Produce end-of-cycle financial reports
- Allocate API/tool budgets per department
- Flag departments with negative ROI
- Calculate estimated monthly earnings projections
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.state import CompanyState, RevenueEvent

logger = logging.getLogger(__name__)


class CFO(BaseAgent):
    def __init__(self):
        soul = get_soul("cfo")
        settings = get_settings()
        super().__init__(soul=soul, model=settings.executive_model)
        self.bus = get_bus()
        self._ledger: list[RevenueEvent] = []

    def record_event(self, event: RevenueEvent) -> None:
        self._ledger.append(event)
        logger.info("💰 Revenue event: [%s] %s — $%.2f", event.department, event.event_type, event.estimated_value_usd)

    def total_estimated_revenue(self) -> float:
        return sum(e.estimated_value_usd for e in self._ledger)

    def by_department(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for e in self._ledger:
            result[e.department] = result.get(e.department, 0.0) + e.estimated_value_usd
        return result

    async def produce_report(self, state: CompanyState) -> dict[str, Any]:
        """Synthesize financial data into an executive report."""
        await self.emit_thought("Crunching the numbers. Let's see where we stand.", self.bus)
        self.soul.set_mood("focused")

        events = state.get("revenue_events", []) + [
            {"department": e.department, "event_type": e.event_type,
             "estimated_value_usd": e.estimated_value_usd, "description": e.description}
            for e in self._ledger
        ]

        by_dept: dict[str, dict] = {}
        for e in events:
            dept = e.get("department", "unknown")
            if dept not in by_dept:
                by_dept[dept] = {"total": 0.0, "events": 0}
            by_dept[dept]["total"] += e.get("estimated_value_usd", 0.0)
            by_dept[dept]["events"] += 1

        total = sum(v["total"] for v in by_dept.values())

        prompt = f"""
Produce a CFO financial summary for cycle #{state.get('cycle_count', 0)}.

Revenue by department:
{chr(10).join(f"- {k}: ${v['total']:.2f} ({v['events']} events)" for k, v in by_dept.items())}

Total estimated revenue: ${total:.2f}
Active departments: {', '.join(state.get('active_departments', []))}

Provide:
1. Overall financial health assessment
2. Which departments have best ROI
3. Budget recommendations for next cycle
4. Any cost-cutting opportunities
5. Revenue projections for next 30 days

Respond in JSON:
{{
  "health": "excellent|good|fair|poor",
  "best_roi_departments": [],
  "worst_roi_departments": [],
  "budget_recommendations": {{}},
  "cost_cuts": [],
  "30_day_projection_usd": 0.0,
  "cfo_summary": "string"
}}
"""
        response = await self.think(prompt)
        data = response.as_json()

        report = {
            "cycle": state.get("cycle_count", 0),
            "total_revenue_usd": total,
            "by_department": by_dept,
            "timestamp": datetime.utcnow().isoformat(),
            **data,
        }

        await self.bus.send(
            "Nova (CFO)", "Marcus (CEO)",
            f"Cycle #{report['cycle']} report: ${total:.2f} total | {data.get('health', 'unknown')} health | "
            f"30-day projection: ${data.get('30_day_projection_usd', 0):.0f}",
            message_type="report",
        )

        logger.info("CFO report generated: $%.2f total revenue this cycle", total)
        return report
