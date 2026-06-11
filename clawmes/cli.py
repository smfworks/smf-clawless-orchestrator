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
from . import config as cfg
from . import onboard as onboard_mod
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


def cmd_onboard(args: argparse.Namespace) -> int:
    if args.provider and args.model:
        summary = onboard_mod.run_noninteractive(
            args.provider, args.model, base_url=args.base_url,
            api_key=args.api_key, use_env_ref=not args.api_key,
        )
        print(f"Configured (non-interactive): model = {summary['model']}")
        print(f"Config written to: {cfg.config_path()}")
        return 0
    onboard_mod.run()
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

    po = sub.add_parser("onboard", help="pick a model provider + model (interactive)")
    po.add_argument("--provider", choices=["ollama", "openrouter", "github",
                                           "openai", "anthropic", "xai",
                                           "vercel-ai-gateway", "custom"],
                    help="non-interactive: provider id")
    po.add_argument("--model", help="non-interactive: model id")
    po.add_argument("--base-url", default=None, help="non-interactive: custom base URL")
    po.add_argument("--api-key", default=None,
                    help="non-interactive: paste key (else an env reference is used)")
    po.set_defaults(func=cmd_onboard)
    return parser


def _maybe_first_run_onboard(command: str) -> None:
    """Offer onboarding on first use when nothing is configured (TTY only)."""
    if command in ("onboard", "demo"):
        return
    if cfg.is_configured() or not sys.stdin.isatty():
        return
    print("No model provider configured yet. Clawmes will run in OFFLINE MOCK mode.")
    ans = input("Run setup now to pick a provider (Ollama/OpenRouter/GitHub/...)? [y/N]: ").strip().lower()
    if ans == "y":
        onboard_mod.run()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _maybe_first_run_onboard(args.command)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
