"""Clawmes TUI — a stdlib, dependency-free interactive terminal UI.

Launch with ``clawmes tui``. Keeps one Supervisor for the whole session so the
observability dashboard and consolidated memory accumulate across runs.
"""
from __future__ import annotations

import asyncio
import os
import sys

from . import Supervisor, Budget
from . import config as cfg
from . import onboard as onboard_mod
from .profiles import Topology
from .supervisor import GoalOutcome


def _color(s: str, code: str) -> str:
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return s
    return f"\033[{code}m{s}\033[0m"


def _bold(s: str) -> str: return _color(s, "1")
def _cyan(s: str) -> str: return _color(s, "36")
def _green(s: str) -> str: return _color(s, "32")
def _yellow(s: str) -> str: return _color(s, "33")
def _dim(s: str) -> str: return _color(s, "2")


def _clear() -> None:
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def _provider_line() -> str:
    model = cfg.get_default_model()
    if model:
        return _green(f"provider: {model}")
    return _yellow("provider: not configured (OFFLINE MOCK mode)")


MENU = [
    ("Run a goal (design + spawn a swarm)", "run"),
    ("Show observability dashboard", "dashboard"),
    ("View consolidated memory + skills", "memory"),
    ("Configure model provider (onboard)", "onboard"),
    ("Quit", "quit"),
]


def render_menu() -> str:
    lines = [_bold("Clawmes Orchestrator — swarm spawning"), _provider_line(), ""]
    for i, (label, _key) in enumerate(MENU, 1):
        lines.append(f"  {_cyan(str(i))}. {label}")
    return "\n".join(lines)


def _pause() -> None:
    input(_dim("\n[enter] to continue "))


def _do_run(sup: Supervisor) -> None:
    goal = input("\nEnter goal: ").strip()
    if not goal:
        return
    profile = sup.design_swarm(goal)
    size = input(f"Swarm size [{profile.size}]: ").strip()
    if size.isdigit():
        profile.size = int(size)
    topo = input(f"Topology {[t.value for t in Topology]} [{profile.topology.value}]: ").strip()
    if topo in [t.value for t in Topology]:
        profile.topology = Topology(topo)

    async def _go() -> GoalOutcome:
        result = await sup.spawner.spawn(profile, task=goal, budget=sup.default_budget)
        consolidation = sup._consolidate(result.swarm_id)
        return GoalOutcome(goal=goal, profile=profile,
                           aggregation=result.aggregation,
                           consolidation=consolidation, swarm_id=result.swarm_id)

    print(_dim(f"\nspawning {profile.size} agents ({profile.topology.value})…"))
    out = asyncio.run(_go())
    print(_bold(f"\nswarm {out.swarm_id}: ") +
          f"{out.profile.name} size={out.profile.size}")
    print(_green(f"agreement {out.aggregation.agreement:.2f} "
                 f"({out.aggregation.n_ok}/{out.aggregation.n_total} ok)"))
    print(_bold("synthesis: ") + out.aggregation.summary)
    print(_dim(f"consolidated: promoted {out.consolidation['promoted']} -> "
               f"{out.consolidation['memory_after']}"))
    _pause()


def _do_dashboard(sup: Supervisor) -> None:
    print(_bold("\nObservability dashboard:"))
    print(sup.dashboard.render())
    _pause()


def _do_memory(sup: Supervisor) -> None:
    print(_bold("\nParent memory: ") + str(sup.memory.stats()))
    if sup.memory.skills:
        print(_bold("Skills learned:"))
        for s in sup.memory.skills:
            print("  " + s.text)
    _pause()


def run() -> int:
    sup = Supervisor(default_budget=Budget(max_tokens=80_000))
    actions = {"run": _do_run, "dashboard": _do_dashboard, "memory": _do_memory}
    while True:
        _clear()
        print(render_menu())
        choice = input("\nSelect [1-{0}]: ".format(len(MENU))).strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(MENU)):
            continue
        key = MENU[int(choice) - 1][1]
        if key == "quit":
            print(_dim("Goodbye."))
            return 0
        if key == "onboard":
            onboard_mod.run()
            _pause()
            continue
        actions[key](sup)


if __name__ == "__main__":
    sys.exit(run())
