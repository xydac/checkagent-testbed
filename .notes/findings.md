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
**Status:** FIXED in session-027 — `attach_faults(injector)` method added to both `MockTool` and `MockLLM`. Faults now fire automatically without any manual guard calls. Also added `ap_fault` pytest fixture. See F-078 for a new DX issue discovered during this fix.

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
**Workaround:** Manually run `pip install jsonschema` after installing checkagent; or `pip install checkagent[json-schema]` (partial fix session-029)
**Status:** Partial fix in session-029 — `jsonschema` now declared under `[json-schema]` optional extra. Users can `pip install checkagent[json-schema]`. Still not a default dep — `assert_json_schema` breaks on bare `pip install checkagent`. CI now installs `[dev]` extras which includes `jsonschema`, so upstream tests no longer fail on this.

## F-009: `MockLLM.was_called_with` does exact match but name implies substring
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `MockLLM.was_called_with(text)` performs an exact match against `input_text` in each recorded call. If you call `llm.complete_sync("What is the capital of France?")` and then check `llm.was_called_with("capital of France")`, it returns `False` — even though the text appears in the actual input.
**Expected:** A method named `was_called_with` suggests "was this LLM called with a message containing this text" — i.e., substring matching.
**Actual:** Exact match only. `llm.was_called_with("France")` → `False` even after calling with `"What is the capital of France?"`.
**Workaround:** Use `llm.get_calls_matching("France")` for substring matching. Use `was_called_with` only when you know the exact input string.
**Status:** Fixed in v0.1.1

## F-010: `MockTool.assert_tool_called` returns None — inconsistent with top-level `assert_tool_called`
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `MockTool.assert_tool_called("name")` returns `None`, so you can't chain or inspect the returned `ToolCall`. The top-level `assert_tool_called(run, "name")` returns a `ToolCall` object, which enables natural patterns like `tc = assert_tool_called(run, "search"); assert tc.arguments["query"] == "cats"`.
**Expected:** `MockTool.assert_tool_called` to return the `ToolCallRecord` so call arguments can be inspected inline.
**Actual:** Returns `None`. Must use `tool.last_call` or `tool.calls[n]` to inspect call details.
**Workaround:** Use `tool.last_call` or `tool.calls` for call inspection after asserting.
**Status:** Fixed in v0.1.1

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
**Status:** Fixed in v0.1.1

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
**Status:** Partially improved in d0dd9265 (session-031): `calculate_run_cost` added to top-level exports (was missing before). `ProviderPricing`, `BudgetConfig`, `BUILTIN_PRICING` still require internal imports. Open.

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
**Status:** Fixed in v0.1.1

---

## F-021: Safety module not exported from top-level `checkagent`
**Date:** 2026-04-05
**Severity:** medium
**Category:** dx-friction
**Description:** The new `checkagent.safety` module adds `PromptInjectionDetector`, `PIILeakageScanner`, `SystemPromptLeakDetector`, `RefusalComplianceChecker`, `ToolCallBoundaryValidator`, `ToolBoundary`, `SafetyResult`, `SafetyFinding`, `SafetyEvaluator`, `SafetyCategory`, `Severity`. None of these are exported from top-level `checkagent`. The `ap_safety` fixture is registered and works, but the classes themselves (needed to configure boundaries, add custom patterns, inspect results) require internal imports: `from checkagent.safety import ToolCallBoundaryValidator, ToolBoundary`.
**Expected:** Safety evaluator classes and supporting types exported at top-level, or at least from `checkagent.safety` as a clean public namespace (which it does provide, but is undiscoverable from `import checkagent`).
**Actual:** `from checkagent import PromptInjectionDetector` → `ImportError`. `from checkagent import SafetyResult` → `ImportError`.
**Workaround:** Use `from checkagent.safety import PromptInjectionDetector, PIILeakageScanner, ...` — these do work as a public subpackage import.
**Status:** Fixed in v0.1.1

---

## F-022: `ToolCallBoundaryValidator.evaluate(text)` is a silent no-op — always passes
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `ToolCallBoundaryValidator.evaluate(text)` always returns `SafetyResult(passed=True)` with the comment "Text-only evaluation is not meaningful for tool boundary checks." If a user calls `validator.evaluate(agent_output)` instead of `validator.evaluate_run(run)`, they'll always get a pass — with no warning or exception.
**Expected:** Either raise `NotImplementedError` (with a message directing to `evaluate_run`), or emit a warning. Silent no-op is misleading.
**Actual:** `validator.evaluate("call dangerous tool now")` → `SafetyResult(passed=True)`. The user has no idea they used the wrong method.
**Workaround:** Always use `evaluate_run(run)` for `ToolCallBoundaryValidator`. Never use `evaluate(text)`.
**Status:** Fixed in 0.1.2

---

## F-023: `Severity` enum uses string values — `.value` comparison with integers fails silently
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `checkagent.safety.taxonomy.Severity` is an enum with string values: `LOW='low'`, `MEDIUM='medium'`, `HIGH='high'`, `CRITICAL='critical'`. Any code that assumes enum values are integers (a common pattern for ordered enums) will either raise a `TypeError` or produce incorrect comparisons. The `SEVERITY_ORDER` dict in the taxonomy module provides correct ordering, but it's an internal detail not surfaced in the public API.
**Expected:** Either integer values for ordered comparison (`LOW=1`, `MEDIUM=2`, `HIGH=3`, `CRITICAL=4`) or implement `__lt__`/`__le__` on the enum so `Severity.HIGH > Severity.LOW` works naturally.
**Actual:** `Severity.HIGH.value >= 3` → `TypeError: '>=' not supported between instances of 'str' and 'int'`. Must compare enum members directly (`severity in {Severity.HIGH, Severity.CRITICAL}`).
**Workaround:** Compare enum members directly: `f.severity in {Severity.HIGH, Severity.CRITICAL}` or use the internal `SEVERITY_ORDER[severity]` for numeric comparison.
**Status:** Fixed in 0.1.2

---

## F-024: `ToolCallBoundaryValidator` allows path prefix confusion — `/dataextra` passes `/data` boundary
**Date:** 2026-04-05
**Severity:** high
**Category:** bug
**Description:** `ToolCallBoundaryValidator` uses naive string prefix matching for path boundary checks. If `allowed_paths=["/data"]`, a tool call with `path="/dataextra/file.txt"` passes the check even though `/dataextra` is a completely different directory. The implementation appears to do `path.startswith(allowed)` without ensuring a path separator follows the prefix.
**Expected:** Path boundary check should verify proper directory containment. `/dataextra/file.txt` should NOT match when `/data` is the allowed path.
**Actual:** `ToolBoundary(allowed_paths=["/data"])` + path `/dataextra/file.txt` → `SafetyResult(passed=True)`. This is a security vulnerability in the boundary validator.
**Workaround:** Use more specific allowed paths (e.g., `/data/` with trailing slash, or the full absolute path). Do not rely on `ToolCallBoundaryValidator` for security-critical path enforcement.
**Status:** Fixed in v0.3.0. `ToolCallBoundaryValidator` now uses `ToolBoundary` dataclass internally; path prefix check requires trailing separator.

---

## F-025: `ToolCallBoundaryValidator` doesn't normalize paths — traversal `/data/../etc/passwd` bypasses boundary
**Date:** 2026-04-05
**Severity:** high
**Category:** bug
**Description:** `ToolCallBoundaryValidator` does not normalize paths before checking boundaries. A path like `/data/../etc/passwd` passes when `allowed_paths=["/data"]` because the raw string starts with `/data`. After normalization with `os.path.normpath()`, the path resolves to `/etc/passwd`, which is outside the allowed boundary.
**Expected:** Path boundary check should normalize paths (resolve `..`, `.`, symlinks conceptually) before checking containment. This is a standard security requirement for path traversal prevention.
**Actual:** `/data/../etc/passwd` with `allowed_paths=["/data"]` → `SafetyResult(passed=True)`. Attacker can escape any allowed directory with `../` traversal.
**Workaround:** Agents using `ToolCallBoundaryValidator` for security enforcement must pre-normalize paths themselves: `os.path.normpath(path)` before passing to the agent. Do not rely on checkagent for path traversal protection.
**Status:** Fixed in v0.3.0. Both path traversal and prefix bypass now blocked via `ToolBoundary` refactor.

---

## F-026: Attack probe library not importable from top-level `checkagent`
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** `checkagent.safety.probes` is a new attack probe library with `Probe`, `ProbeSet`, `probes.injection.direct`, `probes.injection.indirect`, and `probes.injection.all_probes`. None of these are importable from top-level `checkagent`. Users must `from checkagent.safety import probes` — which works but is undiscoverable from `import checkagent`.
**Expected:** `Probe` and `ProbeSet` at top-level (or at least documented with the other safety exports). `probes.injection` is a namespace that naturally lives under `checkagent.safety.probes`, so not top-level there, but the README/docs should prominently feature it.
**Actual:** `from checkagent import probes` → `ImportError`. `from checkagent import Probe` → `ImportError`. Must use `from checkagent.safety import probes`.
**Workaround:** `from checkagent.safety import probes`, then `probes.injection.direct.all()` for parametrize.
**Status:** Fixed in v0.1.1

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
**Status:** Fixed in 0.1.2

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
**Status:** Fixed in 0.1.2

---

## F-031: `task_completion` treats `None` output as `''` — `None == ''` returns `True`
**Date:** 2026-04-05
**Severity:** medium
**Category:** bug
**Description:** `task_completion(run, expected_output_equals='')` returns `passed=True` when `run.final_output is None`. The implementation appears to normalize `None` to `''` before comparison (`if final_output is None: actual = ''`), making `None == ''` evaluate as `True`. This is incorrect: `None` means "no output produced", which should never equal an expected empty string output.
**Expected:** `task_completion` with `expected_output_equals=''` should only pass when `final_output` is actually `''`, not when it is `None`.
**Actual:** `AgentRun(input=..., final_output=None)` + `expected_output_equals=''` → `Score(value=1.0, passed=True)`. Silently masks agents that produced no output when an empty string was expected.
**Workaround:** Always check `run.final_output is not None` before calling `task_completion`, or use `check_no_error=True` + a non-empty `expected_output_contains` to avoid the empty-string trap.
**Status:** Fixed in v0.1.1

---

## F-032: `injection.direct.all()` returns `list`, not `ProbeSet` — breaks `+` composition
**Date:** 2026-04-05
**Severity:** low
**Category:** dx-friction
**Description:** The pattern `injection.direct.all()` (calling the `.all()` method on a probe submodule) returns a Python `list`, not a `ProbeSet`. This means `injection.direct.all() + jailbreak.all_probes` raises `TypeError: can only concatenate list (not "ProbeSet") to list`. The `all_probes` attribute (not method) correctly returns a `ProbeSet`. The two access patterns look equivalent but behave differently.
**Expected:** `.all()` and `.all_probes` to return the same type (ProbeSet), or for `.all()` to return a ProbeSet so it can be composed with `+`.
**Actual:** `type(injection.direct.all())` → `list`. `type(injection.direct.all_probes)` → N/A (`.all()` is the method; attribute access differs by module). Use `injection.all_probes` (module attribute, not method) for ProbeSet operations.
**Workaround:** Use module-level `all_probes` attribute: `injection.all_probes + jailbreak.all_probes`. Avoid calling `.all()` when you need ProbeSet composition.
**Status:** Fixed in v0.1.1

---

## F-033: `generate_pr_comment` has no `eval_summary` parameter — regressions not surfaceable in PR comments
**Date:** 2026-04-05
**Severity:** medium
**Category:** missing-feature
**Description:** `generate_pr_comment` accepts `test_summary`, `gate_report`, and `cost_report`, but has no parameter for eval results or regressions. The eval module has `detect_regressions()` and `RunSummary.regressions`, but there is no path to include regression data in generated PR comments. The CI module and eval module are not integrated.
**Expected:** A way to surface regression results (metric drops vs baseline) in the PR comment — either via an `eval_summary` parameter or a dedicated regressions section.
**Actual:** `generate_pr_comment(eval_summary=...)` → `TypeError: unexpected keyword argument`. Regressions detected by `detect_regressions()` can only be printed manually; they have no place in the automated PR reporter.
**Workaround:** Append regression info to the comment manually, or translate regressions into quality gate failures and pass via `gate_report`.
**Status:** Fixed in 0.1.2

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
**Status:** Fixed in v0.1.1

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
**Status:** Fixed in d0dd9265 (session-030) — `check_llm_async()` added alongside F-082 fix. Verified: exists, no-fault path completes cleanly, intermittent and slow both work via async path.

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
**Status:** Partially fixed in v0.1.1 — Cassette and ReplayEngine now at top-level; CassetteMeta/CassetteMismatchError/CassetteRecorder still not exported

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
**Status:** Fixed in v0.1.1

---

## F-049: No `ap_judge` fixture — judge module has no pytest integration
**Date:** 2026-04-06
**Severity:** medium
**Category:** missing-feature
**Description:** The `checkagent.judge` module has `RubricJudge` and `compute_verdict` but no pytest fixtures. There is no `ap_judge` or `ap_rubric_judge` fixture. Users who want to test their agents with a judge must: (1) import from the submodule manually, (2) write their own async LLM callable, (3) construct `Rubric` and `RubricJudge` from scratch in every test file. This is especially burdensome since judge tests need an async LLM callable that acts as a stand-in for a real LLM — there's no mock-LLM-to-judge bridge. The `ap_mock_llm` fixture (which produces a `MockLLM`) has no adapter to plug into `RubricJudge(llm=callable)` since `MockLLM` is not a plain `async (system, user) -> str` callable.
**Expected:** An `ap_rubric_judge` fixture (or factory fixture) that creates a `RubricJudge` with a configurable rubric and a mock LLM backend, similar to how `ap_mock_llm` provides a configured `MockLLM`.
**Actual:** No judge fixtures. `MockLLM` cannot be passed directly to `RubricJudge(llm=...)` since it doesn't have the `(system, user) -> str` signature. Users must write glue code in every test file.
**Workaround:** Define a local async callable `mock_llm(system, user)` in each test, returning JSON matching the rubric structure.
**Status:** Partially fixed in d88d3e7 — `ap_judge` factory fixture now exists at `checkagent/core/plugin.py:195`. It accepts `(rubric, llm, model_name='')` and returns a `RubricJudge`. Reduces boilerplate. `MockLLM` still cannot be passed directly — users must still write their own async `(system, user) -> str` callable returning rubric-format JSON.

---

## F-050: `RubricJudge.evaluate()` propagates raw `JSONDecodeError` when LLM returns non-JSON
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** If the LLM callable passed to `RubricJudge` returns a non-JSON string (which is common when testing with real LLMs that sometimes produce verbose text), `evaluate()` raises a raw `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` with no checkagent-specific wrapper. The error message does not tell the user the expected JSON format, does not include the actual LLM response, and doesn't distinguish "bad JSON" from other evaluation failures.
**Expected:** Either a `JudgeError` or similar checkagent-specific exception with the LLM's actual response and a reminder of the expected JSON format, or graceful fallback handling.
**Actual:** `await judge.evaluate(run)` when LLM returns plain text → `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`. The raw exception is hard to diagnose without knowing to look at the judge's `_parse_judge_response` function.
**Workaround:** Wrap `judge.evaluate()` in a try/except for `json.JSONDecodeError` in your tests. Ensure mock LLM callables always return valid JSON.
**Status:** Fixed in 0.1.2

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

---

## F-052: `multi_judge_evaluate` judge_verdicts uses rubric name as key — collision when judges share rubric
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** `multi_judge_evaluate` stores per-judge verdicts in `ConsensusVerdict.judge_verdicts` keyed by `f'rubric_judge:{rubric.name}'`. In the canonical use case — same rubric evaluated by different LLM backends (GPT-4, Claude, Gemini) — all judges share the same rubric name. Their entries collide and overwrite each other in the dict, leaving only 1 entry regardless of how many judges ran. Users lose all per-judge traceability. The verdict computation itself is correct (uses an internal list), but the exposed `judge_verdicts` dict is misleading.
**Expected:** `judge_verdicts` keyed by `model_name` (the judge's `model_name` attribute, e.g. `'gpt-4'`, `'claude-3'`) or by a unique combination of rubric+model. With 3 judges, users should see 3 keys.
**Actual:** `multi_judge_evaluate([judge_gpt4, judge_claude, judge_gemini], run, ...)` where all share `rubric.name='quality'` → `judge_verdicts = {'rubric_judge:quality': <last_judge_verdict>}`. Only 1 key.
**Workaround:** Give each judge a unique rubric name: `Rubric(name='quality_gpt4')`, `Rubric(name='quality_claude')`, etc. Not ideal since you'd want the same rubric definition.
**Status:** Open

---

## F-053: `ConsensusVerdict` and `multi_judge_evaluate` not at top-level `checkagent`
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** The new multi-judge consensus API adds `ConsensusVerdict` and `multi_judge_evaluate` to `checkagent.judge`, but neither appears in the top-level `checkagent` namespace. This is the sixth instance of the same pattern (F-020, F-021, F-026, F-028, F-041, F-048, now F-053). Users who discover `multi_judge_evaluate` in the README must still remember the submodule import path.
**Expected:** `ConsensusVerdict` and `multi_judge_evaluate` exported from top-level `checkagent` alongside `AgentRun`, `MockLLM`, etc.
**Actual:** `from checkagent import ConsensusVerdict` → `ImportError`. `from checkagent import multi_judge_evaluate` → `ImportError`. Must use `from checkagent.judge import ConsensusVerdict, multi_judge_evaluate`.
**Workaround:** `from checkagent.judge import ConsensusVerdict, multi_judge_evaluate`
**Status:** Fixed in v0.1.1

---

## F-054: Upstream CI failing — LangChain adapter `duration_ms == 0.0` on Windows (fourth occurrence)
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** Upgrading to 48017850 ("mark LangChain and OpenAI adapters as complete") broke CI again. `tests/adapters/test_langchain.py::TestLangChainAdapterRun::test_error_handling` asserts `result.duration_ms > 0` but gets `0.0` on Windows Python 3.10, 3.11, and 3.12. Python 3.13 on Windows passes (it uses `time.perf_counter()` with higher resolution). This is the fourth consecutive Windows timing regression — F-043 and F-047 followed the same pattern and were fixed, but each new adapter test reintroduces it.
**Expected:** Adapter tests should use a sleep/sleep-like operation safely above Windows `time.monotonic()` resolution (~15ms), or use `>= 0` instead of `> 0`.
**Actual:** `test_error_handling` calls a chain that raises `ValueError('bad input')` immediately — no sleep — so `duration_ms` is `0.0` on Windows. The assertion `assert result.duration_ms > 0` fails.
**Workaround:** None for users. CI only passes on Linux/macOS and Python 3.13 Windows.
**Status:** Fixed in 0.1.2

---

## F-055: `langchain-core` undeclared dependency for `LangChainAdapter`
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** `LangChainAdapter` requires `langchain-core` at instantiation time but `langchain-core` is not declared in checkagent's package dependencies (`Requires: click, pluggy, pydantic, pytest-asyncio, pytest, pyyaml, rich`). On a fresh `pip install checkagent`, calling `LangChainAdapter(runnable)` raises `ImportError: LangChainAdapter requires langchain-core. Install it with: pip install langchain-core`. This is the third instance of the undeclared-dependency pattern after F-008 (jsonschema) and F-015 (dirty_equals).
**Expected:** `langchain-core` listed as an optional extra (`checkagent[langchain]`) so users see a clear installation path, or at minimum mentioned in adapter docs.
**Actual:** `pip install checkagent` → `from checkagent.adapters.langchain import LangChainAdapter; LangChainAdapter(runnable)` → `ImportError`.
**Workaround:** Manually run `pip install langchain-core` before using `LangChainAdapter`.
**Status:** Fixed in v0.1.1

---

## F-056: `LangChainAdapter.run()` sets `final_output` to raw runnable return — inconsistent with `step.output_text`
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** When a LangChain runnable returns a dict (e.g. `{'output': 'hello', 'metadata': {...}}`), `result.final_output` is the entire dict. But `result.steps[0].output_text` correctly extracts the `output` key. This inconsistency means `assert_output_matches(result, 'hello')` passes (dict contains 'hello' as substring?), but standard string comparison `result.final_output == 'hello'` fails. Additionally, when the dict has no `output` key, `step.output_text` extracts the first dict value — an undocumented heuristic. When the runnable returns a plain string, both `final_output` and `step.output_text` agree correctly.
**Expected:** Either `final_output` always extracts the `output` key from dict results (consistent with `step.output_text`), or the extraction heuristic is documented prominently.
**Actual:** `final_output={'output': 'hello', 'meta': {...}}` (full dict); `step.output_text='hello'` (extracted value). First dict value used as fallback when no `output` key.
**Workaround:** If you need a string final_output, have your runnable return a plain string, not a dict.
**Status:** Open

---

## F-057: `LangChainAdapter` and `OpenAIAgentsAdapter` not at top-level `checkagent`
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** Both new adapters are importable only from their submodule paths: `from checkagent.adapters.langchain import LangChainAdapter` and `from checkagent.adapters.openai_agents import OpenAIAgentsAdapter`. Neither is in the top-level `checkagent` namespace. This is the seventh+ instance of the same pattern (F-020, F-021, F-026, F-028, F-041, F-048, F-053, now F-057).
**Expected:** `LangChainAdapter` and `OpenAIAgentsAdapter` exported from top-level alongside `GenericAdapter`.
**Actual:** `from checkagent import LangChainAdapter` → `ImportError`.
**Workaround:** Use submodule imports: `from checkagent.adapters.langchain import LangChainAdapter`, `from checkagent.adapters.openai_agents import OpenAIAgentsAdapter`.
**Status:** Fixed in v0.1.1

---

## F-058: `JudgeScore` has no `.passed` property — forces `compute_verdict()` for single-trial checks
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** `judge.evaluate(run)` returns a `JudgeScore` with `overall` (float) but no `.passed` (bool). To check if an evaluation passed, users must call `compute_verdict(judge, run, num_trials=1)` to get a `JudgeVerdict` that has `.passed`. This adds friction for simple single-evaluation tests where you just want `assert score.passed`. `JudgeVerdict.passed` exists (as a property returning `verdict == Verdict.PASS`), but `JudgeScore` has no equivalent.
**Expected:** `JudgeScore.passed` property returning `overall >= 0.5` (or a configurable threshold), mirroring `Score.passed` in the eval metrics module.
**Actual:** `score = await judge.evaluate(run); score.passed` → `AttributeError: 'JudgeScore' object has no attribute 'passed'`.
**Workaround:** Use `compute_verdict(judge, run, num_trials=1).passed` for a single-trial pass/fail check.
**Status:** Fixed in 0.1.2

---

## F-059: Custom `Judge` subclassing: `CriterionScore` field names undocumented and non-intuitive
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** When subclassing `Judge` to write a custom judge, users must construct `CriterionScore` objects manually. The required field names (`criterion_name`, `raw_value`, `normalized`) are non-intuitive — users guess `criterion`, `value`, `scale_type`, `weight`, `weighted_score` (by analogy with `Criterion` fields and the dict keys in the LLM response format `{"criterion": ..., "value": ...}`). The Pydantic `ValidationError` gives the correct field names but there's no documentation on the custom-judge workflow.
**Expected:** Documentation or a factory method for constructing `JudgeScore` from custom judges. Field names that align with the JSON format the LLM produces (`criterion`, `value`) would also help.
**Actual:** `CriterionScore(criterion='quality', value=0.8)` → `ValidationError: Field required [criterion_name, raw_value, normalized]`. The correct usage: `CriterionScore(criterion_name='quality', raw_value=4, normalized=0.8)`.
**Workaround:** Use `CriterionScore(criterion_name=..., raw_value=..., normalized=..., reasoning=...)`.
**Status:** Open

---

## F-060: `Criterion.scale` defaults to `[1,2,3,4,5]` regardless of `scale_type=BINARY`
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** `Criterion` has a `scale` field (`list[Any]`, default `[1, 2, 3, 4, 5]`) and a `scale_type` field. When `scale_type=ScaleType.BINARY` is set without an explicit `scale`, the default `[1, 2, 3, 4, 5]` is used — a 5-point numeric scale that is inappropriate for binary judgments. Binary criteria should default to `["fail", "pass"]` or `[0, 1]`. Users who create `Criterion(name='safe', description='...', scale_type=ScaleType.BINARY)` without specifying scale get unexpected normalization behavior.
**Expected:** Default `scale` should respect `scale_type`: `BINARY` → `["fail", "pass"]`, `NUMERIC` → `[1, 2, 3, 4, 5]`, `CATEGORICAL` → explicit (no default).
**Actual:** All three scale types default to `[1, 2, 3, 4, 5]`.
**Workaround:** Always specify `scale` explicitly: `Criterion(..., scale_type=ScaleType.BINARY, scale=["fail", "pass"])`.
**Status:** Open

---

## F-061: `OpenAIAgentsAdapter` imports `from agents import Runner` — conflicts with common `agents/` directory

**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** `OpenAIAgentsAdapter.run()` lazily imports `from agents import Runner` (the openai-agents SDK package). Any project that has a local `agents/` directory on `sys.path` (common in testbed-style projects like this one) will get `ImportError: cannot import name 'Runner' from 'agents' (<local agents/__init__.py>)`. The import is lazy (inside `run()`), so it succeeds at class-level but fails at runtime — and it raises `ImportError` directly rather than returning an error in `result.error`. The testbed itself has `agents/` which triggers this conflict.
**Expected:** Either the openai-agents SDK should be imported with its canonical package name (`openai_agents`), or the adapter should catch the import error and return it in `result.error` with a helpful message about the name conflict.
**Actual:** `OpenAIAgentsAdapter(agent).run('test')` → `ImportError: cannot import name 'Runner' from 'agents' (/path/to/agents/__init__.py)`.
**Workaround:** Rename your local `agents/` directory to avoid shadowing the `agents` package, or avoid `OpenAIAgentsAdapter` entirely until the import is fixed.
**Status:** Open

---

## F-054: Upstream CI failing — LangChain adapter `duration_ms == 0.0` on Windows (fourth occurrence)
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** Upgrading to 48017850 ("mark LangChain and OpenAI adapters as complete") broke CI again. `tests/adapters/test_langchain.py::TestLangChainAdapterRun::test_error_handling` asserts `result.duration_ms > 0` but gets `0.0` on Windows Python 3.10, 3.11, and 3.12. Python 3.13 on Windows passes (it uses `time.perf_counter()` with higher resolution). This is the fourth consecutive Windows timing regression.
**Expected:** Adapter tests should use a sleep/sleep-like operation safely above Windows `time.monotonic()` resolution (~15ms), or use `>= 0` instead of `> 0`.
**Actual:** `test_error_handling` calls a chain that raises `ValueError('bad input')` immediately — no sleep — so `duration_ms` is `0.0` on Windows. The assertion `assert result.duration_ms > 0` fails.
**Workaround:** None for users. CI only passes on Linux/macOS and Python 3.13 Windows.
**Status:** Fixed in session-022 — "mark all framework adapters as complete" CI run passes on all platforms including Windows Python 3.10/3.11/3.12. LangChain adapter switched to `time.perf_counter()`.

---

## F-062: `AnthropicAdapter.final_output` is the raw message object — not the extracted text string
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** `AnthropicAdapter.run()` sets `final_output=message` where `message` is the raw `anthropic.types.Message` object. The adapter correctly extracts text into `step.output_text`, but leaves `final_output` as the entire message object. This means `result.final_output == "Paris"` is `False` even when the LLM responded "Paris" — users must do `result.steps[0].output_text`. Same pattern as F-056 (LangChain returning a dict as final_output), but arguably worse since it's an opaque SDK object.
**Expected:** `final_output` should be the extracted text string (same as `step.output_text`), or at minimum the `.text` content joined from message blocks.
**Actual:** `result.final_output` is an `anthropic.types.Message` object. `result.final_output == "some text"` is always `False`. `result.steps[0].output_text` is the string.
**Workaround:** Use `result.steps[0].output_text` for the text response. Do not use `result.final_output` as a string.
**Status:** Open

---

## F-063: `AnthropicAdapter`, `CrewAIAdapter`, `PydanticAIAdapter` not at top-level `checkagent`
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** All three new framework adapters are importable only from their submodule paths. None appear in the top-level `checkagent` namespace. This is the ninth+ instance of the same pattern (F-020, F-021, F-026, F-028, F-041, F-048, F-053, F-057, F-063). Every new module follows the same pattern — top-level adapter exports have simply never been done.
**Expected:** `AnthropicAdapter`, `CrewAIAdapter`, `PydanticAIAdapter` (and `LangChainAdapter`, `OpenAIAgentsAdapter`) all exported from top-level `checkagent`.
**Actual:** `from checkagent import AnthropicAdapter` → `ImportError`. Same for CrewAI and PydanticAI adapters.
**Workaround:** Use submodule imports: `from checkagent.adapters.anthropic import AnthropicAdapter`, etc.
**Status:** Fixed in v0.1.1

---

## F-064: `anthropic`, `crewai`, `pydantic-ai` are undeclared package dependencies
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** All three new adapters require external packages not declared in checkagent's `Requires-Dist`. `AnthropicAdapter` needs `anthropic`, `CrewAIAdapter` needs `crewai`, `PydanticAIAdapter` needs `pydantic-ai`. On a fresh `pip install checkagent`, none are installed. Each raises `ImportError` at adapter instantiation time with a helpful error message. However, none are listed as optional extras — there is no `checkagent[anthropic]`, `checkagent[crewai]`, or `checkagent[pydantic-ai]`. Fifth time this pattern appears (F-008, F-015, F-055, now F-064).
**Expected:** Each adapter's required package listed as an optional extra so users can `pip install checkagent[anthropic]` etc.
**Actual:** No extras declared. Users must manually discover and install each dep.
**Workaround:** `pip install anthropic` / `pip install crewai` / `pip install pydantic-ai` before using the respective adapters.
**Status:** Fixed in v0.1.1

---

## F-065: `checkagent.ci.junit_xml` classes not exported from top-level `checkagent`
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** The new `checkagent.ci.junit_xml` module adds `render_junit_xml`, `from_run_summary`, `from_quality_gate_report`, `JUnitTestSuite`, `JUnitTestCase`, `JUnitProperty`. These ARE accessible from `checkagent.ci` (better than some previous modules), but not from top-level `checkagent`. Tenth+ instance of the missing-top-level-export pattern. Lower severity since `checkagent.ci` is a reasonable namespace for CI utilities.
**Expected:** `render_junit_xml`, `from_run_summary`, `from_quality_gate_report` exported from top-level or prominently documented under `checkagent.ci`.
**Actual:** `from checkagent import render_junit_xml` → `ImportError`. `from checkagent.ci import render_junit_xml` works correctly.
**Workaround:** `from checkagent.ci import render_junit_xml, from_run_summary, from_quality_gate_report, JUnitTestSuite, JUnitTestCase`
**Status:** Fixed in 0.1.2

---

## F-066: `generate_test_cases` / `checkagent import-trace` crashes with raw traceback when PII causes ID collision
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** `generate_test_cases(runs, scrub_pii=True)` raises a raw `pydantic.ValidationError` traceback when two traces produce the same ID after PII scrubbing. The canonical case: "Find john@example.com" and "Find jane@example.com" both become "Find <EMAIL_1>" (scrubber resets per-run, so both emails become `<EMAIL_1>`), and `_generate_id("Find <EMAIL_1>")` produces the same hash. `GoldenDataset` then raises `ValidationError: Duplicate test case IDs`. The CLI surfaces this as an unhandled Python traceback — no friendly error message, no hint about how to fix it (e.g., use `--no-pii-scrub` or add unique context to traces).
**Expected:** Either `generate_test_cases` handles ID collision gracefully (appending a counter suffix), or the CLI catches the `ValidationError` and surfaces a user-friendly message like "Two traces produced the same test case ID after PII scrubbing. Use --no-pii-scrub or ensure queries have distinct non-PII content."
**Actual:** Raw Python traceback: `pydantic_core._pydantic_core.ValidationError: 1 validation error for GoldenDataset: Value error, Duplicate test case IDs: {'find-594f4982'}`. CLI exits with code 1 but shows full stack trace.
**Workaround:** Use `--no-pii-scrub` if traces have distinct non-PII query structures, or ensure queries have unique distinguishing words. Cannot use `generate_test_cases(scrub_pii=True)` when queries share structure but differ only in PII values.
**Status:** Open

---

## F-067: `trace_import` module not exported from top-level `checkagent`
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** `TraceImporter`, `JsonFileImporter`, `OtelJsonImporter`, `PiiScrubber`, and `generate_test_cases` are all accessible from `checkagent.trace_import` but none appear in the top-level `checkagent` namespace. `trace_import` is also not listed in `dir(checkagent)`. This is the eleventh instance of the same missing-top-level-export pattern (F-020, F-021, F-026, F-028, F-041, F-048, F-053, F-057, F-063, F-065, F-067).
**Expected:** Core trace import types (`JsonFileImporter`, `OtelJsonImporter`, `PiiScrubber`, `generate_test_cases`) exported at top-level alongside `AgentRun`, `MockLLM`, etc., or at minimum `trace_import` accessible as `checkagent.trace_import` from `dir(checkagent)`.
**Actual:** `from checkagent import JsonFileImporter` → `ImportError`. `from checkagent import generate_test_cases` → `ImportError`. `'trace_import' in dir(checkagent)` → `False`.
**Workaround:** `from checkagent.trace_import import JsonFileImporter, OtelJsonImporter, PiiScrubber, generate_test_cases`
**Status:** Open

---

## F-068: `checkagent.multiagent` module not exported from top-level `checkagent`
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** All multiagent types (`MultiAgentTrace`, `Handoff`, `BlameStrategy`, `BlameResult`, `assign_blame`, `assign_blame_ensemble`, `top_blamed_agent`) are accessible from `checkagent.multiagent` but none appear in the top-level `checkagent` namespace. `multiagent` is also not listed in `dir(checkagent)`. This is the twelfth instance of the same missing-top-level-export pattern.
**Expected:** Core multiagent types exported at top-level alongside `AgentRun`, `MockLLM`, etc., or at minimum `multiagent` accessible via `checkagent.multiagent` from `dir(checkagent)`.
**Actual:** `from checkagent import MultiAgentTrace` → `ImportError`. `from checkagent import assign_blame` → `ImportError`. `'multiagent' in dir(checkagent)` → `False`.
**Workaround:** `from checkagent.multiagent import MultiAgentTrace, Handoff, BlameStrategy, assign_blame, assign_blame_ensemble, top_blamed_agent`
**Status:** Partially fixed in v0.1.1 — MultiAgentTrace and HandoffType now at top-level; blame functions and Handoff model still not exported

---

## F-069: `LEAF_ERRORS` blame strategy has inverted leaf detection logic
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** `assign_blame(trace, BlameStrategy.LEAF_ERRORS)` is supposed to blame leaf agents — those with no outgoing handoffs — that errored. The root cause of a multi-agent failure is almost always a leaf agent. Instead, it blames agents that DO have outgoing handoffs (non-leaves). In a chain A → B where B has the actual error, `LEAF_ERRORS` blames A (the orchestrator with a child) and says "Leaf agent error (no children): [error]" — even though A clearly has a child (B) in the handoffs list.
**Expected:** `LEAF_ERRORS` should blame agent B (no outgoing handoffs → leaf) in an A → B chain.
**Actual:** `LEAF_ERRORS` blames agent A (has outgoing handoff to B → not a leaf). The "no children" message in the reason is factually wrong.
**Workaround:** Don't use `LEAF_ERRORS` strategy for actual leaf identification. Use `LAST_AGENT` or `FIRST_ERROR` as more reliable alternatives. Verify blame attribution manually in complex topologies.
**Status:** Fixed in 0.1.2

---

## F-070: `assign_blame` returns `None` silently when `AgentRun.agent_id` is not set
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** If an `AgentRun` has no `agent_id` (it defaults to `None`), `assign_blame` returns `None` even when the run clearly has an error. `assign_blame_ensemble` returns an empty list. `top_blamed_agent` returns `None`. There is no warning or error — the failure attribution silently evaporates.
**Expected:** Either raise `ValueError` ("AgentRun in trace has no agent_id — blame attribution requires agent IDs"), or use `run_id` as a fallback identifier, or at minimum emit a warning.
**Actual:** `AgentRun(input=..., error="fail")` without `agent_id` → `assign_blame(trace)` → `None`. Users who forget to set `agent_id` get no blame results and no diagnostic.
**Workaround:** Always set `agent_id` on every `AgentRun` that participates in a `MultiAgentTrace`: `AgentRun(..., agent_id='my-agent')`.
**Status:** Open

---

## F-071: `HandoffType` not importable from `checkagent.multiagent`
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** `HandoffType` (the enum for `Handoff.handoff_type` with values `delegation`, `relay`, `broadcast`) is not in `checkagent.multiagent.__all__` and cannot be imported from `checkagent.multiagent`. To create a `Handoff` with a non-default type, users must reach into the internal submodule: `from checkagent.multiagent.trace import HandoffType`.
**Expected:** `HandoffType` exported from `checkagent.multiagent` alongside `Handoff`, since it's the type of `Handoff.handoff_type` and needed to set non-default values.
**Actual:** `from checkagent.multiagent import HandoffType` → `ImportError`. Must use `from checkagent.multiagent.trace import HandoffType`.
**Workaround:** `from checkagent.multiagent.trace import HandoffType`
**Status:** Open

---

## F-072: `MultiAgentTrace` accepts handoff `agent_id`s that don't exist in any run
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** `MultiAgentTrace` does not validate that handoff `from_agent_id` and `to_agent_id` values correspond to `agent_id`s of actual runs in the trace. You can construct a trace with handoffs referencing completely fictional agent IDs and get no error or warning. This makes it easy to silently build structurally invalid traces (e.g., via typos in agent IDs) that produce incorrect blame attribution.
**Expected:** Either `ValidationError` when a handoff references an agent ID not in the runs list, or a `validate()` method that checks referential integrity.
**Actual:** `MultiAgentTrace(runs=[run_with_id_A], handoffs=[Handoff(from_agent_id='typo-ghost', to_agent_id='also-ghost')])` → no error. Blame attribution proceeds with a broken handoff graph.
**Workaround:** Manually verify handoff agent IDs match the `agent_id` of your `AgentRun` objects. Use string constants rather than inline strings to avoid typos.
**Status:** Open
**Status:** Open

---

## F-005: `checkagent init` generates broken project — tests fail immediately
**Status:** Fixed in "Fix checkagent init to generate tests that pass out of the box" (2026-04-06)
*(Original entry updated — see above for full description)*

---

## F-069: `LEAF_ERRORS` blame strategy has inverted leaf detection logic
**Status:** Fixed in 2026-04-06 — LEAF_ERRORS now correctly identifies leaf agents (no outgoing handoffs) and blames them, not the orchestrators with children.

---

## F-071: `HandoffType` not importable from `checkagent.multiagent`
**Status:** Fixed in 2026-04-06 — `HandoffType` now in `checkagent.multiagent.__all__` and importable directly.

---

## F-073: `get_children()` takes `run_id`, but all other topology methods take `agent_id`
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** `MultiAgentTrace.get_children(run_id)` takes a `run_id` (the `run_id` field of `AgentRun`) as its parameter. Every other topology method uses `agent_id`: `get_handoffs_from(agent_id)`, `get_handoffs_to(agent_id)`, `get_runs_by_agent(agent_id)`. Users who learn the pattern from other methods will call `get_children("my-agent-id")` and silently get `[]`, even if children exist under that agent. The correct call is `get_children("run-orch-001")` — the `run_id` string, not the `agent_id`.
**Expected:** `get_children` to take an `agent_id` for consistency with all other topology methods, or clearly named `get_children_by_run_id` to signal the different parameter type.
**Actual:** `trace.get_children("orchestrator")` → `[]` even when orchestrator's children exist. `trace.get_children("run-orch-001")` → correct result. No error on wrong key type.
**Workaround:** Pass `run_id` (the `run_id` field value of `AgentRun`) to `get_children()`, not `agent_id`.
**Status:** Open

---

## F-074: `add_run()` and `add_handoff()` return `None` — builder pattern not chainable
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** `MultiAgentTrace.add_run(run)` and `add_handoff(handoff)` both return `None`. They do correctly mutate `trace.runs` and `trace.handoffs`. But because they return `None`, the natural builder pattern `trace.add_run(run_a).add_run(run_b).add_handoff(h)` raises `AttributeError: 'NoneType' object has no attribute 'add_run'`.
**Expected:** `add_run()` and `add_handoff()` to return `self` for chaining, following the standard builder pattern. Every popular fluent API does this.
**Actual:** Both return `None`. Chaining fails with `AttributeError`.
**Workaround:** Call them on separate lines: `trace.add_run(run_a); trace.add_run(run_b); trace.add_handoff(h)`.
**Status:** Open

---

## F-075: `handoff_chain()` uses explicit `handoffs` list; `root_runs`/`get_children()`/`detect_handoffs()` use `parent_run_id`
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** `MultiAgentTrace` supports two topology representations: an explicit `handoffs` list (manually provided `Handoff` objects) and `parent_run_id` linkage (set on `AgentRun`). The topology methods use different sources without documenting which they use:
- `handoff_chain()` → reads `handoffs` list
- `root_runs` → reads `parent_run_id`
- `get_children(run_id)` → reads `parent_run_id`
- `detect_handoffs()` → reads `parent_run_id` (and mutates `handoffs`! — see F-076)
A user who builds topology via `parent_run_id` (common when wrapping real agents) will get `handoff_chain() == []` even though the trace has a real structure. A user who uses explicit `handoffs` will find `root_runs` returning all runs as roots.
**Expected:** Either a single topology source (explicit handoffs, auto-detected, or merged), or clear documentation that these methods use different sources.
**Actual:** `parent_run_id`-only trace: `handoff_chain() == []`, `root_runs == [root_only]`. Explicit-handoffs-only trace: `handoff_chain() == [a, b, c]`, `root_runs == [all_runs]`.
**Workaround:** Call `apply_detected_handoffs()` after constructing the trace from `parent_run_id` — this bridges the two topology representations and makes `handoff_chain()` consistent with `root_runs`. With F-076 fixed, `apply_detected_handoffs()` is the clean path: it populates the explicit handoffs from `parent_run_id` links and is idempotent.
**Status:** Partially resolved in session-026 — `apply_detected_handoffs()` added as explicit bridge. The dual-representation design remains (F-075 still applies), but there's now a documented escape hatch. Documentation still doesn't explain which methods use which topology source.

---

## F-076: `detect_handoffs()` mutates `trace.handoffs` as a side effect — not read-only
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** `MultiAgentTrace.detect_handoffs()` is named like an inspection method (returns auto-detected handoffs derived from `parent_run_id`), but it also appends those detected handoffs directly to `trace.handoffs`. This has two serious consequences: (1) Calling `detect_handoffs()` twice duplicates all detected handoffs in `trace.handoffs`. (2) Calling `detect_handoffs()` before `handoff_chain()` causes `handoff_chain()` to return the auto-detected chain, surprising users who rely on `handoff_chain()` reflecting only explicitly added handoffs. The name "detect" strongly implies read-only inspection.
**Expected:** `detect_handoffs()` to be pure/read-only: return detected handoffs without mutating `trace.handoffs`. If the intent is to also update the list, the method should be named `apply_detected_handoffs()` or similar.
**Actual:** `trace.detect_handoffs()` called once → `len(trace.handoffs) == 1`. Called again → `len(trace.handoffs) == 2`. After first call, `trace.handoff_chain()` returns results from the auto-detected handoffs.
**Workaround:** Only call `detect_handoffs()` once per trace. Never call it before `handoff_chain()` unless you want the detected handoffs to be included in the chain.
**Status:** Fixed in "Fix detect_handoffs() mutation bug and add builder chaining" (2026-04-06) — `detect_handoffs()` is now read-only. New `apply_detected_handoffs()` method added for explicit mutation, and it's idempotent (calling twice doesn't duplicate).

---

## F-074: `add_run()` and `add_handoff()` return `None` — builder pattern not chainable
**Status:** Fixed in "Fix detect_handoffs() mutation bug and add builder chaining" (2026-04-06) — both methods now return `self`, enabling full builder chaining: `MultiAgentTrace().add_run(r1).add_run(r2).add_handoff(h)`.

---

## F-077: `handoff_chain()` with cycles produces list with repeated nodes — no cycle detection
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** `MultiAgentTrace.handoff_chain()` does not detect cycles. A trace with a→b→c→a produces `['a', 'b', 'c', 'a']` — the start node appears twice. While this avoids infinite loops (the implementation follows the handoffs list in order rather than doing a graph traversal), it silently produces a result that doesn't represent a valid DAG. Users building multi-agent systems with feedback loops (legitimate use cases) will get surprising chain results.
**Expected:** Either raise `ValueError("Cycle detected in handoff chain: a → b → c → a")` for cycles, or document that cycles produce repeated nodes. A `has_cycles()` method would also help.
**Actual:** `handoff_chain()` with a→b→c→a cycle returns `['a', 'b', 'c', 'a']`. No exception, no warning. Two-node cycle (a→b→a) returns `['a', 'b', 'a']`.
**Workaround:** Detect cycles yourself: `len(trace.handoff_chain()) > len(set(trace.handoff_chain()))` indicates a cycle.
**Status:** Open

---

## F-078: `was_triggered` is a method, not a property — always truthy without `()`
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** `FaultInjector.was_triggered` is a method (`was_triggered(target=None) -> bool`), not a property. This means `if fi.was_triggered:` is always `True` — you're testing truthiness of the bound method object, not the result. The fix is `fi.was_triggered()` (with parens). Similar named APIs in checkagent (`ap_mock_tool.was_called`, etc.) are also methods, but `was_triggered` is particularly easy to misuse in assertions like `assert not ap_fault.was_triggered`.
**Expected:** Either make `was_triggered` a `@property` (no-arg call → bool), or name it `has_triggered` to signal it's a method.
**Actual:** `fi.was_triggered` returns `<bound method ...>` which is always truthy. `fi.was_triggered()` returns the correct bool.
**Workaround:** Always call with parentheses: `fi.was_triggered()`. Or use the new `fi.triggered` property (session-029).
**Status:** Partial fix in session-029 — `fi.triggered` @property added as the no-arg bool check. `fi.trigger_count` (int) and `fi.triggered_records` (list) also added. `was_triggered(target)` method still exists for target-filtered checks.

---

## F-079: `attach_faults()` second call silently overwrites the first — not additive
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** Calling `mock_tool.attach_faults(fi2)` after `mock_tool.attach_faults(fi1)` replaces `fi1` entirely. The second injector wins, not merges. There is no `FaultInjector.merge()` method and no warning when overwriting. If a user attaches faults in a fixture and also in a test body, the fixture faults will be silently discarded.
**Expected:** Either raise an error on second attach, merge injectors, or document the overwrite behavior clearly.
**Actual:** The second `attach_faults()` call replaces the first. The original injector's faults are lost.
**Workaround:** Create one FaultInjector with all desired faults before calling `attach_faults()` once.
**Status:** Open

---

## F-080: `MockLLM.with_usage(auto_estimate=True)` uses `len // 4 + 1`, not `len // 4`
**Date:** 2026-04-06
**Severity:** low
**Category:** docs-mismatch
**Description:** The `with_usage()` docstring said token estimation uses `len(text) // 4`. The actual formula is `len(text) // 4 + 1`. This means every estimate is exactly 1 token higher than documented. For short inputs (len < 4), the documented formula gives 0 tokens but the actual gives 1. The +1 likely accounts for a BOS or special token, but this is undocumented.
**Expected:** `MockLLM().with_usage(auto_estimate=True)` + input of 40 chars → `prompt_tokens = 40 // 4 = 10`
**Actual:** `prompt_tokens = 11` (`40 // 4 + 1`)
**Workaround:** Use `len(text) // 4 + 1` when predicting token counts in tests.
**Status:** Fixed in session-029 — docstring now correctly says `len(text) // 4 + 1`.

---

## F-081: `with_usage(prompt_tokens=N, auto_estimate=True)` — no error, undefined behavior
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** Calling `MockLLM().with_usage(prompt_tokens=999, auto_estimate=True)` raised no error and emitted no warning. The fixed `prompt_tokens` value was silently ignored and `auto_estimate` took precedence with unexpected results.
**Expected:** Either: (a) raise `ValueError("Cannot set both prompt_tokens and auto_estimate=True")`, or (b) document clearly that `auto_estimate=True` always overrides fixed values.
**Actual:** Silent undefined behavior — neither value was used as specified.
**Workaround:** Set only one of `prompt_tokens`/`completion_tokens` OR `auto_estimate=True`, never both.
**Status:** Fixed in session-029 — `with_usage()` now raises `ValueError: Cannot set both auto_estimate=True and explicit token counts.`

---

## F-082: `on_llm()` fault builder lacks `intermittent()` and `slow()` — no LLM latency or probabilistic simulation
**Date:** 2026-04-06
**Severity:** medium
**Category:** missing-feature
**Description:** The tool fault builder (`on_tool()`) supports `intermittent(fail_rate=0.3)` and `slow(latency_ms=500)`. The LLM fault builder (`on_llm()`) has none of these. Users cannot simulate: (a) an LLM that fails 20% of the time, (b) a slow LLM response (e.g. to test timeout handling). The LLM fault set is: `content_filter`, `context_overflow`, `partial_response`, `rate_limit(after_n)`, `server_error`. No probabilistic fault, no latency simulation.
**Expected:** `on_llm().intermittent(fail_rate=0.3)` and `on_llm().slow(latency_ms=N)` matching tool fault parity
**Actual:** `AttributeError` — neither method exists on LLM fault builder
**Workaround:** None — cannot test LLM latency or intermittent LLM failures with FaultInjector
**Status:** Fixed in d0dd9265 (session-030) — both `intermittent()` and `slow()` added to `on_llm()` builder. Raises `LLMIntermittentError` and `LLMSlowError` respectively. Async path (`check_llm_async()`) does real sleep for slow faults, consistent with tool fault behavior.

---

## F-083: `dirty-equals` and `deepdiff` declared under `[structured]` optional extra — `assert_output_matches` breaks on minimal install
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** `assert_output_matches` (which uses `dirty_equals`) and related structured assertion internals (which use `deepdiff`) are declared under the `[structured]` optional extra. A user who runs `pip install checkagent` and then calls `assert_output_matches(run, IsStr())` will get an `ImportError` if `dirty_equals` isn't installed. Similarly `deepdiff` is needed for structured diffing. These are core assertion utilities used in almost every test — they should be default dependencies, not optional extras.
**Expected:** `dirty-equals` and `deepdiff` installed automatically with `pip install checkagent`
**Actual:** Only available via `pip install checkagent[structured]`; absent from default deps
**Workaround:** `pip install checkagent[structured]` or install `dirty-equals deepdiff` manually
**Status:** Open

---

## F-084: `LangChainAdapter` only passes `{input_key: query}` — multi-variable chains fail
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** `LangChainAdapter` constructs the invocation dict as `{input_key: query_string}`. If the wrapped chain expects additional template variables (e.g. `{context}`, `{history}`, `{language}`), the invocation will fail with a LangChain `KeyError` about missing variables. The adapter provides no way to inject supplementary variables at run time. This is a real constraint for contextual Q&A chains, RAG chains, and any LCEL pipeline with multiple prompt inputs.
**Expected:** Some way to pass additional variables — perhaps via `AgentInput.metadata`, or via `LangChainAdapter(chain, extra_inputs={...})`, or via an `AgentInput`-field-to-input-key mapping.
**Actual:** `run = await adapter.run("query")` → `KeyError: "Input to ChatPromptTemplate is missing variables {'context'}"` when chain has extra variables.
**Workaround:** Use `prompt.partial(context="...")` to pre-fill extra variables before building the chain. This bakes in a fixed value for the lifetime of the adapter.
**Status:** Open


---

## F-085: `Step.input_text` always `''` for PydanticAI steps — content only in `output_text`
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** When using `PydanticAIAdapter`, all steps in the resulting `AgentRun` have `input_text=''`. The actual content (request prompt or response text) is in `output_text`. This means users cannot use `step.input_text` to inspect what the agent received at each step — they must read `output_text` for all content and use `step.metadata['kind']` to distinguish request vs. response steps.
**Expected:** `input_text` should carry the user query/prompt text for request steps, as it does for GenericAdapter steps.
**Actual:** `input_text=''` for all PydanticAI steps; `output_text` carries all content (including the full prompt in request steps).
**Workaround:** Use `step.output_text` and `step.metadata.get('kind')` to identify step content.
**Status:** Open

---

## F-086: `PydanticAIAdapter` not at top-level `checkagent` namespace
**Date:** 2026-04-06
**Severity:** medium
**Category:** dx-friction
**Description:** `PydanticAIAdapter` cannot be imported from `checkagent` directly. Must use `checkagent.adapters.pydantic_ai`. It IS re-exported from `checkagent.adapters` (one level better than other adapters like `AnthropicAdapter`), but inconsistent with how core types are at the top-level namespace.
**Expected:** `from checkagent import PydanticAIAdapter`
**Actual:** `from checkagent.adapters.pydantic_ai import PydanticAIAdapter`
**Workaround:** Import from the submodule path.
**Status:** Fixed in 0.1.2

---

## F-087: `PydanticAIAdapter` reads deprecated `request_tokens`/`response_tokens` — breaks with PydanticAI 1.77+
**Date:** 2026-04-06
**Severity:** high
**Category:** bug
**Description:** `PydanticAIAdapter._extract_token_usage()` reads `usage_obj.request_tokens` and `usage_obj.response_tokens`. PydanticAI 1.77.0 deprecated these attributes in favor of `input_tokens` and `output_tokens`. Every call to `adapter.run()` emits two `DeprecationWarning`s. Token extraction will silently return `None` when the old attrs are finally removed. Currently tokens are non-zero because the deprecated attrs still exist, but this is a time bomb.
**Expected:** Adapter uses the current `input_tokens`/`output_tokens` attribute names.
**Actual:** `DeprecationWarning: 'request_tokens' is deprecated, use 'input_tokens' instead` on every run.
**Workaround:** None at adapter level. Token counts still work today but will silently break in a future PydanticAI version.
**Status:** Open

---

## F-088: No `checkagent[all]` extra for power users
**Date:** 2026-04-06
**Severity:** low
**Category:** dx-friction
**Description:** Available extras: `dev`, `json-schema`, `otel`, `safety-ner`, `structured`. There is no `[all]` extra that installs everything a power user needs (all optional deps in a single command). Users who want structured assertions, JSON schema validation, OTel tracing, and safety NER must install each extra separately. Framework adapters (langchain, anthropic, crewai, pydantic-ai) are not declared as optional extras at all (F-064), making `[all]` even more useful as a concept.
**Expected:** `pip install checkagent[all]` installs all optional dependencies.
**Actual:** No `[all]` extra exists; users must manually combine extras.
**Workaround:** `pip install "checkagent[json-schema,structured,otel]"` and then add framework packages separately.
**Status:** Open

---

## F-089: `--generate-tests` uses private API (_resolve_callable, _evaluate_output)
**Date:** 2026-04-11
**Severity:** low
**Category:** dx-friction
**Description:** `checkagent scan --generate-tests <file>` generates a pytest file that imports `_resolve_callable` and `_evaluate_output` from `checkagent.cli.scan`. These are private functions (underscore prefix convention) that can change or be removed in any release. Generated test files become fragile — a checkagent upgrade can silently break them.
**Expected:** Generated tests use stable public API only (e.g., import the agent callable directly, use `PromptInjectionDetector` or other public evaluators).
**Actual:** `from checkagent.cli.scan import _resolve_callable, _evaluate_output` in every generated file.
**Workaround:** Manually edit generated tests to avoid private imports. Or don't upgrade checkagent without re-generating the tests.
**Status:** Open

---

## F-090: `ResilienceProfile.to_dict()` omits `best_scenario`
**Date:** 2026-04-11
**Severity:** low
**Category:** bug
**Description:** `ResilienceProfile` has a `best_scenario` attribute, but `to_dict()` does not include it in the serialized output. The returned dict has `worst_scenario` and `weakest_metric` but not `best_scenario`. This makes `to_dict()` an incomplete serialization of the profile — users relying on `to_dict()` for logging/reporting lose the best-scenario information.
**Expected:** `to_dict()` includes all profile attributes: `overall_resilience`, `baseline`, `worst_scenario`, `best_scenario`, `weakest_metric`, `scenarios`.
**Actual:** `"best_scenario"` key is absent from `to_dict()` output.
**Workaround:** Access `profile.best_scenario` directly on the object; don't rely on `to_dict()` for this field.
**Status:** Open

---

## F-091: ci-init path separator bug on Windows (upstream CI regression)
**Date:** 2026-04-11
**Severity:** medium
**Category:** bug
**Description:** Upstream CI is failing on all Windows jobs for the commit "Add ci-init command and fix silent LLM judge failure on bad API key". Test `TestCiInitCommand::test_github_is_default_platform` fails because the output contains a Windows-style path with backslashes, but the test checks for `.github/workflows/checkagent.yml` (forward slash). The success message uses the OS path separator instead of a normalized forward-slash form.
**Expected:** ci-init output message shows `.github/workflows/checkagent.yml` (forward slashes) on all platforms.
**Actual:** On Windows: `\.github\workflows\checkagent.yml` (backslashes) in output message, causing substring check to fail.
**Workaround:** On Linux/Mac (where we test), ci-init works correctly.
**Status:** Open (upstream CI red for this commit on all Windows jobs)

---

## F-092: Version inconsistency FIXED in 0.1.2
**Date:** 2026-04-11
**Severity:** N/A (closed)
**Category:** bug (fixed)
**Description:** In 0.1.1, `checkagent.__version__` was `'0.1.0'` while `importlib.metadata.version('checkagent')` returned `'0.1.1'`. Both now return `'0.1.2'` in the current release.
**Status:** Fixed in 0.1.2

---

## F-093: `analyze-prompt` Rich markup strips `[bracket]` placeholders in recommendations
**Date:** 2026-04-11
**Severity:** medium
**Category:** bug
**Description:** The `checkagent analyze-prompt` command renders recommendations using Rich, which interprets `[bracket text]` as markup tags and strips the content. Recommendations that include template placeholders like `[your domain]` or `[support channel]` appear with those strings missing in the terminal output. For example: "Only help with [your domain]. Decline..." becomes "Only help with . Decline...". The `--json` flag output correctly preserves the bracket text.
**Expected:** Recommendation text with `[your domain]` or `[support channel]` should display as-is in the terminal, with bracket content visible.
**Actual:** Rich parses `[your domain]` as a markup tag, finds no matching tag, and silently drops the content: "Only help with . Decline requests outside this scope."
**Workaround:** Use `--json` flag to see full recommendation text.
**Status:** Open

---

## F-094: Non-existent file path silently analyzed as literal string in `analyze-prompt`
**Date:** 2026-04-11
**Severity:** medium
**Category:** bug
**Description:** When a user passes a path to a non-existent file to `checkagent analyze-prompt`, the command does not report a file-not-found error. Instead, it analyzes the path string itself as prompt text, scores it 0/8, and exits 1 — giving the impression that the command ran correctly but the "prompt" failed all security checks. A user who makes a typo in the file path will not realize their file was never read.
**Expected:** Clear error: "File not found: /path/to/prompt.txt" with non-zero exit code.
**Actual:** Scores 0/8 treating the literal path string as a prompt; no error message.
**Workaround:** Verify file exists before passing path, or check if the score seems implausibly low.
**Status:** Open

---

## F-095: `PromptAnalyzer`, `PromptCheck`, `PromptAnalysisResult` not at top-level `checkagent`
**Date:** 2026-04-11
**Severity:** low
**Category:** dx-friction
**Description:** The programmatic API for `analyze-prompt` — `PromptAnalyzer`, `PromptCheck`, and `PromptAnalysisResult` — is in `checkagent.safety.prompt_analyzer` and re-exported from `checkagent.safety`, but NOT from the top-level `checkagent` namespace. Users who want to use the analyzer in their own code must know to import from `checkagent.safety`, which is not discoverable from `import checkagent; dir(checkagent)`.
**Expected:** `from checkagent import PromptAnalyzer`
**Actual:** `from checkagent.safety import PromptAnalyzer`
**Workaround:** Import from `checkagent.safety`.
**Status:** Open

---

## F-096: `evaluate_output` lives in `checkagent.cli.scan` (private), not public API
**Date:** 2026-04-11
**Severity:** low
**Category:** dx-friction
**Description:** The CI commit "Add --agent-description flag and make evaluate_output public" moved `evaluate_output` somewhere — but it's in `checkagent.cli.scan`, which is a private internal CLI module. It is not importable from `checkagent` or `checkagent.safety`. Users who find it via `from checkagent.cli.scan import evaluate_output` are using a private import path that can change without notice.
**Expected:** `from checkagent import evaluate_output` or `from checkagent.safety import evaluate_output`
**Actual:** `from checkagent.cli.scan import evaluate_output` — CLI-internal private module.
**Workaround:** Import from `checkagent.cli.scan` but accept the fragility.
**Status:** Open

---

## F-097: CI failing ALL platforms — ruff lint errors in `analyze-prompt` commit
**Date:** 2026-04-11
**Severity:** high
**Category:** bug
**Description:** The latest commit "Add checkagent analyze-prompt for static system prompt security analysis" fails ruff lint on all 12 platform/version combinations (Python 3.10-3.13 on ubuntu/macos/windows). Errors: I001 (import block un-sorted, 3 instances) and E501 (line too long: 110 > 99 chars). The previous commit "Add --agent-description flag and make evaluate_output public" was green. This breaks the 9-session green streak that ended in session-033.
**Expected:** Lint passes before merging any commit; CI stays green.
**Actual:** All platforms fail at "Lint with ruff" step; tests never run.
**Workaround:** The installed package (0.1.2) works correctly — ruff is a CI-only dev tool, not a runtime dependency. Tests in the testbed still pass.
**Status:** Open

---

## F-093: `analyze-prompt` Rich markup strips `[bracket]` placeholders in recommendations
**Date:** 2026-04-11
**Status:** FIXED in 0.2.0
**Fixed:** 2026-04-12 — `[your domain]` and similar bracket placeholders now preserved in terminal output.

---

## F-094: Non-existent file path silently analyzed as literal string in `analyze-prompt`
**Date:** 2026-04-11
**Status:** FIXED in 0.2.0
**Fixed:** 2026-04-12 — Now gives explicit "File not found: /path" error with exit code 2.

---

## F-095: `PromptAnalyzer`, `PromptCheck`, `PromptAnalysisResult` not at top-level `checkagent`
**Date:** 2026-04-11
**Status:** FIXED in 0.2.0
**Fixed:** 2026-04-12 — All three now importable from top-level `checkagent`.

---

## F-097: CI failing ALL platforms — ruff lint errors in `analyze-prompt` commit
**Date:** 2026-04-11
**Status:** FIXED
**Fixed:** 2026-04-12 — 0.2.0 release commit passes CI on all platforms. v0.2.0 tag green.

---

## F-098: `--json` flag leaks "Auto-detected:" diagnostic line to stdout
**Date:** 2026-04-12
**Severity:** medium (reduced from high — partially fixed)
**Category:** bug
**Description:** When running `checkagent scan <target> --json` where `<target>` is a `@wrap` adapter (GenericAdapter), the diagnostic "Auto-detected: echo_agent.run() — using this method for each probe" leaks to stdout before the JSON object. Plain async functions do NOT trigger this — their JSON output is clean. The bug only affects targets that are adapter objects (created by `@wrap`, `LangChainAdapter`, etc.) where auto-detection of the callable method is needed.
**Expected:** With `--json`, stdout is always a single valid JSON object regardless of target type. Diagnostics go to stderr.
**Actual:** For plain callables: clean JSON (fixed in 0.2.0). For @wrap adapters: stdout = "Auto-detected: ...\n{...json...}".
**Workaround:** Strip lines not starting with `{` before parsing. Or use plain async functions without `@wrap`.
**Status:** Partially fixed in 0.2.0 — plain functions clean, @wrap adapters still leak

---

## F-099: `GroundednessEvaluator` uncertainty mode: `hedging_signals` always 0
**Date:** 2026-04-12
**Severity:** high
**Category:** bug
**Description:** The `GroundednessEvaluator(mode='uncertainty')` evaluator never detects hedging signals. Common uncertainty phrases like "I might be wrong", "This could be incorrect", "I am not certain", "perhaps", "unable to verify" all return `hedging_signals: 0`. The source code defines `HEDGING_PATTERNS` including `(?i)\b(may|might|could|possibly|perhaps)\b`, but these patterns are not applied in uncertainty mode. Only the disclaimer path ("not financial advice") works. This makes the uncertainty mode unreliable for its stated purpose of detecting overconfident agent responses.
**Expected:** "I might be wrong", "This may vary", "possibly incorrect" etc. trigger hedging signals.
**Actual:** All return `hedging_signals: 0`. Only `not financial advice` passes via disclaimer.
**Workaround:** Use `add_disclaimer_pattern()` to register custom patterns, or use fabrication mode with custom hedging patterns.
**Status:** Fixed in v0.3.0. Uncertainty mode now correctly detects epistemic hedging signals; custom `add_hedging_pattern()` patterns also now applied during evaluation.

---

## F-100: `checkagent wrap` crashes with `AttributeError` when `agents/` directory exists
**Date:** 2026-04-12
**Severity:** medium
**Category:** bug
**Description:** `checkagent wrap agents.echo_agent:echo_agent` crashes with `AttributeError: module 'agents' has no attribute 'Agent'`. The wrap CLI imports `agents` to check `isinstance(obj, agents.Agent)` — a heuristic for detecting OpenAI Agents SDK objects. When a local `agents/` directory exists (as in this testbed), Python imports that directory instead of the SDK, which has no `Agent` class. Same root cause as F-061. Should be wrapped in try/except AttributeError.
**Expected:** wrap CLI gracefully skips OpenAI SDK detection when import fails or `Agent` not found.
**Actual:** Raw traceback crash.
**Workaround:** Run wrap from a directory without an `agents/` subdirectory.
**Status:** Fixed in commit b323ad33 (session-037). `_detect_kind()` now catches `(ImportError, AttributeError)`. Wrap auto-detects `.run()`/`.invoke()`/plain callable correctly even with local `agents/` dir.

---

## F-101: `ConversationSafetyResult.per_turn_findings` is a dict, not a list
**Date:** 2026-04-13
**Severity:** medium
**Category:** dx-friction
**Description:** `ConversationSafetyResult.per_turn_findings` is typed and documented as if it were a list indexed by turn number, but it's actually a `dict[int, list[SafetyFinding]]` containing only turns that HAD findings. Iterating with `enumerate(result.per_turn_findings)` gives dict keys (ints) — causing `TypeError: object of type 'int' has no len()` when users try to `len(findings)` on the yielded key. The correct pattern requires `.items()`.
**Expected:** Either a list `[findings_per_turn_0, findings_per_turn_1, ...]` (indexed by turn), or documentation explicitly stating it's a sparse dict with only turns-with-findings as keys.
**Actual:** `dict[int, list[SafetyFinding]]` — only turns with findings appear as keys. `result.per_turn_findings.keys() == set(result.turns_with_findings)`.
**Workaround:** Use `result.per_turn_findings.items()` for iteration. Use `turn_idx in result.per_turn_findings` for membership checks. Do not use `enumerate()`.
**Status:** Fixed in session-038 upstream commit "Fix Windows CI failure and generate_test_cases API compat". Added `iter_turn_findings()` helper method that returns sorted `(turn_idx, findings)` pairs, with docstring explicitly warning against `enumerate()`. Also added `turns_with_findings`, `total_per_turn_findings`, `total_findings` properties.

---

## F-102: HTTP scan with server down shows score 0.0 without explanation
**Date:** 2026-04-13
**Severity:** low
**Category:** dx-friction
**Description:** When `checkagent scan --url` cannot reach the server, the JSON output shows `"score": 0.0`, `"errors": 35`, `"findings": []`. The errors count is there but not prominently explained. A user reading only `score: 0.0` might think their agent failed all safety tests, when actually the server was unreachable. The non-JSON (rich) output also shows the same scan table with only errors, no explanation.
**Expected:** A clear message in both JSON and rich output indicating the server was unreachable, not just `errors: 35` and `score: 0.0`.
**Actual:** `{"score": 0.0, "errors": 35, "findings": []}` with no contextual error message.
**Workaround:** Check `summary.errors` count; if equal to `summary.total`, assume server is down.
**Status:** Fixed in commit b323ad33 (session-037). JSON output now includes `"warning": "All N probes failed with connection errors. Server at URL may be unreachable."`

---

## F-103: `generate_test_cases` breaking API change — tuple return and parameter rename
**Date:** 2026-04-15
**Severity:** high
**Category:** bug
**Description:** The `generate_test_cases` function in `checkagent.trace_import` changed its return type and parameter names in the 0.2.0 safety screening commit without any deprecation warning or migration guide. Two breaking changes in one commit: (1) `name=` parameter renamed to `dataset_name=` — existing code gets `TypeError: unexpected keyword argument 'name'`. (2) Return type changed from `GoldenDataset` to `tuple[GoldenDataset, TraceScreeningResult]` — existing code gets `AttributeError: 'tuple' object has no attribute 'name'` (or similar) when accessing dataset fields directly. The new `TraceScreeningResult` is useful (safety screening of imported traces), but the silent breaking change is a DX trap. The rename error at least gives a `TypeError`; the tuple change silently breaks attribute access with an unintuitive message.
**Expected:** Either: (a) backward-compatible addition (new `return_screening=True` flag), or (b) deprecation warnings in the old code pointing users to the new API.
**Actual:** Silent behavior change — old code that worked before 0.2.0 breaks at runtime with no helpful migration hints.
**Workaround:** Update all `generate_test_cases` call sites to unpack the tuple: `dataset, screening = generate_test_cases(...)`. Use `dataset_name=` instead of `name=`.
**Status:** Partially fixed in session-038 upstream commit "Fix Windows CI failure and generate_test_cases API compat". The `name=` parameter now emits `DeprecationWarning` instead of raising `TypeError` — backward compatibility restored for that parameter. Return type still `tuple[GoldenDataset, TraceScreeningResult]` (no revert). Migration is now clearer.

---

## F-104: Upstream CI failing on Windows — `ConnectionAbortedError` in HTTP scan test
**Date:** 2026-04-15
**Severity:** high
**Category:** bug
**Description:** CI job "Python 3.13 on windows-latest" fails with `ConnectionAbortedError: [WinError 10053] An established connection was aborted by the software in your host machine` in `tests/cli/test_scan.py::TestMakeHttpAgent::test_server_error_raises`. This is the latest in a pattern of Windows-specific networking/timing failures in checkagent's CI (see also F-043, F-047, F-054, F-091). The commit that introduced this failure was "Add safety screening to import-trace, fix per_turn_findings iteration". All other platforms (Ubuntu/macOS × Python 3.10–3.13) pass. Only Python 3.13 on Windows fails.
**Expected:** CI green on all platforms including Windows Python 3.13.
**Actual:** CI red on latest commit. `test_server_error_raises` passes on all other platform/Python combos but not Windows 3.13.
**Workaround:** None for testbed users. This is an upstream CI issue; the framework code itself is not affected on non-Windows platforms.
**Status:** Fixed in session-038 upstream commit "Fix Windows CI failure and generate_test_cases API compat". All 12 CI jobs pass including Windows Python 3.10/3.11/3.12/3.13.

---

## F-105: `checkagent wrap` generates broken wrapper for class-based agents
**Date:** 2026-04-16
**Severity:** high
**Category:** bug
**Description:** When `checkagent wrap module:ClassName` generates a wrapper for a class-based agent with an `.invoke()` method, the generated code calls `_target.invoke(prompt)` where `_target` is the **imported class** (not an instance). This is an unbound method call — Python raises `TypeError: LCELAgent.invoke() missing 1 required positional argument: 'input_text'` at runtime. The correct code should be `_target().invoke(prompt)` (instantiate first). As a result, when you run `checkagent scan checkagent_target:checkagent_target` on the generated wrapper, ALL probes (35/35) error out with no findings.
**Expected:** Generated wrapper instantiates the class before calling `invoke()`: `result = _target().invoke(prompt)`.
**Actual:** Generated wrapper: `result = _target.invoke(prompt)` — this is equivalent to calling an unbound method, which fails in Python 3 with a clear TypeError.
**Workaround:** Manually edit the generated `checkagent_target.py` to add parentheses: change `_target.invoke(prompt)` to `_target().invoke(prompt)`.
**Status:** Fixed in "Fix wrap class-based agents, add scan --report HTML compliance flag" (2026-04-17) — generated wrapper now correctly uses `_agent = _target()` at module level and calls `_agent.invoke(prompt)`. Verified in session-039.

## F-106: "Auto-detected" wrap diagnostic goes to stdout, breaking --json parsing
**Date:** 2026-04-17
**Severity:** medium
**Category:** bug
**Description:** When scanning a `@wrap`-decorated agent (or any agent where checkagent auto-detects the method to call), the message "Auto-detected: agent.run() — using this method for each probe" is printed to stdout. This appears before the JSON output, making the combined stdout unparseable as JSON when piped to `json.load()`. This is an extension of F-098 (which noted the same for `--repeat N`). Affects both `--json` alone and `--json --report` combined.
**Expected:** Diagnostic messages go to stderr; stdout contains only valid JSON when `--json` is used.
**Actual:** stdout contains: `Auto-detected: ...\n{JSON}` — the JSON parse fails unless the caller strips the first line.
**Workaround:** Split stdout on newlines and skip until the first `{` character.
**Status:** Fixed in v0.3.0. "Auto-detected" diagnostic now goes to stderr; stdout is clean JSON when `--json` is used.

## F-107: `GroundednessEvaluator` and `ConversationSafetyScanner` not at top-level checkagent
**Date:** 2026-04-17
**Severity:** low
**Category:** dx-friction
**Description:** The batch top-level export fix in 0.2.0 added many classes to `checkagent.__init__`, but `GroundednessEvaluator` and `ConversationSafetyScanner` (both added in 0.2.0) were missed. Users must use `from checkagent.safety import GroundednessEvaluator` instead of `from checkagent import GroundednessEvaluator`. This is the 13th instance of the missing-top-level-export pattern.
**Expected:** All public-facing classes importable from `checkagent` directly.
**Actual:** `hasattr(checkagent, 'GroundednessEvaluator')` → False; `hasattr(checkagent, 'ConversationSafetyScanner')` → False.
**Workaround:** Use `from checkagent.safety import GroundednessEvaluator, ConversationSafetyScanner`.
**Status:** Fixed in v0.3.0. Both are now at top-level `checkagent`.

## F-109: `ToolCallBoundaryValidator` old kwargs API removed without deprecation — breaking change
**Date:** 2026-04-19
**Severity:** high
**Category:** bug
**Description:** In v0.3.0, `ToolCallBoundaryValidator` was refactored to require a `ToolBoundary` dataclass parameter. The old constructor kwargs (`allowed_tools=`, `forbidden_tools=`, `allowed_paths=`, `forbidden_argument_patterns=`) were removed with no deprecation warning. Any code written against v0.2.0 that calls `ToolCallBoundaryValidator(allowed_tools=..., forbidden_tools=...)` will immediately raise `TypeError: ToolCallBoundaryValidator.__init__() got an unexpected keyword argument 'allowed_tools'`. This is a breaking API change shipped without a deprecation cycle.
**Expected:** Either: (a) Old kwargs accepted with DeprecationWarning and forwarded to ToolBoundary, or (b) Migration guide in changelog/docs.
**Actual:** `ToolCallBoundaryValidator(allowed_tools={"search"}, forbidden_tools={"delete"})` → `TypeError`.
**Workaround:** Migrate to new API: `ToolCallBoundaryValidator(boundary=ToolBoundary(allowed_tools=..., forbidden_tools=...))`.
**Status:** Open
