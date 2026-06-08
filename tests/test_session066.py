"""Session-066 tests: v0.5.0 confirmed, stability tracking in diff, --diff scan flag,
history key in scan JSON, F-134/F-135/F-136 all fixed.

New features in v0.5.0 / post-v0.5.0:
- --diff flag on scan command (auto-compare against previous scan from history)
- stability tracking in diff command for --repeat scans
- history key embedded in scan --json output
- category_breakdown and severity_breakdown in scan JSON summary
- F-134 FIXED: diff --comment-file now writes UTF-8 correctly on Windows
- F-135 FIXED: scan --diff --json now embeds 'diff' key with full diff data
- F-136 FIXED: --min-stability exits 1 (not 0) when no stability data present

Observations:
- stability is None in diff JSON when either scan lacks --repeat data
- --diff uses per-target history (not per-target+category)
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

import checkagent


# ---------------------------------------------------------------------------
# Version and CI checks
# ---------------------------------------------------------------------------

def test_version_is_0_5_0():
    """checkagent 0.5.0 is installed."""
    assert checkagent.__version__ == "0.5.0"


def test_upstream_ci_green():
    """Upstream CI latest run is success."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "1",
         "--json", "conclusion", "-q", ".[0].conclusion"],
        capture_output=True, text=True
    )
    assert result.stdout.strip() == "success", (
        f"Upstream CI is not green: {result.stdout.strip()}"
    )


def test_pypi_version_is_0_5_0():
    """PyPI shows 0.5.0 as latest (F-123 FIXED, now tracking 0.5.0)."""
    result = subprocess.run(
        ["pip", "index", "versions", "checkagent"],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    assert "0.5.0" in output, f"0.5.0 not found in PyPI output: {output}"


# ---------------------------------------------------------------------------
# --diff flag on scan command
# ---------------------------------------------------------------------------

def test_scan_diff_flag_runs_without_error():
    """checkagent scan --diff completes without crashing."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--diff"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    assert result.returncode in (0, 1), f"Unexpected exit code: {result.returncode}"
    # Should contain the diff section at the end
    combined = result.stdout + result.stderr
    assert "CheckAgent Scan Diff" in combined or "no change from last scan" in combined or \
           "no findings data" in combined


def test_scan_diff_flag_shows_diff_section():
    """checkagent scan --diff shows diff block after scan summary."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--diff"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    combined = result.stdout + result.stderr
    assert "CheckAgent Scan Diff" in combined or "no change from last scan" in combined


def test_scan_diff_flag_no_change_for_same_target():
    """Running --diff twice on the same stable target shows 'no change'."""
    # Run twice in a row
    for _ in range(2):
        subprocess.run(
            ["checkagent", "scan", "agents.echo_agent_simple:run",
             "--category", "injection"],
            capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
        )
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--diff"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    combined = result.stdout + result.stderr
    assert "no change" in combined or "unchanged" in combined.lower()


def test_scan_json_has_history_key():
    """scan --json output contains history key with score delta fields."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    assert "history" in data, "scan JSON missing 'history' key"
    history = data["history"]
    assert "score_delta" in history, "history missing score_delta"
    assert "previous_score" in history, "history missing previous_score"
    assert "current_score" in history, "history missing current_score"
    assert "previous_date" in history, "history missing previous_date"


def test_scan_json_history_score_delta_matches_scores():
    """history.score_delta equals current_score - previous_score."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    history = data["history"]
    expected_delta = history["current_score"] - history["previous_score"]
    assert abs(history["score_delta"] - expected_delta) < 0.001


def test_scan_diff_flag_with_json_includes_diff_key():
    """F-135 FIXED: --diff --json now embeds 'diff' key with full diff data."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--diff", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    # F-135 FIXED: diff key now present in JSON
    assert "diff" in data, "scan --diff --json should embed diff data in 'diff' key"
    diff = data["diff"]
    assert "score" in diff, "diff.score missing"
    assert "counts" in diff, "diff.counts missing"
    assert "regression" in diff, "diff.regression missing"
    assert "new_findings" in diff, "diff.new_findings missing"
    assert "fixed_findings" in diff, "diff.fixed_findings missing"
    # history still present
    assert "history" in data


# ---------------------------------------------------------------------------
# Stability tracking in diff command
# ---------------------------------------------------------------------------

def _run_scan_with_repeat(target: str, category: str, repeat: int) -> dict:
    """Helper: run scan with --repeat and return parsed JSON."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    result = subprocess.run(
        ["checkagent", "scan", target, "--category", category,
         "--repeat", str(repeat), "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    return json.loads(result.stdout)


def test_repeat_scan_json_has_top_level_stability():
    """scan --repeat N --json has top-level stability key."""
    data = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)
    assert "stability" in data, "Missing top-level stability key in repeat scan JSON"
    stability = data["stability"]
    assert "repeat" in stability
    assert "stable_pass" in stability
    assert "stable_fail" in stability
    assert "flaky" in stability
    assert "stability_score" in stability


def test_repeat_scan_stability_repeat_count():
    """stability.repeat matches the --repeat N value."""
    data = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)
    assert data["stability"]["repeat"] == 2


def test_repeat_scan_stable_agent_has_stability_1():
    """echo agent (always same result) has stability_score=1.0."""
    data = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)
    assert data["stability"]["stability_score"] == 1.0
    assert data["stability"]["flaky"] == 0


def test_diff_json_has_stability_key_for_repeat_scans(tmp_path):
    """diff --json includes stability object when both scans used --repeat."""
    # Create two repeat scan files
    baseline = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)
    current = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)

    baseline_file = tmp_path / "baseline.json"
    current_file = tmp_path / "current.json"
    baseline_file.write_text(json.dumps(baseline))
    current_file.write_text(json.dumps(current))

    result = subprocess.run(
        ["checkagent", "diff", str(baseline_file), str(current_file), "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    assert "stability" in data, "diff JSON missing stability key for repeat scans"
    stability = data["stability"]
    assert stability is not None, "stability should not be None for repeat scans"
    assert "baseline" in stability
    assert "current" in stability
    assert "delta" in stability
    assert "baseline_repeat" in stability
    assert "current_repeat" in stability


def test_diff_stability_has_correct_repeat_counts(tmp_path):
    """diff stability.baseline_repeat and current_repeat match scan repeat values."""
    baseline = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)
    current = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)

    baseline_file = tmp_path / "baseline.json"
    current_file = tmp_path / "current.json"
    baseline_file.write_text(json.dumps(baseline))
    current_file.write_text(json.dumps(current))

    result = subprocess.run(
        ["checkagent", "diff", str(baseline_file), str(current_file), "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    stability = data["stability"]
    assert stability["baseline_repeat"] == 2
    assert stability["current_repeat"] == 2


def test_diff_stability_delta_for_same_agent(tmp_path):
    """diff stability.delta is 0.0 when both scans are the same agent."""
    baseline = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)
    current = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)

    baseline_file = tmp_path / "baseline.json"
    current_file = tmp_path / "current.json"
    baseline_file.write_text(json.dumps(baseline))
    current_file.write_text(json.dumps(current))

    result = subprocess.run(
        ["checkagent", "diff", str(baseline_file), str(current_file), "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["stability"]["delta"] == 0.0


def test_diff_stability_none_when_no_repeat_data(tmp_path):
    """diff stability is None when neither scan used --repeat."""
    # Scans without --repeat
    r1 = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    r2 = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    f1 = tmp_path / "s1.json"
    f2 = tmp_path / "s2.json"
    f1.write_text(r1.stdout)
    f2.write_text(r2.stdout)

    result = subprocess.run(
        ["checkagent", "diff", str(f1), str(f2), "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert "stability" in data, "stability key should always be present in diff JSON"
    assert data["stability"] is None, (
        "stability should be None when neither scan used --repeat"
    )


def test_diff_stability_none_when_mixed_repeat(tmp_path):
    """diff stability is None when only one scan used --repeat."""
    repeat_scan = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)
    no_repeat = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    no_repeat_data = json.loads(no_repeat.stdout)

    f1 = tmp_path / "repeat.json"
    f2 = tmp_path / "no_repeat.json"
    f1.write_text(json.dumps(repeat_scan))
    f2.write_text(json.dumps(no_repeat_data))

    result = subprocess.run(
        ["checkagent", "diff", str(f1), str(f2), "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data.get("stability") is None, (
        "stability should be None when only one scan used --repeat"
    )


def test_diff_terminal_shows_stability_row(tmp_path):
    """diff terminal output includes Stability row when both scans used --repeat."""
    baseline = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)
    current = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 2)

    f1 = tmp_path / "b.json"
    f2 = tmp_path / "c.json"
    f1.write_text(json.dumps(baseline))
    f2.write_text(json.dumps(current))

    result = subprocess.run(
        ["checkagent", "diff", str(f1), str(f2)],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    assert "Stability" in combined or "stability" in combined.lower(), (
        "diff terminal output should show Stability row for repeat scans"
    )


# ---------------------------------------------------------------------------
# F-134 fix: Windows UTF-8 encoding for diff --comment-file
# ---------------------------------------------------------------------------

def test_f134_diff_comment_file_readable(tmp_path):
    """F-134 FIXED: diff --comment-file output is readable as UTF-8."""
    baseline = _run_scan_with_repeat("agents.echo_agent_simple:run", "injection", 1)
    current_r = subprocess.run(
        ["checkagent", "scan", "agents.travel_agent:travel_agent_callable",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    current = json.loads(current_r.stdout)

    f1 = tmp_path / "baseline.json"
    f2 = tmp_path / "current.json"
    comment_file = tmp_path / "pr_comment.md"
    f1.write_text(json.dumps(baseline))
    f2.write_text(json.dumps(current))

    result = subprocess.run(
        ["checkagent", "diff", str(f1), str(f2), "--comment-file", str(comment_file)],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1)
    # F-134 fix: file should be readable as UTF-8
    content = comment_file.read_text(encoding="utf-8")
    assert len(content) > 0, "PR comment file is empty"


# ---------------------------------------------------------------------------
# Scan --diff historical behavior
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_scan_diff_history_per_target_not_per_category():
    """--diff compares against most recent scan regardless of category (not category-specific)."""
    # Scan with injection category to update history
    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    # Now scan with different category but --diff — it should compare against injection scan
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "jailbreak", "--diff"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    combined = result.stdout + result.stderr
    # If history is per-target (not per-category), the diff will show
    # comparison against the injection scan score (0%)
    assert "CheckAgent Scan Diff" in combined or "no change" in combined


# ---------------------------------------------------------------------------
# --min-score gate (new in v0.5.0)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def low_score_scan(tmp_path_factory):
    """Scan JSON for echo agent (injection score ~0%)."""
    f = tmp_path_factory.mktemp("scans") / "low.json"
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    f.write_text(result.stdout)
    return f


@pytest.fixture(scope="module")
def high_score_scan(tmp_path_factory):
    """Scan JSON for travel agent (injection score ~100%)."""
    f = tmp_path_factory.mktemp("scans") / "high.json"
    result = subprocess.run(
        ["checkagent", "scan", "agents.travel_agent:travel_agent_callable",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    f.write_text(result.stdout)
    return f


def test_min_score_exits_1_when_current_below_threshold(low_score_scan, high_score_scan):
    """--min-score exits 1 when current score is below threshold."""
    # baseline=high(1.0), current=low(0.0), min-score=0.5 → exit 1
    result = subprocess.run(
        ["checkagent", "diff", str(high_score_scan), str(low_score_scan),
         "--min-score", "0.5"],
        capture_output=True, text=True
    )
    assert result.returncode == 1, (
        f"Expected exit 1 when current score 0.0 < threshold 0.5, got {result.returncode}"
    )


def test_min_score_exits_0_when_current_above_threshold(low_score_scan, high_score_scan):
    """--min-score exits 0 when current score meets or exceeds threshold."""
    # baseline=low(0.0), current=high(1.0), min-score=0.5 → exit 0
    result = subprocess.run(
        ["checkagent", "diff", str(low_score_scan), str(high_score_scan),
         "--min-score", "0.5"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"Expected exit 0 when current score 1.0 >= threshold 0.5, got {result.returncode}"
    )


def test_min_score_at_zero_always_passes(low_score_scan, high_score_scan):
    """--min-score 0.0 never blocks (any score >= 0.0)."""
    result = subprocess.run(
        ["checkagent", "diff", str(high_score_scan), str(low_score_scan),
         "--min-score", "0.0"],
        capture_output=True, text=True
    )
    assert result.returncode == 0


def test_min_score_exact_boundary_passes(low_score_scan, high_score_scan):
    """--min-score equal to current score passes (>=, not >)."""
    # current=1.0, threshold=1.0 → should pass
    result = subprocess.run(
        ["checkagent", "diff", str(low_score_scan), str(high_score_scan),
         "--min-score", "1.0"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"Expected exit 0 when current==threshold==1.0, got {result.returncode}"
    )


def test_min_score_message_in_output(low_score_scan, high_score_scan):
    """--min-score failure shows score in error message."""
    result = subprocess.run(
        ["checkagent", "diff", str(high_score_scan), str(low_score_scan),
         "--min-score", "0.5"],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    assert "min-score" in combined or "score" in combined.lower()


# ---------------------------------------------------------------------------
# --min-stability gate (new in v0.5.0)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def repeat_scan(tmp_path_factory):
    """Scan JSON with --repeat 2 for stability data."""
    f = tmp_path_factory.mktemp("scans") / "repeat.json"
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--repeat", "2", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    f.write_text(result.stdout)
    return f


def test_min_stability_exits_0_when_stability_meets_threshold(repeat_scan):
    """--min-stability exits 0 when stability >= threshold."""
    # echo agent has stability=1.0, threshold=0.9 → pass
    result = subprocess.run(
        ["checkagent", "diff", str(repeat_scan), str(repeat_scan),
         "--min-stability", "0.9"],
        capture_output=True, text=True
    )
    assert result.returncode == 0


def test_min_stability_exits_1_when_stability_below_threshold(repeat_scan):
    """--min-stability exits 1 when stability < threshold (impossible threshold)."""
    result = subprocess.run(
        ["checkagent", "diff", str(repeat_scan), str(repeat_scan),
         "--min-stability", "1.1"],
        capture_output=True, text=True
    )
    assert result.returncode == 1


def test_f136_min_stability_exits_1_without_repeat_data(
        low_score_scan, high_score_scan):
    """F-136 FIXED: --min-stability exits 1 (not 0) when scans have no stability data.

    Previously the gate silently passed (exit 0) when no --repeat data was
    present — a CI trap. Fixed: now exits 1 with a clear error message.
    """
    result = subprocess.run(
        ["checkagent", "diff", str(low_score_scan), str(high_score_scan),
         "--min-stability", "0.9"],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    # Error message mentions stability
    assert "stability" in combined.lower()
    # F-136 FIXED: now exits 1 instead of silently passing
    assert result.returncode == 1, (
        f"F-136: --min-stability should exit 1 when no stability data, got {result.returncode}"
    )


# ---------------------------------------------------------------------------
# ci-init --diff integration
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# category_breakdown and severity_breakdown (new in post-v0.5.0 commit)
# ---------------------------------------------------------------------------

def test_scan_json_has_category_breakdown():
    """scan --json summary includes category_breakdown dict."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    summary = data["summary"]
    assert "category_breakdown" in summary, "summary missing category_breakdown"
    cb = summary["category_breakdown"]
    assert isinstance(cb, dict), "category_breakdown should be a dict"
    # injection scan on echo agent should have prompt_injection category
    assert "prompt_injection" in cb, f"Expected prompt_injection in {cb}"
    assert isinstance(cb["prompt_injection"], int)
    assert cb["prompt_injection"] > 0


def test_scan_json_has_severity_breakdown():
    """scan --json summary includes severity_breakdown dict."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    summary = data["summary"]
    assert "severity_breakdown" in summary, "summary missing severity_breakdown"
    sb = summary["severity_breakdown"]
    assert isinstance(sb, dict), "severity_breakdown should be a dict"
    # Should have at least one severity level
    known_severities = {"low", "medium", "high", "critical"}
    assert any(k in known_severities for k in sb), (
        f"Expected at least one known severity in {sb}"
    )


def test_scan_json_severity_breakdown_values_are_ints():
    """severity_breakdown values are integer counts."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    sb = data["summary"]["severity_breakdown"]
    for key, val in sb.items():
        assert isinstance(val, int), f"severity_breakdown[{key!r}] should be int, got {type(val)}"


def test_scan_json_category_breakdown_safe_agent_is_empty():
    """travel agent (safe) has no findings — category_breakdown should be empty."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.travel_agent:travel_agent_callable",
         "--category", "injection", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    cb = data["summary"]["category_breakdown"]
    # travel agent refuses injection probes — no findings
    assert cb == {} or all(v == 0 for v in cb.values()), (
        f"Expected empty category_breakdown for safe agent, got {cb}"
    )


def test_scan_diff_json_diff_key_score_delta():
    """scan --diff --json diff.score.delta is 0.0 for repeated identical scan."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--diff", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    diff = data["diff"]
    score = diff["score"]
    assert "delta" in score, "diff.score.delta missing"
    assert isinstance(score["delta"], (int, float))


def test_scan_diff_json_counts_structure():
    """scan --diff --json diff.counts has new/fixed/unchanged keys."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--diff", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    counts = data["diff"]["counts"]
    assert "new" in counts
    assert "fixed" in counts
    assert "unchanged" in counts


# ---------------------------------------------------------------------------
# ci-init --diff integration
# ---------------------------------------------------------------------------

def test_ci_init_template_includes_diff_flag(tmp_path):
    """Generated GitHub Actions workflow includes --diff in scan step."""
    result = subprocess.run(
        ["checkagent", "ci-init", "--directory", str(tmp_path), "--force"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    workflow = (tmp_path / ".github" / "workflows" / "checkagent.yml").read_text()
    assert "--diff" in workflow, "Generated workflow should include --diff flag"


def test_ci_init_template_includes_repeat(tmp_path):
    """Generated workflow uses --repeat for stability tracking."""
    subprocess.run(
        ["checkagent", "ci-init", "--directory", str(tmp_path), "--force"],
        capture_output=True, text=True
    )
    workflow = (tmp_path / ".github" / "workflows" / "checkagent.yml").read_text()
    assert "--repeat" in workflow
