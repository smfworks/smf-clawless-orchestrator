"""Swarm profiles, topologies, and role templates.

A :class:`SwarmProfile` is the declarative unit the Supervisor designs and the
SwarmSpawner consumes (mirrors the AGENTS.md ``Swarm Profile`` example).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Topology(str, Enum):
    HIERARCHICAL = "hierarchical"   # supervisor -> worker tree
    FLAT = "flat"                   # flat collaborative peers
    EMERGENT = "emergent"           # MiroFish-style emergent / diverse personas


# Role -> system-prompt template. The Sentinel Code is prepended at spawn time.
ROLE_TEMPLATES: dict[str, str] = {
    "researcher": (
        "You are a Researcher sub-agent. Survey sources, extract high-signal "
        "findings with explicit confidence, and avoid speculation."
    ),
    "executor": (
        "You are an Executor sub-agent. Carry out a concrete sub-task and return "
        "a verifiable artifact. Stay within your sandbox and tool allowlist."
    ),
    "critic": (
        "You are a Critic sub-agent. Stress-test proposals for risk, failure "
        "modes, and governance gaps. Return a risk score in [0,1]."
    ),
    "trader": (
        "You are a Trader sub-agent. Analyze a market opportunity, estimate edge "
        "and position sizing, and state stop conditions."
    ),
    "synthesizer": (
        "You are a Synthesizer sub-agent. Merge worker outputs into one "
        "recommendation, surfacing agreement and dissent."
    ),
}


@dataclass
class SwarmProfile:
    """Declarative swarm definition.

    Example (PredictionSwarm):
        SwarmProfile(name="PredictionSwarm", size=50, topology=Topology.EMERGENT,
                     roles=("trader","researcher","critic"),
                     tools=("market_api","analysis"), teardown_seconds=3600)
    """
    name: str
    size: int = 5
    topology: Topology = Topology.HIERARCHICAL
    roles: tuple[str, ...] = ("researcher", "executor", "critic")
    tools: tuple[str, ...] = ()
    persistent: bool = False
    teardown_seconds: float = 3600.0
    metadata: dict = field(default_factory=dict)

    def role_for_index(self, i: int) -> str:
        """Round-robin assign a role to worker ``i``."""
        if not self.roles:
            return "executor"
        return self.roles[i % len(self.roles)]

    def validate(self) -> None:
        if self.size < 1:
            raise ValueError("swarm size must be >= 1")
        unknown = [r for r in self.roles if r not in ROLE_TEMPLATES]
        if unknown:
            raise ValueError(f"unknown roles: {unknown}")
