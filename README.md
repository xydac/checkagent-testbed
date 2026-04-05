# checkagent-testbed

Customer-zero testbed for [CheckAgent](https://github.com/xydac/checkagent) -- exercising the public API as an external consumer would.

## What's here

- **agents/echo_agent.py** -- simplest possible agent (uppercases input), wrapped with `@wrap` from `checkagent.adapters.generic`
- **agents/booking_agent.py** -- multi-step agent that checks a calendar and creates an event, using MockLLM and MockTool
- **tests/test_echo.py** -- basic GenericAdapter + MockLLM smoke tests
- **tests/test_booking.py** -- tool mocking, call order assertions, AgentRun tool call records
- **tests/test_faults.py** -- fault injection: timeouts, rate limits, context overflow

## Running

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Test results (2026-04-04, checkagent 0.0.1a1)

All 13 tests pass:

```
tests/test_booking.py::test_booking_happy_path PASSED
tests/test_booking.py::test_booking_tool_call_order PASSED
tests/test_booking.py::test_booking_unavailable PASSED
tests/test_booking.py::test_booking_records_tool_calls_in_agentrun PASSED
tests/test_echo.py::test_echo_basic PASSED
tests/test_echo.py::test_echo_preserves_input PASSED
tests/test_echo.py::test_echo_empty_string PASSED
tests/test_faults.py::test_tool_timeout PASSED
tests/test_faults.py::test_tool_rate_limit PASSED
tests/test_faults.py::test_llm_context_overflow PASSED
tests/test_faults.py::test_llm_rate_limit PASSED
tests/test_faults.py::test_fault_records PASSED
tests/test_faults.py::test_no_fault_for_unconfigured_tool PASSED
```

## Customer-zero findings

1. **GenericAdapter is great for simple agents** -- `@wrap` on an async function works exactly as documented. The adapter handles `AgentRun` construction automatically.

2. **GenericAdapter doesn't cover tool-using agents** -- for agents that call tools, you need to build the `AgentRun` (with `ToolCall` records in `Step.tool_calls`) manually. The `GenericAdapter.run()` method creates a single `Step` with no tool calls. A real tool-using agent needs either a framework-specific adapter or a richer generic adapter that can observe tool calls.

3. **MockLLM and MockTool work independently but aren't wired together** -- the README example shows `ap_mock_llm.on_input(contains="...").respond(tool_call(...))` but that fluent API doesn't exist yet. MockLLM only returns strings via `add_rule()`. There's no `tool_call()` helper. The booking agent has to manually orchestrate between MockLLM and MockTool.

4. **FaultInjector is standalone** -- it raises exceptions when you call `check_tool()` / `check_llm()`, but it isn't wired into MockTool or MockLLM automatically. The agent code has to explicitly call `ap_fault.check_tool("name")` before each tool call. An integration where MockTool consults FaultInjector automatically would be useful.

5. **checkagent.yml loads fine** -- the config loader picks it up. No issues with the `version: 1` format.

6. **The pytest plugin registers correctly** -- `@pytest.mark.agent_test(layer="mock")` works, `--agent-layer` filtering works, all three fixtures (`ap_mock_llm`, `ap_mock_tool`, `ap_fault`) are available without any conftest.py setup.

7. **No `assert_tool_called` at the top-level module** -- the README example imports `from checkagent import assert_tool_called` but this doesn't exist. The assertion helpers live on `MockTool` instances (`ap_mock_tool.assert_tool_called(...)`) and `AgentRun` has `tool_was_called()`. Consider adding convenience functions to the top-level `checkagent` namespace.
