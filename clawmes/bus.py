"""Communication layer: structured channels + shared result queues.

A lightweight async message bus stands in for ``session_send`` / messaging
gateways. Each swarm has its own results queue; agents publish structured
:class:`Message` objects that the Supervisor (or a synthesis agent) collects.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    sender: str
    role: str
    content: str
    ok: bool = True
    meta: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)


class MessageBus:
    """Per-swarm async queues for result aggregation and inter-agent comms."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[Message]] = {}

    def channel(self, swarm_id: str) -> asyncio.Queue[Message]:
        return self._queues.setdefault(swarm_id, asyncio.Queue())

    async def send(self, swarm_id: str, msg: Message) -> None:
        await self.channel(swarm_id).put(msg)

    async def collect(self, swarm_id: str, expected: int, timeout: float = 60.0) -> list[Message]:
        """Drain ``expected`` messages from a swarm channel (best-effort)."""
        q = self.channel(swarm_id)
        out: list[Message] = []
        deadline = time.monotonic() + timeout
        while len(out) < expected:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                out.append(await asyncio.wait_for(q.get(), timeout=remaining))
            except asyncio.TimeoutError:
                break
        return out
