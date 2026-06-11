from clawmes.memory import MemoryStore


def test_subspace_is_cached():
    store = MemoryStore()
    a = store.subspace("sw-1")
    b = store.subspace("sw-1")
    assert a is b


def test_search_returns_relevant():
    store = MemoryStore()
    store.add("orchestration supervisor worker topology")
    store.add("roofing lead generation pipeline")
    hits = store.search("supervisor topology", k=1)
    assert hits and "orchestration" in hits[0].text


def test_consolidation_promotes_and_clears():
    store = MemoryStore()
    sub = store.subspace("sw-x")
    for i in range(4):
        sub.remember(f"episodic finding number {i} with some detail")
    before = store.stats()["semantic"]
    summary = sub.consolidate(discard_raw=True)
    assert summary["promoted"] == 4
    assert summary["skill"] is not None
    assert store.stats()["semantic"] == before + 1   # one distilled insight
    assert len(store.skills) == 1
    assert sub.episodic == []                          # raw cleared (no bloat)


def test_swarm_context_reads_parent():
    store = MemoryStore()
    store.add("shared parent fact about isolation namespaces")
    sub = store.subspace("sw-y")
    ctx = sub.context("isolation namespaces", k=1)
    assert ctx and "isolation" in ctx[0]
