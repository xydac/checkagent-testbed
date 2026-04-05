"""Smoke tests for fault injection."""

import pytest

from checkagent import FaultInjector
from checkagent.mock.fault import (
    ToolTimeoutError,
    ToolRateLimitError,
    LLMContextOverflowError,
    LLMRateLimitError,
)


@pytest.mark.agent_test(layer="mock")
async def test_tool_timeout(ap_fault):
    """FaultInjector should raise ToolTimeoutError."""
    ap_fault.on_tool("search").timeout(5)

    with pytest.raises(ToolTimeoutError):
        ap_fault.check_tool("search")

    assert ap_fault.was_triggered("search")


@pytest.mark.agent_test(layer="mock")
async def test_tool_rate_limit(ap_fault):
    """Rate limit should fire after N successful calls."""
    ap_fault.on_tool("api").rate_limit(after_n=2)

    # First two calls should pass
    ap_fault.check_tool("api")  # call 1 -- ok
    ap_fault.check_tool("api")  # call 2 -- ok

    # Third call should fail
    with pytest.raises(ToolRateLimitError):
        ap_fault.check_tool("api")


@pytest.mark.agent_test(layer="mock")
async def test_llm_context_overflow(ap_fault):
    """LLM context overflow fault should raise."""
    ap_fault.on_llm().context_overflow()

    with pytest.raises(LLMContextOverflowError):
        ap_fault.check_llm()


@pytest.mark.agent_test(layer="mock")
async def test_llm_rate_limit(ap_fault):
    """LLM rate limit after N calls."""
    ap_fault.on_llm().rate_limit(after_n=1)

    ap_fault.check_llm()  # call 1 -- ok

    with pytest.raises(LLMRateLimitError):
        ap_fault.check_llm()  # call 2 -- rate limited


@pytest.mark.agent_test(layer="mock")
async def test_fault_records(ap_fault):
    """FaultInjector should record what happened."""
    ap_fault.on_tool("db").timeout(3)

    with pytest.raises(ToolTimeoutError):
        ap_fault.check_tool("db")

    assert ap_fault.trigger_count == 1
    records = ap_fault.triggered_records
    assert len(records) == 1
    assert records[0].target == "db"


@pytest.mark.agent_test(layer="mock")
async def test_no_fault_for_unconfigured_tool(ap_fault):
    """Tools without faults should pass through cleanly."""
    ap_fault.on_tool("broken").timeout(5)

    # "healthy" has no faults -- should not raise
    ap_fault.check_tool("healthy")

    assert not ap_fault.was_triggered("healthy")
