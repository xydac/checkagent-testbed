"""Session 027 — attach_faults() / ap_fault fixture (F-004 fix).

F-004 was the longest-open finding: FaultInjector was not wired into MockTool/MockLLM.
Users had to manually call check_tool()/check_llm() in their agent code.
The fix: attach_faults(injector) on MockTool and MockLLM.
"""
import pytest
import asyncio
import time
from checkagent import MockTool, MockLLM, FaultInjector
from checkagent.mock.fault import (
    ToolTimeoutError,
    ToolRateLimitError,
    ToolIntermittentError,
    ToolSlowError,
    ToolEmptyResponseError,
    ToolMalformedResponseError,
    LLMServerError,
    LLMRateLimitError,
)


# ---------------------------------------------------------------------------
# ap_fault fixture
# ---------------------------------------------------------------------------


def test_ap_fault_fixture_is_fault_injector(ap_fault):
    """ap_fault fixture yields a FaultInjector instance."""
    assert isinstance(ap_fault, FaultInjector)


def test_ap_fault_fixture_starts_clean(ap_fault):
    """ap_fault fixture yields a fresh injector with no history."""
    assert ap_fault.trigger_count == 0
    # Note: was_triggered is a METHOD not a property — must call it
    assert not ap_fault.was_triggered()


def test_ap_fault_was_triggered_is_method_not_property(ap_fault):
    """Regression: was_triggered is a method — fi.was_triggered (no parens) is always truthy."""
    # This is a potential DX trap: forgetting () always returns a bound method (truthy)
    bound_method = ap_fault.was_triggered  # no ()
    assert callable(bound_method), "was_triggered without () returns the bound method itself"
    assert bool(bound_method) is True, "The bound method object is always truthy — a DX trap"

    # The correct usage is fi.was_triggered()
    assert ap_fault.was_triggered() is False  # nothing triggered yet


# ---------------------------------------------------------------------------
# attach_faults on MockTool
# ---------------------------------------------------------------------------


def test_attach_faults_tool_timeout(ap_fault, ap_mock_tool):
    """attach_faults() wires FaultInjector into MockTool — fault fires automatically."""
    ap_fault.on_tool("search").timeout(seconds=0.01)
    ap_mock_tool.register("search", response={"results": []},
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(ap_fault)

    with pytest.raises(ToolTimeoutError):
        ap_mock_tool.call_sync("search", {})


def test_attach_faults_tool_rate_limit(ap_mock_tool):
    """rate_limit fault fires automatically via attach_faults."""
    fi = FaultInjector()
    fi.on_tool("api").rate_limit()
    ap_mock_tool.register("api", response="data",
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(fi)

    with pytest.raises(ToolRateLimitError):
        ap_mock_tool.call_sync("api", {})


def test_attach_faults_tool_intermittent_always_fail(ap_mock_tool):
    """Intermittent fault at fail_rate=1.0 always fires via attach_faults."""
    fi = FaultInjector()
    fi.on_tool("risky").intermittent(fail_rate=1.0)
    ap_mock_tool.register("risky", response="ok",
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(fi)

    with pytest.raises(ToolIntermittentError):
        ap_mock_tool.call_sync("risky", {})


def test_attach_faults_tool_intermittent_never_fail(ap_mock_tool):
    """Intermittent fault at fail_rate=0.0 never fires via attach_faults."""
    fi = FaultInjector()
    fi.on_tool("safe").intermittent(fail_rate=0.0)
    ap_mock_tool.register("safe", response="ok",
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(fi)

    result = ap_mock_tool.call_sync("safe", {})
    assert result == "ok"


def test_attach_faults_returns_empty(ap_mock_tool):
    """returns_empty fault fires via attach_faults."""
    fi = FaultInjector()
    fi.on_tool("fetch").returns_empty()
    ap_mock_tool.register("fetch", response={"data": "value"},
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(fi)

    with pytest.raises(ToolEmptyResponseError):
        ap_mock_tool.call_sync("fetch", {})


def test_attach_faults_returns_malformed(ap_mock_tool):
    """returns_malformed fault fires via attach_faults."""
    fi = FaultInjector()
    fi.on_tool("parser").returns_malformed()
    ap_mock_tool.register("parser", response={"data": "value"},
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(fi)

    with pytest.raises(ToolMalformedResponseError):
        ap_mock_tool.call_sync("parser", {})


# ---------------------------------------------------------------------------
# attach_faults on MockLLM
# ---------------------------------------------------------------------------


def test_attach_faults_llm_server_error_sync(ap_mock_llm):
    """attach_faults wires LLM fault into MockLLM — fires on complete_sync."""
    fi = FaultInjector()
    fi.on_llm().server_error()
    ap_mock_llm.add_rule(".*", "Hello")
    ap_mock_llm.attach_faults(fi)

    with pytest.raises(LLMServerError):
        ap_mock_llm.complete_sync("Tell me something")


@pytest.mark.asyncio
async def test_attach_faults_llm_server_error_async(ap_mock_llm):
    """attach_faults wires LLM fault into MockLLM — fires on async complete."""
    fi = FaultInjector()
    fi.on_llm().server_error()
    ap_mock_llm.add_rule(".*", "Hello")
    ap_mock_llm.attach_faults(fi)

    with pytest.raises(LLMServerError):
        await ap_mock_llm.complete("Tell me something")


def test_attach_faults_llm_rate_limit(ap_mock_llm):
    """LLM rate_limit fault fires via attach_faults."""
    fi = FaultInjector()
    fi.on_llm().rate_limit()
    ap_mock_llm.add_rule(".*", "Hello")
    ap_mock_llm.attach_faults(fi)

    with pytest.raises(LLMRateLimitError):
        ap_mock_llm.complete_sync("Query")


# ---------------------------------------------------------------------------
# Async tool faults via attach_faults
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attach_faults_async_tool_timeout(ap_fault, ap_mock_tool):
    """Async tool.call() also respects faults attached via attach_faults."""
    ap_fault.on_tool("search").timeout(seconds=0.01)
    ap_mock_tool.register("search", response={},
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(ap_fault)

    with pytest.raises(ToolTimeoutError):
        await ap_mock_tool.call("search", {})


@pytest.mark.asyncio
async def test_attach_faults_slow_async_delays(ap_mock_tool):
    """Slow fault via attach_faults causes real async delay (not exception)."""
    fi = FaultInjector()
    fi.on_tool("slow").slow(latency_ms=50)
    ap_mock_tool.register("slow", response="done",
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(fi)

    start = time.perf_counter()
    result = await ap_mock_tool.call("slow", {})
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result == "done"
    assert elapsed_ms >= 40, f"Expected ~50ms delay, got {elapsed_ms:.0f}ms"


def test_attach_faults_slow_sync_raises_tool_slow_error(ap_mock_tool):
    """Slow fault via attach_faults still raises ToolSlowError in sync paths (F-016 persists)."""
    fi = FaultInjector()
    fi.on_tool("slow").slow(latency_ms=50)
    ap_mock_tool.register("slow", response="done",
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(fi)

    # F-016: sync call raises instead of sleeping
    with pytest.raises(ToolSlowError, match="use async for real delay"):
        ap_mock_tool.call_sync("slow", {})


# ---------------------------------------------------------------------------
# Scoping — fault only fires for named tool
# ---------------------------------------------------------------------------


def test_attach_faults_only_affects_named_tool(ap_fault, ap_mock_tool):
    """Fault for 'bad_tool' does not affect 'good_tool'."""
    ap_fault.on_tool("bad_tool").timeout()
    ap_mock_tool.register("bad_tool", response="x",
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.register("good_tool", response="ok",
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(ap_fault)

    result = ap_mock_tool.call_sync("good_tool", {})
    assert result == "ok"

    with pytest.raises(ToolTimeoutError):
        ap_mock_tool.call_sync("bad_tool", {})


# ---------------------------------------------------------------------------
# Chaining and overwrite behavior
# ---------------------------------------------------------------------------


def test_attach_faults_returns_self(ap_mock_tool, ap_mock_llm):
    """attach_faults() returns self for builder chaining."""
    fi = FaultInjector()
    assert ap_mock_tool.attach_faults(fi) is ap_mock_tool
    assert ap_mock_llm.attach_faults(fi) is ap_mock_llm


def test_attach_faults_second_call_overwrites_first(ap_mock_tool):
    """Second attach_faults() overwrites the first injector — not additive."""
    fi1 = FaultInjector()
    fi1.on_tool("x").timeout()

    fi2 = FaultInjector()  # no faults

    ap_mock_tool.register("x", response="ok",
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(fi1)
    ap_mock_tool.attach_faults(fi2)  # overwrites fi1

    # fi1 is gone — call should succeed
    result = ap_mock_tool.call_sync("x", {})
    assert result == "ok", "Second attach_faults() overwrites the first (not additive)"


# ---------------------------------------------------------------------------
# Fault records
# ---------------------------------------------------------------------------


def test_attach_faults_records_in_injector(ap_fault, ap_mock_tool):
    """Faults triggered via attach_faults are recorded in the FaultInjector."""
    ap_fault.on_tool("search").timeout()
    ap_mock_tool.register("search", response={},
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(ap_fault)

    try:
        ap_mock_tool.call_sync("search", {})
    except ToolTimeoutError:
        pass

    assert ap_fault.was_triggered()
    assert ap_fault.trigger_count >= 1


def test_attach_faults_persist_through_reset_calls(ap_mock_tool):
    """Attached FaultInjector is not cleared by reset_calls() — faults persist."""
    fi = FaultInjector()
    fi.on_tool("x").timeout()
    ap_mock_tool.register("x", response="ok",
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(fi)

    ap_mock_tool.reset_calls()  # should not detach faults

    with pytest.raises(ToolTimeoutError):
        ap_mock_tool.call_sync("x", {})


def test_attach_faults_persist_through_reset(ap_mock_tool):
    """Attached FaultInjector persists through reset() — faults are not cleared."""
    fi = FaultInjector()
    fi.on_tool("x").timeout()
    ap_mock_tool.register("x", response="ok",
                          schema={"type": "object", "properties": {}})
    ap_mock_tool.attach_faults(fi)

    ap_mock_tool.reset()  # should not detach faults

    with pytest.raises(ToolTimeoutError):
        ap_mock_tool.call_sync("x", {})
