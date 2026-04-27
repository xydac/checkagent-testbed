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
| ap_fault mock integration | 5 | 4 | F-004 FIXED: attach_faults() wires FaultInjector into MockTool/MockLLM; ap_fault fixture added; second attach silently overwrites (F-079); was_triggered DX trap (F-078) | 2026-04-06 |
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
| AnthropicAdapter (basic run/error) | 4 | 3 | String input coercion works; error captured in AgentRun.error; duration_ms uses perf_counter; final_output is raw message object not string (F-062); anthropic undeclared dep (F-064) | 2026-04-06 |
| AnthropicAdapter.final_output | 2 | 2 | Raw Anthropic Message object — not string. Use step.output_text for text. Same pattern as F-056 but worse (opaque SDK object) | 2026-04-06 |
| CrewAIAdapter (basic run/error) | 4 | 3 | String input coercion works; final_output=result.raw (string — correct!); error captured; crewai undeclared dep (F-064) | 2026-04-06 |
| PydanticAIAdapter (basic run/error) | 4 | 3 | String input coercion works; final_output=result.data (correct); error captured; pydantic-ai undeclared dep (F-064) | 2026-04-06 |
| New adapters top-level exports | N/A | 1 | AnthropicAdapter, CrewAIAdapter, PydanticAIAdapter all absent from top-level checkagent (F-063). Ninth+ instance of pattern | 2026-04-06 |
| Adapter optional extras | 1 | 1 | anthropic/crewai/pydantic-ai not declared as optional extras — users can't pip install checkagent[anthropic] (F-064) | 2026-04-06 |
| checkagent.ci.junit_xml (JUnit XML) | 5 | 4 | render_junit_xml, from_run_summary, from_quality_gate_report all work; valid XML output; time_s aggregates correctly; gate verdicts map to failures/skipped correctly; accessible from checkagent.ci (good); not at top-level checkagent (F-065) | 2026-04-06 |
| JUnit XML from_run_summary | 5 | 4 | Synthetic mode creates generic test cases; test_details mode creates named cases with failure/skip support; integrates with RunSummary counts | 2026-04-06 |
| JUnit XML from_quality_gate_report | 5 | 5 | Blocked → failure, Warned → pass with property, Skipped → skipped; properties attached (actual/threshold/direction); clean mapping | 2026-04-06 |
| upstream CI (session-023) | 5 | 5 | Green for last 2 runs ("mark production trace import as complete", "mark all framework adapters"). Stable | 2026-04-06 |
| checkagent import-trace CLI | 4 | 4 | Solid: auto-detect JSON/JSONL/OTel, --filter-status, --limit, --tag, --no-pii-scrub, --source; friendly missing-file error; crashes with raw traceback on PII ID collision (F-066) | 2026-04-06 |
| JsonFileImporter | 5 | 4 | Handles flat, native (steps), span, and JSONL formats; filter by status; limit; not at top-level (F-067) | 2026-04-06 |
| OtelJsonImporter | 5 | 4 | Parses OTLP JSON correctly; groups by traceId; root span detection; tool spans from child names; error from status.code; not at top-level (F-067) | 2026-04-06 |
| PiiScrubber | 5 | 5 | Deterministic replacements; 5 built-in patterns (email/phone/SSN/CC/IP); extra_patterns; scrub_value for nested dicts/lists; reset() works correctly | 2026-04-06 |
| generate_test_cases | 3 | 1 | F-103: Breaking API change — returns tuple not GoldenDataset, `name=` renamed to `dataset_name=`, no deprecation. Existing code breaks silently. Safety screening useful but the migration story is terrible. | 2026-04-15 |
| TraceScreeningResult | 5 | 4 | New in 0.2.0 (safety screening commit): total/clean/flagged counts, findings_by_trace with SafetyFinding objects. Catches injection in traced outputs. Not at top-level. | 2026-04-15 |
| trace_import top-level exports | N/A | 1 | Eleventh instance of missing-top-level-export pattern (F-067) | 2026-04-06 |
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
| GroundednessEvaluator top-level export | N/A | 1 | Missing from top-level checkagent (F-107) — 13th instance of pattern; use from checkagent.safety import GroundednessEvaluator | 2026-04-17 |
| groundedness scan category | 5 | 5 | --category groundedness runs 8 probes (fabrication+uncertainty) with 0 errors; composable with ProbeSet; clean JSON output | 2026-04-17 |
| ToolBoundary dataclass | 4 | 3 | Clean config object; F-109 shim added; but forbidden_argument_patterns is dict[str,str] not set — confusing name causes AttributeError (F-111) | 2026-04-20 |
| PromptAnalysisResult.missing_high/missing_medium/recommendations | 5 | 5 | New properties in v0.3.0: filter failed checks by severity; recommendations returns actionable strings; all work correctly | 2026-04-19 |
| checkagent.wrap Python API | 5 | 4 | @wrap decorator and wrap(fn) both work cleanly; wrap(callable_instance) works; wrap(Class) with invoke() silently returns None — CLI handles class agents but Python API doesn't auto-detect invoke() | 2026-04-20 |
| upstream CI (session-041) | 5 | 5 | Green — all 12 jobs passing. Latest: "Fix F-109: add deprecation shim". 3 consecutive successes. | 2026-04-20 |
| wrap() Python API (framework agents) | 5 | 5 | F-112 FIXED: wrap() auto-detects PydanticAI Agent → PydanticAIAdapter, LangChain Runnable → LangChainAdapter; unrecognized non-callables get helpful TypeError listing adapters | 2026-04-22 |
| PydanticAI real agent end-to-end (session-043) | 5 | 5 | wrap(pydantic_ai.Agent) now works directly — auto-detects and returns PydanticAIAdapter with string final_output. No lambda workaround needed. | 2026-04-22 |
| ToolBoundary new API (non-deprecated) | 5 | 4 | Now at top-level checkagent (from checkagent import ToolBoundary). Deprecation migration path fully resolved. F-111 improved: set raises TypeError with clear dict format message | 2026-04-22 |
| upstream CI (session-043) | 5 | 5 | Green — latest "Fix F-112: wrap() auto-detects framework agents, add ToolBoundary top…" passes all platforms. 4 consecutive successes. | 2026-04-22 |
| ProbeSet.filter() tags case-sensitivity | 2 | 2 | F-113 NEW: tags are case-sensitive (indirect ≠ INDIRECT) while severity is case-insensitive. Inconsistent — users who learn severity is case-insensitive will be surprised. All tag values are lowercase. | 2026-04-22 |
| --llm-judge flag error handling | 5 | 5 | Clear, actionable error messages for both Anthropic (ANTHROPIC_API_KEY) and OpenAI (OPENAI_API_KEY) — no stack trace, correct env var name per model | 2026-04-23 |
| wrap() + PydanticAI structured output_type | 5 | 4 | wrap(Agent(output_type=Model)) auto-detects → PydanticAIAdapter; final_output is Pydantic model instance (not str). assert_output_schema and assert_json_schema(result.final_output, ...) both work correctly | 2026-04-23 |
| CrewAI adapter lazy import | 5 | 5 | Importable without crewai; raises ImportError with clear message ("requires crewai") at instantiation; wrap() TypeError lists CrewAIAdapter as option | 2026-04-23 |
| upstream CI (session-044) | 5 | 5 | Green — new ROADMAP-only commit today ("Add Phase 5"). No code changes. 5 consecutive successes. | 2026-04-24 |
| v0.3.0 PyPI gap | 1 | 1 | F-114: v0.3.0 not on PyPI — `pip install checkagent` gets 0.2.0. All 0.3.0 fixes (F-099/F-101/F-103/F-109/F-110/F-112) unavailable to first-time users. | 2026-04-24 |
| checkagent init (session-044) | 5 | 5 | Still works: generates 2-test project that passes immediately. Phase 5 end-to-end goal confirmed on git main. | 2026-04-24 |
| PromptAnalyzer scope_boundary patterns | 5 | 4 | New patterns (session-045): 'ONLY answer HR questions', 'your role is limited to', 'domain agent and only' all detected correctly; old patterns still work; DX: patterns are fully invisible to users (no docs listing what to write) | 2026-04-25 |
| upstream CI (session-045) | 5 | 5 | Green — new commit "Expand scope_boundary patterns to catch common real-world phrasings". 6 consecutive successes. | 2026-04-25 |
| check_behavioral_compliance (overall) | 4 | 3 | Core logic works: detects compliance via no-refusal + structural divergence; correctly skips scope-limiting refusals; importable from checkagent.safety; F-115 (severity not inherited from probe), F-116 (probe field empty), F-117 (not at top-level checkagent) | 2026-04-27 |
| behavioral baseline: refusal detection | 5 | 5 | 5 common refusal patterns all correctly return 0 findings; scope-limiting refusals pass cleanly after latest fix | 2026-04-27 |
| behavioral baseline: compliance detection | 4 | 3 | Detects structural divergence (bullets, tables, code blocks, length_anomaly) and basic no-refusal; short compliant responses missed (length bias); finding quality good | 2026-04-27 |
| upstream CI (session-046) | 5 | 5 | Green — 7 consecutive successes. "Fix behavioral detector false positive on scope-limiting refusals" passes all platforms. | 2026-04-27 |
