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

## Setup

Requires **Python 3.10+**. No third-party packages are needed to run (offline
mock LLM); `pytest` is the only dev dependency.

```bash
# 1. clone
git clone https://github.com/smfworks/smf-clawless-orchestrator.git
cd smf-clawless-orchestrator

# 2. (recommended) create a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

# 3. install (editable) with the `clawmes` CLI + dev tools
pip install -e ".[dev]"
```

That's it — everything runs offline with a deterministic mock LLM, no API keys.

## Configure a model provider

Clawmes mirrors **OpenClaw's onboarding model**. Run the wizard to pick a
provider and model — it's offered automatically on first use, or run it anytime:

```bash
clawmes onboard
```

The wizard walks you through:
1. **Existing-config detection** — Keep / Modify / Reset (like `openclaw onboard`).
2. **Pick a provider** — Ollama · OpenRouter · GitHub Models · OpenAI · Anthropic · Custom (OpenAI-compatible).
3. **Pick a model** — suggestions per provider (Ollama models are auto-discovered from the local host), or enter one manually.
4. **Key storage** — environment-variable reference (recommended; nothing secret on disk) or paste-now (stored in `~/.clawmes/auth-profiles.json`, gitignored).

Config is written OpenClaw-style to `~/.clawmes/clawmes.json` (override the dir
with `CLAWMES_HOME`):

```json
{
  "agents": { "defaults": { "model": "openrouter/openai/gpt-4o-mini" } },
  "providers": {
    "openrouter": {
      "baseUrl": "https://openrouter.ai/api/v1",
      "compatibility": "openai",
      "keyRef": { "source": "env", "id": "OPENROUTER_API_KEY" }
    }
  }
}
```

Non-interactive (scripts/CI):

```bash
clawmes onboard --provider ollama --model llama3.1
clawmes onboard --provider openrouter --model "openai/gpt-4o-mini"   # uses OPENROUTER_API_KEY
```

**Model selection (`CLAWMES_LLM`):** `auto` (default — use the configured
provider if onboarded, else offline mock) · `mock` (always offline) · `real`
(always use the provider).

## Quick start

```bash
python demo.py            # end-to-end demo (mock LLM, offline)
pytest -q                 # 18 tests
```

## CLI

After `pip install -e .` the `clawmes` command is available (or run
`python -m clawmes.cli ...` without installing):

```bash
clawmes demo                                  # run the bundled demo
clawmes run "research AI orchestration papers and propose integrations"
clawmes run "large parallel Kalshi prediction" --size 50 --topology emergent
clawmes run "<goal>" --max-tokens 80000 --max-agents 200
clawmes --help
```

| Command | What it does |
|---|---|
| `clawmes run "<goal>"` | Supervisor designs a swarm, spawns it, prints synthesis + dashboard |
| `clawmes run ... --size N --topology {hierarchical,flat,emergent}` | override the designed profile |
| `clawmes run ... --max-tokens N --max-agents N` | set governance budgets |
| `clawmes demo` | run the full bundled demo |

## Tests & CI

`pytest -q` runs the 18-test suite. GitHub Actions
(`.github/workflows/ci.yml`) runs tests on Python 3.10–3.12 plus a demo/CLI
smoke test on every push and PR to `main`.

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
