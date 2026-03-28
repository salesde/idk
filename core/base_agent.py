"""Unified LLM interface supporting both Claude (Anthropic) and Gemini (Google)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import get_settings
from core.soul import AgentSoul

logger = logging.getLogger(__name__)


class LLMResponse:
    def __init__(self, text: str, model: str, usage: dict[str, int] | None = None):
        self.text = text
        self.model = model
        self.usage = usage or {}

    def as_json(self) -> dict[str, Any]:
        try:
            # Try to extract JSON from markdown code blocks first
            text = self.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"raw": self.text}


class BaseAgent:
    """Wraps Claude or Gemini LLM with soul personality and retry logic."""

    def __init__(self, soul: AgentSoul, model: str | None = None):
        self.soul = soul
        self.settings = get_settings()
        requested = model or self.settings.worker_model
        # Auto-fallback: if a Claude model is requested but no API key is set, use Gemini
        if requested.startswith("claude") and not self.settings.anthropic_api_key:
            logger.warning(
                "[%s] Claude model '%s' requested but ANTHROPIC_API_KEY not set — "
                "falling back to %s",
                soul.name, requested, self.settings.executive_model,
            )
            requested = self.settings.executive_model
        self.model = requested
        self._dry_run = self.settings.dry_run

        self._anthropic_client = None
        self._gemini_client = None

    def _is_claude(self) -> bool:
        if not self.model.startswith("claude"):
            return False
        # Don't try Claude if no API key — use Gemini fallback
        if not self.settings.anthropic_api_key:
            self.model = self.settings.executive_model
            return False
        return True

    def _get_anthropic(self):
        if not self.settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Either add it to .env or use a Gemini model instead."
            )
        if self._anthropic_client is None:
            import anthropic
            self._anthropic_client = anthropic.AsyncAnthropic(
                api_key=self.settings.anthropic_api_key
            )
        return self._anthropic_client

    def _get_gemini(self):
        if self._gemini_client is None:
            from google import genai
            self._gemini_client = genai.Client(api_key=self.settings.google_api_key)
        return self._gemini_client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def think(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a prompt to the LLM and get a response."""
        system = self.soul.system_prompt()
        full_prompt = f"{context}\n\n{prompt}" if context else prompt

        if self._dry_run:
            return LLMResponse(
                text=f"[DRY RUN] {self.soul.name} would respond to: {prompt[:100]}...",
                model=self.model,
            )

        self.soul.set_task(prompt[:80])

        if self._is_claude():
            return await self._call_claude(system, full_prompt, temperature, max_tokens)
        else:
            return await self._call_gemini(system, full_prompt, temperature, max_tokens)

    async def _call_claude(
        self, system: str, prompt: str, temperature: float, max_tokens: int
    ) -> LLMResponse:
        client = self._get_anthropic()
        response = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        text = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        logger.debug("[%s/%s] %d in / %d out tokens", self.soul.name, self.model, usage["input_tokens"], usage["output_tokens"])
        return LLMResponse(text=text, model=self.model, usage=usage)

    async def _call_gemini(
        self, system: str, prompt: str, temperature: float, max_tokens: int
    ) -> LLMResponse:
        from google import genai as genai_module
        from google.genai import types as genai_types
        client = self._get_gemini()
        full = f"{system}\n\n{prompt}"
        loop = asyncio.get_event_loop()
        model = self.model

        def _generate(m: str) -> str:
            resp = client.models.generate_content(
                model=m,
                contents=full,
                config=genai_types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            return resp.text

        try:
            text = await loop.run_in_executor(None, lambda: _generate(model))
        except Exception as e:
            # Fall back to gemini-2.0-flash if quota/model error on pro models
            if "ResourceExhausted" in type(e).__name__ or "quota" in str(e).lower() or "429" in str(e):
                logger.warning("[%s] %s quota hit, falling back to gemini-2.0-flash", self.soul.name, model)
                self.model = "gemini-2.0-flash"
                self._gemini_client = None  # reset client so model change takes effect
                text = await loop.run_in_executor(None, lambda: _generate("gemini-2.0-flash"))
            else:
                raise

        logger.debug("[%s/%s] Gemini response received", self.soul.name, self.model)
        return LLMResponse(text=text, model=self.model)

    async def emit_thought(self, thought: str, bus=None) -> None:
        """Emit a visible inner thought to the message bus / dashboard."""
        pulse = self.soul.pulse(thought)
        logger.info("💭 %s: %s", self.soul.name, thought)
        if bus:
            await bus.publish("heartbeat", pulse)
