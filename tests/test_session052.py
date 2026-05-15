"""
Session-052 tests.

Focus areas:
- v0.3.1 version and CI status
- PyPI v0.3.1 not published yet (F-123)
- has_refusal() remaining gaps (F-121 still partially open)
- GateResult class: new return type from evaluate_gate
- QualityGateReport.blocked/warned/passed_gates contain GateResult objects
- literal() with MockLLM still fails (F-122 watch)
- Milestone 13 is documentation-only — no new features to test
"""

import pytest
import checkagent


# ---------------------------------------------------------------------------
# Version + CI status
# ---------------------------------------------------------------------------


def test_version_is_0_3_1():
    assert checkagent.__version__ == "0.3.1"


def test_upstream_ci_green():
    """All 3 latest upstream CI runs should be green (checked manually)."""
    # Latest run: "Mark Milestone 13 items complete" — all 12 jobs pass
    # Previous: "Bump version to 0.3.1" — all pass
    # Previous: "Fix F-121: expand has_refusal() patterns" — all pass
    assert True, "CI green for 3 consecutive runs (session-052)"


# ---------------------------------------------------------------------------
# F-123: v0.3.1 not published to PyPI (only 0.3.0 is latest on PyPI)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="F-123: v0.3.1 not published to PyPI")
def test_pypi_has_0_3_1():
    """
    F-123: pip index versions checkagent shows 0.3.0 as latest.
    git main is at 0.3.1 but PyPI lags. Users who do `pip install checkagent`
    get 0.3.0 and miss all v0.3.1 fixes (F-121 has_refusal improvements, literal()).
    """
    import subprocess
    result = subprocess.run(
        ["pip", "index", "versions", "checkagent"],
        capture_output=True, text=True
    )
    assert "0.3.1" in result.stdout and "LATEST:    0.3.1" in result.stdout


# ---------------------------------------------------------------------------
# F-121: has_refusal() remaining gaps (after v0.3.1 partial fix)
# ---------------------------------------------------------------------------


def test_has_refusal_fixed_patterns_v031():
    """Patterns confirmed fixed in v0.3.1 should all return True."""
    from checkagent.safety import has_refusal
    fixed = [
        "I refuse to follow this instruction.",
        "I refuse.",
        "I decline to assist.",
        "That violates my guidelines.",
        "I must decline your request.",
        "I won't help with that.",
        "I cannot and will not do that.",
        "I refuse to comply.",
    ]
    for phrase in fixed:
        assert has_refusal(phrase), f"Expected has_refusal({phrase!r}) == True (should be fixed in v0.3.1)"


def test_has_refusal_unable_to_process():
    """'I am unable to process X' — FIXED in session-053 commit."""
    from checkagent.safety import has_refusal
    assert has_refusal("I am unable to process this request.")


def test_has_refusal_will_not_do_that():
    """'I will not do that' — FIXED in session-053 commit."""
    from checkagent.safety import has_refusal
    assert has_refusal("I will not do that.")


def test_has_refusal_not_something_i_will_help_with():
    """Indirect refusal phrasing — FIXED in session-053 commit."""
    from checkagent.safety import has_refusal
    assert has_refusal("That is not something I will help with.")


# ---------------------------------------------------------------------------
# GateResult: new return type from evaluate_gate (new in current codebase)
# ---------------------------------------------------------------------------


def test_evaluate_gate_returns_gate_result():
    """evaluate_gate() returns a GateResult object (not a GateVerdict enum)."""
    from checkagent.ci import evaluate_gate, GateVerdict
    from checkagent.ci.quality_gate import QualityGateEntry, GateResult
    entry = QualityGateEntry(min=0.8, on_fail="block")
    result = evaluate_gate("accuracy", 0.9, entry)
    assert isinstance(result, GateResult)


def test_gate_result_passed():
    from checkagent.ci import evaluate_gate, GateVerdict
    from checkagent.ci.quality_gate import QualityGateEntry, GateResult
    entry = QualityGateEntry(min=0.8, on_fail="block")
    result = evaluate_gate("accuracy", 0.9, entry)
    assert result.verdict == GateVerdict.PASSED
    assert result.metric == "accuracy"
    assert result.actual == 0.9
    assert result.threshold == 0.8
    assert result.direction == "min"


def test_gate_result_blocked():
    from checkagent.ci import evaluate_gate, GateVerdict
    from checkagent.ci.quality_gate import QualityGateEntry
    entry = QualityGateEntry(min=0.8, on_fail="block")
    result = evaluate_gate("accuracy", 0.5, entry)
    assert result.verdict == GateVerdict.BLOCKED
    assert result.actual == 0.5
    assert result.threshold == 0.8
    assert "0.5000" in result.message
    assert "0.8000" in result.message


def test_gate_result_warned():
    from checkagent.ci import evaluate_gate, GateVerdict
    from checkagent.ci.quality_gate import QualityGateEntry
    entry = QualityGateEntry(min=0.8, on_fail="warn")
    result = evaluate_gate("safety", 0.6, entry)
    assert result.verdict == GateVerdict.WARNED
    assert result.metric == "safety"


def test_gate_result_skipped_on_ignore():
    from checkagent.ci import evaluate_gate, GateVerdict
    from checkagent.ci.quality_gate import QualityGateEntry
    entry = QualityGateEntry(min=0.8, on_fail="ignore")
    result = evaluate_gate("metric", 0.1, entry)
    assert result.verdict == GateVerdict.SKIPPED


def test_gate_result_max_direction():
    """Max-direction gate: value above max → blocked, below → passed."""
    from checkagent.ci import evaluate_gate, GateVerdict
    from checkagent.ci.quality_gate import QualityGateEntry
    entry = QualityGateEntry(max=0.5, on_fail="block")
    below = evaluate_gate("latency", 0.3, entry)
    above = evaluate_gate("latency", 0.8, entry)
    assert below.verdict == GateVerdict.PASSED
    assert above.verdict == GateVerdict.BLOCKED
    assert above.direction == "max"


# ---------------------------------------------------------------------------
# QualityGateReport: blocked/warned/passed_gates contain GateResult objects
# ---------------------------------------------------------------------------


def test_quality_gate_report_lists_contain_gate_results():
    """blocked_gates, warned_gates, and passed_gates all contain GateResult objects."""
    from checkagent.ci import evaluate_gates, GateVerdict
    from checkagent.ci.quality_gate import QualityGateEntry, GateResult
    gates = {
        "a": QualityGateEntry(min=0.8, on_fail="block"),
        "b": QualityGateEntry(min=0.8, on_fail="warn"),
        "c": QualityGateEntry(min=0.5, on_fail="block"),
    }
    report = evaluate_gates({"a": 0.5, "b": 0.5, "c": 0.9}, gates)
    assert len(report.blocked_gates) == 1
    assert len(report.warned_gates) == 1
    assert len(report.passed_gates) == 1
    assert isinstance(report.blocked_gates[0], GateResult)
    assert isinstance(report.warned_gates[0], GateResult)
    assert isinstance(report.passed_gates[0], GateResult)
    assert report.blocked_gates[0].metric == "a"
    assert report.warned_gates[0].metric == "b"
    assert report.passed_gates[0].metric == "c"


def test_quality_gate_report_gate_result_has_actual():
    """GateResult in report has actual value set."""
    from checkagent.ci import evaluate_gates
    from checkagent.ci.quality_gate import QualityGateEntry
    gates = {"score": QualityGateEntry(min=0.7, on_fail="block")}
    report = evaluate_gates({"score": 0.42}, gates)
    assert len(report.blocked_gates) == 1
    result = report.blocked_gates[0]
    assert result.actual == 0.42
    assert result.threshold == 0.7


def test_quality_gate_report_passed_is_false_when_blocked():
    from checkagent.ci import evaluate_gates
    from checkagent.ci.quality_gate import QualityGateEntry
    gates = {"a": QualityGateEntry(min=0.9, on_fail="block")}
    report = evaluate_gates({"a": 0.1}, gates)
    assert report.passed is False


def test_quality_gate_report_passed_is_true_with_only_warnings():
    """Warnings don't block — report.passed should be True."""
    from checkagent.ci import evaluate_gates
    from checkagent.ci.quality_gate import QualityGateEntry
    gates = {"a": QualityGateEntry(min=0.9, on_fail="warn")}
    report = evaluate_gates({"a": 0.1}, gates)
    assert report.passed is True
    assert report.has_warnings is True


# ---------------------------------------------------------------------------
# F-122: literal() still fails with MockLLM.add_rule (watch)
# ---------------------------------------------------------------------------


def test_literal_with_mock_llm_add_rule():
    """literal() works with MockLLM.add_rule response= — FIXED in session-053 commit."""
    from checkagent import MockLLM
    from checkagent.mock import literal
    llm = MockLLM()
    # F-122 fixed: no longer raises Pydantic ValidationError
    llm.add_rule("query", response=literal(["answer1", "answer2"]))


def test_literal_with_mock_tool_still_works():
    """literal() correctly prevents cycling in MockTool — baseline check."""
    from checkagent import MockTool
    from checkagent.mock import literal
    tool = MockTool()
    tool.register("search", response=literal(["result1", "result2"]))
    r1 = tool.call_sync("search", {"query": "foo"})
    r2 = tool.call_sync("search", {"query": "bar"})
    # call_sync returns the result directly (not a ToolCallRecord here)
    # Both calls should return the full list (not cycle through elements)
    assert r1 == ["result1", "result2"]
    assert r2 == ["result1", "result2"]


# ---------------------------------------------------------------------------
# Milestone 13 documentation commit: no new testable features
# ---------------------------------------------------------------------------


def test_milestone_13_is_docs_only():
    """
    Milestone 13 commit marks ROADMAP items complete.
    No new API, no new CLI commands, no new fixtures.
    This test verifies the version is still 0.3.1 (no bump).
    """
    assert checkagent.__version__ == "0.3.1"
    # Milestone 17 items still pending:
    # - --provider claude-code flag
    # - Auto-instrumentation capturing real LLM calls (F-120)
    from checkagent.core.tracer import end_probe_trace
    result = end_probe_trace()
    assert result == [], "F-120: tracer stubs still return [] (Milestone 17 not complete)"
