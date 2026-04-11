"""
Session 006 tests — dirty_equals matchers, MockLLM sync/matching, MockTool.call_sync,
MockMCPServer full agent scenario.
"""

import pytest
import asyncio
from checkagent import (
    AgentRun,
    AgentInput,
    MockLLM,
    MockTool,
    MockMCPServer,
    StructuredAssertionError,
    assert_output_matches,
)
from dirty_equals import (
    AnyThing,
    IsApprox,
    IsInstance,
    IsInt,
    IsPositiveInt,
    IsStr,
)


# ---------------------------------------------------------------------------
# assert_output_matches with dirty_equals matchers
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_isstr():
    """IsStr() matcher accepts any string value."""
    run = AgentRun(
        input={"query": "greet"},
        final_output={"message": "Hello, world!", "count": 3},
    )
    assert_output_matches(run, {"message": IsStr()})


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_isstr_regex():
    """IsStr(regex=) matches string by pattern."""
    run = AgentRun(
        input={"query": "search cats"},
        final_output={"message": "Found 42 results for cats"},
    )
    assert_output_matches(run, {"message": IsStr(regex=r"Found \d+ results.*")})


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_isstr_regex_mismatch_raises():
    """IsStr(regex=) raises StructuredAssertionError when regex doesn't match."""
    run = AgentRun(
        input={"query": "search"},
        final_output={"message": "No results found"},
    )
    with pytest.raises(StructuredAssertionError):
        assert_output_matches(run, {"message": IsStr(regex=r"Found \d+ results.*")})


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_isint():
    """IsInt() matcher accepts any integer."""
    run = AgentRun(
        input={"query": "count"},
        final_output={"count": 42, "label": "results"},
    )
    assert_output_matches(run, {"count": IsInt()})


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_isint_on_string_raises():
    """IsInt() raises when value is a string."""
    run = AgentRun(
        input={"query": "count"},
        final_output={"count": "not a number"},
    )
    with pytest.raises(StructuredAssertionError) as exc_info:
        assert_output_matches(run, {"count": IsInt()})
    assert "count" in str(exc_info.value)


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_ispositive_int():
    """IsPositiveInt() rejects zero and negative values."""
    run_positive = AgentRun(
        input={"query": "x"},
        final_output={"score": 5},
    )
    run_zero = AgentRun(
        input={"query": "x"},
        final_output={"score": 0},
    )

    assert_output_matches(run_positive, {"score": IsPositiveInt()})

    with pytest.raises(StructuredAssertionError):
        assert_output_matches(run_zero, {"score": IsPositiveInt()})


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_isapprox():
    """IsApprox(x, delta=d) accepts values within delta of x."""
    run = AgentRun(
        input={"query": "score"},
        final_output={"confidence": 0.95, "threshold": 0.5},
    )
    assert_output_matches(run, {"confidence": IsApprox(1.0, delta=0.1)})


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_isapprox_out_of_range_raises():
    """IsApprox raises when value is outside delta range."""
    run = AgentRun(
        input={"query": "score"},
        final_output={"confidence": 0.5},
    )
    with pytest.raises(StructuredAssertionError):
        assert_output_matches(run, {"confidence": IsApprox(1.0, delta=0.1)})


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_anything():
    """AnyThing() accepts any value including None."""
    run = AgentRun(
        input={"query": "x"},
        final_output={"field1": None, "field2": 42, "field3": "text"},
    )
    assert_output_matches(run, {"field1": AnyThing()})
    assert_output_matches(run, {"field2": AnyThing()})
    assert_output_matches(run, {"field3": AnyThing()})


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_isinstance():
    """IsInstance(T) accepts values of type T."""
    run = AgentRun(
        input={"query": "x"},
        final_output={"count": 7, "label": "ok"},
    )
    assert_output_matches(run, {"count": IsInstance(int)})
    assert_output_matches(run, {"label": IsInstance(str)})


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_multiple_matchers():
    """Multiple dirty_equals matchers can be combined in one pattern dict."""
    run = AgentRun(
        input={"query": "search cats"},
        final_output={
            "status": "ok",
            "count": 42,
            "message": "Found 42 results",
            "confidence": 0.97,
        },
    )
    assert_output_matches(
        run,
        {
            "status": IsStr(),
            "count": IsPositiveInt(),
            "message": IsStr(regex=r"Found \d+ results"),
            "confidence": IsApprox(1.0, delta=0.1),
        },
    )


@pytest.mark.agent_test(layer="mock")
async def test_assert_output_matches_error_names_failing_field():
    """StructuredAssertionError message names the specific field that failed."""
    run = AgentRun(
        input={"query": "x"},
        final_output={"status": "ok", "count": "not_a_number"},
    )
    with pytest.raises(StructuredAssertionError) as exc_info:
        assert_output_matches(run, {"status": IsStr(), "count": IsInt()})
    error_msg = str(exc_info.value)
    assert "count" in error_msg


# ---------------------------------------------------------------------------
# MockLLM.complete_sync() and get_calls_matching()
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_complete_sync_returns_str():
    """complete_sync returns a plain string, same as async complete."""
    llm = MockLLM()
    llm.add_rule("hello", "world")
    result = llm.complete_sync("say hello")
    assert isinstance(result, str)
    assert result == "world"


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_complete_sync_records_call():
    """complete_sync call is recorded in llm.calls."""
    llm = MockLLM()
    llm.add_rule("ping", "pong")
    llm.complete_sync("ping test")
    assert llm.call_count == 1
    assert llm.last_call.input_text == "ping test"
    assert llm.last_call.response_text == "pong"


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_complete_sync_uses_default_when_no_rule():
    """complete_sync falls back to default_response when no rule matches."""
    llm = MockLLM()
    llm.default_response = "fallback"
    result = llm.complete_sync("anything")
    assert result == "fallback"
    assert llm.last_call.was_default is True


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_get_calls_matching_substring():
    """get_calls_matching returns calls whose input_text contains the pattern."""
    llm = MockLLM()
    llm.complete_sync("What is the capital of France?")
    llm.complete_sync("What is the capital of Germany?")
    llm.complete_sync("Tell me a joke")

    france_calls = llm.get_calls_matching("France")
    assert len(france_calls) == 1
    assert france_calls[0].input_text == "What is the capital of France?"

    capital_calls = llm.get_calls_matching("capital")
    assert len(capital_calls) == 2

    no_calls = llm.get_calls_matching("nonexistent")
    assert no_calls == []


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_get_calls_matching_empty_pattern_returns_all():
    """get_calls_matching with empty string returns all calls."""
    llm = MockLLM()
    llm.complete_sync("first")
    llm.complete_sync("second")
    llm.complete_sync("third")

    all_calls = llm.get_calls_matching("")
    assert len(all_calls) == 3


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_was_called_with_requires_exact_match():
    """was_called_with does SUBSTRING matching on input_text — F-009 FIXED.

    Previously (buggy): was_called_with required exact match only.
    Now (correct): was_called_with does substring matching.
    """
    llm = MockLLM()
    llm.complete_sync("What is the capital of France?")

    # substring match: True — F-009 FIXED
    assert llm.was_called_with("capital of France") is True

    # non-matching substring: False
    assert llm.was_called_with("xyz_not_in_input") is False


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_complete_sync_and_async_both_recorded():
    """complete_sync and async complete are tracked in the same calls list."""
    llm = MockLLM()
    llm.add_rule("sync", "sync-response")
    llm.add_rule("async", "async-response")

    llm.complete_sync("sync call")
    await llm.complete("async call")

    assert llm.call_count == 2
    texts = [c.input_text for c in llm.calls]
    assert "sync call" in texts
    assert "async call" in texts


# ---------------------------------------------------------------------------
# MockTool.call_sync()
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_call_sync_returns_configured_response():
    """call_sync returns the response configured with register()."""
    tool = MockTool()
    tool.register("search", response={"results": ["item1", "item2"]})
    result = tool.call_sync("search", {"query": "cats"})
    assert result == {"results": ["item1", "item2"]}


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_call_sync_records_call():
    """call_sync records a ToolCallRecord accessible via .calls and .last_call."""
    tool = MockTool()
    tool.register("lookup", response="found it")
    tool.call_sync("lookup", {"id": "abc123"})

    assert tool.call_count == 1
    assert tool.last_call.tool_name == "lookup"
    assert tool.last_call.arguments == {"id": "abc123"}


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_call_sync_validates_schema():
    """call_sync enforces JSON schema when strict_validation=True (default)."""
    tool = MockTool()
    tool.register(
        "create",
        response="created",
        schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    )

    # valid call succeeds
    result = tool.call_sync("create", {"name": "Alice"})
    assert result == "created"

    # missing required field raises
    with pytest.raises(Exception) as exc_info:
        tool.call_sync("create", {})
    assert "name" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_call_sync_unregistered_tool_raises():
    """call_sync on an unregistered tool name raises an error."""
    tool = MockTool()
    with pytest.raises(Exception) as exc_info:
        tool.call_sync("nonexistent", {})
    assert "nonexistent" in str(exc_info.value)


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_call_sync_failed_calls_recorded():
    """Even failing call_sync attempts are recorded in call history."""
    tool = MockTool()
    tool.register("fetch", response="data")

    # successful call
    tool.call_sync("fetch", None)
    # failed call (unregistered)
    try:
        tool.call_sync("missing", None)
    except Exception:
        pass

    # Both calls are in the history
    assert tool.call_count == 2
    tool_names = [c.tool_name for c in tool.calls]
    assert "fetch" in tool_names
    assert "missing" in tool_names


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_call_sync_and_async_share_call_history():
    """call_sync and async call() both write to the same .calls list."""
    tool = MockTool()
    tool.register("op", response="done")

    tool.call_sync("op", {"source": "sync"})
    await tool.call("op", {"source": "async"})

    assert tool.call_count == 2
    sources = [c.arguments.get("source") for c in tool.calls]
    assert "sync" in sources
    assert "async" in sources


@pytest.mark.agent_test(layer="mock")
async def test_mock_tool_call_sync_assertion_helpers_work():
    """assert_tool_called and assert_tool_not_called work after call_sync.

    F-010 FIXED: MockTool.assert_tool_called() now returns a ToolCallRecord (not None).
    """
    tool = MockTool()
    tool.register("search", response="results")
    tool.call_sync("search", {"query": "cats"})

    # F-010 FIXED: assert_tool_called returns a ToolCallRecord
    result = tool.assert_tool_called("search")
    assert result is not None
    assert hasattr(result, 'tool_name')

    # to inspect call details, use last_call
    assert tool.last_call.tool_name == "search"
    assert tool.last_call.arguments == {"query": "cats"}

    # assert a different tool was NOT called
    tool.assert_tool_not_called("delete")

    # assert a called tool raises when using assert_tool_not_called
    with pytest.raises(Exception):
        tool.assert_tool_not_called("search")


# ---------------------------------------------------------------------------
# MockMCPServer — full agent scenario
# ---------------------------------------------------------------------------


async def mcp_agent(query: str, mcp_server: MockMCPServer) -> dict:
    """
    A simulated agent that:
    1. Calls an MCP 'search' tool to find results
    2. Calls an MCP 'summarize' tool to summarize them
    3. Returns a structured result dict
    """
    # Step 1: search
    search_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "search", "arguments": {"query": query, "limit": 5}},
    }
    search_response = await mcp_server.handle_message(search_request)
    search_results = search_response["result"]["content"][0]["text"]

    # Step 2: summarize
    summarize_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "summarize", "arguments": {"text": search_results}},
    }
    summarize_response = await mcp_server.handle_message(summarize_request)
    summary = summarize_response["result"]["content"][0]["text"]

    return {"query": query, "results": search_results, "summary": summary}


@pytest.mark.agent_test(layer="mock")
async def test_mcp_agent_calls_search_and_summarize(ca_mock_mcp_server):
    """Full agent scenario: agent makes sequential MCP tool calls and builds output."""
    mcp = ca_mock_mcp_server
    mcp.register_tool("search", response="cat, siamese cat, tabby cat")
    mcp.register_tool("summarize", response="3 cat breeds found")

    result = await mcp_agent("cats", mcp)

    assert result["query"] == "cats"
    assert result["results"] == "cat, siamese cat, tabby cat"
    assert result["summary"] == "3 cat breeds found"

    mcp.assert_tool_called("search", times=1, with_args={"query": "cats", "limit": 5})
    mcp.assert_tool_called("summarize", times=1)


@pytest.mark.agent_test(layer="mock")
async def test_mcp_agent_tool_call_order(ca_mock_mcp_server):
    """Verify that the agent calls tools in the correct order."""
    mcp = ca_mock_mcp_server
    mcp.register_tool("search", response="results here")
    mcp.register_tool("summarize", response="summary here")

    await mcp_agent("dogs", mcp)

    calls = mcp.get_calls_for("search")
    assert len(calls) == 1
    assert calls[0].arguments["query"] == "dogs"

    summarize_calls = mcp.get_calls_for("summarize")
    assert len(summarize_calls) == 1
    assert "results here" in summarize_calls[0].arguments["text"]


@pytest.mark.agent_test(layer="mock")
async def test_mcp_agent_error_propagation(ca_mock_mcp_server):
    """When MCP search returns an error, agent receives isError=True result."""
    mcp = ca_mock_mcp_server
    mcp.register_tool("search", error="Search service unavailable")

    search_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "search", "arguments": {"query": "cats"}},
    }
    response = await mcp.handle_message(search_request)

    # Error tool calls set isError=True in result
    assert response["result"]["isError"] is True
    assert "Search service unavailable" in response["result"]["content"][0]["text"]


@pytest.mark.agent_test(layer="mock")
async def test_mcp_agent_assert_output_with_matchers(ca_mock_mcp_server):
    """Combine MCP agent execution with dirty_equals matchers on final output."""
    mcp = ca_mock_mcp_server
    mcp.register_tool("search", response="12 items found")
    mcp.register_tool("summarize", response="Summary: 12 items")

    result = await mcp_agent("books", mcp)

    # Build AgentRun from result and assert with dirty_equals
    run = AgentRun(
        input={"query": "books"},
        final_output=result,
    )
    assert_output_matches(
        run,
        {
            "query": IsStr(),
            "results": IsStr(regex=r"\d+ items found"),
            "summary": IsStr(regex=r"Summary:.*"),
        },
    )


@pytest.mark.agent_test(layer="mock")
async def test_mcp_agent_multiple_queries_isolated(ca_mock_mcp_server):
    """Each ca_mock_mcp_server fixture is fresh; state doesn't bleed between tests."""
    mcp = ca_mock_mcp_server
    mcp.register_tool("search", response="fresh result")

    await mcp_agent("fresh query", mcp)

    # Only 1 call — no state leaked from previous tests
    calls = mcp.get_calls_for("search")
    assert len(calls) == 1
