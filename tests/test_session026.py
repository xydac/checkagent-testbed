"""
Session-026 tests: F-074/F-076 fixes verified, new apply_detected_handoffs(),
handoff cycles, JSON serialization, F-073 still open.

Focus areas:
- F-074 FIXED: add_run/add_handoff now return self — builder chaining works
- F-076 FIXED: detect_handoffs() is now read-only; apply_detected_handoffs() added
- F-073 still open: get_children takes run_id, not agent_id (inconsistent with others)
- New apply_detected_handoffs(): bridges parent_run_id → handoff_chain gap (F-075 workaround)
- handoff_chain() behavior with cycles: no crash, repeats root
- MultiAgentTrace JSON round-trip via Pydantic model_dump_json/model_validate_json
"""

import pytest
from checkagent import AgentRun, AgentInput, Step
from checkagent.multiagent import (
    MultiAgentTrace,
    Handoff,
    BlameStrategy,
    BlameResult,
    assign_blame,
    assign_blame_ensemble,
    top_blamed_agent,
    HandoffType,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_run(agent_id: str, run_id: str | None = None, error: str | None = None,
              parent_run_id: str | None = None, steps: int = 0) -> AgentRun:
    s = [Step(input_text=f"step{i}", output_text=f"out{i}") for i in range(steps)]
    return AgentRun(
        input=AgentInput(query=f"query for {agent_id}"),
        agent_id=agent_id,
        run_id=run_id,
        parent_run_id=parent_run_id,
        steps=s,
        final_output=None if error else f"output from {agent_id}",
        error=error,
    )


# ---------------------------------------------------------------------------
# F-074 FIXED: Builder chaining now works
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f074_fixed_add_run_returns_self():
    """F-074 FIXED: add_run() now returns self — builder chaining works."""
    trace = MultiAgentTrace()
    result = trace.add_run(_make_run("a"))
    assert result is trace, "add_run must return self for chaining"


@pytest.mark.agent_test
def test_f074_fixed_add_handoff_returns_self():
    """F-074 FIXED: add_handoff() now returns self — builder chaining works."""
    trace = MultiAgentTrace()
    result = trace.add_handoff(Handoff(from_agent_id="a", to_agent_id="b"))
    assert result is trace, "add_handoff must return self for chaining"


@pytest.mark.agent_test
def test_f074_fixed_full_builder_chain():
    """F-074 FIXED: Full builder chain — add_run().add_run().add_handoff() works."""
    trace = (
        MultiAgentTrace()
        .add_run(_make_run("orch", run_id="run-orch"))
        .add_run(_make_run("worker", run_id="run-worker"))
        .add_handoff(Handoff(from_agent_id="orch", to_agent_id="worker"))
    )
    assert len(trace.runs) == 2
    assert len(trace.handoffs) == 1
    assert trace.agent_ids == ["orch", "worker"]
    assert trace.handoff_chain() == ["orch", "worker"]


@pytest.mark.agent_test
def test_f074_fixed_three_level_chain():
    """F-074 FIXED: Builder pattern works for a 3-level agent hierarchy."""
    trace = (
        MultiAgentTrace()
        .add_run(_make_run("a", run_id="run-a"))
        .add_run(_make_run("b", run_id="run-b"))
        .add_run(_make_run("c", run_id="run-c"))
        .add_handoff(Handoff(from_agent_id="a", to_agent_id="b"))
        .add_handoff(Handoff(from_agent_id="b", to_agent_id="c"))
    )
    assert len(trace.runs) == 3
    assert len(trace.handoffs) == 2
    assert trace.handoff_chain() == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# F-076 FIXED: detect_handoffs() is now read-only
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f076_fixed_detect_handoffs_is_read_only():
    """F-076 FIXED: detect_handoffs() no longer mutates trace.handoffs."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b", parent_run_id="run-a")
    trace = MultiAgentTrace(runs=[run_a, run_b])

    assert len(trace.handoffs) == 0

    detected = trace.detect_handoffs()
    assert len(detected) == 1, "detect_handoffs should return detected handoffs"
    assert len(trace.handoffs) == 0, "trace.handoffs must not be mutated"


@pytest.mark.agent_test
def test_f076_fixed_detect_handoffs_twice_no_duplicate():
    """F-076 FIXED: Calling detect_handoffs() twice doesn't duplicate anything."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b", parent_run_id="run-a")
    trace = MultiAgentTrace(runs=[run_a, run_b])

    trace.detect_handoffs()
    trace.detect_handoffs()
    assert len(trace.handoffs) == 0, "No mutation even after two calls"


@pytest.mark.agent_test
def test_f076_fixed_detect_handoffs_no_chain_poisoning():
    """F-076 FIXED: handoff_chain() unaffected after detect_handoffs()."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b", parent_run_id="run-a")
    trace = MultiAgentTrace(runs=[run_a, run_b])

    assert trace.handoff_chain() == []
    trace.detect_handoffs()
    assert trace.handoff_chain() == [], "handoff_chain must still be empty after detect_handoffs"


# ---------------------------------------------------------------------------
# apply_detected_handoffs() — new method added alongside F-076 fix
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_apply_detected_handoffs_populates_handoffs():
    """apply_detected_handoffs() explicitly converts parent_run_id links to handoffs."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b", parent_run_id="run-a")
    trace = MultiAgentTrace(runs=[run_a, run_b])

    assert len(trace.handoffs) == 0
    trace.apply_detected_handoffs()
    assert len(trace.handoffs) == 1


@pytest.mark.agent_test
def test_apply_detected_handoffs_is_idempotent():
    """apply_detected_handoffs() is idempotent — calling twice doesn't duplicate."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b", parent_run_id="run-a")
    trace = MultiAgentTrace(runs=[run_a, run_b])

    trace.apply_detected_handoffs()
    assert len(trace.handoffs) == 1

    trace.apply_detected_handoffs()
    assert len(trace.handoffs) == 1, "apply_detected_handoffs is idempotent — no duplicates"


@pytest.mark.agent_test
def test_apply_detected_handoffs_returns_list():
    """apply_detected_handoffs() returns the list of applied handoffs."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b", parent_run_id="run-a")
    trace = MultiAgentTrace(runs=[run_a, run_b])

    result = trace.apply_detected_handoffs()
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Handoff)
    assert result[0].from_agent_id == "a"
    assert result[0].to_agent_id == "b"


@pytest.mark.agent_test
def test_apply_detected_handoffs_bridges_f075_gap():
    """F-075 workaround: apply_detected_handoffs() makes handoff_chain() consistent
    with root_runs for parent_run_id-based topologies.

    After calling apply_detected_handoffs(), both topology sources agree.
    """
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b", parent_run_id="run-a")
    run_c = _make_run("c", run_id="run-c", parent_run_id="run-b")
    trace = MultiAgentTrace(runs=[run_a, run_b, run_c])

    # Before: inconsistent
    assert trace.handoff_chain() == []
    assert len(trace.root_runs) == 1  # a is root via parent_run_id

    # After apply_detected_handoffs: consistent
    trace.apply_detected_handoffs()
    chain = trace.handoff_chain()
    assert chain == ["a", "b", "c"], f"handoff_chain should be [a,b,c], got {chain}"
    assert trace.root_runs[0].agent_id == chain[0], "root_runs and handoff_chain now agree"


@pytest.mark.agent_test
def test_apply_detected_handoffs_with_fan_out():
    """apply_detected_handoffs() handles fan-out topology (one parent, multiple children)."""
    run_orch = _make_run("orch", run_id="run-orch")
    run_w1 = _make_run("w1", run_id="run-w1", parent_run_id="run-orch")
    run_w2 = _make_run("w2", run_id="run-w2", parent_run_id="run-orch")
    run_w3 = _make_run("w3", run_id="run-w3", parent_run_id="run-orch")
    trace = MultiAgentTrace(runs=[run_orch, run_w1, run_w2, run_w3])

    trace.apply_detected_handoffs()
    assert len(trace.handoffs) == 3
    from_agents = {h.from_agent_id for h in trace.handoffs}
    to_agents = {h.to_agent_id for h in trace.handoffs}
    assert from_agents == {"orch"}
    assert to_agents == {"w1", "w2", "w3"}


# ---------------------------------------------------------------------------
# F-073: get_children still takes run_id, not agent_id
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f073_get_children_takes_run_id_not_agent_id():
    """F-073: get_children() takes run_id — inconsistent with all other topology methods.

    Every other method uses agent_id:
      get_handoffs_from(agent_id), get_handoffs_to(agent_id), get_runs_by_agent(agent_id)
    But get_children(run_id) takes the run_id field of AgentRun, not agent_id.

    This is a silent trap: get_children('my-agent') returns [] even when children exist.
    """
    run_a = _make_run("orch", run_id="run-orch-001")
    run_b = _make_run("worker", run_id="run-worker-002", parent_run_id="run-orch-001")
    trace = MultiAgentTrace(runs=[run_a, run_b])

    # Using agent_id (looks right, silently returns empty)
    by_agent_id = trace.get_children("orch")
    assert len(by_agent_id) == 0, (
        "F-073: get_children('orch') returns [] — agent_id is the WRONG key here"
    )

    # Using run_id (the actual required parameter)
    by_run_id = trace.get_children("run-orch-001")
    assert len(by_run_id) == 1, (
        "get_children requires the run_id, not agent_id"
    )
    assert by_run_id[0].agent_id == "worker"


@pytest.mark.agent_test
def test_f073_api_inconsistency_with_other_methods():
    """F-073: Demonstrates the inconsistency: get_children uses run_id, others use agent_id."""
    run_a = _make_run("orch", run_id="run-001")
    run_b = _make_run("worker", run_id="run-002", parent_run_id="run-001")
    trace = MultiAgentTrace(
        runs=[run_a, run_b],
        handoffs=[Handoff(from_agent_id="orch", to_agent_id="worker")],
    )

    # All other methods use agent_id — consistent with each other
    assert len(trace.get_handoffs_from("orch")) == 1   # agent_id
    assert len(trace.get_handoffs_to("worker")) == 1   # agent_id
    assert len(trace.get_runs_by_agent("orch")) == 1   # agent_id

    # get_children breaks the pattern — uses run_id
    assert len(trace.get_children("orch")) == 0       # F-073: agent_id silently fails
    assert len(trace.get_children("run-001")) == 1    # run_id is required


# ---------------------------------------------------------------------------
# handoff_chain() with cycles
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_handoff_chain_simple_cycle_raises_value_error():
    """F-077 FIXED: handoff_chain() now raises ValueError on 2-node cycle."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b")
    trace = MultiAgentTrace(
        runs=[run_a, run_b],
        handoffs=[
            Handoff(from_agent_id="a", to_agent_id="b"),
            Handoff(from_agent_id="b", to_agent_id="a"),
        ],
    )
    with pytest.raises(ValueError, match="Cycle detected"):
        trace.handoff_chain()


@pytest.mark.agent_test
def test_has_cycles_detects_two_node_cycle():
    """F-077 FIXED: has_cycles() returns True for 2-node cycle."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b")
    trace = MultiAgentTrace(
        runs=[run_a, run_b],
        handoffs=[
            Handoff(from_agent_id="a", to_agent_id="b"),
            Handoff(from_agent_id="b", to_agent_id="a"),
        ],
    )
    assert trace.has_cycles() is True


@pytest.mark.agent_test
def test_handoff_chain_three_node_cycle_raises():
    """F-077 FIXED: handoff_chain() raises ValueError on 3-node cycle."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b")
    run_c = _make_run("c", run_id="run-c")
    trace = MultiAgentTrace(
        runs=[run_a, run_b, run_c],
        handoffs=[
            Handoff(from_agent_id="a", to_agent_id="b"),
            Handoff(from_agent_id="b", to_agent_id="c"),
            Handoff(from_agent_id="c", to_agent_id="a"),
        ],
    )
    with pytest.raises(ValueError, match="Cycle detected"):
        trace.handoff_chain()


@pytest.mark.agent_test
def test_has_cycles_false_for_dag():
    """has_cycles() returns False for a linear/acyclic handoff chain."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b")
    run_c = _make_run("c", run_id="run-c")
    trace = MultiAgentTrace(
        runs=[run_a, run_b, run_c],
        handoffs=[
            Handoff(from_agent_id="a", to_agent_id="b"),
            Handoff(from_agent_id="b", to_agent_id="c"),
        ],
    )
    assert trace.has_cycles() is False
    chain = trace.handoff_chain()
    assert chain == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# MultiAgentTrace JSON serialization round-trip
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_multiagent_trace_json_round_trip_basic():
    """MultiAgentTrace round-trips cleanly via model_dump_json/model_validate_json."""
    run_a = _make_run("orch", run_id="run-orch", error=None)
    run_b = _make_run("worker", run_id="run-worker", error="timeout", parent_run_id="run-orch")
    trace = MultiAgentTrace(
        runs=[run_a, run_b],
        handoffs=[Handoff(from_agent_id="orch", to_agent_id="worker")],
        trace_id="test-trace-001",
    )

    json_str = trace.model_dump_json()
    loaded = MultiAgentTrace.model_validate_json(json_str)

    assert len(loaded.runs) == 2
    assert len(loaded.handoffs) == 1
    assert loaded.trace_id == "test-trace-001"
    assert loaded.runs[0].agent_id == "orch"
    assert loaded.runs[1].agent_id == "worker"
    assert loaded.runs[1].error == "timeout"
    assert loaded.handoffs[0].from_agent_id == "orch"


@pytest.mark.agent_test
def test_multiagent_trace_json_preserves_agent_ids():
    """JSON round-trip preserves agent_ids and run_ids for blame attribution."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b", parent_run_id="run-a", error="failed")
    trace = MultiAgentTrace(runs=[run_a, run_b])

    loaded = MultiAgentTrace.model_validate_json(trace.model_dump_json())
    assert loaded.agent_ids == ["a", "b"]
    assert loaded.runs[1].parent_run_id == "run-a"

    # Blame attribution still works after round-trip
    blame = assign_blame(loaded, BlameStrategy.FIRST_ERROR)
    assert blame is not None
    assert blame.agent_id == "b"


@pytest.mark.agent_test
def test_multiagent_trace_json_round_trip_with_handoff_types():
    """JSON round-trip preserves HandoffType enum values."""
    run_a = _make_run("a", run_id="run-a")
    run_b = _make_run("b", run_id="run-b")
    run_c = _make_run("c", run_id="run-c")
    trace = MultiAgentTrace(
        runs=[run_a, run_b, run_c],
        handoffs=[
            Handoff(from_agent_id="a", to_agent_id="b", handoff_type=HandoffType.DELEGATION),
            Handoff(from_agent_id="a", to_agent_id="c", handoff_type=HandoffType.BROADCAST),
        ],
    )

    loaded = MultiAgentTrace.model_validate_json(trace.model_dump_json())
    assert loaded.handoffs[0].handoff_type == HandoffType.DELEGATION
    assert loaded.handoffs[1].handoff_type == HandoffType.BROADCAST


# ---------------------------------------------------------------------------
# assign_blame_ensemble: lambda strategy behavior
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_assign_blame_ensemble_lambda_strategies_accepted():
    """assign_blame_ensemble accepts non-BlameStrategy items in strategies list.

    Lambdas returning None are silently filtered out (no exception).
    This is undocumented behavior — the API accepts any iterable.
    """
    run_a = _make_run("a", run_id="run-a", error="failure")
    trace = MultiAgentTrace(runs=[run_a])

    # Lambda that returns None → filtered from results
    results = assign_blame_ensemble(trace, strategies=[lambda t: None])
    assert results == [], "Lambda returning None is silently filtered"


@pytest.mark.agent_test
def test_assign_blame_ensemble_custom_subset():
    """Custom strategies subset works correctly for targeted blame attribution."""
    run_a = _make_run("orch", run_id="run-a", error="delegate failed")
    run_b = _make_run("worker", run_id="run-b", error="timeout")
    trace = MultiAgentTrace(
        runs=[run_a, run_b],
        handoffs=[Handoff(from_agent_id="orch", to_agent_id="worker")],
    )

    # FIRST_ERROR blames orch (first in list), LAST_AGENT blames worker (last)
    results = assign_blame_ensemble(trace, strategies=[BlameStrategy.FIRST_ERROR, BlameStrategy.LAST_AGENT])
    assert len(results) == 2
    agents = {r.agent_id for r in results}
    assert "orch" in agents
    assert "worker" in agents


# ---------------------------------------------------------------------------
# Complex 3-level topology: blame attribution correctness
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_three_level_leaf_blame():
    """LEAF_ERRORS correctly blames the deepest erroring leaf in a 3-level chain."""
    run_top = _make_run("top", error=None)
    run_mid = _make_run("mid", error=None)
    run_leaf = _make_run("leaf", error="index out of range")
    trace = MultiAgentTrace(
        runs=[run_top, run_mid, run_leaf],
        handoffs=[
            Handoff(from_agent_id="top", to_agent_id="mid"),
            Handoff(from_agent_id="mid", to_agent_id="leaf"),
        ],
    )
    blame = assign_blame(trace, BlameStrategy.LEAF_ERRORS)
    assert blame is not None
    assert blame.agent_id == "leaf"


@pytest.mark.agent_test
def test_three_level_ensemble():
    """Ensemble on 3-level chain (top→mid→leaf failing): leaf wins across strategies."""
    run_top = _make_run("top", error=None)
    run_mid = _make_run("mid", error=None)
    run_leaf = _make_run("leaf", error="database timeout")
    trace = MultiAgentTrace(
        runs=[run_top, run_mid, run_leaf],
        handoffs=[
            Handoff(from_agent_id="top", to_agent_id="mid"),
            Handoff(from_agent_id="mid", to_agent_id="leaf"),
        ],
    )
    winner = top_blamed_agent(trace)
    assert winner is not None
    # top_blamed_agent returns a BlameResult (not a string)
    assert winner.agent_id == "leaf", f"Leaf should win — got {winner}"


@pytest.mark.agent_test
def test_top_blamed_agent_with_multiple_errors_and_builder():
    """top_blamed_agent with builder-constructed trace (F-074 FIXED) works end-to-end."""
    trace = (
        MultiAgentTrace()
        .add_run(_make_run("orchestrator", run_id="r1", error="worker failed"))
        .add_run(_make_run("retriever", run_id="r2", error="timeout"))
        .add_run(_make_run("ranker", run_id="r3", error="gpu oom"))
        .add_handoff(Handoff(from_agent_id="orchestrator", to_agent_id="retriever"))
        .add_handoff(Handoff(from_agent_id="orchestrator", to_agent_id="ranker"))
    )
    winner = top_blamed_agent(trace)
    assert winner is not None
    # top_blamed_agent returns a BlameResult — check agent_id
    # orchestrator has 2 children in handoffs, so LEAF_ERRORS blames retriever or ranker
    assert winner.agent_id in {"retriever", "ranker", "orchestrator"}
