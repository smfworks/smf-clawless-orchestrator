"""Swarm Spawning Engine.

Given a :class:`SwarmProfile`, the spawner:
* derives a per-swarm governor (budget caps, allowlist, kill-switch, audit),
* creates an isolated memory subspace + sandbox namespace per swarm,
* clones N role-specialized sub-agents from base templates,
* runs them in parallel (async) with real-time dashboard updates,
* aggregates results, and auto-tears-down ephemeral swarms.

Sandbox note: this reference build isolates via per-swarm namespaces + scoped
governors. Production should back each agent with a Docker/Orgo-style VM; the
``sandbox_factory`` hook lets you inject that without touching orchestration.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from .agent import SubAgent
from .aggregate import Aggregation, aggregate
from .bus import MessageBus
from .governance import (
    Budget,
    GovernancePolicy,
    SwarmGovernor,
    BudgetExceeded,
    SwarmKilled,
)
from .llm import LLMClient
from .memory import MemoryStore
from .observability import Dashboard
from .profiles import SwarmProfile


@dataclass
class SwarmResult:
    swarm_id: str
    profile: SwarmProfile
    aggregation: Aggregation
    governor_snapshot: dict
    torn_down: bool


# A sandbox factory takes (swarm_id, agent_id) and returns a context handle.
SandboxFactory = Callable[[str, str], object]


def _default_sandbox(swarm_id: str, agent_id: str) -> dict:
    """No-op sandbox namespace. Replace with Docker/Orgo VM provisioning."""
    return {"namespace": f"sbx/{swarm_id}/{agent_id}", "isolated": True}


@dataclass
class SwarmSpawner:
    llm: LLMClient
    memory: MemoryStore
    dashboard: Dashboard
    bus: MessageBus = field(default_factory=MessageBus)
    sandbox_factory: SandboxFactory = _default_sandbox

    async def spawn(
        self,
        profile: SwarmProfile,
        task: str,
        budget: Budget | None = None,
        parent_governor: SwarmGovernor | None = None,
    ) -> SwarmResult:
        profile.validate()
        swarm_id = f"sw-{uuid.uuid4().hex[:8]}"

        # Derive governor: nested swarms inherit the parent's kill-switch,
        # audit trail, shared budget and an incremented depth.
        policy = GovernancePolicy(
            allowed_tools=profile.tools,
            human_in_the_loop=profile.metadata.get("human_in_the_loop", False),
        )
        if parent_governor is not None:
            governor = parent_governor.child(policy=policy)
        else:
            governor = SwarmGovernor(budget=budget or Budget(), policy=policy, depth=0)

        # Honor the per-swarm teardown deadline for ephemeral swarms.
        if not profile.persistent:
            governor.budget.max_wall_seconds = min(
                governor.budget.max_wall_seconds, profile.teardown_seconds
            )

        self.dashboard.register(swarm_id, profile.name, profile.size, depth=governor.depth)
        self.dashboard.update(swarm_id, status="running")
        sub_memory = self.memory.subspace(swarm_id)

        # Clone role-specialized agents into isolated namespaces.
        agents: list[SubAgent] = []
        try:
            for i in range(profile.size):
                agent_id = f"{swarm_id}-a{i:03d}"
                governor.register_agent(agent_id)        # enforces max_agents
                self.sandbox_factory(swarm_id, agent_id)  # provision sandbox
                agents.append(
                    SubAgent(
                        agent_id=agent_id,
                        role=profile.role_for_index(i),
                        swarm_id=swarm_id,
                        llm=self.llm,
                        governor=governor,
                        memory=sub_memory,
                        bus=self.bus,
                        dashboard=self.dashboard,
                    )
                )
        except (BudgetExceeded, SwarmKilled) as exc:
            self.dashboard.finish(swarm_id, status="error")
            governor.log(swarm_id, "spawn-abort", str(exc))

        # Run all agents in parallel.
        results = await asyncio.gather(
            *(a.run(task) for a in agents), return_exceptions=True
        )
        messages = [r for r in results if not isinstance(r, Exception)]

        agg = aggregate(messages)
        self.dashboard.update(swarm_id, agents=governor.agents_spawned)

        # Auto-teardown for ephemeral swarms.
        torn_down = False
        if not profile.persistent:
            governor.log(swarm_id, "teardown", "ephemeral auto-teardown")
            torn_down = True
            self.dashboard.finish(swarm_id, status="done")
        else:
            self.dashboard.update(swarm_id, status="running")

        return SwarmResult(
            swarm_id=swarm_id,
            profile=profile,
            aggregation=agg,
            governor_snapshot=governor.snapshot(),
            torn_down=torn_down,
        )
