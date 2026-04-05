"""Smoke tests for the booking agent using MockTool."""

import pytest

from agents.booking_agent import run_booking


@pytest.mark.agent_test(layer="mock")
async def test_booking_happy_path(ap_mock_llm, ap_mock_tool):
    """Full booking flow with mocked tools."""
    ap_mock_llm.add_rule("book", "check_calendar")
    ap_mock_tool.register("check_calendar", response={"available": True})
    ap_mock_tool.register(
        "create_event",
        response={"event_id": "evt_001", "confirmed": True},
    )

    result = await run_booking(
        "Book a meeting for April 10 at 2pm",
        llm=ap_mock_llm,
        tool=ap_mock_tool,
    )

    assert result.succeeded
    assert result.tool_was_called("check_calendar")
    assert result.tool_was_called("create_event")

    # Also check via MockTool's own assertion helpers
    ap_mock_tool.assert_tool_called("check_calendar", with_args={"date": "2026-04-10"})
    ap_mock_tool.assert_tool_called("create_event", with_args={"title": "Meeting"})


@pytest.mark.agent_test(layer="mock")
async def test_booking_tool_call_order(ap_mock_llm, ap_mock_tool):
    """Tools should be called in the right order: calendar first, then event."""
    ap_mock_llm.add_rule("book", "check_calendar")
    ap_mock_tool.register("check_calendar", response={"available": True})
    ap_mock_tool.register(
        "create_event",
        response={"event_id": "evt_002", "confirmed": True},
    )

    result = await run_booking(
        "Book a meeting",
        llm=ap_mock_llm,
        tool=ap_mock_tool,
    )

    calls = ap_mock_tool.calls
    assert len(calls) == 2
    assert calls[0].tool_name == "check_calendar"
    assert calls[1].tool_name == "create_event"


@pytest.mark.agent_test(layer="mock")
async def test_booking_unavailable(ap_mock_llm, ap_mock_tool):
    """When calendar is not available, create_event should NOT be called."""
    ap_mock_llm.add_rule("book", "check_calendar")
    ap_mock_tool.register("check_calendar", response={"available": False})
    ap_mock_tool.register("create_event", response={"event_id": "evt_003", "confirmed": True})

    result = await run_booking(
        "Book a meeting",
        llm=ap_mock_llm,
        tool=ap_mock_tool,
    )

    assert result.succeeded
    assert result.final_output == "Calendar not available"
    ap_mock_tool.assert_tool_called("check_calendar")
    ap_mock_tool.assert_tool_not_called("create_event")


@pytest.mark.agent_test(layer="mock")
async def test_booking_records_tool_calls_in_agentrun(ap_mock_llm, ap_mock_tool):
    """AgentRun should contain the tool call records in its steps."""
    ap_mock_llm.add_rule("book", "check_calendar")
    ap_mock_tool.register("check_calendar", response={"available": True})
    ap_mock_tool.register("create_event", response={"event_id": "evt_004", "confirmed": True})

    result = await run_booking(
        "Book a meeting",
        llm=ap_mock_llm,
        tool=ap_mock_tool,
    )

    all_tool_calls = result.tool_calls
    assert len(all_tool_calls) == 2
    assert all_tool_calls[0].name == "check_calendar"
    assert all_tool_calls[1].name == "create_event"
    assert all_tool_calls[1].result == {"event_id": "evt_004", "confirmed": True}
