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
async def test_tool_timeout(ca_fault):
    """FaultInjector should raise ToolTimeoutError."""
    ca_fault.on_tool("search").timeout(5)

    with pytest.raises(ToolTimeoutError):
        ca_fault.check_tool("search")

    assert ca_fault.was_triggered("search")


@pytest.mark.agent_test(layer="mock")
async def test_tool_rate_limit(ca_fault):
    """Rate limit should fire after N successful calls."""
    ca_fault.on_tool("api").rate_limit(after_n=2)

    # First two calls should pass
    ca_fault.check_tool("api")  # call 1 -- ok
    ca_fault.check_tool("api")  # call 2 -- ok

    # Third call should fail
    with pytest.raises(ToolRateLimitError):
        ca_fault.check_tool("api")


@pytest.mark.agent_test(layer="mock")
async def test_llm_context_overflow(ca_fault):
    """LLM context overflow fault should raise."""
    ca_fault.on_llm().context_overflow()

    with pytest.raises(LLMContextOverflowError):
        ca_fault.check_llm()


@pytest.mark.agent_test(layer="mock")
async def test_llm_rate_limit(ca_fault):
    """LLM rate limit after N calls."""
    ca_fault.on_llm().rate_limit(after_n=1)

    ca_fault.check_llm()  # call 1 -- ok

    with pytest.raises(LLMRateLimitError):
        ca_fault.check_llm()  # call 2 -- rate limited


@pytest.mark.agent_test(layer="mock")
async def test_fault_records(ca_fault):
    """FaultInjector should record what happened."""
    ca_fault.on_tool("db").timeout(3)

    with pytest.raises(ToolTimeoutError):
        ca_fault.check_tool("db")

    assert ca_fault.trigger_count == 1
    records = ca_fault.triggered_records
    assert len(records) == 1
    assert records[0].target == "db"


@pytest.mark.agent_test(layer="mock")
async def test_no_fault_for_unconfigured_tool(ca_fault):
    """Tools without faults should pass through cleanly."""
    ca_fault.on_tool("broken").timeout(5)

    # "healthy" has no faults -- should not raise
    ca_fault.check_tool("healthy")

    assert not ca_fault.was_triggered("healthy")
