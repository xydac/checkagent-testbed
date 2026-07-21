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
| ap_mock_llm | 5 | 5 | F-001 FIXED: on_input(contains/pattern/exact).respond() and .stream() now work; literal() works in add_rule() and on_input().respond() (F-122 fixed) | 2026-05-15 |
| ap_mock_tool | 4 | 4 | Schema validation + assertions nice | 2026-04-05 |
| ap_fault fluent API | 5 | 4 | Complete fluent builder (all fault types), inspection API, async variant; naming inconsistency on returns_empty/returns_malformed (F-007) | 2026-04-05 |
| ap_fault mock integration | 5 | 5 | F-079 FIXED (session-072): second attach with different injector raises ValueError with helpful message; same injector is idempotent; was_triggered DX trap (F-078) also fixed in prior session | 2026-07-05 |
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
| ToolCallBoundaryValidator | 4 | 4 | F-022 FIXED: evaluate(text) raises NotImplementedError. evaluate_run() works correctly. ToolBoundary now at top-level (F-112 commit). F-111 partial: forbidden_argument_patterns still confusingly named but TypeError message is now clear | 2026-04-22 |
| Severity enum | 3 | 2 | String values instead of ordered integers — can't compare with >= or <; must use set membership or SEVERITY_ORDER dict (F-023) | 2026-04-05 |
| attack probe library (Probe, ProbeSet) | 5 | 4 | 35 probes (25 direct + 10 indirect), clean composable API (filter/+/iter), parametrize-friendly; not at top-level (F-026) | 2026-04-05 |
| probes.injection.direct | 5 | 5 | 25 well-categorized probes; Severity.CRITICAL for high-risk attacks; names are pytest-friendly param IDs | 2026-04-05 |
| probes.injection.indirect | 5 | 5 | 10 indirect injection probes (tool results, RAG, email, calendar, DB); all tagged "indirect" | 2026-04-05 |
| ProbeSet.filter() | 5 | 5 | Filter by tags, category, severity; returns new ProbeSet; combined filtering works | 2026-04-05 |
| severity_meets_threshold | 5 | 5 | Correct ordering (LOW<MED<HIGH<CRITICAL); works as F-023 workaround; importable from checkagent.safety | 2026-04-05 |
| OWASP_MAPPING | 5 | 4 | All SafetyCategory values covered; string values (OWASP IDs); importable from checkagent.safety | 2026-04-05 |
| ToolCallBoundaryValidator path checks | 5 | 4 | F-024/F-025/F-109 all FIXED. Path security solid, deprecation shim added for kwargs migration | 2026-04-20 |
| end-to-end eval pipeline (datasets→metrics→aggregate→RunSummary) | 5 | 3 | Full pipeline works: TestCase → task_completion → aggregate_scores → RunSummary.save/load → detect_regressions; API requires tuples not Score objects (surprising) | 2026-04-05 |
| TestCase.input field | 3 | 2 | Input is `str` not `dict` — surprising for agents that expect structured input. Users who pass dicts get ValidationError with confusing message | 2026-04-05 |
| jailbreak probe library (probes_jailbreak) | 5 | 4 | 15 probes (7 roleplay + 8 encoding); CRITICAL to LOW severity; clean tag/category metadata; case-sensitive severity string filter gotcha | 2026-04-05 |
| PII probe library (probes_pii) | 5 | 4 | 10 extraction probes; all HIGH severity; diverse tags (direct/social_engineering/harvest etc.); importable via safety module | 2026-04-05 |
| scope/boundary probe library (probes_scope) | 5 | 4 | 8 boundary probes covering financial/travel/medical/political actions; MEDIUM to CRITICAL severity | 2026-04-05 |
| ProbeSet.filter() severity case-sensitivity | 5 | 5 | FIXED in v0.3.0: filter(severity='CRITICAL') and filter(severity='critical') now return same count. Tags filter still case-sensitive (DX trap) | 2026-04-21 |
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
| FaultInjector async LLM faults | 5 | 5 | F-037 FIXED (session-030): check_llm_async() added alongside F-082 fix; intermittent and slow both work via async path; real sleep for slow, raises LLMIntermittentError for intermittent | 2026-04-06 |
| FaultInjector.intermittent() fail_rate | 5 | 4 | fail_rate=1.0 always raises; fail_rate=0.0 never raises; seed param for deterministic results; async works same as sync | 2026-04-05 |
| AgentRun.input strict typing | 3 | 2 | Requires AgentInput (or dict coercion); plain string raises ValidationError with unhelpful message — doesn't hint at AgentInput(query=...) fix (F-038) | 2026-04-05 |
| CassetteRecorder | 5 | 4 | record_llm_call/record_tool_call work correctly; tokens/duration/status/redact all captured; finalize() → Cassette with correct metadata; not at top-level (F-041) | 2026-04-05 |
| ReplayEngine (SEQUENCE) | 4 | 3 | Core playback works; remaining/all_used/reset all correct; but silently ignores kind — tool request matches llm interaction (F-044) | 2026-04-05 |
| ReplayEngine (EXACT) | 5 | 4 | Body matching correct; raises CassetteMismatchError with strategy name in message; default strategy | 2026-04-05 |
| ReplayEngine (SUBSET) | 5 | 4 | Recorded body must be subset of request body — semantics are correct if you read docs carefully; error on subset mismatch | 2026-04-05 |
| ReplayEngine block_unmatched | 5 | 4 | F-042 FIXED (session-069): block_unmatched=False now returns None on mismatch; True (default) still raises CassetteMismatchError | 2026-06-27 |
| CassetteMismatchError | 5 | 5 | Clean exception hierarchy; message includes kind and strategy; raised on exhausted cassette | 2026-04-05 |
| MatchStrategy enum | 5 | 4 | 3 values (EXACT/SEQUENCE/SUBSET); string values; default is EXACT (sensible) | 2026-04-05 |
| TimedCall | 5 | 4 | Context manager; accurate ms timing; reusable; only one field (duration_ms); minimal but functional | 2026-04-05 |
| upstream CI (c03b11f) | 1 | 1 | Still red — new failure: Windows encoding error in demo-generated test (byte 0x97 em dash, F-043). Previous root cause F-008 may also still apply | 2026-04-05 |
| @pytest.mark.cassette (session-017) | 2 | 2 | CassetteRecorder+ReplayEngine exist now but still no pytest fixture — marker still no-op; no ap_cassette, no auto record/replay | 2026-04-05 |
| checkagent migrate-cassettes CLI | 2 | 2 | Command now exists (F-039 partially resolved) but v0→v1 migration not implemented (F-045); always returns exit code 0 even on failure | 2026-04-06 |
| migrate-cassettes v0 support | 1 | 1 | "No migration registered from v0" — the only migration needed is unimplemented (F-045) | 2026-04-06 |
| Cassette.save()/load() path handling | 5 | 5 | F-046 FIXED (session-069): both save() and load() now accept str or pathlib.Path | 2026-06-27 |
| upstream CI (session-018) | 1 | 1 | Still red — new failure: TimedCall.duration_ms == 0.0 on Windows for short sleep (F-047). Third consecutive CI failure, third different root cause | 2026-04-06 |
| upstream CI (session-019) | 4 | 4 | FIXED — latest run passing. F-047 and F-043 both resolved upstream. Stable for the first time in 3 sessions | 2026-04-06 |
| checkagent.judge module (overall) | 4 | 3 | Core judge logic solid: RubricJudge, compute_verdict, 3 scale types, weighted criteria, statistical verdicts; not at top-level (F-048); no ap_judge fixture (F-049) | 2026-04-06 |
| RubricJudge.evaluate() | 4 | 3 | Weighted scoring correct; markdown fence stripping works; bad JSON propagates raw JSONDecodeError (F-050); wrong criterion names silent 0.0 (F-051) | 2026-04-06 |
| compute_verdict | 5 | 5 | PASS/FAIL/INCONCLUSIVE logic correct; confidence field correct; all trials stored; error propagates; num_trials=0 raises ValueError | 2026-04-06 |
| Rubric / Criterion | 5 | 5 | Validation correct (empty criteria raises); get_criterion works; all 3 scale types (numeric/binary/categorical) normalize correctly | 2026-04-06 |
| JudgeScore / JudgeVerdict | 5 | 5 | score_for() lookup/miss; passed property; num_trials; reasoning summary; Verdict str enum values | 2026-04-06 |
| judge pytest integration | 1 | 1 | No ap_judge fixture; MockLLM incompatible with RubricJudge(llm=) signature; users must write all glue code (F-049) | 2026-04-06 |
| upstream CI (session-020) | 5 | 5 | Still green — "mark multi-judge consensus as complete" passing. Stable for second consecutive session | 2026-04-06 |
| ap_judge fixture | 4 | 4 | F-049 partially fixed: factory fixture now exists, accepts (rubric, llm, model_name); reduces boilerplate; MockLLM still can't plug in directly | 2026-04-06 |
| judge pytest integration (session-020) | 2 | 2 | ap_judge fixture added (improvement) but no MockLLM bridge — still requires custom async callable + rubric-format JSON in every test (F-049 partial) | 2026-04-06 |
| multi_judge_evaluate | 3 | 3 | Core consensus logic correct: majority vote, PASS/FAIL/INCONCLUSIVE, concurrent=True/False, < 2 judges raises; judge_verdicts key collision when rubric names match (F-052, canonical use case!) | 2026-04-06 |
| ConsensusVerdict | 4 | 3 | Fields: verdict, judge_verdicts, agreement_rate, has_disagreement, reasoning — all correct; judge_verdicts loses entries on key collision (F-052); not at top-level checkagent (F-053) | 2026-04-06 |
| multi_judge_evaluate tie-breaking | 3 | 2 | 1 PASS + 1 FAIL → PASS (undocumented PASS bias for ties); agreement_rate=0.5; has_disagreement=True | 2026-04-06 |
| LangChainAdapter (basic run/error/stream) | 4 | 3 | Core functionality solid; dict final_output inconsistency (F-056); string input coercion works; stream events correct; langchain-core undeclared dep (F-055) | 2026-04-06 |
| LangChainAdapter not at top-level | N/A | 1 | Seventh+ instance of missing top-level export pattern (F-057) | 2026-04-06 |
| OpenAIAgentsAdapter | 1 | 1 | Imports from 'agents' package which conflicts with common project dir names (F-061); lazy import raises ImportError at run() not at instantiation | 2026-04-06 |
| upstream CI (session-021) | 1 | 1 | Failing again — fourth Windows timing regression. LangChain adapter test_error_handling duration_ms==0.0 on Windows 3.10/3.11/3.12 (F-054) | 2026-04-06 |
| Custom Judge subclassing | 3 | 2 | Judge ABC works; CriterionScore field names non-intuitive (F-059); no docs on custom judge workflow; JudgeScore has no .passed (F-058) | 2026-04-06 |
| JudgeScore.passed | 1 | 1 | Doesn't exist — must call compute_verdict() for single-trial pass/fail (F-058) | 2026-04-06 |
| Criterion default scale for BINARY | 2 | 2 | Defaults to [1,2,3,4,5] regardless of scale_type; BINARY should default to 2-item scale (F-060) | 2026-04-06 |
| upstream CI (session-022) | 5 | 5 | Green again — "mark all framework adapters as complete" passes all platforms including Windows. F-054 fixed (perf_counter). Stable for third consecutive session | 2026-04-06 |
| AnthropicAdapter (basic run/error) | 5 | 4 | F-062 FIXED (session-076): final_output now extracts string correctly. String input coercion, error capture, perf_counter timing all solid. anthropic undeclared dep (F-064) still open | 2026-07-17 |
| AnthropicAdapter.final_output | 5 | 5 | F-062 FIXED (session-076): final_output is now the extracted text string, consistent with step.output_text. No longer returns raw message object. | 2026-07-17 |
| CrewAIAdapter (basic run/error) | 4 | 3 | String input coercion works; final_output=result.raw (string — correct!); error captured; crewai undeclared dep (F-064) | 2026-04-06 |
| PydanticAIAdapter (basic run/error) | 4 | 3 | String input coercion works; final_output=result.data (correct); error captured; pydantic-ai undeclared dep (F-064) | 2026-04-06 |
| New adapters top-level exports | N/A | 1 | AnthropicAdapter, CrewAIAdapter, PydanticAIAdapter all absent from top-level checkagent (F-063). Ninth+ instance of pattern | 2026-04-06 |
| Adapter optional extras | 1 | 1 | anthropic/crewai/pydantic-ai not declared as optional extras — users can't pip install checkagent[anthropic] (F-064) | 2026-04-06 |
| checkagent.ci.junit_xml (JUnit XML) | 5 | 4 | render_junit_xml, from_run_summary, from_quality_gate_report all work; valid XML output; time_s aggregates correctly; gate verdicts map to failures/skipped correctly; accessible from checkagent.ci (good); not at top-level checkagent (F-065) | 2026-04-06 |
| JUnit XML from_run_summary | 5 | 4 | Synthetic mode creates generic test cases; test_details mode creates named cases with failure/skip support; integrates with RunSummary counts | 2026-04-06 |
| JUnit XML from_quality_gate_report | 5 | 5 | Blocked → failure, Warned → pass with property, Skipped → skipped; properties attached (actual/threshold/direction); clean mapping | 2026-04-06 |
| upstream CI (session-023) | 5 | 5 | Green for last 2 runs ("mark production trace import as complete", "mark all framework adapters"). Stable | 2026-04-06 |
| checkagent import-trace CLI | 4 | 4 | Solid: auto-detect JSON/JSONL/OTel, --filter-status, --limit, --tag, --no-pii-scrub, --source; friendly missing-file error; crashes with raw traceback on PII ID collision (F-066) | 2026-04-06 |
| JsonFileImporter | 5 | 5 | Handles flat, native (steps), span, and JSONL formats; filter by status; limit; F-067 FIXED (session-077): now at top-level | 2026-07-18 |
| OtelJsonImporter | 5 | 5 | Parses OTLP JSON correctly; groups by traceId; root span detection; tool spans from child names; error from status.code; F-067 FIXED (session-077): now at top-level | 2026-07-18 |
| PiiScrubber | 5 | 5 | Deterministic replacements; 5 built-in patterns (email/phone/SSN/CC/IP); extra_patterns; scrub_value for nested dicts/lists; reset() works correctly | 2026-04-06 |
| generate_test_cases | 3 | 1 | F-103: Breaking API change — returns tuple not GoldenDataset, `name=` renamed to `dataset_name=`, no deprecation. Existing code breaks silently. Safety screening useful but the migration story is terrible. | 2026-04-15 |
| TraceScreeningResult | 5 | 4 | New in 0.2.0 (safety screening commit): total/clean/flagged counts, findings_by_trace with SafetyFinding objects. Catches injection in traced outputs. Not at top-level. | 2026-04-15 |
| trace_import top-level exports | 5 | 5 | F-067 FIXED (session-077): TraceImporter, JsonFileImporter, OtelJsonImporter, PiiScrubber, generate_test_cases all now at top-level checkagent | 2026-07-18 |
| checkagent.multiagent (overall) | 3 | 3 | New multi-agent trace + blame attribution module. Core logic works for most strategies; LEAF_ERRORS bug (F-069) makes the most useful strategy unreliable; agent_id silent failure (F-070); not at top-level (F-068) | 2026-04-06 |
| MultiAgentTrace construction | 5 | 4 | Clean Pydantic model; runs + handoffs + trace_id; defaults to empty lists; no handoff agent_id validation (F-072) | 2026-04-06 |
| Handoff model | 5 | 4 | All HandoffType values work (delegation/relay/broadcast); optional metadata (latency_ms, input_summary, from/to run_id); HandoffType not in multiagent namespace (F-071) | 2026-04-06 |
| assign_blame FIRST_ERROR | 5 | 4 | Correctly blames first errored run in list; confidence=0.8; reason includes error message; returns None when no errors | 2026-04-06 |
| assign_blame LAST_AGENT | 5 | 4 | Correctly blames last errored run in list; confidence=0.6; works symmetrically with FIRST_ERROR | 2026-04-06 |
| assign_blame MOST_STEPS | 4 | 3 | Correct when steps differ; returns first alphabetically when tied at 0 steps; reports step count in reason | 2026-04-06 |
| assign_blame HIGHEST_COST | 4 | 3 | Correct when total_prompt_tokens+total_completion_tokens set; returns None without token data (expected but undocumented); uses new split token fields | 2026-04-06 |
| assign_blame LEAF_ERRORS | 1 | 1 | Inverted logic: blames agents WITH children instead of leaf agents (F-069). Fundamental bug in the strategy most useful for root cause attribution | 2026-04-06 |
| assign_blame_ensemble | 4 | 4 | Runs all (or custom) strategies; skips None results; returns list of BlameResult; custom strategies list works | 2026-04-06 |
| top_blamed_agent | 4 | 4 | Returns most-blamed agent across strategies; reason shows "N/M strategies"; tie breaks in favor of first alphabetically; returns None cleanly on empty/no-error trace | 2026-04-06 |
| BlameResult model | 5 | 4 | agent_id, agent_name, strategy, confidence (0-1), reason, run_id all correct; confidence respects [0,1] bounds per strategy | 2026-04-06 |
| multiagent top-level exports | N/A | 1 | Twelfth instance of missing-top-level-export pattern (F-068); HandoffType also missing from submodule namespace (F-071) | 2026-04-06 |
| upstream CI (session-024) | 5 | 5 | Green for 3 consecutive runs including new "mark multi-agent trace and credit assignment as complete". Stable | 2026-04-06 |
| checkagent init (session-025) | 5 | 5 | F-005 FIXED — generates pyproject.toml with asyncio_mode+pythonpath; generated tests pass immediately. 10-session fix finally landed | 2026-04-06 |
| assign_blame LEAF_ERRORS (session-025) | 5 | 4 | F-069 FIXED — now correctly blames leaf agents (no outgoing handoffs). Root cause attribution now works as intended | 2026-04-06 |
| HandoffType namespace (session-025) | 5 | 5 | F-071 FIXED — HandoffType importable from checkagent.multiagent directly | 2026-04-06 |
| MultiAgentTrace.add_run/add_handoff | 3 | 2 | Correctly mutates trace state; returns None (not chainable — F-074); works correctly for sequential calls | 2026-04-06 |
| MultiAgentTrace.root_runs | 4 | 3 | Correctly identifies roots via parent_run_id; returns all runs when no parent_run_id set (expected); uses parent_run_id not explicit handoffs (F-075) | 2026-04-06 |
| MultiAgentTrace.get_children | 3 | 2 | Works correctly when given run_id; takes run_id not agent_id unlike all other topology methods — API inconsistency trap (F-073) | 2026-04-06 |
| MultiAgentTrace.detect_handoffs | 2 | 2 | Auto-detects from parent_run_id correctly; MUTATES trace.handoffs as side effect (F-076); calling twice duplicates handoffs; name implies read-only | 2026-04-06 |
| MultiAgentTrace.handoff_chain | 4 | 3 | Returns topological order from explicit handoffs; correct when handoffs set; returns [] when only parent_run_id used (F-075) | 2026-04-06 |
| MultiAgentTrace aggregate properties | 5 | 5 | total_steps, total_tokens, total_duration_ms, succeeded, failed_runs all correct; None when data missing (expected) | 2026-04-06 |
| MultiAgentTrace.agent_ids | 5 | 5 | Returns all agent IDs in order; correct | 2026-04-06 |
| MultiAgentTrace.get_runs_by_agent | 5 | 4 | Returns all runs for agent_id; handles multi-run agents correctly | 2026-04-06 |
| MultiAgentTrace.get_handoffs_from/to | 5 | 4 | Both work correctly from explicit handoffs; use agent_id (consistent with get_runs_by_agent) | 2026-04-06 |
| upstream CI (session-025) | 5 | 5 | Green for 4 consecutive runs including latest "Fix checkagent init". Very stable | 2026-04-06 |
| upstream CI (session-026) | 5 | 5 | Green for 5 consecutive runs — "Fix detect_handoffs() mutation bug and add builder chaining" passes. Very stable | 2026-04-06 |
| MultiAgentTrace.add_run/add_handoff (session-026) | 5 | 5 | F-074 FIXED — both return self; builder chaining now works: .add_run().add_run().add_handoff() | 2026-04-06 |
| MultiAgentTrace.detect_handoffs (session-026) | 5 | 5 | F-076 FIXED — now read-only; does not mutate trace.handoffs; calling twice still returns same results | 2026-04-06 |
| apply_detected_handoffs() | 5 | 4 | New method: converts parent_run_id links to explicit handoffs; idempotent; returns applied list; bridges F-075 gap | 2026-04-06 |
| MultiAgentTrace.handoff_chain() with cycles | 3 | 2 | No crash on cyclic handoffs; returns list with repeated nodes (a→b→c→a → ['a','b','c','a']); no cycle detection or warning (F-077) | 2026-04-06 |
| MultiAgentTrace JSON serialization | 5 | 5 | model_dump_json/model_validate_json round-trip preserves all fields: runs, handoffs, trace_id, agent_ids, HandoffType enums | 2026-04-06 |
| assign_blame_ensemble lambda strategies | 3 | 3 | Accepts lambdas as strategies (undocumented); lambdas returning None are silently filtered; must return BlameResult to contribute | 2026-04-06 |
| MockLLM.with_usage() | 4 | 3 | Fixed tokens work on complete/complete_sync/stream; auto_estimate formula wrong in docs (F-080: actual is len//4+1 not len//4); setting both fixed+auto_estimate is silent undefined behavior (F-081); no error raised | 2026-04-06 |
| MatchMode top-level export | 5 | 5 | Importable from checkagent; EXACT/SUBSTRING/REGEX all work; SUBSTRING default for add_rule means '.*' is literal (DX trap but documented behavior) | 2026-04-06 |
| upstream CI (session-028) | 5 | 5 | Green — 6 consecutive successes. "Add framework overhead benchmarks for RQ4 paper data" passes all platforms | 2026-04-06 |
| MockLLM.with_usage() (session-029) | 5 | 5 | F-080 FIXED (docstring now correct), F-081 FIXED (ValueError on conflict), F-078 partial fix (triggered property added) | 2026-04-06 |
| FaultInjector.triggered property | 5 | 5 | New @property returning bool; trigger_count and triggered_records also added; was_triggered(target) still works | 2026-04-06 |
| on_llm() fault methods | 5 | 5 | F-082 FIXED (session-030): all 7 types now work — content_filter/context_overflow/partial_response/rate_limit/server_error/intermittent/slow; full parity with tool fault builder; LLMIntermittentError/LLMSlowError importable from checkagent.mock.fault | 2026-04-06 |
| assert_json_schema (session-029) | 2 | 3 | F-008 partial fix: jsonschema now under [json-schema] extra; still not default dep. dirty-equals/deepdiff also only under [structured] (F-083) | 2026-04-06 |
| upstream CI (session-029) | 5 | 5 | Green — 7 consecutive successes. "Fix DX issues: jsonschema dep, triggered property, with_usage validation" passes all platforms | 2026-04-06 |
| upstream CI (session-031) | 5 | 5 | Green — 8 consecutive successes ("Add intermittent and slow faults to LLM fault builder"). Same commit as session-030 — no new upstream changes | 2026-04-06 |
| LangChain real agent integration (session-031) | 4 | 3 | LCEL chain + LangChainAdapter + FakeChatModel works cleanly; multi-variable chain fails (F-084 — use prompt.partial() workaround); string final_output ✓ when StrOutputParser used | 2026-04-06 |
| calculate_run_cost (session-031) | 5 | 5 | Now at top-level checkagent (improvement from F-018 partial fix); API unchanged (pricing_overrides/default_pricing); ProviderPricing/BUILTIN_PRICING still internal | 2026-04-06 |
| CostTracker/CostBreakdown/CostReport/BudgetExceededError (session-031) | 5 | 5 | All 5 cost classes now at top-level checkagent; was already true in prior sessions but confirmed against d0dd9265 | 2026-04-06 |
| upstream CI (session-032) | 5 | 5 | Green — 9 consecutive successes. Same commit as session-031 — no new upstream changes | 2026-04-06 |
| PydanticAI real agent integration (session-032) | 4 | 3 | Works with PydanticAI 1.77.0 via TestModel; final_output correct (string or Pydantic model); tokens extracted; structured output + assert_output_schema works; F-085 (input_text always ''), F-086 (not at top-level), F-087 (deprecated token attrs) | 2026-04-06 |
| PydanticAIAdapter structured output | 5 | 4 | Pydantic model instance flows through correctly; use model_dump() for assert_output_schema | 2026-04-06 |
| checkagent[all] extra | 1 | 1 | F-088: No [all] extra — users must manually combine extras and install framework deps separately | 2026-04-06 |
| LangChain tool-calling agents | 2 | 2 | bind_tools() raises NotImplementedError on GenericFakeChatModel — no clean fake model for tool calling; custom stateful runnable works as workaround but mock layer cannot intercept internal tool calls | 2026-04-06 |
| upstream CI (session-033) | 2 | 2 | Red — Windows-only failure on new ci-init command (F-091 path separator). Breaks 9-session green streak. All non-Windows platforms passing. | 2026-04-11 |
| top-level exports (0.1.2 batch fix) | 5 | 5 | F-020/F-021/F-026/F-030/F-032/F-048/F-053/F-057/F-063/F-068/F-086 ALL FIXED — 11 findings resolved in one release. Every adapter, eval, safety, judge, multiagent class now at top-level checkagent. | 2026-04-11 |
| checkagent scan CLI | 4 | 4 | New in 0.1.2: scans Python callables + HTTP endpoints; all 4 categories (injection/jailbreak/pii/scope); JSON output, badge SVG, --generate-tests; async agents handled correctly; F-089 (private API in generated tests) | 2026-04-11 |
| checkagent ci-init CLI | 4 | 4 | New in 0.1.2: scaffolds GitHub/GitLab CI configs; valid YAML; custom scan targets; --force overwrite; clean UX; F-091 (Windows path separator in output message) | 2026-04-11 |
| PydanticAI adapter streaming | 5 | 5 | run_stream() emits RUN_START/TEXT_DELTA/RUN_END; StreamCollector works correctly; aggregated_text correct; time_to_first_token populated | 2026-04-11 |
| ResilienceProfile | 4 | 4 | from_scores() and from_runs() both work; to_dict() complete except best_scenario (F-090); worst_scenario/weakest_metric correct; overall capped at [0,1] | 2026-04-11 |
| version consistency (0.1.2) | 5 | 5 | __version__ and importlib.metadata both return '0.1.2'. Version inconsistency bug from 0.1.1 fixed. | 2026-04-11 |
| upstream CI (session-034) | 1 | 1 | Red — ALL platforms failing. Latest commit "Add checkagent analyze-prompt" breaks ruff lint (I001 unsorted imports x3, E501 line too long). Previous commit was green. | 2026-04-11 |
| checkagent analyze-prompt CLI | 3 | 3 | New: 8-check static analysis (no LLM needed); exit 0/1 based on HIGH checks; --json output; file reading works; F-093 (Rich markup strips [brackets]), F-094 (nonexistent file silent), exit code behavior undocumented | 2026-04-11 |
| PromptAnalyzer Python API | 4 | 4 | F-110 FIXED: CheckResult now has .severity/.name @property shortcuts; check_results and missing_high now use consistent access pattern | 2026-04-22 |
| data_enumeration scan category | 4 | 3 | New 5th category; 20 probes (HIGH+CRITICAL); correct category metadata; echo agents get false positives (expected); DataEnumerationDetector/probes_data_enumeration not at top-level | 2026-04-11 |
| class-based agent scan | 4 | 4 | module:ClassName auto-instantiates class; correct probe execution; refusal class agent scores 1.0 on injection; clean JSON output | 2026-04-11 |
| EvalCase top-level export | 4 | 4 | At top-level checkagent; id+input+expected_tools/output_contains/output_equals/max_steps/tags/context/metadata; still str-only input (same as TestCase) | 2026-04-11 |
| SafetyFinding/SafetyResult/SafetyEvaluator top-level | 5 | 4 | All 3 at top-level; SafetyEvaluator.evaluate_run() returns SafetyResult correctly; evaluate() for direct output text; clean API | 2026-04-11 |
| ScenarioResult top-level export | 5 | 5 | At top-level; scenario/scores/degradation/resilience fields all correct | 2026-04-11 |
| TestRunSummary | 5 | 4 | Alias for CI RunSummary with better name; same pass_rate/total/passed/failed; resolves F-029 naming confusion partially | 2026-04-11 |
| upstream CI (session-035) | 5 | 5 | GREEN — v0.2.0 published to PyPI. All platforms passing. F-097 fixed. | 2026-04-12 |
| checkagent 0.2.0 upgrade | 5 | 4 | PyPI release! 2107 tests upstream. F-093/F-094/F-095/F-097 all fixed. New: groundedness, compliance, conversation scanner, SARIF, wrap, --repeat | 2026-04-12 |
| GroundednessEvaluator (fabrication mode) | 4 | 4 | Detects missing hedging language correctly; evaluate() and evaluate_run() both work; custom patterns via add_hedging_pattern(); uncertainty mode broken (F-099) | 2026-04-12 |
| GroundednessEvaluator (uncertainty mode) | 5 | 4 | F-099 FIXED in v0.3.0: hedging signals detected correctly; add_hedging_pattern() now applied; requires `description` arg (undocumented) | 2026-04-19 |
| probes_groundedness | 4 | 4 | 8 probes (fabrication+uncertainty); correct category/severity; module structure consistent with probes_injection/probes_pii — all are modules with .all_probes ProbeSet; ProbeSet composition works | 2026-04-17 |
| ConversationSafetyScanner | 4 | 3 | Detects per-turn and aggregate findings; uses conv.say(); requires evaluators list (no default); split/accumulation attack detection via aggregate_only_findings; not at top-level | 2026-04-12 |
| ConversationSafetyResult | 5 | 4 | F-101 FIXED: iter_turn_findings() helper added with docstring warning against enumerate(); turns_with_findings/total_per_turn_findings/total_findings properties also added | 2026-04-16 |
| ComplianceReport / generate_compliance_report | 5 | 4 | Correct totals/rates; has_critical_findings works; to_dict() complete; not at top-level | 2026-04-12 |
| render_compliance_markdown/json/html | 5 | 4 | All three render correctly; markdown has proper table, JSON is parseable, HTML returns valid markup | 2026-04-12 |
| EU_AI_ACT_MAPPING | 5 | 4 | Covers all SafetyCategory values; Article strings; not at top-level checkagent | 2026-04-12 |
| SARIF 2.1.0 output (--sarif) | 5 | 5 | Valid SARIF 2.1.0; tool metadata with version; rules with remediation markdown; works alongside --json | 2026-04-12 |
| --repeat N flag | 5 | 4 | Stability object in JSON (repeat, stable_pass, stable_fail, flaky, stability_score); echo agent shows 1.0 stability; F-098 (diagnostic on stdout breaks --json parse) | 2026-04-12 |
| --prompt-file flag | 5 | 5 | Static analysis shown inline with dynamic scan; correct scores; injection guard detected | 2026-04-12 |
| checkagent wrap CLI | 5 | 4 | F-105 FIXED: generates correct `_agent = _target()` then `_agent.invoke(prompt)`; 0 errors on class agent scan; auto-detection message goes to stdout (F-106) | 2026-04-17 |
| checkagent wrap (plain function) | 5 | 5 | "No wrapper needed, scan directly" message for plain callables; correct auto-detection | 2026-04-16 |
| checkagent scan --url (HTTP) | 5 | 5 | HTTP endpoint scanning works: POST probes, --input-field, --output-field, auto-detect, -H headers, --json clean, --generate-tests creates stdlib test file, server-down shows errors count | 2026-04-13 |
| --repeat N with --url (flaky agents) | 5 | 5 | stability_score < 1.0 for flaky server; stable_pass/stable_fail/flaky counts correct; probe fails if ANY run triggers finding | 2026-04-16 |
| generate_test_cases (session-038) | 4 | 3 | F-103 partially fixed: name= now emits DeprecationWarning (not TypeError). safety_check=False skips screening correctly. Return type still tuple (breaking). | 2026-04-16 |
| upstream CI (session-037) | 1 | 1 | Red — Windows Python 3.13 ConnectionAbortedError in HTTP scan test (F-104) | 2026-04-15 |
| upstream CI (session-038) | 5 | 5 | GREEN — all 12 jobs passing including Windows 3.10/3.11/3.12/3.13. F-104 fixed. 1 session red streak ended. | 2026-04-16 |
| checkagent scan --report HTML | 5 | 5 | Generates valid HTML with summary stats, category breakdown, OWASP LLM Top 10 + EU AI Act regulatory mapping; works alongside --json; written confirmation in terminal | 2026-04-17 |
| GroundednessEvaluator top-level export | 5 | 5 | F-107 FIXED in v0.3.0: importable from checkagent directly alongside ConversationSafetyScanner and PromptCheck | 2026-05-02 |
| groundedness scan category | 5 | 5 | --category groundedness runs 8 probes (fabrication+uncertainty) with 0 errors; composable with ProbeSet; clean JSON output | 2026-04-17 |
| ToolBoundary dataclass | 4 | 3 | Clean config object; F-109 shim added; but forbidden_argument_patterns is dict[str,str] not set — confusing name causes AttributeError (F-111) | 2026-04-20 |
| PromptAnalysisResult.missing_high/missing_medium/recommendations | 5 | 5 | New properties in v0.3.0: filter failed checks by severity; recommendations returns actionable strings; all work correctly | 2026-04-19 |
| checkagent.wrap Python API | 5 | 4 | @wrap decorator and wrap(fn) both work cleanly; wrap(callable_instance) works; wrap(Class) with invoke() silently returns None — CLI handles class agents but Python API doesn't auto-detect invoke() | 2026-04-20 |
| upstream CI (session-041) | 5 | 5 | Green — all 12 jobs passing. Latest: "Fix F-109: add deprecation shim". 3 consecutive successes. | 2026-04-20 |
| wrap() Python API (framework agents) | 5 | 5 | F-112 FIXED: wrap() auto-detects PydanticAI Agent → PydanticAIAdapter, LangChain Runnable → LangChainAdapter; unrecognized non-callables get helpful TypeError listing adapters | 2026-04-22 |
| PydanticAI real agent end-to-end (session-043) | 5 | 5 | wrap(pydantic_ai.Agent) now works directly — auto-detects and returns PydanticAIAdapter with string final_output. No lambda workaround needed. | 2026-04-22 |
| ToolBoundary new API (non-deprecated) | 5 | 4 | Now at top-level checkagent (from checkagent import ToolBoundary). Deprecation migration path fully resolved. F-111 improved: set raises TypeError with clear dict format message | 2026-04-22 |
| upstream CI (session-043) | 5 | 5 | Green — latest "Fix F-112: wrap() auto-detects framework agents, add ToolBoundary top…" passes all platforms. 4 consecutive successes. | 2026-04-22 |
| ProbeSet.filter() tags case-sensitivity | 5 | 5 | F-113 FIXED (session-047): filter(tags={'INDIRECT'}) now returns same count as filter(tags={'indirect'}). Fully consistent with severity/category filter behavior. | 2026-04-30 |
| --llm-judge flag error handling | 5 | 5 | Clear, actionable error messages for both Anthropic (ANTHROPIC_API_KEY) and OpenAI (OPENAI_API_KEY) — no stack trace, correct env var name per model | 2026-04-23 |
| wrap() + PydanticAI structured output_type | 5 | 4 | wrap(Agent(output_type=Model)) auto-detects → PydanticAIAdapter; final_output is Pydantic model instance (not str). assert_output_schema and assert_json_schema(result.final_output, ...) both work correctly | 2026-04-23 |
| CrewAI adapter lazy import | 5 | 5 | Importable without crewai; raises ImportError with clear message ("requires crewai") at instantiation; wrap() TypeError lists CrewAIAdapter as option | 2026-04-23 |
| upstream CI (session-044) | 5 | 5 | Green — new ROADMAP-only commit today ("Add Phase 5"). No code changes. 5 consecutive successes. | 2026-04-24 |
| v0.3.0 PyPI release | 5 | 5 | F-114 FIXED (2026-05-02): pip install checkagent now returns 0.3.0. All 0.3.0 fixes now reachable for first-time users. | 2026-05-02 |
| checkagent init (session-044) | 5 | 5 | Still works: generates 2-test project that passes immediately. Phase 5 end-to-end goal confirmed on git main. | 2026-04-24 |
| PromptAnalyzer scope_boundary patterns | 5 | 4 | New patterns (session-045): 'ONLY answer HR questions', 'your role is limited to', 'domain agent and only' all detected correctly; old patterns still work; DX: patterns are fully invisible to users (no docs listing what to write) | 2026-04-25 |
| upstream CI (session-045) | 5 | 5 | Green — new commit "Expand scope_boundary patterns to catch common real-world phrasings". 6 consecutive successes. | 2026-04-25 |
| check_behavioral_compliance (overall) | 5 | 5 | F-117 FIXED (session-049): now importable from top-level checkagent. All DX gaps resolved. | 2026-05-06 |
| behavioral baseline: refusal detection | 5 | 5 | 5 common refusal patterns all correctly return 0 findings; scope-limiting refusals pass cleanly after latest fix | 2026-04-27 |
| behavioral baseline: compliance detection | 4 | 3 | Detects structural divergence (bullets, tables, code blocks, length_anomaly) and basic no-refusal; short compliant responses missed (length bias); finding quality good | 2026-04-27 |
| upstream CI (session-046) | 5 | 5 | Green — 7 consecutive successes. "Fix behavioral detector false positive on scope-limiting refusals" passes all platforms. | 2026-04-27 |
| PromptAnalyzer role_clarity patterns | 5 | 4 | F-108 FIXED (session-047): 'You are AcmeBot', 'I am Aria' (proper nouns, no article) now detected. 'politely decline' (bare), 'tell the user you cannot', 'Never share salary' also added. DX: still no docs listing which phrases trigger each check. | 2026-04-30 |
| scan history persistence | 5 | 5 | F-118 FIXED (session-049): score_delta is now 0.0 (not -0.0) for equal scores. History delta DX is clean. | 2026-05-06 |
| checkagent history CLI | 5 | 5 | Table output with Date/Time/Score/Passed/Failed/Total/Time; --limit works; friendly message for unknown targets; --help documents TARGET and --limit; clean exit 0 | 2026-04-30 |
| checkagent init .gitignore protection | 5 | 5 | Creates .checkagent/ entry in .gitignore; appends to existing .gitignore; idempotent (no duplicates on second run) | 2026-04-30 |
| upstream CI (session-047) | 5 | 5 | Green — 3 consecutive successes. Latest: "Expand analyze-prompt patterns to reduce false negatives on real-world prompts". 8 consecutive successes total. | 2026-04-30 |
| PromptAnalyzer RAG patterns | 5 | 4 | New (session-048): 'say: I cannot find enough information' → refusal_behavior; 'do not use external knowledge' and 'base answers strictly on retrieved content' → data_scope; all three work correctly with no false positives on generic prompts | 2026-05-02 |
| upstream CI (session-048) | 5 | 5 | Green — 9 consecutive successes. Latest: "Fix false negatives on RAG-style refusal and data-scope patterns". Stable. | 2026-05-02 |
| --badge SVG generation | 5 | 5 | New in session-049: shields.io-style SVG badge; color-coded by score (green #4c1 high, red #e05d44 low); "N/M safe" label; "Badge written → FILE" terminal confirmation; works combined with --json | 2026-05-06 |
| upstream CI (session-049) | 5 | 5 | Green — 10 consecutive successes. Latest: "Add one-click test file generation to browser playground". All platforms passing. | 2026-05-06 |
| history --url flag | 5 | 5 | F-119 FIXED (session-050): `checkagent history --url http://...` now works. HTTP scan history end-to-end confirmed. | 2026-05-11 |
| has_refusal() / check_no_refusal() | 3 | 3 | New in session-050: check_no_refusal() clean API, LOW severity signal. has_refusal() misses 'I refuse', 'decline', 'violates my guidelines' (F-121) — limits usefulness of refusal-aware scan. | 2026-05-11 |
| Refusal-aware scan (false positive fix) | 4 | 3 | Correctly eliminates false positives for agents that refuse probes using "cannot/unable/must refuse" phrases. Fails for agents that say "I refuse to follow" or "I decline" — F-121 limits coverage. | 2026-05-11 |
| --interactive TUI flag | 4 | 4 | New in session-050: -i/--interactive flag for checkagent scan; documented in --help; exits cleanly when no TTY (CI-safe). Interactive mode itself can't be tested non-interactively. | 2026-05-11 |
| checkagent.core.tracer (auto-instrumentation) | 2 | 2 | Skeleton API exists (install/begin/end/uninstall); all lifecycle methods work without error; end_probe_trace() always returns [] — patches are stubs (F-120). Milestone 17 pending. | 2026-05-11 |
| ca_ fixture aliases | 5 | 5 | New in session-050: ca_mock_llm, ca_mock_tool, ca_conversation, ca_fault, ca_safety, ca_stream_collector all work as expected; consistent with ap_ aliases but shorter. | 2026-05-11 |
| upstream CI (session-050) | 5 | 5 | Green — all 3 latest runs success including new TUI and refusal-fix commits. 11+ consecutive successes. | 2026-05-11 |
| has_refusal() (session-051) | 4 | 4 | F-121 PARTIALLY FIXED in v0.3.1: 'I refuse', 'I decline', 'violates my guidelines', "I won't do that", 'must decline', 'policies' all now detected. Remaining gaps: 'I am unable to process', "I won't help" bare, 'I will not do that'. | 2026-05-13 |
| literal() MockTool response | 4 | 3 | New in v0.3.1: prevents list cycling in MockTool.register(). Works correctly. Docstring misleads — says MockTool/MockLLM but MockLLM.add_rule() raises ValidationError (F-122). | 2026-05-13 |
| upstream CI (session-051) | 5 | 5 | Green — latest 'Bump version to 0.3.1' and 'Fix F-121' both pass all platforms. 12+ consecutive successes. | 2026-05-13 |
| upstream CI (session-052) | 5 | 5 | Green — "Mark Milestone 13 items complete" passes all 12 platforms. 13+ consecutive successes. | 2026-05-14 |
| has_refusal() (session-052) | 4 | 4 | F-121 3 remaining gaps confirmed: 'I am unable to process', 'I will not do that', 'That is not something I will help with'. Also "I won't help" now works (fixed in v0.3.1). | 2026-05-14 |
| GateResult class (evaluate_gate return type) | 5 | 4 | New: evaluate_gate() returns GateResult with metric/verdict/actual/threshold/direction/message. Richer than old GateVerdict. QualityGateReport lists now contain GateResult objects. | 2026-05-14 |
| v0.3.1 PyPI release | 1 | 1 | F-123: v0.3.1 not published to PyPI. PyPI latest is still 0.3.0. Users miss has_refusal + literal() fixes. | 2026-05-14 |
| has_refusal() (session-053) | 5 | 4 | F-121 FULLY FIXED: all 3 remaining gaps resolved — 'I am unable to process', 'I will not do that', 'That is not something I will help with' all return True. 8+ phrases confirmed working. | 2026-05-15 |
| literal() in MockLLM (session-053) | 5 | 4 | F-122 FIXED: literal() now accepted by MockLLM.add_rule() AND on_input().respond(). List values JSON-serialized in LLM context. Importable from checkagent/checkagent.mock/checkagent.mock.tool. | 2026-05-15 |
| MockLLM.on_input().respond() fluent API (session-053) | 5 | 5 | F-001 FIXED: on_input(contains/pattern/exact).respond(str/list/literal) and .stream(chunks) all work. Multiple rules compose cleanly. Unmatched falls back to default. | 2026-05-15 |
| auto-instrumentation tracer (session-053) | 2 | 2 | F-120 still open: install_patches()/uninstall_patches() work; begin_probe_trace() returns None; end_probe_trace() returns []. Stubs only. Milestone 17 still pending. | 2026-05-15 |
| ca_tracer fixture | 3 | 4 | New in session-054: fixture exists, lifecycle clean (begin/end/events/llm_calls/tool_calls), is_installed() guards. F-120 still open: no events captured without real API calls. Functionality score low until tracing actually works. | 2026-05-17 |
| checkagent.core.tracer API (session-054) | 3 | 5 | F-124 FIXED (session-055): is_installed() now at top-level. All 6 tracer symbols exported. F-120 still open: still no captured events without real API calls. | 2026-05-18 |
| upstream CI (session-054) | 4 | 4 | Latest run GREEN ("Show real findings in README scan example"). Previous red: openai not installed in CI broke test_openai_async_real_client_traced — quickly fixed. 1-run red streak, now green. | 2026-05-17 |
| v0.3.1 PyPI release (session-054) | 1 | 1 | F-123 still open: PyPI shows 0.3.0, git main has 0.3.1. ca_tracer / F-120 fixes not reachable for PyPI users. | 2026-05-17 |
| analyze-prompt --llm flag | 4 | 3 | New in session-055: semantic LLM verification for failing pattern checks; clear error for invalid models; new JSON fields (llm_verified_count, llm_model, llm_passed per check); F-125: silent fallback when no API key — "Running..." message misleads user but verifies 0 checks | 2026-05-18 |
| upstream CI (session-055) | 5 | 5 | Green — latest "Add --llm flag to analyze-prompt for semantic verification". 11+ consecutive successes. | 2026-05-18 |
| --extra-body flag (scan HTTP) | 5 | 5 | New in session-056: merges extra JSON into every HTTP probe request; enables Dify/custom API endpoint scanning; F-126/F-127 both FIXED (session-058): warning shown on callable, and warning now goes to stderr (not stdout) — `--json` output is clean JSON | 2026-05-22 |
| analyze-prompt --llm flag (session-056) | 4 | 4 | F-125 FIXED: now warns "LLM verification skipped — API_KEY is not set" for both Anthropic/OpenAI; llm_passed is now None (not False) when LLM not run — more semantically correct | 2026-05-19 |
| upstream CI (session-056) | 5 | 5 | Green — latest "Add --extra-body to scan for Dify and custom API endpoints" passes all platforms. 12+ consecutive successes. | 2026-05-19 |
| v0.3.1 PyPI release (session-056) | 1 | 1 | F-123 still open: PyPI shows 0.3.0 as latest, git main is 0.3.1. 0.3.1 only available via git install. | 2026-05-19 |
| --generate-tests HTTP passthrough (session-057) | 5 | 4 | FIXED: EXTRA_BODY, INPUT_FIELD, OUTPUT_FIELD, AUTH_HEADERS all embedded in generated file; payload merges correctly; generated tests run against live server; F-128: uses evaluate_output() (static only) — misses ~60% of behavioral/baseline findings from scan | 2026-05-20 |
| upstream CI (session-057) | 5 | 5 | Green — "Fix --generate-tests HTTP passthrough: use scan-time input_field, extra_body, headers; warn on --extra-body without --url (F-126)" passes all 12 platforms. 13+ consecutive successes. | 2026-05-20 |
| v0.3.1 PyPI release (session-057) | 1 | 1 | F-123 still open: PyPI shows 0.3.0 as latest, git main is 0.3.1. | 2026-05-20 |
| evaluate_output_with_baseline | 5 | 5 | F-128 FIXED (session-058): new function at top-level checkagent; detects code blocks/length/table divergence vs baseline; empty baseline falls back to static-only; category param passes through; safe response returns 0 findings | 2026-05-22 |
| --generate-tests (baseline-aware, session-058) | 5 | 5 | F-128 FIXED: generated tests now use evaluate_output_with_baseline + session-scoped baseline fixture; echo agent: 35/35 tests fail (vs 14/35 before). Full parity with scan findings. | 2026-05-22 |
| upstream CI (session-058) | 5 | 5 | Green — "Fix F-128: add evaluate_output_with_baseline; generated tests now include baseline comparison" passes all 12 platforms. 14+ consecutive successes. | 2026-05-22 |
| v0.3.1 PyPI release (session-058) | 1 | 1 | F-123 still open: PyPI shows 0.3.0 as latest, git main is 0.3.1. | 2026-05-22 |
| scan_gates config (ScanGatesConfig) | 5 | 4 | max_critical/max_high/max_findings/min_score all work; on_fail block→exit 2, warn→exit 0; quality_gates in JSON; ScanGatesConfig at top-level; no docs on quality_gates JSON structure | 2026-05-23 |
| --comment-file flag | 5 | 5 | Generates GitHub-formatted PR comment markdown; ✅/❌ emoji; summary table + findings table + truncation; works with --json; terminal confirmation; CheckAgent footer | 2026-05-23 |
| upstream CI (session-059) | 2 | 2 | F-129: Windows 3.13 failing at actions/checkout@v4 — GitHub Actions Node.js 20 deprecation. Code is fine, actions pins need updating before June 2 2026 deadline | 2026-05-23 |
| upstream CI (session-060) | 4 | 4 | Latest run GREEN all 12 platforms incl. Windows 3.13; F-129 FIXED. Previous run (docs commit) was red. | 2026-05-24 |
| salary/currency PII patterns | 2 | 2 | F-130: matches ANY dollar amount — $9.99 product price flagged as salary_amount. Massive false positive rate for any agent discussing prices or finance | 2026-05-24 |
| --verbose flag (scan) | 1 | 2 | F-131: crashes with MarkupError when echo agents return [bracket] text; DX gap: warning says "Use --verbose" even when already using --verbose; still doesn't show per-probe error details | 2026-05-24 |
| 40%+ probe error warning | 4 | 3 | Warning shown in terminal when 40%+ probes error (useful safety net); JSON output has no error_warning field (programmatic users can't detect this); warning says "Use --verbose" even in verbose mode | 2026-05-24 |
| HTML compliance report (agent+version) | 5 | 3 | Report now includes agent target and checkagent version; DX gap: version labeled "Model" (implies LLM model, not framework version) | 2026-05-24 |
| salary/currency PII patterns (session-061) | 4 | 4 | F-130 FIXED: retail prices ($9.99, $23.50) no longer flagged. Real salaries ($95k, $1.5M, $120,000) still detected. Tradeoff: hourly wages like $25.50 are false negatives now | 2026-05-26 |
| --verbose flag (session-061) | 5 | 4 | F-131 FIXED: markup_escape() applied to all probe/response text; no more MarkupError on echo agents; DX gaps remain: warning text doesn't adapt when already in verbose mode | 2026-05-26 |
| --llm-judge claude-code | 5 | 5 | F-132 FIXED: evaluator field now in JSON summary as summary.evaluator='claude-code'. Full feature confirmed: zero API key, $0.00 cost, more accurate than regex for echo agents | 2026-05-28 |
| --repeat + --llm-judge combination | 5 | 5 | Fully compatible: stability object present, repeat count correct, evaluator field preserved across repeat runs, no errors; clean JSON throughout | 2026-05-28 |
| real PydanticAI agent + LLM judge | 5 | 4 | travel_agent scanned with --llm-judge claude-code on scope category: 8/8 probes pass, 0 errors, evaluator field correct; PydanticAI API changes (custom_output_text→custom_output_text, result.data→result.output) are agent-side not checkagent issues | 2026-05-28 |
| upstream CI (session-061) | 5 | 5 | Green — "Add Milestones 18-19 to ROADMAP" and "Add --llm-judge claude-code" both pass all 12 platforms. 16+ consecutive successes. | 2026-05-26 |
| upstream CI (session-062) | 5 | 5 | Green — all 5 latest CI runs success across CI and Deploy Docs workflows. Latest: "Add score interpretation table and framework guide links to README" (2026-05-28). Stable. | 2026-05-28 |
| upstream CI (session-063) | 5 | 5 | Green — v0.4.0 released. Latest: "Add real-world benchmark data to README". All 5 recent runs green. 17+ consecutive successes. | 2026-06-02 |
| v0.4.0 PyPI release | 5 | 5 | F-123 FIXED: v0.3.1 published 2026-05-30, v0.4.0 published 2026-06-02. `pip install checkagent` now gets 0.4.0. | 2026-06-02 |
| checkagent.core.tracer (session-063) | 5 | 5 | F-120 FIXED: MockLLM now emits tracer events; TracerContext.begin/end captures llm_call events with type/provider/model/prompt_preview/response_preview/latency_ms; MockTool still no events (LLM-only for now) | 2026-06-02 |
| MockTool tracer events (session-064) | 5 | 4 | Post-v0.4.0 commit: MockTool.call()/call_sync() now emit tool_call events to TracerContext; error field populated on failed calls; result stored as string repr; begin/end_probe_trace() also captures tool events; tc.tool_calls resets on each begin() | 2026-06-03 |
| --comment-file + --llm-judge (session-064) | 4 | 3 | Comment file generated correctly, non-empty; but evaluator method not shown in PR comment (F-133); JSON output has evaluator field; terminal shows it but markdown template doesn't | 2026-06-03 |
| upstream CI (session-064) | 5 | 5 | Green — latest "Update TracerContext docs to describe tool_call events; close Milestone 19". All 5 recent runs green. 18+ consecutive successes. | 2026-06-03 |
| 40%+ probe error warning (session-063) | 5 | 5 | error_warning JSON field added in v0.4.0: type/error_count/total_count/error_rate/message; programmatic CI can now detect unreliable scans; verbose hint fixed ("shown above" vs "Use --verbose") | 2026-06-02 |
| --generate-tests (session-063) | 5 | 5 | F-089 FIXED: generated tests now use public resolve_callable; no private _resolve_callable in generated files | 2026-06-02 |
| --comment-file + --llm-judge (session-065) | 5 | 4 | F-133 FIXED: PR comment now includes Evaluator row when --llm-judge used. Confirmed both ways: with judge → Evaluator row present; without judge → no Evaluator row. | 2026-06-05 |
| checkagent diff command | 5 | 4 | New in session-065 (post-v0.4.0): compare two scan JSONs; score delta, new/fixed/unchanged findings; --fail-on-new exits 1 on regression; --comment-file generates GitHub PR markdown; --json structured output. All features confirmed working. F-134 (Windows UTF-8 UnicodeDecodeError on generated markdown) open. | 2026-06-05 |
| upstream CI (session-065) | 1 | 1 | RED — "Document diff command and --diff flag in README and CLI reference" fails Windows 3.12 and 3.13. F-134: test reads diff --comment-file output without encoding='utf-8'; cp1252 can't decode UTF-8 emoji bytes. 19-session green streak broken. | 2026-06-05 |
| checkagent history + sparkline | 5 | 5 | New in session-065 (post-v0.4.0): Trend: line with sparkline chart + "stable/improved/declined N%" summary text; ↑/↓ delta markers in table rows; --limit controls row count; unknown target gives friendly message. All confirmed. | 2026-06-05 |
| upstream CI (session-066) | 5 | 5 | GREEN — v0.5.0 released (2026-06-06). F-134 FIXED. Latest commits: "Document diff gates and stability tracking" (2026-06-07). 2 consecutive green runs. | 2026-06-07 |
| v0.5.0 PyPI release | 5 | 5 | v0.5.0 published 2026-06-06 to PyPI. pip install checkagent returns 0.5.0. | 2026-06-07 |
| diff --comment-file UTF-8 (F-134 fixed) | 5 | 5 | F-134 FIXED in v0.5.0: encoding='utf-8' now specified when writing comment files; readable on Windows. Confirmed locally. | 2026-06-07 |
| checkagent diff --min-score | 5 | 4 | New gate flag: exits 1 when current score < threshold; exits 0 at boundary (>=); clear error message with score/threshold; no gap found in core logic | 2026-06-07 |
| checkagent diff --min-stability | 5 | 4 | F-136 FIXED (session-066): now exits 1 with clear message when no stability data — gate is no longer a silent no-op; threshold enforcement correct | 2026-06-08 |
| scan --diff flag | 5 | 5 | F-135 FIXED (session-066): `--diff --json` now embeds full `diff` key (score.delta, counts, regression, new/fixed_findings) in JSON output; complete machine-readable regression detection from a single scan command | 2026-06-08 |
| ci-init --diff integration | 5 | 4 | Generated workflow includes --repeat 3 --diff; PR diff comment section is commented out without showing how to store/fetch baseline artifact in GitHub Actions — gap for the most useful CI pattern | 2026-06-07 |
| scan JSON category_breakdown | 5 | 5 | New (session-066): summary.category_breakdown shows finding counts by category (e.g. prompt_injection: 35); summary.severity_breakdown shows counts by severity level; both are dicts, empty for safe agents | 2026-06-08 |
| v1.0.0 PyPI release | 5 | 5 | v1.0.0 published 2026-06-13. `pip install checkagent` now returns 1.0.0. First stable/major release. | 2026-06-13 |
| upstream CI (session-067) | 1 | 1 | RED — F-142: latest commit "Add --fix flag to analyze-prompt" breaks Windows 3.11/3.12/3.13. Drive letter C: treated as module name. Linux/macOS all green. | 2026-06-13 |
| analyze-prompt --fix | 5 | 4 | New in v1.0.0: generates hardened prompt with boilerplate security controls for all failing checks. Text output clean; F-141: --fix --json outputs two JSON objects (invalid json.load()); DX gap: replace markers like [DEFINE SCOPE] need docs | 2026-06-13 |
| dashboard command | 5 | 3 | New in v0.6.0: reads .checkagent/history/, shows per-agent score table with trend/count/scans. Text output good; F-139: JSON missing trend + average_score; 262 agents tracked (port-per-session accumulation is a cosmetic noise issue) | 2026-06-13 |
| ci-init template (v1.0.0) | 5 | 5 | Significantly improved: two-job structure (scan + pr-diff), quality gates active by default, auto-post PR comment via GitHub script, artifact upload/download for cross-job baseline comparison. Production-ready. | 2026-06-13 |
| --category multi-flag (F-137) | 1 | 1 | F-137 still open in v1.0.0: only last --category runs; all others silently dropped | 2026-06-13 |
| diff --min-score scale (F-138) | 2 | 2 | F-138 still open in v1.0.0: --min-score 80 means 8000%, fails 100% agent. No validation or hint. | 2026-06-13 |
| v1.1.0 PyPI release | 5 | 5 | v1.1.0 published 2026-06-25. `pip install checkagent` returns 1.1.0. | 2026-06-25 |
| upstream CI (session-068) | 5 | 5 | GREEN — latest 2 runs green ("Enhance --list-targets: show constructor args and scan hints"). The "Bump version to 1.1.0" commit was briefly red (ruff lint) but fixed quickly. | 2026-06-25 |
| wrap --list-targets | 5 | 5 | New in v1.1.0: lists callable targets in a .py file without importing; shows function type (async fn/function/class); scan command hint for each; shows "Requires: api_key, ..." for classes with required constructor args + adapter/extract-prompt hint | 2026-06-25 |
| wrap --extract-prompt | 5 | 4 | New in v1.1.0: AST-based extraction of system_prompt/prompt/instruction variables; saves to <varname>.txt in CWD; shows preview + scan suggestion; DX gap: writes to CWD not to agent file's directory; --force needed to overwrite | 2026-06-25 |
| checkagent watch command | 5 | 5 | New in v1.1.0: file watcher for system prompts; updates analyze-prompt score on save; --interval controls poll rate; --llm for semantic verification; nonexistent file gives clear error immediately | 2026-06-25 |
| --system-prompt scan mode | 4 | 4 | New: scan a system prompt string/file directly via LLM without Python code; static analyze-prompt section runs immediately; LLM-based probe section requires API key; error message now mentions LLM config (F-144 FIXED); 35/35 errors with no API key but graceful | 2026-06-25 |
| --exit-zero flag | 5 | 4 | New: forces scan exit 0 even with findings; JSON still valid; tip shown in terminal; DX gap: help text references --min-score/--fail-on-new (diff-only flags) incorrectly (F-143 open) | 2026-06-25 |
| analyze-prompt --fix (v1.1.0) | 5 | 5 | F-141 FIXED: --fix --json now outputs single valid JSON with hardened_prompt key; F-145 NEW: [your domain] in table Note column stripped by Rich again | 2026-06-25 |
| analyze-prompt example hints (post-v1.1.0) | 5 | 5 | MISSING checks now show Try: "..." hint in table Note column with a 52-char excerpt from the recommendation; helps users know exactly what to add; F-145 FIXED: [your domain] bracket content now preserved via rich_escape() | 2026-06-27 |
| scan JSON probe_description + remediation | 5 | 5 | Each finding now includes probe_description (short sentence about the attack) and remediation (list of concrete steps); structured, actionable output for CI and downstream tooling | 2026-06-27 |
| wrap --list-targets (constructor args) | 5 | 5 | Enhanced: classes with required __init__ args show "Requires: api_key, model" + adapter/extract-prompt hint; directs users to next step without confusion; no change needed for function targets | 2026-06-27 |
| --exit-zero flag (F-143 status) | 5 | 5 | F-143 FIXED: help text now says "Use checkagent diff --min-score to enforce score thresholds after scanning" — directs to correct command; no longer references nonexistent --min-score on scan | 2026-06-27 |
| --category multi-flag (session-068) | 5 | 5 | F-137 FIXED in v1.1.0: all specified --category flags now run; tested injection+jailbreak+pii → all 3 appear in category_breakdown | 2026-06-25 |
| diff --min-score (session-068) | 5 | 4 | F-138 FIXED in v1.1.0: --min-score 80 now rejected with range error; --min-score 0.8 accepted | 2026-06-25 |
| dashboard --json (session-068) | 5 | 5 | F-139 FIXED in v1.1.0: JSON now includes trend and average_score per agent entry | 2026-06-25 |
| CassetteRecorder end-to-end (session-070) | 5 | 4 | Full record→finalize→save→load→replay cycle works. api_cassette pytest fixture added (session-070). F-045 FIXED. F-044 still open (SEQUENCE ignores kind). | 2026-06-28 |
| analyze-prompt table Note F-145 (session-069) | 5 | 4 | F-145 FIXED: 'Try:' hint text in table Note now preserves [brackets]. F-146 NEW: Prompt: header preview still strips brackets (different code path) | 2026-06-27 |
| analyze-prompt Prompt: header F-146 (cycle-192) | 5 | 5 | F-146 FIXED: Prompt: preview line now escapes [brackets] via rich_escape() — same fix pattern as F-145 but for the header, not the table Note | 2026-06-28 |
| ap_cassette pytest fixture (cycle-192) | 5 | 5 | NEW: ap_cassette fixture implements auto record/replay mode detection based on cassette file existence; @pytest.mark.cassette(path=...) overrides path; CassetteFixture has is_recording()/is_replaying() helpers; exported from checkagent | 2026-06-28 |
| v0→v1 cassette migration F-045 (cycle-192) | 5 | 5 | F-045 FIXED: _migrate_v0_to_v1 registered in _MIGRATIONS; normalizes meta fields, assigns interaction id/sequence; migrate_cassette_data() now works end-to-end on version=0 cassettes | 2026-06-28 |
| checkagent v1.2.0 upgrade | 5 | 4 | CI green. F-044 FIXED (strict_kind=True in SEQUENCE), F-146 FIXED (Prompt: header brackets). Enriched HTML compliance report: SVG gauge, stat cards, findings table, remediation. Not yet on PyPI. | 2026-07-04 |
| ReplayEngine strict_kind (v1.2.0) | 5 | 4 | F-044 FIXED: strict_kind=True enforces kind matching in SEQUENCE strategy; default is False (permissive, backward-compat); CassetteMismatchError message mentions 'kind' on mismatch | 2026-07-04 |
| stress-prompt CLI (v1.2.0) | 4 | 3 | New command: 9 adversarial transforms, 8 security checks, robustness score; stdin/file/literal input; --json clean output. F-147 (100% for 0-control prompts), F-148 (no Python API). transform count varies (8 vs 9) for single-sentence prompts. | 2026-07-04 |
| checkagent v1.3.0 upgrade | 5 | 5 | CI green. F-147 FIXED (N/A for zero-control prompts), F-148 FIXED (stress_prompt/ablate_prompt/predict_attack_surface Python APIs). New: ablate-prompt CLI, predict_attack_surface, AttackSurface/AttackVector, has_cycles(), get_children_by_agent(), CassetteRecorder.record_response(). F-090 FIXED. F-149 new. | 2026-07-10 |
| stress-prompt Python API (v1.3.0) | 5 | 5 | F-148 FIXED: stress_prompt(prompt) returns dict with robustness_score/baseline_passing/transforms/fragile_checks/robust_checks/no_controls_detected. F-147 FIXED: no_controls_detected=True and robustness_score=0.0 when no controls found. | 2026-07-10 |
| ablate-prompt CLI + Python API (v1.3.0) | 5 | 5 | New: ablate-prompt CLI removes each sentence and measures score impact; identifies load-bearing/redundant/single-points-of-failure. ablate_prompt() Python API. --json clean. Bracket content preserved. Single-sentence handled gracefully with error message. | 2026-07-10 |
| predict_attack_surface (v1.3.0) | 5 | 5 | New: predicts vulnerable probe categories from PromptAnalysisResult. Returns AttackSurface(risk_level/risk_score/total_exposed_probes/vectors). analyze-prompt --predict adds attack_surface to --json. Fully integrated with CLI and Python API. | 2026-07-10 |
| ResilienceProfile.to_dict() best_scenario (v1.3.0) | 5 | 5 | F-090 FIXED: to_dict() now includes best_scenario key alongside worst_scenario, weakest_metric, most_resilient_metric. Value is scenario name with least degradation. | 2026-07-10 |
| MultiAgentTrace.has_cycles() (v1.3.0) | 5 | 5 | F-077 FIXED: has_cycles() detects cyclic handoffs correctly; returns False for DAGs and empty traces; returns True for 2-node and 3-node cycles. | 2026-07-10 |
| MultiAgentTrace.get_children_by_agent() (v1.3.0) | 3 | 2 | New method: returns child runs by agent_id; correct when run_id explicitly set; F-149: silently returns [] when run_id=None (default). Users must always set explicit run_id. | 2026-07-10 |
| CassetteRecorder.record_response() (v1.3.0) | 5 | 5 | New simplified API: record_response(prompt, response) creates interaction without needing to build request/response objects manually. Integrates with ReplayEngine SEQUENCE correctly. | 2026-07-10 |
| upstream CI (session-072) | 5 | 5 | GREEN — all 3 latest runs success. Latest: "Add RQ3 safety probe detection experiment" (2026-07-10). Stable. | 2026-07-10 |
| MultiAgentTrace.get_children_by_agent() (session-073) | 5 | 5 | F-149 FIXED: AgentRun.run_id now auto-generates UUID by default — get_children_by_agent() works without manual UUID management. | 2026-07-14 |
| generate_targeted_probes (session-073) | 4 | 3 | New: bridges analyze-prompt to scan — maps failing checks to probe categories. Both function and TargetedProbeSet at top-level. F-150: TargetedProbeSet not iterable/filterable/sized — must do ProbeSet(targeted.probes) to use probe APIs. No CLI equivalent. | 2026-07-14 |
| upstream CI (session-073) | 1 | 1 | RED — "Add generate_targeted_probes" commit fails ruff lint (I001 unsorted imports, F841 unused variable). All 12 jobs fail before running tests. F-152. | 2026-07-14 |
| PyPI releases (session-073) | 1 | 1 | F-151: PyPI latest is v1.1.0 (2026-06-25). v1.2.0 and v1.3.0 not published. Users on pip install miss stress-prompt/ablate-prompt Python APIs, cassette fixes, predict_attack_surface. 19+ days behind. | 2026-07-14 |
| v1.4.0 PyPI release | 5 | 5 | F-151/F-152 FIXED: v1.4.0 published to PyPI 2026-07-15. F-150 (TargetedProbeSet protocol) also fixed. F-056 (LangChain dict final_output) fixed. CI green. | 2026-07-15 |
| generate_targeted_probes (session-074) | 5 | 4 | F-150 FIXED: TargetedProbeSet now fully implements ProbeSet protocol — iter/len/filter/__add__ all work. No CLI equivalent still (no --generate-probes flag on analyze-prompt). | 2026-07-15 |
| LangChainAdapter (session-074) | 5 | 4 | F-056 FIXED: final_output now extracts string from dict returns (same as output_text). Both 'output' key and first-value fallback work consistently. | 2026-07-15 |
| checkagent compare | 5 | 4 | F-153 FIXED (session-075): only_agent_a/only_agent_b now returns actual probe names (individual failing probe IDs) instead of ['']. More specific than category names. | 2026-07-16 |
| --generate-tests (session-074) | 5 | 5 | Enhanced in v1.4.0: now generates regression tests for passed probes AND xfail tests for current findings; xfail tests run cleanly; terminal shows counts. | 2026-07-15 |
| upstream CI (session-074) | 5 | 5 | GREEN — v1.4.0 "Bump version to 1.4.0" and "Fix ruff I001 + F841" pass all 12 platforms. F-152 resolved. Stable. | 2026-07-15 |
| scan --targeted | 4 | 3 | New (post-v1.4.0): reduces probe count for well-secured prompts (101→27 for 2-gap prompt); no reduction for gap-heavy prompts (102 vs 101); requires --prompt-file; clean error without it. F-154: DX gap — benefit depends on prompt quality, not documented. | 2026-07-16 |
| upstream CI (session-075) | 5 | 5 | GREEN — "Add --targeted flag to scan" passes all 12 platforms. Stable. | 2026-07-16 |
| --targeted + --llm-judge (compose) | 5 | 5 | Both flags compose cleanly: 27 probes, evaluator field in JSON, prompt_analysis key present, score 1.0 on refusal agent; no errors | 2026-07-17 |
| compare --url-a / --url-b | 5 | 4 | F-155 FIXED in v1.5.0: --url-a/--url-b now implemented; "No scan history" error is clear; no traceback; error goes to stdout not stderr (minor DX gap) | 2026-07-19 |
| compare score_delta semantics | 3 | 4 | F-156 IMPROVED: winner + margin fields added in v1.5.0; sign still undocumented (b-a, negative when a wins) but winner field + text "Winner:" line reduce confusion significantly | 2026-07-19 |
| upstream CI (session-076) | 5 | 5 | GREEN — "Add scan workflow guide: end-to-end safety hardening loop" passes all 3 latest runs. Docs-only commit. Stable. | 2026-07-17 |
| probe-list command | 5 | 5 | F-157 FIXED in v1.5.0: error message now shows "full_name (alias)" e.g. "prompt_injection (injection)". Both formats accepted. Fully consistent with JSON output. | 2026-07-19 |
| upstream CI (session-077) | 5 | 5 | GREEN — "Add probe-list command: show all safety probe categories with OWASP mapping" passes all 3 latest runs. Stable. | 2026-07-18 |
| upstream CI (session-078) | 2 | 2 | F-158: v1.5.0 bump commit fails ruff N806 (history.py:217 _DISPLAY uppercase in function). All 12 CI jobs fail. PyPI publish succeeded anyway — package published from red CI commit. | 2026-07-19 |
| v1.5.0 PyPI release | 4 | 4 | Published 2026-07-19. F-155/F-157 FIXED; winner+margin in compare. F-158: released from a CI-failing commit (ruff N806). Package works correctly despite the lint error. | 2026-07-19 |
| upstream CI (session-079) | 5 | 5 | F-158 FIXED: "Fix N806: rename _DISPLAY to _display" + "Add category delta to watch rescan" — both pass all 12 platforms. Green again. | 2026-07-20 |
| F-068 multiagent top-level exports (session-079) | 5 | 5 | FULLY FIXED: Handoff, assign_blame, BlameStrategy, BlameResult, top_blamed_agent all now at top-level checkagent alongside MultiAgentTrace and HandoffType. Complete. | 2026-07-20 |
| probe-list --verbose | 5 | 5 | F-160 FIXED in v1.6.0: --verbose + --examples no longer duplicates probe data; examples stays ≤3, probes has full list. Both flags work together cleanly now. | 2026-07-21 |
| scan per-category delta (terminal + JSON) | 5 | 5 | F-159 FIXED in v1.6.0: category_delta now in diff --json (top-level) and scan --diff --json (inside 'diff' key). Structure: {cat: {baseline, current, delta}}. Machine-readable. | 2026-07-21 |
| watch category delta | 5 | 4 | watch rescan now shows per-category change between scans; new commit "Add category delta to watch rescan". Can't test interactively in non-TTY environment. | 2026-07-20 |
| checkagent v1.6.0 upgrade | 5 | 5 | CI green on bump commit. F-159/F-160 both fixed. PyPI published 2026-07-21. Clean upgrade from 1.5.0. | 2026-07-21 |
