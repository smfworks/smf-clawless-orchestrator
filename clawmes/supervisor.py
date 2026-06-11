"""Orchestration Supervisor — the enhanced brain.

Responsibilities:
* decompose a high-level goal,
* design a swarm (size / topology / roles / tools / teardown),
* spawn it via the SwarmSpawner,
* aggregate results (synthesis / voting),
* trigger Hermes-style memory consolidation + skill promotion.

In mock mode the design step uses keyword heuristics; swap :meth:`design_swarm`
for an LLM planning call to make it fully model-driven.
"""
from __future__ import annotations

from dataclasses import dataclass

from .aggregate import Aggregation
from .governance import Budget
from .llm import LLMClient
from .memory import MemoryStore
from .observability import Dashboard
from .profiles import SwarmProfile, Topology
from .spawner import SwarmResult, SwarmSpawner


@dataclass
class GoalOutcome:
    goal: str
    profile: SwarmProfile
    aggregation: Aggregation
    consolidation: dict
    swarm_id: str


class Supervisor:
    def __init__(
        self,
        llm: LLMClient | None = None,
        memory: MemoryStore | None = None,
        dashboard: Dashboard | None = None,
        default_budget: Budget | None = None,
    ) -> None:
        self.llm = llm or LLMClient()
        self.memory = memory or MemoryStore()
        self.dashboard = dashboard or Dashboard()
        self.default_budget = default_budget or Budget()
        self.spawner = SwarmSpawner(
            llm=self.llm, memory=self.memory, dashboard=self.dashboard
        )

    # ------------------------------------------------------------- planning
    def design_swarm(self, goal: str) -> SwarmProfile:
        """Decide swarm parameters from the goal (heuristic in mock mode)."""
        g = goal.lower()
        if any(k in g for k in ("market", "kalshi", "predict", "trade", "arbitrage")):
            return SwarmProfile(
                name="PredictionSwarm",
                size=int(self._scale(g, base=8, big=50)),
                topology=Topology.EMERGENT,
                roles=("trader", "researcher", "critic"),
                tools=("market_api", "analysis"),
                teardown_seconds=3600,
            )
        if any(k in g for k in ("research", "paper", "analy", "survey", "investigate")):
            return SwarmProfile(
                name="ResearchSwarm",
                size=int(self._scale(g, base=5, big=20)),
                topology=Topology.HIERARCHICAL,
                roles=("researcher", "critic", "synthesizer"),
                tools=("web", "analysis"),
                teardown_seconds=1800,
            )
        if any(k in g for k in ("write", "content", "draft", "blog", "debate")):
            return SwarmProfile(
                name="ContentSwarm",
                size=int(self._scale(g, base=4, big=12)),
                topology=Topology.FLAT,
                roles=("researcher", "executor", "critic", "synthesizer"),
                tools=("web",),
                teardown_seconds=1200,
            )
        return SwarmProfile(
            name="GeneralSwarm",
            size=5,
            topology=Topology.HIERARCHICAL,
            roles=("researcher", "executor", "critic"),
            tools=(),
        )

    @staticmethod
    def _scale(goal: str, base: int, big: int) -> int:
        """Crude size signal: bigger swarm for 'large/parallel/high-volume' goals."""
        if any(k in goal for k in ("large", "parallel", "high-volume", "massive", "swarm")):
            return big
        return base

    # ------------------------------------------------------------- execution
    async def run_goal(
        self, goal: str, budget: Budget | None = None
    ) -> GoalOutcome:
        profile = self.design_swarm(goal)
        result: SwarmResult = await self.spawner.spawn(
            profile, task=goal, budget=budget or self.default_budget
        )
        # Hermes-style consolidation: distill the swarm's episodic log into
        # durable memory + a reusable skill candidate.
        consolidation = self._consolidate(result.swarm_id)
        return GoalOutcome(
            goal=goal,
            profile=profile,
            aggregation=result.aggregation,
            consolidation=consolidation,
            swarm_id=result.swarm_id,
        )

    def _consolidate(self, swarm_id: str) -> dict:
        # The spawner's agents wrote episodic records into the cached subspace
        # for this swarm id; consolidate that same instance.
        before = self.memory.stats()
        view = self.memory.subspace(swarm_id)
        summary = view.consolidate()
        summary["memory_before"] = before
        summary["memory_after"] = self.memory.stats()
        return summary
