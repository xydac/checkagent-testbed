"""
Tests for multi-turn Conversation API and remaining session-003 items.

Covers:
- Conversation / ca_conversation fixture (session-003 new feature)
- assert_json_schema with real JSON Schema dicts
- assert_tool_called call_index parameter
- StructuredAssertionError message quality
- checkagent run --layer filtering (tested via pytest.mark inspection)
"""

import pytest
from checkagent import (
    AgentRun,
    AgentInput,
    Conversation,
    Step,
    ToolCall,
    assert_tool_called,
    assert_json_schema,
    StructuredAssertionError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def history_aware_agent(inp: AgentInput) -> AgentRun:
    """Agent that echoes back a reference to the previous turn."""
    history = inp.conversation_history
    if not history:
        response = f"You said: {inp.query}"
    else:
        last_user = next(
            (h["content"] for h in reversed(history) if h["role"] == "user"),
            None,
        )
        response = f'You previously said "{last_user}", now: {inp.query}'
    step = Step(step_index=0, input_text=inp.query, output_text=response, tool_calls=[])
    return AgentRun(input=inp, steps=[step], final_output=response)


async def counter_agent(inp: AgentInput) -> AgentRun:
    """Agent that reports how many turns have happened."""
    turn_number = len([h for h in inp.conversation_history if h["role"] == "user"]) + 1
    response = f"turn {turn_number}"
    step = Step(step_index=0, input_text=inp.query, output_text=response, tool_calls=[])
    return AgentRun(input=inp, steps=[step], final_output=response)


# ---------------------------------------------------------------------------
# ca_conversation fixture tests
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_ca_conversation_is_conversation_factory(ca_conversation):
    """ca_conversation fixture should return the Conversation class itself."""
    assert ca_conversation is Conversation


@pytest.mark.agent_test(layer="mock")
async def test_conversation_single_turn(ca_conversation):
    """A single turn should record the result and increment total_turns."""
    conv = ca_conversation(history_aware_agent)
    result = await conv.say("hello")

    assert conv.total_turns == 1
    assert result.final_output == "You said: hello"
    assert result.succeeded


@pytest.mark.agent_test(layer="mock")
async def test_conversation_two_turns_history_passed(ca_conversation):
    """Second turn should receive history from the first turn."""
    conv = ca_conversation(history_aware_agent)

    await conv.say("first message")
    r2 = await conv.say("second message")

    assert conv.total_turns == 2
    # Second turn should reference the first turn's input
    assert "first message" in r2.final_output


@pytest.mark.agent_test(layer="mock")
async def test_conversation_context_references(ca_conversation):
    """conv.context_references(1, 0) should return True when turn 1 echoes turn 0."""
    conv = ca_conversation(history_aware_agent)

    await conv.say("hello world")
    await conv.say("what did I say?")

    assert conv.context_references(1, 0) is True


@pytest.mark.agent_test(layer="mock")
async def test_conversation_total_turns_counting(ca_conversation):
    """total_turns, last_turn, and last_result should stay consistent."""
    conv = ca_conversation(counter_agent)

    await conv.say("a")
    await conv.say("b")
    await conv.say("c")

    assert conv.total_turns == 3
    assert conv.last_turn.input_text == "c"
    assert conv.last_result.final_output == "turn 3"


@pytest.mark.agent_test(layer="mock")
async def test_conversation_get_turn_by_index(ca_conversation):
    """get_turn(n) should return the n-th turn."""
    conv = ca_conversation(counter_agent)

    await conv.say("first")
    await conv.say("second")

    turn0 = conv.get_turn(0)
    turn1 = conv.get_turn(1)

    assert turn0.input_text == "first"
    assert turn0.output_text == "turn 1"
    assert turn1.input_text == "second"
    assert turn1.output_text == "turn 2"


@pytest.mark.agent_test(layer="mock")
async def test_conversation_get_turn_out_of_range(ca_conversation):
    """get_turn with out-of-range index should raise IndexError."""
    conv = ca_conversation(counter_agent)
    await conv.say("only one turn")

    with pytest.raises(IndexError):
        conv.get_turn(5)


@pytest.mark.agent_test(layer="mock")
async def test_conversation_reset(ca_conversation):
    """reset() should clear all turns and start fresh."""
    conv = ca_conversation(counter_agent)

    await conv.say("turn 1")
    await conv.say("turn 2")
    assert conv.total_turns == 2

    conv.reset()
    assert conv.total_turns == 0
    assert conv.last_turn is None
    assert conv.last_result is None

    # After reset, next say should behave like first turn
    r = await conv.say("after reset")
    assert conv.total_turns == 1
    assert r.final_output == "turn 1"


@pytest.mark.agent_test(layer="mock")
async def test_conversation_turns_property_is_copy(ca_conversation):
    """conv.turns should return a copy, not the internal list."""
    conv = ca_conversation(counter_agent)
    await conv.say("a")

    turns = conv.turns
    turns.clear()  # mutating the returned list should not affect the conversation

    assert conv.total_turns == 1


@pytest.mark.agent_test(layer="mock")
async def test_conversation_tool_was_called_across_turns(ca_conversation):
    """tool_was_called should aggregate across all turns."""

    async def tool_calling_agent(inp: AgentInput) -> AgentRun:
        tc = ToolCall(name="search", arguments={"q": inp.query}, result="ok")
        step = Step(
            step_index=0,
            input_text=inp.query,
            output_text="searched",
            tool_calls=[tc],
        )
        return AgentRun(input=inp, steps=[step], final_output="searched")

    conv = ca_conversation(tool_calling_agent)

    await conv.say("first query")
    await conv.say("second query")

    assert conv.total_tool_calls == 2
    assert conv.tool_was_called("search") is True
    assert conv.tool_was_called("nonexistent") is False
    assert len(conv.all_tool_calls) == 2


@pytest.mark.agent_test(layer="mock")
async def test_conversation_tool_was_called_in_turn(ca_conversation):
    """tool_was_called_in_turn checks a specific turn only."""

    call_count = [0]

    async def sometimes_calls_tool(inp: AgentInput) -> AgentRun:
        call_count[0] += 1
        if call_count[0] == 1:
            tc = ToolCall(name="lookup", arguments={}, result="found")
            step = Step(
                step_index=0,
                input_text=inp.query,
                output_text="done",
                tool_calls=[tc],
            )
        else:
            step = Step(
                step_index=0,
                input_text=inp.query,
                output_text="done",
                tool_calls=[],
            )
        return AgentRun(input=inp, steps=[step], final_output="done")

    conv = ca_conversation(sometimes_calls_tool)

    await conv.say("first")   # calls lookup
    await conv.say("second")  # no tool

    assert conv.tool_was_called_in_turn(0, "lookup") is True
    assert conv.tool_was_called_in_turn(1, "lookup") is False


# ---------------------------------------------------------------------------
# assert_json_schema tests
# ---------------------------------------------------------------------------

BOOKING_SCHEMA = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "confirmed": {"type": "boolean"},
        "seats": {"type": "integer", "minimum": 1},
    },
    "required": ["event_id", "confirmed"],
    "additionalProperties": False,
}


@pytest.mark.agent_test(layer="mock")
async def test_assert_json_schema_valid_dict():
    """assert_json_schema passes for a valid dict against a JSON Schema."""
    assert_json_schema(
        {"event_id": "evt_200", "confirmed": True},
        BOOKING_SCHEMA,
    )


@pytest.mark.agent_test(layer="mock")
async def test_assert_json_schema_valid_with_optional_field():
    """Optional fields that meet constraints should pass."""
    assert_json_schema(
        {"event_id": "evt_201", "confirmed": False, "seats": 3},
        BOOKING_SCHEMA,
    )


@pytest.mark.agent_test(layer="mock")
async def test_assert_json_schema_valid_json_string():
    """assert_json_schema should accept a JSON string as input."""
    import json
    assert_json_schema(
        json.dumps({"event_id": "evt_202", "confirmed": True}),
        BOOKING_SCHEMA,
    )


@pytest.mark.agent_test(layer="mock")
async def test_assert_json_schema_missing_required():
    """Missing required field raises StructuredAssertionError with path info."""
    with pytest.raises(StructuredAssertionError) as exc_info:
        assert_json_schema({"event_id": "evt_203"}, BOOKING_SCHEMA)

    err = exc_info.value
    assert "confirmed" in str(err)
    assert "required" in str(err).lower()


@pytest.mark.agent_test(layer="mock")
async def test_assert_json_schema_wrong_type():
    """Wrong field type raises StructuredAssertionError naming the field and path."""
    with pytest.raises(StructuredAssertionError) as exc_info:
        assert_json_schema(
            {"event_id": "evt_204", "confirmed": "yes"},  # confirmed should be bool
            BOOKING_SCHEMA,
        )

    err = exc_info.value
    assert "confirmed" in str(err)
    assert "boolean" in str(err).lower()


@pytest.mark.agent_test(layer="mock")
async def test_assert_json_schema_minimum_violation():
    """Integer below minimum raises StructuredAssertionError with path info."""
    with pytest.raises(StructuredAssertionError) as exc_info:
        assert_json_schema(
            {"event_id": "evt_205", "confirmed": True, "seats": 0},
            BOOKING_SCHEMA,
        )

    err = exc_info.value
    assert "seats" in str(err)
    assert "minimum" in str(err).lower()


@pytest.mark.agent_test(layer="mock")
async def test_assert_json_schema_additional_properties_rejected():
    """Extra properties rejected when additionalProperties is False."""
    with pytest.raises(StructuredAssertionError):
        assert_json_schema(
            {"event_id": "evt_206", "confirmed": True, "surprise": "field"},
            BOOKING_SCHEMA,
        )


# ---------------------------------------------------------------------------
# assert_tool_called call_index tests
# ---------------------------------------------------------------------------

def _run_with_two_search_calls() -> AgentRun:
    """Build an AgentRun with two calls to the same 'search' tool."""
    tc1 = ToolCall(name="search", arguments={"q": "first query"}, result="result1")
    tc2 = ToolCall(name="search", arguments={"q": "second query"}, result="result2")
    step = Step(
        step_index=0,
        input_text="search twice",
        output_text="done",
        tool_calls=[tc1, tc2],
    )
    return AgentRun(
        input=AgentInput(query="search twice"),
        steps=[step],
        final_output="done",
    )


@pytest.mark.agent_test(layer="mock")
async def test_assert_tool_called_call_index_0():
    """call_index=0 selects the first call."""
    run = _run_with_two_search_calls()
    tc = assert_tool_called(run, "search", call_index=0)
    assert tc.arguments["q"] == "first query"


@pytest.mark.agent_test(layer="mock")
async def test_assert_tool_called_call_index_1():
    """call_index=1 selects the second call."""
    run = _run_with_two_search_calls()
    tc = assert_tool_called(run, "search", call_index=1)
    assert tc.arguments["q"] == "second query"


@pytest.mark.agent_test(layer="mock")
async def test_assert_tool_called_call_index_out_of_range():
    """call_index beyond the number of calls raises StructuredAssertionError."""
    run = _run_with_two_search_calls()
    with pytest.raises(StructuredAssertionError) as exc_info:
        assert_tool_called(run, "search", call_index=2)

    err = str(exc_info.value)
    assert "2" in err  # mentions the requested index
    assert "search" in err


# ---------------------------------------------------------------------------
# StructuredAssertionError message quality
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_structured_assertion_error_wrong_tool_name():
    """Error for missing tool should list what tools were actually called."""
    step = Step(
        step_index=0,
        input_text="test",
        output_text="done",
        tool_calls=[
            ToolCall(name="check_calendar", arguments={"date": "2026-04-10"}, result={})
        ],
    )
    run = AgentRun(
        input=AgentInput(query="test"),
        steps=[step],
        final_output="done",
    )

    with pytest.raises(StructuredAssertionError) as exc_info:
        assert_tool_called(run, "create_event")

    err = exc_info.value
    assert "create_event" in str(err)
    assert "check_calendar" in str(err)  # should mention what WAS called
    assert err.details is not None
    assert "available" in err.details  # key listing what was actually called


@pytest.mark.agent_test(layer="mock")
async def test_structured_assertion_error_arg_mismatch():
    """Error for arg mismatch should show expected vs actual values."""
    step = Step(
        step_index=0,
        input_text="test",
        output_text="done",
        tool_calls=[
            ToolCall(
                name="check_calendar",
                arguments={"date": "2026-04-10"},
                result={},
            )
        ],
    )
    run = AgentRun(
        input=AgentInput(query="test"),
        steps=[step],
        final_output="done",
    )

    with pytest.raises(StructuredAssertionError) as exc_info:
        assert_tool_called(run, "check_calendar", date="2026-04-11")

    err = exc_info.value
    assert "2026-04-10" in str(err)  # actual value shown
    assert "2026-04-11" in str(err)  # expected value shown
    assert err.details is not None
