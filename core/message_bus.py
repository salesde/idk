"""Async in-process pub/sub message bus for inter-agent communication."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class MessageBus:
    """Simple async pub/sub bus. Agents subscribe to topics and publish events."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable[[Any], Awaitable[None]]]] = defaultdict(list)
        self._history: list[dict[str, Any]] = []
        self._max_history = 1000

    def subscribe(self, topic: str, callback: Callable[[Any], Awaitable[None]]) -> None:
        self._subscribers[topic].append(callback)
        logger.debug("Subscribed to topic '%s'", topic)

    def unsubscribe(self, topic: str, callback: Callable[[Any], Awaitable[None]]) -> None:
        if callback in self._subscribers[topic]:
            self._subscribers[topic].remove(callback)

    async def publish(self, topic: str, payload: Any) -> None:
        entry = {"topic": topic, "payload": payload, "timestamp": datetime.utcnow().isoformat()}
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        callbacks = list(self._subscribers.get(topic, []))
        if callbacks:
            await asyncio.gather(*[cb(payload) for cb in callbacks], return_exceptions=True)

    async def send(self, from_agent: str, to_agent: str, content: str, message_type: str = "info", metadata: dict | None = None) -> None:
        from core.state import AgentMessage
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
        )
        logger.info("📨 %s → %s: %s", from_agent, to_agent, content[:120])
        await self.publish(f"agent.{to_agent}", msg)
        await self.publish("agent.all", msg)

    def get_history(self, topic: str | None = None, limit: int = 50) -> list[dict]:
        if topic:
            return [e for e in self._history if e["topic"] == topic][-limit:]
        return self._history[-limit:]


# Global singleton bus
_bus: MessageBus | None = None


def get_bus() -> MessageBus:
    global _bus
    if _bus is None:
        _bus = MessageBus()
    return _bus
