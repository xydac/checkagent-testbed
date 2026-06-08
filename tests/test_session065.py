"""Session-065 tests: sparkline history command, F-133 fixed (--comment-file evaluator),
multi-category LLM judge scan, v0.4.0 confirmed, checkagent diff command.

New features in session-065 (post-v0.4.0 commit):
- history command: sparkline trend chart + score summary text
- diff command: compare two scan results, --fail-on-new, --comment-file, --json

Fixes confirmed this session:
- F-133 FIXED: --comment-file now includes Evaluator row when --llm-judge is used
- F-123 FIXED: PyPI now has v0.4.0 (confirmed in session-063, re-confirmed here)

New findings this session:
- F-134: diff --comment-file generates UTF-8 with emoji; Windows cp1252 UnicodeDecodeError (upstream CI red)
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

@pytest.mark.xfail(reason="Version upgraded to 0.5.0 in session-066")
def test_version_is_0_4_0():
    """checkagent 0.4.0 is installed."""
    assert checkagent.__version__ == "0.4.0"


def test_upstream_ci_green():
    """Upstream CI latest run is success."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "1",
         "--json", "status,conclusion"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert len(data) > 0
    assert data[0]["conclusion"] == "success", f"CI not green: {data[0]}"


# ---------------------------------------------------------------------------
# F-133 FIXED: --comment-file includes Evaluator row with --llm-judge
# ---------------------------------------------------------------------------

def test_f133_comment_file_includes_evaluator_with_llm_judge(tmp_path):
    """F-133 FIXED: --comment-file PR markdown now includes Evaluator row
    when --llm-judge is used."""
    comment_file = tmp_path / "pr_comment.md"
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection",
         "--llm-judge", "claude-code",
         "--comment-file", str(comment_file)],
        capture_output=True, text=True
    )
    assert comment_file.exists(), "comment file not created"
    content = comment_file.read_text()
    assert "Evaluator" in content, \
        f"'Evaluator' row absent from PR comment. Got:\n{content[:600]}"
    assert "LLM judge" in content or "claude-code" in content, \
        f"LLM judge info absent from PR comment. Got:\n{content[:600]}"


def test_comment_file_without_llm_judge_has_no_evaluator_row(tmp_path):
    """Without --llm-judge, the PR comment has no Evaluator row (expected asymmetry)."""
    comment_file = tmp_path / "pr_comment.md"
    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection",
         "--comment-file", str(comment_file)],
        capture_output=True, text=True
    )
    assert comment_file.exists(), "comment file not created"
    content = comment_file.read_text()
    # Without LLM judge, no evaluator row is added — evaluator is implied to be regex
    assert "Evaluator" not in content, \
        f"Unexpected Evaluator row in non-llm-judge comment:\n{content[:600]}"


def test_f133_json_output_has_evaluator_field_with_llm_judge():
    """F-133 FIXED: JSON output has summary.evaluator field when --llm-judge is used."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection",
         "--llm-judge", "claude-code",
         "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert "evaluator" in data["summary"], \
        f"evaluator field missing from summary: {data['summary']}"
    assert data["summary"]["evaluator"] == "claude-code"


# ---------------------------------------------------------------------------
# sparkline history command (new in post-v0.4.0 commit)
# ---------------------------------------------------------------------------

def test_history_command_shows_trend_line():
    """history command now shows a Trend: sparkline line below the table."""
    result = subprocess.run(
        ["checkagent", "history", "agents.echo_agent_simple:run", "--limit", "5"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    output = result.stdout
    assert "Trend:" in output, \
        f"No 'Trend:' line found in history output:\n{output}"


def test_history_trend_shows_score_summary():
    """Trend line includes a score summary (stable/improved/declined + percentage)."""
    result = subprocess.run(
        ["checkagent", "history", "agents.echo_agent_simple:run", "--limit", "5"],
        capture_output=True, text=True
    )
    output = result.stdout
    # Should contain either "stable", "improved", "declined" and a percentage
    has_direction = any(w in output for w in ["stable", "improved", "declined", "regressed"])
    assert has_direction, \
        f"No trend direction word (stable/improved/declined/regressed) in output:\n{output}"
    assert "%" in output, f"No percentage in trend summary:\n{output}"


def test_history_limit_flag_controls_row_count():
    """history --limit N shows at most N rows in the table."""
    result = subprocess.run(
        ["checkagent", "history", "agents.echo_agent_simple:run", "--limit", "3"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    output = result.stdout
    # Count table data rows (lines with a date pattern)
    data_rows = [line for line in output.splitlines() if "2026-" in line]
    assert len(data_rows) <= 3, \
        f"Expected at most 3 rows, got {len(data_rows)}"
    assert "3 scan(s) shown" in output or len(data_rows) <= 3


def test_history_unknown_target_friendly_message():
    """history for a target with no history gives a friendly message, not an error."""
    result = subprocess.run(
        ["checkagent", "history", "agents.nonexistent:run"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "No scan history found" in result.stdout or "No scan history" in result.stdout


def test_history_score_delta_markers_in_table():
    """Table rows show ↑ or ↓ markers when score changes between consecutive scans."""
    result = subprocess.run(
        ["checkagent", "history", "agents.echo_agent_simple:run", "--limit", "10"],
        capture_output=True, text=True
    )
    output = result.stdout
    # The history has mixed 0% and 100% scores, so we expect delta markers
    has_up = "↑" in output
    has_down = "↓" in output
    assert has_up or has_down, \
        f"No delta markers (↑↓) found in history output:\n{output}"


# ---------------------------------------------------------------------------
# Multi-category scan with LLM judge
# ---------------------------------------------------------------------------

def test_travel_agent_multi_category_llm_judge_passes():
    """travel_agent scores 100% across injection+jailbreak+pii+scope with LLM judge."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.travel_agent:travel_agent_callable",
         "--category", "injection",
         "--category", "jailbreak",
         "--category", "pii",
         "--category", "scope",
         "--llm-judge", "claude-code",
         "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    s = data["summary"]
    assert s["score"] == 1.0, \
        f"Expected 100% score, got {s['score']:.0%}. Findings: {data.get('findings', [])}"
    assert s["evaluator"] == "claude-code"


def test_llm_judge_and_comment_file_combination(tmp_path):
    """--llm-judge + --comment-file combination works cleanly end-to-end."""
    comment_file = tmp_path / "output.md"
    result = subprocess.run(
        ["checkagent", "scan", "agents.travel_agent:travel_agent_callable",
         "--category", "scope",
         "--llm-judge", "claude-code",
         "--comment-file", str(comment_file),
         "--json"],
        capture_output=True, text=True
    )
    # JSON should be clean
    data = json.loads(result.stdout)
    assert "evaluator" in data["summary"]

    # Comment file should mention evaluator
    content = comment_file.read_text(encoding="utf-8")
    assert "Evaluator" in content
    assert "claude-code" in content or "LLM judge" in content


# ---------------------------------------------------------------------------
# checkagent diff command (new post-v0.4.0)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def scan_files(tmp_path_factory):
    """Generate two scan JSON files: echo (0%) and travel agent (100%)."""
    d = tmp_path_factory.mktemp("scans")
    bad = d / "echo_scan.json"
    good = d / "travel_scan.json"

    r = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True
    )
    bad.write_text(r.stdout, encoding="utf-8")

    r = subprocess.run(
        ["checkagent", "scan", "agents.travel_agent:travel_agent_callable",
         "--category", "injection", "--llm-judge", "claude-code", "--json"],
        capture_output=True, text=True
    )
    good.write_text(r.stdout, encoding="utf-8")

    return bad, good


def test_diff_improved_score(scan_files):
    """diff shows score improvement when current is better than baseline."""
    bad, good = scan_files
    result = subprocess.run(
        ["checkagent", "diff", str(bad), str(good), "--json"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["score"]["baseline"] == 0.0
    assert data["score"]["current"] == 1.0
    assert data["score"]["delta"] == 1.0


def test_diff_regression_detected(scan_files):
    """diff detects regression when current is worse than baseline."""
    bad, good = scan_files
    result = subprocess.run(
        ["checkagent", "diff", str(good), str(bad), "--json"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["regression"] is True
    assert data["counts"]["new"] > 0


def test_diff_fail_on_new_exits_1_when_regression(scan_files):
    """--fail-on-new exits with code 1 when new findings (regressions) detected."""
    bad, good = scan_files
    result = subprocess.run(
        ["checkagent", "diff", str(good), str(bad), "--fail-on-new"],
        capture_output=True, text=True
    )
    assert result.returncode == 1, \
        f"Expected exit 1 for regression, got {result.returncode}"


def test_diff_fail_on_new_exits_0_when_improved(scan_files):
    """--fail-on-new exits with code 0 when no new findings (improvement or stable)."""
    bad, good = scan_files
    result = subprocess.run(
        ["checkagent", "diff", str(bad), str(good), "--fail-on-new"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, \
        f"Expected exit 0 for improvement, got {result.returncode}"


def test_diff_identical_scans(scan_files):
    """diff of identical files shows zero new/fixed/unchanged findings."""
    bad, _ = scan_files
    result = subprocess.run(
        ["checkagent", "diff", str(bad), str(bad), "--json"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["score"]["delta"] == 0.0
    assert data["counts"]["new"] == 0
    assert data["counts"]["fixed"] == 0
    assert data["regression"] is False


def test_diff_comment_file_created(scan_files, tmp_path):
    """diff --comment-file creates a GitHub PR comment markdown file."""
    bad, good = scan_files
    out = tmp_path / "diff.md"
    result = subprocess.run(
        ["checkagent", "diff", str(bad), str(good), "--comment-file", str(out)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert out.exists(), "comment file not created"
    content = out.read_text(encoding="utf-8")
    assert "CheckAgent" in content
    assert "Score" in content


def test_diff_comment_file_is_utf8(scan_files, tmp_path):
    """diff --comment-file output is valid UTF-8 (F-134: Windows cp1252 can't decode it)."""
    bad, good = scan_files
    out = tmp_path / "diff.md"
    subprocess.run(
        ["checkagent", "diff", str(bad), str(good), "--comment-file", str(out)],
        capture_output=True, text=True
    )
    # This is what the upstream CI test does WITHOUT encoding= -- fails on Windows
    # We read with explicit utf-8 here; the bug is that users who call read_text()
    # without encoding on Windows will get UnicodeDecodeError (F-134)
    raw_bytes = out.read_bytes()
    raw_bytes.decode("utf-8")  # Should not raise


def test_diff_json_structure(scan_files):
    """diff --json output has expected top-level keys."""
    bad, good = scan_files
    result = subprocess.run(
        ["checkagent", "diff", str(bad), str(good), "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    for key in ("baseline_target", "current_target", "score", "probes",
                 "new_findings", "fixed_findings", "unchanged_findings",
                 "counts", "regression"):
        assert key in data, f"Missing key '{key}' in diff JSON output"


def test_diff_targets_shown_in_json(scan_files):
    """diff --json records the target names from each scan file."""
    bad, good = scan_files
    result = subprocess.run(
        ["checkagent", "diff", str(bad), str(good), "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["baseline_target"] == "agents.echo_agent_simple:run"
    assert data["current_target"] == "agents.travel_agent:travel_agent_callable"
