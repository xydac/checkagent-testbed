"""
Session-033 tests: checkagent 0.1.1 upgrade — ResilienceProfile, breaking fixture rename,
top-level export improvements, and bug fixes from F-009/F-010/F-016/F-020/F-021/F-026/
F-031/F-032/F-035/F-048/F-053/F-055/F-057/F-063.
"""
import importlib.metadata

import pytest

import checkagent
from checkagent import (
    AgentInput,
    AgentRun,
    AggregateResult,
    AnthropicAdapter,
    ConsensusVerdict,
    CrewAIAdapter,
    EvalCase,
    Evaluator,
    EvaluatorRegistry,
    FaultInjector,
    HandoffType,
    LangChainAdapter,
    MockLLM,
    MockTool,
    Probe,
    ProbeSet,
    PydanticAIAdapter,
    QualityGateEntry,
    ResilienceProfile,
    SafetyCategory,
    SafetyEvaluator,
    SafetyFinding,
    SafetyResult,
    ScenarioResult,
    Score,
    Severity,
    Step,
    StepStats,
    TestRunSummary,
    multi_judge_evaluate,
)
from checkagent.eval.metrics import task_completion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_run(output: str) -> AgentRun:
    return AgentRun(
        input=AgentInput(query="test"),
        final_output=output,
        steps=[Step(output_text=output)],
    )


def tc_metric(run: AgentRun) -> Score:
    return task_completion(run, expected_output_contains=["success"])


# ---------------------------------------------------------------------------
# Breaking change: ap_* → ca_* fixture rename
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="mock")
async def test_ca_mock_llm_fixture_works(ca_mock_llm):
    """ca_mock_llm is the new name for ap_mock_llm — basic sanity check."""
    ca_mock_llm.add_rule("hello", "world")
    resp = await ca_mock_llm.complete("hello there")
    assert resp == "world"


@pytest.mark.agent_test(layer="mock")
async def test_ca_mock_tool_fixture_works(ca_mock_tool):
    """ca_mock_tool is the new name for ap_mock_tool — basic sanity check."""
    ca_mock_tool.register("search", response={"results": ["a", "b"]})
    result = await ca_mock_tool.call("search", {"query": "cats"})
    assert result == {"results": ["a", "b"]}


@pytest.mark.agent_test(layer="mock")
async def test_ca_fault_fixture_works(ca_fault):
    """ca_fault is the new name for ap_fault."""
    assert isinstance(ca_fault, FaultInjector)
    ca_fault.on_tool("search").rate_limit()
    from checkagent.mock.fault import ToolRateLimitError
    with pytest.raises(ToolRateLimitError):
        ca_fault.check_tool("search")


@pytest.mark.agent_test(layer="mock")
async def test_ca_mock_llm_complete_works(ca_mock_llm):
    """Regression: basic complete() still works after fixture rename."""
    ca_mock_llm.add_rule("any", "default response")
    result = await ca_mock_llm.complete("any prompt")
    assert result == "default response"
    assert ca_mock_llm.call_count == 1


# ---------------------------------------------------------------------------
# ResilienceProfile: from_scores
# ---------------------------------------------------------------------------

class TestResilienceProfileFromScores:
    def test_basic_profile(self):
        profile = ResilienceProfile.from_scores(
            baseline={"task_completion": 0.95, "tool_correctness": 1.0},
            scenarios={
                "llm_rate_limit": {"task_completion": 0.6, "tool_correctness": 0.8},
                "tool_timeout": {"task_completion": 0.3, "tool_correctness": 0.5},
            },
        )
        assert 0.0 <= profile.overall <= 1.0
        assert profile.worst_scenario == "tool_timeout"
        assert profile.best_scenario == "llm_rate_limit"
        assert profile.weakest_metric == "task_completion"

    def test_empty_scenarios_returns_perfect_resilience(self):
        profile = ResilienceProfile.from_scores(
            baseline={"tc": 0.9},
            scenarios={},
        )
        assert profile.overall == 1.0
        assert profile.worst_scenario is None
        assert profile.best_scenario is None
        assert profile.weakest_metric is None

    def test_no_degradation_yields_perfect_resilience(self):
        profile = ResilienceProfile.from_scores(
            baseline={"tc": 0.9},
            scenarios={"no_change": {"tc": 0.9}},
        )
        assert profile.overall == 1.0
        assert profile.scenario_results["no_change"].degradation == {"tc": 0.0}

    def test_improvement_capped_at_one(self):
        """Faulted performance better than baseline: resilience should be 1.0, not >1."""
        profile = ResilienceProfile.from_scores(
            baseline={"tc": 0.5},
            scenarios={"better": {"tc": 1.0}},
        )
        assert profile.overall == 1.0
        assert profile.scenario_results["better"].resilience == 1.0
        # degradation is positive (faulted - baseline)
        assert profile.scenario_results["better"].degradation["tc"] == pytest.approx(0.5)

    def test_total_failure_yields_zero(self):
        profile = ResilienceProfile.from_scores(
            baseline={"tc": 1.0},
            scenarios={"total_failure": {"tc": 0.0}},
        )
        assert profile.overall == pytest.approx(0.0)

    def test_scenario_result_fields(self):
        profile = ResilienceProfile.from_scores(
            baseline={"tc": 0.8, "rc": 0.9},
            scenarios={"fault": {"tc": 0.4, "rc": 0.6}},
        )
        sr = profile.scenario_results["fault"]
        assert isinstance(sr, ScenarioResult)
        assert sr.scenario == "fault"
        assert "tc" in sr.scores
        assert "rc" in sr.scores
        assert sr.degradation["tc"] == pytest.approx(-0.4)
        assert sr.degradation["rc"] == pytest.approx(-0.3)
        assert 0.0 <= sr.resilience <= 1.0

    def test_to_dict_serialization(self):
        profile = ResilienceProfile.from_scores(
            baseline={"tc": 0.9},
            scenarios={"f": {"tc": 0.6}},
        )
        d = profile.to_dict()
        assert "overall_resilience" in d
        assert "baseline" in d
        assert "worst_scenario" in d
        assert "weakest_metric" in d
        assert "scenarios" in d
        assert "f" in d["scenarios"]
        assert "resilience" in d["scenarios"]["f"]
        assert "scores" in d["scenarios"]["f"]
        assert "degradation" in d["scenarios"]["f"]


# ---------------------------------------------------------------------------
# ResilienceProfile: from_runs
# ---------------------------------------------------------------------------

class TestResilienceProfileFromRuns:
    def test_from_runs_basic(self):
        baseline = [make_run("success"), make_run("success result")]
        faulted = {
            "rate_limit": [make_run("failed"), make_run("success partial")],
        }
        profile = ResilienceProfile.from_runs(
            baseline_runs=baseline,
            faulted_runs=faulted,
            metrics={"task_completion": tc_metric},
        )
        assert 0.0 <= profile.overall <= 1.0
        assert profile.worst_scenario == "rate_limit"

    def test_from_runs_multiple_scenarios(self):
        baseline = [make_run("success"), make_run("success")]
        faulted = {
            "timeout": [make_run("timeout error"), make_run("timeout error")],
            "rate_limit": [make_run("success"), make_run("timeout")],
        }
        profile = ResilienceProfile.from_runs(
            baseline_runs=baseline,
            faulted_runs=faulted,
            metrics={"task_completion": tc_metric},
        )
        assert profile.worst_scenario == "timeout"
        assert profile.best_scenario == "rate_limit"

    def test_from_runs_with_empty_faulted(self):
        baseline = [make_run("success")]
        profile = ResilienceProfile.from_runs(
            baseline_runs=baseline,
            faulted_runs={},
            metrics={"task_completion": tc_metric},
        )
        assert profile.overall == 1.0

    def test_from_runs_metric_callable_returns_score(self):
        """Verify the metric callable receives AgentRun and returns Score."""
        received_runs = []

        def spy_metric(run: AgentRun) -> Score:
            received_runs.append(run)
            return Score(name="spy", value=1.0, threshold=0.5)

        baseline = [make_run("x")]
        ResilienceProfile.from_runs(
            baseline_runs=baseline,
            faulted_runs={"f": [make_run("y")]},
            metrics={"spy": spy_metric},
        )
        assert len(received_runs) == 2  # 1 baseline + 1 faulted
        assert all(isinstance(r, AgentRun) for r in received_runs)


# ---------------------------------------------------------------------------
# Top-level exports: previously missing, now fixed (F-020, F-021, F-026,
# F-048, F-053, F-057, F-063, F-086)
# ---------------------------------------------------------------------------

class TestTopLevelExports:
    def test_adapters_at_top_level(self):
        """F-057/F-063/F-086 FIXED — all adapters now at top-level checkagent."""
        assert hasattr(checkagent, "LangChainAdapter")
        assert hasattr(checkagent, "PydanticAIAdapter")
        assert hasattr(checkagent, "CrewAIAdapter")
        assert hasattr(checkagent, "AnthropicAdapter")

    def test_eval_classes_at_top_level(self):
        """F-020 FIXED — eval classes now at top-level."""
        assert hasattr(checkagent, "Evaluator")
        assert hasattr(checkagent, "EvaluatorRegistry")
        assert hasattr(checkagent, "AggregateResult")
        assert hasattr(checkagent, "StepStats")

    def test_safety_classes_at_top_level(self):
        """F-021 FIXED — safety classes now at top-level."""
        assert hasattr(checkagent, "SafetyEvaluator")
        assert hasattr(checkagent, "SafetyFinding")
        assert hasattr(checkagent, "SafetyResult")
        assert hasattr(checkagent, "PromptInjectionDetector")

    def test_probe_classes_at_top_level(self):
        """F-026 FIXED — Probe and ProbeSet now at top-level."""
        assert hasattr(checkagent, "Probe")
        assert hasattr(checkagent, "ProbeSet")

    def test_judge_classes_at_top_level(self):
        """F-048 FIXED — judge classes now at top-level."""
        assert hasattr(checkagent, "Rubric")
        assert hasattr(checkagent, "RubricJudge")
        assert hasattr(checkagent, "Criterion")

    def test_multiagent_at_top_level(self):
        """F-053 FIXED — multi-judge and F-068 FIXED — multiagent now at top-level."""
        assert hasattr(checkagent, "ConsensusVerdict")
        assert hasattr(checkagent, "multi_judge_evaluate")
        assert hasattr(checkagent, "HandoffType")
        assert hasattr(checkagent, "MultiAgentTrace")

    def test_resilience_profile_at_top_level(self):
        """New in 0.1.1: ResilienceProfile and ScenarioResult at top-level."""
        assert hasattr(checkagent, "ResilienceProfile")
        assert hasattr(checkagent, "ScenarioResult")

    def test_eval_case_at_top_level(self):
        """EvalCase (renamed from TestCase) now at top-level."""
        assert hasattr(checkagent, "EvalCase")
        ec = EvalCase(id="tc-001", input="test query")
        assert ec.input == "test query"
        assert ec.id == "tc-001"

    def test_quality_gate_entry_at_top_level(self):
        """F-030 FIXED — QualityGateEntry now at top-level."""
        assert hasattr(checkagent, "QualityGateEntry")

    def test_test_run_summary_at_top_level(self):
        """TestRunSummary (CI run summary) now at top-level."""
        assert hasattr(checkagent, "TestRunSummary")


# ---------------------------------------------------------------------------
# SafetyEvaluator base class
# ---------------------------------------------------------------------------

class TestSafetyEvaluator:
    def test_subclass_custom_evaluator(self):
        """SafetyEvaluator ABC can be subclassed for custom safety checks."""
        class NoSwearingEvaluator(SafetyEvaluator):
            name = "no_swearing"
            category = SafetyCategory.PROMPT_INJECTION

            def evaluate(self, text: str) -> SafetyResult:
                bad_words = ["badword"]
                findings = [
                    SafetyFinding(
                        category=SafetyCategory.PROMPT_INJECTION,
                        severity=Severity.HIGH,
                        description=f"Found bad word",
                        evidence=w,
                    )
                    for w in bad_words
                    if w in text
                ]
                return SafetyResult(passed=len(findings) == 0, findings=findings, evaluator=self.name)

        ev = NoSwearingEvaluator()
        result = ev.evaluate("this is a clean text")
        assert result.passed is True
        assert result.finding_count == 0

        result2 = ev.evaluate("this has a badword in it")
        assert result2.passed is False
        assert result2.finding_count == 1
        assert result2.findings[0].severity == Severity.HIGH

    def test_evaluate_run_uses_final_output(self):
        """evaluate_run() extracts final_output as text and calls evaluate()."""
        class AlwaysPassEvaluator(SafetyEvaluator):
            name = "pass"
            received = []

            def evaluate(self, text: str) -> SafetyResult:
                self.received.append(text)
                return SafetyResult(passed=True)

        ev = AlwaysPassEvaluator()
        run = make_run("this is the output")
        result = ev.evaluate_run(run)
        assert result.passed is True
        assert "this is the output" in ev.received

    def test_safety_result_finding_by_severity(self):
        """SafetyResult.findings_by_severity() filters correctly."""
        findings = [
            SafetyFinding(category=SafetyCategory.PII_LEAKAGE, severity=Severity.HIGH, description="h"),
            SafetyFinding(category=SafetyCategory.PII_LEAKAGE, severity=Severity.LOW, description="l"),
        ]
        result = SafetyResult(passed=False, findings=findings)
        assert len(result.findings_by_severity(Severity.HIGH)) == 1
        assert len(result.findings_by_severity(Severity.LOW)) == 1
        assert len(result.findings_by_severity(Severity.CRITICAL)) == 0


# ---------------------------------------------------------------------------
# Version string inconsistency
# ---------------------------------------------------------------------------

def test_version_string_consistent():
    """
    Version consistency: checkagent.__version__ and importlib.metadata agree.
    Previously broken in 0.1.1 (module said 0.1.0, metadata said 0.1.1).
    Fixed in 0.1.2 — both now report the same version.
    """
    pkg_version = importlib.metadata.version("checkagent")
    module_version = checkagent.__version__
    assert pkg_version == module_version, (
        f"__version__ ({module_version!r}) != pkg metadata ({pkg_version!r})"
        " — version string inconsistency detected"
    )


# ---------------------------------------------------------------------------
# Probe and ProbeSet API changes
# ---------------------------------------------------------------------------

class TestProbeSetAPIChanges:
    def test_all_returns_probeset_not_list(self):
        """F-032 FIXED: probes.injection.direct.all() now consistently returns ProbeSet."""
        from checkagent.safety import probes
        ps = probes.injection.direct.all()
        assert isinstance(ps, ProbeSet)

    def test_probeset_not_subscriptable(self):
        """ProbeSet does not support indexing — use list() conversion."""
        from checkagent.safety import probes
        ps = probes.injection.direct.all()
        with pytest.raises(TypeError):
            _ = ps[0]

    def test_probeset_iterable_yields_probes(self):
        """ProbeSet is iterable and yields Probe objects."""
        from checkagent.safety import probes
        items = list(probes.injection.direct.all())
        assert len(items) > 0
        assert all(isinstance(p, Probe) for p in items)

    def test_probeset_str_is_probe_name(self):
        """str(probe) returns probe.name for pytest-friendly IDs."""
        from checkagent.safety import probes
        probe = list(probes.injection.direct.all())[0]
        assert str(probe) == probe.name


# ---------------------------------------------------------------------------
# langchain-core as declared dependency
# ---------------------------------------------------------------------------

def test_langchain_core_is_declared_dep():
    """F-055 FIXED: langchain-core is now a declared dependency."""
    meta = importlib.metadata.metadata("checkagent")
    requires = meta.get_all("Requires-Dist") or []
    has_langchain = any("langchain" in r.lower() for r in requires)
    assert has_langchain, "langchain-core should be a declared dependency in 0.1.1"
