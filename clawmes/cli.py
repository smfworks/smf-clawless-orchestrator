"""Command-line interface for the Clawmes Orchestrator.

Usage:
    clawmes demo                       # run the bundled end-to-end demo
    clawmes run "<goal>"               # design + spawn a swarm for a goal
    clawmes run "<goal>" --size 50 --topology emergent --max-tokens 80000

If installed via `pip install -e .` the entry point is `clawmes`; otherwise run
`python -m clawmes.cli ...`.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from . import Supervisor, Budget, SwarmProfile
from .profiles import Topology


def _print_outcome(out, dashboard) -> None:
    p = out.profile
    print(f"swarm:        {out.swarm_id}")
    print(f"profile:      {p.name}  size={p.size}  topology={p.topology.value}")
    print(f"agreement:    {out.aggregation.agreement:.2f} "
          f"({out.aggregation.n_ok}/{out.aggregation.n_total} workers ok)")
    print(f"synthesis:    {out.aggregation.summary}")
    print(f"consolidated: promoted {out.consolidation['promoted']} episodic; "
          f"memory={out.consolidation['memory_after']}")
    print("\ndashboard:")
    print(dashboard.render())


def cmd_run(args: argparse.Namespace) -> int:
    sup = Supervisor(default_budget=Budget(
        max_tokens=args.max_tokens, max_agents=args.max_agents
    ))
    # Let the Supervisor design the swarm, then honor explicit overrides.
    profile = sup.design_swarm(args.goal)
    if args.size:
        profile.size = args.size
    if args.topology:
        profile.topology = Topology(args.topology)

    async def _go():
        result = await sup.spawner.spawn(
            profile, task=args.goal, budget=sup.default_budget
        )
        consolidation = sup._consolidate(result.swarm_id)
        from .supervisor import GoalOutcome
        return GoalOutcome(
            goal=args.goal, profile=profile,
            aggregation=result.aggregation,
            consolidation=consolidation, swarm_id=result.swarm_id,
        )

    out = asyncio.run(_go())
    _print_outcome(out, sup.dashboard)
    return 0


def cmd_demo(_args: argparse.Namespace) -> int:
    import runpy
    import os
    demo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "demo.py")
    runpy.run_path(demo, run_name="__main__")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clawmes", description="Clawmes Orchestrator CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("run", help="design + spawn a swarm for a goal")
    pr.add_argument("goal", help="the high-level goal text")
    pr.add_argument("--size", type=int, default=0, help="override swarm size")
    pr.add_argument("--topology", choices=[t.value for t in Topology], default=None,
                    help="override topology")
    pr.add_argument("--max-tokens", type=int, default=50_000, dest="max_tokens",
                    help="per-swarm token budget (default 50000)")
    pr.add_argument("--max-agents", type=int, default=1000, dest="max_agents",
                    help="agent-count cap (default 1000)")
    pr.set_defaults(func=cmd_run)

    pd = sub.add_parser("demo", help="run the bundled end-to-end demo")
    pd.set_defaults(func=cmd_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
