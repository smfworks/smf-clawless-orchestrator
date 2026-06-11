"""Sub-agent: a single spawned worker.

Each sub-agent runs in a scoped context (its system prompt carries the Sentinel
Code + role template), is grounded with shared parent memory, charges its LLM
usage against the swarm governor, screens inputs for injection, and publishes a
structured result to the bus. Agents may request child swarms (recursive
spawning) subject to depth/budget caps enforced by the governor.
"""
from __future__ import annotations

from dataclasses import dataclass

from .bus import Message, MessageBus
from .governance import SwarmGovernor, SENTINEL_CODE, BudgetExceeded, SwarmKilled
from .llm import LLMClient
from .memory import SwarmMemory
from .observability import Dashboard
from .profiles import ROLE_TEMPLATES


@dataclass
class SubAgent:
    agent_id: str
    role: str
    swarm_id: str
    llm: LLMClient
    governor: SwarmGovernor
    memory: SwarmMemory
    bus: MessageBus
    dashboard: Dashboard

    def system_prompt(self) -> str:
        role_tmpl = ROLE_TEMPLATES.get(self.role, "You are a generalist sub-agent.")
        return f"{SENTINEL_CODE}\n\n{role_tmpl}"

    async def run(self, task: str) -> Message:
        try:
            # 1. Injection screen on the inbound task.
            if not self.governor.screen(self.agent_id, task):
                return await self._publish(
                    "rejected: possible prompt injection in task", ok=False
                )

            # 2. Ground with shared parent context (read-only).
            context = self.memory.context(task, k=3)
            grounded = task
            if context:
                grounded = task + "\n\nContext:\n- " + "\n- ".join(context)

            # 3. Reason. Charge tokens against the swarm budget.
            text, usage = self.llm.complete(grounded, system=self.system_prompt())
            self.governor.charge(self.agent_id, usage.total)

            # 4. Screen the output too, then persist to episodic memory.
            if not self.governor.screen(self.agent_id, text):
                return await self._publish("rejected: tainted output", ok=False)
            self.memory.remember(text, source=f"{self.role}:{self.agent_id}")

            # 5. Update observability.
            st = self.dashboard.swarms.get(self.swarm_id)
            if st:
                st.tokens += usage.total
                st.api_calls += 1
                st.ok += 1

            return await self._publish(text, ok=True, tokens=usage.total)

        except (BudgetExceeded, SwarmKilled, PermissionError) as exc:
            st = self.dashboard.swarms.get(self.swarm_id)
            if st:
                st.failed += 1
            return await self._publish(f"halted: {exc}", ok=False)

    async def _publish(self, content: str, ok: bool, tokens: int = 0) -> Message:
        msg = Message(
            sender=self.agent_id,
            role=self.role,
            content=content,
            ok=ok,
            meta={"tokens": tokens, "swarm": self.swarm_id},
        )
        await self.bus.send(self.swarm_id, msg)
        return msg
