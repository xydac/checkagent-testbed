"""
Session 024 — multiagent trace and credit assignment module.

New feature: checkagent.multiagent
  - MultiAgentTrace: container for multi-agent runs + handoffs
  - Handoff: agent-to-agent handoff with type and metadata
  - BlameStrategy: 5 strategies for attributing failures
  - assign_blame: single-strategy blame attribution
  - assign_blame_ensemble: multi-strategy blame attribution
  - top_blamed_agent: consensus blame across strategies

Key findings this session:
  - F-068: multiagent module not at top-level checkagent (12th instance of pattern)
  - F-069: LEAF_ERRORS blames agents WITH outgoing handoffs (inverted leaf logic)
  - F-070: assign_blame returns None silently when agent_id is not set on AgentRun
  - F-071: HandoffType not importable from checkagent.multiagent (only .trace submodule)
  - F-072: MultiAgentTrace doesn't validate handoff agent IDs (nonexistent IDs silently accepted)
"""

import pytest
from checkagent import AgentRun, AgentInput
from checkagent.multiagent import (
    MultiAgentTrace,
    Handoff,
    BlameStrategy,
    BlameResult,
    assign_blame,
    assign_blame_ensemble,
    top_blamed_agent,
)
from checkagent.multiagent.trace import HandoffType


# ---------------------------------------------------------------------------
# Helper: build a standard three-agent trace (orchestrator -> search -> summarizer)
# ---------------------------------------------------------------------------

def _make_three_agent_trace(
    orchestrator_error=None,
    search_error=None,
    summarizer_error=None,
    search_tokens=(100, 50),
    summarizer_tokens=(200, 80),
):
    run_orch = AgentRun(
        input=AgentInput(query="Research and summarize AI papers"),
        final_output=None if orchestrator_error else "done",
        agent_id="orchestrator",
        agent_name="OrchestratorAgent",
        error=orchestrator_error,
    )
    run_search = AgentRun(
        input=AgentInput(query="Search arxiv"),
        final_output=None if search_error else "results",
        agent_id="search",
        agent_name="SearchAgent",
        error=search_error,
        total_prompt_tokens=search_tokens[0],
        total_completion_tokens=search_tokens[1],
    )
    run_summarizer = AgentRun(
        input=AgentInput(query="Summarize"),
        final_output=None if summarizer_error else "summary",
        agent_id="summarizer",
        agent_name="SummarizerAgent",
        error=summarizer_error,
        total_prompt_tokens=summarizer_tokens[0],
        total_completion_tokens=summarizer_tokens[1],
    )
    trace = MultiAgentTrace(
        runs=[run_orch, run_search, run_summarizer],
        handoffs=[
            Handoff(from_agent_id="orchestrator", to_agent_id="search"),
            Handoff(from_agent_id="orchestrator", to_agent_id="summarizer"),
        ],
        trace_id="trace-test-001",
    )
    return trace


# ---------------------------------------------------------------------------
# F-068: multiagent module not at top-level checkagent
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f068_multiagent_not_at_top_level():
    """F-068: multiagent module not exported from top-level checkagent namespace."""
    import checkagent
    assert not hasattr(checkagent, "MultiAgentTrace"), \
        "F-068 FIXED: MultiAgentTrace is now at top-level checkagent"
    assert not hasattr(checkagent, "Handoff"), \
        "F-068 FIXED: Handoff is now at top-level checkagent"
    assert not hasattr(checkagent, "assign_blame"), \
        "F-068 FIXED: assign_blame is now at top-level checkagent"
    assert not hasattr(checkagent, "BlameStrategy"), \
        "F-068 FIXED: BlameStrategy is now at top-level checkagent"
    assert not hasattr(checkagent, "top_blamed_agent"), \
        "F-068 FIXED: top_blamed_agent is now at top-level checkagent"


@pytest.mark.agent_test
def test_f068_multiagent_importable_from_submodule():
    """Workaround for F-068: all multiagent types work from checkagent.multiagent."""
    # All of these should work despite not being at top-level
    from checkagent.multiagent import (
        MultiAgentTrace,
        Handoff,
        BlameStrategy,
        BlameResult,
        assign_blame,
        assign_blame_ensemble,
        top_blamed_agent,
    )
    assert MultiAgentTrace is not None
    assert Handoff is not None
    assert assign_blame is not None


# ---------------------------------------------------------------------------
# F-071: HandoffType not importable from checkagent.multiagent
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f071_handoff_type_not_in_multiagent_namespace():
    """F-071 FIXED: HandoffType is now accessible from checkagent.multiagent."""
    import checkagent.multiagent as ma
    assert hasattr(ma, "HandoffType"), \
        "HandoffType should be importable from checkagent.multiagent"
    from checkagent.multiagent import HandoffType
    assert set(e.value for e in HandoffType) == {"delegation", "relay", "broadcast"}


@pytest.mark.agent_test
def test_f071_handoff_type_accessible_from_internal_submodule():
    """Workaround: HandoffType importable from checkagent.multiagent.trace."""
    from checkagent.multiagent.trace import HandoffType
    assert set(e.value for e in HandoffType) == {"delegation", "relay", "broadcast"}


# ---------------------------------------------------------------------------
# MultiAgentTrace construction
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_multiagent_trace_construction_basic():
    """MultiAgentTrace can be constructed with runs and handoffs."""
    trace = _make_three_agent_trace(search_error="Rate limit")
    assert trace.trace_id == "trace-test-001"
    assert len(trace.runs) == 3
    assert len(trace.handoffs) == 2


@pytest.mark.agent_test
def test_multiagent_trace_empty_construction():
    """MultiAgentTrace defaults to empty runs and handoffs."""
    trace = MultiAgentTrace()
    assert trace.runs == []
    assert trace.handoffs == []
    assert trace.trace_id is None


@pytest.mark.agent_test
def test_multiagent_trace_runs_preserve_order():
    """Runs are stored in insertion order."""
    r1 = AgentRun(input=AgentInput(query="a"), agent_id="a", final_output="ok")
    r2 = AgentRun(input=AgentInput(query="b"), agent_id="b", final_output="ok")
    r3 = AgentRun(input=AgentInput(query="c"), agent_id="c", final_output="ok")
    trace = MultiAgentTrace(runs=[r1, r2, r3])
    assert [r.agent_id for r in trace.runs] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Handoff construction and types
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_handoff_defaults_to_delegation():
    """Handoff defaults to DELEGATION type."""
    h = Handoff(from_agent_id="a", to_agent_id="b")
    assert h.handoff_type == HandoffType.DELEGATION


@pytest.mark.agent_test
def test_handoff_all_types():
    """All HandoffType values are constructable."""
    h_relay = Handoff(from_agent_id="a", to_agent_id="b", handoff_type=HandoffType.RELAY)
    h_broadcast = Handoff(from_agent_id="a", to_agent_id="b", handoff_type=HandoffType.BROADCAST)
    assert h_relay.handoff_type == HandoffType.RELAY
    assert h_broadcast.handoff_type == HandoffType.BROADCAST


@pytest.mark.agent_test
def test_handoff_optional_metadata():
    """Handoff accepts optional metadata fields."""
    h = Handoff(
        from_agent_id="orch",
        to_agent_id="worker",
        from_run_id="run-001",
        to_run_id="run-002",
        input_summary="here is the context",
        latency_ms=45.2,
    )
    assert h.from_run_id == "run-001"
    assert h.to_run_id == "run-002"
    assert h.input_summary == "here is the context"
    assert h.latency_ms == 45.2


# ---------------------------------------------------------------------------
# F-072: MultiAgentTrace doesn't validate handoff agent IDs
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f072_multiagent_trace_accepts_nonexistent_handoff_agent_ids():
    """F-072: MultiAgentTrace accepts handoffs referencing agent IDs not in any run."""
    real_run = AgentRun(input=AgentInput(query="real"), agent_id="real", final_output="ok")
    # These agent IDs don't exist in any run — no error is raised
    trace = MultiAgentTrace(
        runs=[real_run],
        handoffs=[
            Handoff(from_agent_id="ghost-agent", to_agent_id="also-ghost")
        ],
    )
    assert len(trace.handoffs) == 1
    # No validation error — dangling handoff references are silently accepted
    assert trace.handoffs[0].from_agent_id == "ghost-agent"


# ---------------------------------------------------------------------------
# assign_blame — basic strategy behavior
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_assign_blame_returns_none_on_no_errors():
    """assign_blame returns None when no run has an error."""
    r = AgentRun(input=AgentInput(query="all good"), agent_id="happy", final_output="success")
    trace = MultiAgentTrace(runs=[r])
    result = assign_blame(trace)
    assert result is None


@pytest.mark.agent_test
def test_assign_blame_returns_none_on_empty_trace():
    """assign_blame returns None for empty MultiAgentTrace."""
    trace = MultiAgentTrace()
    result = assign_blame(trace)
    assert result is None


@pytest.mark.agent_test
def test_assign_blame_first_error():
    """FIRST_ERROR blames the first run (in list order) that has an error."""
    run_a = AgentRun(input=AgentInput(query="a"), agent_id="a", final_output=None, error="error A")
    run_b = AgentRun(input=AgentInput(query="b"), agent_id="b", final_output=None, error="error B")
    trace = MultiAgentTrace(runs=[run_a, run_b])
    blame = assign_blame(trace, BlameStrategy.FIRST_ERROR)
    assert blame is not None
    assert blame.agent_id == "a"
    assert blame.strategy == BlameStrategy.FIRST_ERROR
    assert 0.0 <= blame.confidence <= 1.0
    assert blame.reason != ""


@pytest.mark.agent_test
def test_assign_blame_last_agent():
    """LAST_AGENT blames the last run (in list order) that has an error."""
    run_a = AgentRun(input=AgentInput(query="a"), agent_id="a", final_output=None, error="error A")
    run_b = AgentRun(input=AgentInput(query="b"), agent_id="b", final_output=None, error="error B")
    trace = MultiAgentTrace(runs=[run_a, run_b])
    blame = assign_blame(trace, BlameStrategy.LAST_AGENT)
    assert blame is not None
    assert blame.agent_id == "b"
    assert blame.strategy == BlameStrategy.LAST_AGENT


@pytest.mark.agent_test
def test_assign_blame_highest_cost():
    """HIGHEST_COST blames the failed agent with most tokens (prompt + completion)."""
    run_cheap = AgentRun(
        input=AgentInput(query="cheap"),
        agent_id="cheap",
        final_output=None,
        error="fail",
        total_prompt_tokens=10,
        total_completion_tokens=5,
    )
    run_expensive = AgentRun(
        input=AgentInput(query="expensive"),
        agent_id="expensive",
        final_output=None,
        error="fail",
        total_prompt_tokens=5000,
        total_completion_tokens=2000,
    )
    trace = MultiAgentTrace(runs=[run_cheap, run_expensive])
    blame = assign_blame(trace, BlameStrategy.HIGHEST_COST)
    assert blame is not None
    assert blame.agent_id == "expensive"
    assert blame.strategy == BlameStrategy.HIGHEST_COST


@pytest.mark.agent_test
def test_assign_blame_highest_cost_returns_none_without_token_data():
    """HIGHEST_COST returns None when no runs have token counts."""
    run = AgentRun(input=AgentInput(query="no tokens"), agent_id="a", final_output=None, error="fail")
    trace = MultiAgentTrace(runs=[run])
    blame = assign_blame(trace, BlameStrategy.HIGHEST_COST)
    # Without token data, HIGHEST_COST cannot determine cost — returns None
    assert blame is None


@pytest.mark.agent_test
def test_assign_blame_most_steps():
    """MOST_STEPS blames the failed agent with the most steps."""
    from checkagent import Step
    step1 = Step(input_text="t1", output_text="r1")
    step2 = Step(input_text="t2", output_text="r2")
    step3 = Step(input_text="t3", output_text="r3")
    run_few = AgentRun(
        input=AgentInput(query="few steps"),
        agent_id="few",
        final_output=None,
        error="fail",
        steps=[step1],
    )
    run_many = AgentRun(
        input=AgentInput(query="many steps"),
        agent_id="many",
        final_output=None,
        error="fail",
        steps=[step1, step2, step3],
    )
    trace = MultiAgentTrace(runs=[run_few, run_many])
    blame = assign_blame(trace, BlameStrategy.MOST_STEPS)
    assert blame is not None
    assert blame.agent_id == "many"


@pytest.mark.agent_test
def test_assign_blame_blame_result_fields():
    """BlameResult has all expected fields with correct types."""
    run = AgentRun(input=AgentInput(query="test"), agent_id="agent-x", agent_name="AgentX",
                   final_output=None, error="something broke")
    trace = MultiAgentTrace(runs=[run])
    blame = assign_blame(trace, BlameStrategy.FIRST_ERROR)
    assert blame is not None
    assert blame.agent_id == "agent-x"
    assert blame.agent_name == "AgentX"
    assert blame.strategy == BlameStrategy.FIRST_ERROR
    assert isinstance(blame.confidence, float)
    assert 0.0 <= blame.confidence <= 1.0
    assert isinstance(blame.reason, str)
    assert len(blame.reason) > 0


# ---------------------------------------------------------------------------
# F-069: LEAF_ERRORS inverted logic bug
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f069_leaf_errors_blames_wrong_agent():
    """F-069: LEAF_ERRORS blames agents WITH outgoing handoffs instead of leaf agents.

    In a chain A -> B where only B errors, LEAF_ERRORS should blame B (the leaf).
    The actual behavior blames A (the non-leaf), which is inverted.
    """
    run_a = AgentRun(
        input=AgentInput(query="orchestrate"),
        agent_id="a",
        final_output=None,
        error="wrapped error",
    )
    run_b = AgentRun(
        input=AgentInput(query="do work"),
        agent_id="b",
        final_output=None,
        error="root cause error",
    )
    trace = MultiAgentTrace(
        runs=[run_a, run_b],
        handoffs=[Handoff(from_agent_id="a", to_agent_id="b")],
    )
    blame = assign_blame(trace, BlameStrategy.LEAF_ERRORS)
    assert blame is not None
    # F-069 FIXED: LEAF_ERRORS now correctly blames b (the leaf, no outgoing handoffs)
    assert blame.agent_id == "b", (
        f"Expected leaf agent 'b' to be blamed, got '{blame.agent_id}'"
    )


@pytest.mark.agent_test
def test_f069_leaf_errors_expected_correct_behavior():
    """F-069: Documents the expected correct behavior for LEAF_ERRORS.

    In a chain A -> B where B has the error:
    - A has an outgoing handoff to B => A is NOT a leaf
    - B has no outgoing handoffs => B IS a leaf
    LEAF_ERRORS should blame B. Currently it blames A (bug).
    """
    run_a = AgentRun(input=AgentInput(query="orch"), agent_id="a", final_output=None, error="downstream fail")
    run_b = AgentRun(input=AgentInput(query="work"), agent_id="b", final_output=None, error="actual error")
    trace = MultiAgentTrace(
        runs=[run_a, run_b],
        handoffs=[Handoff(from_agent_id="a", to_agent_id="b")],
    )
    blame = assign_blame(trace, BlameStrategy.LEAF_ERRORS)
    assert blame is not None
    # F-069 FIXED: LEAF_ERRORS now correctly blames the leaf (b), not the orchestrator (a)
    assert blame.agent_id == "b", (
        f"Expected leaf agent 'b' (no outgoing handoffs) to be blamed, got '{blame.agent_id}'"
    )


# ---------------------------------------------------------------------------
# F-070: assign_blame returns None silently when agent_id is not set
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f070_assign_blame_returns_none_without_agent_id():
    """F-070: assign_blame returns None when AgentRun has no agent_id, even if it errors."""
    run = AgentRun(
        input=AgentInput(query="anonymous agent"),
        final_output=None,
        error="something broke",
        # No agent_id set
    )
    trace = MultiAgentTrace(runs=[run])
    blame = assign_blame(trace, BlameStrategy.FIRST_ERROR)
    # BUG F-070: the run has an error but assign_blame returns None because agent_id is None
    assert blame is None, (
        "F-070 FIXED: assign_blame now handles runs without agent_id"
    )


@pytest.mark.agent_test
def test_f070_assign_blame_ensemble_empty_without_agent_id():
    """F-070: assign_blame_ensemble returns empty list when no runs have agent_id."""
    run = AgentRun(input=AgentInput(query="anon"), final_output=None, error="fail")
    trace = MultiAgentTrace(runs=[run])
    results = assign_blame_ensemble(trace)
    assert results == [], (
        "F-070 FIXED: assign_blame_ensemble now handles runs without agent_id"
    )


# ---------------------------------------------------------------------------
# assign_blame_ensemble
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_assign_blame_ensemble_default_returns_multiple_results():
    """assign_blame_ensemble returns results for all applicable strategies."""
    run = AgentRun(
        input=AgentInput(query="test"),
        agent_id="agent-a",
        final_output=None,
        error="error",
        total_prompt_tokens=100,
        total_completion_tokens=50,
    )
    trace = MultiAgentTrace(runs=[run])
    results = assign_blame_ensemble(trace)
    assert len(results) >= 1
    assert all(isinstance(r, BlameResult) for r in results)
    assert all(r.agent_id == "agent-a" for r in results)


@pytest.mark.agent_test
def test_assign_blame_ensemble_custom_strategies():
    """assign_blame_ensemble accepts a custom list of strategies."""
    run = AgentRun(input=AgentInput(query="test"), agent_id="a", final_output=None, error="err")
    trace = MultiAgentTrace(runs=[run])
    results = assign_blame_ensemble(trace, strategies=[BlameStrategy.FIRST_ERROR, BlameStrategy.LAST_AGENT])
    assert len(results) == 2
    strategies_returned = {r.strategy for r in results}
    assert BlameStrategy.FIRST_ERROR in strategies_returned
    assert BlameStrategy.LAST_AGENT in strategies_returned


@pytest.mark.agent_test
def test_assign_blame_ensemble_skips_none_results():
    """assign_blame_ensemble skips strategies that return None (e.g. HIGHEST_COST without tokens)."""
    run = AgentRun(input=AgentInput(query="test"), agent_id="a", final_output=None, error="err")
    trace = MultiAgentTrace(runs=[run])
    results = assign_blame_ensemble(trace, strategies=[BlameStrategy.FIRST_ERROR, BlameStrategy.HIGHEST_COST])
    # HIGHEST_COST returns None without token data, so only FIRST_ERROR should appear
    assert len(results) == 1
    assert results[0].strategy == BlameStrategy.FIRST_ERROR


# ---------------------------------------------------------------------------
# top_blamed_agent
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_top_blamed_agent_returns_most_blamed():
    """top_blamed_agent returns the agent blamed by most strategies."""
    run_a = AgentRun(
        input=AgentInput(query="a"),
        agent_id="a",
        final_output=None,
        error="error a",
        total_prompt_tokens=5000,
        total_completion_tokens=2000,
    )
    run_b = AgentRun(
        input=AgentInput(query="b"),
        agent_id="b",
        final_output=None,
        error="error b",
        total_prompt_tokens=10,
        total_completion_tokens=5,
    )
    trace = MultiAgentTrace(runs=[run_a, run_b])
    top = top_blamed_agent(trace)
    assert top is not None
    # a: first_error, most_steps, highest_cost, leaf_errors (4/5)
    # b: last_agent (1/5)
    assert top.agent_id == "a"
    assert "strategies" in top.reason.lower() or "/" in top.reason


@pytest.mark.agent_test
def test_top_blamed_agent_returns_none_on_empty_trace():
    """top_blamed_agent returns None for empty trace."""
    trace = MultiAgentTrace()
    result = top_blamed_agent(trace)
    assert result is None


@pytest.mark.agent_test
def test_top_blamed_agent_returns_none_on_no_errors():
    """top_blamed_agent returns None when no agent has an error."""
    run = AgentRun(input=AgentInput(query="ok"), agent_id="happy", final_output="success")
    trace = MultiAgentTrace(runs=[run])
    result = top_blamed_agent(trace)
    assert result is None


@pytest.mark.agent_test
def test_top_blamed_agent_uses_strategy_of_winning_approach():
    """top_blamed_agent BlameResult.strategy field reflects the dominant strategy."""
    run = AgentRun(input=AgentInput(query="test"), agent_id="only-agent", final_output=None, error="fail")
    trace = MultiAgentTrace(runs=[run])
    top = top_blamed_agent(trace, strategies=[BlameStrategy.FIRST_ERROR])
    assert top is not None
    assert top.agent_id == "only-agent"


@pytest.mark.agent_test
def test_top_blamed_agent_custom_strategies():
    """top_blamed_agent accepts a custom list of strategies."""
    run = AgentRun(input=AgentInput(query="test"), agent_id="a", final_output=None, error="err")
    trace = MultiAgentTrace(runs=[run])
    top = top_blamed_agent(trace, strategies=[BlameStrategy.FIRST_ERROR, BlameStrategy.LAST_AGENT])
    assert top is not None
    assert top.agent_id == "a"


# ---------------------------------------------------------------------------
# Real-world multi-agent scenario: orchestrator delegates to subagents
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_multi_agent_scenario_leaf_error_attribution():
    """Realistic scenario: orchestrator delegates, leaf subagent fails.

    Tests that blame attribution identifies the correct responsible agent.
    Note: LEAF_ERRORS currently has the F-069 bug, so we test FIRST_ERROR here.
    """
    trace = _make_three_agent_trace(
        orchestrator_error=None,
        search_error="Rate limit exceeded",
        summarizer_error=None,
    )
    # Without error on orchestrator, FIRST_ERROR should blame search agent
    blame = assign_blame(trace, BlameStrategy.FIRST_ERROR)
    assert blame is not None
    assert blame.agent_id == "search"
    assert "Rate limit" in blame.reason


@pytest.mark.agent_test
def test_multi_agent_scenario_ensemble_on_healthy_trace():
    """Ensemble blame on a healthy trace (no errors) returns empty list."""
    trace = _make_three_agent_trace()  # no errors
    results = assign_blame_ensemble(trace)
    assert results == []
    top = top_blamed_agent(trace)
    assert top is None


@pytest.mark.agent_test
def test_multi_agent_scenario_multiple_errors_first_blamed():
    """When multiple agents fail, FIRST_ERROR blames the first in list order."""
    trace = _make_three_agent_trace(
        orchestrator_error="pipeline error",
        search_error="timeout",
        summarizer_error=None,
    )
    blame = assign_blame(trace, BlameStrategy.FIRST_ERROR)
    assert blame is not None
    # orchestrator is index 0 and has an error, so FIRST_ERROR blames it
    assert blame.agent_id == "orchestrator"


@pytest.mark.agent_test
def test_multi_agent_trace_with_relay_handoffs():
    """MultiAgentTrace can be constructed with relay-type handoffs."""
    run_a = AgentRun(input=AgentInput(query="step 1"), agent_id="stage-1", final_output="partial")
    run_b = AgentRun(input=AgentInput(query="step 2"), agent_id="stage-2", final_output=None, error="fail at stage 2")
    trace = MultiAgentTrace(
        runs=[run_a, run_b],
        handoffs=[
            Handoff(
                from_agent_id="stage-1",
                to_agent_id="stage-2",
                handoff_type=HandoffType.RELAY,
                input_summary="passing output from stage 1",
                latency_ms=12.5,
            )
        ],
    )
    blame = assign_blame(trace, BlameStrategy.LAST_AGENT)
    assert blame is not None
    assert blame.agent_id == "stage-2"
    assert trace.handoffs[0].handoff_type == HandoffType.RELAY
    assert trace.handoffs[0].latency_ms == 12.5


@pytest.mark.agent_test
def test_blame_result_confidence_bounds():
    """BlameResult.confidence is always between 0.0 and 1.0."""
    run = AgentRun(input=AgentInput(query="test"), agent_id="x", final_output=None, error="fail",
                   total_prompt_tokens=100, total_completion_tokens=50)
    trace = MultiAgentTrace(runs=[run])
    for strategy in BlameStrategy:
        result = assign_blame(trace, strategy)
        if result is not None:
            assert 0.0 <= result.confidence <= 1.0, \
                f"confidence out of bounds for {strategy}: {result.confidence}"


@pytest.mark.agent_test
def test_blame_strategy_enum_values():
    """BlameStrategy has all 5 expected values."""
    values = {e.value for e in BlameStrategy}
    assert values == {"first_error", "last_agent", "most_steps", "highest_cost", "leaf_errors"}
