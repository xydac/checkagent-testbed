# Testbed Journal

What I tried each cycle, what happened, what surprised me.

---

## Session 9 — 2026-04-05 (cost tracking: CostTracker, CostBreakdown, BudgetExceededError)

**Upgraded from:** 8e6a0a8 → e38593a

**What I tried:**
- Upgraded checkagent from git main (8e6a0a8 → e38593a)
- Re-ran 225 existing tests — all 225 pass cleanly (no collection errors, no new failures)
- Confirmed F-014 is fixed: datasets module fully restored in e38593a. GoldenDataset, TestCase, parametrize_cases all importable. All 35 session-007 tests pass. The session-008 regression xfail markers now fall through to normal pass (because the import succeeds, the xfail branch is never hit).
- Explored the new cost tracking API: `calculate_run_cost`, `CostTracker`, `CostBreakdown`, `CostReport`, `BudgetExceededError`, `BUILTIN_PRICING`
- Tested `calculate_run_cost` with known models (claude-sonnet), unknown models (unpriced), custom pricing_overrides, and default_pricing fallback
- Tested `CostTracker` accumulation: run_count, total_cost, total_tokens all accumulate correctly across multiple `record()` calls
- Tested all three budget enforcement methods: `check_test_budget(breakdown)`, `check_suite_budget()`, `check_ci_budget()` — all raise `BudgetExceededError` correctly when over limit
- Verified that no budget configured → no error (all three check methods are no-ops)
- Tested `CostReport.budget_utilization()` — returns fractions for each configured limit
- Probed top-level namespace for companion types (`ProviderPricing`, `BudgetConfig`, `BUILTIN_PRICING`) — none are top-level exported. Filed F-018.
- Checked for `ap_cost_tracker` fixture — does not exist. Filed F-019.
- Confirmed F-005 (checkagent init) still broken — ninth session without a fix. Still emits "async def functions are not natively supported" because generated project lacks asyncio_mode = "auto".
- Wrote 36 new tests — all 36 pass
- Total: 261 tests pass, 0 failures, 1 warning (F-013 TestCase collection warning, still open)

**What surprised me:**
- The datasets regression is fully fixed. This is the right call — the entire module was wiped in 8e6a0a8, and having it back restores confidence in the framework. The fix came one session after I filed the critical finding, which is a reasonable turnaround.
- The cost tracking API is thoughtfully designed. The three-level budget model (`per_test`, `per_suite`, `per_ci_run`) maps well to real CI workflows. `BUILTIN_PRICING` already has 16 models including Claude 4, GPT-4o, and Gemini 2.5 Pro — this is genuinely useful without configuration.
- The unpriced_steps design is good: instead of raising or silently skipping, it counts steps with no pricing and returns `total_cost=0.0` for those steps while still tracking the ones it can. This gives partial information rather than all-or-nothing.
- The biggest DX rough edge: `ProviderPricing`, `BudgetConfig`, and `BUILTIN_PRICING` are all needed to use `CostTracker` customizations, but none are at top-level. You export `CostTracker` (which takes a `BudgetConfig`) but not `BudgetConfig` itself. A user reading the docstring for `CostTracker.__init__` will see `budget: BudgetConfig | None` and then have to hunt for where to import `BudgetConfig` from. It's at `checkagent.core.config` — an implementation-internal path.
- The missing `ap_cost_tracker` fixture is the larger gap. `CostTracker` is stateful and session-scoped by nature, but there's no standard pytest integration. The obvious pattern — budget from `ap_config`, teardown that calls `check_suite_budget()`, so suite tests fail if budget is exceeded — is left entirely to the user. This is the same pattern checkagent follows for `ap_config` (auto-wired), `ap_mock_llm` (auto-fresh per test), etc. Cost tracking should get the same treatment.

**Overall impression:**
Two sessions: critical crash (datasets gone) followed by a clean fix (datasets restored, cost tracking added). The cost tracking module itself is well-implemented — math is correct, three-tier budget model is practical, error messages are helpful. The DX issues are fixable: promote `ProviderPricing`/`BudgetConfig`/`BUILTIN_PRICING` to top-level exports, and add an `ap_cost_tracker` fixture. F-005 (`checkagent init`) remains the most embarrassing persistent bug — the very first thing a new user does after reading the README fails, and it's been broken for nine consecutive sessions.

**Next time I want to try:**
- Test `check_tool_async()` with `slow()` to confirm real latency vs just raising (F-016 in async context)
- Test FaultInjector `intermittent()` at edge probabilities (0.0, 1.0, 0.5) — determinism guarantees?
- Test `MockTool.was_called` predicate (vs `assert_tool_called` assertion)
- Test `MockTool.get_calls_for("name")` — verify it filters by tool name
- Check if `checkagent run --layer judge` now works (F-014 fixed, so collection should succeed)
- Test `CostTracker` with `pricing_overrides` parameter at construction vs at `calculate_run_cost` level
- Probe whether `CostReport.to_dict()` matches `CostBreakdown.to_dict()` structure

---

## Session 1 — 2026-04-05 (Initial Setup)

**What I tried:**
- Installed checkagent from git main
- Created a simple echo agent with @wrap decorator
- Created a booking agent that uses tools
- Wrote mock layer tests, tool assertion tests, fault injection tests

**What worked:**
- Install was clean, no dependency issues
- pytest plugin loaded automatically — no conftest.py needed
- MockTool schema validation and call recording are solid
- FaultInjector fluent API is intuitive (`.on_tool("x").timeout(5)`)
- Config file auto-discovery works great

**What surprised me:**
- The README examples don't match the actual API. The fluent MockLLM API and `assert_tool_called` import shown in the README don't exist. This would be the first thing a new user tries and it would fail.
- GenericAdapter is too simple for anything beyond echo agents. Real agents that call tools need to build AgentRun manually, which is a lot of boilerplate.
- FaultInjector is decoupled from the mocks — you have to manually call `check_tool()` guard methods. I expected faults to fire automatically when MockTool is called.

**Overall impression:**
The foundation is solid. Plugin auto-loading and config discovery are best-in-class. But the gap between what the README promises and what actually works would frustrate a first-time user. Fix the docs-API mismatch before any public announcement.

**Next time I want to try:**
- checkagent init and checkagent demo CLI commands
- Writing a more complex multi-step agent test
- Testing structured output if available
- See if streaming mock exists

---

## Session 2 — 2026-04-05 (CLI + New Assertions)

**Upgraded from:** commit c64f211 (same version string 0.0.1a1, but new code)

**What I tried:**
- Re-ran all 13 existing tests — all pass, nothing regressed
- Tested `checkagent demo`, `checkagent init`, and `checkagent run` CLI commands
- Explored new top-level imports: `assert_tool_called`, `assert_output_schema`, `assert_output_matches`, `assert_json_schema`, `StreamEvent`, `StreamEventType`
- Wrote 11 new tests covering all the new assertion helpers and `run_stream`

**What worked:**
- F-002 is fixed: `assert_tool_called` (and friends) are now importable from `checkagent`. The function takes `(result, tool_name, **kwargs)`, returns the matching `ToolCall`, raises `StructuredAssertionError` on miss. Clean, well-designed API.
- `assert_output_schema` validates Pydantic models against JSON output. Handles both raw dicts and JSON strings. Raises `StructuredAssertionError` with field-level detail on failure.
- `assert_output_matches` does partial dict matching. Straightforward.
- `checkagent demo` is genuinely delightful — 8 tests, zero config, runs in milliseconds, outputs a clean summary panel with next steps. Best onboarding experience I've seen in a testing framework.
- `checkagent run` works correctly in an existing project (passes through to pytest, asyncio_mode picked up from pyproject.toml).
- `GenericAdapter.run_stream` synthesizes `RUN_START`, `TEXT_DELTA`, `STEP_END`, `RUN_END` events. Works as a fallback streamer for non-streaming agents.

**What surprised me:**
- `checkagent init` is broken at the most embarrassing level. The help text says "The generated tests pass immediately with no API keys required" but they don't pass at all. Two problems stack: no `pyproject.toml` means pytest can't find `sample_agent` module (ImportError), and even with `PYTHONPATH=.` the tests fail because `asyncio_mode=auto` isn't set. Both problems are trivially fixable on the init side. This is the command a new user runs first — it needs to work.
- The streaming `StreamEventType` enum has 10 values (`RUN_START`, `RUN_END`, `STEP_START`, `STEP_END`, `TEXT_DELTA`, `TOOL_CALL_START`, `TOOL_CALL_DELTA`, `TOOL_CALL_END`, `TOOL_RESULT`, `ERROR`). That's a surprisingly complete streaming event model for an alpha.
- The `Detected frameworks: openai` message during `checkagent init` is curious — I don't have openai installed. It must be scanning imports or env vars. The tip to "use framework-specific adapters" implies adapters exist, but I can't find an `openai` adapter in the public API.

**Overall impression:**
Big improvement this cycle. The new assertion API is excellent — well-typed, raises structured errors, composable. The `demo` command sets a high bar for onboarding DX. But `checkagent init` is critically broken: it promises working tests and delivers import errors. That's the one thing that needs an urgent fix before any wider release.

**Next time I want to try:**
- Test `checkagent run --layer mock` filtering
- Find the openai adapter (if it exists) and test it
- Try `assert_json_schema` with a real JSON Schema dict
- Test `assert_tool_called(result, "name", call_index=1)` for indexing specific calls
- Try `StructuredAssertionError` message quality — what does the error tell you?

---

## Session 3 — 2026-04-05 (Multi-turn Conversation + Deep Assertions)

**Upgraded from:** session-002 state (version still 0.0.1a1, fresh rebuild from git main)

**What I tried:**
- Re-ran all 24 existing tests — all pass, no regressions
- Spotted `Conversation` and `Turn` in top-level `checkagent` namespace (new since last session)
- Tested the full `Conversation` / `ap_conversation` API: `say()`, `total_turns`, `total_tool_calls`, `all_tool_calls`, `get_turn()`, `tool_was_called()`, `tool_was_called_in_turn()`, `context_references()`, `reset()`, `turns` (copy semantics), `last_turn`, `last_result`
- Tested `checkagent run --layer mock` and `--layer eval` — layer filtering confirmed working
- Tested `assert_json_schema` against a real JSON Schema with required fields, type constraints, minimum/maximum, and `additionalProperties: false`
- Tested `assert_tool_called(result, "name", call_index=N)` for selecting the Nth call to a repeated tool
- Probed `StructuredAssertionError` message quality: wrong tool name, arg mismatch, out-of-range call_index
- Investigated `context_references` edge cases

**What worked:**
- `Conversation` API is solid. `ap_conversation` fixture returns the class itself (you call `ap_conversation(agent_fn)` to get an instance) — slightly unusual but documented in the fixture docstring.
- History accumulates correctly across turns: each `say()` builds `[user, assistant, user, assistant, ...]` history and passes it to the next agent call.
- `reset()` clears all turns cleanly — next `say()` behaves as if it's the first turn.
- `turns` property returns a copy — mutation of the returned list doesn't corrupt the internal state.
- `assert_json_schema` error messages are excellent: they include the failing path (`properties → confirmed → type`), the failed constraint, and the actual value. Best error messages of any assertion in the framework.
- `assert_tool_called(call_index=N)` works cleanly for repeated-tool scenarios. OOB raises `StructuredAssertionError` with the tool name and count in the message.
- `StructuredAssertionError` on wrong tool name lists the tools that WERE called. On arg mismatch it shows both the expected and actual value per argument. Very debuggable.
- `--layer eval` correctly deselects all 47 tests (none are marked eval).

**What surprised me:**
- `context_references` is a substring heuristic and is easy to accidentally satisfy. If turn 0's query is "hello" and turn 1's output says "hello world", `context_references(1, 0)` returns True — even if the agent has no memory. The docs acknowledge this, and the fixture docstring says to use the judge layer for robust detection. But users might reach for `context_references` as a quick sanity check and get misleading results.
- `total_tokens`, `total_prompt_tokens`, `total_completion_tokens` all return `None` for every `Conversation` where the agent uses `GenericAdapter` (which doesn't set token counts). This is expected behavior, but there's no warning or indication that tokens won't be populated unless you're using a real LLM adapter. Could trip up someone trying to write a token-budget assertion.
- F-005 (`checkagent init` broken) still not fixed. Checked on fresh upgrade — still generates projects that fail immediately.

**Overall impression:**
The Conversation API is the most polished feature so far. 11 new Conversation tests, 7 JSON Schema tests, 3 call_index tests, 2 error quality tests — 23 new tests, all green first try. Zero surprises during test writing except the `context_references` false-positive edge case. If the rest of the framework was at this level of polish, it would be production-ready.

**Next time I want to try:**
- Test the `judge` layer if it materializes (`checkagent.judge` module exists but is empty)
- Test `replay` layer — `checkagent.replay` module exists, explore what's there
- Look for the openai adapter mentioned in `checkagent init` output
- Write a test that asserts `total_tokens` once a real LLM adapter appears
- Test `Conversation.total_steps` across agents with multiple steps per turn

---

## Session 4 — 2026-04-05 (FaultInjector Fluent API + StreamCollector + Score)

**Upgraded from:** session-003 state (version still 0.0.1a1, fresh rebuild from git main)

**What I tried:**
- Re-ran all 47 existing tests — all pass, no regressions
- Verified F-005 (`checkagent init` broken) is still open: same two failures — `ModuleNotFoundError: No module named 'sample_agent'` without `pyproject.toml`, and `async def functions are not natively supported` without `asyncio_mode = "auto"`
- Explored the FaultInjector API in depth — found a full fluent builder API that wasn't there before
- Wrote 43 new tests across: FaultInjector fluent/inspection API (15), StreamCollector rich API (13), Conversation.total_steps (4), Score class (8), AgentRun.succeeded/error/tokens (4)
- Discovered and filed F-007 (ToolFaultBuilder naming inconsistency)
- Updated F-004 status to "partially resolved"

**What worked:**
- `FaultInjector` now has a complete fluent builder: `on_tool(name).timeout()`, `.rate_limit(after_n=N)`, `.slow(latency_ms=N)`, `.returns_malformed()`, `.returns_empty()`, `.intermittent(fail_rate, seed)`, and `on_llm().rate_limit()`, `.context_overflow()`, `.server_error(message)`, `.content_filter()`, `.partial_response()`. All 11 fault types covered.
- `check_tool_async()` exists alongside `check_tool()`. The async slow fault actually delays (real `asyncio.sleep`). The sync slow fault raises `ToolSlowError` immediately — a clean and documented tradeoff.
- Builder methods return the `FaultInjector` instance for optional chaining. Nice touch.
- New inspection API: `has_faults_for()`, `has_llm_faults()`, `reset_records()` (clears history but preserves config) vs `reset()` (clears everything) — the split is exactly right.
- `StreamCollector` is more complete than I expected: `time_to_first_token`, `tool_call_started(name)`, `has_error`, `error_events`, `reset()`, `of_type()`, `first_of_type()`. All correct.
- `Score` class is textbook Pydantic: `passed` auto-calculates from threshold via `model_post_init`, explicit `passed=True/False` overrides the auto-calculation, out-of-range values raise `ValidationError`. Clean.
- `Conversation.total_steps` works exactly as expected — sums steps across all turns, resets to 0 after `conv.reset()`.
- `AgentRun.succeeded` / `AgentRun.error` / `AgentRun.total_tokens` all behave correctly.

**What surprised me:**
- The fluent fault API existed but was completely undiscovered in prior sessions. I had only found `check_tool()` and logged F-004 as a pure DX issue. The fixtures docstring for `ap_fault` actually showed the fluent API all along — I just hadn't read it carefully. Lesson: always read fixture docstrings, not just the class API.
- `ToolFaultBuilder` uses `returns_empty()` and `returns_malformed()` (F-007), while `timeout()`, `rate_limit()`, `slow()`, `intermittent()` use plain verb forms. The inconsistency isn't harmful but would trip up a user trying to autocomplete — half the methods start with `returns_`, half don't.
- `checkagent.judge` and `checkagent.replay` are both completely empty modules. There's a `judge` layer registered as a valid layer in `VALID_LAYERS`, and `ap_fault.on_llm()` fixture docstring shows planned usage, but nothing is implemented. These look like reserved namespaces for future features.
- F-005 (`checkagent init` broken) is now on its fourth session without a fix. At this point it's not a "missed edge case" — it's actively blocking every new user who follows the documented quickstart.

**Overall impression:**
Strong session. The FaultInjector API is now very good — complete fault type coverage, fluent configuration, inspection, both sync and async modes. StreamCollector is similarly complete. The Score class is exactly what you'd want for eval-layer testing once the judge module materializes. All 90 tests pass. The main unresolved gap continues to be `checkagent init` (F-005) and the empty judge/replay modules — the framework's promise of layered testing (mock → replay → eval → judge) is only half-delivered so far.

**Next time I want to try:**
- Test the `@pytest.mark.safety(category, severity)` marker — it's registered in the plugin but never tested
- Test `@pytest.mark.cassette(path)` marker — registered but behavior unknown
- Test `ap_config` fixture — gives access to loaded `CheckAgentConfig`
- Probe `MockLLM.stream()` — does it exist? If so, test `ap_stream_collector` with a real `MockLLM` stream
- Test what happens when `assert_output_matches` is given a `dirty_equals` matcher

---

## Session 5 — 2026-04-05 (MockMCPServer, MockLLM.stream(), ap_config, markers)

**Upgraded from:** session-004 state → ed0b21a (clean install via uv pip)

**What I tried:**
- Upgraded checkagent from git main
- Re-ran all 90 existing tests — 7 failed immediately due to `ModuleNotFoundError: No module named 'jsonschema'` (F-008)
- Installed `jsonschema` manually — all 90 pass after that
- Discovered `MockMCPServer` and `ap_mock_mcp_server` fixture — a new MCP mock server
- Tested `MockLLM.stream()` + `stream_response()` — real multi-chunk streaming from MockLLM
- Tested `ap_config` fixture — exposes loaded `CheckAgentConfig`
- Tested `@pytest.mark.safety` and `@pytest.mark.cassette` markers
- Wrote 38 new tests across all of the above — all green on first run (after fixing a `complete()` return type assumption)
- Filed F-008 (undeclared `jsonschema` dependency)

**What worked:**
- `MockMCPServer` is comprehensive. Full JSON-RPC 2.0 coverage: `initialize`, `tools/list`, `tools/call` (success + configured error + unknown tool), notification handling (no response), `handle_raw` (JSON string in/out), and a correct parse error on malformed JSON. Protocol details are correct: `isError` in result (not at top-level), `content[0].type == "text"`, dict responses are JSON-encoded.
- `ap_mock_mcp_server` fixture works exactly as advertised — fresh instance per test, same API as `MockMCPServer`.
- `register_tool()` returns `self` for chaining, has `input_schema` defaulting to `{"type": "object", "properties": {}}` when not specified.
- Assertion helpers on `MockMCPServer` are solid: `assert_tool_called(times=N, with_args={})` is more capable than `MockTool`'s assertion API (it has per-arg checking and count checking in one call).
- `MockLLM.stream()` + `stream_response()` work exactly as documented. Multi-chunk streaming works, fallback to `add_rule` response works (single-chunk), fallback to default works. `streamed=True` correctly set on `LLMCall`.
- `stream_response` takes priority over `add_rule` for the same matching pattern — sensible behavior.
- `ap_config` returns a `CheckAgentConfig` with all the fields described in the source (version, asyncio_mode, defaults, providers, budget, quality_gates, cassettes, safety, pii, plugins).
- `@pytest.mark.safety` and `@pytest.mark.cassette` are registered — tests with these markers run without errors even though the backend modules are empty.

**What surprised me:**
- The `jsonschema` dependency regression (F-008): `assert_json_schema` had been scoring 5/5, but it only works because `jsonschema` happened to be in the environment from a prior install. The fresh upgrade wiped it and 7 tests failed. This is a silent breakage — no warning at import time, just a runtime `ImportError` when the function is called. Most users would see this on first run.
- `MockMCPServer.assert_tool_called` raises a plain `AssertionError`, not `StructuredAssertionError`. The rest of the framework (top-level `assert_tool_called`, `MockTool`) raises `StructuredAssertionError` — but `MockMCPServer` is inconsistent. Not filed as a separate finding since `AssertionError` is still correct behavior, but worth noting.
- The `safety` and `replay` modules remain completely empty — they're just namespace placeholders. `@pytest.mark.safety` and `@pytest.mark.cassette` are registered but have zero runtime behavior. No filtering, no reporting, nothing.
- `MockLLM.complete()` returns a plain `str`, not an `LLMResponse` or similar object. I assumed it would return a structured type (the internal `LLMCall` stores `response_text`), but the public API just hands back the raw string. Tripped up two tests before I checked the signature.
- `checkagent init` is now on its fifth session without being fixed. This is a critical path for new users.

**Overall impression:**
`MockMCPServer` is the standout new feature — it's well-designed, protocol-correct, and fully testable. If you're writing an agent that uses MCP tools, this gives you everything you need. `MockLLM.stream()` completes the streaming story — you can now test streaming agents end-to-end without `GenericAdapter`. The framework is maturing fast in the mock layer. The persistent gaps are: `jsonschema` as an undeclared dep (breaks fresh installs), `checkagent init` still broken, and empty safety/replay/judge modules that are clearly planned but not delivered. 128 tests pass total.

**Next time I want to try:**
- Test `assert_output_matches` with `dirty_equals` matchers (`IsStr`, `IsInt`, `IsApprox`, etc.)
- Test `MockMCPServer` in a full agent scenario (agent → MCP call → assert)
- Test `MockLLM.complete_sync()` — it exists but has never been tested
- Check if `checkagent init` is fixed
- Test `MockLLM.get_calls_matching()` — listed in attrs but never tested
- Test `MockTool.call_sync()` — listed in attrs but never tested

---

## Session 6 — 2026-04-05 (dirty_equals, sync APIs, MockMCPServer agent scenario)

**Upgraded from:** session-005 state (ed0b21a) → c32f77d (clean upgrade via uv pip)

**What I tried:**
- Upgraded checkagent from git main (ed0b21a → c32f77d)
- Re-ran all 128 existing tests — all pass, no regressions
- Tested `assert_output_matches` with all major dirty_equals matchers
- Tested `MockLLM.complete_sync()`, `get_calls_matching()`, `was_called_with()`
- Tested `MockTool.call_sync()` including schema validation and failure recording
- Tested `MockMCPServer` in a full multi-step agent scenario (search → summarize)
- Checked if `checkagent init` is fixed (it is not)
- Filed 3 new findings: F-009, F-010, F-011
- Wrote 31 new tests — all green (some required corrections after initial failures)
- Total: 159 tests pass

**What worked:**
- `assert_output_matches` + dirty_equals is excellent. `IsStr()`, `IsStr(regex=)`, `IsInt()`, `IsPositiveInt()`, `IsApprox(x, delta=d)`, `AnyThing()`, `IsInstance(T)` all work correctly. Multiple matchers in one pattern dict work. Error messages name the specific failing field: `output.count: 42 does not match IsStr()`. This is a genuine 5/5 experience.
- `MockLLM.complete_sync()` works identically to async `complete()` — same rule matching, same default fallback, same `LLMCall` recording. Useful in sync test helpers and for agents that don't use async.
- `get_calls_matching()` does substring search on `input_text`. Empty pattern returns all calls. Returns `list[LLMCall]` with full call details.
- `MockTool.call_sync()` is a clean sync alternative to `call()`. Schema validation fires the same way. Failed calls (ToolNotFoundError, ToolValidationError) are still recorded in call history — this is interesting: the call history includes all attempts, not just successful ones.
- `MockMCPServer` in a full agent scenario works well. `handle_message(dict)` is the correct method for dict input (not `handle()`). Chained tool calls work correctly — search result is passed to summarize, assertions verify the full flow. `MCPCallRecord.arguments` is an attribute (not subscriptable as dict).

**What surprised me:**
- `MockLLM.was_called_with(text)` does EXACT match on `input_text`, not substring. The name strongly implies containment semantics (like Mockito's `verify(mock).method(contains("text"))`), but it only returns `True` if the entire input string matches. Filed as F-009. The fix is already there: use `get_calls_matching()` for substring.
- `MockTool.assert_tool_called()` returns `None`, unlike the top-level `assert_tool_called(run, name)` which returns a `ToolCall`. Filed as F-010. The inconsistency means you can't write `tc = tool.assert_tool_called("search"); assert tc.arguments["q"] == "cats"` — you need `tool.last_call` instead.
- `MockMCPServer` has no `handle()` method — the dict-input method is named `handle_message()`. First instinct was `handle(dict)` which raises `AttributeError`. The split between `handle_raw(str)` and `handle_message(dict)` is sensible but needs better docs. Filed as F-011.
- `IsApprox` from dirty_equals uses `delta=` not `rel=` for its tolerance parameter. `IsApprox(1.0, rel=0.1)` raises `TypeError`. Minor but tripped me up.
- `checkagent init` is now in its sixth session without a fix. At this point I'd file a critical bug report upstream if this were a real project.

**Overall impression:**
Session was productive with no surprises on the happy path. The dirty_equals integration is the cleanest feature in the assertion layer — it works naturally and the error messages are excellent. The three new findings (F-009/010/011) are all low-severity DX issues, not bugs. The mock layer is now very mature: sync and async variants, full MCP protocol support, complete streaming. The framework's outstanding gap is still the missing judge/replay/eval implementations — the layered testing architecture is advertised but only the mock layer is delivered.

**Next time I want to try:**
- Try the `checkagent run` command with `--layer judge` to see how it handles the empty module
- Write a test that exercises `FaultInjector` with `MockTool.call_sync()` (manual guard pattern)
- Test `MockTool.strict_validation=False` — does it skip schema checks?
- Test `MockLLM.reset_calls()` and `MockTool.reset_calls()` — verify they clear call history without removing registered rules/tools
- Test `AgentRun` with multiple `Step` objects containing multiple `ToolCall` objects — does `assert_tool_called(run, name, call_index=N)` correctly index across steps?
- Probe whether there are any new exports in c32f77d that weren't in ed0b21a

---

## Session 7 — 2026-04-05 (GoldenDataset / datasets module, AgentInput)

**Upgraded from:** session-006 state (c32f77d) → c786006 (clean upgrade via uv pip)

**What I tried:**
- Upgraded checkagent from git main (c32f77d → c786006)
- Re-ran all 159 existing tests — all pass, no regressions
- Discovered new `checkagent.datasets` module with `GoldenDataset`, `TestCase`, `load_dataset`, `load_cases`, `parametrize_cases`
- Discovered `AgentInput` now exported from top-level `checkagent`
- Thoroughly tested the datasets module: construction, JSON loading, YAML loading, tag filtering, parametrize integration, error cases
- Wrote a golden dataset fixture file (`tests/golden/travel_agent.json`) and 35 new tests using it
- Filed 2 new findings: F-012 (YAML integer version rejected), F-013 (TestCase name triggers PytestCollectionWarning)
- Total: 194 tests pass

**What worked:**
- `GoldenDataset` / `TestCase` construction is clean. `TestCase` requires only `id` and `input`; everything else defaults sensibly (empty lists, None, empty dicts). Pydantic validation fires correctly on missing required fields.
- `load_dataset(path)` handles JSON and YAML files. Error messages are descriptive: `FileNotFoundError: Dataset file not found: ...`, `ValueError: Unsupported file format: .toml (expected .json, .yaml, or .yml)`. Duplicate case ID detection is built-in and raises `ValidationError` with the offending IDs listed.
- `load_cases(path, tags=None)` is a convenient wrapper. Tag filtering works as expected: `tags=None` and `tags=[]` both return all cases; `tags=["foo"]` returns cases matching ANY of the listed tags; nonexistent tags return `[]`.
- `parametrize_cases(path, tags=None)` is the standout feature. Returns `(argname, argvalues)` tuple exactly compatible with `@pytest.mark.parametrize(*parametrize_cases(...))`. pytest IDs are set to the case `id` fields — test output shows `test_foo[book-paris-001]` etc. Tag filtering works on the parametrize side too.
- Full end-to-end flow works: golden JSON file → `parametrize_cases` → parametrized test → `assert_tool_called` + `assert_output_matches`. This is exactly what data-driven agent testing should look like.
- `AgentInput` is a clean struct for structuring agent inputs. Stores query, context dict, conversation_history, and metadata. Importable from top-level `checkagent`.

**What surprised me:**
- `GoldenDataset.version` is typed as `str` with no coercion, so YAML files with an unquoted integer version field (`version: 2`) fail validation — filed as F-012. The workaround is to quote: `version: '2'`. This will catch every user who writes standard YAML since version numbers are overwhelmingly written without quotes.
- `TestCase` (from `checkagent.datasets`) has a class name that starts with `Test`, which triggers `PytestCollectionWarning: cannot collect test class 'TestCase' because it has a __init__ constructor`. This fires on any test file that imports `TestCase`. Filed as F-013. The class should be named `AgentTestCase`, `DatasetCase`, or similar to avoid the pytest naming conflict.
- The `parametrize_cases` return format (`(argname, argvalues)`) unpacks correctly with `*` in `pytest.mark.parametrize(*parametrize_cases(...))`. Very clean API — the design choice to return a tuple instead of just the values means it's a literal drop-in for `@pytest.mark.parametrize`.
- `AgentInput` was apparently exported all along (based on `__all__`), but never appeared in prior test files. Adding it to the test suite now.
- `checkagent init` still broken — now on its seventh session without a fix.

**Overall impression:**
The `datasets` module is a meaningful addition — it bridges the gap between "write individual test cases in pytest" and "run your agent against a golden dataset". The API is well-designed: file loading with validation, tag filtering, and pytest parametrize integration all work correctly. The two findings (F-012, F-013) are both fixable in under an hour. The `TestCase` naming issue is the more frustrating one — it's visible on every import. The framework is steadily filling out its feature surface; the persistence of F-005 (`checkagent init` broken) is the main blot on an otherwise improving story.

**Next time I want to try:**
- Test `MockTool.strict_validation=False` — does it skip schema checks entirely?
- Test `MockLLM.reset_calls()` and `MockTool.reset_calls()` — verify they clear history without removing rules/tools
- Try `checkagent run --layer judge` to see how it handles the still-empty judge module
- Write a test that exercises FaultInjector with `MockTool.call_sync()` (manual guard pattern)
- Test `AgentRun` with multiple Step objects and `assert_tool_called(call_index=N)` across steps
- Check if YAML coercion for `GoldenDataset.version` is fixed (F-012)
- Check if `TestCase` naming warning is resolved (F-013)

---

## Session 8 — 2026-04-05 (strict_validation, reset, FaultInjector+sync, multi-step indexing)

**Upgraded from:** c786006 → 8e6a0a8

**What I tried:**
- Upgraded checkagent from git main (c786006 → 8e6a0a8)
- Re-ran 159 existing tests — immediately hit two collection errors: (1) `dirty_equals` not installed, (2) `checkagent.datasets.GoldenDataset` missing
- Installed dirty_equals manually — session-006 tests recovered (159 pass)
- Confirmed that the entire datasets module was emptied in 8e6a0a8 — F-014 filed
- Tested `MockTool.strict_validation=False` — skips schema validation, call still recorded, works with both call() and call_sync()
- Tested `MockLLM.reset()` vs `reset_calls()` and `MockTool.reset()` vs `reset_calls()` — identical observable behavior (F-017)
- Tested FaultInjector with `MockTool.call_sync()` manual guard pattern — timeout, rate_limit, not_triggered_for_different_tool all work as expected
- Discovered `slow()` raises `ToolSlowError` in sync check_tool() context instead of sleeping (F-016)
- Tested `checkagent run --layer judge` — fails because test_session007.py collection error aborts run
- Tested `assert_tool_called(run, name, call_index=N)` across multiple Steps — indexes globally across steps, OOB gives clean error
- Wrote 31 new tests (27 pass, 4 xfailed documenting datasets regression)
- Total: 186 tests pass, 4 xfailed (datasets regression markers in test_session008.py), test_session007.py still uncollectable

**What surprised me:**
- The biggest shock: the entire datasets module was wiped in the upgrade. 35 session-007 tests are now uncollectable. This is a critical regression — the datasets feature was one of the best additions in the prior session.
- `dirty_equals` was never a checkagent dependency — it must have been manually installed in a prior session. When the venv needed it fresh this session, it wasn't there. Filed as F-015.
- `slow()` RAISES instead of sleeping in sync context. The error message says "use async for real delay" — so the design intent is that `check_tool_async()` does actual latency simulation. The sync version converts a latency sim into a call-abort. This is a sharp edge that will trip up users who write sync agents. Filed as F-016.
- `reset()` and `reset_calls()` are functionally identical on both MockLLM and MockTool — neither method removes registered rules or tools, both just clear call history. Having two methods with identical behavior and no documented distinction is pure confusion. Filed as F-017.
- `assert_tool_called(call_index=N)` correctly indexes tool calls across step boundaries, not per-step. So if step 0 has 2 `search` calls and step 1 has 1, then `call_index=2` would be out of bounds (only 2 search calls total). The `summarize` call in step 1 is at `call_index=0` since it's the only summarize call. Correct and useful behavior.

**Overall impression:**
This session was dominated by the datasets regression — a critical backward compatibility break in the upgrade from c786006 to 8e6a0a8. The rest of the mock layer continues to be solid: strict_validation, reset/reset_calls, and FaultInjector all work correctly (with the slow() async caveat). The multi-step call_index feature is exactly right. But losing the entire datasets module in an upgrade is a serious red flag for production-readiness. The framework is still alpha (0.0.1a1) but this kind of regression undermines trust. The datasets module was the most user-visible new feature in session-007; having it vanish in session-008 is the kind of thing that would make a real user uninstall.

**Next time I want to try:**
- Check if datasets regression (F-014) is fixed
- Check if dirty_equals dependency (F-015) is declared
- Test `check_tool_async()` with `slow()` to confirm it actually introduces latency (not just raises)
- Test FaultInjector `intermittent()` fault — what's the trigger probability semantics?
- Test `MockTool.was_called` — is this a predicate or an assertion?
- Test `MockTool.get_calls_for("name")` — returns all calls for a specific tool name
- Probe whether any new modules were added in 8e6a0a8 to replace what was removed
- Try `checkagent run --layer judge` once test_session007.py collection is fixed

---

## Session 10 — 2026-04-05 (eval metrics, aggregate stats, Evaluator/Registry, safety module)

**Upgraded from:** e38593a → 0a91584

**What I tried:**
- Upgraded checkagent from git main (e38593a → 0a91584)
- Re-ran 261 existing tests — all pass, no regressions from prior sessions
- Confirmed F-018 (ProviderPricing/BudgetConfig/BUILTIN_PRICING not at top-level) still open
- Discovered two major new feature areas: `checkagent.eval` metrics/aggregate/evaluator and `checkagent.safety` module
- Tested `checkagent run --layer judge tests/` — correctly deselects all 261 tests (no judge-layer tests exist yet)
- Wrote 96 new tests covering: eval metrics (step_efficiency, task_completion, tool_correctness, trajectory_match), aggregate functions (aggregate_scores, compute_step_stats, detect_regressions), RunSummary save/load, Evaluator/EvaluatorRegistry, ap_safety fixture, and all 5 safety evaluators
- Filed F-020 (eval classes not at top-level), F-021 (safety classes not at top-level), F-022 (ToolCallBoundaryValidator.evaluate() silent no-op), F-023 (Severity enum string values)
- Total: 357 tests pass, 0 failures

**What surprised me:**
- The `ap_safety` fixture is brand new and actually useful — it returns all 5 safety evaluators pre-configured. The `@pytest.mark.safety` marker was previously a no-op stub (scored 3/5), and now there are real safety evaluators — but the marker still doesn't auto-apply them. The fixture approach is more flexible.
- `Severity` enum uses string values (`'low'`, `'medium'`, `'high'`, `'critical'`) instead of integers. This means `Severity.HIGH > Severity.LOW` is False (string comparison is alphabetical — 'high' < 'low'!), and `Severity.HIGH.value >= 3` raises `TypeError`. The `SEVERITY_ORDER` dict exists internally for correct ordering, but it's not surfaced in the public API. Any user who tries to filter "HIGH or above" will be surprised. Filed as F-023.
- `ToolCallBoundaryValidator.evaluate(text)` is a silent pass-through — it always returns `passed=True` with no warning. The docstring says "Text-only evaluation is not meaningful for tool boundary checks" — but a user who calls the wrong method gets a false pass with no indication of the mistake. Compare to `SystemPromptLeakDetector` and others which DO implement `evaluate(text)` correctly. The asymmetry is confusing. Filed as F-022.
- `Evaluator` ABC + `EvaluatorRegistry` are a well-designed extension point. Subclassing is clean, `discover_entry_points()` enables plugin distribution, and `score_all()` runs all registered evaluators. Not at top-level (F-020) but the API itself is solid.
- `RunSummary.save()` and `.load()` enable baseline comparisons across test runs — this plus `detect_regressions()` creates a real regression detection pipeline. The design is good; the discoverability is poor (requires knowing the internal module path).
- F-005 (`checkagent init` still broken): not retested this session, but it's been open for 10 sessions now.

**Overall impression:**
This is the biggest feature drop yet. The eval metrics + safety module together represent a significant step toward production-readiness. The eval functions (`step_efficiency`, `task_completion`, `tool_correctness`, `trajectory_match`) are well-designed and cover the most common "did the agent do what we expected" questions. The safety module is surprisingly complete — 5 evaluators covering injection, PII, system prompt leakage, refusal compliance, and tool boundaries. All of it works correctly.

The persistent frustration is discoverability: none of these new classes are at the top-level `checkagent` namespace. Every feature release adds more internal module paths a user needs to memorize. The pattern has now repeated across 4 sessions (F-018, F-020, F-021). F-005 (`checkagent init` still broken) is the other lingering embarrassment — a new user's first experience remains broken.

**Next time I want to try:**
- Test `checkagent init` again — ten sessions and still broken (F-005)
- Try `ToolCallBoundaryValidator` with `path_arg_names` — what constitutes a "path-like" argument?
- Test `EvaluatorRegistry.discover_entry_points()` with an actual installed entry point
- Try building a real end-to-end eval scenario: datasets → parametrize_cases → trajectory_match + tool_correctness → aggregate_scores → RunSummary → detect_regressions
- Check if `@pytest.mark.safety` marker now does anything with the `ap_safety` fixture in scope
- Probe `OWASP_MAPPING` in the safety module
- Test path-boundary edge cases: symlinks, relative paths, subdirectory traversal

---

## Session 11 — 2026-04-05 (attack probe library, path boundary security, end-to-end eval pipeline)

**Upgraded from:** 0a91584 → latest main (still 0.0.1a1)

**What I tried:**
- Upgraded checkagent from git main
- Re-ran 357 existing tests — all pass, no regressions
- Confirmed open findings: F-005 (init still broken — 11th session), F-018, F-020, F-021, F-022, F-023 all still open
- Discovered new module: `checkagent.safety.probes` with attack probe library
- Wrote 65 new tests covering: attack probe library (Probe, ProbeSet), severity_meets_threshold, OWASP_MAPPING, end-to-end eval pipeline, ToolCallBoundaryValidator path edge cases
- Filed F-024 (path prefix confusion bug), F-025 (path traversal bypass bug), F-026 (probes not at top-level)
- Total: 422 tests pass, 0 failures

**What surprised me:**
- The attack probe library is a significant new addition — 35 injection probes (25 direct + 10 indirect) covering classic attacks, persona hijacking, system prompt extraction, and indirect injection via tool results/RAG/email/calendar. The API is clean and composable: `ProbeSet.filter(tags={"ignore"})`, `direct + indirect`, iteration works with `for probe in probe_set`. The `@pytest.mark.parametrize("attack", probes.injection.direct.all())` pattern works exactly as documented.
- `severity_meets_threshold(sev, threshold)` is a proper fix for F-023 — it correctly implements `SEVERITY_ORDER[sev] >= SEVERITY_ORDER[threshold]` so users can filter findings by severity without dealing with the string enum limitation. This function should have been the headline feature in the safety module release instead of buried in `checkagent.safety.taxonomy`.
- **Two security bugs in `ToolCallBoundaryValidator`**: (1) `/dataextra/file.txt` passes when `allowed_paths=["/data"]` — naive `startswith` without path separator check. (2) `/data/../etc/passwd` passes the same boundary — no path normalization. These are not just DX issues, they're security vulnerabilities in a module that exists specifically for security enforcement. Filed as F-024 and F-025.
- `aggregate_scores` takes `list[tuple[str, float, bool | None]]` not `list[Score]` — this is a surprising API choice. The `Score` object already has `name`, `value`, and `passed` fields, but `aggregate_scores` ignores them and requires you to unpack manually. The session-010 tests documented this correctly but I still fell into the trap when writing the pipeline tests.
- `TestCase.input` is typed as `str`, not `dict` or `Any`. This means you can't pass structured input (e.g., `{"query": "...", "context": {...}}`) to a TestCase. For multi-parameter agents, users must serialize to a string. This is a usability gap for anything beyond single-string queries.
- End-to-end pipeline (`TestCase → task_completion → aggregate_scores → RunSummary → detect_regressions`) works correctly when you use the right API shapes. The regression detection is elegant: `detect_regressions(current_aggs, baseline_aggs, threshold=0.1)` returns `list[RegressionResult]` with `.regressed`, `.metric_name`, `.delta` fields.
- F-005 (checkagent init) still broken in session 11. The generated tests still fail due to missing `asyncio_mode = "auto"` in pytest config. Eleven sessions. This is the most embarrassing persistent bug.

**Path boundary security analysis:**
```
allowed_paths=["/data"]

/data/subdir/file.txt     → passed=True   ✓ correct
/etc/passwd               → passed=False  ✓ correct
/dataextra/file.txt       → passed=True   ✗ should be False (F-024)
/data/../etc/passwd       → passed=True   ✗ should be False (F-025)
```
The implementation appears to use simple `str.startswith(allowed_path)` matching. Both bugs arise from not doing proper path handling. These are meaningful security vulnerabilities, not just edge cases.

**Overall impression:**
The attack probe library is the headline feature this session. It's well-designed, composable, and ready for `@pytest.mark.parametrize` usage. The `severity_meets_threshold` function quietly fixes the F-023 usability issue without requiring enum changes. 

The path boundary security bugs (F-024, F-025) are serious. `ToolCallBoundaryValidator` is positioned as a security feature, but it fails on basic adversarial paths. A user who trusts this for security enforcement is vulnerable. These should be P0 fixes.

F-005 continues to be the framework's longest-running embarrassment.

**Next time I want to try:**
- Test `ap_safety.assert_no_injection()` pattern — is there such a method? (implied by probe README example)
- Test `ProbeSet` with real agent + `PromptInjectionDetector.evaluate()` in parametrized test
- Test `checkagent run --layer safety` if it exists  
- Investigate whether `ToolCallBoundaryValidator` has a `normalize_paths` option we missed
- Probe whether `task_completion` correctly handles `expected_output_contains` list with multiple items (AND vs OR logic)
- Test `TestCase` with a string-serialized JSON input to work around the str-only input field
- Check if F-005 has any progress — maybe add a conftest manually to see if there's a hint

---

## Session 12 — 2026-04-05 (new probe categories, task_completion AND logic, F-027 silent field drop)

**Upgraded from:** 0a91584 → 27d4af4 (still 0.0.1a1)

**What I tried:**
- Upgraded checkagent from git main
- Re-ran 422 existing tests — all pass, no regressions
- Explored new probe categories in the safety module
- Investigated task_completion expected_output_contains list behavior
- Tested checkagent run --layer safety (invalid layer)
- Verified F-024, F-025 still open
- Checked F-005 (init): now generates conftest.py but it's empty — still broken
- Filed F-027: AgentRun/Step silently drop unknown fields
- Wrote 53 new tests; total now 475, all pass

**What I found:**

**Three new probe categories — probe library is now 68 total:**
- `probes_jailbreak` (15 probes): roleplay (7) + encoding (8). Roleplay attacks range from "you are NoPolicies" persona to screenwriter framing; encoding attacks cover base64, ROT13, hex, homoglyphs, zero-width chars. CRITICAL to LOW severity.
- `probes_pii` (10 probes): all PII extraction attempts — direct (email/phone), social engineering, bulk export, metadata harvesting, document export, credentials, financial, conversation replay. All HIGH severity.
- `probes_scope` (8 probes): boundary tests for actions outside agent scope — booking flights, bank transfers, SQL execution, medical advice, destructive actions. MEDIUM to CRITICAL severity.

Accessible via `from checkagent.safety import probes_jailbreak` (module object) or `from checkagent.safety.probes import jailbreak`. ProbeSet combination across categories works: `injection.all_probes + jailbreak.all_probes + pii.all_probes + scope.all_probes` → ProbeSet of 68. All 68 names are unique.

**F-027: AgentRun/Step silently drop unknown fields — worst DX issue I've found:**
`AgentRun(output='hello')` silently discards the value because the correct field is `final_output`. No ValidationError, no warning. `final_output` stays `None`. Same trap exists in `Step`: correct fields are `input_text`/`output_text`, not `input`/`output`. I burned time debugging this when testing task_completion — the metric kept seeing `None` output and scoring 0. Adding `extra='forbid'` to the model config would immediately expose this mistake.

**task_completion with list confirmed AND logic:**
`expected_output_contains=['42', 'Paris']` — all items must appear in `final_output`. Partial scores work: 1 of 2 matched → value=0.5. `threshold` applies to the fractional score. `check_no_error=True` (default) prepends an implicit error-check, so a 2-item list results in 3 checks total. This is documented via `metadata['checks']`.

**ProbeSet.filter() DX gotchas:**
- Tags filter uses OR logic: `filter(tags={'roleplay', 'persona'})` matches probes with ANY of those tags. Not AND. Not documented.
- Severity filter is case-sensitive for strings: `filter(severity='CRITICAL')` → 0 results. Must use lowercase `'critical'` or `Severity.CRITICAL` enum.

**checkagent run --layer safety:** Not a valid layer. `--layer` only accepts `mock|replay|eval|judge`. Safety tests currently have no designated layer marker, so they run in all layers.

**F-005 (init) progress note:** `checkagent init` now generates `tests/conftest.py` — this is new. But the conftest is empty (just a docstring). The fundamental bugs remain: no `pythonpath` config → `ModuleNotFoundError: No module named 'sample_agent'`. Twelfth session without a fix.

**F-024, F-025:** Both path boundary security bugs confirmed still open.

**Next time I want to try:**
- Test whether `ProbeSet.filter(tags={'a', 'b'})` AND logic can be achieved by chaining `.filter()` calls
- Test `ap_safety.assert_no_injection()` — does it exist?
- Try `checkagent run --layer judge` to confirm judge layer works
- Test `EvaluatorRegistry.discover_entry_points()` with an actual installed plugin
- Test what happens when you pass a ProbeSet directly to `@pytest.mark.parametrize` (does it unpack properly?)
- Test `task_completion` with `expected_output_equals` for exact match
- Check if there's a way to extend scope/boundary probes with custom actions

---

## Session 013 — 2026-04-05 (CI quality gates, ProbeSet AND logic, task_completion bugs)

**Upgraded from:** 27d4af4 → 735700f (still 0.0.1a1)
**New commit message:** "Add CI quality gates, PR reporter, and GitHub Action (F5.1, F5.3)"

**What I tried:**
- Upgraded checkagent from git main
- Re-ran 475 existing tests — all pass, no regressions
- Explored the new `checkagent.ci` module thoroughly
- Tested ProbeSet chained filter for AND logic (from session-012 "next time" list)
- Tested ProbeSet with `@pytest.mark.parametrize` directly
- Investigated `task_completion` with `expected_output_equals`
- Tested `checkagent run --layer judge`
- Filed F-028 through F-032

**What I found:**

**New `checkagent.ci` module — quality gates and PR reporter:**
The big new feature this session. `checkagent.ci` exposes `evaluate_gate`, `evaluate_gates`, `QualityGateReport`, `generate_pr_comment`, `scores_to_dict`, `GateResult`, `GateVerdict`, and a CI-focused `RunSummary`. 

The core gate logic is solid: min/max/range gates all work, `on_fail='block'|'warn'|'ignore'` all behave correctly (ignore → SKIPPED), missing metrics → SKIPPED. `QualityGateReport` has clean properties: `.passed` (False if any blocked), `.blocked_gates`, `.warned_gates`, `.passed_gates`, `.has_warnings`. Warnings don't block (`.passed` stays True with only warnings).

`generate_pr_comment` produces clean GitHub-flavored Markdown tables with emoji status markers (✅ ⚠️ ❌). Works with test_summary, gate_report, cost_report, or any combination. All-None produces a minimal header. Nice feature.

**F-028: CI types not at top-level (consistent with F-020/F-021):**
`from checkagent import evaluate_gates` → ImportError. Continuing the pattern.

**F-030: QualityGateEntry not in checkagent.ci.__all__:**
This is worse than F-028 — QualityGateEntry isn't even in `checkagent.ci.__all__`, so it's invisible to `from checkagent.ci import *` and tab completion on the ci module. You need `from checkagent.ci.quality_gate import QualityGateEntry`. Discovered this when trying to use the gates API.

**F-029: Two RunSummary classes, same name, incompatible:**
`checkagent.ci.RunSummary` (test run counts) and `checkagent.eval.aggregate.RunSummary` (eval aggregates) coexist. `generate_pr_comment(test_summary=eval_summary)` raises `AttributeError: 'RunSummary' object has no attribute 'total'`. No type hint enforcement prevents the mistake. Worst part: if you're using both eval and CI features in the same test suite, you have to alias one of them on import.

**ProbeSet chained filter for AND logic (confirmed!):**
`probeset.filter(tags={'a'}).filter(tags={'b'})` achieves AND logic. `jailbreak.all_probes.filter(tags={'roleplay'}).filter(tags={'persona'})` → 2 probes (both tags required). Single `filter(tags={'roleplay','persona'})` → 7 probes (either tag). Works cross-dimension too: `.filter(tags={'roleplay'}).filter(severity='critical')` gives roleplay AND critical. This should be documented.

**ProbeSet with pytest.mark.parametrize works natively:**
`@pytest.mark.parametrize("probe", list(injection.direct.filter(severity='critical')))` — 7 parametrized test cases, each with a Probe object. `str(probe)` returns `probe.name` (pytest-friendly hyphenated IDs like `ignore-previous-basic`). Clean DX once you know to call `list()` on the ProbeSet.

**F-032: injection.direct.all() returns list, not ProbeSet:**
`injection.direct.all()` (calling the `.all()` method) returns a Python list. `injection.all_probes` (module attribute) returns a ProbeSet. This makes `injection.direct.all() + jailbreak.all_probes` fail with `TypeError`. Burned time on this when writing the cross-module AND filter test. Use `injection.all_probes` for composition.

**F-031: task_completion None == '' bug:**
`task_completion(run, expected_output_equals='')` passes when `final_output=None`. The implementation normalizes None → '' before comparison. Confirmed via testing: `None == '0'` fails correctly; `None == ''` passes. Silently masks agents that produced no output. Filed as medium bug — could cause false positives in suites that check for "agent produced empty output successfully".

**task_completion with expected_output_equals:**
Case-sensitive exact match (as expected). Can be combined with `expected_output_contains` (both are checked, all must pass). Partial substrings don't match. Clean API overall, aside from the None bug.

**checkagent run --layer judge:**
Works. Deselects all 475 tests because none have `@pytest.mark.agent_test(layer='judge')`. Confirmed the layer filtering mechanism is functioning.

**Wrote 74 new tests; total now 549, all pass.**

**Next time I want to try:**
- Test the full CI pipeline end-to-end: write a conftest fixture that runs evaluate_gates after tests and can block CI
- Check if there's a pytest plugin hook that connects checkagent.ci to pytest exit codes
- Test `QualityGateEntry(on_fail='ignore')` more — does SKIPPED count toward report.passed?
- Test `generate_pr_comment` with regressions in the eval RunSummary (there's a `regressions` field)
- Investigate whether `ProbeSet.__add__` preserves ordering
- Check if there's a `checkagent.ci` pytest fixture (like `ap_quality_gates`)
- Test what happens with `@pytest.mark.agent_test(layer='judge')` — can we write a judge test?

---

## Session 014 — 2026-04-05

**Upgraded from:** 735700f → 90ab3c5 (still 0.0.1a1)
**New commit message:** (no new features detected — same top-level exports as session-013)

**What I tried:**
- Upgraded checkagent from git main (90ab3c5)
- Re-ran all 549 existing tests — all pass, no regressions
- Explored CI pipeline end-to-end: runs → metrics → aggregate → evaluate_gates → generate_pr_comment
- Investigated `generate_pr_comment` signature for eval/regression support
- Tested `ProbeSet + operator` for ordering guarantees and duplicate handling
- Wrote judge-layer marker tests — confirmed `@pytest.mark.agent_test(layer='judge')` works
- Investigated `checkagent run` default `-m agent_test` filter behavior
- Tested `RunSummary.save()` / `RunSummary.load()` round-trip with regressions
- Tested CI quality gates pytest plugin integration (or lack thereof)
- Tested `QualityGateEntry` missing-metric behavior
- Filed F-033 through F-035

**What I found:**

**Full CI pipeline works end-to-end (with correct dict API):**
`aggregate_scores()` takes `list[tuple[str, float, bool | None]]` — 3-tuple, not 2-tuple. `evaluate_gates()` takes `dict[str, QualityGateEntry]` — dict keyed by metric name, not a list. Once you get the API right the pipeline is clean: compute metric scores → aggregate → evaluate_gates → generate_pr_comment produces a valid GitHub-flavored Markdown comment.

**F-033: generate_pr_comment has no eval_summary or regressions param:**
The eval and CI modules are completely disconnected. `generate_pr_comment` signature is `(test_summary, gate_report, cost_report, title)`. No `eval_summary`, no `regressions`, no way to surface `detect_regressions()` output in PR comments. The workaround is to translate regressions into gate failures manually. This is a significant gap for the "CI/CD-first" claim.

**F-034: checkagent run silently runs only marked tests:**
`checkagent run tests/` runs 221 tests (only `@pytest.mark.agent_test`), while `pytest tests/` runs 549. The `build_pytest_args()` function injects `-m agent_test` by default. There's no warning about this deselection. Users following the README quickstart with `checkagent run` will silently miss 328 tests. This is a significant DX trap.

**F-035: RunSummary.load() drops regressions:**
`RunSummary.save()` calls `to_dict()` which includes regressions. The JSON file contains the regressions array. But `RunSummary.load()` never reads it back — `loaded.regressions` is always `[]`. The round-trip is asymmetric: save more than you load. Must recompute regressions after loading if you need them for `detect_regressions()`.

**ProbeSet + operator — ordering confirmed:**
`left + right` preserves insertion order: all left items first, then all right items. Works cross-category (injection + jailbreak). Duplicates ARE allowed (same probe can appear twice after `ps + ps`). Empty ProbeSet is identity for both `ps + empty` and `empty + ps`. `len(a + b) == len(a) + len(b)`. Clean implementation.

**Judge layer — empty module:**
`checkagent.judge` is an empty module. The layer is recognized by the plugin (`VALID_LAYERS = frozenset({'eval', 'judge', 'replay', 'mock'})`), filtering works correctly. But the judge module has zero functionality — no `ap_judge_llm` fixture, no `JudgeLLM` class, no statistical assertion helpers, nothing. Judge-layer tests can use any other fixture, but the framework provides no judge-specific primitives. This matches the earlier finding that `@pytest.mark.safety` and `@pytest.mark.cassette` exist as markers with no backing implementation.

**CI gates have no pytest exit code integration:**
The plugin has no `pytest_sessionfinish` or `pytest_terminal_summary` hooks. Quality gates defined in `checkagent.yml` are loaded into `ap_config.quality_gates` but never auto-evaluated. To make gate failures affect the build, users must write a session-scoped fixture in their conftest that calls `evaluate_gates()` and raises if not passed. This is significant friction for the "CI/CD-first" claim.

**Missing metric gate → SKIPPED (silent no-op):**
If a quality gate is configured for `task_completion` but the user accidentally passes `task_rate` as the score name, the gate is SKIPPED with `message="Metric 'task_completion' not found in scores"`. The report still passes. There's no validation that gate metric names match any known score name. Typos in gate config fail silently.

**Wrote 41 new tests; total now 590, all pass.**

**Next time I want to try:**
- Write a conftest.py that wires evaluate_gates() into pytest sessionfinish for real CI gate enforcement
- Test `checkagent run --layer judge` with actual judge-marked tests (just did this today, could expand)
- Test what `RunSummary.step_stats` does — can ComputeStepStats feed into it?
- Check if `checkagent.yml` quality_gates field is actually used anywhere in the CLI
- Investigate whether `checkagent run` with existing -m still merges with agent_test somehow
- Check `CostReport.budget_utilization()` with None total_cost edge case
- Test `FaultInjector.check_tool_async()` for real latency simulation (F-016 workaround)

---

## Session 015 — 2026-04-05

**Upgraded from:** 90ab3c5 → ed0b21a (still 0.0.1a1)

**What I tried:**
- Upgraded checkagent from git main (ed0b21a)
- Re-ran all existing tests — discovered F-036 (massive regression)
- Explored FaultInjector async fault behavior (check_tool_async + intermittent)
- Investigated AgentRun.input strict type enforcement
- Filed F-036, F-037, F-038

**What I found:**

**F-036: Catastrophic regression — second time in 15 sessions (also happened F-014):**
ed0b21a stripped the package back to just the core mock layer. Gone: all of datasets, eval.metrics, eval.aggregate, eval.evaluator, ci, safety, and cost tracking. The installed package now has only 19 Python files compared to 40+ in the previous session. The file list tells the story — no `cost.py`, no `metrics.py`, no `aggregate.py`, no safety subpackage files.

7 test files fail to collect (test_session007 through test_session014). 383 previously-passing tests uncollectable. Only 186/590 tests run. I added 10 xfail markers to test_session015.py to track the regression state without breaking CI.

This is the second time this pattern has appeared. Session 008 had xfail markers for F-014 (datasets regression). Those xfails were eventually promoted to passing (e38593a fixed F-014). I'm doing the same thing here — the xfails document the regression and will auto-promote when fixed.

**F-037: No check_llm_async() — async API is half-baked:**
`check_tool_async()` exists and works correctly — confirmed it produces real latency (80ms fast → 80ms sleep, not a raise). But `check_llm_async()` simply doesn't exist. Any async agent code that needs LLM fault simulation must fall back to sync `check_llm()`. This asymmetry is jarring given the async-first design of the rest of the framework.

**FaultInjector.check_tool_async() confirmed as F-016 workaround:**
For slow faults specifically, `await fault.check_tool_async("tool")` does the right thing: actual async sleep, no exception, records in `was_triggered`. Non-slow faults (timeout, rate_limit, etc.) still raise exceptions through `check_tool_async()` — which is correct behavior. The async path only matters for slow faults.

**Intermittent fault semantics confirmed:**
`intermittent(fail_rate=1.0)` → always raises `ToolIntermittentError`. `intermittent(fail_rate=0.0)` → never raises. `seed` kwarg enables deterministic behavior for repeatable tests. Both sync and async versions behave consistently.

**F-038: AgentRun.input strict typing:**
`AgentRun.input` is now typed as `AgentInput` (not `str | AgentInput`). Plain string input raises `ValidationError` with a message that says "Input should be a valid dictionary or instance of AgentInput" — no hint that `AgentInput(query="...")` is the fix. Dict coercion works (Pydantic model_validate). This is likely an intentional API tightening but the error message is not helpful.

**Wrote 31 tests (21 pass + 10 xfail). Total test files now: test_session015.py added.**
**With broken files excluded: 207 pass, 14 xfail.**

**Next time I want to try:**
- Wait for F-036 regression to be fixed — then re-run sessions 009-014
- When fixed: write conftest.py wiring evaluate_gates() into pytest sessionfinish
- When fixed: test CostReport.budget_utilization() with None total_cost edge case
- Test what `checkagent.yml` quality_gates config does in the CLI (when ci module is restored)
- When check_llm_async() is added, document it and test the full async fault pattern
- Check if AgentRun.input string coercion is added (F-038 resolution path)
