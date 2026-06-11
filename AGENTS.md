# AGENTS.md — Clawmes Orchestrator configuration

Declarative configuration for the Supervisor and its swarm profiles. The
Supervisor reads goals and either matches a named profile here or designs one
on the fly (`Supervisor.design_swarm`).

## Governance defaults (Sentinel Code is injected into every agent)

```yaml
budget:
  max_tokens: 100000        # per-swarm token cap (shared across descendants)
  max_api_calls: 500
  max_wall_seconds: 3600
  max_depth: 3              # recursive child-swarm depth limit
  max_agents: 1000          # hard ceiling on agents per swarm tree
policy:
  injection_check: true
  human_in_the_loop: false  # set true for sensitive swarms (e.g. trading, sends)
```

## Swarm profiles

```yaml
- name: PredictionSwarm
  size: 50
  topology: emergent          # MiroFish-style diverse personas
  roles: [trader, researcher, critic]
  tools: [market_api, analysis]
  persistent: false
  teardown_seconds: 3600      # auto-teardown after 1h or convergence

- name: ResearchSwarm
  size: 20
  topology: hierarchical      # supervisor → worker tree
  roles: [researcher, critic, synthesizer]
  tools: [web, analysis]
  teardown_seconds: 1800

- name: ContentSwarm
  size: 12
  topology: flat              # flat collaborative peers
  roles: [researcher, executor, critic, synthesizer]
  tools: [web]
  teardown_seconds: 1200

# SMF Works example: spawn a roofing lead-gen swarm
- name: RoofingLeadGenSwarm
  size: 25
  topology: hierarchical
  roles: [researcher, executor, critic]
  tools: [web, crm_api]
  persistent: true            # resident business-automation swarm
```

## Roles

| Role | Purpose |
|---|---|
| researcher | survey sources, extract high-signal findings + confidence |
| executor | carry out a concrete sub-task, return a verifiable artifact |
| critic | stress-test for risk / failure modes / governance gaps |
| trader | estimate market edge, position sizing, stop conditions |
| synthesizer | merge worker outputs into one recommendation + dissent |

## Topologies

- `hierarchical` — Orchestrator → Worker swarms (default).
- `flat` — flat collaborative peers.
- `emergent` — MiroFish-style emergent behavior from diverse personas.

## Memory layout

```
MemoryStore (parent)
├─ semantic[]            # durable distilled insights (vector-indexed)
├─ skills[]              # reusable patterns promoted from successful swarms
├─ curated{}             # SOUL.md / USER.md / MEMORY.md style docs
└─ /swarms/<uuid>/       # isolated per-swarm subspace
   └─ episodic[]         # private log; consolidated → parent, then discarded
```
