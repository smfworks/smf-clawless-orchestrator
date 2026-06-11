"""Hybrid memory layer (Hermes-enhanced) with per-swarm subspaces.

* Parent store keeps a semantic index (mock vector cosine over hashed
  embeddings — swap for a real vector DB) plus curated Markdown docs
  (SOUL/USER/MEMORY style).
* Each swarm gets an isolated subspace under ``/swarms/<uuid>/`` that shares
  read access to parent context but writes its own episodic log.
* After a swarm finishes, :meth:`consolidate` distills the swarm's episodic
  log into durable semantic memory + skill candidates, then can discard the
  raw log to prevent bloat.
"""
from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field


def _embed(text: str, dims: int = 64) -> list[float]:
    """Deterministic mock embedding via hashed n-gram bucketing."""
    vec = [0.0] * dims
    tokens = text.lower().split()
    for tok in tokens:
        h = int(hashlib.sha1(tok.encode("utf-8")).hexdigest(), 16)
        vec[h % dims] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class MemoryRecord:
    text: str
    kind: str = "semantic"          # semantic | episodic | skill
    source: str = "parent"
    ts: float = field(default_factory=time.time)
    vec: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.vec:
            self.vec = _embed(self.text)


class MemoryStore:
    """The shared, durable parent memory."""

    def __init__(self) -> None:
        self.semantic: list[MemoryRecord] = []
        self.skills: list[MemoryRecord] = []
        self.curated: dict[str, str] = {}   # SOUL.md / USER.md / MEMORY.md style
        self._subspaces: dict[str, "SwarmMemory"] = {}

    def add(self, text: str, kind: str = "semantic", source: str = "parent") -> MemoryRecord:
        rec = MemoryRecord(text=text, kind=kind, source=source)
        (self.skills if kind == "skill" else self.semantic).append(rec)
        return rec

    def search(self, query: str, k: int = 5) -> list[MemoryRecord]:
        qv = _embed(query)
        scored = sorted(self.semantic, key=lambda r: _cosine(qv, r.vec), reverse=True)
        return scored[:k]

    def subspace(self, swarm_id: str) -> "SwarmMemory":
        """Return the (cached) isolated subspace for ``swarm_id``.

        Caching ensures the spawner's agents and the Supervisor's
        consolidation operate on the *same* episodic log.
        """
        if swarm_id not in self._subspaces:
            self._subspaces[swarm_id] = SwarmMemory(parent=self, swarm_id=swarm_id)
        return self._subspaces[swarm_id]

    def stats(self) -> dict:
        return {"semantic": len(self.semantic), "skills": len(self.skills)}


class SwarmMemory:
    """Isolated per-swarm subspace: shared parent reads, private episodic writes."""

    def __init__(self, parent: MemoryStore, swarm_id: str) -> None:
        self.parent = parent
        self.swarm_id = swarm_id
        self.path = f"/swarms/{swarm_id}/"
        self.episodic: list[MemoryRecord] = []

    def remember(self, text: str, source: str = "agent") -> MemoryRecord:
        rec = MemoryRecord(text=text, kind="episodic", source=source)
        self.episodic.append(rec)
        return rec

    def context(self, query: str, k: int = 3) -> list[str]:
        """Shared parent context for grounding a sub-agent."""
        return [r.text for r in self.parent.search(query, k=k)]

    def consolidate(self, discard_raw: bool = True) -> dict:
        """Distill episodic log into durable parent memory + a skill candidate.

        Returns a summary of what was promoted. This is the Hermes-style
        autonomous consolidation step run by the Supervisor post-swarm.
        """
        if not self.episodic:
            return {"promoted": 0, "skill": None}

        # Distil: keep the highest-signal episodic entries (longest, here as a
        # stand-in for a real salience/scoring model) and merge into one insight.
        ranked = sorted(self.episodic, key=lambda r: len(r.text), reverse=True)
        top = ranked[: min(3, len(ranked))]
        insight = f"[swarm {self.swarm_id}] " + " | ".join(r.text[:160] for r in top)
        self.parent.add(insight, kind="semantic", source=f"swarm:{self.swarm_id}")

        # Promote a reusable skill template if the swarm converged on a pattern.
        skill_text = (
            f"Skill candidate from swarm {self.swarm_id}: "
            f"pattern reusable across {len(self.episodic)} episodic steps."
        )
        skill = self.parent.add(skill_text, kind="skill", source=f"swarm:{self.swarm_id}")

        promoted = len(self.episodic)
        if discard_raw:
            self.episodic.clear()   # prevent bloat
        return {"promoted": promoted, "skill": skill.text}
