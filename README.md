# Clawmes Orchestrator

A hybrid **OpenClaw + Hermes** framework with **dynamic sub-agent swarm
spawning**. A reasoning Supervisor decomposes goals, designs and spawns swarms
of specialized sub-agents (Researcher / Executor / Critic / Trader /
Synthesizer), runs them in parallel under a governance sandbox, aggregates
their output, and consolidates what was learned back into durable memory and a
reusable skill library.

Runs **fully offline** out of the box (deterministic mock LLM) — zero API keys
required — so you can prototype swarm patterns immediately, then wire a real
local/cloud model later.

```
            ┌──────────────────────────────────────────────┐
            │              Supervisor (brain)               │
            │  decompose → design swarm → spawn → aggregate │
            │            → consolidate memory/skills        │
            └───────────────┬───────────────────────────────┘
                            │ SwarmProfile (size/topology/roles/tools/teardown)
                ┌───────────▼───────────┐
                │   SwarmSpawner engine  │  per-swarm: governor + memory subspace + sandbox
                └───────────┬───────────┘
        ┌──────────┬────────┼────────┬──────────┐
        ▼          ▼        ▼        ▼          ▼
   Researcher  Executor  Critic   Trader   Synthesizer   ... (N agents, parallel)
        └──────────┴────────┴────────┴──────────┘
                            │ MessageBus (results queue)
                            ▼
                   Aggregation (synthesis / voting)
                            │
        ┌───────────────────┼────────────────────┐
        ▼                   ▼                     ▼
  Hybrid Memory      Governance Sandbox      Observability
  (semantic +        (budgets, kill-switch,  (live dashboard:
   per-swarm          injection screen,       tokens, agents,
   subspaces +        tool allowlist,         success rate)
   consolidation)     Sentinel Code, audit)
```

## Quick start

```bash
cd clawmes-orchestrator
python demo.py            # end-to-end demo (mock LLM, offline)
python -m pytest -q       # 18 tests
```

## What maps to the spec

| Spec component | Module |
|---|---|
| Hybrid memory + per-swarm subspaces + consolidation | `clawmes/memory.py` |
| Swarm Spawning Engine (clone profiles, parallel run, teardown) | `clawmes/spawner.py` |
| Recursive child swarms with depth/resource caps | `clawmes/governance.py` (`SwarmGovernor.child`) |
| Security & governance sandbox (budgets, kill-switch, injection, Sentinel Code, audit) | `clawmes/governance.py` |
| Orchestration Supervisor (decompose/design/aggregate/learn) | `clawmes/supervisor.py` |
| Role specialization | `clawmes/profiles.py` (`ROLE_TEMPLATES`) |
| Topologies: hierarchical / flat / emergent (MiroFish-style) | `clawmes/profiles.py` (`Topology`) |
| Communication channels / shared queues | `clawmes/bus.py` |
| Synthesis / voting aggregation | `clawmes/aggregate.py` |
| Observability dashboard | `clawmes/observability.py` |
| Skill evolution (successful patterns → reusable skills) | `memory.consolidate()` → `MemoryStore.skills` |

## Minimal usage

```python
import asyncio
from clawmes import Supervisor, Budget

async def main():
    sup = Supervisor(default_budget=Budget(max_tokens=50_000, max_agents=1000))
    out = await sup.run_goal("Research AI orchestration papers and propose integrations")
    print(out.aggregation.summary)
    print(out.consolidation)          # promoted episodic → semantic + skill
    print(sup.dashboard.render())     # observability

asyncio.run(main())
```

## Production wiring (next steps)

- **Real model:** implement `LLMClient._complete_real` (local llama.cpp/Ollama or
  cloud fallback) and set `CLAWMES_LLM=real`.
- **True sandboxing:** pass a `sandbox_factory` to `SwarmSpawner` that provisions
  Docker / Orgo-style VMs / Tailscale-namespaced sessions per agent.
- **Vector DB:** replace the mock `_embed`/cosine in `memory.py` with a real
  embedding model + vector store.
- **Persistence:** back `MemoryStore` curated docs with `SOUL.md` / `USER.md` /
  `MEMORY.md` files and the semantic index with your store of choice.
- **Human-in-the-loop:** honor `GovernancePolicy.human_in_the_loop` with an
  approval gate before sensitive swarms execute.

See `AGENTS.md` for declarative swarm-profile configuration.
