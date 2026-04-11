"""Session 027 — attach_faults() / ca_fault fixture (F-004 fix).

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
# ca_fault fixture
# ---------------------------------------------------------------------------


def test_ca_fault_fixture_is_fault_injector(ca_fault):
    """ca_fault fixture yields a FaultInjector instance."""
    assert isinstance(ca_fault, FaultInjector)


def test_ca_fault_fixture_starts_clean(ca_fault):
    """ca_fault fixture yields a fresh injector with no history."""
    assert ca_fault.trigger_count == 0
    # Note: was_triggered is a METHOD not a property — must call it
    assert not ca_fault.was_triggered()


def test_ca_fault_was_triggered_is_method_not_property(ca_fault):
    """Regression: was_triggered is a method — fi.was_triggered (no parens) is always truthy."""
    # This is a potential DX trap: forgetting () always returns a bound method (truthy)
    bound_method = ca_fault.was_triggered  # no ()
    assert callable(bound_method), "was_triggered without () returns the bound method itself"
    assert bool(bound_method) is True, "The bound method object is always truthy — a DX trap"

    # The correct usage is fi.was_triggered()
    assert ca_fault.was_triggered() is False  # nothing triggered yet


# ---------------------------------------------------------------------------
# attach_faults on MockTool
# ---------------------------------------------------------------------------


def test_attach_faults_tool_timeout(ca_fault, ca_mock_tool):
    """attach_faults() wires FaultInjector into MockTool — fault fires automatically."""
    ca_fault.on_tool("search").timeout(seconds=0.01)
    ca_mock_tool.register("search", response={"results": []},
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(ca_fault)

    with pytest.raises(ToolTimeoutError):
        ca_mock_tool.call_sync("search", {})


def test_attach_faults_tool_rate_limit(ca_mock_tool):
    """rate_limit fault fires automatically via attach_faults."""
    fi = FaultInjector()
    fi.on_tool("api").rate_limit()
    ca_mock_tool.register("api", response="data",
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(fi)

    with pytest.raises(ToolRateLimitError):
        ca_mock_tool.call_sync("api", {})


def test_attach_faults_tool_intermittent_always_fail(ca_mock_tool):
    """Intermittent fault at fail_rate=1.0 always fires via attach_faults."""
    fi = FaultInjector()
    fi.on_tool("risky").intermittent(fail_rate=1.0)
    ca_mock_tool.register("risky", response="ok",
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(fi)

    with pytest.raises(ToolIntermittentError):
        ca_mock_tool.call_sync("risky", {})


def test_attach_faults_tool_intermittent_never_fail(ca_mock_tool):
    """Intermittent fault at fail_rate=0.0 never fires via attach_faults."""
    fi = FaultInjector()
    fi.on_tool("safe").intermittent(fail_rate=0.0)
    ca_mock_tool.register("safe", response="ok",
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(fi)

    result = ca_mock_tool.call_sync("safe", {})
    assert result == "ok"


def test_attach_faults_returns_empty(ca_mock_tool):
    """returns_empty fault fires via attach_faults."""
    fi = FaultInjector()
    fi.on_tool("fetch").returns_empty()
    ca_mock_tool.register("fetch", response={"data": "value"},
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(fi)

    with pytest.raises(ToolEmptyResponseError):
        ca_mock_tool.call_sync("fetch", {})


def test_attach_faults_returns_malformed(ca_mock_tool):
    """returns_malformed fault fires via attach_faults."""
    fi = FaultInjector()
    fi.on_tool("parser").returns_malformed()
    ca_mock_tool.register("parser", response={"data": "value"},
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(fi)

    with pytest.raises(ToolMalformedResponseError):
        ca_mock_tool.call_sync("parser", {})


# ---------------------------------------------------------------------------
# attach_faults on MockLLM
# ---------------------------------------------------------------------------


def test_attach_faults_llm_server_error_sync(ca_mock_llm):
    """attach_faults wires LLM fault into MockLLM — fires on complete_sync."""
    fi = FaultInjector()
    fi.on_llm().server_error()
    ca_mock_llm.add_rule(".*", "Hello")
    ca_mock_llm.attach_faults(fi)

    with pytest.raises(LLMServerError):
        ca_mock_llm.complete_sync("Tell me something")


@pytest.mark.asyncio
async def test_attach_faults_llm_server_error_async(ca_mock_llm):
    """attach_faults wires LLM fault into MockLLM — fires on async complete."""
    fi = FaultInjector()
    fi.on_llm().server_error()
    ca_mock_llm.add_rule(".*", "Hello")
    ca_mock_llm.attach_faults(fi)

    with pytest.raises(LLMServerError):
        await ca_mock_llm.complete("Tell me something")


def test_attach_faults_llm_rate_limit(ca_mock_llm):
    """LLM rate_limit fault fires via attach_faults."""
    fi = FaultInjector()
    fi.on_llm().rate_limit()
    ca_mock_llm.add_rule(".*", "Hello")
    ca_mock_llm.attach_faults(fi)

    with pytest.raises(LLMRateLimitError):
        ca_mock_llm.complete_sync("Query")


# ---------------------------------------------------------------------------
# Async tool faults via attach_faults
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attach_faults_async_tool_timeout(ca_fault, ca_mock_tool):
    """Async tool.call() also respects faults attached via attach_faults."""
    ca_fault.on_tool("search").timeout(seconds=0.01)
    ca_mock_tool.register("search", response={},
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(ca_fault)

    with pytest.raises(ToolTimeoutError):
        await ca_mock_tool.call("search", {})


@pytest.mark.asyncio
async def test_attach_faults_slow_async_delays(ca_mock_tool):
    """Slow fault via attach_faults causes real async delay (not exception)."""
    fi = FaultInjector()
    fi.on_tool("slow").slow(latency_ms=50)
    ca_mock_tool.register("slow", response="done",
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(fi)

    start = time.perf_counter()
    result = await ca_mock_tool.call("slow", {})
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result == "done"
    assert elapsed_ms >= 40, f"Expected ~50ms delay, got {elapsed_ms:.0f}ms"


def test_attach_faults_slow_sync_now_sleeps(ca_mock_tool):
    """F-016 FIXED: slow fault via attach_faults now actually sleeps in sync path.

    Previously raised ToolSlowError in sync. Now behaves consistently with async.
    """
    import time
    fi = FaultInjector()
    fi.on_tool("slow").slow(latency_ms=50)
    ca_mock_tool.register("slow", response="done",
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(fi)

    # F-016 FIXED: sync slow fault sleeps instead of raising
    t0 = time.time()
    ca_mock_tool.call_sync("slow", {})
    elapsed_ms = (time.time() - t0) * 1000
    assert elapsed_ms >= 40, f"Expected ~50ms delay, got {elapsed_ms:.0f}ms"


# ---------------------------------------------------------------------------
# Scoping — fault only fires for named tool
# ---------------------------------------------------------------------------


def test_attach_faults_only_affects_named_tool(ca_fault, ca_mock_tool):
    """Fault for 'bad_tool' does not affect 'good_tool'."""
    ca_fault.on_tool("bad_tool").timeout()
    ca_mock_tool.register("bad_tool", response="x",
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.register("good_tool", response="ok",
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(ca_fault)

    result = ca_mock_tool.call_sync("good_tool", {})
    assert result == "ok"

    with pytest.raises(ToolTimeoutError):
        ca_mock_tool.call_sync("bad_tool", {})


# ---------------------------------------------------------------------------
# Chaining and overwrite behavior
# ---------------------------------------------------------------------------


def test_attach_faults_returns_self(ca_mock_tool, ca_mock_llm):
    """attach_faults() returns self for builder chaining."""
    fi = FaultInjector()
    assert ca_mock_tool.attach_faults(fi) is ca_mock_tool
    assert ca_mock_llm.attach_faults(fi) is ca_mock_llm


def test_attach_faults_second_call_overwrites_first(ca_mock_tool):
    """Second attach_faults() overwrites the first injector — not additive."""
    fi1 = FaultInjector()
    fi1.on_tool("x").timeout()

    fi2 = FaultInjector()  # no faults

    ca_mock_tool.register("x", response="ok",
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(fi1)
    ca_mock_tool.attach_faults(fi2)  # overwrites fi1

    # fi1 is gone — call should succeed
    result = ca_mock_tool.call_sync("x", {})
    assert result == "ok", "Second attach_faults() overwrites the first (not additive)"


# ---------------------------------------------------------------------------
# Fault records
# ---------------------------------------------------------------------------


def test_attach_faults_records_in_injector(ca_fault, ca_mock_tool):
    """Faults triggered via attach_faults are recorded in the FaultInjector."""
    ca_fault.on_tool("search").timeout()
    ca_mock_tool.register("search", response={},
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(ca_fault)

    try:
        ca_mock_tool.call_sync("search", {})
    except ToolTimeoutError:
        pass

    assert ca_fault.was_triggered()
    assert ca_fault.trigger_count >= 1


def test_attach_faults_persist_through_reset_calls(ca_mock_tool):
    """Attached FaultInjector is not cleared by reset_calls() — faults persist."""
    fi = FaultInjector()
    fi.on_tool("x").timeout()
    ca_mock_tool.register("x", response="ok",
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(fi)

    ca_mock_tool.reset_calls()  # should not detach faults

    with pytest.raises(ToolTimeoutError):
        ca_mock_tool.call_sync("x", {})


def test_attach_faults_persist_through_reset(ca_mock_tool):
    """Attached FaultInjector persists through reset() — faults are not cleared."""
    fi = FaultInjector()
    fi.on_tool("x").timeout()
    ca_mock_tool.register("x", response="ok",
                          schema={"type": "object", "properties": {}})
    ca_mock_tool.attach_faults(fi)

    ca_mock_tool.reset()  # should not detach faults

    with pytest.raises(ToolTimeoutError):
        ca_mock_tool.call_sync("x", {})
