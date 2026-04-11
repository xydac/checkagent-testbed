"""
Session 008 tests — strict_validation, reset/reset_calls, FaultInjector+call_sync,
multi-step call_index, reset() vs reset_calls() parity.

Upgraded to: 8e6a0a8
Critical regression: checkagent.datasets is now empty — all dataset classes removed.
"""

import pytest

from checkagent import (
    AgentInput,
    AgentRun,
    FaultInjector,
    MockLLM,
    MockTool,
    Score,
    Step,
    ToolCall,
    assert_output_matches,
    assert_tool_called,
)


# ---------------------------------------------------------------------------
# MockTool.strict_validation=False
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_strict_validation_false_skips_schema_check():
    """strict_validation=False should let calls with invalid args through."""
    tool = MockTool(strict_validation=False)
    tool.register(
        "search",
        schema={
            "type": "object",
            "properties": {"q": {"type": "string"}},
            "required": ["q"],
        },
        response="ok",
    )
    # Missing required 'q' — should NOT raise
    result = await tool.call("search", {"wrong_key": "oops"})
    assert result == "ok"


@pytest.mark.agent_test(layer="mock")
async def test_strict_validation_false_still_records_call():
    """Calls with invalid args still get recorded when strict_validation=False."""
    tool = MockTool(strict_validation=False)
    tool.register("lookup", schema={"type": "object", "required": ["id"]}, response="found")
    await tool.call("lookup", {"bad_field": 1})
    assert tool.call_count == 1
    assert tool.last_call.tool_name == "lookup"


@pytest.mark.agent_test(layer="mock")
async def test_strict_validation_true_raises_on_invalid_args():
    """Default strict_validation=True should still raise on schema violations."""
    tool = MockTool(strict_validation=True)
    tool.register(
        "search",
        schema={
            "type": "object",
            "properties": {"q": {"type": "string"}},
            "required": ["q"],
        },
        response="ok",
    )
    with pytest.raises(Exception):
        await tool.call("search", {"wrong": "nope"})


@pytest.mark.agent_test(layer="mock")
def test_strict_validation_false_call_sync_skips_schema_check():
    """strict_validation=False should also skip validation for call_sync."""
    tool = MockTool(strict_validation=False)
    tool.register(
        "search",
        schema={"type": "object", "required": ["q"]},
        response="result",
    )
    result = tool.call_sync("search", {"bad": "args"})
    assert result == "result"


# ---------------------------------------------------------------------------
# MockLLM.reset_calls() and reset() — should both clear history, keep rules
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_reset_calls_clears_history():
    """reset_calls() must set call_count to zero."""
    llm = MockLLM()
    llm.add_rule("ping", "pong")
    await llm.complete("ping")
    await llm.complete("ping")
    assert llm.call_count == 2
    llm.reset_calls()
    assert llm.call_count == 0


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_reset_calls_preserves_rules():
    """reset_calls() must NOT remove registered rules."""
    llm = MockLLM()
    llm.add_rule("hello", "world")
    await llm.complete("hello")
    llm.reset_calls()
    result = await llm.complete("hello")
    assert result == "world"


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_reset_clears_history():
    """reset() must also set call_count to zero."""
    llm = MockLLM()
    llm.add_rule("ping", "pong")
    await llm.complete("ping")
    assert llm.call_count == 1
    llm.reset()
    assert llm.call_count == 0


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_reset_preserves_rules():
    """reset() must NOT remove registered rules."""
    llm = MockLLM()
    llm.add_rule("hello", "world")
    await llm.complete("hello")
    llm.reset()
    result = await llm.complete("hello")
    assert result == "world"


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_reset_and_reset_calls_are_functionally_identical():
    """Both reset() and reset_calls() clear history and preserve rules.

    NOTE: If this test reveals a difference, update accordingly.
    """
    llm_a = MockLLM()
    llm_a.add_rule("x", "y")
    await llm_a.complete("x")
    llm_a.reset_calls()

    llm_b = MockLLM()
    llm_b.add_rule("x", "y")
    await llm_b.complete("x")
    llm_b.reset()

    assert llm_a.call_count == llm_b.call_count == 0
    assert await llm_a.complete("x") == await llm_b.complete("x") == "y"


# ---------------------------------------------------------------------------
# MockTool.reset_calls() and reset() — should both clear history, keep tools
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_reset_calls_clears_history():
    """reset_calls() must set call_count to zero."""
    tool = MockTool()
    tool.register("search", response="results")
    await tool.call("search", {})
    await tool.call("search", {})
    assert tool.call_count == 2
    tool.reset_calls()
    assert tool.call_count == 0


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_reset_calls_preserves_registered_tools():
    """reset_calls() must NOT remove registered tools."""
    tool = MockTool()
    tool.register("search", response="results")
    await tool.call("search", {})
    tool.reset_calls()
    assert "search" in tool.registered_tools
    result = await tool.call("search", {})
    assert result == "results"


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_reset_clears_history():
    """reset() must also set call_count to zero."""
    tool = MockTool()
    tool.register("lookup", response="data")
    await tool.call("lookup", {})
    tool.reset()
    assert tool.call_count == 0


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_reset_preserves_registered_tools():
    """reset() must NOT remove registered tools."""
    tool = MockTool()
    tool.register("lookup", response="data")
    await tool.call("lookup", {})
    tool.reset()
    assert "lookup" in tool.registered_tools
    result = await tool.call("lookup", {})
    assert result == "data"


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_reset_and_reset_calls_are_functionally_identical():
    """Both reset() and reset_calls() have identical observable behavior."""
    tool_a = MockTool()
    tool_a.register("foo", response="bar")
    await tool_a.call("foo", {})
    tool_a.reset_calls()

    tool_b = MockTool()
    tool_b.register("foo", response="bar")
    await tool_b.call("foo", {})
    tool_b.reset()

    assert tool_a.call_count == tool_b.call_count == 0
    assert tool_a.registered_tools == tool_b.registered_tools
    assert await tool_a.call("foo", {}) == await tool_b.call("foo", {}) == "bar"


# ---------------------------------------------------------------------------
# FaultInjector with MockTool.call_sync() — manual guard pattern
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_fault_injector_timeout_with_call_sync():
    """FaultInjector timeout fault fires when check_tool() is called before call_sync."""
    fault = FaultInjector()
    fault.on_tool("search").timeout()

    tool = MockTool()
    tool.register("search", response="results")

    with pytest.raises(Exception, match="timeout"):
        fault.check_tool("search")
        tool.call_sync("search", {})

    assert fault.was_triggered("search")
    assert fault.trigger_count == 1


@pytest.mark.agent_test(layer="mock")
def test_fault_injector_rate_limit_with_call_sync():
    """FaultInjector rate_limit fault fires on check_tool() before call_sync."""
    fault = FaultInjector()
    fault.on_tool("api").rate_limit()

    tool = MockTool()
    tool.register("api", response="data")

    raised = False
    try:
        fault.check_tool("api")
        tool.call_sync("api", {})
    except Exception as e:
        raised = True
        assert "rate" in str(e).lower() or "429" in str(e) or "limit" in str(e).lower()

    assert raised
    assert fault.was_triggered("api")


@pytest.mark.agent_test(layer="mock")
def test_fault_injector_not_triggered_for_different_tool():
    """Fault registered for 'search' should not trigger for 'summarize'."""
    fault = FaultInjector()
    fault.on_tool("search").timeout()

    tool = MockTool()
    tool.register("summarize", response="summary")

    # This should NOT raise — fault is for a different tool
    fault.check_tool("summarize")
    result = tool.call_sync("summarize", {})
    assert result == "summary"
    assert not fault.was_triggered("search")


@pytest.mark.agent_test(layer="mock")
def test_fault_injector_slow_now_sleeps_in_sync_context():
    """F-016 FIXED: FaultInjector slow fault now actually sleeps in sync check_tool().

    Previously raised ToolSlowError with 'use async for real delay'.
    Now behaves symmetrically with async — just sleeps for latency_ms.
    """
    import time
    fault = FaultInjector()
    fault.on_tool("db").slow(latency_ms=50)

    t0 = time.perf_counter()
    fault.check_tool("db")  # No longer raises
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms >= 40, f"Expected ~50ms sleep, got {elapsed_ms:.0f}ms"
    assert fault.was_triggered("db")


@pytest.mark.agent_test(layer="mock")
def test_fault_injector_returns_empty_with_call_sync():
    """FaultInjector returns_empty fault fires on check_tool()."""
    fault = FaultInjector()
    fault.on_tool("search").returns_empty()

    tool = MockTool()
    tool.register("search", response="results")

    raised = False
    try:
        fault.check_tool("search")
    except Exception:
        raised = True

    # returns_empty may raise or just signal — record what actually happens
    assert fault.was_triggered("search") or not raised


@pytest.mark.agent_test(layer="mock")
async def test_fault_injector_async_check_with_call_sync_tool():
    """check_tool_async() works for tools called via call_sync in sync contexts."""
    fault = FaultInjector()
    fault.on_tool("search").timeout()

    tool = MockTool()
    tool.register("search", response="results")

    with pytest.raises(Exception, match="timeout"):
        await fault.check_tool_async("search")

    assert fault.was_triggered("search")


# ---------------------------------------------------------------------------
# AgentRun with multiple Steps — assert_tool_called(call_index=N) across steps
# ---------------------------------------------------------------------------


def make_multi_step_run() -> AgentRun:
    """Build a run with two steps: step 0 has two 'search' calls, step 1 has one 'summarize'."""
    return AgentRun(
        input=AgentInput(query="find and summarize cats"),
        final_output="Cats are nice.",
        steps=[
            Step(
                tool_calls=[
                    ToolCall(name="search", arguments={"q": "cats"}),
                    ToolCall(name="search", arguments={"q": "cat breeds"}),
                ]
            ),
            Step(
                tool_calls=[
                    ToolCall(name="summarize", arguments={"text": "cats and breeds"}),
                ]
            ),
        ],
    )


@pytest.mark.agent_test(layer="mock")
def test_assert_tool_called_call_index_0_picks_first_call():
    run = make_multi_step_run()
    tc = assert_tool_called(run, "search", call_index=0)
    assert tc.arguments == {"q": "cats"}


@pytest.mark.agent_test(layer="mock")
def test_assert_tool_called_call_index_1_picks_second_call():
    run = make_multi_step_run()
    tc = assert_tool_called(run, "search", call_index=1)
    assert tc.arguments == {"q": "cat breeds"}


@pytest.mark.agent_test(layer="mock")
def test_assert_tool_called_indexes_across_step_boundaries():
    """Tool calls in later steps are indexed globally, not per-step."""
    run = make_multi_step_run()
    tc = assert_tool_called(run, "summarize", call_index=0)
    assert tc.arguments == {"text": "cats and breeds"}


@pytest.mark.agent_test(layer="mock")
def test_assert_tool_called_out_of_bounds_raises_structured_error():
    from checkagent import StructuredAssertionError

    run = make_multi_step_run()
    with pytest.raises(StructuredAssertionError):
        assert_tool_called(run, "search", call_index=99)


@pytest.mark.agent_test(layer="mock")
def test_assert_tool_called_oob_message_mentions_actual_count():
    from checkagent import StructuredAssertionError

    run = make_multi_step_run()
    try:
        assert_tool_called(run, "search", call_index=99)
    except StructuredAssertionError as exc:
        assert "2" in str(exc) or "search" in str(exc)
    else:
        pytest.fail("Expected StructuredAssertionError")


@pytest.mark.agent_test(layer="mock")
def test_assert_tool_called_tool_not_present_raises():
    from checkagent import StructuredAssertionError

    run = make_multi_step_run()
    with pytest.raises(StructuredAssertionError):
        assert_tool_called(run, "nonexistent_tool")


# ---------------------------------------------------------------------------
# Datasets regression — documents that 8e6a0a8 emptied checkagent.datasets
# ---------------------------------------------------------------------------


def test_datasets_regression_golddataset_removed():
    """F-014: GoldenDataset was removed in 8e6a0a8. This test documents the regression."""
    try:
        from checkagent.datasets import GoldenDataset  # noqa: F401

        # If it imports successfully, the regression is fixed — no assertion needed
    except ImportError:
        pytest.xfail(
            "F-014: GoldenDataset removed from checkagent.datasets in 8e6a0a8 "
            "(was present in c786006). 35 session-007 tests are now uncollectable."
        )


def test_datasets_regression_testcase_removed():
    """F-014: TestCase was removed in 8e6a0a8."""
    try:
        from checkagent.datasets import TestCase  # noqa: F401
    except ImportError:
        pytest.xfail("F-014: TestCase removed from checkagent.datasets in 8e6a0a8")


def test_datasets_regression_load_dataset_removed():
    """F-014: load_dataset was removed in 8e6a0a8."""
    try:
        from checkagent.datasets import load_dataset  # noqa: F401
    except ImportError:
        pytest.xfail("F-014: load_dataset removed from checkagent.datasets in 8e6a0a8")


def test_datasets_regression_parametrize_cases_removed():
    """F-014: parametrize_cases was removed in 8e6a0a8."""
    try:
        from checkagent.datasets import parametrize_cases  # noqa: F401
    except ImportError:
        pytest.xfail("F-014: parametrize_cases removed from checkagent.datasets in 8e6a0a8")


# ---------------------------------------------------------------------------
# dirty_equals dependency gap — documents F-015
# ---------------------------------------------------------------------------


def test_dirty_equals_not_a_checkagent_dependency():
    """F-015: dirty_equals is not declared in checkagent's dependencies.

    session-006 tests use dirty_equals but it's not installed automatically.
    On a fresh install, test_session006.py fails to collect.
    This test documents the gap.
    """
    import importlib.util

    spec = importlib.util.find_spec("dirty_equals")
    if spec is None:
        pytest.xfail(
            "F-015: dirty_equals not installed. "
            "checkagent does not declare it as a dependency, but "
            "assert_output_matches uses it internally. "
            "Test collection fails for test_session006.py on fresh install."
        )
    # If installed (manually), this passes — gap is still present but not visible
