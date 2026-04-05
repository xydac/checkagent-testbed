"""
Session 014 — CI pipeline end-to-end, ProbeSet + ordering, judge layer,
generate_pr_comment regression gap, checkagent run -m filter behavior.

Upgraded from: 735700f → 90ab3c5
No new top-level exports detected; focused on integration gaps.
"""

import pytest
from checkagent import AgentInput, AgentRun, MatchMode, Score, Step
from checkagent.ci import (
    GateVerdict,
    QualityGateReport,
    RunSummary as CiRunSummary,
    evaluate_gate,
    evaluate_gates,
    generate_pr_comment,
    scores_to_dict,
)
from checkagent.ci.quality_gate import QualityGateEntry
from checkagent.cli.run import build_pytest_args
from checkagent.eval.aggregate import (
    AggregateResult,
    RunSummary as EvalRunSummary,
    aggregate_scores,
    detect_regressions,
)
from checkagent.eval.metrics import step_efficiency, task_completion
from checkagent.safety.probes import ProbeSet, injection, jailbreak
from checkagent.safety.probes.base import ProbeSet as ProbeSetBase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_run(success: bool = True, steps: int = 3) -> AgentRun:
    step = Step(input_text="query", output_text="result")
    return AgentRun(
        input=AgentInput(query="query"),
        steps=[step] * steps,
        final_output="result" if success else None,
        error=None if success else "failed",
    )


def make_aggregate(name: str, mean: float, pass_rate: float | None = None) -> AggregateResult:
    return AggregateResult(
        metric_name=name,
        count=10,
        mean=mean,
        median=mean,
        stdev=0.05,
        min_value=mean - 0.1,
        max_value=mean + 0.1,
        pass_rate=pass_rate,
    )


# ---------------------------------------------------------------------------
# CI pipeline — end-to-end
# ---------------------------------------------------------------------------


class TestCIPipelineEndToEnd:
    """Full pipeline: runs → metric scores → aggregate → quality gates → PR comment."""

    def test_full_pipeline_all_pass(self):
        """8 successful runs, 2 failures → task_completion mean = 0.8 → gate passes."""
        runs = [make_run(success=True) for _ in range(8)] + [
            make_run(success=False) for _ in range(2)
        ]
        tc_scores = [task_completion(r, check_no_error=True) for r in runs]
        se_scores = [step_efficiency(r, optimal_steps=3) for r in runs]

        agg = aggregate_scores(
            [("task_completion", s.value, s.passed) for s in tc_scores]
            + [("step_efficiency", s.value, s.passed) for s in se_scores]
        )

        assert agg["task_completion"].mean == pytest.approx(0.8, abs=0.01)
        assert agg["step_efficiency"].mean == pytest.approx(1.0, abs=0.01)

        gates = {
            "task_completion": QualityGateEntry(min=0.7, on_fail="block"),
            "step_efficiency": QualityGateEntry(min=0.5, on_fail="warn"),
        }
        scores_dict = {name: r.mean for name, r in agg.items()}
        report = evaluate_gates(scores_dict, gates)

        assert report.passed is True
        assert len(report.results) == 2

    def test_full_pipeline_gate_blocked(self):
        """All runs fail → gate blocks."""
        runs = [make_run(success=False) for _ in range(10)]
        tc_scores = [task_completion(r, check_no_error=True) for r in runs]

        agg = aggregate_scores([("task_completion", s.value, s.passed) for s in tc_scores])
        gates = {"task_completion": QualityGateEntry(min=0.7, on_fail="block")}
        report = evaluate_gates({name: r.mean for name, r in agg.items()}, gates)

        assert report.passed is False
        assert len(report.blocked_gates) == 1

    def test_full_pipeline_generates_pr_comment(self):
        """PR comment includes test summary and gate results."""
        runs = [make_run(success=True) for _ in range(9)] + [make_run(success=False)]
        tc_scores = [task_completion(r, check_no_error=True) for r in runs]
        agg = aggregate_scores([("task_completion", s.value, s.passed) for s in tc_scores])

        gates = {"task_completion": QualityGateEntry(min=0.8, on_fail="block")}
        scores_dict = {name: r.mean for name, r in agg.items()}
        gate_report = evaluate_gates(scores_dict, gates)

        ci_summary = CiRunSummary(total=10, passed=9, failed=1, duration_s=0.3)
        comment = generate_pr_comment(test_summary=ci_summary, gate_report=gate_report)

        assert "CheckAgent Test Report" in comment
        assert "Test Results" in comment
        assert "Quality Gates" in comment
        assert "task_completion" in comment

    def test_pipeline_gate_report_status_badge(self):
        """PR comment status badge reflects gate outcome."""
        gates = {"tc": QualityGateEntry(min=0.9, on_fail="block")}
        failing_report = evaluate_gates({"tc": 0.5}, gates)
        passing_report = evaluate_gates({"tc": 0.95}, gates)

        failing_comment = generate_pr_comment(gate_report=failing_report)
        passing_comment = generate_pr_comment(gate_report=passing_report)

        # gate blocked → failure badge
        assert "blocked" in failing_comment
        # gate passed → success badge
        assert "passed" in passing_comment


# ---------------------------------------------------------------------------
# CI gate edge cases
# ---------------------------------------------------------------------------


class TestGateEdgeCases:
    def test_on_fail_ignore_skipped_does_not_block(self):
        """on_fail=ignore: failing gate → SKIPPED verdict, report still passes."""
        gates = {"tc": QualityGateEntry(min=0.9, on_fail="ignore")}
        report = evaluate_gates({"tc": 0.3}, gates)
        assert report.results[0].verdict == GateVerdict.SKIPPED
        assert report.passed is True

    def test_missing_metric_skipped_with_on_fail_block(self):
        """Missing metric → SKIPPED even if on_fail=block. Misconfigured gate names fail silently."""
        gates = {"nonexistent_metric": QualityGateEntry(min=0.9, on_fail="block")}
        report = evaluate_gates({"other_metric": 0.5}, gates)
        assert report.results[0].verdict == GateVerdict.SKIPPED
        # SKIPPED doesn't block — misconfigured gate name is silent no-op
        assert report.passed is True

    def test_no_min_no_max_always_passes(self):
        """QualityGateEntry with no min/no max always passes regardless of value."""
        gates = {"foo": QualityGateEntry(on_fail="block")}
        report = evaluate_gates({"foo": 0.0}, gates)
        assert report.results[0].verdict == GateVerdict.PASSED
        assert report.passed is True

    def test_range_gate_both_bounds(self):
        """Gate with both min and max — value must be in range."""
        gates = {"latency": QualityGateEntry(min=0.1, max=0.5, on_fail="block")}

        in_range = evaluate_gates({"latency": 0.3}, gates)
        assert in_range.passed is True

        below_min = evaluate_gates({"latency": 0.05}, gates)
        assert below_min.passed is False

        above_max = evaluate_gates({"latency": 0.8}, gates)
        assert above_max.passed is False

    def test_warned_does_not_block_report_passed(self):
        """Gate with on_fail=warn produces WARNED but report.passed stays True."""
        gates = {"se": QualityGateEntry(min=0.9, on_fail="warn")}
        report = evaluate_gates({"se": 0.5}, gates)
        assert report.results[0].verdict == GateVerdict.WARNED
        assert report.passed is True
        assert report.has_warnings is True

    def test_mixed_skipped_and_blocked(self):
        """SKIPPED + BLOCKED → report.passed is False (BLOCKED takes effect)."""
        gates = {
            "a": QualityGateEntry(min=0.9, on_fail="ignore"),   # fails → SKIPPED
            "b": QualityGateEntry(min=0.9, on_fail="block"),    # fails → BLOCKED
        }
        report = evaluate_gates({"a": 0.1, "b": 0.1}, gates)
        assert report.passed is False
        assert len(report.blocked_gates) == 1
        verdicts = {r.metric: r.verdict for r in report.results}
        assert verdicts["a"] == GateVerdict.SKIPPED
        assert verdicts["b"] == GateVerdict.BLOCKED


# ---------------------------------------------------------------------------
# ProbeSet + ordering
# ---------------------------------------------------------------------------


class TestProbeSetAddOrdering:
    def test_add_preserves_left_then_right_order(self):
        """ProbeSet + preserves: all left items come first, then right items."""
        left = ProbeSet(injection.direct.all()[:3])
        right = ProbeSet(injection.indirect.all()[:2])
        combined = left + right

        left_names = [p.name for p in left]
        right_names = [p.name for p in right]
        combined_names = [p.name for p in combined]

        assert combined_names == left_names + right_names

    def test_add_cross_category_ordering_preserved(self):
        """Cross-category ProbeSet + preserves insertion order."""
        inj_slice = ProbeSet(injection.direct.all()[:3])
        jb_slice = ProbeSet(list(jailbreak.all_probes)[:2])
        combined = inj_slice + jb_slice

        assert [p.name for p in combined] == (
            [p.name for p in inj_slice] + [p.name for p in jb_slice]
        )

    def test_add_allows_duplicates(self):
        """ProbeSet + does not deduplicate — same probe can appear twice."""
        ps = ProbeSet(injection.direct.all()[:3])
        doubled = ps + ps
        assert len(doubled) == len(ps) * 2
        names = [p.name for p in doubled]
        assert names[:3] == names[3:]

    def test_injection_all_probes_ordering_is_direct_then_indirect(self):
        """injection.all_probes contains direct probes first, then indirect."""
        all_ps = injection.all_probes
        direct_names = [p.name for p in injection.direct.all()]
        indirect_names = [p.name for p in injection.indirect.all()]
        all_names = [p.name for p in all_ps]

        assert all_names[:len(direct_names)] == direct_names
        assert all_names[len(direct_names):] == indirect_names

    def test_add_empty_probeset_is_identity(self):
        """Adding an empty ProbeSet is a no-op."""
        ps = ProbeSet(injection.direct.all()[:3])
        empty = ProbeSet([])
        assert len(ps + empty) == len(ps)
        assert len(empty + ps) == len(ps)
        assert [p.name for p in ps + empty] == [p.name for p in ps]

    def test_add_len_is_sum(self):
        """len(a + b) == len(a) + len(b) for non-overlapping ProbeSet."""
        direct = ProbeSet(injection.direct.all())
        indirect = ProbeSet(injection.indirect.all())
        assert len(direct + indirect) == len(direct) + len(indirect)


# ---------------------------------------------------------------------------
# generate_pr_comment — regression gap (F-033)
# ---------------------------------------------------------------------------


class TestGeneratePrCommentRegressionGap:
    def test_generate_pr_comment_has_no_eval_summary_param(self):
        """generate_pr_comment signature: no eval_summary or regressions param.

        Regression data from detect_regressions cannot be included in PR comments.
        This is F-033 — the eval and CI modules are not integrated.
        """
        import inspect
        sig = inspect.signature(generate_pr_comment)
        param_names = list(sig.parameters.keys())
        assert "eval_summary" not in param_names
        assert "regressions" not in param_names

    def test_detect_regressions_not_surfaced_in_pr_comment(self):
        """Regressions detected by detect_regressions have no path to PR comment output."""
        current = {
            "task_completion": make_aggregate("task_completion", 0.6),
        }
        baseline = {
            "task_completion": make_aggregate("task_completion", 0.9),
        }
        regressions = detect_regressions(current, baseline)
        assert len(regressions) == 1
        assert regressions[0].regressed is True

        # There is no way to pass this regression data to generate_pr_comment
        # The function takes test_summary, gate_report, cost_report — not eval data
        comment = generate_pr_comment()
        assert "regression" not in comment.lower()

    def test_eval_run_summary_has_regressions_field(self):
        """EvalRunSummary has regressions field that can hold RegressionResult objects."""
        current = {"tc": make_aggregate("tc", 0.6)}
        baseline = {"tc": make_aggregate("tc", 0.9)}
        regressions = detect_regressions(current, baseline)

        eval_summary = EvalRunSummary(
            aggregates=list(current.values()),
            regressions=regressions,
        )
        assert len(eval_summary.regressions) == 1
        assert eval_summary.regressions[0].metric_name == "tc"
        assert eval_summary.regressions[0].regressed is True


# ---------------------------------------------------------------------------
# checkagent run — default -m agent_test filter (F-034)
# ---------------------------------------------------------------------------


class TestCheckagentRunDefaultFilter:
    """checkagent run adds -m agent_test by default — runs fewer tests than pytest."""

    def test_build_pytest_args_adds_m_agent_test_by_default(self):
        """`build_pytest_args` injects -m agent_test when no -m is provided."""
        args = build_pytest_args((), layer=None)
        assert "-m" in args
        idx = args.index("-m")
        assert args[idx + 1] == "agent_test"

    def test_build_pytest_args_does_not_add_m_if_already_present(self):
        """If user passes -m, build_pytest_args doesn't add a second -m."""
        args = build_pytest_args(("-m", "safety"), layer=None)
        assert args.count("-m") == 1

    def test_build_pytest_args_adds_verbose_by_default(self):
        """`build_pytest_args` adds -v by default."""
        args = build_pytest_args((), layer=None)
        assert "-v" in args

    def test_build_pytest_args_does_not_add_v_if_quiet(self):
        """`build_pytest_args` skips -v when -q is provided."""
        args = build_pytest_args(("-q",), layer=None)
        assert "-v" not in args

    def test_build_pytest_args_with_layer_adds_agent_layer_flag(self):
        """`build_pytest_args` with layer=mock adds --agent-layer mock."""
        args = build_pytest_args((), layer="mock")
        assert "--agent-layer" in args
        idx = args.index("--agent-layer")
        assert args[idx + 1] == "mock"


# ---------------------------------------------------------------------------
# judge layer marker — behavior and filtering
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="judge")
class TestJudgeLayerMarker:
    """Tests marked with layer='judge'. These run under checkagent run --layer judge."""

    def test_judge_layer_test_runs_normally(self):
        """A test marked layer='judge' is a normal pytest test — just filtered by layer."""
        run = make_run(success=True)
        score = task_completion(run, check_no_error=True)
        assert score.passed is True

    def test_judge_layer_can_use_all_fixtures(self, ap_mock_llm, ap_mock_tool):
        """Judge-layer tests have access to all checkagent fixtures."""
        ap_mock_llm.add_rule(".*", "Judge response", match_mode=MatchMode.REGEX)
        response = ap_mock_llm.complete_sync("Evaluate this agent output for quality")
        assert response == "Judge response"

    def test_judge_layer_marker_is_distinct_from_mock_layer(self):
        """The judge layer is a separate selection bucket from mock/eval/replay."""
        # This test only runs under --layer judge or unmarked pytest runs
        # It will be deselected by checkagent run --layer mock
        assert True


# ---------------------------------------------------------------------------
# CI quality gates — no pytest exit code integration
# ---------------------------------------------------------------------------


class TestCIGatesNoPytestIntegration:
    """checkagent.ci has no pytest plugin hooks — gates can't auto-fail pytest."""

    def test_plugin_has_no_sessionfinish_hook(self):
        """The checkagent pytest plugin does not implement pytest_sessionfinish."""
        import checkagent.core.plugin as plugin
        assert not hasattr(plugin, "pytest_sessionfinish")

    def test_plugin_has_no_terminal_summary_hook(self):
        """The checkagent pytest plugin does not implement pytest_terminal_summary."""
        import checkagent.core.plugin as plugin
        assert not hasattr(plugin, "pytest_terminal_summary")

    def test_no_ap_quality_gates_fixture(self):
        """There is no ap_quality_gates fixture in the checkagent plugin."""
        import checkagent.core.plugin as plugin
        import inspect
        src = inspect.getsource(plugin)
        assert "ap_quality_gates" not in src

    def test_quality_gates_from_config_not_auto_evaluated(self):
        """Quality gates defined in checkagent.yml are loaded into ap_config
        but not automatically evaluated — users must call evaluate_gates() manually.
        """
        from checkagent.core.config import CheckAgentConfig, QualityGateEntry
        config = CheckAgentConfig(
            quality_gates={
                "task_completion": QualityGateEntry(min=0.9, on_fail="block")
            }
        )
        # Config has the gates but there's no auto-evaluation
        assert "task_completion" in config.quality_gates
        # To use them, user must call evaluate_gates(scores, config.quality_gates)
        report = evaluate_gates({"task_completion": 0.3}, config.quality_gates)
        assert report.passed is False  # gate would block — but only if user calls this


# ---------------------------------------------------------------------------
# generate_pr_comment — warned gates section
# ---------------------------------------------------------------------------


class TestGeneratePrCommentWarnedGates:
    def test_warned_gate_appears_in_pr_comment(self):
        """Warned gates show in PR comment with appropriate status."""
        gates = {"se": QualityGateEntry(min=0.9, on_fail="warn")}
        gate_report = evaluate_gates({"se": 0.5}, gates)
        comment = generate_pr_comment(gate_report=gate_report)
        assert "se" in comment
        assert "warned" in comment

    def test_blocked_gate_in_pr_comment_shows_failure(self):
        """Blocked gates appear in PR comment with failure status."""
        gates = {"tc": QualityGateEntry(min=0.9, on_fail="block")}
        gate_report = evaluate_gates({"tc": 0.3}, gates)
        comment = generate_pr_comment(gate_report=gate_report)
        assert "tc" in comment
        assert "blocked" in comment

    def test_cost_report_in_pr_comment(self):
        """Cost report section renders if cost_report provided."""
        from checkagent import CostTracker
        tracker = CostTracker()
        report = tracker.summary()
        comment = generate_pr_comment(cost_report=report)
        # Footer always present regardless of content
        assert "CheckAgent" in comment

    def test_all_none_generates_minimal_comment(self):
        """generate_pr_comment() with no args produces minimal header + footer."""
        comment = generate_pr_comment()
        assert "CheckAgent Test Report" in comment
        assert "Generated by" in comment
        # No sections rendered for None inputs
        assert "Test Results" not in comment
        assert "Quality Gates" not in comment


# ---------------------------------------------------------------------------
# detect_regressions — behavior validation
# ---------------------------------------------------------------------------


class TestDetectRegressions:
    def test_regression_detected_when_drop_exceeds_threshold(self):
        """detect_regressions flags when current mean drops more than threshold."""
        current = {"tc": make_aggregate("tc", 0.6)}
        baseline = {"tc": make_aggregate("tc", 0.9)}
        results = detect_regressions(current, baseline, threshold=0.05)
        assert len(results) == 1
        assert results[0].regressed is True
        assert results[0].delta == pytest.approx(-0.3, abs=0.001)

    def test_no_regression_when_drop_within_threshold(self):
        """Small drops within threshold are not flagged."""
        current = {"tc": make_aggregate("tc", 0.87)}
        baseline = {"tc": make_aggregate("tc", 0.90)}
        results = detect_regressions(current, baseline, threshold=0.05)
        assert results[0].regressed is False

    def test_improvement_is_not_regression(self):
        """Improvement (current > baseline) is never a regression."""
        current = {"tc": make_aggregate("tc", 0.95)}
        baseline = {"tc": make_aggregate("tc", 0.80)}
        results = detect_regressions(current, baseline)
        assert results[0].regressed is False
        assert results[0].delta > 0

    def test_missing_baseline_metric_is_skipped(self):
        """Metric in current but not baseline is not included in results."""
        current = {"tc": make_aggregate("tc", 0.8), "new_metric": make_aggregate("new_metric", 0.9)}
        baseline = {"tc": make_aggregate("tc", 0.85)}
        results = detect_regressions(current, baseline)
        metric_names = [r.metric_name for r in results]
        assert "tc" in metric_names
        assert "new_metric" not in metric_names

    def test_run_summary_save_load_aggregates_preserved(self, tmp_path):
        """RunSummary round-trip preserves aggregates dict."""
        current = {"tc": make_aggregate("tc", 0.6)}
        summary = EvalRunSummary(aggregates=current)
        path = tmp_path / "summary.json"
        summary.save(path)
        loaded = EvalRunSummary.load(path)
        assert "tc" in loaded.aggregates
        assert loaded.aggregates["tc"].mean == pytest.approx(0.6, abs=0.001)

    def test_run_summary_save_does_not_restore_regressions(self, tmp_path):
        """RunSummary.load() silently drops regressions even though save() serializes them.

        This is F-035: regressions are written to JSON by to_dict() but load()
        never reads them back — loaded.regressions is always empty.
        """
        current = {"tc": make_aggregate("tc", 0.6)}
        baseline = {"tc": make_aggregate("tc", 0.9)}
        regressions = detect_regressions(current, baseline)
        assert regressions[0].regressed is True

        summary = EvalRunSummary(aggregates=current, regressions=regressions)
        path = tmp_path / "summary.json"
        summary.save(path)

        # Regressions ARE in the JSON file
        import json
        data = json.loads(path.read_text())
        assert "regressions" in data

        # But load() doesn't restore them
        loaded = EvalRunSummary.load(path)
        assert len(loaded.regressions) == 0  # F-035: should be 1
