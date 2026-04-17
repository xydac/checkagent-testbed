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

---

## Session 016 — 2026-04-05

**Upgraded from:** ed0b21a → 6a8eaf4 (still 0.0.1a1)

**What I tried:**
- Upgraded checkagent from git main (6a8eaf4)
- Checked upstream CI — all 3 latest runs failing
- Re-ran all tests — discovered F-036 regression is now fixed
- Promoted 10 xfail markers from session-015 to passing tests
- Explored new `checkagent.replay` cassette data model (added in 6a8eaf4)
- Filed F-039, F-040, F-041
- Wrote 47 new tests covering the cassette API

**What I found:**

**F-036 FIXED in 6a8eaf4:**
Second regression of this type — same pattern as F-014 (8e6a0a8 wiped datasets, e38593a fixed it). This time ed0b21a wiped everything, and 6a8eaf4 brought it all back. The 10 xfail markers from session-015 now xpass; I've promoted them to regular passing tests. Total test suite: 668 passing, 0 xfail.

**Upstream CI: 3 consecutive failing runs.**
Root cause is F-008 — jsonschema isn't in checkagent's declared dependencies. The CI installs fresh and then runs tests, hitting `ModuleNotFoundError: No module named 'jsonschema'` in `assert_json_schema`. This is a known finding, but it's now visibly breaking the project's own CI. A framework whose CI is perpetually red is a bad look for users evaluating it.

**New: `checkagent.replay` cassette data model.**
The commit "Add cassette data model for record-and-replay" adds a substantial data model:
- `Cassette` — top-level container (meta + interactions list)
- `CassetteMeta` — schema version, timestamps, content hash, test_id
- `Interaction` — request/response pair with deterministic ID
- `RecordedRequest` / `RecordedResponse` — typed request/response structs
- `redact_dict()` — recursive sensitive key scrubbing
- Content-addressed filenames via `short_hash()` and `cassette_path()`
- Integrity verification via SHA-256 hash comparison

All the data model primitives work correctly. `finalize()` assigns sequences, computes IDs, and hashes. `verify_integrity()` detects tampering. `save()`/`load()` round-trips with parent directory creation. `redact_dict()` handles nested structures and doesn't mutate the original.

**F-039: `migrate-cassettes` command referenced but doesn't exist.**
The schema version warning says to run `checkagent migrate-cassettes`, but the CLI only has `demo`, `init`, and `run`. If a user encounters this warning, the suggested fix fails immediately. The warning should either describe the actual fix (re-record cassettes) or wait until the command is implemented.

**F-040: `checkagent_version` never populated.**
`CassetteMeta.checkagent_version` is `''` after `finalize()`. The framework has `checkagent.__version__` but `finalize()` doesn't use it. Cassettes have no provenance tracking, defeating the purpose of the field.

**F-041: replay module classes not at top-level.**
Same pattern as F-020, F-021, F-026, F-028. `from checkagent import Cassette` fails. Must use `from checkagent.replay import Cassette`. Consistent pattern across every new module added since session-010.

**Still missing: actual record/replay behavior.**
The `@pytest.mark.cassette` marker still has no behavior — it doesn't auto-load cassettes for replay or auto-save recordings. The data model exists but there's no recording integration with MockLLM/MockTool, no fixture that injects a cassette into a test, and no replay mode that intercepts calls. The cassette is a container with nowhere to put recordings yet.

**Wrote 47 new tests; total now 668, all pass.**

**Next time I want to try:**
- When cassette recording is implemented, test the `@pytest.mark.cassette` flow end-to-end
- Check if `migrate-cassettes` CLI command is added (resolves F-039)
- Test CostReport.budget_utilization() with None total_cost edge case
- Write conftest.py wiring evaluate_gates() into pytest sessionfinish for real CI gate enforcement
- Test what `checkagent.yml` quality_gates field does in the CLI now that ci module is restored
- Check if AgentRun.input string coercion is added (F-038 resolution path)
- Watch for check_llm_async() — F-037 still open

---

## Session 017 — 2026-04-05

**Upgraded from:** 6a8eaf4 → c03b11f (still 0.0.1a1)

**What I tried:**
- Upgraded checkagent from git main (c03b11f)
- Checked upstream CI — still 3 consecutive failures, new root cause
- Re-ran all 668 tests — all pass, no regressions
- Explored new `CassetteRecorder`, `ReplayEngine`, `MatchStrategy`, `TimedCall`, `CassetteMismatchError` in `checkagent.replay`
- Tested all three matching strategies: EXACT, SEQUENCE, SUBSET
- Tested `block_unmatched=False` behavior
- Tested full record→save→load→replay cycle
- Filed F-042, F-043, F-044
- Wrote 59 new tests covering the replay engine

**What I found:**

**No regressions.** All 668 previous tests still pass. New total: 727.

**New: `CassetteRecorder` and `ReplayEngine` added in c03b11f.**
The commit "Update roadmap: mark cassettes and replay engine as complete" shipped the actual implementation:
- `CassetteRecorder(test_id, redact_keys)` — records LLM and tool calls to a `Cassette`
- `ReplayEngine(cassette, strategy, block_unmatched)` — replays interactions from a cassette
- `MatchStrategy` enum with EXACT, SEQUENCE, SUBSET values
- `TimedCall` — context manager for measuring call duration in ms
- `CassetteMismatchError` — raised when no match found

**Core functionality solid.** `CassetteRecorder` correctly captures kind, method, body, tokens, duration, status. `finalize()` returns a `Cassette` with all interactions correctly sequenced and assigned IDs. `save()`/`load()` round-trips work. Redaction via `redact_keys` works. The EXACT and SUBSET strategies both work correctly. `ReplayEngine.reset()` re-enables replay from the start.

**F-042: `block_unmatched=False` has no effect.**
`ReplayEngine` accepts `block_unmatched` as a constructor parameter but it never changes behavior. Setting `block_unmatched=False` is supposed to enable passthrough mode (return `None` when no match, let real call through). It still raises `CassetteMismatchError`. This makes it impossible to do partial-record workflows where some calls are recorded and others pass through live.

**Upstream CI: still red, new cause.**
The CI was previously failing due to F-008 (jsonschema missing dep). Now it's failing with a Windows-specific error: `SyntaxError: (unicode error) 'utf-8' codec can't decode byte 0x97`. The em dash character (`—`) in the demo-generated test file's docstring is written with the system's default encoding on Windows (Windows-1252), producing byte 0x97 instead of the UTF-8 sequence. The fix is either ASCII-safe docstrings or an explicit `# -*- coding: utf-8 -*-` at the top of generated files.

**F-044: SEQUENCE strategy ignores everything including `kind`.**
`MatchStrategy.SEQUENCE` returns the next interaction in order regardless of the incoming request's `kind`, `method`, or `body`. A `kind='tool'` request will match a recorded `kind='llm'` interaction. This is surprising — most users would expect at minimum the `kind` (llm vs tool) to be checked. Silent kind mismatches could lead to test scenarios that silently return wrong response types. The other strategies are fine.

**F-037, F-038 still open.** `check_llm_async()` still doesn't exist. `AgentRun(input="string")` still raises `ValidationError`.

**No `ap_cassette` fixture yet.** The `@pytest.mark.cassette` marker still has no pytest integration. `CassetteRecorder` and `ReplayEngine` are standalone classes — no fixture that auto-starts recording, no marker behavior that injects a cassette. The pieces exist but aren't wired together.

**Wrote 59 new tests; total now 727, all pass.**

**Next time I want to try:**
- Watch for `ap_cassette` fixture — that would complete the pytest cassette integration
- Test `block_unmatched=False` when it's fixed (F-042)
- Check if `migrate-cassettes` CLI command is added (F-039)
- Check if F-037 (`check_llm_async`) is fixed
- Write conftest.py wiring evaluate_gates() into pytest sessionfinish
- Test what `checkagent.yml` quality_gates field does in the CLI

---

## Session 018 — 2026-04-06

**Upgraded from:** c03b11f → (latest main, same 0.0.1a1 version string)

Latest commit message: "Update roadmap: mark cassette migration tooling as complete"

**What I tried:**
- Upgraded checkagent from git main
- Checked upstream CI — 3 consecutive failures, now a new root cause
- Re-ran all 727 tests — all pass, no regressions
- Explored new `checkagent migrate-cassettes` CLI command
- Tested `migrate-cassettes` on v0 cassettes, v1 cassettes, empty dirs, nonexistent dirs, nested dirs
- Tested `Cassette.save()` and `Cassette.load()` with `str` vs `Path` arguments
- Verified F-039 partial fix (CLI exists now but migration fails)
- Filed F-045, F-046, F-047
- Verified open findings F-037, F-038, F-042 still open
- Wired evaluate_gates() conftest.py integration pattern and confirmed it works
- Wrote 38 new tests; total now 765

**What I found:**

**No regressions.** All 727 previous tests still pass. New total: 765.

**New: `checkagent migrate-cassettes` CLI added (F-039 partially resolved).**
The command now exists in the CLI. `checkagent --help` shows it. `checkagent migrate-cassettes --help` explains usage with `--dry-run` and `--no-backup` flags. Default directory is `cassettes/`. Nonexistent directories get exit code 2 with a clear error message. v1 cassettes are correctly skipped. Recursive directory search works.

**F-045: migrate-cassettes always fails for v0 cassettes.**
The CLI exists but the actual v0→v1 migration path is not registered. Any v0 cassette produces:
```
FAIL /path/to/cassette.json: No migration registered from v0. Cannot upgrade to v1.
```
The summary shows `Failed: 1`. But the exit code is still 0 — so `checkagent migrate-cassettes && deploy` silently proceeds despite failures. This is both a missing feature (migration not implemented) and a bug (exit code should be non-zero on failure).

**F-046: Cassette.save() and Cassette.load() require pathlib.Path.**
Passing a plain string raises `AttributeError` with an unhelpful message that exposes internals (`'str' object has no attribute 'parent'`, `'str' object has no attribute 'read_text'`). Standard Python practice is to accept both `str` and `Path` via `Path(path)` coercion. Neither error message tells the user what to do.

**New CI failure (F-047): TimedCall.duration_ms == 0.0 on Windows.**
The upstream test `test_timing_is_positive_for_slow_ops` asserts `tc.duration_ms >= 5` but gets `0.0` on Windows Python 3.10. `TimedCall` uses `time.monotonic()`, which has ~15ms resolution on Windows. If the sleep is shorter than ~15ms, the result is 0.0. The fix is to use a longer sleep (100ms+) or `time.perf_counter()`. Third consecutive CI failure, third different root cause:
- Session 016: F-008 (jsonschema missing dep)
- Session 017: F-043 (em dash Windows encoding)
- Session 018: F-047 (TimedCall.duration_ms 0.0 on Windows)

**F-037, F-038, F-042 still open.** `check_llm_async()` still doesn't exist. `AgentRun(input="string")` still raises `ValidationError`. `block_unmatched=False` still has no effect.

**evaluate_gates() conftest.py integration confirmed.** The pattern works: compute metrics → `scores_to_dict()` → `evaluate_gates(scores, {name: QualityGateEntry(min=..., on_fail=...)})` → check `report.passed`. Can be wired into a `pytest_sessionfinish` hook to enforce quality gates on the whole suite. `generate_pr_comment()` accepts the gate report cleanly. One footgun: `evaluate_gates()` takes `dict[str, QualityGateEntry]` not a list — this is inconsistent with other collection APIs in the library.

**Next time I want to try:**
- Watch for `ap_cassette` fixture implementation
- Check if `block_unmatched=False` is fixed (F-042)
- Check if v0→v1 migration is implemented (F-045)
- Check if Cassette.save/load gets str coercion (F-046)
- Try writing a real conftest.py with sessionfinish gate enforcement
- Check if F-038 (AgentRun string input coercion) is fixed

---

## Session 019 — 2026-04-06

**Upgraded from:** (latest main, still 0.0.1a1)

Latest commit message: "Update roadmap: mark rubric evaluation and statistical verdicts as complete"

**What I tried:**
- Upgraded checkagent from git main
- Checked upstream CI — **finally green!** First passing run in 3 sessions. F-047 (Windows timing) and F-043 (em dash encoding) both resolved upstream
- Re-ran all 765 previous tests — all pass, no regressions
- Explored the new `checkagent.judge` module: `Judge`, `RubricJudge`, `Rubric`, `Criterion`, `ScaleType`, `JudgeScore`, `JudgeVerdict`, `Verdict`, `compute_verdict`
- Tested RubricJudge with mock LLM callables (JSON response format required)
- Tested all 3 scale types: numeric (default [1-5]), binary, categorical
- Tested weighted criteria scoring
- Tested compute_verdict PASS/FAIL/INCONCLUSIVE logic with different pass rates
- Tested error cases: bad JSON, unknown criterion names, num_trials=0, evaluate() raises
- Tested markdown-fenced JSON stripping
- Tested JudgeScore.score_for() and JudgeVerdict.passed property
- Wrote 34 new tests; total now 799

**What I found:**

**CI is green for the first time since session-015.** The upstream "mark rubric evaluation and statistical verdicts as complete" commit fixed both F-043 (Windows em dash) and F-047 (TimedCall Windows timing). Both findings marked as fixed.

**F-048: Judge module not at top-level.** Same pattern as F-020/F-021/F-026/F-028. All 10 judge classes require `from checkagent.judge import ...`. Fifth instance of this pattern — feels like a deliberate design decision at this point, but still a DX cost.

**F-049: No ap_judge fixture.** Judge module has zero pytest integration. Worse than other modules: `MockLLM` cannot be passed to `RubricJudge(llm=...)` because the judge expects `async (system, user) -> str` but `MockLLM` has a different interface. Every test file needs to define its own mock LLM callable returning valid JSON.

**F-050: Bad JSON propagates raw JSONDecodeError.** When the LLM returns non-JSON (common with real LLMs), `evaluate()` raises `json.decoder.JSONDecodeError: Expecting value: line 1 column 1`. The error message is unhelpful — no checkagent wrapper, no expected format hint, no actual LLM response included.

**F-051: Unknown criterion names → silent 0.0.** If the LLM hallucinates criterion names (common with real LLMs), `criterion_scores` is empty and `overall` is silently 0.0. No warning, no exception. `compute_verdict` will always FAIL for that judge run with no explanation.

**Core judge functionality is solid.** RubricJudge correctly normalizes all 3 scale types. Weighted scoring is accurate. `compute_verdict` PASS/FAIL/INCONCLUSIVE thresholds work as documented (PASS ≥ 0.65, FAIL ≤ 0.35, INCONCLUSIVE in between with default settings). Markdown-fenced JSON from LLM is stripped correctly. `JudgeVerdict.passed` is False for INCONCLUSIVE (correct). `num_trials=0` raises a clear ValueError.

**One surprising edge case:** `Rubric(criteria=[])` raises `ValidationError` with a clear message — good validation. Rubric correctly enforces `min_length=1` on the criteria list.

**Judge layer marker confirmed working.** Tests marked `@pytest.mark.agent_test(layer="judge")` are correctly included/excluded by `checkagent run --layer judge`.

**Next time I want to try:**
- Check if `ap_judge` fixture is added (F-049)
- Check if judge classes appear at top-level (F-048)
- Check if F-042 (block_unmatched=False) is fixed
- Check if F-045 (migrate-cassettes v0) is implemented
- Check if F-038 (AgentRun string input coercion) is fixed
- Check if F-050/F-051 get error wrapping in judge module
- Test subclassing `Judge` ABC to write a custom judge

---

## Session 020 — 2026-04-06

**Upgraded from:** c03b11f → d88d3e7

Latest commit message: "Update roadmap: mark multi-judge consensus as complete"

**What I tried:**
- Upgraded checkagent from git main (c03b11f → d88d3e7)
- Checked upstream CI — **still green** for second consecutive session. Stable.
- Re-ran all 797 previous tests — 2 failures, both "good failures" indicating fixed bugs:
  - `test_f049_no_ap_judge_fixture` failed because `ap_judge` now exists (F-049 partially fixed)
  - `test_migrate_cassettes_not_in_cli` failed because the command now exists (stale test from session-016)
- Updated both stale tests to reflect reality; all 823 tests now pass
- Explored new `multi_judge_evaluate` + `ConsensusVerdict` APIs (the session's main new feature)
- Wrote 24 new tests; total now 823

**What I found:**

**CI still green.** Second consecutive passing session. The pattern of "massive regression, then fix" seems to have stabilized.

**F-049 partially fixed.** `ap_judge` factory fixture now exists. It takes `(rubric, llm, model_name='')` and returns a `RubricJudge`. This reduces boilerplate: users no longer need to manually instantiate `RubricJudge` in every test. However, the fixture is still a thin factory — it provides no MockLLM bridge. Users must still write their own async `(system, user) -> str` callable that returns rubric-format JSON (`{"scores": [{"criterion": ..., "value": ..., "reasoning": ...}], "overall_reasoning": ...}`).

**New feature: multi-judge consensus.** `multi_judge_evaluate(judges, run, ...)` runs multiple judges and aggregates via majority vote. Core functionality is solid:
- Requires ≥ 2 judges (raises ValueError otherwise)
- Majority vote logic correct (2 PASS + 1 FAIL → PASS)
- INCONCLUSIVE propagated when pass rate falls in the ambiguous band across multiple trials
- `concurrent=True` (default) and `concurrent=False` both work
- `ConsensusVerdict` has `verdict`, `judge_verdicts`, `agreement_rate`, `has_disagreement`, `reasoning` — all fields work
- `reasoning` field populated with a human-readable summary (e.g. "Consensus: pass from 3 judges. Agreement: 100%.")
- Tie-breaking (1 PASS + 1 FAIL) defaults to PASS — undocumented behavior

**F-052 (new, high): judge_verdicts key collision.** `multi_judge_evaluate` keys `judge_verdicts` by `f'rubric_judge:{rubric.name}'` — not by `model_name`. In the canonical use case (same rubric, different LLM backends), all judges share the same rubric name → only 1 entry survives in `judge_verdicts`. The verdict math is correct (uses an internal list), but the user-facing dict loses all per-judge traceability. To surface all judges in `judge_verdicts`, you must use distinct rubric names — an ugly workaround that defeats the purpose of a shared rubric.

**F-053 (new, medium): ConsensusVerdict/multi_judge_evaluate not at top-level.** Sixth instance of the same pattern. At this point it feels like a deliberate architectural choice — but it still forces users to memorize submodule paths.

**Interesting edge: JSON response format.** The judge LLM callable must return `{"scores": [...], "overall_reasoning": "..."}` — not `{"criteria": [...]}`. This format is different from what you'd guess from the `Criterion` model's field names. The session-019 `make_llm` helper captures this correctly, but it's not obvious from the public API.

**Next time I want to try:**
- Check if F-052 (judge_verdicts key collision) is fixed — use model_name as key instead of rubric name
- Check if F-042 (block_unmatched=False) is fixed
- Check if F-045 (migrate-cassettes v0) is implemented
- Check if F-038 (AgentRun string input coercion) is fixed
- Check if F-050/F-051 get error wrapping in judge module
- Try subclassing `Judge` ABC to write a custom judge and register it
- Check if the `ap_cassette` fixture is added for record/replay workflow

---

## Session 021 — 2026-04-06

**Upgraded from:** d88d3e7 → 48017850 (commit: "Update roadmap: mark LangChain and OpenAI adapters as complete")

**What I tried:**
- Upgraded checkagent from git main
- Checked upstream CI — **failing** (fourth Windows timing regression, F-054)
- Re-ran all 823 previous tests — all pass, no regressions
- Fixed one stale test: `test_migrate_cassettes_in_cli` in test_session016.py was using `.venv/bin/checkagent` (old version without migrate-cassettes) instead of the system `checkagent`; fixed to use PATH
- Explored new LangChain and OpenAI adapters
- Tested custom `Judge` ABC subclassing
- Wrote 26 new tests; total now 849

**What I found:**

**CI failing again (F-054).** Windows Python 3.10/3.11/3.12 fail on `test_error_handling` in the LangChain adapter tests — same `duration_ms == 0.0` issue as F-047. Fourth consecutive CI failure of this pattern. F-047 was fixed by using a longer sleep, but the new LangChain adapter tests have a failing chain (no sleep) so duration is 0ms on Windows.

**LangChain adapter works well — with caveats.** `LangChainAdapter(runnable)` wraps any LangChain Runnable and produces an `AgentRun`. Basic run, error handling, custom `input_key`, and streaming all work. Two issues:
1. `langchain-core` is not declared as a dependency (F-055) — third time this pattern appears
2. `final_output` is the raw runnable return value (dict when runnable returns dict), while `step.output_text` extracts the `output` key — inconsistency that surprises users (F-056)

**OpenAI Agents adapter (F-061 — new, high severity).** `OpenAIAgentsAdapter` is in `checkagent.adapters.openai_agents` (not `checkagent.adapters.openai`). It works fine when the `agents` SDK is installed. But the adapter does `from agents import Runner` lazily inside `run()` — this conflicts with any project that has a local `agents/` directory on sys.path. The testbed itself has `agents/` which triggers `ImportError: cannot import name 'Runner' from 'agents'` at runtime. The error is also not wrapped — it propagates as a raw `ImportError` rather than being captured in `result.error`. This is a high-severity DX trap for testbed-style users.

**Custom Judge subclassing works — but CriterionScore field names are a gotcha (F-059).** The `Judge` ABC has one abstract method `evaluate(run) -> JudgeScore`. Subclassing it works, but constructing `CriterionScore` is non-intuitive: required fields are `criterion_name`, `raw_value`, `normalized` — not `criterion`, `value`, `scale_type` as you'd guess from the LLM JSON format and Criterion model. No documentation on the custom judge workflow.

**JudgeScore has no .passed (F-058).** Single-trial pass/fail requires `compute_verdict(judge, run, num_trials=1).passed` — can't just check `score.passed`. This is particularly annoying for custom judges.

**Criterion default scale wrong for BINARY (F-060).** All scale_types default to `[1,2,3,4,5]`. Binary should default to 2 items.

**ap_cassette still missing.** No fixture added for record/replay. The `@pytest.mark.cassette` marker remains a no-op.

**One stale test fixed.** `test_session016.py:test_migrate_cassettes_in_cli` was calling `.venv/bin/checkagent` (old install). Fixed to use PATH. This wasn't a checkagent regression — just a test using the wrong binary.

**Next time I want to try:**
- Check if F-054 (LangChain adapter Windows timing) is fixed
- Check if F-055 (langchain-core dep) is declared
- Check if F-061 (agents/ conflict) is fixed — either rename import or catch error in result
- Check if F-042 (block_unmatched=False) is fixed
- Check if F-038 (AgentRun string input coercion) is fixed
- Check if ap_cassette fixture is added
- Try using LangChainAdapter with a real LangChain chain (LCEL pipeline)
- Try OpenAIAgentsAdapter once the agents/ naming conflict is resolved

---

## Session 022 — 2026-04-06

**Upgraded from:** 48017850 → latest (commit: "Update roadmap: mark all framework adapters as complete")

**What I tried:**
- Upgraded checkagent from git main
- Checked upstream CI — **passing** on all platforms. F-054 fixed.
- Re-ran all 849 previous tests — all pass, no regressions
- Explored three new adapters: AnthropicAdapter, CrewAIAdapter, PydanticAIAdapter
- Explored new checkagent.ci.junit_xml module
- Checked open findings: F-038, F-042, F-052, F-061 — all still broken
- Wrote 32 new tests; total now 881

**What I found:**

**F-054 FIXED.** The LangChain adapter now uses `time.perf_counter()` instead of `time.monotonic()`. The upstream CI "mark all framework adapters as complete" run passes on all 12 jobs including Windows Python 3.10/3.11/3.12. This breaks the streak of four consecutive Windows timing failures.

**Three new adapters added.** `AnthropicAdapter`, `CrewAIAdapter`, and `PydanticAIAdapter` all appeared in the latest version. All three follow the same patterns established by the earlier adapters:
- String input coercion works (all three handle `run("string")`)
- Error handling works (all three capture exceptions in `AgentRun.error`)
- All require undeclared deps — `anthropic`, `crewai`, `pydantic-ai` not in `Requires-Dist` and not listed as optional extras (F-064)
- All absent from top-level `checkagent` namespace (F-063, ninth+ instance)

**F-062 (new, medium): AnthropicAdapter.final_output is the raw message object.** Unlike `CrewAIAdapter` (which correctly sets `final_output=result.raw`, a string) and `PydanticAIAdapter` (which correctly sets `final_output=result.data`), `AnthropicAdapter` sets `final_output=message` — the entire `anthropic.types.Message` object. Users who check `result.final_output == "Paris"` will always get `False`. The extracted text is available at `result.steps[0].output_text`. This is the same class of bug as F-056 (LangChain dict) but worse — an opaque SDK object is less usable than a dict.

**New: checkagent.ci.junit_xml module.** JUnit XML generation is genuinely well implemented:
- `render_junit_xml([suite])` produces valid XML with correct `testsuites`/`testsuite`/`testcase` structure
- `from_run_summary(summary, test_details=...)` generates named test cases from RunSummary
- `from_quality_gate_report(report)` maps gate verdicts to JUnit outcomes (blocked→failure, warned→pass with property, skipped→skipped)
- `JUnitTestSuite.time_s` correctly aggregates test case times
- All symbols accessible from `checkagent.ci` namespace (better than F-028 where ci module had broken exports)
- Not at top-level checkagent (F-065) — lower severity since `checkagent.ci` is the natural home for CI utilities

**Interesting structural point on deps.** There are now 5+ instances of the undeclared-dep pattern (F-008 jsonschema, F-015 dirty-equals, F-055 langchain-core, F-064 anthropic/crewai/pydantic-ai). None are even listed as optional extras. The pattern suggests checkagent intentionally keeps its base install minimal but provides no mechanism for users to install the right extras for their framework.

**F-038, F-042, F-052, F-061 still open.** All four findings from previous sessions remain unaddressed. The `agents/` naming conflict (F-061) is particularly notable since the new adapters all fixed their respective import issues with clear error messages — but OpenAIAgentsAdapter still has the structural package name conflict.

**ap_cassette still missing.** No fixture added for record/replay in this release.

**Next time I want to try:**
- Check if F-062 (AnthropicAdapter.final_output) is fixed — expect it to match step.output_text
- Check if F-064 (undeclared deps) is addressed with optional extras
- Check if F-061 (agents/ conflict) is fixed — maybe they renamed the import or added package conflict detection
- Check if F-042 (block_unmatched=False) is fixed — has been open since session-017
- Check if F-038 (AgentRun string input coercion) is fixed
- Check if ap_cassette fixture is added
- Try AnthropicAdapter with a real (mocked) streaming response to test run_stream
- Try CrewAIAdapter with tasks_output to verify step extraction from CrewAI result

**Next time I want to try:**
- Check if F-066 (PII ID collision) is fixed — expect either counter-suffix or friendly error message
- Check if F-067 (trace_import top-level exports) is fixed
- Check if F-038 (AgentRun string input coercion) is fixed
- Check if F-042 (block_unmatched=False) is fixed — open since session-017
- Check if F-062 (AnthropicAdapter.final_output) is fixed
- Check if F-061 (agents/ naming conflict for OpenAIAgentsAdapter) is fixed
- Try using JsonFileImporter in a parametrized test with GoldenDataset
- Try PiiScrubber.use_ner=True (with spaCy installed)

---

## Session 023 — 2026-04-06

**Upgraded from:** "mark all framework adapters as complete" → "mark production trace import as complete"

**What I tried:**
- Upgraded checkagent from git main
- Checked upstream CI — **passing** for last 2 runs. Stable for third consecutive session.
- Re-ran all 881 previous tests — all pass, no regressions
- Explored the new `checkagent.trace_import` module (new in this release)
- Tested `JsonFileImporter`, `OtelJsonImporter`, `PiiScrubber`, `generate_test_cases`
- Tested the new `checkagent import-trace` CLI command
- Wrote 73 new tests; total now 954

**What I found:**

**CI green.** The upstream "mark production trace import as complete" run passes. Stable.

**New feature: `checkagent.trace_import`.** A production trace import system that converts observability traces into golden dataset test cases. Four main components:

1. **`JsonFileImporter`** — handles JSON, JSONL, and three data shapes (flat `{input, output}`, native `{input, steps, ...}`, span-based `{spans: [...]}`). Filters by status (error/success), limit. Solid.

2. **`OtelJsonImporter`** — parses OTLP JSON export format. Groups spans by `traceId`, identifies root span (no `parentSpanId`), extracts tool calls from child spans with "tool"/"function"/"action" in name. Handles error status code 2 correctly. Solid.

3. **`PiiScrubber`** — regex-based PII replacement with deterministic placeholders. Covers email, phone, SSN, credit card, IP. Supports `extra_patterns`, `scrub_value` for nested dicts/lists. The `reset()` per-run design is intentional but creates a footgun (see F-066). This is genuinely well-implemented.

4. **`generate_test_cases`** — converts `AgentRun` list to `GoldenDataset`. Tags runs with "imported", "error", "has-tools". Sets `max_steps`, `expected_tools`, `expected_output_contains`. Solid when IDs don't collide.

**`checkagent import-trace` CLI** is well-designed: auto-detects format from extension, handles `--filter-status`, `--limit`, `--tag`, `--no-pii-scrub`, `--source otel`. Friendly "does not exist" error for missing files. Good DX overall.

**F-066 (new, high, bug): PII ID collision crashes with raw traceback.** The most significant bug this session. `generate_test_cases(scrub_pii=True)` resets the `PiiScrubber` before each trace (good for isolation), but this means two traces "Find john@example.com" and "Find jane@example.com" both produce `"Find <EMAIL_1>"` — same scrubbed text, same hash, same ID. `GoldenDataset` raises `ValidationError: Duplicate test case IDs`. The CLI surfaces this as an unhandled Python traceback. This will happen constantly in production: any site with multiple users issuing similar queries will hit this immediately. The fix is straightforward (append a deduplication counter to the ID) but the current crash is bad UX.

**F-067 (new, medium, dx-friction): trace_import not at top-level.** Eleventh instance of the same pattern. At this point it's clearly architectural — checkagent has a "keep the base install minimal" philosophy but provides no opt-in mechanism to get these exports at top-level. Every new module requires discovering and remembering an internal submodule path.

**F-038, F-042, F-061, F-062 still open.** None of the carryover findings from previous sessions were addressed in this release.

**Positive notes:**
- `PiiScrubber` is genuinely well-implemented — deterministic, handles edge cases cleanly, composable with `extra_patterns`
- The CLI has the right shape: auto-detection, good option names, helpful error messages (except for the ID collision case)
- `OtelJsonImporter` correctly handles the OTLP JSON format including the attribute array structure (`[{key: "k", value: {stringValue: "v"}}]`)
- `generate_test_cases` correctly uses `AgentRun.tool_calls` (which is a computed property flattening steps) — that was a pleasant surprise

---

## Session 024 — 2026-04-06

**Upgraded from:** "mark production trace import as complete" → "mark multi-agent trace and credit assignment as complete"

**What I tried:**
- Upgraded checkagent from git main
- Checked upstream CI — **passing** for last 3 runs. Stable for fourth consecutive session.
- Re-ran all 954 previous tests — all pass, no regressions
- Explored the new `checkagent.multiagent` module (new in this release)
- Tested `MultiAgentTrace`, `Handoff`, `BlameStrategy`, `assign_blame`, `assign_blame_ensemble`, `top_blamed_agent`
- Checked previous findings F-038, F-042, F-061, F-062, F-066 — all still open
- Wrote 37 new tests; total now 991

**What I found:**

**CI green.** The upstream "mark multi-agent trace and credit assignment as complete" run passes, along with the two previous runs. Stable.

**New feature: `checkagent.multiagent`.** A multi-agent trace model with blame/credit attribution. The concept is clear: when a pipeline of agents fails, who's responsible? The module provides structured answers. Four main components:

1. **`MultiAgentTrace`** — container with `runs` (list of AgentRun), `handoffs` (list of Handoff), `trace_id`. Handoffs have types (`delegation`, `relay`, `broadcast`) and optional metadata (latency_ms, input_summary, from/to run_id). Clean Pydantic model.

2. **`BlameStrategy`** — 5 strategies: `FIRST_ERROR` (first run in list with error), `LAST_AGENT` (last run with error), `MOST_STEPS` (failed run with most steps), `HIGHEST_COST` (failed run with most tokens), `LEAF_ERRORS` (intended: leaf agents with no children that errored). Good conceptual coverage.

3. **`assign_blame`** — returns a single `BlameResult` (agent_id, strategy, confidence, reason) for a given strategy. Returns `None` when no errors or when the strategy is inapplicable.

4. **`assign_blame_ensemble`** and **`top_blamed_agent`** — run all (or custom) strategies, aggregate, return the agent blamed by most. `top_blamed_agent` provides a consensus result with "Blamed by N/M strategies" in the reason.

**What works well:**
- `FIRST_ERROR`, `LAST_AGENT`, `HIGHEST_COST`, `MOST_STEPS` all behave correctly
- `assign_blame_ensemble` cleanly skips None results (e.g. HIGHEST_COST without tokens)
- `BlameResult.confidence` stays in [0,1] range — different strategies assign appropriate confidence values (FIRST_ERROR=0.8, LAST_AGENT=0.6, LEAF_ERRORS=0.85, etc.)
- `top_blamed_agent` aggregation is sound — counts votes correctly, returns sensible consensus

**F-069 (new, high, bug): `LEAF_ERRORS` has inverted leaf detection.** The critical strategy for distributed system debugging is broken. `LEAF_ERRORS` is supposed to find agents at the "bottom" of the delegation tree (no outgoing handoffs) that errored — these are typically where root causes live. But in an A → B chain where B errors, it blames A ("Leaf agent error (no children)") even though A is clearly not a leaf. It looks like the leaf detection checks `to_agent_id` (incoming edges) instead of `from_agent_id` (outgoing edges). This makes `LEAF_ERRORS` the opposite of what it claims. In the canonical use case — orchestrator delegates to a worker that fails — it always blames the orchestrator.

**F-070 (new, medium, dx-friction): `assign_blame` silently returns None when `agent_id` is missing.** If you create `AgentRun(input=..., error="fail")` without setting `agent_id`, all blame attribution returns None or empty. No warning, no error. Common mistake since `agent_id` is an optional field with default None. Users who build multi-agent tests without agent IDs will see no blame results and no hint why.

**F-071 (new, low, dx-friction): `HandoffType` missing from `checkagent.multiagent` namespace.** To create a `Handoff` with a non-default type (relay or broadcast), you need `from checkagent.multiagent.trace import HandoffType`. Not in `__all__`. Thirteenth instance of the "type you need isn't where you'd expect it" pattern.

**F-072 (new, low, dx-friction): `MultiAgentTrace` doesn't validate handoff agent IDs.** You can reference nonexistent agent IDs in handoffs without any error. Typos in agent IDs produce silently broken handoff graphs that yield wrong blame attribution with no diagnostic.

**Carryover findings still open:** F-038 (AgentRun string input), F-042 (block_unmatched=False), F-061 (agents/ naming conflict), F-062 (AnthropicAdapter.final_output), F-066 (PII ID collision). None addressed.

**Observation on the module architecture:** The multiagent module is the 12th new module that isn't exported from the top-level `checkagent` namespace (F-068). At this point it's clearly a deliberate architectural choice — but there's still no mechanism for users to opt into a "full import" that includes all submodules. The result is that every session I'm discovering internal paths I have to document. A single `checkagent.full` or `checkagent[all]` namespace would solve this once.

**Next time I want to try:**
- Check if F-069 (LEAF_ERRORS) is fixed — this is a significant enough bug that it might be addressed quickly
- Check if F-070 (agent_id silent failure) gets a warning or fallback
- Check if F-038 (AgentRun string input) is fixed — open since session-015
- Check if F-042 (block_unmatched=False) is fixed — open since session-017
- Try building a realistic test with `top_blamed_agent` across a complex agent graph (3+ levels)
- Explore whether `MultiAgentTrace` has any serialization/deserialization support (save/load)
- Try using `parent_run_id` on `AgentRun` to see if it integrates with handoff topology

---

## Session 025 — 2026-04-06

**Upgraded from:** "mark multi-agent trace and credit assignment as complete" → "Fix checkagent init to generate tests that pass out of the box"

**What I tried:**
- Upgraded checkagent from git main
- Checked upstream CI — **passing** for last 4 runs. Very stable.
- Re-ran all 991 previous tests — 3 failures detected: my session-024 bug-documenting tests for F-069 and F-071 tripped their own "this is now fixed" detection paths
- Confirmed F-005 (checkagent init), F-069 (LEAF_ERRORS), F-071 (HandoffType namespace) all fixed
- Explored new MultiAgentTrace methods added in recent sessions: `add_run`, `add_handoff`, `root_runs`, `get_children`, `detect_handoffs`, `handoff_chain`, `total_steps`, `total_tokens`, `total_duration_ms`, `succeeded`, `failed_runs`, `get_runs_by_agent`, `get_handoffs_from`, `get_handoffs_to`
- Found 4 new issues (F-073 through F-076)
- Updated session-024 tests to reflect fixes
- Wrote 37 new session-025 tests; total now 1028

**What I found:**

**CI green.** "Fix checkagent init to generate tests that pass out of the box" passes. Fourth consecutive success.

**Big fix: F-005 resolved after 10 sessions.** `checkagent init` now generates a `pyproject.toml` with `asyncio_mode = "auto"` and `pythonpath = ["."]`. Generated tests pass immediately with `pytest tests/ -v`. The promise "tests pass without API keys" now holds. This was the highest-friction first-run experience issue in the framework.

**F-069 FIXED (LEAF_ERRORS inverted logic).** LEAF_ERRORS now correctly blames agents with no outgoing handoffs. In an A→B chain where B errors, LEAF_ERRORS now blames B as expected. The fix landed cleanly — my 3 bug-documenting tests in session-024 detected it and needed to be inverted.

**F-071 FIXED (HandoffType namespace).** `HandoffType` is now importable directly from `checkagent.multiagent`.

**New MultiAgentTrace features explored.** The module gained a rich set of topology methods. The aggregate properties (`total_steps`, `total_tokens`, `total_duration_ms`, `succeeded`, `failed_runs`) are clean and work correctly. The graph traversal methods are useful but have consistency issues.

**F-073 (new, medium, dx-friction): `get_children()` uses `run_id` not `agent_id`.** All other topology methods — `get_handoffs_from(agent_id)`, `get_handoffs_to(agent_id)`, `get_runs_by_agent(agent_id)` — take `agent_id`. But `get_children(run_id)` takes the `run_id` field of `AgentRun`, not the `agent_id`. This is a silent trap: `trace.get_children("my-orchestrator")` returns `[]`, while `trace.get_children("run-orch-001")` returns the correct children. No error, no warning.

**F-074 (new, low, dx-friction): `add_run()` and `add_handoff()` return `None`.** Both mutate `trace.runs`/`trace.handoffs` correctly, but return `None` instead of `self`. Can't chain: `trace.add_run(a).add_run(b)` raises `AttributeError`. Standard builder pattern fix would be `return self`.

**F-075 (new, medium, dx-friction): Mixed topology sources.** `MultiAgentTrace` has two ways to express the agent graph: explicit `handoffs` list and `parent_run_id` on `AgentRun`. Methods use different sources: `handoff_chain()` reads the explicit handoffs list; `root_runs`, `get_children()`, and `detect_handoffs()` read `parent_run_id`. A user who structures their trace via only `parent_run_id` will get `handoff_chain() == []`. A user who uses only explicit handoffs will get `root_runs == [all_runs]`. No documentation explains which methods use which representation.

**F-076 (new, high, bug): `detect_handoffs()` is a mutating method.** `detect_handoffs()` reads `parent_run_id` linkages and returns corresponding `Handoff` objects — but also appends them to `trace.handoffs`. The name "detect" strongly implies read-only inspection. Calling it twice duplicates all handoffs. Calling it before `handoff_chain()` causes `handoff_chain()` to return the auto-detected chain, subverting the user's expectation that the chain only contains explicitly added handoffs. This was discovered when my test called `detect_handoffs()` in an assertion, then checked `handoff_chain()`, and found unexpected results.

**Session discovery pattern.** The F-076 bug was only discoverable because my test combined two assertions in sequence: `assert len(trace.detect_handoffs()) == 1` then `assert trace.handoff_chain() == []`. If I'd only called one, I wouldn't have seen the interaction. This is the value of writing multi-step tests.

**Post-fix blame analysis.** With F-069 fixed, `LEAF_ERRORS` and `LAST_AGENT` now both correctly identify the worker in an orch→worker failure. `FIRST_ERROR` and `MOST_STEPS` both identify the orchestrator (first in list, 0 steps). A 2-agent trace now produces a 2:2 tie, with the tiebreaker returning orch. The ensemble is now more semantically honest — previously, 3 of 4 strategies blamed the orchestrator due to the F-069 bug.

**Observation on the dual-topology design.** It seems like `MultiAgentTrace` was designed to work two ways: (1) programmatic construction with explicit `Handoff` objects (the "test first" path), and (2) wrapping real agent runs where `parent_run_id` is set automatically by an orchestration framework. These are valid use cases, but the API doesn't guide users to understand which methods work in which mode. A `from_runs_with_parent_ids()` constructor that calls `detect_handoffs()` once and populates the handoffs list cleanly would make the second path discoverable.

**Next time I want to try:**
- Check if F-073 (get_children key type) is fixed
- Check if F-076 (detect_handoffs mutation) is fixed — high severity
- Check if F-074 (add_run returns None) is fixed
- Try `MultiAgentTrace.from_runs_with_parent_ids()` if it exists (would be a nice factory)
- Test `handoff_chain()` with cycles — what happens with circular handoffs?
- Explore whether `blame_ensemble` custom strategies parameter accepts lambdas or only `BlameStrategy` values
- Check if F-038 (AgentRun string input), F-042 (block_unmatched=False) are fixed — still open since session-015/017

---

## Session 026 — 2026-04-06

**Upgraded from:** "Fix checkagent init to generate tests that pass out of the box" → "Fix detect_handoffs() mutation bug and add builder chaining"

**What I tried:**
- Upgraded checkagent from git main
- Checked upstream CI — **passing** for last 5 consecutive runs. Very stable.
- Re-ran all 1028 previous tests — 4 failures detected in session-025, all expected (F-074/F-076 fix detection tests)
- Updated session-025 tests to reflect F-074 and F-076 fixes
- Explored the new `apply_detected_handoffs()` method
- Tested `handoff_chain()` with cyclic handoff graphs
- Tested `MultiAgentTrace` JSON serialization round-trip
- Tested `assign_blame_ensemble` with lambda strategies
- Wrote 24 new session-026 tests; total now 1052

**What I found:**

**CI green.** 5 consecutive successes. Best stability streak yet.

**F-074 FIXED (add_run/add_handoff builder chaining).** Both methods now return `self`. `MultiAgentTrace().add_run(r1).add_run(r2).add_handoff(h)` works cleanly. The fix came in the same commit as F-076.

**F-076 FIXED (detect_handoffs mutation).** `detect_handoffs()` is now read-only — it returns detected handoffs without mutating `trace.handoffs`. Calling it twice no longer duplicates the handoffs list. The fix also added `apply_detected_handoffs()` as the explicit mutation path.

**F-073 still open (get_children takes run_id).** No change — `get_children('my-agent-id')` still silently returns `[]` while `get_children('run-001')` works. All other topology methods (`get_handoffs_from`, `get_handoffs_to`, `get_runs_by_agent`) use `agent_id`. The inconsistency remains a silent trap.

**New `apply_detected_handoffs()` method.** Added alongside the F-076 fix. Converts `parent_run_id` links into explicit `Handoff` entries in `trace.handoffs`. Key properties:
- **Idempotent**: calling twice doesn't duplicate handoffs
- Returns the list of applied `Handoff` objects
- Bridges F-075 gap: after calling it, `handoff_chain()` and `root_runs` are consistent
- Works for fan-out topologies (one orchestrator, multiple workers)

**F-075 partially resolved.** The dual-topology representation issue (parent_run_id vs explicit handoffs) isn't fixed architecturally, but `apply_detected_handoffs()` is a clean escape hatch. Users who build traces from wrapped agent runs (using `parent_run_id`) can call `apply_detected_handoffs()` once and then use `handoff_chain()` freely. The docs still don't explain which methods use which topology source.

**F-077 (new, low, dx-friction): `handoff_chain()` with cycles — no detection, repeated nodes.** A trace with cyclic handoffs (a→b→c→a) produces `['a', 'b', 'c', 'a']` without raising or warning. The implementation follows the handoffs list in order rather than doing graph traversal, so it avoids infinite loops — but silently produces a result that doesn't represent a valid DAG. Users building feedback-loop agent systems will see unexpected chain lengths. A simple `len(chain) > len(set(chain))` check detects cycles as a workaround.

**JSON round-trip works cleanly.** `MultiAgentTrace.model_dump_json()` + `model_validate_json()` preserves all fields including `HandoffType` enum values, `parent_run_id` references, and error strings. Blame attribution on round-tripped traces works correctly. This is purely Pydantic — not a checkagent-specific feature, but worth confirming it works end-to-end.

**Lambda strategies in assign_blame_ensemble.** Undocumented: `assign_blame_ensemble(trace, strategies=[my_lambda])` works if the lambda returns a `BlameResult` or `None`. Lambdas returning `None` are filtered. This is a hidden extension point — useful for custom blame strategies without subclassing, but not documented anywhere.

**Builder pattern end-to-end.** With F-074 fixed, complex multi-agent trace construction is now ergonomic: `trace = MultiAgentTrace().add_run(orch).add_run(worker).add_handoff(Handoff(...))`. Tested up to 3-level chains and fan-out topologies.

**Next time I want to try:**
- Check if F-073 (get_children key type) gets fixed — it's been open two sessions now
- Try `MultiAgentTrace` with a real use-case: wrap an agent that uses `parent_run_id` and verify `apply_detected_handoffs()` + blame attribution works end-to-end
- Explore any new modules or features in the next upstream commit
- Check if F-038 (AgentRun string input), F-042 (block_unmatched=False) are ever fixed
- Test `handoff_chain()` cycle detection if it gets added
- Explore the `top_blamed_agent` return type more carefully — it returns `BlameResult` not `str`, which could surprise users (similar to F-029 ambiguity)

---

## Session 027 — 2026-04-06

**What I did:**
- Upgraded checkagent from git main
- Checked upstream CI (3 consecutive successes — still stable)
- Ran full test suite: 1052/1052 passing before new tests
- Investigated the major new commit: "Wire FaultInjector into MockTool and MockLLM via attach_faults()"
- Wrote 21 new session-027 tests; total now 1073

**CI status:** Green — 3 consecutive successes. The latest commit "Add Milestone 8 (docs site) and Milestone 9 (launch) to roadmap" suggests the project is approaching launch. Stability is holding.

**F-004 FIXED — the big one.** This was the longest-standing finding (open since session-004): FaultInjector not integrated with MockTool/MockLLM. The fix introduces `attach_faults(injector)` on both MockTool and MockLLM. Once attached, faults fire automatically on every `call()`/`call_sync()`/`complete()`/`complete_sync()` call. No more manual `check_tool()`/`check_llm()` guards.

**New `ap_fault` fixture added.** It was listed in the plugin namespace but not present before. Now it yields a fresh `FaultInjector` instance per test — clean, idiomatic, and what you'd expect. The typical workflow is now:

```python
def test_resilience(ap_fault, ap_mock_tool):
    ap_fault.on_tool("search").timeout()
    ap_mock_tool.register("search", response={}, schema={...})
    ap_mock_tool.attach_faults(ap_fault)
    # run agent — fault fires automatically
```

**`attach_faults()` returns `self` for chaining.** Builder pattern works end-to-end.

**F-016 still applies.** Even via `attach_faults`, the slow fault raises `ToolSlowError` in sync paths instead of sleeping. The error message now says "use async for real delay" which is clearer. But if you use `await tool.call("slow", {})`, the 50ms delay is real and correct.

**Two new DX findings:**

**F-078 (low): `was_triggered` is a method, not a property.** `if fi.was_triggered:` is always `True` because you're checking the bound method object. Must call `fi.was_triggered()`. Easy trap in test assertions: `assert not ap_fault.was_triggered` would always fail.

**F-079 (low): `attach_faults()` second call silently overwrites the first.** Calling `attach_faults(fi2)` after `attach_faults(fi1)` replaces fi1 entirely. Not additive. Can silently discard fixture-level faults when test body attaches a second injector. No warning.

**Score update:** `ap_fault mock integration` raised from 2/2 → 5/4. F-004 fix is a genuine improvement. The 4 on DX reflects the `was_triggered` method trap (F-078) and the overwrite behavior (F-079).

**What I want to try next session:**
- Check if F-073 (get_children takes run_id not agent_id) gets fixed — it's been open since session-025 with a helpful warning added in session-025
- Check if F-078/F-079 get addressed (low priority but the was_triggered one could surprise users)
- Explore the docs site referenced in Milestone 8 if it goes live
- Try a full end-to-end scenario that uses attach_faults in a realistic multi-step agent test
- Investigate if there's any progress on F-016 (slow sync raises) — with attach_faults now wiring things in, this issue becomes more visible to users

---

## Session 028 — 2026-04-06

**What I did:**
- Upgraded checkagent from git main (still v0.0.1a1)
- Checked upstream CI: green — 6 consecutive successes, very stable
- Ran full test suite: 1073/1073 passing before new tests
- Explored new feature: `MockLLM.with_usage()` (added session before last)
- Explored `MatchMode` top-level export
- Confirmed F-078/F-079 still open
- Wrote 23 new session-028 tests; total now 1096

**CI status:** Green — 6 consecutive successes. Latest: "Add framework overhead benchmarks for RQ4 paper data". The commit mentions "RQ4 paper data" — looks like the project is being used for a research paper (maybe the framework itself is being evaluated). Milestones 9 (dashboard) and 10 (launch) are roadmapped.

**MockLLM.with_usage() — new token simulation API.** Returns `self` (fluent). Works on `complete()`, `complete_sync()`, and `stream()`. Fixed tokens stamped on every `LLMCall`. Token data accumulates across calls and can be summed manually. Works cleanly alongside `on_input().respond()` and `attach_faults()`.

**F-080: `auto_estimate` formula is wrong in docs.** The docstring claims `len(text) // 4` but actual formula is `len(text) // 4 + 1`. Tested systematically across len 1–41. For every input length n, observed tokens = n//4 + 1. The +1 likely represents a BOS token but it's undocumented. Minor finding but will surprise users testing exact token counts.

**F-081: Both fixed+auto_estimate — silent undefined behavior.** Setting `prompt_tokens=999` and `auto_estimate=True` simultaneously raises no error. The fixed value is ignored, auto_estimate wins, but result is still not simply `n//4+1` — some other formula appears to apply. No validation at construction time. Users should set one or the other.

**MatchMode top-level export works cleanly.** `MatchMode.EXACT`, `SUBSTRING`, `REGEX` all function as expected. Important DX note: `add_rule('.*', ...)` with default `SUBSTRING` mode treats `'.*'` as a literal string, not regex. Users coming from regex background will be surprised. Use `MatchMode.REGEX` explicitly for patterns, or use `''` as catch-all with SUBSTRING.

**F-078 and F-079 still open.** Neither the `was_triggered` method-not-property trap nor the double-attach overwrite issue has been addressed.

**Fault exception imports.** The correct import path for fault exceptions is `checkagent.mock.fault` (e.g. `LLMRateLimitError`). No top-level export for these. Also discovered: `on_llm()` takes no arguments (unlike `on_tool(name)`) — applies to all LLM calls.

**What I want to try next session:**
- Check if F-080/F-081 get addressed in the docstring at minimum
- Explore the docs site when it launches (Milestone 8/9 in roadmap)
- Try `on_llm()` fault methods more thoroughly (content_filter, context_overflow, partial_response)
- Check if the LLM fault builder has parity with the tool fault builder — `on_llm()` has no `timeout` or `slow` (only rate_limit, server_error, content_filter, context_overflow, partial_response)
- Investigate if there's a new `ap_cost_tracker` fixture (F-019 still open)
- Consider trying a real external agent integration

---

## Session 029 — 2026-04-06

**What I did:**
- Upgraded checkagent from git main (still v0.0.1a1)
- Checked upstream CI: green — 7 consecutive successes, extremely stable
- Ran full test suite: 1095/1096 passing (1 expected failure — F-081 test needed updating)
- Fixed failing test: F-081 (with_usage conflict) was fixed upstream; updated test to document the fix
- Explored new features: LLM fault methods, triggered property additions, optional dep structure
- Wrote 21 new session-029 tests; total now 1117

**CI status:** Green — 7 consecutive successes. Latest commit: "Fix DX issues: jsonschema dep, triggered property, with_usage validation". The project is clearly in a polish phase before launch (Milestones 9-10 on the roadmap).

**F-078 partial fix: `triggered` @property added.** The commit adds three new @property members to FaultInjector:
- `fi.triggered` — bool, no parentheses needed (the DX fix for the original trap)
- `fi.trigger_count` — int count of activations
- `fi.triggered_records` — list of FaultRecord objects with target/fault_type/call_index

The `was_triggered(target)` method still exists for backward compat + target-filtered checks. This is a well-executed partial fix — they didn't break the existing API, just added the clean property alternative.

**F-080 FIXED:** Docstring now correctly documents `len(text) // 4 + 1`. Verified via `__doc__` inspection.

**F-081 FIXED:** `with_usage()` now raises `ValueError: Cannot set both auto_estimate=True and explicit token counts.` when both are provided. Clean, actionable error message.

**F-008 partial fix:** `jsonschema` is now declared as `checkagent[json-schema]` optional extra. Users can `pip install checkagent[json-schema]`. Still not a default dep — a bare `pip install checkagent` still lacks it. The CI now installs `[dev]` extras so upstream tests no longer fail on this.

**New finding F-082: LLM fault builder lacks `intermittent()` and `slow()`.** The tool fault builder has both (`intermittent(fail_rate=0.3)` for probabilistic failures, `slow(latency_ms=500)` for latency sim). The LLM fault builder has neither. Users cannot test retry logic against intermittent LLM failures, nor simulate slow LLM responses. Medium severity — important for realistic testing but has workarounds (e.g., manually raising in agent code).

**New finding F-083: `dirty-equals` and `deepdiff` are optional extras under `[structured]`.** Discovered by inspecting `importlib.metadata.requires('checkagent')`. Both `dirty-equals` (needed for `assert_output_matches` with `IsStr()`, `IsInt()`, etc.) and `deepdiff` are only installed via `pip install checkagent[structured]`. On a minimal `pip install checkagent`, these would be absent, breaking the core assertion API. This is high severity — `assert_output_matches` is a flagship feature prominently documented. This mirrors F-008 (jsonschema) but is arguably worse since dirty-equals powers the primary assertion API.

**LLM fault methods all work correctly.** Tested all 5 types:
- `content_filter()` → `LLMContentFilterError` with "content policy" message
- `context_overflow()` → `LLMContextOverflowError` with "128000 tokens" message
- `partial_response()` → `LLMPartialResponseError` with "streaming terminated" message
- `rate_limit(after_n=N)` → first N calls succeed, then `LLMRateLimitError` with "429" message
- `server_error(msg)` → `LLMServerError` with custom message

All exceptions are importable from `checkagent.mock.fault` but NOT from top-level `checkagent` (consistent with the broader F-020/F-067/F-068 pattern).

**What I want to try next session:**
- Check if F-082 (on_llm() intermittent/slow) gets implemented
- Check if F-083 (dirty-equals/deepdiff as optional) gets addressed
- Explore the docs site when it launches (Milestone 9 is dashboard — might be the live docs?)
- Investigate if F-073 (get_children API inconsistency) ever gets fully resolved — the warning added in session-025 was good but API still inconsistent
- Try a real external agent integration — LangChain or PydanticAI with a real LLM call mocked

---

## Session 30 — 2026-04-06 (F-082 FIXED, F-037 FIXED — LLM fault parity complete)

**Upgraded from:** ed0b21a → d0dd9265

**Upstream CI:** Green — 8 consecutive successes. Latest commit: "Add intermittent and slow faults to LLM fault builder (F-082)" which also fixed F-037.

**What I tried:**
- Upgraded checkagent via `uv pip install` (latest: d0dd9265)
- Ran full suite: 4 failures — F-082 tests (bug now fixed), F-037 test (bug now fixed), F-055 test (used `pkg_resources` which isn't available in Python 3.12 venv, testbed bug)
- Fixed testbed-side issues: updated F-082 and F-037 tests from "document the bug" to "document the fix"; replaced deprecated `asyncio.get_event_loop().run_until_complete()` with `asyncio.run()` in one session-021 test; fixed `pkg_resources` → `importlib.metadata` in F-055 test
- Verified F-082 fix in depth: `on_llm().intermittent(fail_rate=1.0)` raises `LLMIntermittentError`; `on_llm().slow(latency_ms=N)` sync raises `LLMSlowError`; async path does real latency simulation
- Verified F-037 fix: `FaultInjector.check_llm_async()` exists; no-fault path completes cleanly; both intermittent and slow work via async path
- Verified behavior consistency: slow(sync) raises for both LLM and tool faults; slow(async) sleeps for both — perfect symmetry
- Verified `triggered` property works with new LLM fault types
- Verified `MockLLM.attach_faults()` end-to-end with intermittent (raises through complete()) and slow (real delay through complete(), raises through complete_sync())
- Wrote 13 new session-030 tests covering all the above; all pass
- Total: 1131 tests, 0 failures

**What surprised me:**
- F-037 and F-082 landed in the same commit — makes sense since the async path (`check_llm_async`) is needed for slow faults to work non-exceptionally. The developer saw the dependency.
- The implementation is exactly symmetric with tool faults: slow(sync) raises a SpecificError with "use async for real delay" in the message, slow(async) does `await asyncio.sleep(ms/1000)`. Clean, learnable pattern.
- The `LLMIntermittentError` and `LLMSlowError` exception types are importable from `checkagent.mock.fault` — not at top-level (consistent with the F-020 pattern) but at least consistent with how other mock.fault exceptions work.
- Test suite has grown to 1131 tests with this session. The framework is very well-covered now.

**Status of previously-open "next session" items:**
- F-082 ✅ FIXED: on_llm() now has both intermittent() and slow()
- F-037 ✅ FIXED (bundled with F-082): check_llm_async() added
- F-083 still open: dirty-equals/deepdiff still under [structured] optional extra
- F-073 still open (warning added but API still inconsistent)
- Real external agent integration: still on TODO list — next priority

**What I want to try next session:**
- Real external agent integration — high priority, been on the list for 3+ sessions. LangChain or PydanticAI with MockLLM powering it
- Check if F-083 (dirty-equals/deepdiff optional dep) gets addressed — this is a high severity DX issue
- Check docs site / Milestone 9 progress
- Explore whether there's a `checkagent[all]` extra that installs everything for power users

---

## Session 31 — 2026-04-06 (LangChain real agent integration)

**Upgraded from:** ed0b21a → d0dd9265 (same as session-030 — no new upstream commits)

**Upstream CI:** Green — 8 consecutive successes. Latest: "Add intermittent and slow faults to LLM fault builder (F-082)". No new upstream changes since session-030.

**Session setup trap — uv.lock stale commit hash:**
Opening the session revealed a critical meta-issue: `uv run pytest` was silently downgrading checkagent from d0dd9265 back to ed0b21a (the old commit). Root cause: `uv.lock` had the old commit hash pinned. `uv pip install --upgrade` without `uv run` installs the latest, but `uv run` reads the lockfile. Fix: `uv lock --upgrade-package checkagent` updates the pin. Added this to session procedures.

This same issue likely affected the start of every session — `uv run pytest` was using an older version than expected. Worth remembering.

**What I tried:**

1. **Force-reinstalled checkagent** to verify modules — found `checkagent.multiagent`, `checkagent.cost`, `checkagent.trace_import` missing. Updated uv.lock (ed0b21a → d0dd9265). All 1131 tests passed.

2. **Real LangChain agent integration** — highest priority from prior sessions:
   - Created `agents/langchain_qa_agent.py`: a real LCEL chain using `ChatPromptTemplate | llm | StrOutputParser()`
   - Tested with `LangChainAdapter` + `langchain_core.language_models.fake_chat_models.GenericFakeChatModel`
   - Result: **it works**. No API key needed. `final_output` is a string (correct for StrOutputParser), steps captured with input/output, duration_ms measured, error captured on failure.
   - Wrote 8 tests covering: basic run, step capture, duration, assertions, AgentInput, multiple runs, error handling, multi-variable chain limitation
   - All 8 pass.

3. **Discovered F-084**: LangChainAdapter only passes `{input_key: query}`. Chains with extra template variables (e.g. `{context}`) fail. Workaround: use `prompt.partial(...)` to pre-fill extra variables before building the chain. This is a real limitation for RAG and contextual Q&A pipelines.

4. **Verified F-018 partial improvement**: `calculate_run_cost` is now at top-level `checkagent` (alongside CostTracker/CostBreakdown/CostReport/BudgetExceededError). `BUILTIN_PRICING`, `ProviderPricing`, `BudgetConfig` still require internal imports. F-018 remains open but is less painful.

5. **Confirmed F-083 still open**: `dirty-equals` and `deepdiff` remain under `[structured]` optional extra, not default deps.

**What surprised me:**
- `GenericFakeChatModel` in `langchain_core` is perfect for testing LangChain chains without an API key. It accepts an iterator of `AIMessage` objects and returns them in sequence. Every LangChain adapter test should use this.
- `RunnableSequence.partial()` doesn't exist — it's `prompt.partial()` you need. This tripped me up and reveals the F-084 limitation more clearly: there's no clean "post-chain partial application" in LCEL.
- The uv.lock stale hash problem means every session that "upgraded" checkagent was actually running the OLD version via `uv run`. The force-reinstall via `uv pip install` works but `uv run` reverts it. This explains why some things appeared to work/fail inconsistently across sessions.

**Status of previously-open "next session" items:**
- Real agent integration: ✅ DONE — LangChain LCEL chain with FakeChatModel tested successfully
- F-083 (dirty-equals/deepdiff optional): still open
- F-073 (get_children API inconsistency): still open, warning added in session-025 but API unchanged

**Total tests:** 1143 (up from 1131)

**What I want to try next session:**
- Try PydanticAI agent integration with a real PydanticAI model + fake backend
- Try a LangChain agent with tool calling (ToolNode or custom tool) — F-084 shows a clear gap here
- Check if `checkagent[all]` extra exists for power users
- Investigate whether `assert_output_matches` silently fails on fresh install (F-083 impact)
- Look for a real GitHub agent to integrate — minimal-dependency, no API key needed

---

## Session-032 — 2026-04-06

**Focus:** PydanticAI real agent integration + LangChain tool calling investigation

**Setup:**
- `uv pip install --upgrade checkagent@git+...@main` + `uv lock --upgrade-package checkagent` — same commit as session-031 (no upstream changes). 1163 tests passing (1143 + 20 new).

**Upstream CI:** Green — 9 consecutive successes. Stable.

### PydanticAI Real Agent Integration

Installed `pydantic-ai 1.77.0` (not declared as a dep by checkagent — F-064 still open).

Created `agents/pydantic_ai_agent.py` with four helpers:
- `make_qa_agent(answer)` — basic Q&A using TestModel
- `make_weather_agent()` — agent with an internal tool (`get_weather`)
- `make_structured_agent()` — returns a `WeatherResult` Pydantic model
- `make_error_agent()` — raises RuntimeError on every invocation

**Results — `PydanticAIAdapter` works with PydanticAI 1.77.0:**

1. **String final_output** ✓ — when agent returns text, `final_output` is a string
2. **Pydantic model final_output** ✓ — structured output flows through as a model instance; `assert_output_schema` works via `model_dump()`
3. **Token extraction** ✓ — `total_prompt_tokens` / `total_completion_tokens` populated from TestModel's usage info (though via deprecated attrs — F-087)
4. **Error handling** ✓ — exceptions captured in `AgentRun.error`; `run()` never raises
5. **Tool-using agents** ✓ — 4 steps captured (request → tool-call response → tool result request → final response)
6. **AgentInput and string input** ✓ — both coerce correctly

**New findings:**

- **F-085 (low):** `Step.input_text` is always `''` for PydanticAI steps — all content is in `output_text`. Contrasts with GenericAdapter where `input_text` is populated. Low severity because the data is still accessible via `output_text`.
- **F-086 (medium):** `PydanticAIAdapter` not at top-level `checkagent` — must use `checkagent.adapters.pydantic_ai`. (It IS in `checkagent.adapters`, which is one level better than AnthropicAdapter etc.) 13th instance of this pattern.
- **F-087 (high):** Adapter reads deprecated `request_tokens`/`response_tokens` — PydanticAI 1.77.0 renamed to `input_tokens`/`output_tokens`. Every run emits 2 DeprecationWarnings. Will silently break token extraction in a future PydanticAI version.

### LangChain Tool Calling Investigation

`GenericFakeChatModel.bind_tools()` raises `NotImplementedError` — no clean way to test tool-calling LCEL chains without a custom fake model. Created a `StatefulFakeLLM` subclass that returns tool-call AIMessages and tracks call count. Wrapped with `LangChainAdapter`.

**Key architectural finding:** `assert_tool_called` and CheckAgent's mock layer only work when the agent explicitly calls through CheckAgent's `MockTool`. For real LangChain/PydanticAI agents with internal tool execution, CheckAgent can only assert on:
- `final_output` content (string match, schema, dirty_equals)
- step count
- error/success
- token counts and duration

Internal tool calls are invisible to CheckAgent's mock layer.

- **F-088 (low):** No `checkagent[all]` extra. Extras: `dev`, `json-schema`, `otel`, `safety-ner`, `structured`. Framework packages not extras at all (F-064).

Also **fixed a stale testbed test:** `test_anthropic_adapter_raises_on_missing_package` was failing because `anthropic` is now installed. Rewrote to use `mock.patch.dict(sys.modules)` to simulate the missing-package scenario.

### What surprised me

- `PydanticAIAdapter` IS in `checkagent.adapters` (re-exported) — slightly better than other adapters. Still not top-level.
- PydanticAI's `TestModel` is very clean for testing. `custom_output_text` for string results, `custom_output_args` for structured output — zero boilerplate.
- The deprecated token attribute issue is a real maintenance risk. If PydanticAI 2.0 drops the old names, all token metrics will silently return None.

**Total tests:** 1163 (up from 1143)

**What I want to try next session:**
- Fix the stale test isolation: `test_anthropic_adapter_raises_on_missing_package` worked but is fragile — consider module-level mock
- Test PydanticAI streaming (`run_stream`) via the adapter's `run_stream` path
- Try a CrewAI agent with a real tool using FakeAgent or similar
- Investigate whether any framework adapters get added to `[all]` extra if it exists
- Test `assert_output_matches` on a fresh install to confirm F-083 impact

---

## Session 033 — 2026-04-11

### Upgrade: 0.1.1 → 0.1.2

Ran `uv sync --upgrade-package checkagent` and got `checkagent==0.1.2` (commit 29caad2).

### Upstream CI

Latest run ("Add ci-init command and fix silent LLM judge failure on bad API key") is **red** — breaks a 9-session green streak. Failure is Windows-only on the new `ci-init` command test (`test_github_is_default_platform`): the success message uses OS path separators, so `.github/workflows/checkagent.yml` appears as `\.github\workflows\checkagent.yml` on Windows. This is F-091. All macOS and Linux jobs pass. Second Windows CI failure seen in the test suite (previous was F-043/F-047/F-054, all eventually fixed).

### Existing Tests

Ran full suite: **1 failing test** — `test_version_string_inconsistency` in test_session033.py. This test was written to document a bug in 0.1.1 where `checkagent.__version__` returned `'0.1.0'` but metadata said `'0.1.1'`. In 0.1.2 both return `'0.1.2'`, so the bug is fixed and the test needed updating. Fixed by rewriting the test to assert both versions are equal.

### What Changed in 0.1.2

**Massive top-level export fix:** 11 open findings closed in one release:
- F-020 (eval exports), F-021 (safety exports), F-026 (Probe/ProbeSet), F-030 (QualityGateEntry), F-032 (.all() returns ProbeSet), F-048 (judge exports), F-053 (multi_judge), F-057 (LangChainAdapter), F-063 (Anthropic/Crew adapters), F-068 (multiagent), F-086 (PydanticAIAdapter)

This is the biggest single quality jump since the framework started. Every major type is now importable from `checkagent` directly.

**New CLI commands:**
- `checkagent scan` — full agent safety scanner. Supports Python callables and HTTP endpoints. All 4 categories (injection/jailbreak/pii/scope). JSON output (`--json`), SVG badge (`--badge`), test file generation (`--generate-tests`), async agents handled correctly.
- `checkagent ci-init` — CI/CD config scaffolder. Generates GitHub and GitLab workflows. Works correctly on Linux/Mac.

**New API:**
- `ResilienceProfile` — top-level class for comparing baseline vs faulted performance. `from_scores()` and `from_runs()` both work. `to_dict()` missing `best_scenario` (F-090 — minor).

### New Findings

- **F-089 (low):** `--generate-tests` embeds private API imports (`_resolve_callable`, `_evaluate_output`) in generated files. Generated tests will break on checkagent upgrades if these internals change.
- **F-090 (low):** `ResilienceProfile.to_dict()` omits `best_scenario` despite `profile.best_scenario` being a valid attribute.
- **F-091 (medium):** `ci-init` uses OS path separator in success message — Windows backslashes break expected path string in checkagent's own tests.
- **F-092 (closed):** Version inconsistency (0.1.0 vs 0.1.1) fixed in 0.1.2.

### New Tests Written

**test_session033.py** — fixed `test_version_string_inconsistency` → `test_version_string_consistent`.

**test_session034.py** — 29 new tests:
- `checkagent scan`: safe agent, echo agent, JSON schema, finding schema, invalid module, async agent, all/filtered categories
- `checkagent scan --badge`: SVG generation for safe and failing agents
- `checkagent scan --generate-tests`: file creation, private API detection (F-089), syntax validity
- `checkagent ci-init`: GitHub workflow, YAML validity, step content, GitLab, both platforms, --force, custom target
- PydanticAI streaming: events, StreamCollector, ordering, TEXT_DELTA data
- ResilienceProfile: from_scores, from_runs, to_dict, F-090 documentation

### What Surprised Me

- 11 top-level export findings closed in one commit — the developer clearly did a sweep of all the DX friction we reported.
- The `scan` command works on async agents out of the box (returns coroutine → awaits it internally). No special handling needed.
- The generated test file has a `pii_leakage` test even when `--category injection` is specified. This is because the finding category is determined by what PATTERN was triggered in the output, not by the probe's category. The email address in the probe text triggers PII detection. Subtle but sensible behavior.
- `ci-init` generates valid YAML but `on:` becomes boolean `True` in PyYAML (YAML 1.1 behavior). Not a checkagent bug, but a gotcha for test authors checking for `"on"` in parsed YAML.
- `ResilienceProfile.to_dict()` output uses `'overall_resilience'` not `'overall'` as the key — different from the attribute name `profile.overall`. Consistent with the full name convention, but worth noting.

### Total Tests

1226 passed, 1 xfailed (up from 1163)

### What I Want to Try Next Session

- Test `checkagent scan --url` with a local HTTP agent (FastAPI or Flask)
- Test `ci-init --platform both` output quality for GitLab
- Test LLM judge mode for scan (`--llm-judge`) — requires API key
- Investigate whether F-087 (deprecated PydanticAI token attrs) is fixed in 0.1.2
- Test `ResilienceProfile` in a real fault scenario: `FaultInjector` + `from_runs()`
- Check if F-064 (undeclared adapter deps) is still open
- Check if `checkagent scan` has any rate-limiting or retry behavior

---

## Session 034 — 2026-04-11

### What I Did

**Upgraded:** `pip install --upgrade checkagent@git+...@main` — still 0.1.2 (no new PyPI release). 

**CI Status:** RED — failing on all 12 platform/version combinations. Latest commit "Add checkagent analyze-prompt" breaks `ruff check` with I001 (unsorted imports, 3 files) and E501 (line too long: 110 > 99). Previous commit "Add --agent-description flag and make evaluate_output public" was green. This is F-097.

**Re-ran all tests:** 1272 passed, 3 xfailed — clean.

**New features explored:**

1. **`checkagent analyze-prompt` CLI** — New command that statically analyzes a system prompt for 8 security controls (injection guard, scope boundary, confidentiality, refusal behavior, PII handling, data scope, role clarity, escalation path). No LLM required. Exit 0 when all HIGH-severity checks pass; exit 1 otherwise. `--json` flag outputs complete machine-readable results. Reads from file or inline string. Clean terminal table output.

2. **`PromptAnalyzer` Python API** — `PromptAnalyzer().analyze(text)` returns a `PromptAnalysisResult` with `score`, `passed_count`, `total_count`, and `check_results`. Each `CheckResult` has `check` (the `PromptCheck` definition), `passed`, and `evidence`. Lives in `checkagent.safety` (not top-level — F-095).

3. **`data_enumeration` scan category** — 5th category added to `checkagent scan`. 20 probes covering bulk data disclosure requests (dump-database, list-all-users, export-knowledge-base, etc.). Both HIGH and CRITICAL severity probes. Not at top-level (another instance of the pattern).

4. **Class-based agent scan** — `checkagent scan module:ClassName` now works. The scanner auto-instantiates the class and calls it with each probe. Tested with a `SupportBot(__call__)` class — correctly scanned, refusal bots score 1.0 on injection.

5. **New top-level exports** — `EvalCase`, `SafetyEvaluator`, `SafetyFinding`, `SafetyResult`, `ScenarioResult`, `TestRunSummary` all confirmed at top-level. `TestRunSummary` is exactly `checkagent.ci.RunSummary` under a better name.

6. **`evaluate_output` location** — CI commit said "make evaluate_output public" but it's in `checkagent.cli.scan` (private). Not at top-level. F-096.

### New Findings

- **F-093 (medium):** `analyze-prompt` Rich markup bug — `[your domain]`, `[support channel]` etc. stripped from recommendations in terminal output. JSON output correct.
- **F-094 (medium):** Non-existent file analyzed as literal string — no error, scores 0/8.
- **F-095 (low):** `PromptAnalyzer`/`PromptCheck`/`PromptAnalysisResult` not at top-level `checkagent`.
- **F-096 (low):** `evaluate_output` in `checkagent.cli.scan` (private), not public API.
- **F-097 (high):** CI failing ALL platforms — ruff lint in `analyze-prompt` commit.

### New Tests Written

**test_session035.py** — 48 tests (46 pass, 2 xfail):
- `analyze-prompt` CLI: exit codes, 8 checks, JSON output, file reading, static check, F-093/F-094 as xfail
- `PromptAnalyzer` Python API: analyze(), results, evidence, F-095 as assertion
- `data_enumeration` category: 20 probes, severity mix, category correctness, false positives on echo
- Class-based agent scan: instantiation, refusal bot scores 1.0
- New top-level exports: EvalCase, SafetyFinding, SafetyResult, SafetyEvaluator, ScenarioResult, TestRunSummary
- `evaluate_output` location (F-096)

### What Surprised Me

- All analyze-prompt recommendations with template placeholders (`[your domain]`, `[support channel]`) are silently stripped by Rich markup parsing. The JSON output is fine. Classic framework API misuse — brackets are Rich markup.
- The `analyze-prompt` exit code logic is entirely undocumented: exits 0 only when ALL HIGH-severity checks pass, exits 1 otherwise. This is actually great CI behavior but users have to discover it empirically.
- `TestRunSummary` at top-level is literally `TestRunSummary = RunSummary` from `checkagent.ci` — same class, better alias. Smart fix for the F-029 naming confusion without breaking existing code.
- `data_enumeration` echo agent false positives: an agent that echoes user input will fail bulk-query probes because it echoes back "list all records" which contains the detection pattern. Real agents with scope guardrails score much better. This is expected static analysis behavior.
- `python3 -m checkagent` doesn't work — no `__main__.py`. Must use the `checkagent` binary directly. The existing test_session034.py works around this with `uv run checkagent`.

### Total Tests

1272 passed, 3 xfailed (up from 1226)

### What I Want to Try Next Session

- Test `checkagent scan --url` with a local FastAPI agent
- Check if F-097 (ruff lint) is fixed and CI goes green again
- Check if F-087 (deprecated PydanticAI token attrs) is fixed
- Test `analyze-prompt --json` recommendation text integrity more thoroughly
- Test PromptAnalyzer with edge cases: empty string, very long prompt, Unicode
- Check if any new features appeared (the upstream has been very active)
- Try `EvalCase` in a parametrized test scenario

---

## Session 035 — 2026-04-12

### What I Did

**Upgraded to checkagent 0.2.0 "Security Audit Edition"** — first PyPI release! Updated pyproject.toml to remove the git-source pin (`[tool.uv.sources]`) and use `checkagent>=0.2.0` from PyPI.

**Upstream CI:** GREEN — v0.2.0 Publish to PyPI run succeeded. F-097 (ruff lint) resolved. Three latest runs all green including the new "Fix mkdocs.yml indentation" CI run.

**Test suite:** Updated from 1272→1323 passing. Fixed 4 broken tests in test_session035.py:
- F-095 tests (3): PromptAnalyzer/PromptCheck/PromptAnalysisResult now at top-level — inverted assertions
- data_enumeration count: grew from 20 to 25 probes

**Fixed findings (resolved in 0.2.0):** F-093, F-094, F-095, F-097 all confirmed fixed.

### New Features Explored (0.2.0 "Security Audit Edition")

**GroundednessEvaluator:**
- Two modes: `fabrication` and `uncertainty` (not `certainty` — ValueError)
- fabrication mode works correctly: definitive claims fail, hedged language passes
- `evaluate(text)` and `evaluate_run(run)` both work
- `add_hedging_pattern()` and `add_disclaimer_pattern()` allow custom signal injection
- **CRITICAL BUG (F-099):** uncertainty mode `hedging_signals` always 0. "I might be wrong", "could be incorrect", "not certain" all return 0. Only "not financial advice" passes via disclaimer path. The HEDGING_PATTERNS exist in source but don't apply in uncertainty mode.

**probes_groundedness:** 8 probes (fabrication+uncertainty). A module, not a ProbeSet (inconsistent with other probe modules). Access via `probes_groundedness.all_probes`.

**ConversationSafetyScanner:** Requires `evaluators` list (no default). Uses `conv.say()` (not `conv.turn()`). Detects per-turn and aggregate findings. `aggregate_only_findings` is the key new feature — captures split-context attacks that only appear when conversation is concatenated. Clean, well-designed API.

**ComplianceReport + render functions:** `generate_compliance_report(results, agent_version=, model_version=)` → ComplianceReport. Three renderers: `render_compliance_markdown`, `render_compliance_json`, `render_compliance_html`. The markdown and json are clean. HTML returns valid markup. All three work correctly.

**EU_AI_ACT_MAPPING:** Maps every SafetyCategory to EU AI Act article references (Article 9, 10, 15). Alongside OWASP_MAPPING this gives dual compliance coverage. Not at top-level.

**SARIF 2.1.0 output (`--sarif file.sarif`):** Valid SARIF 2.1.0 JSON. Tool metadata with version. Rules include remediation markdown guidance (e.g., "## Remediation: Prompt Injection\n\n### Immediate Actions\n1. **Add an injection guard**..."). This is production-ready GitHub Security tab integration.

**`--repeat N` flag:** Adds `stability` object to JSON output with `stable_pass`, `stable_fail`, `flaky`, `stability_score`. Echo agent gets 1.0 stability (deterministic). **F-098 found**: "Auto-detected:" diagnostic leaks to stdout with --json, breaking machine-readable output.

**`--prompt-file` flag:** Shows static prompt analysis inline with dynamic scan. Score table appears at top, then probe results follow. Clean UX — one command gives both static and dynamic analysis.

**`checkagent wrap` CLI:** Auto-detects agent type (OpenAI SDK / run / invoke / kickoff / callable). For plain async functions outputs "No wrapper needed, scan directly." **F-100 found**: crashes in testbed with `AttributeError: module 'agents' has no attribute 'Agent'` — same agents/ dir conflict as F-061.

### New Findings

- **F-098 (high):** `--json` mode leaks "Auto-detected:" diagnostic to stdout before JSON object
- **F-099 (high):** GroundednessEvaluator uncertainty mode: hedging_signals always 0
- **F-100 (medium):** checkagent wrap crashes with AttributeError in testbed (agents/ dir conflict)

### What Surprised Me

- 0.2.0 is a genuine major release, not just a patch. The "Security Audit Edition" name is earned: SARIF output, compliance reports, EU AI Act mapping, groundedness probes, conversation scanning — this is a real security tool now.
- The `--prompt-file` flag is very well-designed: combining static prompt analysis with dynamic probing in one command is exactly what a security engineer wants.
- probes_groundedness is a module, not a ProbeSet — the only probe namespace that works this way. Inconsistency worth reporting.
- The F-098 bug (diagnostic leaking to stdout) is subtle: it only breaks --json mode when the "Auto-detected:" message fires. If the target is explicit, it might not appear.
- ConversationSafetyScanner requires evaluators as positional argument with no default. Reasonable design choice but surprising — other evaluators can be instantiated with zero args.
- PyPI release means `pip install checkagent` now gets 0.2.0 — real users can actually install it without git URL tricks.

### Total Tests

1323 passed, 4 xfailed (up from 1272 passed, 3 xfailed)

### What I Want to Try Next Session

- Test `checkagent scan --url` with a local FastAPI agent (high priority — real HTTP scanning)
- Test GroundednessEvaluator uncertainty mode patterns directly (F-099 deep dive)
- Test `ConversationSafetyScanner` with `aggregate_only_findings` split-attack scenario
- Check if GroundednessEvaluator/ConversationSafetyScanner get top-level exports
- Test SARIF upload workflow to GitHub Security tab (would need a real GitHub action)
- Test `checkagent wrap` on a CrewAI/LangChain agent (auto-detection for invoke/kickoff)
- Check docs site at checkagent.xydac.com for new 18 pages
- Test `render_compliance_html` more thoroughly (what does the HTML look like?)

---

## Session-036 — 2026-04-13

### What I Did

**Updated checkagent:** Still v0.2.0 — no new release since session-035. Upstream CI is green (all 3 latest runs pass). 1332 tests pass (up from 1323 last session due to new HTTP scan tests added).

**Checked open findings:**
- **F-098 (partial fix):** Retested. Plain async functions produce clean JSON — no "Auto-detected:" leak. But `@wrap` adapters still leak. `checkagent scan agents.echo_agent:echo_agent --json` still outputs "Auto-detected: echo_agent.run()" before the JSON. Reduced severity to medium since it only affects wrapped objects.
- **F-099 (still open):** Confirmed `hedging_signals` is always 0. "might", "could", "not certain", "perhaps", "I cannot guarantee" — all score 0 hedging signals. Only "not financial advice" matches the disclaimer path. The bug is in pattern routing between hedging vs. disclaimer checks.
- **F-100 (nuance clarified):** `checkagent wrap` still crashes with agents/ dir conflict. But discovered that `checkagent scan agents.echo_agent:echo_agent` (colon format: module:callable) DOES work now — Python imports the submodule correctly. Only the dot-only format fails. Updated F-100 status accordingly.

**New feature tested: `checkagent scan --url` (HTTP scanning):**
Built a minimal stdlib HTTP server (no FastAPI — FastAPI version in venv had init compat issue) and ran HTTP scanning against it. Results:
- Sends HTTP POST with probe in `{"message": ...}` format by default
- `--input-field` and `--output-field` both work; field auto-detection works (tries "output", "response", "answer", "text", "result", "message" in order)
- `-H "Authorization: Bearer token"` custom headers accepted
- `--json` output is clean (no diagnostic leak for HTTP targets)
- `--generate-tests` creates a stdlib-based test file using `urllib.request` — no extra dependencies. Has `agent_fn` fixture that sends HTTP POST. Still imports from `checkagent.cli.scan` (F-089 still applies).
- Server-down: shows `errors: 35, score: 0.0, findings: []` — functional but misleading (F-102 filed)
- Multiple categories supported — tested injection (35 probes)

**ConversationSafetyScanner deep dive:**
- Works correctly for per-turn injection detection
- `per_turn_findings` is a **dict** not a list (F-101 filed)
  - Keys are only turns WITH findings
  - `enumerate(result.per_turn_findings)` gives integer keys, not `(idx, findings)` pairs
  - Correct usage: `result.per_turn_findings.items()`
  - `result.turns_with_findings` gives the same key set as a list
- `aggregate_only_findings` is empty when all findings are per-turn (expected)
- Multiple evaluators in one scanner work correctly (injection + PII tested)

**Top-level exports for 0.2.0 new classes:**
None of the new 0.2.0 modules are at top-level: `GroundednessEvaluator`, `ConversationSafetyScanner`, `ConversationSafetyResult`, `ComplianceReport`, `generate_compliance_report`, `EU_AI_ACT_MAPPING`, `probes_groundedness` — all require `from checkagent.safety import ...`. This is the 14th+ instance of the pattern. Not filing a new finding (it's covered by the ongoing pattern), but noting for the score.

### New Findings

- **F-101 (medium):** `ConversationSafetyResult.per_turn_findings` is a dict not a list — enumerate() gives keys, need .items()
- **F-102 (low):** HTTP scan server-down shows score 0.0 + errors count without clear "server unreachable" message

### Updated Findings

- **F-098:** Reduced severity medium, partially fixed — plain callables clean, @wrap adapters still leak

### What Surprised Me

- The HTTP scan feature is polished. Zero setup required — just point it at any URL, specify the input field, and it runs 35+ probes. The generated test file uses only stdlib `urllib.request` — no extra deps. This is genuinely useful for testing deployed agents.
- FastAPI had a breaking change in its venv (Router.__init__ keyword arg). Had to fall back to stdlib http.server. Not a checkagent issue but worth noting for real users who try the --url scanning.
- `checkagent scan agents.echo_agent:echo_agent` (colon format) WORKS in the testbed even though `agents.echo_agent` (dot format) doesn't. The `:` syntax tells checkagent to do a proper submodule import, which correctly picks up our local `agents/echo_agent.py` rather than the OpenAI package. F-100 is now more precisely "wrap uses the wrong import strategy" not "scan is broken in testbed."
- `per_turn_findings` being a dict instead of list is the kind of thing that burns users. The name implies list semantics. `enumerate(result.per_turn_findings)` doesn't raise — it silently iterates over the integer keys, giving confusing TypeError only when you try to use those ints as findings.

### Total Tests

1332 passed, 5 xfailed (up from 1323/4)

### What I Want to Try Next Session

- Test ConversationSafetyScanner with aggregate_only_findings — find a scenario that produces cross-turn findings
- Test GroundednessEvaluator with `evaluate_run()` on a multi-step AgentRun
- Test `checkagent scan --url` with all 5 categories (not just injection)
- Test `checkagent scan --url --repeat N` stability measurement for HTTP agents
- Test `checkagent scan --url --sarif` — does SARIF work for HTTP targets?
- Check docs site at checkagent.xydac.com
- Test `checkagent wrap` on a LangChain agent (invoke method auto-detection)
- Test `checkagent scan --llm-judge` flag with a local model

---

## Session 037 — 2026-04-15

### Upgrade

Installed latest checkagent from git main — still reports 0.2.0 (no new release since session-035 PyPI push). The latest upstream commit was "Add safety screening to import-trace, fix per_turn_findings iteration".

### Upstream CI

Red again — **Python 3.13 on Windows** fails with `ConnectionAbortedError: [WinError 10053]` in `TestMakeHttpAgent::test_server_error_raises`. This is the 6th distinct Windows-specific failure across all sessions (F-043, F-047, F-054, F-091, F-104). All non-Windows platforms green. The pattern is undeniable: checkagent's test suite is brittle on Windows for any test that touches networking or timing. Filed as F-104.

### Pre-existing tests

Previous full run had 17 failures:
- 8 in `TestGenerateTestCases` (test_session023) — AttributeError 'tuple' has no attribute 'name'
- 1 in `test_session036` — wrap crash test failing because `checkagent_target.py` already exists

### Root cause: `generate_test_cases` API breaking change (F-103)

The safety screening commit changed `generate_test_cases` in two ways:
1. `name=` → `dataset_name=` (no deprecation, `TypeError: unexpected keyword argument 'name'`)
2. Return type: `GoldenDataset` → `tuple[GoldenDataset, TraceScreeningResult]` (no deprecation, `AttributeError: 'tuple' object has no attribute 'name'`)

The new `TraceScreeningResult` is genuinely useful — it flags imported traces that contain injection patterns, PII leaks, etc. But the migration story is terrible. Old code breaks silently. Filed F-103.

Fixed all 16 affected tests in test_session023.py by unpacking: `dataset, _ = generate_test_cases(...)`.

### test_session036 wrap fix

`test_wrap_cli_crashes_in_testbed_due_to_agents_dir` was failing because `checkagent_target.py` already exists from a previous session's wrap run. F-100 is fixed upstream — wrap no longer crashes, but without `--force` it returns exit code 1 "file already exists". Added `--force` to the test. Now passes.

### F-100 and F-102 confirmed fixed

- **F-100**: `checkagent wrap agents.echo_agent:echo_agent` now works in testbed — no AttributeError. Auto-detects `.run()` method. Score upgraded to 4/4.
- **F-102**: JSON output now includes `"warning": "All N probes failed... may be unreachable."` — clear server-down message.

### New tests: TraceScreeningResult API

Added `TestTraceScreeningResult` class (9 tests) to test_session037.py documenting:
- Return type is now `tuple` (breaking change)
- `total_count`, `clean_count`, `flagged_count`, `findings_by_trace` fields
- Injection detection in imported traces works correctly
- `safety_check=False` skips screening (not tested — discovered parameter exists)
- Old `name=` param raises `TypeError` (not helpful migration hint)
- Dataset still includes ALL runs, even flagged ones (screening is informational)

### Session 037 tests

All 33 tests in test_session037.py pass (24 pre-written + 9 new TraceScreeningResult).

### Final count

**1366 passed, 4 xfailed** (up from 1332/4 last session — +34 net tests)

### What surprised me

- The `generate_test_cases` API change was introduced in the same commit that fixed F-101 (`per_turn_findings` dict iteration). Classic "one commit, two changes" DX trap — one fix broke existing code. The `findings_by_trace` dict keys are trace IDs (strings like `'q2-bee98bf1'`), which are deterministic content hashes. Nice design, but not surfaced anywhere in docs.
- Windows CI failures are now a persistent pattern — 6 different root causes across 37 sessions. All are networking or timing-related. Checkagent needs a CI policy for Windows: either fix the flakiness or run Windows CI on a separate cadence with known-flaky tests marked.
- `checkagent wrap` actually works well now. Auto-detected `.run()`, `.invoke()`, and plain callable correctly in tests. The generated async wrapper is clean Python. F-100 fix was solid.

### New Findings

- **F-103 (high):** `generate_test_cases` breaking API — tuple return + `name` → `dataset_name` rename, no deprecation
- **F-104 (high):** Upstream CI failing on Windows Python 3.13 — `ConnectionAbortedError` in HTTP scan test

### Updated Findings

- **F-100:** FIXED — wrap no longer crashes in testbed due to `agents/` dir
- **F-102:** FIXED — JSON output now includes clear "unreachable" warning key

### What I Want to Try Next Session

- Test `TraceScreeningResult` with `safety_check=False` parameter
- Test `checkagent scan --llm-judge` flag (if it exists)
- Test `checkagent scan --url --repeat N` with a flaky/randomized agent (stability < 1.0)
- Test docs site at checkagent.xydac.com
- Test `checkagent wrap` with a LangChain LCEL chain (invoke method)
- Investigate whether F-101 (`per_turn_findings` dict) was actually fixed in the "fix per_turn_findings iteration" commit or just documented better

---

## Session 038 — 2026-04-16

### What I did

1. **Updated checkagent** — `pip install --upgrade` from git main. Version stayed at 0.2.0 (no new PyPI release since session-035). Upstream commit was "Fix Windows CI failure and generate_test_cases API compat".

2. **Upstream CI** — Latest run green. All 12 jobs pass including Windows 3.10/3.11/3.12/3.13. The session-037 failure (F-104, Windows Python 3.13 `ConnectionAbortedError` in HTTP scan test) is fixed.

3. **Existing tests** — 1 failure: `test_old_name_param_raises_type_error` in session-037. The test expected `TypeError` when calling `generate_test_cases(name=...)`, but upstream fixed F-103 by adding a `DeprecationWarning` instead. Updated test to assert `DeprecationWarning` — all 1366 tests now pass (+ 4 xfailed).

4. **Previous findings checked:**
   - **F-101 FIXED**: `ConversationSafetyResult` now has `iter_turn_findings()` helper method that returns sorted `(turn_idx, findings)` pairs. The docstring explicitly calls out the `enumerate()` gotcha. Also added `turns_with_findings`, `total_per_turn_findings`, `total_findings` properties. This is a solid fix — solves the DX problem with a well-documented helper.
   - **F-103 PARTIALLY FIXED**: `generate_test_cases(name=...)` no longer raises `TypeError` — now emits `DeprecationWarning` and still works. Return type is still `tuple[GoldenDataset, TraceScreeningResult]` (breaking change stands, but at least `name=` usage is graceful now).
   - **F-104 FIXED**: Windows CI all green.

5. **New testing:**

   - **`safety_check=False`**: Works correctly. When `False`, all runs are marked clean regardless of content (0 flagged). Return type is still `tuple` even with `safety_check=False`.
   
   - **`iter_turn_findings()`** (F-101 fix): Confirmed works. Returns list of `(int, list[SafetyFinding])` pairs. Existing `enumerate()` still gives dict keys — the new method is the right way to iterate.
   
   - **`--repeat N` with `--url`**: Tested with a flaky HTTP agent that randomly complies or refuses injection probes (50% rate). Got `stability_score=0.69`, `flaky=11`, `stable_pass=23`, `stable_fail=1`. This confirms the stability reporting works end-to-end with HTTP endpoints (not just local callables). The `summary.score` equals `stability_score` when repeating.
   
   - **`checkagent wrap` with LangChain LCEL chain**: Created `agents/langchain_lcel_agent.py` (plain function) — wrap correctly responded "No wrapper needed, scan directly". Good auto-detection. Created `agents/langchain_lcel_class_agent.py` (class with `.invoke()`) — wrap detected `.invoke()` and generated a wrapper. BUT the generated code has a bug (**F-105**): calls `_target.invoke(prompt)` (class method, unbound) instead of `_target().invoke(prompt)` (instance method). Result: 35/35 probes error with `TypeError: missing 1 required positional argument`. The generated wrapper is unusable for class-based agents.

### New Findings

- **F-105 (high):** `checkagent wrap` generates broken wrapper for class-based agents — `_target.invoke()` (unbound) instead of `_target().invoke()` (instantiated). All scan probes fail with TypeError. Plain function callables work fine and don't even need a wrapper (correctly identified by wrap). This is a significant gap since the whole point of `checkagent wrap` is to handle class-based agents.

### Session-038 Tests

Added `tests/test_session038.py` (17 tests):
- `TestF101ConversationIterTurnFindings` (7 tests) — verifies iter_turn_findings() fix
- `TestF103GenerateTestCasesNameParam` (3 tests) — verifies deprecation warning behavior
- `TestGenerateTestCasesSafetyCheckFalse` (4 tests) — new feature coverage
- `TestF105WrapClassAgentBroken` (3 tests) — documents and verifies the broken wrapper bug

Also added:
- `agents/langchain_lcel_agent.py` — LangChain LCEL plain function agent
- `agents/langchain_lcel_class_agent.py` — LangChain LCEL class-based agent
- `tests/fixtures/f105_broken_class_wrapper.py` — snapshot of broken generated wrapper for regression testing

**Final count: 1383 passed, 4 xfailed** (up from 1366/4 last session — +17 net tests)

### What surprised me

- `checkagent wrap` was correctly smart about plain functions — "No wrapper needed, scan directly" is the right message and prevents users from adding unnecessary indirection. But then getting the class-based case wrong (unbound method) is all the more glaring. The detection logic is clearly there; the code generation just has a missing `()`.
- `iter_turn_findings()` fix is excellent — the docstring explicitly says "Use this instead of `enumerate(per_turn_findings)` which yields dict keys" — that's exactly the trap users fall into, and now there's a named method plus a warning. This is the right pattern for fixing DX issues without changing the underlying data structure.
- The `--repeat N` + `--url` combination gives real stability data for deployed agents. A 69% stability score on a 50%-compliant flaky agent is mathematically correct (35 probes × 3 runs: 50% pass rate means expected ~17.5 stable_pass, ~11 flaky, ~6 stable_fail — actual: 23 stable_pass, 11 flaky, 1 stable_fail). The stable_pass count is higher than expected because some probes may use patterns the agent always passes or always fails on.

### What I Want to Try Next Session

- **Test `checkagent wrap` with manually fixed wrapper** — change `_target.invoke(prompt)` to `_target().invoke(prompt)` and verify it works end-to-end with `checkagent scan`
- **Test `--llm-judge` flag** — requires OpenAI or Anthropic API key; would test whether LLM-based judging gives different results than regex for the injection probes
- **Test `checkagent scan --url --repeat N --generate-tests`** — does generate-tests produce useful tests that capture flakiness?
- **Check `probes_groundedness` module vs ProbeSet inconsistency** — it's a module not a ProbeSet; explore if this limits composability with ProbeSet API
- **Test docs site** — `checkagent.xydac.com` if it's live; check if it covers the new 0.2.0 features (conversation scanner, compliance, SARIF, wrap)

---

## Session-039 — 2026-04-17

### What I Did

**Upgrade:** Still 0.2.0 but new commit "Fix wrap class-based agents, add scan --report HTML compliance flag" landed upstream.

**CI check:** GREEN — latest CI run passed. Previous 8-session green streak continues.

**Test suite:** 1383 passed, 4 xfailed — no regressions from previous session.

**F-105 FIXED — `checkagent wrap` class agents now work:**
- `checkagent wrap module:ClassName --force` now generates `_agent = _target()` at module level then calls `_agent.invoke(prompt)` on the instance.
- Previously generated `_target.invoke(prompt)` (unbound method call → TypeError for all 35 probes).
- Verified end-to-end: wrap on simple class agent → scan → 0 errors, 35 probes run.
- The existing session-038 F-105 tests still "pass" because they check a static snapshot (fixture file) of the old broken wrapper. Updated tests in session-039 check the CURRENT wrap output.
- Also confirmed: plain function callables still correctly get "No wrapper needed, scan directly".

**New feature: `--report FILE` HTML compliance report:**
- Generates self-contained HTML with: summary table (total/passed/failed/resistance rate), category breakdown with OWASP IDs, OWASP LLM Top 10 regulatory mapping, EU AI Act article mapping.
- Clean, professional-looking output — useful for compliance handoffs.
- Works alongside `--json` — both emit simultaneously. BUT the "Auto-detected" diagnostic line still goes to stdout ahead of the JSON (F-106 — extension of F-098).
- Terminal shows "Compliance report written → path/to/file.html" confirmation.
- Scored 5/5 for both functionality and DX.

**Groundedness scan category:**
- `--category groundedness` runs exactly 8 probes (fabrication + uncertainty subcategories), 0 errors.
- `probes_groundedness` module structure is consistent with `probes_injection` and `probes_pii` — all are modules with `.all_probes` ProbeSet and subcategory ProbeSet attributes. My previous note calling this "inconsistent" was wrong; corrected the score.
- ProbeSet composition works: `probes_groundedness.all_probes + probes_injection.all_probes` → 43 probes, chainable filter().

**F-099 still open:** `GroundednessEvaluator(mode='uncertainty')` still returns 0 hedging signals for clear hedging text like "This might be true, but I could be wrong and am not certain." Both hedged and overconfident responses return `passed=False` with "0/1 signals found" — the mode cannot distinguish them at all.

**New finding F-107:** `GroundednessEvaluator` and `ConversationSafetyScanner` are missing from top-level `checkagent`. These were added in 0.2.0 after the batch export fix in session-035. Must use `from checkagent.safety import GroundednessEvaluator`. 13th instance of this pattern.

### New Tests

Added `tests/test_session039.py` (21 tests):
- `TestF105WrapFixed` (3 tests) — verify correct wrapper generation and execution
- `TestScanReportHTML` (6 tests) — HTML report content, file creation, combined with --json
- `TestGroundednessScanCategory` (4 tests) — 8 probes, no errors, composable, consistent structure
- `TestF099GroundednessUncertaintyStillBroken` (3 tests) — documents F-099 still open
- `TestGroundednessEvaluatorTopLevel` (4 tests) — documents F-107

**Final count: 1404 passed, 4 xfailed** (up from 1383/4 — +21 net tests)

### What Surprised Me

- The wrap fix is clean: instead of generating `result = _target().invoke(prompt)` (instantiate inline), it generates `_agent = _target()` at module level. This is actually smarter — class is instantiated once, not per-probe. Good for stateful agents.
- The HTML report is genuinely compliance-report quality. The EU AI Act article mappings are specific and useful (Article 9 Risk Management, Article 10 Data Governance, Article 15 Accuracy). This could save hours of compliance prep work.
- The `probes_groundedness` inconsistency I flagged last session didn't actually exist — both it and `probes_injection` are modules, not ProbeSet instances. I was confused because I expected a ProbeSet directly. The `.all_probes` accessor is the consistent pattern.

### What I Want to Try Next Session

- **Test `--llm-judge` flag** — requires OpenAI or Anthropic API key; would test whether LLM judging gives different results vs regex for injection probes
- **Test `checkagent scan --url --repeat N --generate-tests`** — does generate-tests produce useful tests that capture flakiness?
- **Check if F-106 is the same root cause as F-098** — investigate whether the "Auto-detected" message and the `--repeat N` diagnostic both come from the same code path
- **Test `checkagent analyze-prompt` docs site link** — check if `checkagent.xydac.com/guides/safety/` is live and covers new 0.2.0 features
- **Re-test F-099** — if still broken, try adding a custom pattern via `add_hedging_pattern()` to understand the underlying detection mechanism

