"""Strategy Validator — final go/no-go check before department activation."""

from __future__ import annotations

import logging

from core.base_agent import BaseAgent
from core.config import get_settings
from core.message_bus import get_bus
from core.soul import get_soul
from core.state import ResearchState

logger = logging.getLogger(__name__)


class StrategyValidator(BaseAgent):
    def __init__(self):
        soul = get_soul("researcher")
        soul.name = "Iris-Validator"
        settings = get_settings()
        super().__init__(soul=soul, model=settings.research_model)
        self.bus = get_bus()
        self.min_confidence = settings.min_research_confidence

    async def validate(self, state: ResearchState) -> ResearchState:
        """Validate the strategy and assign final confidence score."""
        department = state["department"]
        strategy = state.get("strategy", {})

        await self.emit_thought(
            f"Final validation check for {department}. Is this strategy solid enough to greenlight?", self.bus
        )

        prompt = f"""
You are the final validator before a strategy is approved and resources are committed.

Department: {department}
Strategy: {strategy}

Be skeptical. Challenge assumptions. Validate:
1. Is the revenue potential realistic? (not just optimistic)
2. Are the tactics actually executable by AI agents with web search + content generation?
3. Are there any legal or platform ToS issues?
4. Does this align with an organic, no-paid-ads approach?
5. What is the single biggest risk that could kill this?

Final confidence score: What is the probability (0.0-1.0) this strategy generates meaningful revenue in 90 days?

Respond in JSON:
{{
  "confidence": 0.82,
  "revenue_realistic": true,
  "ai_executable": true,
  "legal_risks": [],
  "biggest_risk": "string",
  "risk_mitigation": "string",
  "approved": true,
  "validator_note": "string",
  "suggested_tweaks": []
}}
"""
        response = await self.think(prompt, temperature=0.3)
        data = response.as_json()

        confidence = float(data.get("confidence", 0.5))
        approved = confidence >= self.min_confidence and data.get("approved", False)

        if approved:
            await self.bus.send(
                "Iris-Validator", "Aiden (CTO)",
                f"Strategy for {department} APPROVED. Confidence: {confidence:.0%}. "
                f"{data.get('validator_note', '')}",
                message_type="report",
            )
            self.soul.set_mood("confident")
            logger.info("Strategy APPROVED for %s: %.0f%% confidence", department, confidence * 100)
        else:
            await self.bus.send(
                "Iris-Validator", "Aiden (CTO)",
                f"Strategy for {department} REJECTED. Confidence only {confidence:.0%}. "
                f"Risk: {data.get('biggest_risk', 'Unknown')}",
                message_type="alert",
            )
            self.soul.set_mood("frustrated")
            logger.warning("Strategy REJECTED for %s: %.0f%% confidence", department, confidence * 100)

        updated_strategy = {
            **strategy,
            "confidence": confidence,
            "approved": approved,
            "legal_risks": data.get("legal_risks", []),
            "biggest_risk": data.get("biggest_risk", ""),
            "risk_mitigation": data.get("risk_mitigation", ""),
            "suggested_tweaks": data.get("suggested_tweaks", []),
            "validator_note": data.get("validator_note", ""),
            "summary": strategy.get("analysis_summary", ""),
        }

        return {
            **state,
            "strategy": updated_strategy,
            "confidence": confidence,
            "approved": approved,
        }
