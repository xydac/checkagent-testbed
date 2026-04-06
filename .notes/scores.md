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
| checkagent.datasets (GoldenDataset, TestCase, load_dataset, load_cases, parametrize_cases) | 5 | 4 | FIXED in e38593a: datasets module restored — all classes back. F-012/F-013 still open (F-014 closed) | 2026-04-05 |
| AgentInput | 5 | 5 | Clean struct for query+context+conversation_history+metadata; importable from top-level checkagent | 2026-04-05 |
| MockTool.strict_validation=False | 5 | 5 | Skips schema validation entirely; call still recorded; works for both call() and call_sync() | 2026-04-05 |
| MockLLM.reset() / reset_calls() | 4 | 3 | Both clear history and preserve rules — identical observable behavior. Duplication confusing; no docs on difference (F-017) | 2026-04-05 |
| MockTool.reset() / reset_calls() | 4 | 3 | Both clear history and preserve registered tools — identical observable behavior. Same duplication issue (F-017) | 2026-04-05 |
| FaultInjector.slow() sync behavior | 2 | 2 | Raises ToolSlowError in sync check_tool() instead of sleeping — converts latency sim into exception (F-016). Use check_tool_async() for real delay | 2026-04-05 |
| assert_tool_called(call_index=N) multi-step | 5 | 5 | Correctly indexes across step boundaries; OOB gives clean StructuredAssertionError with count; works for all tool names | 2026-04-05 |
| checkagent.datasets (restored) | 5 | 4 | F-014 fixed in e38593a — GoldenDataset, TestCase, parametrize_cases all back; F-012/F-013 still open | 2026-04-05 |
| calculate_run_cost | 5 | 4 | Correct math, unpriced_steps for missing models, pricing_overrides and default_pricing both work; companion types need internal imports (F-018) | 2026-04-05 |
| CostBreakdown | 5 | 5 | per_model breakdown, total_tokens, to_dict() — clean dataclass with all expected fields | 2026-04-05 |
| CostTracker | 5 | 3 | Accumulation, budget enforcement (per_test/suite/ci), summary() all work correctly; no ap_cost_tracker fixture (F-019); BudgetConfig requires internal import (F-018) | 2026-04-05 |
| CostReport / budget_utilization | 5 | 5 | avg_cost_per_run, budget_utilization() fractions, run_count all correct; to_dict() has expected keys | 2026-04-05 |
| BudgetExceededError | 5 | 5 | Clear error message with limit value and which limit triggered; raised correctly for per_test/suite/ci | 2026-04-05 |
| BUILTIN_PRICING | 5 | 3 | Contains major models (GPT-4o, Claude, Gemini); correct rates; not importable from top-level checkagent (F-018) | 2026-04-05 |
| step_efficiency | 5 | 3 | Correct ratio capping, metadata, threshold; not at top-level (F-020) | 2026-04-05 |
| task_completion | 5 | 4 | case-insensitive substring, exact match, error check, partial score all correct; not at top-level (F-020) | 2026-04-05 |
| tool_correctness | 5 | 4 | P/R/F1 correct, FP/FN metadata, both-empty → 1.0; not at top-level (F-020) | 2026-04-05 |
| trajectory_match | 5 | 4 | strict/ordered/unordered all work; invalid mode raises ValueError; not at top-level (F-020) | 2026-04-05 |
| Evaluator (ABC) + EvaluatorRegistry | 5 | 3 | Subclassing works, register/unregister/score_all/discover_entry_points all correct; not at top-level (F-020) | 2026-04-05 |
| aggregate_scores | 5 | 4 | Grouping, mean, pass_rate, min/max all correct; None pass_rate when no flags; not at top-level (F-020) | 2026-04-05 |
| compute_step_stats | 5 | 4 | mean, p50, p95, min, max correct; empty list returns zeros; not at top-level (F-020) | 2026-04-05 |
| detect_regressions | 5 | 4 | Detects drops, ignores improvements, skips missing baseline metrics; threshold works; not at top-level (F-020) | 2026-04-05 |
| RunSummary save/load | 5 | 4 | Round-trip with aggregates, step_stats, total_cost all preserved; not at top-level (F-020) | 2026-04-05 |
| ap_safety fixture | 5 | 4 | Returns all 5 evaluators (injection/pii/system_prompt/tool_boundary/refusal); fixture works; evaluator classes not at top-level (F-021) | 2026-04-05 |
| PromptInjectionDetector | 5 | 4 | Detects 6 built-in patterns; add_pattern() works; Severity enum string values not comparable with int (F-023) | 2026-04-05 |
| PIILeakageScanner | 5 | 5 | Email, SSN, CC, phone detection; disabled set works; add_pattern() works; deduplicates findings | 2026-04-05 |
| SystemPromptLeakDetector | 5 | 5 | Pattern detection + verbatim fragment leak; set_system_prompt with min_fragment_len; clean API | 2026-04-05 |
| RefusalComplianceChecker | 5 | 5 | Both modes (expect/forbid refusal) work correctly; add_pattern(); result.details populated | 2026-04-05 |
| ToolCallBoundaryValidator | 4 | 3 | Allowed/forbidden tools, path boundaries, arg patterns all work correctly; evaluate(text) silent no-op is misleading (F-022); not at top-level (F-021) | 2026-04-05 |
| Severity enum | 3 | 2 | String values instead of ordered integers — can't compare with >= or <; must use set membership or SEVERITY_ORDER dict (F-023) | 2026-04-05 |
| attack probe library (Probe, ProbeSet) | 5 | 4 | 35 probes (25 direct + 10 indirect), clean composable API (filter/+/iter), parametrize-friendly; not at top-level (F-026) | 2026-04-05 |
| probes.injection.direct | 5 | 5 | 25 well-categorized probes; Severity.CRITICAL for high-risk attacks; names are pytest-friendly param IDs | 2026-04-05 |
| probes.injection.indirect | 5 | 5 | 10 indirect injection probes (tool results, RAG, email, calendar, DB); all tagged "indirect" | 2026-04-05 |
| ProbeSet.filter() | 5 | 5 | Filter by tags, category, severity; returns new ProbeSet; combined filtering works | 2026-04-05 |
| severity_meets_threshold | 5 | 5 | Correct ordering (LOW<MED<HIGH<CRITICAL); works as F-023 workaround; importable from checkagent.safety | 2026-04-05 |
| OWASP_MAPPING | 5 | 4 | All SafetyCategory values covered; string values (OWASP IDs); importable from checkagent.safety | 2026-04-05 |
| ToolCallBoundaryValidator path checks | 2 | 3 | Basic pass/fail works; but naive string prefix allows /dataextra bypass (F-024) and no path normalization allows ../traversal (F-025) — security bugs | 2026-04-05 |
| end-to-end eval pipeline (datasets→metrics→aggregate→RunSummary) | 5 | 3 | Full pipeline works: TestCase → task_completion → aggregate_scores → RunSummary.save/load → detect_regressions; API requires tuples not Score objects (surprising) | 2026-04-05 |
| TestCase.input field | 3 | 2 | Input is `str` not `dict` — surprising for agents that expect structured input. Users who pass dicts get ValidationError with confusing message | 2026-04-05 |
| jailbreak probe library (probes_jailbreak) | 5 | 4 | 15 probes (7 roleplay + 8 encoding); CRITICAL to LOW severity; clean tag/category metadata; case-sensitive severity string filter gotcha | 2026-04-05 |
| PII probe library (probes_pii) | 5 | 4 | 10 extraction probes; all HIGH severity; diverse tags (direct/social_engineering/harvest etc.); importable via safety module | 2026-04-05 |
| scope/boundary probe library (probes_scope) | 5 | 4 | 8 boundary probes covering financial/travel/medical/political actions; MEDIUM to CRITICAL severity | 2026-04-05 |
| ProbeSet.filter() severity case-sensitivity | 3 | 2 | filter(severity='critical') works; filter(severity='CRITICAL') returns 0 silently — case-sensitive string filter is a DX trap | 2026-04-05 |
| ProbeSet.filter() tags OR logic | 5 | 3 | filter(tags={'a','b'}) is OR (any match) not AND (all required) — not documented, surprising to users expecting AND logic | 2026-04-05 |
| task_completion expected_output_contains list | 5 | 4 | AND logic: all items must appear; partial scores; threshold applies to fraction; check_no_error=True adds implicit check | 2026-04-05 |
| AgentRun / Step field names | 2 | 1 | Silent field drop: AgentRun(output=...) discards value (correct: final_output); Step(input=...) discards (correct: input_text). No ValidationError (F-027) | 2026-04-05 |
| checkagent.ci (quality gates module) | 5 | 3 | Core gate logic solid (min/max/range/warn/block); QualityGateEntry not in ci.__all__ (F-030); all CI types absent from top-level checkagent (F-028) | 2026-04-05 |
| evaluate_gate / evaluate_gates | 5 | 4 | Correct logic; missing metric → SKIPPED; on_fail=ignore → SKIPPED; no min/max → always PASSED (silent trap); invalid on_fail raises ValidationError | 2026-04-05 |
| QualityGateReport | 5 | 5 | .passed, .blocked_gates, .warned_gates, .passed_gates, .has_warnings all work cleanly | 2026-04-05 |
| QualityGateEntry | 4 | 2 | Works correctly; not in ci.__all__ (F-030); no min+max → silently passes anything | 2026-04-05 |
| generate_pr_comment | 5 | 4 | Generates GitHub Markdown tables for test summary, quality gates, cost; footer always present; accepts all-None; RunSummary name collision (F-029) | 2026-04-05 |
| checkagent.ci.RunSummary | 4 | 2 | Test run counts (total/passed/failed/etc.) + pass_rate; name collides with eval.aggregate.RunSummary (F-029) | 2026-04-05 |
| scores_to_dict | 5 | 5 | Clean list[Score] → dict[str, float] conversion; empty list returns {}; integrates with evaluate_gates | 2026-04-05 |
| GateVerdict enum | 5 | 5 | 4 values (passed/warned/blocked/skipped); string values; used cleanly in report properties | 2026-04-05 |
| ProbeSet chained filter (AND logic) | 5 | 4 | .filter().filter() achieves AND — works correctly; not documented; OR is the single-call behavior | 2026-04-05 |
| ProbeSet parametrize compatibility | 5 | 5 | iter() gives Probe objects; str(probe) returns probe.name (pytest-friendly IDs); len() works; can pass list(ProbeSet) directly to parametrize | 2026-04-05 |
| injection.direct.all() vs all_probes | 3 | 2 | .all() returns list; .all_probes is ProbeSet; inconsistent — mixing them breaks + composition (F-032) | 2026-04-05 |
| task_completion expected_output_equals | 4 | 3 | Exact match works; case-sensitive (expected); None treated as '' — None == '' → True (F-031); can combine with expected_output_contains | 2026-04-05 |
| checkagent run --layer judge | 5 | 4 | Correctly deselects all non-judge tests; needs @pytest.mark.agent_test(layer='judge') to select tests | 2026-04-05 |
| checkagent run default filter | 3 | 2 | Runs only -m agent_test tests by default — silent deselection of 328/549 tests (F-034) | 2026-04-05 |
| ProbeSet + operator | 5 | 5 | Order preserved (left then right); cross-category works; duplicates allowed; empty ProbeSet is identity | 2026-04-05 |
| detect_regressions | 5 | 4 | Correct delta/threshold logic; improvement not flagged; missing-baseline skipped; not at top-level | 2026-04-05 |
| RunSummary.save() / load() | 3 | 2 | save() serializes regressions to JSON; load() drops them silently (F-035). Aggregates round-trip correctly | 2026-04-05 |
| generate_pr_comment (eval integration) | 1 | 1 | No eval_summary param, no regressions param — CI and eval modules completely disconnected (F-033) | 2026-04-05 |
| judge layer marker | 4 | 3 | @pytest.mark.agent_test(layer='judge') filters correctly; checkagent run --layer judge works; but judge module is empty — no judge fixtures, no JudgeLLM, nothing | 2026-04-05 |
| CI quality gates pytest integration | 1 | 1 | No pytest_sessionfinish/terminal_summary hooks; no ap_quality_gates fixture; gates defined in config are not auto-evaluated; users must wire everything manually (F-034) | 2026-04-05 |
| QualityGateEntry missing metric typo | 2 | 2 | Misconfigured gate metric name → SKIPPED (not an error); silently passes — no validation that gate names match computed score names | 2026-04-05 |
| checkagent package stability (ed0b21a) | 1 | 1 | CRITICAL REGRESSION: datasets, eval.metrics, eval.aggregate, eval.evaluator, ci, safety, cost tracking all stripped (F-036). Only sessions 004-008 survive | 2026-04-05 |
| checkagent package stability (6a8eaf4) | 4 | 4 | F-036 FIXED — all modules restored. 668 tests passing. Second regression of this type; stability improving but pattern is concerning | 2026-04-05 |
| checkagent.replay (Cassette data model) | 4 | 3 | Core cassette API solid: finalize/integrity/serialize/save/load all work; redact_dict correctly handles nested dicts; schema version warning works; but: not at top-level (F-041), migrate-cassettes CLI missing (F-039), checkagent_version never set (F-040) | 2026-04-05 |
| Cassette.finalize() | 5 | 4 | Assigns sequential IDs, sequence numbers, content hash correctly; deterministic ID from request body | 2026-04-05 |
| Cassette.verify_integrity() | 5 | 5 | Detects tampering reliably; empty-hash cassette passes without check | 2026-04-05 |
| Cassette save/load round-trip | 5 | 5 | Full fidelity: all fields preserved; parent dirs auto-created | 2026-04-05 |
| Cassette schema version warning | 4 | 2 | Warning fires correctly on old schema; message references non-existent migrate-cassettes CLI (F-039) | 2026-04-05 |
| redact_dict | 5 | 5 | Recursive; handles nested dicts and lists; doesn't mutate original; configurable key set | 2026-04-05 |
| Cassette.cassette_path() | 4 | 3 | Correct :: → / mapping and space → _ substitution; square brackets not sanitized (potential Windows issue); path is content-addressed | 2026-04-05 |
| @pytest.mark.cassette (with replay module) | 3 | 2 | Data model exists now; marker still has no record/replay behavior; F-039/F-040/F-041 all open | 2026-04-05 |
| upstream CI (3 consecutive failures) | 1 | 1 | CI red for all 3 latest runs — F-008 (jsonschema undeclared dep) breaks checkagent's own test suite | 2026-04-05 |
| FaultInjector.check_tool_async() | 5 | 4 | Real latency simulation: 80ms slow fault → 80ms actual sleep; no exception unlike sync; records in was_triggered/trigger_count; other fault types still raise | 2026-04-05 |
| FaultInjector async LLM faults | 1 | 1 | check_llm_async() does not exist — no async LLM fault simulation (F-037). Only check_llm() sync available | 2026-04-05 |
| FaultInjector.intermittent() fail_rate | 5 | 4 | fail_rate=1.0 always raises; fail_rate=0.0 never raises; seed param for deterministic results; async works same as sync | 2026-04-05 |
| AgentRun.input strict typing | 3 | 2 | Requires AgentInput (or dict coercion); plain string raises ValidationError with unhelpful message — doesn't hint at AgentInput(query=...) fix (F-038) | 2026-04-05 |
| CassetteRecorder | 5 | 4 | record_llm_call/record_tool_call work correctly; tokens/duration/status/redact all captured; finalize() → Cassette with correct metadata; not at top-level (F-041) | 2026-04-05 |
| ReplayEngine (SEQUENCE) | 4 | 3 | Core playback works; remaining/all_used/reset all correct; but silently ignores kind — tool request matches llm interaction (F-044) | 2026-04-05 |
| ReplayEngine (EXACT) | 5 | 4 | Body matching correct; raises CassetteMismatchError with strategy name in message; default strategy | 2026-04-05 |
| ReplayEngine (SUBSET) | 5 | 4 | Recorded body must be subset of request body — semantics are correct if you read docs carefully; error on subset mismatch | 2026-04-05 |
| ReplayEngine block_unmatched | 1 | 1 | block_unmatched=False has no effect — always raises CassetteMismatchError (F-042). Passthrough mode not implemented | 2026-04-05 |
| CassetteMismatchError | 5 | 5 | Clean exception hierarchy; message includes kind and strategy; raised on exhausted cassette | 2026-04-05 |
| MatchStrategy enum | 5 | 4 | 3 values (EXACT/SEQUENCE/SUBSET); string values; default is EXACT (sensible) | 2026-04-05 |
| TimedCall | 5 | 4 | Context manager; accurate ms timing; reusable; only one field (duration_ms); minimal but functional | 2026-04-05 |
| upstream CI (c03b11f) | 1 | 1 | Still red — new failure: Windows encoding error in demo-generated test (byte 0x97 em dash, F-043). Previous root cause F-008 may also still apply | 2026-04-05 |
| @pytest.mark.cassette (session-017) | 2 | 2 | CassetteRecorder+ReplayEngine exist now but still no pytest fixture — marker still no-op; no ap_cassette, no auto record/replay | 2026-04-05 |
| checkagent migrate-cassettes CLI | 2 | 2 | Command now exists (F-039 partially resolved) but v0→v1 migration not implemented (F-045); always returns exit code 0 even on failure | 2026-04-06 |
| migrate-cassettes v0 support | 1 | 1 | "No migration registered from v0" — the only migration needed is unimplemented (F-045) | 2026-04-06 |
| Cassette.save()/load() path handling | 3 | 2 | Both require pathlib.Path; str raises AttributeError with confusing 'parent'/'read_text' message; no Path coercion (F-046) | 2026-04-06 |
| upstream CI (session-018) | 1 | 1 | Still red — new failure: TimedCall.duration_ms == 0.0 on Windows for short sleep (F-047). Third consecutive CI failure, third different root cause | 2026-04-06 |
| upstream CI (session-019) | 4 | 4 | FIXED — latest run passing. F-047 and F-043 both resolved upstream. Stable for the first time in 3 sessions | 2026-04-06 |
| checkagent.judge module (overall) | 4 | 3 | Core judge logic solid: RubricJudge, compute_verdict, 3 scale types, weighted criteria, statistical verdicts; not at top-level (F-048); no ap_judge fixture (F-049) | 2026-04-06 |
| RubricJudge.evaluate() | 4 | 3 | Weighted scoring correct; markdown fence stripping works; bad JSON propagates raw JSONDecodeError (F-050); wrong criterion names silent 0.0 (F-051) | 2026-04-06 |
| compute_verdict | 5 | 5 | PASS/FAIL/INCONCLUSIVE logic correct; confidence field correct; all trials stored; error propagates; num_trials=0 raises ValueError | 2026-04-06 |
| Rubric / Criterion | 5 | 5 | Validation correct (empty criteria raises); get_criterion works; all 3 scale types (numeric/binary/categorical) normalize correctly | 2026-04-06 |
| JudgeScore / JudgeVerdict | 5 | 5 | score_for() lookup/miss; passed property; num_trials; reasoning summary; Verdict str enum values | 2026-04-06 |
| judge pytest integration | 1 | 1 | No ap_judge fixture; MockLLM incompatible with RubricJudge(llm=) signature; users must write all glue code (F-049) | 2026-04-06 |
