"""
Session 013 — CI quality gates, ProbeSet AND logic, task_completion expected_output_equals,
generate_pr_comment, RunSummary collision, edge cases.

Upgraded from: 27d4af4 → 735700f
New feature: checkagent.ci — quality gates, PR reporter
"""

import pytest
from checkagent import AgentInput, AgentRun, Score
from checkagent.ci import (
    GateResult,
    GateVerdict,
    QualityGateReport,
    RunSummary as CiRunSummary,
    evaluate_gate,
    evaluate_gates,
    generate_pr_comment,
    scores_to_dict,
)
from checkagent.ci.quality_gate import QualityGateEntry
from checkagent.ci.reporter import generate_pr_comment as reporter_generate_pr_comment
from checkagent.eval.aggregate import RunSummary as EvalRunSummary
from checkagent.eval.metrics import task_completion
from checkagent.safety.probes import injection, jailbreak, pii, scope


# ---------------------------------------------------------------------------
# CI quality gates — core evaluate_gate
# ---------------------------------------------------------------------------


class TestEvaluateGate:
    def test_min_gate_pass(self):
        entry = QualityGateEntry(min=0.8, on_fail="block")
        r = evaluate_gate("task_completion", 0.9, entry)
        assert r.verdict == GateVerdict.PASSED
        assert r.actual == 0.9
        assert r.threshold == 0.8

    def test_min_gate_exact_boundary_passes(self):
        entry = QualityGateEntry(min=0.8, on_fail="block")
        r = evaluate_gate("task_completion", 0.8, entry)
        assert r.verdict == GateVerdict.PASSED

    def test_min_gate_fail_block(self):
        entry = QualityGateEntry(min=0.8, on_fail="block")
        r = evaluate_gate("task_completion", 0.7, entry)
        assert r.verdict == GateVerdict.BLOCKED
        assert "0.7000" in r.message
        assert "0.8000" in r.message

    def test_min_gate_fail_warn(self):
        entry = QualityGateEntry(min=0.8, on_fail="warn")
        r = evaluate_gate("task_completion", 0.5, entry)
        assert r.verdict == GateVerdict.WARNED

    def test_min_gate_fail_ignore(self):
        # on_fail='ignore' should produce SKIPPED, not BLOCKED
        entry = QualityGateEntry(min=0.8, on_fail="ignore")
        r = evaluate_gate("task_completion", 0.5, entry)
        assert r.verdict == GateVerdict.SKIPPED

    def test_max_gate_pass(self):
        entry = QualityGateEntry(max=0.5, on_fail="block")
        r = evaluate_gate("latency", 0.3, entry)
        assert r.verdict == GateVerdict.PASSED

    def test_max_gate_fail(self):
        entry = QualityGateEntry(max=0.5, on_fail="block")
        r = evaluate_gate("latency", 0.7, entry)
        assert r.verdict == GateVerdict.BLOCKED
        assert "0.7000 > max 0.5000" in r.message

    def test_range_gate_in_range(self):
        entry = QualityGateEntry(min=0.3, max=0.8, on_fail="block")
        r = evaluate_gate("metric", 0.5, entry)
        assert r.verdict == GateVerdict.PASSED

    def test_range_gate_above_max(self):
        entry = QualityGateEntry(min=0.3, max=0.8, on_fail="block")
        r = evaluate_gate("metric", 0.9, entry)
        assert r.verdict == GateVerdict.BLOCKED

    def test_range_gate_below_min(self):
        entry = QualityGateEntry(min=0.3, max=0.8, on_fail="block")
        r = evaluate_gate("metric", 0.2, entry)
        assert r.verdict == GateVerdict.BLOCKED

    def test_no_min_max_always_passes(self):
        # FINDING: QualityGateEntry() with no min/max silently passes everything
        # This could be a misconfiguration trap
        entry = QualityGateEntry(on_fail="block")
        r = evaluate_gate("metric", 0.0, entry)
        assert r.verdict == GateVerdict.PASSED

    def test_invalid_on_fail_raises(self):
        with pytest.raises(Exception, match="Invalid on_fail"):
            QualityGateEntry(min=0.8, on_fail="explode")


# ---------------------------------------------------------------------------
# evaluate_gates — dict of gates
# ---------------------------------------------------------------------------


class TestEvaluateGates:
    def test_all_pass(self):
        gates = {
            "task_completion": QualityGateEntry(min=0.8, on_fail="block"),
            "step_efficiency": QualityGateEntry(min=0.5, on_fail="warn"),
        }
        scores = {"task_completion": 0.95, "step_efficiency": 0.8}
        report = evaluate_gates(scores, gates)
        assert report.passed is True
        assert len(report.results) == 2
        assert all(r.verdict == GateVerdict.PASSED for r in report.results)

    def test_one_blocked(self):
        gates = {
            "task_completion": QualityGateEntry(min=0.8, on_fail="block"),
            "step_efficiency": QualityGateEntry(min=0.5, on_fail="warn"),
        }
        scores = {"task_completion": 0.6, "step_efficiency": 0.8}
        report = evaluate_gates(scores, gates)
        assert report.passed is False
        assert len(report.blocked_gates) == 1
        assert report.blocked_gates[0].metric == "task_completion"

    def test_warned_does_not_block(self):
        gates = {
            "step_efficiency": QualityGateEntry(min=0.5, on_fail="warn"),
        }
        scores = {"step_efficiency": 0.3}
        report = evaluate_gates(scores, gates)
        assert report.passed is True  # warnings don't block
        assert report.has_warnings is True
        assert len(report.warned_gates) == 1

    def test_missing_metric_is_skipped(self):
        gates = {
            "task_completion": QualityGateEntry(min=0.8, on_fail="block"),
            "nonexistent": QualityGateEntry(min=0.5, on_fail="block"),
        }
        scores = {"task_completion": 0.9}
        report = evaluate_gates(scores, gates)
        metrics_by_name = {r.metric: r for r in report.results}
        assert metrics_by_name["nonexistent"].verdict == GateVerdict.SKIPPED
        assert report.passed is True  # SKIPPED doesn't block


# ---------------------------------------------------------------------------
# QualityGateReport properties
# ---------------------------------------------------------------------------


class TestQualityGateReport:
    def _make_report(self):
        return QualityGateReport(
            results=[
                GateResult("m1", GateVerdict.PASSED, 0.95, 0.8),
                GateResult("m2", GateVerdict.WARNED, 0.45, 0.5, message="below threshold"),
                GateResult("m3", GateVerdict.BLOCKED, 0.6, 0.9, message="gate blocked"),
                GateResult("m4", GateVerdict.SKIPPED),
            ]
        )

    def test_passed_false_when_blocked(self):
        assert self._make_report().passed is False

    def test_passed_gates_list(self):
        passed = self._make_report().passed_gates
        assert len(passed) == 1
        assert passed[0].metric == "m1"

    def test_blocked_gates_list(self):
        blocked = self._make_report().blocked_gates
        assert len(blocked) == 1
        assert blocked[0].metric == "m3"

    def test_warned_gates_list(self):
        warned = self._make_report().warned_gates
        assert len(warned) == 1
        assert warned[0].metric == "m2"

    def test_has_warnings_true(self):
        assert self._make_report().has_warnings is True

    def test_has_warnings_false_when_no_warnings(self):
        report = QualityGateReport(
            results=[
                GateResult("m1", GateVerdict.PASSED, 0.9, 0.8),
                GateResult("m2", GateVerdict.BLOCKED, 0.5, 0.8),
            ]
        )
        assert report.has_warnings is False

    def test_passed_true_when_only_warnings(self):
        report = QualityGateReport(
            results=[GateResult("m1", GateVerdict.WARNED, 0.4, 0.5)]
        )
        assert report.passed is True


# ---------------------------------------------------------------------------
# GateVerdict enum
# ---------------------------------------------------------------------------


class TestGateVerdict:
    def test_all_verdicts(self):
        verdicts = {v.value for v in GateVerdict}
        assert verdicts == {"passed", "warned", "blocked", "skipped"}

    def test_verdict_string_values(self):
        assert GateVerdict.PASSED.value == "passed"
        assert GateVerdict.BLOCKED.value == "blocked"
        assert GateVerdict.WARNED.value == "warned"
        assert GateVerdict.SKIPPED.value == "skipped"


# ---------------------------------------------------------------------------
# scores_to_dict
# ---------------------------------------------------------------------------


class TestScoresToDict:
    def test_converts_score_list(self):
        scores = [
            Score(name="task_completion", value=0.9, threshold=0.8),
            Score(name="step_efficiency", value=0.6, threshold=0.5),
        ]
        d = scores_to_dict(scores)
        assert d == {"task_completion": 0.9, "step_efficiency": 0.6}

    def test_empty_list(self):
        assert scores_to_dict([]) == {}

    def test_pipeline_scores_to_gates(self):
        scores = [
            Score(name="task_completion", value=0.95, threshold=0.8),
            Score(name="tool_correctness", value=0.7, threshold=0.9),
        ]
        gates = {
            "task_completion": QualityGateEntry(min=0.8, on_fail="block"),
            "tool_correctness": QualityGateEntry(min=0.9, on_fail="block"),
        }
        report = evaluate_gates(scores_to_dict(scores), gates)
        assert len(report.blocked_gates) == 1
        assert report.blocked_gates[0].metric == "tool_correctness"


# ---------------------------------------------------------------------------
# generate_pr_comment
# ---------------------------------------------------------------------------


class TestGeneratePrComment:
    def test_title_in_output(self):
        comment = generate_pr_comment(title="My Report")
        assert "## My Report" in comment

    def test_default_title(self):
        comment = generate_pr_comment()
        assert "## CheckAgent Test Report" in comment

    def test_no_args_produces_minimal_output(self):
        comment = generate_pr_comment()
        # Minimal but valid Markdown — no error
        assert "---" in comment

    def test_with_test_summary(self):
        summary = CiRunSummary(total=20, passed=18, failed=2, duration_s=5.2)
        comment = generate_pr_comment(test_summary=summary)
        assert "| Total tests | 20 |" in comment
        assert "| Passed | 18 |" in comment
        assert "| Failed | 2 |" in comment
        assert "90.0%" in comment  # pass rate

    def test_with_gate_report_all_pass(self):
        report = QualityGateReport(
            results=[GateResult("task_completion", GateVerdict.PASSED, 0.95, 0.8)]
        )
        comment = generate_pr_comment(gate_report=report)
        assert "| task_completion |" in comment
        assert ":white_check_mark:" in comment

    def test_with_gate_report_blocked(self):
        report = QualityGateReport(
            results=[GateResult("tool_correctness", GateVerdict.BLOCKED, 0.6, 0.9)]
        )
        comment = generate_pr_comment(gate_report=report)
        assert ":x:" in comment
        assert "blocked" in comment.lower()

    def test_status_line_shows_blocked_count(self):
        report = QualityGateReport(
            results=[
                GateResult("m1", GateVerdict.BLOCKED, 0.5, 0.8),
                GateResult("m2", GateVerdict.BLOCKED, 0.4, 0.7),
            ]
        )
        comment = generate_pr_comment(gate_report=report)
        assert "2 quality gate(s) blocked" in comment

    def test_generated_by_footer(self):
        comment = generate_pr_comment()
        assert "CheckAgent" in comment
        # Footer always present
        assert "---" in comment


# ---------------------------------------------------------------------------
# CiRunSummary
# ---------------------------------------------------------------------------


class TestCiRunSummary:
    def test_basic_fields(self):
        s = CiRunSummary(total=10, passed=8, failed=1, skipped=1, errors=0, duration_s=2.5)
        assert s.total == 10
        assert s.passed == 8
        assert s.failed == 1

    def test_pass_rate(self):
        s = CiRunSummary(total=10, passed=9)
        assert s.pass_rate == pytest.approx(0.9)

    def test_pass_rate_zero_total(self):
        s = CiRunSummary(total=0)
        assert s.pass_rate == 0.0

    def test_to_dict(self):
        s = CiRunSummary(total=5, passed=4)
        d = s.to_dict()
        assert isinstance(d, dict)


# ---------------------------------------------------------------------------
# F-029: RunSummary name collision — ci vs eval
# ---------------------------------------------------------------------------


class TestRunSummaryCollision:
    def test_ci_and_eval_runsummary_are_different_types(self):
        """F-029: Two incompatible RunSummary classes exist with the same name."""
        assert CiRunSummary is not EvalRunSummary

    def test_ci_runsummary_has_pass_counts(self):
        s = CiRunSummary(total=10, passed=8)
        assert hasattr(s, "total")
        assert hasattr(s, "passed")

    def test_eval_runsummary_has_aggregates(self):
        s = EvalRunSummary()
        assert hasattr(s, "save")
        assert hasattr(s, "load")
        assert not hasattr(s, "total")

    def test_passing_eval_runsummary_to_generate_pr_comment_raises(self):
        """Passing the wrong RunSummary to generate_pr_comment raises AttributeError."""
        eval_summary = EvalRunSummary()
        with pytest.raises(AttributeError):
            generate_pr_comment(test_summary=eval_summary)


# ---------------------------------------------------------------------------
# F-030: QualityGateEntry not in checkagent.ci.__all__
# ---------------------------------------------------------------------------


class TestQualityGateEntryExports:
    def test_qualitygatentry_not_in_ci_all(self):
        """F-030: QualityGateEntry is required to use CI gates but not in ci.__all__."""
        import checkagent.ci as ci
        assert "QualityGateEntry" not in ci.__all__

    def test_qualitygatentry_not_accessible_as_ci_attribute(self):
        import checkagent.ci as ci
        assert not hasattr(ci, "QualityGateEntry")

    def test_qualitygatentry_accessible_from_submodule(self):
        from checkagent.ci.quality_gate import QualityGateEntry as QGE
        assert QGE is not None


# ---------------------------------------------------------------------------
# F-028: checkagent.ci not in top-level checkagent namespace
# ---------------------------------------------------------------------------


class TestCIModuleTopLevel:
    def test_ci_not_in_top_level_checkagent(self):
        """F-028: checkagent.ci module and its classes aren't exported from top-level."""
        import checkagent
        assert not hasattr(checkagent, "QualityGateReport")
        assert not hasattr(checkagent, "GateResult")
        assert not hasattr(checkagent, "evaluate_gates")
        assert not hasattr(checkagent, "generate_pr_comment")

    def test_ci_accessible_as_submodule(self):
        from checkagent import ci
        assert hasattr(ci, "evaluate_gates")
        assert hasattr(ci, "generate_pr_comment")


# ---------------------------------------------------------------------------
# ProbeSet chained filter for AND logic
# ---------------------------------------------------------------------------


class TestProbeSetChainedFilter:
    def test_single_filter_returns_matching_probes(self):
        jb = jailbreak.all_probes
        result = jb.filter(tags={"roleplay"})
        assert all("roleplay" in p.tags for p in result)

    def test_chained_filter_achieves_and_logic(self):
        """Chaining .filter() achieves AND logic (single call is OR)."""
        jb = jailbreak.all_probes
        and_result = jb.filter(tags={"roleplay"}).filter(tags={"persona"})
        or_result = jb.filter(tags={"roleplay", "persona"})
        # AND is a subset of OR
        assert len(and_result) < len(or_result)
        # All AND results have BOTH tags
        for p in and_result:
            assert "roleplay" in p.tags
            assert "persona" in p.tags

    def test_chained_filter_cross_dimension(self):
        """Can chain filter on different dimensions (tags then severity)."""
        jb = jailbreak.all_probes
        result = jb.filter(tags={"roleplay"}).filter(severity="critical")
        for p in result:
            assert "roleplay" in p.tags
            assert p.severity.value == "critical"

    def test_chained_filter_is_idempotent_on_same_tag(self):
        jb = jailbreak.all_probes
        single = jb.filter(tags={"roleplay"})
        double = jb.filter(tags={"roleplay"}).filter(tags={"roleplay"})
        assert len(single) == len(double)

    def test_combined_all_probes_chained_filter(self):
        """AND filter across combined probeset works (use all_probes, not all())."""
        # NOTE: .all() returns a list; use .all_probes for ProbeSet operations
        all_probes = injection.all_probes + jailbreak.all_probes + pii.all_probes + scope.all_probes
        critical_injection = all_probes.filter(severity="critical").filter(
            tags={"ignore"}
        )
        for p in critical_injection:
            assert p.severity.value == "critical"
            assert "ignore" in p.tags


# ---------------------------------------------------------------------------
# ProbeSet parametrize compatibility
# ---------------------------------------------------------------------------


class TestProbeSetParametrize:
    def test_probeset_is_iterable(self):
        probes = injection.direct.filter(severity="critical")
        items = list(probes)
        assert len(items) > 0

    def test_probeset_has_len(self):
        probes = injection.direct.all()
        assert len(probes) == 25

    def test_probe_str_returns_name(self):
        """str(probe) returns probe.name — ideal for pytest parametrize IDs."""
        probes = list(injection.direct.all())
        for p in probes[:5]:
            assert str(p) == p.name

    def test_probe_name_is_pytest_friendly(self):
        """Probe names use hyphens and lowercase — valid pytest param IDs."""
        for p in injection.direct.all():
            # pytest param IDs can't have spaces or special chars
            assert " " not in p.name
            assert p.name == p.name.lower() or "-" in p.name

    @pytest.mark.parametrize("probe", list(injection.direct.filter(severity="critical")))
    def test_parametrize_direct_critical_probes(self, probe):
        """ProbeSet can be passed directly to pytest.mark.parametrize via list()."""
        assert probe.input  # probe has non-empty input
        assert probe.severity.value == "critical"
        assert probe.category is not None


# ---------------------------------------------------------------------------
# task_completion with expected_output_equals
# ---------------------------------------------------------------------------


class TestTaskCompletionEquals:
    def _run(self, output):
        return AgentRun(input=AgentInput(query="test"), final_output=output)

    def test_exact_match_passes(self):
        r = task_completion(self._run("The answer is 42"), expected_output_equals="The answer is 42")
        assert r.value == pytest.approx(1.0)
        assert r.passed is True

    def test_case_sensitive(self):
        """expected_output_equals is case-sensitive — 'hello' != 'Hello'."""
        r = task_completion(self._run("The answer is 42"), expected_output_equals="the answer is 42")
        assert r.passed is False

    def test_partial_substring_does_not_match(self):
        """expected_output_equals requires full match — '42' != 'The answer is 42'."""
        r = task_completion(self._run("The answer is 42"), expected_output_equals="42")
        assert r.passed is False

    def test_empty_string_matches_empty_output(self):
        r = task_completion(self._run(""), expected_output_equals="")
        assert r.passed is True

    def test_nonmatching_string_fails(self):
        r = task_completion(self._run("Paris"), expected_output_equals="London")
        assert r.passed is False

    def test_none_output_falsely_equals_empty_string(self):
        """F-031 FIXED: None != '' now correctly treated as False."""
        r = task_completion(self._run(None), expected_output_equals="")
        assert r.passed is False

    def test_none_output_does_not_equal_nonempty_string(self):
        r = task_completion(self._run(None), expected_output_equals="hello")
        assert r.passed is False

    def test_equals_and_contains_can_be_combined(self):
        """Both expected_output_equals and expected_output_contains can be used together."""
        run = self._run("The answer is 42")
        r = task_completion(
            run,
            expected_output_equals="The answer is 42",
            expected_output_contains="42",
        )
        assert r.passed is True
        # metadata.checks should have entries for both
        assert len(r.metadata["checks"]) >= 2

    def test_error_run_fails_equals(self):
        run = AgentRun(
            input=AgentInput(query="test"),
            final_output=None,
            error="LLM failed",
        )
        r = task_completion(run, expected_output_equals="something")
        assert r.passed is False
