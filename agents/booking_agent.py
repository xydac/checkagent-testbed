"""Booking agent -- a slightly more complex agent that orchestrates tool calls.

Simulates a meeting booking flow:
1. Check calendar availability
2. Create event if available
3. Return confirmation

The agent accepts a MockLLM and MockTool so tests can inject mocks.
"""

from checkagent.adapters.generic import wrap
from checkagent.core.types import AgentRun, AgentInput, Step, ToolCall


async def run_booking(query: str, *, llm=None, tool=None) -> AgentRun:
    """Run the booking agent with injectable LLM and tool mocks.

    This does NOT use the @wrap decorator because we need to build
    an AgentRun with tool call records ourselves. The GenericAdapter
    doesn't know about tools -- it just wraps a callable.

    This is a "customer zero" finding: for agents that use tools,
    GenericAdapter alone isn't enough. You need to build the AgentRun
    manually or use a framework-specific adapter.
    """
    input = AgentInput(query=query)
    steps = []
    tool_calls = []

    # Step 1: Ask LLM what to do
    if llm:
        llm_response = await llm.complete(query)
    else:
        llm_response = "check_calendar"

    # Step 2: Check calendar
    if tool:
        calendar_result = await tool.call(
            "check_calendar", {"date": "2026-04-10", "time": "14:00"}
        )
    else:
        calendar_result = {"available": True}

    tool_calls.append(
        ToolCall(
            name="check_calendar",
            arguments={"date": "2026-04-10", "time": "14:00"},
            result=calendar_result,
        )
    )

    # Step 3: Create event if available
    available = (
        calendar_result.get("available", False)
        if isinstance(calendar_result, dict)
        else False
    )

    if available:
        if tool:
            event_result = await tool.call(
                "create_event",
                {"date": "2026-04-10", "time": "14:00", "title": "Meeting"},
            )
        else:
            event_result = {"event_id": "evt_123", "confirmed": True}

        tool_calls.append(
            ToolCall(
                name="create_event",
                arguments={
                    "date": "2026-04-10",
                    "time": "14:00",
                    "title": "Meeting",
                },
                result=event_result,
            )
        )
        confirmation = f"Meeting booked: {event_result}"
    else:
        confirmation = "Calendar not available"

    steps.append(
        Step(
            step_index=0,
            input_text=query,
            output_text=confirmation,
            tool_calls=tool_calls,
        )
    )

    return AgentRun(
        input=input,
        steps=steps,
        final_output=confirmation,
    )
