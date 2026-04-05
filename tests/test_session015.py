"""
Session 015 — Regression tracking + async fault exploration.

New commit: ed0b21a. Massive regression: datasets, eval.metrics,
eval.aggregate, eval.evaluator, ci, safety, and cost-tracking modules
have all been stripped from the installed package. Only the core mock
layer (sessions 004-008 coverage) still works.

This session:
- Registers the regression with xfail markers so CI stays green
- Tests FaultInjector.check_tool_async() behavior (F-016 workaround)
- Documents that check_llm_async does NOT exist (gap in async API)
- Tests AgentRun.input strict type enforcement (AgentInput required)
- Confirms intermittent fault fail_rate semantics
"""

import time

import pytest

from checkagent import (
    AgentInput,
    AgentRun,
    FaultInjector,
    MockLLM,
    MockTool,
    Score,
    Step,
)
from checkagent.mock.fault import (
    ToolSlowError,
    ToolIntermittentError,
    LLMServerError,
    LLMRateLimitError,
)

# ---------------------------------------------------------------------------
# Regression markers: features broken in ed0b21a
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="datasets module stripped in ed0b21a (regression)")
def test_regression_datasets_golddataset():
    from checkagent.datasets import GoldenDataset  # noqa: F401


@pytest.mark.xfail(reason="datasets module stripped in ed0b21a (regression)")
def test_regression_datasets_testcase():
    from checkagent.datasets import TestCase  # noqa: F401


@pytest.mark.xfail(reason="eval.metrics module stripped in ed0b21a (regression)")
def test_regression_eval_metrics():
    from checkagent.eval.metrics import task_completion  # noqa: F401


@pytest.mark.xfail(reason="eval.aggregate module stripped in ed0b21a (regression)")
def test_regression_eval_aggregate():
    from checkagent.eval.aggregate import aggregate_scores  # noqa: F401


@pytest.mark.xfail(reason="eval.evaluator module stripped in ed0b21a (regression)")
def test_regression_eval_evaluator():
    from checkagent.eval.evaluator import Evaluator  # noqa: F401


@pytest.mark.xfail(reason="ci module stripped in ed0b21a (regression)")
def test_regression_ci_gate():
    from checkagent.ci import GateResult, GateVerdict  # noqa: F401


@pytest.mark.xfail(reason="ci module stripped in ed0b21a (regression)")
def test_regression_ci_quality_gate_entry():
    from checkagent.ci.quality_gate import QualityGateEntry  # noqa: F401


@pytest.mark.xfail(reason="safety module stripped in ed0b21a (regression)")
def test_regression_safety_detectors():
    from checkagent.safety import PromptInjectionDetector  # noqa: F401


@pytest.mark.xfail(reason="cost tracking stripped in ed0b21a (regression)")
def test_regression_cost_tracker():
    from checkagent import CostTracker  # noqa: F401


@pytest.mark.xfail(reason="cost tracking stripped in ed0b21a (regression)")
def test_regression_cost_budget_exceeded_error():
    from checkagent import BudgetExceededError  # noqa: F401


# ---------------------------------------------------------------------------
# FaultInjector.check_tool_async() — async slow fault (F-016 workaround)
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_check_tool_async_slow_waits_real_latency():
    """check_tool_async() with slow fault actually sleeps — unlike sync version."""
    fault = FaultInjector()
    fault.on_tool("api").slow(latency_ms=80)

    start = time.monotonic()
    await fault.check_tool_async("api")
    elapsed_ms = (time.monotonic() - start) * 1000

    assert elapsed_ms >= 70, f"Expected >=70ms sleep, got {elapsed_ms:.1f}ms"


@pytest.mark.agent_test(layer="mock")
async def test_check_tool_async_slow_does_not_raise():
    """check_tool_async() slow fault completes without exception (unlike sync)."""
    fault = FaultInjector()
    fault.on_tool("api").slow(latency_ms=20)

    # Should NOT raise — real latency instead
    await fault.check_tool_async("api")


@pytest.mark.agent_test(layer="mock")
def test_check_tool_sync_slow_raises_tool_slow_error():
    """sync check_tool() raises ToolSlowError for slow fault (confirmed regression vs async)."""
    fault = FaultInjector()
    fault.on_tool("api").slow(latency_ms=20)

    with pytest.raises(ToolSlowError):
        fault.check_tool("api")


@pytest.mark.agent_test(layer="mock")
async def test_check_tool_async_slow_records_triggered():
    """Async slow fault records trigger in was_triggered / trigger_count."""
    fault = FaultInjector()
    fault.on_tool("db").slow(latency_ms=20)

    await fault.check_tool_async("db")

    assert fault.was_triggered("db") is True
    assert fault.trigger_count == 1


@pytest.mark.agent_test(layer="mock")
async def test_check_tool_async_no_fault_for_other_tool():
    """Async slow fault does NOT fire for a different tool name."""
    fault = FaultInjector()
    fault.on_tool("api").slow(latency_ms=20)

    # Should complete instantly with no fault
    start = time.monotonic()
    await fault.check_tool_async("other_tool")
    elapsed_ms = (time.monotonic() - start) * 1000

    assert elapsed_ms < 50, f"Should be fast for unfaulted tool, got {elapsed_ms:.1f}ms"
    assert fault.was_triggered("api") is False


@pytest.mark.agent_test(layer="mock")
async def test_check_tool_async_timeout_still_raises():
    """check_tool_async() still raises for non-slow faults like timeout."""
    fault = FaultInjector()
    fault.on_tool("api").timeout()

    with pytest.raises(Exception):
        await fault.check_tool_async("api")


@pytest.mark.agent_test(layer="mock")
async def test_check_tool_async_rate_limit_still_raises():
    """check_tool_async() raises for rate_limit fault."""
    fault = FaultInjector()
    fault.on_tool("api").rate_limit(after_n=0)

    with pytest.raises(Exception):
        await fault.check_tool_async("api")


# ---------------------------------------------------------------------------
# No check_llm_async — gap in async API
# ---------------------------------------------------------------------------


def test_no_check_llm_async_method():
    """FaultInjector does NOT have check_llm_async — only check_tool_async."""
    fault = FaultInjector()
    assert not hasattr(fault, "check_llm_async"), (
        "check_llm_async was added — update xfail and findings"
    )


def test_check_llm_sync_works_for_llm_faults():
    """check_llm() (sync) raises for LLM server_error fault."""
    fault = FaultInjector()
    fault.on_llm().server_error()

    with pytest.raises(LLMServerError):
        fault.check_llm()


def test_check_llm_sync_works_for_rate_limit():
    """check_llm() (sync) raises for LLM rate_limit fault."""
    fault = FaultInjector()
    fault.on_llm().rate_limit()

    with pytest.raises(LLMRateLimitError):
        fault.check_llm()


# ---------------------------------------------------------------------------
# FaultInjector.intermittent() — fail_rate semantics
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_intermittent_fail_rate_1_always_raises():
    """intermittent(fail_rate=1.0) always raises ToolIntermittentError."""
    fault = FaultInjector()
    fault.on_tool("api").intermittent(fail_rate=1.0)

    for _ in range(3):
        with pytest.raises(ToolIntermittentError):
            fault.check_tool("api")


@pytest.mark.agent_test(layer="mock")
def test_intermittent_fail_rate_0_never_raises():
    """intermittent(fail_rate=0.0) never raises — always passes through."""
    fault = FaultInjector()
    fault.on_tool("api").intermittent(fail_rate=0.0)

    for _ in range(3):
        fault.check_tool("api")  # Should not raise


@pytest.mark.agent_test(layer="mock")
async def test_intermittent_async_fail_rate_1_always_raises():
    """Async: intermittent(fail_rate=1.0) raises ToolIntermittentError."""
    fault = FaultInjector()
    fault.on_tool("api").intermittent(fail_rate=1.0)

    with pytest.raises(ToolIntermittentError):
        await fault.check_tool_async("api")


@pytest.mark.agent_test(layer="mock")
def test_intermittent_with_seed_is_deterministic():
    """intermittent(fail_rate=0.5, seed=42) produces deterministic results."""
    fault1 = FaultInjector()
    fault1.on_tool("api").intermittent(fail_rate=0.5, seed=42)

    fault2 = FaultInjector()
    fault2.on_tool("api").intermittent(fail_rate=0.5, seed=42)

    results1 = []
    results2 = []
    for _ in range(10):
        try:
            fault1.check_tool("api")
            results1.append("ok")
        except ToolIntermittentError:
            results1.append("err")

    for _ in range(10):
        try:
            fault2.check_tool("api")
            results2.append("ok")
        except ToolIntermittentError:
            results2.append("err")

    assert results1 == results2, "Same seed should produce same results"


# ---------------------------------------------------------------------------
# AgentRun.input strict typing
# ---------------------------------------------------------------------------


def test_agentrun_input_requires_agentinput():
    """AgentRun.input is typed AgentInput — plain str raises ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AgentRun(input="find cats", final_output="result")


def test_agentrun_input_accepts_agentinput():
    """AgentRun.input accepts AgentInput instances."""
    inp = AgentInput(query="find cats")
    run = AgentRun(input=inp, final_output="cats found")
    assert run.input.query == "find cats"


def test_agentrun_input_accepts_dict_coercion():
    """AgentRun.input coerces dict to AgentInput via Pydantic."""
    run = AgentRun(input={"query": "find dogs"}, final_output="dogs found")
    assert run.input.query == "find dogs"


def test_agentrun_input_agentinput_context_preserved():
    """AgentInput context dict is preserved through AgentRun."""
    inp = AgentInput(query="search", context={"user_id": "abc"})
    run = AgentRun(input=inp, final_output="ok")
    assert run.input.context == {"user_id": "abc"}


# ---------------------------------------------------------------------------
# Verify core mock layer unaffected by regression
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_core_mock_llm_still_works():
    """MockLLM basic usage still works in ed0b21a."""
    llm = MockLLM()
    llm.add_rule("hello", "world")
    response = await llm.complete("hello")
    assert response == "world"


@pytest.mark.agent_test(layer="mock")
def test_core_mock_tool_still_works():
    """MockTool.call_sync() returns response value directly (not ToolCallRecord)."""
    tool = MockTool()
    tool.register("search", response={"results": ["a", "b"]})
    result = tool.call_sync("search", {"query": "cats"})
    assert result == {"results": ["a", "b"]}
    # ToolCallRecord is in tool.calls/.last_call, not the return value
    assert tool.last_call.result == {"results": ["a", "b"]}


@pytest.mark.agent_test(layer="mock")
def test_core_score_still_works():
    """Score still works in ed0b21a."""
    s = Score(name="accuracy", value=0.9, threshold=0.8)
    assert s.passed is True
