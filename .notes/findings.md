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
