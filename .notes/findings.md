# Findings Log

DX issues, API gaps, bugs, and confusion points discovered while using CheckAgent.

Format:
```
## F-{number}: {title}
**Date:** YYYY-MM-DD
**Severity:** critical | high | medium | low
**Category:** bug | dx-friction | missing-feature | docs-mismatch
**Description:** What happened
**Expected:** What the docs/README promised
**Actual:** What actually happened
**Workaround:** How I got around it (if possible)
**Status:** Open | Fixed in {version/commit}
```

---

## F-001: README fluent API doesn't exist
**Date:** 2026-04-05
**Severity:** high
**Category:** docs-mismatch
**Description:** README shows `ap_mock_llm.on_input(contains="book").respond(tool_call(...))` but MockLLM only has `add_rule()` returning strings.
**Expected:** Fluent builder API as documented
**Actual:** Only `add_rule(pattern, response, match_mode)` exists
**Workaround:** Use `add_rule()` directly
**Status:** Open

## F-002: assert_tool_called not importable from checkagent
**Date:** 2026-04-05
**Severity:** high
**Category:** docs-mismatch
**Description:** README shows `from checkagent import assert_tool_called` but this doesn't exist.
**Expected:** Top-level import for common assertion helpers
**Actual:** Assertions are methods on MockTool instances (`mock_tool.assert_tool_called("name")`)
**Workaround:** Use MockTool methods directly
**Status:** Fixed in c64f211 — `assert_tool_called`, `assert_output_schema`, `assert_output_matches`, `assert_json_schema` all now importable from `checkagent`

## F-003: GenericAdapter doesn't handle tool-using agents
**Date:** 2026-04-05
**Severity:** medium
**Category:** missing-feature
**Description:** GenericAdapter wraps simple callables but creates single-Step runs with no tool calls. Agents that use tools must build AgentRun manually.
**Expected:** Some way to capture tool calls from wrapped functions
**Actual:** Must construct AgentRun with Steps and ToolCalls by hand
**Workaround:** Build AgentRun manually in agent code
**Status:** Open

## F-004: FaultInjector not integrated with mocks
**Date:** 2026-04-05
**Severity:** medium
**Category:** dx-friction
**Description:** FaultInjector is standalone — agent code must call `check_tool()` before each operation. Not automatically wired into MockTool/MockLLM.
**Expected:** Faults fire automatically when mock tools are called
**Actual:** Manual guard calls required
**Workaround:** Call `fault.check_tool("name")` explicitly before each tool invocation
**Status:** Partially resolved in session-004 — FaultInjector now has a complete fluent builder API (`on_tool().timeout()`, `on_tool().rate_limit()`, `on_tool().slow()`, `on_tool().returns_malformed()`, `on_tool().returns_empty()`, `on_tool().intermittent()`, `on_llm().rate_limit()`, `on_llm().context_overflow()`, `on_llm().server_error()`, `on_llm().content_filter()`, `on_llm().partial_response()`). Also has inspection API: `records`, `triggered_records`, `trigger_count`, `was_triggered()`, `has_faults_for()`, `has_llm_faults()`, `reset_records()`, `check_tool_async()`. Integration with MockTool/MockLLM still requires manual guard calls.

## F-005: `checkagent init` generates broken project — tests fail immediately
**Date:** 2026-04-05
**Severity:** critical
**Category:** bug
**Description:** `checkagent init` scaffolds a project but the generated tests fail with two errors when you run `pytest tests/ -v`: (1) `ModuleNotFoundError: No module named 'sample_agent'` because no `pyproject.toml` configures `pythonpath = ["."]`, and (2) even with `PYTHONPATH=.`, tests fail with "async def functions are not natively supported" because `asyncio_mode = "auto"` is not configured.
**Expected:** "The generated tests pass immediately with no API keys required" (from `checkagent init --help`)
**Actual:** Zero tests pass out of the box. Two structural issues: no pythonpath config, no asyncio_mode config.
**Workaround:** Manually create `pyproject.toml` with `[tool.pytest.ini_options] asyncio_mode = "auto"` and `pythonpath = ["."]`
**Status:** Open (still not fixed in session-006 — sixth session without a fix)

## F-006: `context_references` heuristic produces false positives on short inputs
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `conv.context_references(turn, ref_turn)` uses substring matching — it checks if the earlier turn's input *or* output appears anywhere in the later turn's output. If the earlier input is a short common word like "hello", nearly any response from the agent will match.
**Expected:** A reliable signal that the agent is semantically referencing a prior turn
**Actual:** Any suffix/substring coincidence triggers a True result. Example: turn 0 input = "hello", turn 1 output = "hello there" → returns True even if the agent isn't tracking state.
**Workaround:** Only use `context_references` with long, specific inputs that are unlikely to appear by coincidence. The docs acknowledge this is a heuristic and suggest the judge layer for robust reference detection.
**Status:** Open (by design — docs flag the limitation)

## F-007: ToolFaultBuilder method naming inconsistency
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `ToolFaultBuilder` methods have inconsistent naming conventions. Fault types that return errors are named `returns_malformed()` and `returns_empty()`, while others use plain verb forms: `timeout()`, `rate_limit()`, `slow()`, `intermittent()`. The `returns_` prefix on only two methods creates an asymmetric API.
**Expected:** Consistent naming — either all use plain verbs (`malformed()`, `empty()`) or all use `returns_X()` / `raises_X()` convention
**Actual:** Mixed: `timeout()`, `rate_limit()`, `slow()`, `intermittent()`, `returns_malformed()`, `returns_empty()`
**Workaround:** Just remember the actual names; they all work correctly
**Status:** Open

## F-008: `assert_json_schema` silently requires `jsonschema` as undeclared dependency
**Date:** 2026-04-05
**Severity:** high
**Category:** bug
**Description:** `assert_json_schema` requires the `jsonschema` package at runtime but it is not declared in checkagent's package dependencies. On a fresh `pip install checkagent`, calling `assert_json_schema` raises `ImportError: jsonschema is required for assert_json_schema. Install it with: pip install jsonschema`. This caused 7 previously-passing tests to fail after a clean upgrade in session-005.
**Expected:** `jsonschema` listed as either a required dependency or an optional extra (`checkagent[json-schema]`), so it's installed automatically
**Actual:** `uv pip install checkagent` does not install `jsonschema`. Any test using `assert_json_schema` fails with `ImportError` on fresh install.
**Workaround:** Manually run `pip install jsonschema` after installing checkagent
**Status:** Open

## F-009: `MockLLM.was_called_with` does exact match but name implies substring
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `MockLLM.was_called_with(text)` performs an exact match against `input_text` in each recorded call. If you call `llm.complete_sync("What is the capital of France?")` and then check `llm.was_called_with("capital of France")`, it returns `False` — even though the text appears in the actual input.
**Expected:** A method named `was_called_with` suggests "was this LLM called with a message containing this text" — i.e., substring matching.
**Actual:** Exact match only. `llm.was_called_with("France")` → `False` even after calling with `"What is the capital of France?"`.
**Workaround:** Use `llm.get_calls_matching("France")` for substring matching. Use `was_called_with` only when you know the exact input string.
**Status:** Open

## F-010: `MockTool.assert_tool_called` returns None — inconsistent with top-level `assert_tool_called`
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `MockTool.assert_tool_called("name")` returns `None`, so you can't chain or inspect the returned `ToolCall`. The top-level `assert_tool_called(run, "name")` returns a `ToolCall` object, which enables natural patterns like `tc = assert_tool_called(run, "search"); assert tc.arguments["query"] == "cats"`.
**Expected:** `MockTool.assert_tool_called` to return the `ToolCallRecord` so call arguments can be inspected inline.
**Actual:** Returns `None`. Must use `tool.last_call` or `tool.calls[n]` to inspect call details.
**Workaround:** Use `tool.last_call` or `tool.calls` for call inspection after asserting.
**Status:** Open

## F-011: `MockMCPServer` uses `handle_message` for dict input — not `handle`
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `MockMCPServer` exposes two handle methods: `handle_raw(json_string)` for raw JSON strings, and `handle_message(dict)` for pre-parsed dicts. The method name `handle_message` is not discoverable from the class name pattern — a user would naturally try `handle()` or `handle_raw()` first.
**Expected:** Either a generic `handle(msg)` that accepts both str and dict (with type dispatch), or clear documentation that the dict-input method is `handle_message`.
**Actual:** `mcp.handle(dict)` raises `AttributeError`. Must use `handle_message(dict)`.
**Workaround:** Use `handle_message(dict)` for dict input, `handle_raw(str)` for JSON strings.
**Status:** Open

## F-012: `GoldenDataset.version` rejects unquoted YAML integers
**Date:** 2026-04-05
**Severity:** medium
**Category:** bug
**Description:** `GoldenDataset.version` is typed as `str` with no Pydantic coercion, so YAML files with an unquoted integer version field (e.g., `version: 2`) raise `ValidationError: Input should be a valid string`. YAML parses unquoted `2` as `int`, and pydantic refuses it.
**Expected:** Version numbers like `1`, `2`, `3` are universally valid. The field should accept integers and coerce them to strings, or use `str | int`.
**Actual:** `version: 2` in YAML → `ValidationError`. Must quote: `version: '2'`.
**Workaround:** Always quote version values in YAML: `version: '2'` instead of `version: 2`.
**Status:** Open

## F-013: `TestCase` class name causes `PytestCollectionWarning`
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `checkagent.datasets.TestCase` is a Pydantic model whose class name starts with `Test`. pytest tries to collect it as a test class and emits `PytestCollectionWarning: cannot collect test class 'TestCase' because it has a __init__ constructor`. This warning appears in every test file that imports `TestCase`.
**Expected:** No warnings when importing a public API class. Either the class should be renamed (e.g., `AgentTestCase`, `DatasetCase`) or the warning should be suppressed via `collect_ignore` in the pytest plugin.
**Actual:** Warning fires on any import: `cannot collect test class 'TestCase' because it has a __init__ constructor (from: tests/test_session007.py)`.
**Workaround:** Can suppress with `filterwarnings = ["ignore::pytest.PytestCollectionWarning"]` in pytest config, but shouldn't have to.
**Status:** Open

---

## F-014: `checkagent.datasets` module emptied in 8e6a0a8 — GoldenDataset and all dataset classes removed
**Date:** 2026-04-05
**Severity:** critical
**Category:** bug
**Description:** Upgrading from c786006 to 8e6a0a8 wiped the entire `checkagent.datasets` module. `GoldenDataset`, `TestCase`, `load_dataset`, `load_cases`, and `parametrize_cases` all gone. `checkagent.datasets.__init__.py` is now empty. The datasets subpackage directory still exists but exports nothing.
**Expected:** Backward-compatible upgrade — all public API from c786006 should still work after upgrading to 8e6a0a8.
**Actual:** `from checkagent.datasets import GoldenDataset` raises `ImportError`. All 35 session-007 tests are uncollectable. The test_session007.py file cannot even be imported.
**Workaround:** None. Pin to c786006 to retain datasets support. The datasets regression also blocks `checkagent run --layer judge tests/` from completing (collection aborts on the import error).
**Status:** Open

---

## F-015: `dirty_equals` not declared as a checkagent dependency
**Date:** 2026-04-05
**Severity:** medium
**Category:** bug
**Description:** `checkagent` uses `dirty_equals` matchers in `assert_output_matches` (and test files use it directly) but `dirty_equals` is not listed in checkagent's declared dependencies (`Requires: click, pluggy, pydantic, pytest, pytest-asyncio, pyyaml, rich`). After upgrading checkagent from a fresh environment, `dirty_equals` is not installed and test_session006.py fails to collect with `ModuleNotFoundError: No module named 'dirty_equals'`.
**Expected:** `dirty_equals` listed as a required or optional checkagent dependency so it installs automatically.
**Actual:** `uv pip install checkagent@git...` does not install dirty_equals. Any file importing from `dirty_equals` fails with `ModuleNotFoundError` on collection.
**Workaround:** Manually run `pip install dirty-equals` after installing checkagent.
**Status:** Open

---

## F-016: `FaultInjector.slow()` raises `ToolSlowError` in sync context — not a latency simulation
**Date:** 2026-04-05
**Severity:** medium
**Category:** dx-friction
**Description:** `fault.on_tool("x").slow()` is expected to simulate slow responses by adding latency. But calling `fault.check_tool("x")` in a synchronous context raises `ToolSlowError: FaultInjection(x): slow response (Nms) — use async for real delay`. The fault raises instead of sleeping, which is surprising. The error message suggests using `check_tool_async()` for real delay.
**Expected:** `slow()` should simulate latency — either sleep synchronously or be clearly documented as async-only. The current behavior converts a latency simulation into an exception that aborts the tool call.
**Actual:** Synchronous `check_tool()` raises `ToolSlowError`. Only `check_tool_async()` produces real latency simulation.
**Workaround:** Use `await fault.check_tool_async("x")` for slow fault simulation. Never use `check_tool()` for slow faults.
**Status:** Open

---

## F-017: `MockLLM.reset()` and `reset_calls()` are functionally identical — undocumented duplication
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** Both `MockLLM.reset()` and `MockLLM.reset_calls()` clear call history and preserve registered rules. Same for `MockTool.reset()` and `MockTool.reset_calls()`. They have different names but identical observable behavior — neither removes registered rules or tools.
**Expected:** Either the two methods do different things (e.g., `reset()` clears everything including rules, `reset_calls()` only clears history), or one is an alias of the other with documentation explaining why both exist.
**Actual:** No observable difference. Having two methods with the same behavior creates confusion about which to use.
**Workaround:** Use either one — they're interchangeable.
**Status:** Open
