"""
Session-030 tests: F-082 FIXED (on_llm intermittent/slow), F-037 FIXED (check_llm_async),
upstream still green (8 consecutive). Focus: LLM fault parity with tool faults.
"""

import asyncio
import time

import pytest

from checkagent.mock.fault import FaultInjector


# ---------------------------------------------------------------------------
# F-082 FIXED: on_llm() now has intermittent() and slow()
# ---------------------------------------------------------------------------


@pytest.mark.agent_test
def test_f082_fixed_on_llm_intermittent_at_full_rate():
    """on_llm().intermittent(fail_rate=1.0) always raises LLMIntermittentError."""
    from checkagent.mock.fault import LLMIntermittentError

    fi = FaultInjector()
    fi.on_llm().intermittent(fail_rate=1.0, seed=42)

    with pytest.raises(LLMIntermittentError):
        fi.check_llm()


@pytest.mark.agent_test
def test_f082_fixed_on_llm_intermittent_at_zero_rate():
    """on_llm().intermittent(fail_rate=0.0) never raises."""
    fi = FaultInjector()
    fi.on_llm().intermittent(fail_rate=0.0, seed=42)

    fi.check_llm()  # Should not raise
    assert not fi.triggered


@pytest.mark.agent_test
def test_f082_fixed_on_llm_slow_sync_raises():
    """on_llm().slow() with check_llm() sync raises LLMSlowError (consistent with tool behavior)."""
    from checkagent.mock.fault import LLMSlowError

    fi = FaultInjector()
    fi.on_llm().slow(latency_ms=50)

    with pytest.raises(LLMSlowError) as exc_info:
        fi.check_llm()

    assert "50" in str(exc_info.value) or "slow" in str(exc_info.value).lower()


@pytest.mark.agent_test
async def test_f082_fixed_on_llm_slow_async_real_delay():
    """on_llm().slow() with check_llm_async() produces real latency, no exception."""
    fi = FaultInjector()
    fi.on_llm().slow(latency_ms=60)

    t0 = time.perf_counter()
    await fi.check_llm_async()
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms >= 50, f"Expected >=50ms delay, got {elapsed_ms:.1f}ms"
    assert fi.triggered, "slow async should set triggered=True"


@pytest.mark.agent_test
def test_f082_fixed_llm_intermittent_triggers_correctly():
    """LLM intermittent sets triggered/trigger_count correctly."""
    from checkagent.mock.fault import LLMIntermittentError

    fi = FaultInjector()
    fi.on_llm().intermittent(fail_rate=1.0, seed=99)

    assert not fi.triggered
    assert fi.trigger_count == 0

    with pytest.raises(LLMIntermittentError):
        fi.check_llm()

    assert fi.triggered
    assert fi.trigger_count == 1


@pytest.mark.agent_test
def test_f082_fixed_llm_slow_consistent_with_tool_slow():
    """LLM slow (sync) raises, tool slow (sync) also raises — behavior is now symmetric."""
    from checkagent.mock.fault import LLMSlowError, ToolSlowError

    # LLM slow sync
    fi_llm = FaultInjector()
    fi_llm.on_llm().slow(latency_ms=50)
    with pytest.raises(LLMSlowError):
        fi_llm.check_llm()

    # Tool slow sync
    fi_tool = FaultInjector()
    fi_tool.on_tool("my_tool").slow(latency_ms=50)
    with pytest.raises(ToolSlowError):
        fi_tool.check_tool("my_tool")


# ---------------------------------------------------------------------------
# F-037 FIXED: check_llm_async() now exists
# ---------------------------------------------------------------------------


@pytest.mark.agent_test
def test_f037_fixed_check_llm_async_exists():
    """F-037 FIXED: FaultInjector.check_llm_async() now exists."""
    fi = FaultInjector()
    assert hasattr(fi, "check_llm_async"), "check_llm_async should be available"
    assert callable(fi.check_llm_async)


@pytest.mark.agent_test
async def test_f037_fixed_check_llm_async_no_faults():
    """check_llm_async() with no faults configured completes without raising."""
    fi = FaultInjector()
    await fi.check_llm_async()  # Should not raise


@pytest.mark.agent_test
async def test_f037_fixed_check_llm_async_with_intermittent():
    """check_llm_async() applies intermittent LLM faults correctly."""
    from checkagent.mock.fault import LLMIntermittentError

    fi = FaultInjector()
    fi.on_llm().intermittent(fail_rate=1.0, seed=77)

    with pytest.raises(LLMIntermittentError):
        await fi.check_llm_async()


# ---------------------------------------------------------------------------
# MockLLM + attach_faults() + new LLM fault types end-to-end
# ---------------------------------------------------------------------------


@pytest.mark.agent_test
async def test_mocklllm_attach_faults_intermittent_llm():
    """MockLLM.attach_faults() with intermittent LLM fault — complete() raises."""
    from checkagent.mock.fault import LLMIntermittentError
    from checkagent.mock.llm import MockLLM

    fi = FaultInjector()
    fi.on_llm().intermittent(fail_rate=1.0, seed=1)

    llm = MockLLM()
    llm.attach_faults(fi)

    with pytest.raises(LLMIntermittentError):
        await llm.complete("anything")

    assert fi.triggered


@pytest.mark.agent_test
async def test_mocklllm_attach_faults_slow_llm_async_real_delay():
    """MockLLM.attach_faults() with slow LLM fault — complete() sleeps then returns."""
    from checkagent.mock.llm import MockLLM

    fi = FaultInjector()
    fi.on_llm().slow(latency_ms=70)

    llm = MockLLM()
    llm.attach_faults(fi)

    t0 = time.perf_counter()
    result = await llm.complete("anything")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms >= 60, f"Expected >=60ms, got {elapsed_ms:.1f}ms"
    assert result is not None  # Still returns a response after delay
    assert fi.triggered


@pytest.mark.agent_test
def test_mocklllm_attach_faults_slow_llm_sync_raises():
    """MockLLM.complete_sync() with slow LLM fault raises LLMSlowError."""
    from checkagent.mock.fault import LLMSlowError
    from checkagent.mock.llm import MockLLM

    fi = FaultInjector()
    fi.on_llm().slow(latency_ms=50)

    llm = MockLLM()
    llm.attach_faults(fi)

    with pytest.raises(LLMSlowError):
        llm.complete_sync("anything")


# ---------------------------------------------------------------------------
# Retry simulation: intermittent LLM with retry loop
# ---------------------------------------------------------------------------


@pytest.mark.agent_test
async def test_intermittent_llm_retry_simulation():
    """
    Realistic scenario: agent retries on LLM failure.
    Simulate: first call fails (rate_limit), second succeeds.
    Uses after_n parameter on rate_limit, not intermittent, to get predictable behavior.
    """
    from checkagent.mock.fault import LLMRateLimitError
    from checkagent.mock.llm import MockLLM

    fi = FaultInjector()
    fi.on_llm().rate_limit(after_n=1)

    llm = MockLLM()
    llm.attach_faults(fi)

    # First call succeeds (n=0, not yet at limit)
    result1 = await llm.complete("query 1")
    assert result1 is not None

    # Second call fails (n=1, at limit)
    with pytest.raises(LLMRateLimitError):
        await llm.complete("query 2")

    # After reset, first call succeeds again
    fi.reset()
    result3 = await llm.complete("query 3")
    assert result3 is not None
