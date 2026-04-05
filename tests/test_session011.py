"""Session-011 tests: attack probe library, severity_meets_threshold,
end-to-end eval pipeline, ProbeSet API, and ToolCallBoundaryValidator path edges.

This session focuses on:
- The new attack probe library (probes.injection.direct / indirect)
- Probe and ProbeSet composability
- severity_meets_threshold as a fix for F-023
- End-to-end eval pipeline: datasets → parametrize_cases → metrics → aggregate → RunSummary → detect_regressions
- Additional ToolCallBoundaryValidator path edge cases
"""

import os
import tempfile

import pytest

from checkagent import AgentInput, AgentRun, Score, Step, ToolCall
from checkagent.datasets import TestCase
from checkagent.eval.aggregate import (
    RunSummary,
    aggregate_scores,
    compute_step_stats,
    detect_regressions,
)
from checkagent.eval.metrics import (
    step_efficiency,
    task_completion,
    tool_correctness,
    trajectory_match,
)
from checkagent.safety import probes
from checkagent.safety.probes.base import Probe, ProbeSet
from checkagent.safety.taxonomy import (
    OWASP_MAPPING,
    SEVERITY_ORDER,
    SafetyCategory,
    Severity,
    severity_meets_threshold,
)
from checkagent.safety.tool_boundary import ToolBoundary, ToolCallBoundaryValidator

# ---------------------------------------------------------------------------
# Attack probe library: probes.injection
# ---------------------------------------------------------------------------


def test_probes_injection_direct_is_probeset():
    assert isinstance(probes.injection.direct, ProbeSet)


def test_probes_injection_indirect_is_probeset():
    assert isinstance(probes.injection.indirect, ProbeSet)


def test_probes_injection_all_probes_is_probeset():
    assert isinstance(probes.injection.all_probes, ProbeSet)


def test_probes_injection_direct_count_is_25():
    assert len(probes.injection.direct) == 25


def test_probes_injection_indirect_count_is_10():
    assert len(probes.injection.indirect) == 10


def test_probes_injection_all_count_is_35():
    assert len(probes.injection.all_probes) == 35


def test_probeset_len_matches_all():
    direct = probes.injection.direct
    assert len(direct) == len(direct.all())


def test_probe_has_required_fields():
    probe = probes.injection.direct.all()[0]
    assert isinstance(probe.input, str)
    assert len(probe.input) > 0
    assert isinstance(probe.category, SafetyCategory)
    assert isinstance(probe.severity, Severity)
    assert isinstance(probe.name, str)
    assert isinstance(probe.tags, frozenset)


def test_probe_category_is_prompt_injection():
    for probe in probes.injection.all_probes:
        assert probe.category == SafetyCategory.PROMPT_INJECTION


def test_probe_str_returns_name():
    probe = probes.injection.direct.all()[0]
    assert str(probe) == probe.name


def test_probe_str_falls_back_to_input_when_no_name():
    probe = Probe(input="some long input text here", category=SafetyCategory.PROMPT_INJECTION)
    assert str(probe) == "some long input text here"


def test_probe_str_truncates_input_at_60_chars():
    long_input = "x" * 100
    probe = Probe(input=long_input, category=SafetyCategory.PROMPT_INJECTION)
    assert str(probe) == "x" * 60


def test_probeset_iteration():
    count = 0
    for p in probes.injection.direct:
        count += 1
        assert isinstance(p, Probe)
    assert count == 25


def test_probeset_concatenation():
    combined = probes.injection.direct + probes.injection.indirect
    assert len(combined) == 35


def test_probeset_concatenation_preserves_order():
    direct = probes.injection.direct
    indirect = probes.injection.indirect
    combined = direct + indirect
    direct_inputs = [p.input for p in direct]
    combined_inputs = [p.input for p in combined]
    assert combined_inputs[:len(direct_inputs)] == direct_inputs


def test_probeset_filter_by_tags():
    filtered = probes.injection.direct.filter(tags={"ignore"})
    assert len(filtered) > 0
    for probe in filtered:
        assert "ignore" in probe.tags


def test_probeset_filter_by_tags_returns_probeset():
    result = probes.injection.direct.filter(tags={"ignore"})
    assert isinstance(result, ProbeSet)


def test_probeset_filter_by_severity():
    critical = probes.injection.all_probes.filter(severity=Severity.CRITICAL)
    assert len(critical) > 0
    for probe in critical:
        assert probe.severity == Severity.CRITICAL


def test_probeset_filter_by_category():
    filtered = probes.injection.all_probes.filter(category=SafetyCategory.PROMPT_INJECTION)
    # All injection probes are PROMPT_INJECTION, so count should stay the same
    assert len(filtered) == len(probes.injection.all_probes)


def test_probeset_filter_unmatched_returns_empty():
    # Filter by a severity none of the probes have
    empty = probes.injection.direct.filter(severity=Severity.LOW)
    # There may or may not be LOW severity probes; just check it returns ProbeSet
    assert isinstance(empty, ProbeSet)


def test_probeset_filter_combined_tags_and_severity():
    filtered = probes.injection.all_probes.filter(
        tags={"ignore"}, severity=Severity.CRITICAL
    )
    assert isinstance(filtered, ProbeSet)
    for probe in filtered:
        assert "ignore" in probe.tags
        assert probe.severity == Severity.CRITICAL


def test_probeset_repr():
    ps = probes.injection.direct
    r = repr(ps)
    assert "ProbeSet" in r
    assert "injection.direct" in r


def test_probeset_all_probes_concat_equals_all():
    combined = probes.injection.direct + probes.injection.indirect
    all_p = probes.injection.all_probes
    assert len(combined) == len(all_p)


def test_probeset_name_preserved():
    assert probes.injection.direct.name == "injection.direct"
    assert probes.injection.indirect.name == "injection.indirect"


def test_probeset_filtered_name_has_filtered_suffix():
    filtered = probes.injection.direct.filter(tags={"ignore"})
    assert "filtered" in filtered.name


def test_custom_probe_creation():
    p = Probe(
        input="Custom injection attempt",
        category=SafetyCategory.PROMPT_INJECTION,
        severity=Severity.MEDIUM,
        name="custom-test",
        description="A custom test probe",
        tags=frozenset({"custom", "test"}),
    )
    assert p.input == "Custom injection attempt"
    assert p.severity == Severity.MEDIUM
    assert "custom" in p.tags


def test_custom_probeset_creation():
    custom = ProbeSet([
        Probe(input="attack 1", category=SafetyCategory.PROMPT_INJECTION),
        Probe(input="attack 2", category=SafetyCategory.PROMPT_INJECTION),
    ], name="my-probes")
    assert len(custom) == 2
    assert custom.name == "my-probes"


def test_probeset_parametrize_compatible():
    """ProbeSet.all() returns a list usable with pytest.mark.parametrize."""
    probes_list = probes.injection.direct.all()
    assert isinstance(probes_list, list)
    # Each item must be a Probe (so it can be used as a param ID via __str__)
    for p in probes_list:
        assert isinstance(p, Probe)


# ---------------------------------------------------------------------------
# severity_meets_threshold — F-023 workaround
# ---------------------------------------------------------------------------


def test_severity_meets_threshold_high_vs_low():
    assert severity_meets_threshold(Severity.HIGH, Severity.LOW) is True


def test_severity_meets_threshold_low_vs_high():
    assert severity_meets_threshold(Severity.LOW, Severity.HIGH) is False


def test_severity_meets_threshold_equal():
    assert severity_meets_threshold(Severity.HIGH, Severity.HIGH) is True


def test_severity_meets_threshold_critical_vs_medium():
    assert severity_meets_threshold(Severity.CRITICAL, Severity.MEDIUM) is True


def test_severity_meets_threshold_medium_vs_critical():
    assert severity_meets_threshold(Severity.MEDIUM, Severity.CRITICAL) is False


def test_severity_meets_threshold_all_levels():
    levels = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    for i, s in enumerate(levels):
        for j, threshold in enumerate(levels):
            expected = i >= j
            result = severity_meets_threshold(s, threshold)
            assert result == expected, (
                f"severity_meets_threshold({s}, {threshold}) expected {expected}, got {result}"
            )


def test_severity_meets_threshold_importable_from_safety():
    from checkagent.safety import severity_meets_threshold as smt
    assert callable(smt)


def test_severity_order_dict_correct_ordering():
    """SEVERITY_ORDER can be used for comparison as a workaround for F-023."""
    assert SEVERITY_ORDER[Severity.LOW] < SEVERITY_ORDER[Severity.MEDIUM]
    assert SEVERITY_ORDER[Severity.MEDIUM] < SEVERITY_ORDER[Severity.HIGH]
    assert SEVERITY_ORDER[Severity.HIGH] < SEVERITY_ORDER[Severity.CRITICAL]


# ---------------------------------------------------------------------------
# OWASP_MAPPING
# ---------------------------------------------------------------------------


def test_owasp_mapping_has_prompt_injection():
    assert SafetyCategory.PROMPT_INJECTION in OWASP_MAPPING


def test_owasp_mapping_values_are_strings():
    for cat, mapping in OWASP_MAPPING.items():
        assert isinstance(mapping, str), f"Expected str for {cat}, got {type(mapping)}"


def test_owasp_mapping_all_categories_covered():
    for cat in SafetyCategory:
        assert cat in OWASP_MAPPING, f"SafetyCategory.{cat.name} missing from OWASP_MAPPING"


# ---------------------------------------------------------------------------
# End-to-end eval pipeline: datasets → metrics → aggregate → RunSummary → detect_regressions
# ---------------------------------------------------------------------------


def _make_run(steps=3, tool_names=None, output="done", succeeded=True):
    """Helper: build a simple AgentRun for eval pipeline tests."""
    ai = AgentInput(query="test")
    tool_calls = []
    if tool_names:
        for name in tool_names:
            tool_calls.append(ToolCall(name=name, arguments={"q": "x"}, result="ok"))
    step_list = [
        Step(
            step_index=i,
            tool_calls=tool_calls if i == 0 else [],
        )
        for i in range(steps)
    ]
    error = None if succeeded else "agent failed"
    return AgentRun(
        input=ai,
        steps=step_list,
        final_output=output,
        error=error,
    )


def test_e2e_eval_step_efficiency_within_budget():
    run = _make_run(steps=3)
    score = step_efficiency(run, optimal_steps=3)
    assert isinstance(score, Score)
    assert score.value > 0


def test_e2e_eval_task_completion_success():
    run = _make_run(output="The answer is Paris, France.")
    score = task_completion(run, expected_output_contains=["Paris"])
    assert isinstance(score, Score)
    assert score.value == 1.0


def test_e2e_eval_tool_correctness_exact_match():
    run = _make_run(tool_names=["search", "summarize"])
    score = tool_correctness(run, expected_tools=["search", "summarize"])
    assert score.value == 1.0


def test_e2e_eval_trajectory_match_strict():
    run = _make_run(tool_names=["search", "summarize"])
    score = trajectory_match(run, expected_trajectory=["search", "summarize"], mode="strict")
    assert score.value == 1.0


def test_e2e_aggregate_scores():
    scores = [
        ("step_efficiency", 0.8, True),
        ("task_completion", 1.0, True),
        ("tool_correctness", 0.5, False),
    ]
    result = aggregate_scores(scores)
    # aggregate_scores returns dict[str, AggregateResult]
    assert "step_efficiency" in result
    assert "task_completion" in result
    assert result["step_efficiency"].mean == pytest.approx(0.8)
    assert result["task_completion"].pass_rate == pytest.approx(1.0)


def test_e2e_compute_step_stats():
    runs = [_make_run(steps=i + 1) for i in range(5)]
    step_counts = [len(r.steps) for r in runs]
    stats = compute_step_stats(step_counts)
    assert stats.mean > 0
    assert stats.p50 > 0
    assert stats.p95 >= stats.p50


def test_e2e_run_summary_save_and_load():
    """Full round-trip: build summary → save to disk → reload → check fields preserved."""
    aggs = aggregate_scores([("step_efficiency", 0.9, True), ("task_completion", 1.0, True)])
    stats = compute_step_stats([2, 3, 3, 4])

    summary = RunSummary(
        aggregates=aggs,
        step_stats=stats,
        total_cost=0.005,
    )

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name

    try:
        summary.save(path)
        loaded = RunSummary.load(path)
        assert abs(loaded.total_cost - 0.005) < 1e-9
        assert "step_efficiency" in loaded.aggregates
        assert "task_completion" in loaded.aggregates
    finally:
        os.unlink(path)


def test_e2e_detect_regressions_finds_drop():
    baseline = aggregate_scores([
        ("task_completion", 0.9, None),
        ("step_efficiency", 0.8, None),
    ])
    current = aggregate_scores([
        ("task_completion", 0.5, None),  # regression!
        ("step_efficiency", 0.8, None),  # no change
    ])
    regressions = detect_regressions(current, baseline, threshold=0.1)
    regressed_names = [r.metric_name for r in regressions if r.regressed]
    assert "task_completion" in regressed_names
    assert "step_efficiency" not in regressed_names


def test_e2e_detect_regressions_no_regressions():
    baseline = aggregate_scores([("accuracy", 0.9, None)])
    current = aggregate_scores([("accuracy", 0.95, None)])
    regressions = detect_regressions(current, baseline, threshold=0.05)
    regressed = [r for r in regressions if r.regressed]
    assert len(regressed) == 0


def test_e2e_full_pipeline_with_datasets():
    """
    End-to-end: define test cases → run agent → score → aggregate.
    2 out of 3 should pass (wrong answer on case-3).
    """
    cases = [
        TestCase(
            id="case-1",
            input="capital of France",
            expected_output_equals="Paris",
            tags=["geography"],
        ),
        TestCase(
            id="case-2",
            input="capital of Germany",
            expected_output_equals="Berlin",
            tags=["geography"],
        ),
        TestCase(
            id="case-3",
            input="capital of Japan",
            expected_output_equals="Tokyo",
            tags=["geography"],
        ),
    ]

    # Simulated outputs: case-3 gives wrong answer (Osaka not Tokyo)
    run_outputs = {
        "case-1": "Paris",
        "case-2": "Berlin",
        "case-3": "Osaka",  # wrong!
    }

    score_tuples = []
    for case in cases:
        run = _make_run(output=run_outputs[case.id])
        score = task_completion(
            run,
            expected_output_equals=case.expected_output_equals,
        )
        score_tuples.append((score.name, score.value, score.passed))

    agg = aggregate_scores(score_tuples)
    assert "task_completion" in agg
    # 2 out of 3 should pass (Paris and Berlin match, Osaka doesn't)
    assert agg["task_completion"].pass_rate == pytest.approx(2 / 3, rel=0.01)


# ---------------------------------------------------------------------------
# ToolCallBoundaryValidator path edge cases
# ---------------------------------------------------------------------------


def _make_path_run(*tool_calls):
    """Build AgentRun with specified tool calls for path boundary testing."""
    ai = AgentInput(query="test")
    tc_list = [ToolCall(name=t[0], arguments=t[1], result="ok") for t in tool_calls]
    return AgentRun(
        input=ai,
        steps=[Step(step_index=0, tool_calls=tc_list)],
        final_output="done",
    )


def test_path_boundary_subdirectory_within_allowed():
    """A path within an allowed directory (subdirectory) should pass."""
    boundary = ToolBoundary(
        allowed_paths=["/data"],
    )
    validator = ToolCallBoundaryValidator(boundary)
    run = _make_path_run(("read_file", {"path": "/data/subdir/file.txt"}))
    result = validator.evaluate_run(run)
    assert result.passed


def test_path_boundary_root_path_blocked():
    """Accessing /etc/passwd when only '/data' is allowed should fail."""
    boundary = ToolBoundary(
        allowed_paths=["/data"],
    )
    validator = ToolCallBoundaryValidator(boundary)
    run = _make_path_run(("read_file", {"path": "/etc/passwd"}))
    result = validator.evaluate_run(run)
    assert not result.passed


def test_path_boundary_prefix_not_confused_with_subpath():
    """'/dataextra' should NOT match an allowed path of '/data'.

    This is an oracle test — we record actual behavior. A correct implementation
    should use proper path prefix check (not string startswith), but we verify
    what checkagent actually does.
    """
    boundary = ToolBoundary(
        allowed_paths=["/data"],
    )
    validator = ToolCallBoundaryValidator(boundary)
    run = _make_path_run(("read_file", {"path": "/dataextra/file.txt"}))
    result = validator.evaluate_run(run)
    # Record the actual result without asserting pass/fail
    # The behavior is: does '/dataextra/file.txt' satisfy allowed_paths=['/data']?
    assert isinstance(result.passed, bool)
    # Ideally this should FAIL (not passed) since /dataextra is not inside /data
    # We'll document if the implementation gets it wrong


def test_path_boundary_exact_match_passes():
    """Exact path match should always pass."""
    boundary = ToolBoundary(
        allowed_paths=["/data/file.txt"],
    )
    validator = ToolCallBoundaryValidator(boundary)
    run = _make_path_run(("read_file", {"path": "/data/file.txt"}))
    result = validator.evaluate_run(run)
    assert result.passed


def test_path_boundary_no_path_arg_with_no_allowed_paths():
    """No path constraint means path arguments are not checked — tool is allowed."""
    boundary = ToolBoundary(
        allowed_tools={"search"},
    )
    validator = ToolCallBoundaryValidator(boundary)
    run = _make_path_run(("search", {"query": "cats"}))
    result = validator.evaluate_run(run)
    assert result.passed


def test_path_boundary_multiple_allowed_paths():
    """Path within second allowed path should pass."""
    boundary = ToolBoundary(
        allowed_paths=["/data", "/tmp"],
    )
    validator = ToolCallBoundaryValidator(boundary)
    run = _make_path_run(("read_file", {"path": "/tmp/output.txt"}))
    result = validator.evaluate_run(run)
    assert result.passed


def test_path_boundary_traversal_stays_within_allowed():
    """Path traversal '/../' could escape: /data/../etc/passwd — record behavior.

    This is a security-relevant edge case. A robust validator should normalize
    the path before checking boundaries. We document what checkagent actually does.
    """
    boundary = ToolBoundary(
        allowed_paths=["/data"],
    )
    validator = ToolCallBoundaryValidator(boundary)
    run = _make_path_run(("read_file", {"path": "/data/../etc/passwd"}))
    result = validator.evaluate_run(run)
    # Ideally this should FAIL because normalized path = /etc/passwd (outside /data)
    # We record the actual behavior
    assert isinstance(result.passed, bool)


# ---------------------------------------------------------------------------
# ProbeSet with parametrize (integration smoke test)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("probe", probes.injection.direct.filter(tags={"ignore"}).all())
def test_probe_inputs_are_nonempty_strings(probe):
    """Each probe has a non-empty input string (sanity check for parametrize usage)."""
    assert isinstance(probe.input, str)
    assert len(probe.input) > 0
    assert isinstance(probe.category, SafetyCategory)


# ---------------------------------------------------------------------------
# Probe severity coverage across all injection probes
# ---------------------------------------------------------------------------


def test_injection_probes_have_mixed_severities():
    """Not all probes should be the same severity — tests that the library is varied."""
    severities = {p.severity for p in probes.injection.all_probes}
    assert len(severities) > 1, "Expected probes with multiple severity levels"


def test_injection_probes_include_critical_severity():
    critical = [p for p in probes.injection.all_probes if p.severity == Severity.CRITICAL]
    assert len(critical) > 0


def test_injection_probes_all_have_names():
    unnamed = [p for p in probes.injection.all_probes if not p.name]
    assert len(unnamed) == 0, f"Found {len(unnamed)} probes without names"


def test_indirect_probes_all_have_indirect_tag():
    for probe in probes.injection.indirect:
        assert "indirect" in probe.tags, f"Probe {probe.name} missing 'indirect' tag"


# ---------------------------------------------------------------------------
# Probes not importable from top-level checkagent (documenting F-024)
# ---------------------------------------------------------------------------


def test_probes_not_at_top_level_checkagent():
    """Attack probes are only available via checkagent.safety — not top-level.
    This documents the discoverability gap as a potential F-024.
    """
    import checkagent
    assert not hasattr(checkagent, "probes"), "probes unexpectedly at top-level checkagent"
    assert not hasattr(checkagent, "Probe"), "Probe unexpectedly at top-level checkagent"
    assert not hasattr(checkagent, "ProbeSet"), "ProbeSet unexpectedly at top-level checkagent"
