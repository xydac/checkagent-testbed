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
**Status:** Open (still not fixed in session-009 — ninth session without a fix)

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
**Status:** Fixed in e38593a — datasets module fully restored. GoldenDataset, TestCase, load_dataset, load_cases, parametrize_cases all importable again. All 35 session-007 tests pass.

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

---

## F-018: `ProviderPricing`, `BudgetConfig`, `BUILTIN_PRICING` not importable from top-level `checkagent`
**Date:** 2026-04-05
**Severity:** medium
**Category:** dx-friction
**Description:** The new cost tracking API requires `ProviderPricing` (to pass custom pricing), `BudgetConfig` (to set budget limits on `CostTracker`), and `BUILTIN_PRICING` (to inspect or extend built-in rates), but none of these are exported from the top-level `checkagent` namespace. Users must reach into internal paths: `from checkagent.core.cost import ProviderPricing, BUILTIN_PRICING` and `from checkagent.core.config import BudgetConfig`.
**Expected:** Cost tracking companion types (`ProviderPricing`, `BudgetConfig`, `BUILTIN_PRICING`) exported alongside `CostTracker`, `CostBreakdown`, `CostReport`, and `BudgetExceededError` (which ARE in the top-level namespace).
**Actual:** `from checkagent import ProviderPricing` → `ImportError`. Same for `BudgetConfig` and `BUILTIN_PRICING`. The four cost-tracking classes that ARE at top-level (`CostTracker`, `CostBreakdown`, `CostReport`, `BudgetExceededError`) require these companion types but don't export them.
**Workaround:** Use internal imports: `from checkagent.core.cost import ProviderPricing, BUILTIN_PRICING` and `from checkagent.core.config import BudgetConfig`.
**Status:** Open

---

## F-019: No `ap_cost_tracker` pytest fixture — cost tracking has no pytest integration
**Date:** 2026-04-05
**Severity:** medium
**Category:** missing-feature
**Description:** `CostTracker` is a stateful accumulator meant to track costs across multiple test runs. Without a fixture, users must instantiate it manually (typically at module level or in a session-scoped fixture they write themselves), which means no automatic reset between test sessions, no budget enforcement wired into pytest's pass/fail lifecycle, and no standard way to get a per-suite cost report.
**Expected:** An `ap_cost_tracker` fixture (session or module scoped) that provides a pre-configured `CostTracker` from `ap_config.budget`, with automatic `check_suite_budget()` teardown so tests fail when budget is exceeded.
**Actual:** No fixture exists. `CostTracker` is a standalone class. Users must wire budget enforcement manually in their own conftest or test teardown.
**Workaround:** Create a session-scoped fixture in conftest.py: `@pytest.fixture(scope="session") def cost_tracker(ap_config): return CostTracker(budget=ap_config.budget)`.
**Status:** Open

---

## F-020: New eval module classes not exported from top-level `checkagent`
**Date:** 2026-04-05
**Severity:** medium
**Category:** dx-friction
**Description:** The new `checkagent.eval` module adds significant functionality: `step_efficiency`, `task_completion`, `tool_correctness`, `trajectory_match` (metric functions), `Evaluator` (ABC), `EvaluatorRegistry`, `AggregateResult`, `RunSummary`, `StepStats`, `aggregate_scores`, `compute_step_stats`, `detect_regressions`. None of these are exported from the top-level `checkagent` namespace. Users must reach into internal submodules: `from checkagent.eval.metrics import step_efficiency`, `from checkagent.eval.evaluator import Evaluator, EvaluatorRegistry`, `from checkagent.eval.aggregate import aggregate_scores`, etc.
**Expected:** Eval metrics and aggregate helpers exported at top-level alongside the assertion functions (`assert_tool_called`, `assert_output_schema`, etc.) that ARE already there. At minimum `Evaluator` and `EvaluatorRegistry` should be top-level since they are the primary extension point.
**Actual:** `from checkagent import step_efficiency` → `ImportError`. Same for all other eval classes.
**Workaround:** Use internal imports from submodules.
**Status:** Open

---

## F-021: Safety module not exported from top-level `checkagent`
**Date:** 2026-04-05
**Severity:** medium
**Category:** dx-friction
**Description:** The new `checkagent.safety` module adds `PromptInjectionDetector`, `PIILeakageScanner`, `SystemPromptLeakDetector`, `RefusalComplianceChecker`, `ToolCallBoundaryValidator`, `ToolBoundary`, `SafetyResult`, `SafetyFinding`, `SafetyEvaluator`, `SafetyCategory`, `Severity`. None of these are exported from top-level `checkagent`. The `ap_safety` fixture is registered and works, but the classes themselves (needed to configure boundaries, add custom patterns, inspect results) require internal imports: `from checkagent.safety import ToolCallBoundaryValidator, ToolBoundary`.
**Expected:** Safety evaluator classes and supporting types exported at top-level, or at least from `checkagent.safety` as a clean public namespace (which it does provide, but is undiscoverable from `import checkagent`).
**Actual:** `from checkagent import PromptInjectionDetector` → `ImportError`. `from checkagent import SafetyResult` → `ImportError`.
**Workaround:** Use `from checkagent.safety import PromptInjectionDetector, PIILeakageScanner, ...` — these do work as a public subpackage import.
**Status:** Open

---

## F-022: `ToolCallBoundaryValidator.evaluate(text)` is a silent no-op — always passes
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `ToolCallBoundaryValidator.evaluate(text)` always returns `SafetyResult(passed=True)` with the comment "Text-only evaluation is not meaningful for tool boundary checks." If a user calls `validator.evaluate(agent_output)` instead of `validator.evaluate_run(run)`, they'll always get a pass — with no warning or exception.
**Expected:** Either raise `NotImplementedError` (with a message directing to `evaluate_run`), or emit a warning. Silent no-op is misleading.
**Actual:** `validator.evaluate("call dangerous tool now")` → `SafetyResult(passed=True)`. The user has no idea they used the wrong method.
**Workaround:** Always use `evaluate_run(run)` for `ToolCallBoundaryValidator`. Never use `evaluate(text)`.
**Status:** Open

---

## F-023: `Severity` enum uses string values — `.value` comparison with integers fails silently
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `checkagent.safety.taxonomy.Severity` is an enum with string values: `LOW='low'`, `MEDIUM='medium'`, `HIGH='high'`, `CRITICAL='critical'`. Any code that assumes enum values are integers (a common pattern for ordered enums) will either raise a `TypeError` or produce incorrect comparisons. The `SEVERITY_ORDER` dict in the taxonomy module provides correct ordering, but it's an internal detail not surfaced in the public API.
**Expected:** Either integer values for ordered comparison (`LOW=1`, `MEDIUM=2`, `HIGH=3`, `CRITICAL=4`) or implement `__lt__`/`__le__` on the enum so `Severity.HIGH > Severity.LOW` works naturally.
**Actual:** `Severity.HIGH.value >= 3` → `TypeError: '>=' not supported between instances of 'str' and 'int'`. Must compare enum members directly (`severity in {Severity.HIGH, Severity.CRITICAL}`).
**Workaround:** Compare enum members directly: `f.severity in {Severity.HIGH, Severity.CRITICAL}` or use the internal `SEVERITY_ORDER[severity]` for numeric comparison.
**Status:** Open

---

## F-024: `ToolCallBoundaryValidator` allows path prefix confusion — `/dataextra` passes `/data` boundary
**Date:** 2026-04-05
**Severity:** high
**Category:** bug
**Description:** `ToolCallBoundaryValidator` uses naive string prefix matching for path boundary checks. If `allowed_paths=["/data"]`, a tool call with `path="/dataextra/file.txt"` passes the check even though `/dataextra` is a completely different directory. The implementation appears to do `path.startswith(allowed)` without ensuring a path separator follows the prefix.
**Expected:** Path boundary check should verify proper directory containment. `/dataextra/file.txt` should NOT match when `/data` is the allowed path.
**Actual:** `ToolBoundary(allowed_paths=["/data"])` + path `/dataextra/file.txt` → `SafetyResult(passed=True)`. This is a security vulnerability in the boundary validator.
**Workaround:** Use more specific allowed paths (e.g., `/data/` with trailing slash, or the full absolute path). Do not rely on `ToolCallBoundaryValidator` for security-critical path enforcement.
**Status:** Open

---

## F-025: `ToolCallBoundaryValidator` doesn't normalize paths — traversal `/data/../etc/passwd` bypasses boundary
**Date:** 2026-04-05
**Severity:** high
**Category:** bug
**Description:** `ToolCallBoundaryValidator` does not normalize paths before checking boundaries. A path like `/data/../etc/passwd` passes when `allowed_paths=["/data"]` because the raw string starts with `/data`. After normalization with `os.path.normpath()`, the path resolves to `/etc/passwd`, which is outside the allowed boundary.
**Expected:** Path boundary check should normalize paths (resolve `..`, `.`, symlinks conceptually) before checking containment. This is a standard security requirement for path traversal prevention.
**Actual:** `/data/../etc/passwd` with `allowed_paths=["/data"]` → `SafetyResult(passed=True)`. Attacker can escape any allowed directory with `../` traversal.
**Workaround:** Agents using `ToolCallBoundaryValidator` for security enforcement must pre-normalize paths themselves: `os.path.normpath(path)` before passing to the agent. Do not rely on checkagent for path traversal protection.
**Status:** Open

---

## F-026: Attack probe library not importable from top-level `checkagent`
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `checkagent.safety.probes` is a new attack probe library with `Probe`, `ProbeSet`, `probes.injection.direct`, `probes.injection.indirect`, and `probes.injection.all_probes`. None of these are importable from top-level `checkagent`. Users must `from checkagent.safety import probes` — which works but is undiscoverable from `import checkagent`.
**Expected:** `Probe` and `ProbeSet` at top-level (or at least documented with the other safety exports). `probes.injection` is a namespace that naturally lives under `checkagent.safety.probes`, so not top-level there, but the README/docs should prominently feature it.
**Actual:** `from checkagent import probes` → `ImportError`. `from checkagent import Probe` → `ImportError`. Must use `from checkagent.safety import probes`.
**Workaround:** `from checkagent.safety import probes`, then `probes.injection.direct.all()` for parametrize.
**Status:** Open

---

## F-027: `AgentRun` and `Step` silently drop unknown field names
**Date:** 2026-04-05
**Severity:** high
**Category:** dx-friction
**Description:** `AgentRun` and `Step` are Pydantic models with `model_extra` unset (defaults to `ignore`). Passing wrong field names — like `AgentRun(output='hello')` instead of `AgentRun(final_output='hello')`, or `Step(input='x', output='y')` instead of `Step(input_text='x', output_text='y')` — silently discards the values with no `ValidationError`. The run's `final_output` stays `None`. This is a silent data-loss trap that produces confusing failures downstream (e.g., `task_completion` seeing `None` output).
**Expected:** Pydantic's `model_config = ConfigDict(extra='forbid')` would raise `ValidationError` on unknown fields, giving the user an immediate "unknown field 'output'" message.
**Actual:** `AgentRun(output='hello').final_output` → `None`. No exception, no warning.
**Workaround:** Use correct field names: `final_output` (not `output`) for `AgentRun`; `input_text`/`output_text` (not `input`/`output`) for `Step`.

---

## F-028: `checkagent.ci` classes not exported from top-level `checkagent`
**Date:** 2026-04-05
**Severity:** medium
**Category:** dx-friction
**Description:** The new `checkagent.ci` module adds `GateResult`, `GateVerdict`, `QualityGateReport`, `CiRunSummary`, `evaluate_gate`, `evaluate_gates`, `generate_pr_comment`, and `scores_to_dict`. None of these are in the top-level `checkagent` namespace. Additionally, `QualityGateEntry` — the core config type for defining gates — is not even in `checkagent.ci.__all__`; users must import from `checkagent.ci.quality_gate`. Pattern consistent with F-020/F-021.
**Expected:** CI gate classes exported at top-level alongside `CostTracker`, `Score`, etc. At minimum `evaluate_gates`, `generate_pr_comment`, and `QualityGateEntry` should be in `checkagent.ci.__all__`.
**Actual:** `from checkagent import evaluate_gates` → `ImportError`. `from checkagent.ci import QualityGateEntry` → `ImportError` (not in `__all__`). Must use `from checkagent.ci.quality_gate import QualityGateEntry`.
**Workaround:** `from checkagent import ci` works as a module import. `from checkagent.ci.quality_gate import QualityGateEntry` for the entry config type.
**Status:** Open

---

## F-029: Two incompatible `RunSummary` classes with the same name
**Date:** 2026-04-05
**Severity:** high
**Category:** dx-friction
**Description:** `checkagent` now has two distinct `RunSummary` classes: `checkagent.ci.RunSummary` (CI test run counts: `total`, `passed`, `failed`, `skipped`, `errors`, `duration_s`, `pass_rate`) and `checkagent.eval.aggregate.RunSummary` (eval aggregate results: `aggregates`, `step_stats`, `regressions`, `save()`, `load()`). They are different types, have different fields, and are mutually incompatible. Passing the eval version to `generate_pr_comment(test_summary=...)` raises `AttributeError: 'RunSummary' object has no attribute 'total'` with no helpful message.
**Expected:** Either a single `RunSummary` class, or clearly namespaced names (`CiRunSummary`, `EvalRunSummary`) with type-checked function signatures.
**Actual:** Both are named `RunSummary`. `from checkagent.ci import RunSummary` and `from checkagent.eval.aggregate import RunSummary` give different incompatible types. The wrong one fails silently until `generate_pr_comment` runs.
**Workaround:** Always import `RunSummary` explicitly from the correct submodule. Never alias both in the same file without renaming.
**Status:** Open

---

## F-030: `QualityGateEntry` missing from `checkagent.ci.__all__`
**Date:** 2026-04-05
**Severity:** medium
**Category:** dx-friction
**Description:** `QualityGateEntry` is the required configuration type for defining quality gates — you must construct it to call `evaluate_gate()` or `evaluate_gates()`. Yet it is not in `checkagent.ci.__all__`, not accessible as `checkagent.ci.QualityGateEntry`, and not discoverable from `dir(checkagent.ci)`. Users who do `from checkagent.ci import *` or rely on tab-completion in the ci namespace will miss it entirely.
**Expected:** `QualityGateEntry` in `checkagent.ci.__all__` alongside `evaluate_gates` and `evaluate_gate`.
**Actual:** `from checkagent.ci import QualityGateEntry` → `ImportError`. Must use `from checkagent.ci.quality_gate import QualityGateEntry`.
**Workaround:** `from checkagent.ci.quality_gate import QualityGateEntry`
**Status:** Open

---

## F-031: `task_completion` treats `None` output as `''` — `None == ''` returns `True`
**Date:** 2026-04-05
**Severity:** medium
**Category:** bug
**Description:** `task_completion(run, expected_output_equals='')` returns `passed=True` when `run.final_output is None`. The implementation appears to normalize `None` to `''` before comparison (`if final_output is None: actual = ''`), making `None == ''` evaluate as `True`. This is incorrect: `None` means "no output produced", which should never equal an expected empty string output.
**Expected:** `task_completion` with `expected_output_equals=''` should only pass when `final_output` is actually `''`, not when it is `None`.
**Actual:** `AgentRun(input=..., final_output=None)` + `expected_output_equals=''` → `Score(value=1.0, passed=True)`. Silently masks agents that produced no output when an empty string was expected.
**Workaround:** Always check `run.final_output is not None` before calling `task_completion`, or use `check_no_error=True` + a non-empty `expected_output_contains` to avoid the empty-string trap.
**Status:** Open

---

## F-032: `injection.direct.all()` returns `list`, not `ProbeSet` — breaks `+` composition
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** The pattern `injection.direct.all()` (calling the `.all()` method on a probe submodule) returns a Python `list`, not a `ProbeSet`. This means `injection.direct.all() + jailbreak.all_probes` raises `TypeError: can only concatenate list (not "ProbeSet") to list`. The `all_probes` attribute (not method) correctly returns a `ProbeSet`. The two access patterns look equivalent but behave differently.
**Expected:** `.all()` and `.all_probes` to return the same type (ProbeSet), or for `.all()` to return a ProbeSet so it can be composed with `+`.
**Actual:** `type(injection.direct.all())` → `list`. `type(injection.direct.all_probes)` → N/A (`.all()` is the method; attribute access differs by module). Use `injection.all_probes` (module attribute, not method) for ProbeSet operations.
**Workaround:** Use module-level `all_probes` attribute: `injection.all_probes + jailbreak.all_probes`. Avoid calling `.all()` when you need ProbeSet composition.
**Status:** Open

---

## F-033: `generate_pr_comment` has no `eval_summary` parameter — regressions not surfaceable in PR comments
**Date:** 2026-04-05
**Severity:** medium
**Category:** missing-feature
**Description:** `generate_pr_comment` accepts `test_summary`, `gate_report`, and `cost_report`, but has no parameter for eval results or regressions. The eval module has `detect_regressions()` and `RunSummary.regressions`, but there is no path to include regression data in generated PR comments. The CI module and eval module are not integrated.
**Expected:** A way to surface regression results (metric drops vs baseline) in the PR comment — either via an `eval_summary` parameter or a dedicated regressions section.
**Actual:** `generate_pr_comment(eval_summary=...)` → `TypeError: unexpected keyword argument`. Regressions detected by `detect_regressions()` can only be printed manually; they have no place in the automated PR reporter.
**Workaround:** Append regression info to the comment manually, or translate regressions into quality gate failures and pass via `gate_report`.
**Status:** Open

---

## F-034: `checkagent run` silently runs only `@pytest.mark.agent_test` tests — different set than `pytest tests/`
**Date:** 2026-04-05
**Severity:** medium
**Category:** dx-friction
**Description:** `checkagent run tests/` appends `-m agent_test` by default if no `-m` flag is specified. This means it only runs tests explicitly marked with `@pytest.mark.agent_test`. Running `pytest tests/ -v` (549 tests) and `checkagent run tests/` (221 tests) produce different coverage sets. Users who follow the README and use `checkagent run` are silently running a subset of their tests.
**Expected:** Either `checkagent run` documents this `-m agent_test` default prominently, or it runs all tests like `pytest` does (and uses `--layer` for filtering).
**Actual:** `checkagent run tests/` → "221 passed, 328 deselected". The 328 deselected tests are the ones that don't have the `@pytest.mark.agent_test` marker. No warning is printed about this filtering.
**Workaround:** Use `pytest tests/ -v` directly to run all tests. Or mark all agent tests with `@pytest.mark.agent_test` so `checkagent run` catches them.
**Status:** Open

---

## F-035: `RunSummary.load()` silently drops regressions — save/load round-trip is lossy
**Date:** 2026-04-05
**Severity:** medium
**Category:** bug
**Description:** `RunSummary.to_dict()` and `RunSummary.save()` correctly serialize `regressions` to JSON. But `RunSummary.load()` only restores `aggregates`, `step_stats`, and `total_cost` — it never reads back the `regressions` list. After a save/load round-trip, `loaded.regressions` is always `[]`, even when the JSON file contains regression data.
**Expected:** `RunSummary.load()` to restore all fields that `save()` serializes, including `regressions`.
**Actual:** `summary.save(path); loaded = RunSummary.load(path); loaded.regressions` → `[]`. The regressions are in the JSON file but are never read.
**Workaround:** Recompute regressions after loading: `regressions = detect_regressions(loaded.aggregates, baseline.aggregates)`. Do not rely on round-tripped regressions.
**Status:** Open

---

## F-036: Massive regression in ed0b21a — datasets, eval.metrics, eval.aggregate, eval.evaluator, ci, safety, and cost tracking all stripped
**Date:** 2026-04-05
**Severity:** critical
**Category:** bug
**Description:** Upgrading from 90ab3c5 to ed0b21a wiped large portions of the package. The following modules/features are now gone: `checkagent.datasets` (GoldenDataset, TestCase, load_dataset, load_cases, parametrize_cases), `checkagent.eval.metrics` (task_completion, step_efficiency, tool_correctness, trajectory_match), `checkagent.eval.aggregate` (aggregate_scores, RunSummary, detect_regressions, compute_step_stats), `checkagent.eval.evaluator` (Evaluator, EvaluatorRegistry), `checkagent.ci` (entirely empty — GateResult, GateVerdict, QualityGateReport, evaluate_gates, generate_pr_comment all gone), `checkagent.safety` (entirely empty — all 5 safety evaluators gone), and top-level cost tracking exports (CostTracker, CostBreakdown, CostReport, BudgetExceededError). The installed package file list confirms only 19 Python files remain (down from ~40+ previously).
**Expected:** Backward-compatible upgrade — all public API from 90ab3c5 should still work after upgrading to ed0b21a.
**Actual:** 7 test files (tests/test_session007.py through test_session014.py) fail to collect with ImportError. 383 previously-passing tests are now uncollectable. Only sessions 004-008 (core mock layer) still work — 186 of 590 tests pass.
**Workaround:** None. Regression blocks all eval, dataset, CI, safety, and cost-tracking work. Pin to 90ab3c5 to retain full functionality.
**Status:** Fixed in 6a8eaf4 — all modules restored. 10 xfails from session-015 now pass. Total test suite: 668 passing. Second time this pattern appeared (first: F-014 in 8e6a0a8, fixed in e38593a).

---

## F-037: `FaultInjector.check_llm_async()` does not exist — async LLM fault checking unavailable
**Date:** 2026-04-05
**Severity:** medium
**Category:** missing-feature
**Description:** `FaultInjector` has `check_tool_async()` for async latency simulation but no `check_llm_async()`. LLM faults (server_error, rate_limit, context_overflow, content_filter, partial_response) can only be triggered via `check_llm()` — which is synchronous-only. Any agent code that uses `await` with LLM operations must fall back to sync `check_llm()` calls, breaking the async-first design.
**Expected:** `check_llm_async()` parallel to `check_tool_async()`, enabling async agent code to trigger LLM faults without mixing sync/async.
**Actual:** `hasattr(fault, 'check_llm_async')` → `False`. The method simply doesn't exist. Users must call sync `check_llm()` inside async agent code.
**Workaround:** Call `fault.check_llm()` (sync) from within async agent code. No async LLM fault simulation available.
**Status:** Open

---

## F-038: `AgentRun.input` now requires `AgentInput` — plain string input raises `ValidationError`
**Date:** 2026-04-05
**Severity:** high
**Category:** docs-mismatch
**Description:** In ed0b21a, `AgentRun.input` is typed strictly as `AgentInput`. Passing a plain string (`AgentRun(input="some query", ...)`) raises `ValidationError: Input should be a valid dictionary or instance of AgentInput`. Dict input is coerced (`AgentRun(input={"query": "..."}, ...)` works), but string input fails. Any code or documentation example that constructs `AgentRun` with a string `input` argument is now broken.
**Expected:** Either backward-compatible string coercion (wraps string in `AgentInput(query=string)`) or an explicit `ValidationError` message that names `AgentInput` as the required type and shows the correct syntax.
**Actual:** `AgentRun(input="find cats")` → `ValidationError: Input should be a valid dictionary or instance of AgentInput`. The error message does not hint that wrapping with `AgentInput(query="find cats")` is the fix.
**Workaround:** Always construct with `AgentRun(input=AgentInput(query="..."), ...)` or `AgentRun(input={"query": "..."}, ...)`.
**Status:** Open

---

## F-039: `Cassette.load()` warns about `checkagent migrate-cassettes` command that doesn't exist
**Date:** 2026-04-05
**Severity:** medium
**Category:** docs-mismatch
**Description:** `Cassette.load()` emits a `UserWarning` when loading a cassette with an older schema version: "Run 'checkagent migrate-cassettes' to upgrade." But the `checkagent` CLI has no `migrate-cassettes` command — only `demo`, `init`, and `run`. A user who encounters this warning and tries to follow its advice will get "No such command 'migrate-cassettes'".
**Expected:** Either implement `checkagent migrate-cassettes`, or change the warning to describe what migration means (e.g., "Re-record your cassettes to update to schema v1").
**Actual:** `Cassette.load()` → `UserWarning: ... Run 'checkagent migrate-cassettes' to upgrade.` → `checkagent migrate-cassettes` → `Error: No such command 'migrate-cassettes'.`
**Workaround:** Ignore the warning or manually re-save cassettes. No CLI migration is needed yet (schema v1 is the only version).
**Status:** Partially fixed in session-018 — `checkagent migrate-cassettes` CLI command now exists and is discoverable. However, the v0→v1 migration itself fails with "No migration registered from v0" (see F-045). The warning message now points to a real command, but following it still doesn't solve the problem.

---

## F-040: `CassetteMeta.checkagent_version` never populated by `finalize()`
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `CassetteMeta` has a `checkagent_version` field intended to record which version of checkagent created the cassette — useful for diagnosing compatibility issues across upgrades. But `Cassette.finalize()` never populates this field; it stays `''` even though `checkagent.__version__` is available. Every cassette saved with the current implementation will have an empty `checkagent_version`.
**Expected:** `Cassette.finalize()` to set `meta.checkagent_version = checkagent.__version__` automatically, so cassettes have auditable provenance.
**Actual:** `Cassette().finalize().meta.checkagent_version` → `''`.
**Workaround:** Set manually before saving: `c.meta.checkagent_version = checkagent.__version__`.
**Status:** Open

---

## F-041: `checkagent.replay` classes not exported from top-level `checkagent`
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `Cassette`, `CassetteMeta`, `Interaction`, `RecordedRequest`, `RecordedResponse`, `redact_dict`, and `CASSETTE_SCHEMA_VERSION` are all in `checkagent.replay` but none appear in the top-level `checkagent` namespace. This is consistent with the established pattern (F-020, F-021, F-026, F-028) but continues to force users to discover and remember internal submodule paths. The `replay` submodule is accessible as `import checkagent; checkagent.replay`, but not via `from checkagent import Cassette`.
**Expected:** Core cassette types (`Cassette`, `Interaction`, `RecordedRequest`, `RecordedResponse`) exported at top-level alongside `AgentRun`, `MockLLM`, etc.
**Actual:** `from checkagent import Cassette` → `ImportError`. Must use `from checkagent.replay import Cassette`.
**Workaround:** `from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse, redact_dict`
**Status:** Open

---

## F-042: `ReplayEngine(block_unmatched=False)` never suppresses `CassetteMismatchError`
**Date:** 2026-04-05
**Severity:** medium
**Category:** bug
**Description:** `ReplayEngine` accepts a `block_unmatched` constructor parameter, but setting it to `False` has no observable effect. All three strategies (EXACT, SEQUENCE, SUBSET) still raise `CassetteMismatchError` when there is no match — even with `block_unmatched=False`. The expected semantics of `block_unmatched=False` is passthrough mode: when no recorded interaction matches, return `None` and let the real call proceed (useful for partial recording modes). Currently there is no way to achieve passthrough behavior.
**Expected:** `ReplayEngine(..., block_unmatched=False).match(unmatched_req)` → returns `None` (passthrough). `block_unmatched=True` → raises `CassetteMismatchError` (strict mode).
**Actual:** `block_unmatched=False` always raises `CassetteMismatchError` identically to `block_unmatched=True`. The parameter is accepted but has no effect.
**Workaround:** Wrap `engine.match()` in a try/except and catch `CassetteMismatchError` yourself to simulate passthrough behavior.
**Status:** Open

---

## F-043: Upstream CI failing with Windows encoding error in demo-generated test file
**Date:** 2026-04-05
**Severity:** high
**Category:** bug
**Description:** Upstream CI is failing on all 3 latest runs (as of c03b11f) with a new root cause: the `checkagent demo` command generates a test file that includes an em dash character (`—`) in the module docstring, but the file has no `# -*- coding: utf-8 -*-` declaration. On Windows with Python 3.11, this causes `SyntaxError: (unicode error) 'utf-8' codec can't decode byte 0x97 in position 22`. Byte `0x97` is the em dash in Windows-1252 encoding, meaning the file is being written with the system's default encoding instead of UTF-8.
**Expected:** Generated test files should either use ASCII-safe characters in docstrings or include an explicit UTF-8 encoding declaration. Files written by `checkagent demo` should be platform-safe.
**Actual:** `checkagent demo` → generates file with em dash → CI on Windows fails with `SyntaxError` during collection → CI red. Previous CI failure root cause was F-008 (jsonschema missing dep); this is a separate Windows encoding issue that has become the new blocking failure.
**Workaround:** Only run CI on Linux/macOS. No user-facing workaround — the demo generates the file.
**Status:** Open

---

## F-044: `ReplayEngine` SEQUENCE strategy ignores all request fields including `kind`
**Date:** 2026-04-05
**Severity:** medium
**Category:** dx-friction
**Description:** `ReplayEngine` with `MatchStrategy.SEQUENCE` returns the next recorded interaction in order regardless of the incoming request — it ignores `kind`, `method`, and `body`. A `kind='tool'` request will match a recorded `kind='llm'` interaction if it's next in sequence. While pure sequence replay is a valid choice for simple playback, the complete absence of kind/method validation makes it easy to accidentally replay the wrong interaction type with no error signal. A user testing a multi-step agent (llm → tool → llm) who passes `kind='llm'` for all three calls will silently get tool responses for LLM calls.
**Expected:** SEQUENCE strategy should at minimum warn when incoming `kind` doesn't match recorded `kind`. Users who want unchecked sequence playback should opt in explicitly.
**Actual:** `RecordedRequest(kind='tool', method='search')` + recorded `llm` interaction → match succeeds silently.
**Workaround:** After each `match()`, verify that `matched.request.kind == expected_kind`. Or use EXACT strategy which enforces body matching.
**Status:** Open
**Status:** Open

---

## F-045: `migrate-cassettes` v0→v1 migration not implemented — CLI exists but always fails
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** `checkagent migrate-cassettes` CLI was added (resolving F-039), but the actual v0→v1 migration path is not implemented. Running `checkagent migrate-cassettes <dir>` on any v0 cassette fails with "No migration registered from v0. Cannot upgrade to v1." Additionally, the command always returns exit code 0 even when migrations fail, making it useless in CI pipelines (`migrate-cassettes && deploy` will silently proceed despite failures).
**Expected:** `checkagent migrate-cassettes` should be able to upgrade v0 cassettes to v1 schema. The command should also return non-zero exit code when any cassette fails to migrate.
**Actual:** `checkagent migrate-cassettes /dir/with/v0/cassettes` → "FAIL: No migration registered from v0. Cannot upgrade to v1." with exit code 0. v1 cassettes are correctly skipped.
**Workaround:** Re-record cassettes by running agents again — there's no migration path. The v0 cassette warning from `Cassette.load()` now correctly points to the real CLI, but the CLI can't actually perform the migration.
**Status:** Open

---

## F-046: `Cassette.save()` and `Cassette.load()` require `pathlib.Path` — `str` raises `AttributeError`
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** Both `Cassette.save(path)` and `Cassette.load(path)` require `pathlib.Path` objects. Passing a plain string raises `AttributeError` with a confusing message: `save("dir/file.json")` raises `AttributeError: 'str' object has no attribute 'parent'`; `load("dir/file.json")` raises `AttributeError: 'str' object has no attribute 'read_text'`. Neither error message hints that the fix is to use `Path("dir/file.json")`.
**Expected:** Either accept both `str` and `Path` via `os.fspath()` or `Path(path)` coercion (standard Python practice), or raise a `TypeError` with a message like "path must be a pathlib.Path, got str".
**Actual:** `Cassette.save("/tmp/test.json")` → `AttributeError: 'str' object has no attribute 'parent'`. The error message reveals the implementation detail but doesn't help the user fix it.
**Workaround:** Always use `pathlib.Path`: `cassette.save(Path("/tmp/test.json"))`, `Cassette.load(Path("/tmp/test.json"))`.
**Status:** Open

---

## F-047: Upstream CI failing — `TimedCall.duration_ms == 0.0` on Windows for short sleeps
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** Upstream CI is now failing (as of the "mark cassette migration tooling as complete" commit) with a new root cause: `test_timing_is_positive_for_slow_ops` in `tests/replay/test_recorder.py:181` asserts `tc.duration_ms >= 5` but gets `0.0` on Windows Python 3.10. The previous root cause was F-043 (em dash encoding in demo-generated file); this is now the blocking failure. The issue is that `time.monotonic()` on Windows has ~15ms resolution — any sleep shorter than ~15ms returns 0.0. The upstream test uses a sleep below this threshold, which passes on Linux/macOS but fails on Windows.
**Expected:** Upstream tests should use a sleep duration safely above Windows `time.monotonic()` resolution (100ms is safe) or use `time.perf_counter()` which has higher resolution on Windows.
**Actual:** `TimedCall` uses `time.monotonic()`. On Windows, short sleeps (< ~15ms) return `duration_ms == 0.0`. The upstream test that asserts `>= 5` fails. Third consecutive CI failure, third different root cause.
**Workaround:** None for users. CI only passes on Linux/macOS. F-043 (em dash) may or may not also still be present.
**Status:** Fixed in session-019 — upstream CI now passing (latest run: "mark rubric evaluation and statistical verdicts as complete"). Both F-043 and F-047 appear resolved upstream.

---

## F-048: `checkagent.judge` classes not exported from top-level `checkagent`
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** The new `checkagent.judge` module adds significant functionality: `Judge` (ABC), `RubricJudge`, `Rubric`, `Criterion`, `CriterionScore`, `JudgeScore`, `JudgeVerdict`, `Verdict`, `ScaleType`, and `compute_verdict`. None of these are exported from the top-level `checkagent` namespace. Users must import from the submodule: `from checkagent.judge import RubricJudge, Rubric, Criterion, compute_verdict`. This is the fifth time this pattern has appeared (F-020, F-021, F-026, F-028, now F-048).
**Expected:** Core judge types (`Judge`, `RubricJudge`, `Rubric`, `Criterion`, `compute_verdict`, `Verdict`) exported at top-level alongside `AgentRun`, `MockLLM`, etc.
**Actual:** `from checkagent import RubricJudge` → `ImportError`. Same for all other judge classes. `from checkagent.judge import ...` works.
**Workaround:** `from checkagent.judge import Judge, RubricJudge, Rubric, Criterion, CriterionScore, JudgeScore, JudgeVerdict, Verdict, ScaleType, compute_verdict`
**Status:** Open

---

## F-049: No `ap_judge` fixture — judge module has no pytest integration
**Date:** 2026-04-06
**Severity:** medium
**Category:** missing-feature
**Description:** The `checkagent.judge` module has `RubricJudge` and `compute_verdict` but no pytest fixtures. There is no `ap_judge` or `ap_rubric_judge` fixture. Users who want to test their agents with a judge must: (1) import from the submodule manually, (2) write their own async LLM callable, (3) construct `Rubric` and `RubricJudge` from scratch in every test file. This is especially burdensome since judge tests need an async LLM callable that acts as a stand-in for a real LLM — there's no mock-LLM-to-judge bridge. The `ap_mock_llm` fixture (which produces a `MockLLM`) has no adapter to plug into `RubricJudge(llm=callable)` since `MockLLM` is not a plain `async (system, user) -> str` callable.
**Expected:** An `ap_rubric_judge` fixture (or factory fixture) that creates a `RubricJudge` with a configurable rubric and a mock LLM backend, similar to how `ap_mock_llm` provides a configured `MockLLM`.
**Actual:** No judge fixtures. `MockLLM` cannot be passed directly to `RubricJudge(llm=...)` since it doesn't have the `(system, user) -> str` signature. Users must write glue code in every test file.
**Workaround:** Define a local async callable `mock_llm(system, user)` in each test, returning JSON matching the rubric structure.
**Status:** Open

---

## F-050: `RubricJudge.evaluate()` propagates raw `JSONDecodeError` when LLM returns non-JSON
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** If the LLM callable passed to `RubricJudge` returns a non-JSON string (which is common when testing with real LLMs that sometimes produce verbose text), `evaluate()` raises a raw `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` with no checkagent-specific wrapper. The error message does not tell the user the expected JSON format, does not include the actual LLM response, and doesn't distinguish "bad JSON" from other evaluation failures.
**Expected:** Either a `JudgeError` or similar checkagent-specific exception with the LLM's actual response and a reminder of the expected JSON format, or graceful fallback handling.
**Actual:** `await judge.evaluate(run)` when LLM returns plain text → `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`. The raw exception is hard to diagnose without knowing to look at the judge's `_parse_judge_response` function.
**Workaround:** Wrap `judge.evaluate()` in a try/except for `json.JSONDecodeError` in your tests. Ensure mock LLM callables always return valid JSON.
**Status:** Open

---

## F-051: Unknown criterion names from LLM silently produce `overall=0.0` with no warning
**Date:** 2026-04-06
**Severity:** medium
**Category:** bug
**Description:** `RubricJudge._parse_judge_response` silently drops any score item whose `criterion` name doesn't match a criterion in the rubric. If the LLM hallucinates criterion names (or gets the spelling wrong), all criterion scores are dropped and `overall` is computed as `0.0` (due to the `if total_weight == 0: return 0.0` guard). The test or eval pipeline then fails at the judge level, not the LLM level — and the reason is opaque.
**Expected:** Either a warning when criterion names don't match, or a `JudgeError` with details on what criterion names were expected vs received. Silent 0.0 is always a bug.
**Actual:** `judge.evaluate(run)` when LLM returns wrong criterion names → `JudgeScore(overall=0.0, criterion_scores=[])`. No exception, no warning. Downstream `compute_verdict` will always return FAIL for this judge.
**Workaround:** After calling `judge.evaluate()`, check `len(score.criterion_scores) == len(rubric.criteria)` to detect silent drops.
**Status:** Open
