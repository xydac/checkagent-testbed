"""
Session-062 tests: --repeat + --llm-judge combination, F-132 fixed (evaluator in JSON),
F-120 still stubs, real PydanticAI agent + LLM judge integration.
"""
import json
import subprocess
import pytest
import sys


# ---------------------------------------------------------------------------
# Upstream CI — green as of 2026-05-28
# ---------------------------------------------------------------------------

def test_upstream_ci_latest_green():
    """Latest upstream CI runs are green (all 5 recent runs succeeded)."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "5",
         "--json", "status,conclusion,displayTitle"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    for run in data:
        assert run["conclusion"] == "success", (
            f"CI run failed: {run['displayTitle']}"
        )


# ---------------------------------------------------------------------------
# F-132 FIXED: evaluator now present in JSON output for --llm-judge
# ---------------------------------------------------------------------------

def test_f132_fixed_evaluator_field_in_json():
    """F-132 FIXED: JSON output includes 'evaluator' field in summary when --llm-judge used."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code", "--category", "injection", "--json"],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    assert "evaluator" in data["summary"], (
        "F-132 should be fixed: 'evaluator' field missing from summary in JSON output. "
        f"Summary keys: {list(data['summary'].keys())}"
    )
    assert data["summary"]["evaluator"] == "claude-code", (
        f"Expected evaluator='claude-code', got {data['summary'].get('evaluator')}"
    )


def test_f132_fixed_evaluator_is_accessible_in_json():
    """F-132 FIXED: evaluator field is at summary.evaluator, not top-level."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code", "--category", "injection", "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    # Verify top-level keys are still correct
    assert "summary" in data
    assert "findings" in data
    assert "target" in data
    # evaluator is in summary, not at top-level
    assert "evaluator" in data["summary"]


# ---------------------------------------------------------------------------
# --repeat + --llm-judge combination — verified working
# ---------------------------------------------------------------------------

def test_repeat_and_llm_judge_combination_works():
    """--repeat + --llm-judge combination produces valid JSON output."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code", "--category", "injection",
         "--repeat", "2", "--json"],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"--repeat + --llm-judge produced invalid JSON: {e}\nstdout: {result.stdout[:400]}")
    assert "summary" in data
    assert "stability" in data, "Expected 'stability' object in JSON when --repeat is used"


def test_repeat_with_llm_judge_stability_object():
    """--repeat N + --llm-judge: stability object has correct shape."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code", "--category", "injection",
         "--repeat", "2", "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    stability = data.get("stability", {})
    assert "repeat" in stability, "stability.repeat missing"
    assert stability["repeat"] == 2, f"Expected repeat=2, got {stability['repeat']}"
    assert "stable_pass" in stability
    assert "stable_fail" in stability
    assert "flaky" in stability
    assert "stability_score" in stability


def test_repeat_with_llm_judge_evaluator_persists():
    """--repeat + --llm-judge: evaluator field is still set correctly in summary."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code", "--category", "injection",
         "--repeat", "2", "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["summary"].get("evaluator") == "claude-code", (
        f"evaluator should be 'claude-code' with --repeat, got: {data['summary'].get('evaluator')}"
    )


def test_repeat_3_with_llm_judge_correct_repeat_count():
    """--repeat 3 + --llm-judge: stability.repeat is 3."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code", "--category", "scope",
         "--repeat", "3", "--json"],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    assert data.get("stability", {}).get("repeat") == 3, (
        f"Expected stability.repeat=3, got {data.get('stability', {}).get('repeat')}"
    )


# ---------------------------------------------------------------------------
# F-120 (still open): auto-instrumentation tracer captures no events
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="F-120: ca_tracer / auto-instrumentation still stubs — end_probe_trace() returns [], no events captured"
)
def test_f120_tracer_captures_events():
    """F-120: begin_probe_trace() / end_probe_trace() should capture LLM call events."""
    try:
        from checkagent.core.tracer import (
            install_patches, uninstall_patches,
            begin_probe_trace, end_probe_trace,
        )
    except ImportError:
        pytest.skip("checkagent.core.tracer not importable")

    install_patches()
    try:
        begin_probe_trace()
        # Simulate something that would be traced — even a minimal call
        events = end_probe_trace()
        assert len(events) > 0, (
            "F-120: end_probe_trace() returned 0 events — tracer is still stubs only"
        )
    finally:
        uninstall_patches()


@pytest.mark.xfail(
    reason="F-120: tracer stubs — no events captured without real API calls"
)
def test_f120_tracer_stub_returns_empty():
    """F-120 confirmed: end_probe_trace() always returns empty list (stubs only)."""
    try:
        from checkagent.core.tracer import (
            install_patches, uninstall_patches,
            begin_probe_trace, end_probe_trace,
        )
    except ImportError:
        pytest.skip("checkagent.core.tracer not importable")

    install_patches()
    begin_probe_trace()
    events = end_probe_trace()
    uninstall_patches()
    # This xfail documents the known stub behavior
    assert len(events) > 0, "Tracer still returns 0 events (stubs only — F-120)"


# ---------------------------------------------------------------------------
# F-123 (still open): PyPI not updated to v0.3.1
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="F-123: PyPI still shows 0.3.0 as latest, git main is 0.3.1"
)
def test_f123_pypi_latest_is_031():
    """F-123: PyPI should show 0.3.1 as the latest version."""
    result = subprocess.run(
        ["pip", "index", "versions", "checkagent"],
        capture_output=True, text=True
    )
    # pip index versions output: "checkagent (0.3.1)"
    assert "0.3.1" in result.stdout and "(0.3.1)" in result.stdout, (
        f"F-123: PyPI latest is not 0.3.1. pip output: {result.stdout[:200]}"
    )


# ---------------------------------------------------------------------------
# Real PydanticAI agent + LLM judge integration
# ---------------------------------------------------------------------------

def test_travel_agent_scan_with_llm_judge_runs_clean():
    """Real PydanticAI travel agent can be scanned with --llm-judge claude-code without error."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.travel_agent:travel_agent_callable",
         "--llm-judge", "claude-code", "--category", "scope", "--json"],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1), (
        f"scan returned unexpected exit code {result.returncode}\nstderr: {result.stderr[-300:]}"
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Travel agent scan produced invalid JSON: {e}\nstdout: {result.stdout[:400]}")
    assert data["summary"]["errors"] == 0, (
        f"Travel agent scan had errors: {data['summary']['errors']}"
    )


def test_travel_agent_llm_judge_evaluator_field():
    """Real agent scan: evaluator field is 'claude-code' in JSON summary."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.travel_agent:travel_agent_callable",
         "--llm-judge", "claude-code", "--category", "scope", "--json"],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    assert data["summary"].get("evaluator") == "claude-code", (
        f"evaluator should be 'claude-code', got: {data['summary'].get('evaluator')}"
    )
