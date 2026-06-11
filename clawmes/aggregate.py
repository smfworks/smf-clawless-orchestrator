"""Result aggregation: synthesis + simple voting/consensus."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .bus import Message


@dataclass
class Aggregation:
    summary: str
    agreement: float          # fraction of successful workers
    dissent: list[str]
    n_total: int
    n_ok: int


def aggregate(messages: list[Message]) -> Aggregation:
    """Combine worker messages into a single recommendation.

    Uses majority success as a consensus proxy and surfaces failures/dissent.
    """
    n_total = len(messages)
    ok = [m for m in messages if m.ok]
    failed = [m for m in messages if not m.ok]
    agreement = (len(ok) / n_total) if n_total else 0.0

    # Lightweight "voting": cluster on role to show contribution balance.
    by_role = Counter(m.role for m in ok)
    role_summary = ", ".join(f"{r}:{c}" for r, c in by_role.most_common())

    headline = ok[0].content if ok else "no successful worker output"
    summary = (
        f"Consensus from {len(ok)}/{n_total} workers ({role_summary}). "
        f"Lead finding: {headline}"
    )
    dissent = [f"{m.sender}({m.role}): {m.content[:120]}" for m in failed]
    return Aggregation(
        summary=summary,
        agreement=agreement,
        dissent=dissent,
        n_total=n_total,
        n_ok=len(ok),
    )
