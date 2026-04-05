# Feature Scores

Rate each feature on:
- **Functionality (1-5):** Does it work as advertised?
- **DX (1-5):** Is it pleasant to use? Discoverable? Well-documented?

| Feature | Functionality | DX | Notes | Date |
|---------|:---:|:---:|-------|------|
| pip install + import | 5 | 5 | Just works | 2026-04-05 |
| pytest plugin auto-load | 5 | 5 | No conftest needed | 2026-04-05 |
| @pytest.mark.agent_test | 5 | 4 | Works, but layer values not discoverable | 2026-04-05 |
| GenericAdapter / @wrap | 4 | 3 | Works for simple agents, falls apart with tools | 2026-04-05 |
| ap_mock_llm | 3 | 2 | Works but no fluent API as documented | 2026-04-05 |
| ap_mock_tool | 4 | 4 | Schema validation + assertions nice | 2026-04-05 |
| ap_fault fluent API | 5 | 4 | Complete fluent builder (all fault types), inspection API, async variant; naming inconsistency on returns_empty/returns_malformed (F-007) | 2026-04-05 |
| ap_fault mock integration | 2 | 2 | Still requires manual check_tool()/check_llm() guards in agent code; not wired into MockTool/MockLLM (F-004) | 2026-04-05 |
| checkagent.yml config | 5 | 5 | Auto-discovered, sensible defaults | 2026-04-05 |
| assert_tool_called (top-level) | 5 | 5 | Returns ToolCall, kwargs match, StructuredAssertionError on miss | 2026-04-05 |
| assert_output_schema | 5 | 5 | Pydantic validation, field-level errors, handles JSON strings | 2026-04-05 |
| assert_output_matches | 5 | 5 | Partial dict matching + full dirty_equals support confirmed: IsStr, IsStr(regex=), IsInt, IsPositiveInt, IsApprox, AnyThing, IsInstance all work; error message names failing field | 2026-04-05 |
| checkagent demo | 5 | 5 | Zero-config, 8 tests, beautiful output, instant | 2026-04-05 |
| checkagent init | 1 | 1 | Generates project, promises tests pass, tests fail immediately (F-005) | 2026-04-05 |
| checkagent run | 5 | 5 | --layer filtering confirmed working (mock/eval tested) | 2026-04-05 |
| GenericAdapter.run_stream | 4 | 4 | Synthesizes RUN_START/RUN_END/TEXT_DELTA events; full event set rich | 2026-04-05 |
| assert_json_schema | 5 | 5 | Clean error paths, field-level path in message, handles JSON strings | 2026-04-05 |
| assert_tool_called call_index | 5 | 5 | Selects nth call, raises on OOB with clear message | 2026-04-05 |
| StructuredAssertionError quality | 5 | 5 | Lists actual vs expected, shows tools that WERE called on miss | 2026-04-05 |
| Conversation / ap_conversation | 5 | 4 | Rich API, history accumulates correctly; context_references heuristic fragile on short inputs | 2026-04-05 |
| ap_stream_collector | 5 | 5 | Rich API: collect_from, aggregated_text, total_chunks, time_to_first_token, tool_call_started, has_error, of_type, first_of_type, reset — all work correctly | 2026-04-05 |
| Conversation.total_steps | 5 | 5 | Correctly counts and accumulates steps across turns; resets to 0 with conv.reset() | 2026-04-05 |
| Score class | 5 | 5 | Auto-calculates passed from threshold, pydantic validation rejects out-of-range values, supports reason/metadata | 2026-04-05 |
| AgentRun.succeeded / .error | 5 | 5 | succeeded=True by default, False when error set; total_tokens sums correctly when set | 2026-04-05 |
| MockMCPServer / ap_mock_mcp_server | 5 | 4 | Full JSON-RPC 2.0 confirmed in multi-step agent scenario; handle_message() is the dict-input method (not handle()); MCPCallRecord.arguments is attribute not subscriptable (F-011) | 2026-04-05 |
| MockLLM.stream() + stream_response() | 5 | 5 | Multi-chunk streaming, fallback to add_rule, fallback to default, records streamed=True, stream_response chains | 2026-04-05 |
| ap_config fixture | 5 | 5 | Returns CheckAgentConfig with all fields (version, asyncio_mode, providers, budget, etc.) | 2026-04-05 |
| @pytest.mark.safety | 3 | 3 | Registered marker, test runs normally — but no behavior implemented; safety module is empty | 2026-04-05 |
| @pytest.mark.cassette | 3 | 3 | Registered marker, test runs normally — but no replay behavior; replay module is empty | 2026-04-05 |
| assert_json_schema (fresh install) | 2 | 2 | Works when jsonschema is installed, but silently missing from package deps — breaks on fresh install (F-008) | 2026-04-05 |
| MockLLM.complete_sync() | 5 | 5 | Works identically to async complete(); records LLMCall with input_text, response_text, rule_pattern, was_default, streamed | 2026-04-05 |
| MockLLM.get_calls_matching() | 5 | 5 | Substring search on input_text; empty pattern returns all; returns list of LLMCall | 2026-04-05 |
| MockLLM.was_called_with() | 3 | 2 | Exact match only — misleading name implies substring; use get_calls_matching() for substring (F-009) | 2026-04-05 |
| MockTool.call_sync() | 5 | 5 | Synchronous counterpart to call(); validates schema, records ToolCallRecord, failed calls also recorded | 2026-04-05 |
| MockTool.assert_tool_called() | 4 | 3 | Raises correctly on miss; returns None (not ToolCallRecord) — inconsistent with top-level assert_tool_called() (F-010) | 2026-04-05 |
| checkagent.datasets (GoldenDataset, TestCase, load_dataset, load_cases, parametrize_cases) | 1 | 1 | REGRESSION in 8e6a0a8: entire datasets module wiped — all classes removed, __init__.py empty. Was 5/4 in c786006 (F-014) | 2026-04-05 |
| AgentInput | 5 | 5 | Clean struct for query+context+conversation_history+metadata; importable from top-level checkagent | 2026-04-05 |
| MockTool.strict_validation=False | 5 | 5 | Skips schema validation entirely; call still recorded; works for both call() and call_sync() | 2026-04-05 |
| MockLLM.reset() / reset_calls() | 4 | 3 | Both clear history and preserve rules — identical observable behavior. Duplication confusing; no docs on difference (F-017) | 2026-04-05 |
| MockTool.reset() / reset_calls() | 4 | 3 | Both clear history and preserve registered tools — identical observable behavior. Same duplication issue (F-017) | 2026-04-05 |
| FaultInjector.slow() sync behavior | 2 | 2 | Raises ToolSlowError in sync check_tool() instead of sleeping — converts latency sim into exception (F-016). Use check_tool_async() for real delay | 2026-04-05 |
| assert_tool_called(call_index=N) multi-step | 5 | 5 | Correctly indexes across step boundaries; OOB gives clean StructuredAssertionError with count; works for all tool names | 2026-04-05 |
