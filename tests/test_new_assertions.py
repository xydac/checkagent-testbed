"""
Tests for new assertion features added in session-002.

Covers:
- assert_tool_called as top-level function (F-002 fix)
- assert_output_schema with Pydantic models
- assert_output_matches for fuzzy matching
- run_stream for streaming support
"""

import pytest
from pydantic import BaseModel

from checkagent import (
    AgentRun,
    Step,
    ToolCall,
    assert_tool_called,
    assert_output_schema,
    assert_output_matches,
    StructuredAssertionError,
)
from checkagent.adapters.generic import GenericAdapter
from agents.booking_agent import run_booking


# --- assert_tool_called (top-level) ---


@pytest.mark.agent_test(layer="mock")
async def test_assert_tool_called_top_level_happy_path(ap_mock_llm, ap_mock_tool):
    """assert_tool_called as a free function should match calls in AgentRun."""
    ap_mock_llm.add_rule("book", "check_calendar")
    ap_mock_tool.register("check_calendar", response={"available": True})
    ap_mock_tool.register("create_event", response={"event_id": "evt_007", "confirmed": True})

    result = await run_booking("Book a meeting", llm=ap_mock_llm, tool=ap_mock_tool)

    # Top-level assert_tool_called should work the same as MockTool.assert_tool_called
    assert_tool_called(result, "check_calendar")
    assert_tool_called(result, "create_event")


@pytest.mark.agent_test(layer="mock")
async def test_assert_tool_called_with_args(ap_mock_llm, ap_mock_tool):
    """assert_tool_called should support keyword arg matching."""
    ap_mock_llm.add_rule("book", "check_calendar")
    ap_mock_tool.register("check_calendar", response={"available": True})
    ap_mock_tool.register("create_event", response={"event_id": "evt_008", "confirmed": True})

    result = await run_booking("Book a meeting", llm=ap_mock_llm, tool=ap_mock_tool)

    assert_tool_called(result, "check_calendar", date="2026-04-10")
    assert_tool_called(result, "create_event", title="Meeting")


@pytest.mark.agent_test(layer="mock")
async def test_assert_tool_called_raises_on_missing(ap_mock_llm, ap_mock_tool):
    """assert_tool_called should raise StructuredAssertionError for unmatched tools."""
    ap_mock_llm.add_rule("book", "check_calendar")
    ap_mock_tool.register("check_calendar", response={"available": True})
    ap_mock_tool.register("create_event", response={"event_id": "evt_009", "confirmed": True})

    result = await run_booking("Book a meeting", llm=ap_mock_llm, tool=ap_mock_tool)

    with pytest.raises(StructuredAssertionError):
        assert_tool_called(result, "nonexistent_tool")


@pytest.mark.agent_test(layer="mock")
async def test_assert_tool_called_returns_toolcall(ap_mock_llm, ap_mock_tool):
    """assert_tool_called should return the matched ToolCall for further inspection."""
    ap_mock_llm.add_rule("book", "check_calendar")
    ap_mock_tool.register("check_calendar", response={"available": True})
    ap_mock_tool.register("create_event", response={"event_id": "evt_010", "confirmed": True})

    result = await run_booking("Book a meeting", llm=ap_mock_llm, tool=ap_mock_tool)

    tc = assert_tool_called(result, "create_event")
    assert isinstance(tc, ToolCall)
    assert tc.result == {"event_id": "evt_010", "confirmed": True}


# --- assert_output_schema ---


class BookingConfirmation(BaseModel):
    event_id: str
    confirmed: bool


class EchoResponse(BaseModel):
    text: str
    length: int


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_schema_valid():
    """assert_output_schema should parse valid JSON output into Pydantic model."""
    import json

    # Build an AgentRun with JSON final_output
    output = {"event_id": "evt_100", "confirmed": True}
    run = AgentRun(
        input={"query": "test"},
        steps=[],
        final_output=json.dumps(output),
    )

    result = assert_output_schema(run, BookingConfirmation)
    assert isinstance(result, BookingConfirmation)
    assert result.event_id == "evt_100"
    assert result.confirmed is True


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_schema_invalid_raises():
    """assert_output_schema should raise StructuredAssertionError for invalid output."""
    import json

    # Missing 'confirmed' field
    run = AgentRun(
        input={"query": "test"},
        steps=[],
        final_output=json.dumps({"event_id": "evt_101"}),
    )

    with pytest.raises(StructuredAssertionError):
        assert_output_schema(run, BookingConfirmation)


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_schema_non_json_raises():
    """assert_output_schema should raise on plain-text output when Pydantic model expected."""
    run = AgentRun(
        input={"query": "test"},
        steps=[],
        final_output="Calendar not available",
    )

    with pytest.raises(StructuredAssertionError):
        assert_output_schema(run, BookingConfirmation)


# --- assert_output_matches ---


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_dict():
    """assert_output_matches should match dict output against a pattern."""
    run = AgentRun(
        input={"query": "test"},
        steps=[],
        final_output={"status": "ok", "count": 3},
    )

    # Partial match: only check one field
    assert_output_matches(run, {"status": "ok"})


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_raises_on_mismatch():
    """assert_output_matches should raise on mismatched field."""
    run = AgentRun(
        input={"query": "test"},
        steps=[],
        final_output={"status": "error", "count": 0},
    )

    with pytest.raises(StructuredAssertionError):
        assert_output_matches(run, {"status": "ok"})


# --- run_stream ---


@pytest.mark.agent_test(layer="mock")
async def test_run_stream_yields_events():
    """GenericAdapter.run_stream should yield StreamEvents for a simple agent."""
    from checkagent import StreamEvent, StreamEventType

    async def simple_agent(prompt: str) -> str:
        return f"ECHO: {prompt}"

    adapter = GenericAdapter(simple_agent)
    events = []
    async for event in adapter.run_stream("hello"):
        events.append(event)

    assert len(events) > 0
    assert all(isinstance(e, StreamEvent) for e in events)


@pytest.mark.agent_test(layer="mock")
async def test_run_stream_contains_run_start_and_end():
    """run_stream should emit RUN_START and RUN_END events."""
    from checkagent import StreamEventType

    async def simple_agent(prompt: str) -> str:
        return "done"

    adapter = GenericAdapter(simple_agent)
    event_types = []
    async for event in adapter.run_stream("go"):
        event_types.append(event.event_type)

    assert StreamEventType.RUN_START in event_types
    assert StreamEventType.RUN_END in event_types
