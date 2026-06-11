"""Clawmes Orchestrator — a hybrid OpenClaw + Hermes framework with
dynamic sub-agent swarm spawning.

Public surface:
    Supervisor      - the orchestration brain (decompose -> design -> spawn -> aggregate -> learn)
    SwarmSpawner    - the swarm spawning engine
    SwarmProfile    - declarative swarm definition (size/topology/tools/duration/role)
    MemoryStore     - hybrid memory layer with per-swarm subspaces + consolidation
    SwarmGovernor   - budget caps, kill-switch, injection checks, audit trail
    Dashboard       - observability over live swarms
"""
from .supervisor import Supervisor
from .spawner import SwarmSpawner
from .profiles import SwarmProfile, Topology, ROLE_TEMPLATES
from .memory import MemoryStore, SwarmMemory
from .governance import SwarmGovernor, Budget, GovernancePolicy, BudgetExceeded, KillSwitch
from .observability import Dashboard
from .llm import LLMClient

__all__ = [
    "Supervisor",
    "SwarmSpawner",
    "SwarmProfile",
    "Topology",
    "ROLE_TEMPLATES",
    "MemoryStore",
    "SwarmMemory",
    "SwarmGovernor",
    "Budget",
    "GovernancePolicy",
    "BudgetExceeded",
    "KillSwitch",
    "Dashboard",
    "LLMClient",
]

__version__ = "0.1.0"
