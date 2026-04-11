"""Session 005 tests: MockMCPServer, MockLLM.stream(), ca_config, markers.

New features discovered in this session:
- MockMCPServer / ca_mock_mcp_server fixture
- MockLLM.stream() and stream_response() for real streaming from MockLLM
- ca_config fixture (access loaded CheckAgentConfig)
- @pytest.mark.safety and @pytest.mark.cassette markers (registered, behavior unknown)
"""
from __future__ import annotations

import json
import pytest
from checkagent import (
    CheckAgentConfig,
    MockLLM,
    MockMCPServer,
    StreamCollector,
)
from checkagent.mock.mcp import MCPCallRecord


# ---------------------------------------------------------------------------
# MockMCPServer — initialize handshake
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mcp_initialize_handshake(ca_mock_mcp_server):
    """initialize returns the correct protocol version and server info."""
    resp = await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "clientInfo": {"name": "test-client", "version": "1.0"},
            "protocolVersion": "2024-11-05",
        },
    })
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    result = resp["result"]
    assert result["protocolVersion"] == MockMCPServer.MCP_VERSION
    assert "serverInfo" in result
    assert result["serverInfo"]["name"] == "mock-mcp-server"


@pytest.mark.agent_test(layer="mock")
async def test_mcp_custom_name_and_version():
    """Constructor name and version appear in initialize response."""
    server = MockMCPServer(name="my-server", version="2.5.1")
    resp = await server.handle_message({
        "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}
    })
    assert resp["result"]["serverInfo"]["name"] == "my-server"
    assert resp["result"]["serverInfo"]["version"] == "2.5.1"


# ---------------------------------------------------------------------------
# MockMCPServer — tools/list
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mcp_tools_list_empty(ca_mock_mcp_server):
    """tools/list returns empty list when no tools registered."""
    resp = await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}
    })
    assert resp["result"]["tools"] == []


@pytest.mark.agent_test(layer="mock")
async def test_mcp_tools_list_with_registered_tools(ca_mock_mcp_server):
    """tools/list returns registered tools with name, description, inputSchema."""
    ca_mock_mcp_server.register_tool(
        "get_weather",
        description="Get current weather",
        input_schema={"type": "object", "properties": {"city": {"type": "string"}}},
        response={"temp": 72},
    )
    resp = await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}
    })
    tools = resp["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "get_weather"
    assert tools[0]["description"] == "Get current weather"
    assert tools[0]["inputSchema"]["properties"]["city"] == {"type": "string"}


@pytest.mark.agent_test(layer="mock")
async def test_mcp_tool_definitions_property(ca_mock_mcp_server):
    """tool_definitions property returns MCPToolDef objects."""
    ca_mock_mcp_server.register_tool("search", description="search tool")
    ca_mock_mcp_server.register_tool("summarize", description="summarize tool")
    defs = ca_mock_mcp_server.tool_definitions
    assert len(defs) == 2
    names = {d.name for d in defs}
    assert names == {"search", "summarize"}


# ---------------------------------------------------------------------------
# MockMCPServer — tools/call success
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mcp_tools_call_success_dict_response(ca_mock_mcp_server):
    """tools/call returns dict response JSON-encoded in content[0].text."""
    ca_mock_mcp_server.register_tool("get_weather", response={"temp": 72, "unit": "F"})
    resp = await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "get_weather", "arguments": {"city": "NYC"}},
    })
    assert "isError" not in resp["result"] or resp["result"].get("isError") is False
    content = resp["result"]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "text"
    parsed = json.loads(content[0]["text"])
    assert parsed == {"temp": 72, "unit": "F"}


@pytest.mark.agent_test(layer="mock")
async def test_mcp_tools_call_success_string_response(ca_mock_mcp_server):
    """tools/call with string response passes through as-is (no double-encoding)."""
    ca_mock_mcp_server.register_tool("echo", response="hello world")
    resp = await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "echo", "arguments": {}},
    })
    assert resp["result"]["content"][0]["text"] == "hello world"


@pytest.mark.agent_test(layer="mock")
async def test_mcp_tools_call_records_call(ca_mock_mcp_server):
    """tools/call records an MCPCallRecord with correct fields."""
    ca_mock_mcp_server.register_tool("search", response={"results": []})
    await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "search", "arguments": {"q": "pytest"}},
    })
    assert ca_mock_mcp_server.call_count == 1
    record = ca_mock_mcp_server.last_call
    assert isinstance(record, MCPCallRecord)
    assert record.tool_name == "search"
    assert record.arguments == {"q": "pytest"}
    assert record.is_error is False


# ---------------------------------------------------------------------------
# MockMCPServer — tools/call error paths
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mcp_tools_call_configured_error(ca_mock_mcp_server):
    """tools/call with error= returns isError:True in result."""
    ca_mock_mcp_server.register_tool("flaky", error="Service unavailable")
    resp = await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "flaky", "arguments": {}},
    })
    assert resp["result"]["isError"] is True
    assert "Service unavailable" in resp["result"]["content"][0]["text"]
    # Still records the call
    assert ca_mock_mcp_server.call_count == 1
    assert ca_mock_mcp_server.last_call.is_error is True


@pytest.mark.agent_test(layer="mock")
async def test_mcp_tools_call_unknown_tool(ca_mock_mcp_server):
    """tools/call for an unregistered tool returns isError:True."""
    resp = await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}},
    })
    assert resp["result"]["isError"] is True
    assert "nonexistent_tool" in resp["result"]["content"][0]["text"]
    # Still recorded
    assert ca_mock_mcp_server.call_count == 1


@pytest.mark.agent_test(layer="mock")
async def test_mcp_unknown_method_returns_error(ca_mock_mcp_server):
    """Unrecognized JSON-RPC method returns error code -32601."""
    resp = await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 99, "method": "unknown/method", "params": {}
    })
    assert "error" in resp
    assert resp["error"]["code"] == -32601


# ---------------------------------------------------------------------------
# MockMCPServer — notifications (no response)
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mcp_notification_returns_none(ca_mock_mcp_server):
    """notifications/initialized (no id) returns None — no response sent."""
    resp = await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    })
    assert resp is None


# ---------------------------------------------------------------------------
# MockMCPServer — handle_raw
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mcp_handle_raw_valid_json(ca_mock_mcp_server):
    """handle_raw accepts a JSON string and returns a JSON string response."""
    ca_mock_mcp_server.register_tool("ping", response="pong")
    raw_request = json.dumps({
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "ping", "arguments": {}},
    })
    raw_response = await ca_mock_mcp_server.handle_raw(raw_request)
    parsed = json.loads(raw_response)
    assert parsed["result"]["content"][0]["text"] == "pong"


@pytest.mark.agent_test(layer="mock")
async def test_mcp_handle_raw_invalid_json(ca_mock_mcp_server):
    """handle_raw with malformed JSON returns a parse error response."""
    raw_response = await ca_mock_mcp_server.handle_raw("not valid json {{{")
    parsed = json.loads(raw_response)
    assert "error" in parsed
    assert parsed["error"]["code"] == -32700  # Parse error


@pytest.mark.agent_test(layer="mock")
async def test_mcp_handle_raw_notification_returns_empty_string(ca_mock_mcp_server):
    """handle_raw for a notification (no id) returns empty string."""
    raw = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
    result = await ca_mock_mcp_server.handle_raw(raw)
    assert result == ""


# ---------------------------------------------------------------------------
# MockMCPServer — assertions
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mcp_assert_tool_called_basic(ca_mock_mcp_server):
    """assert_tool_called passes when tool was called."""
    ca_mock_mcp_server.register_tool("search", response={})
    await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "search", "arguments": {"q": "test"}},
    })
    ca_mock_mcp_server.assert_tool_called("search")  # should not raise


@pytest.mark.agent_test(layer="mock")
async def test_mcp_assert_tool_called_never_called_raises(ca_mock_mcp_server):
    """assert_tool_called raises AssertionError when tool was never called."""
    ca_mock_mcp_server.register_tool("search", response={})
    with pytest.raises(AssertionError, match="search"):
        ca_mock_mcp_server.assert_tool_called("search")


@pytest.mark.agent_test(layer="mock")
async def test_mcp_assert_tool_called_times(ca_mock_mcp_server):
    """assert_tool_called with times= checks exact call count."""
    ca_mock_mcp_server.register_tool("ping", response="ok")
    for _ in range(3):
        await ca_mock_mcp_server.handle_message({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "ping", "arguments": {}},
        })
    ca_mock_mcp_server.assert_tool_called("ping", times=3)
    with pytest.raises(AssertionError, match="3"):
        ca_mock_mcp_server.assert_tool_called("ping", times=1)


@pytest.mark.agent_test(layer="mock")
async def test_mcp_assert_tool_called_with_args(ca_mock_mcp_server):
    """assert_tool_called with_args= checks argument values."""
    ca_mock_mcp_server.register_tool("search", response={})
    await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "search", "arguments": {"q": "pytest", "limit": 10}},
    })
    ca_mock_mcp_server.assert_tool_called("search", with_args={"q": "pytest"})
    with pytest.raises(AssertionError, match="limit"):
        ca_mock_mcp_server.assert_tool_called("search", with_args={"limit": 99})


@pytest.mark.agent_test(layer="mock")
async def test_mcp_assert_tool_not_called_passes(ca_mock_mcp_server):
    """assert_tool_not_called passes when tool was never called."""
    ca_mock_mcp_server.register_tool("search", response={})
    ca_mock_mcp_server.assert_tool_not_called("search")  # should not raise


@pytest.mark.agent_test(layer="mock")
async def test_mcp_assert_tool_not_called_raises_when_called(ca_mock_mcp_server):
    """assert_tool_not_called raises AssertionError when tool was called."""
    ca_mock_mcp_server.register_tool("search", response={})
    await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "search", "arguments": {}},
    })
    with pytest.raises(AssertionError, match="1"):
        ca_mock_mcp_server.assert_tool_not_called("search")


# ---------------------------------------------------------------------------
# MockMCPServer — inspection helpers
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mcp_get_calls_for_filters_by_tool(ca_mock_mcp_server):
    """get_calls_for returns only calls for the named tool."""
    ca_mock_mcp_server.register_tool("search", response={})
    ca_mock_mcp_server.register_tool("lookup", response={})
    for _ in range(2):
        await ca_mock_mcp_server.handle_message({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "search", "arguments": {}},
        })
    await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "lookup", "arguments": {}},
    })
    assert len(ca_mock_mcp_server.get_calls_for("search")) == 2
    assert len(ca_mock_mcp_server.get_calls_for("lookup")) == 1


@pytest.mark.agent_test(layer="mock")
async def test_mcp_was_called(ca_mock_mcp_server):
    """was_called returns True/False correctly."""
    ca_mock_mcp_server.register_tool("search", response={})
    assert ca_mock_mcp_server.was_called("search") is False
    await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "search", "arguments": {}},
    })
    assert ca_mock_mcp_server.was_called("search") is True


@pytest.mark.agent_test(layer="mock")
async def test_mcp_registered_tools_property(ca_mock_mcp_server):
    """registered_tools returns list of tool names."""
    ca_mock_mcp_server.register_tool("a", response="A")
    ca_mock_mcp_server.register_tool("b", response="B")
    assert set(ca_mock_mcp_server.registered_tools) == {"a", "b"}


# ---------------------------------------------------------------------------
# MockMCPServer — reset
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mcp_reset_clears_calls(ca_mock_mcp_server):
    """reset() clears all recorded calls."""
    ca_mock_mcp_server.register_tool("ping", response="ok")
    await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "ping", "arguments": {}},
    })
    assert ca_mock_mcp_server.call_count == 1
    ca_mock_mcp_server.reset()
    assert ca_mock_mcp_server.call_count == 0
    assert ca_mock_mcp_server.last_call is None


@pytest.mark.agent_test(layer="mock")
async def test_mcp_reset_calls_clears_calls_keeps_tools(ca_mock_mcp_server):
    """reset_calls() clears calls but keeps registered tools."""
    ca_mock_mcp_server.register_tool("ping", response="ok")
    await ca_mock_mcp_server.handle_message({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "ping", "arguments": {}},
    })
    ca_mock_mcp_server.reset_calls()
    assert ca_mock_mcp_server.call_count == 0
    assert "ping" in ca_mock_mcp_server.registered_tools


@pytest.mark.agent_test(layer="mock")
async def test_mcp_register_tool_chains(ca_mock_mcp_server):
    """register_tool returns self for method chaining."""
    result = ca_mock_mcp_server.register_tool("a", response="A")
    assert result is ca_mock_mcp_server


# ---------------------------------------------------------------------------
# MockLLM.stream() + stream_response()
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_stream_response_multi_chunk(ca_mock_llm, ca_stream_collector):
    """stream_response configures multi-chunk streaming; collector aggregates it."""
    ca_mock_llm.stream_response("weather", ["It is ", "sunny ", "today!"])
    await ca_stream_collector.collect_from(ca_mock_llm.stream("What is the weather?"))

    assert ca_stream_collector.aggregated_text == "It is sunny today!"
    assert ca_stream_collector.total_chunks == 3


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_stream_fallback_to_add_rule(ca_mock_llm, ca_stream_collector):
    """When no stream_response rule matches, stream() falls back to add_rule response."""
    ca_mock_llm.add_rule("hello", "Hello there!")
    await ca_stream_collector.collect_from(ca_mock_llm.stream("hello world"))

    # Fallback yields the full response as a single TEXT_DELTA chunk
    assert ca_stream_collector.aggregated_text == "Hello there!"
    assert ca_stream_collector.total_chunks == 1


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_stream_fallback_to_default(ca_mock_llm, ca_stream_collector):
    """When no rules match, stream() falls back to default response."""
    # MockLLM default response is empty string or None — test it doesn't crash
    await ca_stream_collector.collect_from(ca_mock_llm.stream("some random input"))
    assert isinstance(ca_stream_collector.aggregated_text, str)
    assert ca_stream_collector.total_chunks >= 1


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_stream_records_call_as_streamed(ca_mock_llm):
    """stream() records the LLM call with streamed=True."""
    ca_mock_llm.stream_response("ping", ["pong"])
    async for _ in ca_mock_llm.stream("ping"):
        pass
    assert ca_mock_llm.call_count == 1
    assert ca_mock_llm.last_call.streamed is True


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_stream_response_returns_self_for_chaining(ca_mock_llm):
    """stream_response() returns MockLLM for fluent chaining."""
    result = ca_mock_llm.stream_response("a", ["chunk"])
    assert result is ca_mock_llm


@pytest.mark.agent_test(layer="mock")
async def test_mock_llm_stream_stream_rule_takes_priority_over_add_rule(ca_mock_llm, ca_stream_collector):
    """stream_response rule takes priority over add_rule for the same pattern."""
    ca_mock_llm.add_rule("hello", "regular response")
    ca_mock_llm.stream_response("hello", ["stream ", "chunk"])
    await ca_stream_collector.collect_from(ca_mock_llm.stream("say hello please"))

    assert ca_stream_collector.aggregated_text == "stream chunk"


# ---------------------------------------------------------------------------
# ca_config fixture
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_ca_config_returns_check_agent_config(ca_config):
    """ca_config fixture provides a CheckAgentConfig instance."""
    assert isinstance(ca_config, CheckAgentConfig)


@pytest.mark.agent_test(layer="mock")
def test_ca_config_has_version_field(ca_config):
    """ca_config.version is an integer (default 1)."""
    assert isinstance(ca_config.version, int)
    assert ca_config.version >= 1


@pytest.mark.agent_test(layer="mock")
def test_ca_config_has_asyncio_mode(ca_config):
    """ca_config.asyncio_mode is 'auto' or 'strict'."""
    assert ca_config.asyncio_mode in {"auto", "strict"}


# ---------------------------------------------------------------------------
# @pytest.mark.safety marker
# ---------------------------------------------------------------------------


@pytest.mark.safety(category="injection", severity="high")
@pytest.mark.agent_test(layer="mock")
async def test_safety_marker_does_not_crash(ca_mock_llm):
    """@pytest.mark.safety is registered — test runs normally without error."""
    ca_mock_llm.add_rule("inject", "I cannot help with that.")
    result = await ca_mock_llm.complete("inject malicious payload")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# @pytest.mark.cassette marker
# ---------------------------------------------------------------------------


@pytest.mark.cassette("fixtures/my_cassette.yaml")
@pytest.mark.agent_test(layer="mock")
async def test_cassette_marker_does_not_crash(ca_mock_llm):
    """@pytest.mark.cassette is registered — test runs without error even with no actual cassette."""
    # The marker is registered but has no behavior yet (replay module is empty)
    ca_mock_llm.add_rule("test", "response")
    result = await ca_mock_llm.complete("test input")
    assert result == "response"
