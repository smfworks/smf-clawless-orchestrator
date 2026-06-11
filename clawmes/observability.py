"""Observability: a centralized view of live/finished swarms.

Tracks per-swarm status, token usage, agent counts, and success rates, and
renders a compact text dashboard (stand-in for a web dashboard).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SwarmStat:
    swarm_id: str
    name: str
    size: int
    status: str = "spawning"        # spawning | running | done | killed | error
    tokens: int = 0
    api_calls: int = 0
    agents: int = 0
    ok: int = 0
    failed: int = 0
    depth: int = 0
    started: float = field(default_factory=time.time)
    ended: float | None = None

    @property
    def success_rate(self) -> float:
        done = self.ok + self.failed
        return (self.ok / done) if done else 0.0


class Dashboard:
    """In-memory registry the Supervisor/Spawner update as swarms progress."""

    def __init__(self) -> None:
        self.swarms: dict[str, SwarmStat] = {}

    def register(self, swarm_id: str, name: str, size: int, depth: int = 0) -> SwarmStat:
        st = SwarmStat(swarm_id=swarm_id, name=name, size=size, depth=depth)
        self.swarms[swarm_id] = st
        return st

    def update(self, swarm_id: str, **fields) -> None:
        st = self.swarms.get(swarm_id)
        if not st:
            return
        for k, v in fields.items():
            setattr(st, k, v)

    def finish(self, swarm_id: str, status: str = "done") -> None:
        st = self.swarms.get(swarm_id)
        if st:
            st.status = status
            st.ended = time.time()

    def render(self) -> str:
        if not self.swarms:
            return "(no swarms)"
        rows = [
            f"{'swarm':<18} {'name':<18} {'depth':>5} {'agents':>6} "
            f"{'tok':>7} {'ok':>4} {'fail':>4} {'rate':>5} {'status':<8}"
        ]
        for st in self.swarms.values():
            rows.append(
                f"{st.swarm_id[:18]:<18} {st.name[:18]:<18} {st.depth:>5} "
                f"{st.agents:>6} {st.tokens:>7} {st.ok:>4} {st.failed:>4} "
                f"{st.success_rate:>5.2f} {st.status:<8}"
            )
        return "\n".join(rows)
