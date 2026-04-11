"""Session-004 tests: FaultInjector fluent API, StreamCollector rich API,
Conversation.total_steps, Score class, and AgentRun.succeeded/.error."""

import asyncio
import time

import pytest

from checkagent import (
    AgentInput,
    AgentRun,
    Conversation,
    FaultInjector,
    Score,
    Step,
    StreamCollector,
    StreamEvent,
    StreamEventType,
    ToolCall,
)
from checkagent.adapters.generic import GenericAdapter, wrap
from checkagent.mock.fault import (
    LLMContentFilterError,
    LLMContextOverflowError,
    LLMPartialResponseError,
    LLMRateLimitError,
    LLMServerError,
    ToolEmptyResponseError,
    ToolIntermittentError,
    ToolMalformedResponseError,
    ToolRateLimitError,
    ToolSlowError,
    ToolTimeoutError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_simple_run(query: str = "hi", output: str = "ok") -> AgentRun:
    """Return an AgentRun with a single step and no tool calls."""
    inp = AgentInput(query=query)
    step = Step(step_index=0, input_text=query, output_text=output)
    return AgentRun(input=inp, steps=[step], final_output=output)


def make_multistep_run(query: str, n_steps: int) -> AgentRun:
    """Return an AgentRun with n_steps steps."""
    inp = AgentInput(query=query)
    steps = [
        Step(step_index=i, input_text=f"step-{i}", output_text=f"out-{i}")
        for i in range(n_steps)
    ]
    return AgentRun(input=inp, steps=steps, final_output=f"out-{n_steps - 1}")


async def multistep_agent(inp: AgentInput, *, n_steps: int = 2) -> AgentRun:
    return make_multistep_run(inp.query, n_steps=n_steps)


# ---------------------------------------------------------------------------
# FaultInjector — fluent API (F-004 re-check)
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_fault_fluent_on_tool_timeout():
    """on_tool().timeout() raises ToolTimeoutError immediately."""
    fault = FaultInjector()
    fault.on_tool("db").timeout(10)

    with pytest.raises(ToolTimeoutError) as exc_info:
        fault.check_tool("db")

    assert "db" in str(exc_info.value).lower() or exc_info.type is ToolTimeoutError


@pytest.mark.agent_test(layer="mock")
async def test_fault_fluent_on_tool_malformed():
    """on_tool().returns_malformed() raises ToolMalformedResponseError."""
    fault = FaultInjector()
    fault.on_tool("search").returns_malformed(data={"corrupt": True})

    with pytest.raises(ToolMalformedResponseError):
        fault.check_tool("search")


@pytest.mark.agent_test(layer="mock")
async def test_fault_fluent_on_tool_returns_empty():
    """on_tool().returns_empty() raises ToolEmptyResponseError.

    NOTE: method is returns_empty(), not empty() — inconsistent with timeout/slow/rate_limit.
    See F-007 in findings.md.
    """
    fault = FaultInjector()
    fault.on_tool("noop").returns_empty()

    with pytest.raises(ToolEmptyResponseError):
        fault.check_tool("noop")


@pytest.mark.agent_test(layer="mock")
async def test_fault_fluent_on_tool_intermittent_deterministic():
    """Intermittent fault at 100% fail_rate fires every time (seed=0)."""
    fault = FaultInjector()
    fault.on_tool("flaky").intermittent(fail_rate=1.0, seed=0)

    with pytest.raises(ToolIntermittentError):
        fault.check_tool("flaky")


@pytest.mark.agent_test(layer="mock")
async def test_fault_fluent_on_tool_intermittent_never():
    """Intermittent fault at 0% fail_rate never fires."""
    fault = FaultInjector()
    fault.on_tool("stable").intermittent(fail_rate=0.0, seed=42)

    # Should not raise
    for _ in range(5):
        fault.check_tool("stable")


@pytest.mark.agent_test(layer="mock")
async def test_fault_fluent_on_llm_server_error():
    """on_llm().server_error() raises LLMServerError."""
    fault = FaultInjector()
    fault.on_llm().server_error(message="HTTP 503")

    with pytest.raises(LLMServerError) as exc_info:
        fault.check_llm()

    # Check that the message is preserved somewhere in the error
    assert "503" in str(exc_info.value)


@pytest.mark.agent_test(layer="mock")
async def test_fault_fluent_on_llm_content_filter():
    """on_llm().content_filter() raises LLMContentFilterError."""
    fault = FaultInjector()
    fault.on_llm().content_filter()

    with pytest.raises(LLMContentFilterError):
        fault.check_llm()


@pytest.mark.agent_test(layer="mock")
async def test_fault_fluent_on_llm_partial_response():
    """on_llm().partial_response() raises LLMPartialResponseError."""
    fault = FaultInjector()
    fault.on_llm().partial_response()

    with pytest.raises(LLMPartialResponseError):
        fault.check_llm()


@pytest.mark.agent_test(layer="mock")
async def test_fault_fluent_returns_self():
    """Fluent builder methods return the FaultInjector for chaining."""
    fault = FaultInjector()
    returned = fault.on_tool("db").timeout(5)
    assert returned is fault, "on_tool().timeout() should return the FaultInjector"

    returned2 = fault.on_llm().server_error()
    assert returned2 is fault, "on_llm().server_error() should return the FaultInjector"


# ---------------------------------------------------------------------------
# FaultInjector — inspection API
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_fault_has_faults_for():
    """has_faults_for() returns True after configuring a tool fault."""
    fault = FaultInjector()
    fault.on_tool("cache").timeout(1)

    assert fault.has_faults_for("cache")
    assert not fault.has_faults_for("other")


@pytest.mark.agent_test(layer="mock")
async def test_fault_has_llm_faults():
    """has_llm_faults() returns True after configuring an LLM fault."""
    fault = FaultInjector()
    assert not fault.has_llm_faults()

    fault.on_llm().rate_limit(after_n=5)
    assert fault.has_llm_faults()


@pytest.mark.agent_test(layer="mock")
async def test_fault_reset_records_preserves_config():
    """reset_records() clears call history but keeps fault configuration."""
    fault = FaultInjector()
    fault.on_tool("db").timeout(1)

    with pytest.raises(ToolTimeoutError):
        fault.check_tool("db")

    assert fault.trigger_count == 1
    fault.reset_records()

    # Config is still there — another call should still raise
    assert fault.trigger_count == 0
    with pytest.raises(ToolTimeoutError):
        fault.check_tool("db")


@pytest.mark.agent_test(layer="mock")
async def test_fault_full_reset_clears_everything():
    """reset() clears both records and fault configuration."""
    fault = FaultInjector()
    fault.on_tool("db").timeout(1)

    with pytest.raises(ToolTimeoutError):
        fault.check_tool("db")

    fault.reset()

    # After full reset, no faults are configured
    fault.check_tool("db")  # should not raise
    assert fault.trigger_count == 0
    assert not fault.has_faults_for("db")


@pytest.mark.agent_test(layer="mock")
async def test_fault_check_tool_async_slow_no_raise():
    """check_tool_async() with slow fault delays but does NOT raise."""
    fault = FaultInjector()
    fault.on_tool("queue").slow(latency_ms=10)

    # slow fault doesn't raise — it just delays (async version)
    start = time.monotonic()
    await fault.check_tool_async("queue")
    elapsed_ms = (time.monotonic() - start) * 1000
    assert elapsed_ms >= 5, f"Expected at least 5ms delay, got {elapsed_ms:.1f}ms"


@pytest.mark.agent_test(layer="mock")
async def test_fault_check_tool_sync_slow_raises():
    """check_tool() (sync) with slow fault does NOT raise ToolSlowError — F-016 FIXED.

    Previously (buggy): sync slow fault raised ToolSlowError immediately.
    Now (correct): sync slow fault does not raise; it completes normally.
    """
    fault = FaultInjector()
    fault.on_tool("queue").slow(latency_ms=5000)

    # F-016 FIXED: sync slow fault no longer raises ToolSlowError
    fault.check_tool("queue")  # should not raise


# ---------------------------------------------------------------------------
# StreamCollector — rich API
# ---------------------------------------------------------------------------


def _make_stream_events() -> list[StreamEvent]:
    """Build a realistic sequence of StreamEvents with timestamps spaced out."""
    t0 = 1000.0
    return [
        StreamEvent(event_type=StreamEventType.RUN_START, data=None, timestamp=t0),
        StreamEvent(event_type=StreamEventType.STEP_START, data=None, timestamp=t0 + 0.01),
        StreamEvent(event_type=StreamEventType.TOOL_CALL_START, data={"name": "search"}, timestamp=t0 + 0.02),
        StreamEvent(event_type=StreamEventType.TOOL_CALL_END, data={"name": "search"}, timestamp=t0 + 0.03),
        StreamEvent(event_type=StreamEventType.TEXT_DELTA, data="Hello ", timestamp=t0 + 0.1),
        StreamEvent(event_type=StreamEventType.TEXT_DELTA, data="world!", timestamp=t0 + 0.15),
        StreamEvent(event_type=StreamEventType.STEP_END, data=None, timestamp=t0 + 0.2),
        StreamEvent(event_type=StreamEventType.RUN_END, data=None, timestamp=t0 + 0.25),
    ]


async def _async_event_generator(events):
    for e in events:
        yield e


@pytest.mark.agent_test(layer="mock")
async def test_stream_collector_collect_from():
    """collect_from() populates the collector from an async iterator."""
    collector = StreamCollector()
    events = _make_stream_events()
    await collector.collect_from(_async_event_generator(events))

    assert collector.total_events == len(events)


@pytest.mark.agent_test(layer="mock")
async def test_stream_collector_aggregated_text():
    """aggregated_text joins all TEXT_DELTA data."""
    collector = StreamCollector()
    await collector.collect_from(_async_event_generator(_make_stream_events()))

    assert collector.aggregated_text == "Hello world!"


@pytest.mark.agent_test(layer="mock")
async def test_stream_collector_total_chunks():
    """total_chunks counts TEXT_DELTA events."""
    collector = StreamCollector()
    await collector.collect_from(_async_event_generator(_make_stream_events()))

    assert collector.total_chunks == 2


@pytest.mark.agent_test(layer="mock")
async def test_stream_collector_time_to_first_token():
    """time_to_first_token measures RUN_START → first TEXT_DELTA gap."""
    collector = StreamCollector()
    await collector.collect_from(_async_event_generator(_make_stream_events()))

    ttft = collector.time_to_first_token
    assert ttft is not None
    # timestamps: RUN_START at t0, first TEXT_DELTA at t0+0.1
    assert abs(ttft - 0.1) < 0.01, f"Expected ~0.1s, got {ttft}"


@pytest.mark.agent_test(layer="mock")
async def test_stream_collector_time_to_first_token_none_without_run_start():
    """time_to_first_token returns None if RUN_START event is absent."""
    collector = StreamCollector()
    collector.add(StreamEvent(event_type=StreamEventType.TEXT_DELTA, data="hi"))

    assert collector.time_to_first_token is None


@pytest.mark.agent_test(layer="mock")
async def test_stream_collector_tool_call_started():
    """tool_call_started() detects TOOL_CALL_START events by name."""
    collector = StreamCollector()
    await collector.collect_from(_async_event_generator(_make_stream_events()))

    assert collector.tool_call_started("search")
    assert not collector.tool_call_started("unknown")


@pytest.mark.agent_test(layer="mock")
async def test_stream_collector_has_error_false():
    """has_error is False when no ERROR events are present."""
    collector = StreamCollector()
    await collector.collect_from(_async_event_generator(_make_stream_events()))

    assert not collector.has_error


@pytest.mark.agent_test(layer="mock")
async def test_stream_collector_has_error_true():
    """has_error is True when an ERROR event is present."""
    collector = StreamCollector()
    collector.add(StreamEvent(event_type=StreamEventType.ERROR, data="timeout"))

    assert collector.has_error
    assert len(collector.error_events) == 1
    assert collector.error_events[0].data == "timeout"


@pytest.mark.agent_test(layer="mock")
async def test_stream_collector_reset():
    """reset() clears all collected events."""
    collector = StreamCollector()
    await collector.collect_from(_async_event_generator(_make_stream_events()))
    assert collector.total_events > 0

    collector.reset()
    assert collector.total_events == 0
    assert collector.aggregated_text == ""


@pytest.mark.agent_test(layer="mock")
async def test_stream_collector_of_type():
    """of_type() filters to a specific event type."""
    collector = StreamCollector()
    await collector.collect_from(_async_event_generator(_make_stream_events()))

    deltas = collector.of_type(StreamEventType.TEXT_DELTA)
    assert len(deltas) == 2
    assert all(e.event_type == StreamEventType.TEXT_DELTA for e in deltas)


@pytest.mark.agent_test(layer="mock")
async def test_stream_collector_first_of_type():
    """first_of_type() returns the first matching event or None."""
    collector = StreamCollector()
    await collector.collect_from(_async_event_generator(_make_stream_events()))

    first = collector.first_of_type(StreamEventType.TEXT_DELTA)
    assert first is not None
    assert first.data == "Hello "

    missing = collector.first_of_type(StreamEventType.ERROR)
    assert missing is None


@pytest.mark.agent_test(layer="mock")
async def test_ca_stream_collector_fixture(ca_stream_collector):
    """ca_stream_collector fixture provides a fresh StreamCollector each test."""
    assert isinstance(ca_stream_collector, StreamCollector)
    assert ca_stream_collector.total_events == 0

    ca_stream_collector.add(StreamEvent(event_type=StreamEventType.TEXT_DELTA, data="x"))
    assert ca_stream_collector.total_events == 1


# ---------------------------------------------------------------------------
# Conversation.total_steps
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_conversation_total_steps_single_turn():
    """total_steps counts steps from a single-step agent."""

    async def single_step_agent(inp: AgentInput) -> AgentRun:
        return make_multistep_run(inp.query, n_steps=1)

    conv = Conversation(single_step_agent)
    await conv.say("hello")

    assert conv.total_steps == 1


@pytest.mark.agent_test(layer="mock")
async def test_conversation_total_steps_multi_step():
    """total_steps counts all steps across a multi-step agent per turn."""

    async def three_step_agent(inp: AgentInput) -> AgentRun:
        return make_multistep_run(inp.query, n_steps=3)

    conv = Conversation(three_step_agent)
    await conv.say("first")

    assert conv.total_steps == 3


@pytest.mark.agent_test(layer="mock")
async def test_conversation_total_steps_accumulates_across_turns():
    """total_steps sums steps across multiple turns."""

    async def two_step_agent(inp: AgentInput) -> AgentRun:
        return make_multistep_run(inp.query, n_steps=2)

    conv = Conversation(two_step_agent)
    await conv.say("turn one")
    await conv.say("turn two")
    await conv.say("turn three")

    # 3 turns × 2 steps each
    assert conv.total_steps == 6


@pytest.mark.agent_test(layer="mock")
async def test_conversation_total_steps_resets_after_reset():
    """Conversation.reset() zeros out total_steps."""

    async def two_step_agent(inp: AgentInput) -> AgentRun:
        return make_multistep_run(inp.query, n_steps=2)

    conv = Conversation(two_step_agent)
    await conv.say("before reset")
    assert conv.total_steps == 2

    conv.reset()
    assert conv.total_steps == 0


# ---------------------------------------------------------------------------
# Score class
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_score_basic_construction():
    """Score accepts name and value in [0, 1]."""
    s = Score(name="accuracy", value=0.85)
    assert s.name == "accuracy"
    assert s.value == 0.85
    assert s.passed is None  # no threshold set


@pytest.mark.agent_test(layer="mock")
async def test_score_auto_passed_when_above_threshold():
    """Score sets passed=True when value >= threshold."""
    s = Score(name="coherence", value=0.9, threshold=0.8)
    assert s.passed is True


@pytest.mark.agent_test(layer="mock")
async def test_score_auto_passed_false_when_below_threshold():
    """Score sets passed=False when value < threshold."""
    s = Score(name="relevance", value=0.4, threshold=0.6)
    assert s.passed is False


@pytest.mark.agent_test(layer="mock")
async def test_score_exact_threshold_passes():
    """Score sets passed=True when value == threshold (boundary)."""
    s = Score(name="exact", value=0.75, threshold=0.75)
    assert s.passed is True


@pytest.mark.agent_test(layer="mock")
async def test_score_passed_none_without_threshold():
    """Score.passed stays None if no threshold and no explicit passed."""
    s = Score(name="fluency", value=0.6)
    assert s.passed is None


@pytest.mark.agent_test(layer="mock")
async def test_score_explicit_passed_overrides():
    """Explicit passed=True/False is preserved regardless of threshold."""
    s = Score(name="custom", value=0.2, passed=True)
    assert s.passed is True


@pytest.mark.agent_test(layer="mock")
async def test_score_value_out_of_range():
    """Score rejects values outside [0, 1]."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Score(name="bad", value=1.5)

    with pytest.raises(ValidationError):
        Score(name="bad", value=-0.1)


@pytest.mark.agent_test(layer="mock")
async def test_score_with_reason_and_metadata():
    """Score stores optional reason and metadata without error."""
    s = Score(
        name="safety",
        value=1.0,
        threshold=0.95,
        reason="No harmful content detected.",
        metadata={"model": "claude-3", "run_id": "abc123"},
    )
    assert s.passed is True
    assert "harmful" in s.reason
    assert s.metadata["model"] == "claude-3"


# ---------------------------------------------------------------------------
# AgentRun.succeeded and .error
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_agentrun_succeeded_true_by_default():
    """AgentRun.succeeded is True when no error is set."""
    result = make_simple_run()
    assert result.succeeded is True
    assert result.error is None


@pytest.mark.agent_test(layer="mock")
async def test_agentrun_succeeded_false_when_error_set():
    """AgentRun.succeeded is False when error field is populated."""
    inp = AgentInput(query="fail")
    result = AgentRun(input=inp, error="LLM rate limited")
    assert result.succeeded is False
    assert result.error == "LLM rate limited"


@pytest.mark.agent_test(layer="mock")
async def test_agentrun_total_tokens_none_without_token_counts():
    """total_tokens is None when prompt/completion tokens are not set."""
    result = make_simple_run()
    assert result.total_tokens is None


@pytest.mark.agent_test(layer="mock")
async def test_agentrun_total_tokens_sums_when_set():
    """total_tokens sums prompt and completion tokens."""
    inp = AgentInput(query="count tokens")
    result = AgentRun(
        input=inp,
        final_output="hello",
        total_prompt_tokens=100,
        total_completion_tokens=25,
    )
    assert result.total_tokens == 125
