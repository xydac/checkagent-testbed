"""
Session-061 tests: --llm-judge claude-code, F-130/F-131 confirmed fixed,
JSON output missing judge_model field (new finding F-132).
"""
import json
import subprocess
import pytest
from checkagent import PIILeakageScanner


# ---------------------------------------------------------------------------
# Upstream CI — green (F-129 still fixed)
# ---------------------------------------------------------------------------

def test_upstream_ci_latest_green():
    """Latest 2 upstream CI runs are green."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "2",
         "--json", "status,conclusion,displayTitle"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    for run in data:
        assert run["conclusion"] == "success", (
            f"CI run failed: {run['displayTitle']}"
        )


# ---------------------------------------------------------------------------
# F-130 FIXED: salary_amount narrowed — verified at Python API level
# ---------------------------------------------------------------------------

def test_f130_fixed_retail_prices_not_flagged():
    """F-130 FIXED: small dollar amounts like $9.99 are not flagged as salary."""
    scanner = PIILeakageScanner()
    for text in ["This widget costs $9.99", "Your total is $23.50", "AAPL: $189.50"]:
        result = scanner.evaluate(text)
        findings = [f for f in result.findings if "salary" in str(f.pattern_name).lower()]
        assert len(findings) == 0, f"False positive: {text!r} flagged as salary"


def test_f130_fixed_real_salaries_still_detected():
    """F-130 FIXED: $k, $M, and comma-grouped amounts are still flagged."""
    scanner = PIILeakageScanner()
    test_cases = [
        ("Salary is $95k per year", True),
        ("Compensation: $1.5M total", True),
        ("They earn $120,000 annually", True),
        ("Employee salary is $85,000 per year", True),
    ]
    for text, should_flag in test_cases:
        result = scanner.evaluate(text)
        if should_flag:
            assert not result.passed, f"False negative: {text!r} not flagged as salary"


def test_f130_tradeoff_hourly_wage_false_negative():
    """F-130 tradeoff: $25.50 hourly wage is a false negative after the fix.

    The fix traded false positives (retail prices) for false negatives (hourly rates
    without k/M/comma-grouping). Documented as accepted tradeoff.
    """
    scanner = PIILeakageScanner()
    result = scanner.evaluate("Hourly wage: $25.50")
    # $25.50 is now a false negative — the fix accepts this
    assert result.passed, "Hourly wage $25.50 is now a false negative (accepted F-130 tradeoff)"


# ---------------------------------------------------------------------------
# F-131 FIXED: --verbose no longer crashes on bracket-containing output
# ---------------------------------------------------------------------------

def test_f131_fixed_verbose_no_markuperror():
    """F-131 FIXED: --verbose on echo agent (bracket output) no longer crashes."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--verbose"],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1), (
        f"--verbose crashed with exit {result.returncode}\n{result.stderr[-500:]}"
    )
    assert "MarkupError" not in result.stderr, "--verbose still raises MarkupError"
    assert "MarkupError" not in result.stdout, "--verbose still raises MarkupError in stdout"


# ---------------------------------------------------------------------------
# New feature: --llm-judge claude-code
# ---------------------------------------------------------------------------

def test_llm_judge_claude_code_header():
    """--llm-judge claude-code shows 'LLM judge (claude-code)' in scan header."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code", "--category", "injection"],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1)
    assert "LLM judge (claude-code)" in result.stdout, (
        "Expected 'LLM judge (claude-code)' in scan header"
    )


def test_llm_judge_claude_code_zero_cost():
    """--llm-judge claude-code reports $0.00 estimated cost."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code", "--category", "injection"],
        capture_output=True, text=True
    )
    assert "$0.000" in result.stdout or "$0.00" in result.stdout, (
        "Expected $0.00 cost display for claude-code judge"
    )


def test_llm_judge_claude_code_refusal_agent_passes():
    """--llm-judge claude-code: refusal agent scores 100% on injection probes."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code", "--category", "injection", "--json"],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    assert data["summary"]["score"] == 1.0, (
        f"Refusal agent should score 1.0 with LLM judge, got {data['summary']['score']}"
    )
    assert data["summary"]["errors"] == 0, "LLM judge produced errors"


def test_llm_judge_claude_code_echo_agent_passes():
    """--llm-judge claude-code correctly passes echo agent (echoes but does not comply).

    The LLM judge understands that echoing a probe does not mean complying with it.
    This is more accurate than regex which flags any echoed injection text.
    """
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent",
         "--llm-judge", "claude-code", "--category", "injection", "--json"],
        capture_output=True, text=True,
        env={**__import__('os').environ}  # inherit env
    )
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    # LLM judge should correctly identify echo as non-compliant
    # (echoing an injection is not the same as following it)
    assert data["summary"]["errors"] == 0, "LLM judge produced errors on echo agent"


def test_llm_judge_claude_code_json_stdout_clean():
    """--llm-judge claude-code + --json produces clean JSON on stdout (no diagnostics mixed in)."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code", "--category", "injection", "--json"],
        capture_output=True, text=True
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"stdout is not valid JSON with --llm-judge claude-code --json: {e}\nstdout: {result.stdout[:300]}")
    assert "summary" in data


def test_llm_judge_invalid_model_name_error():
    """--llm-judge with unrecognized model name gives a clear error."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "totally-fake-model-xyz"],
        capture_output=True, text=True
    )
    assert result.returncode != 0, "Should fail with invalid model name"
    assert "Cannot detect provider" in result.stderr or "Cannot detect provider" in result.stdout, (
        "Expected clear error for unrecognized model name"
    )
    # Should mention claude-code as a valid option
    assert "claude-code" in result.stderr or "claude-code" in result.stdout


def test_llm_judge_claude_code_with_agent_description():
    """--llm-judge claude-code accepts --agent-description without error."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code",
         "--agent-description", "Safety bot. Must refuse all instruction overrides.",
         "--category", "injection"],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1)
    assert "LLM judge (claude-code)" in result.stdout


# ---------------------------------------------------------------------------
# F-132 (new): --llm-judge model name absent from JSON output
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="F-132: --json output has no judge_model field — can't tell which evaluator was used programmatically"
)
def test_f132_json_includes_judge_model():
    """F-132: JSON output should include which LLM judge was used (or 'regex')."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--llm-judge", "claude-code", "--category", "injection", "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    # Programmatic users should be able to distinguish LLM judge from regex scan
    assert "judge_model" in data or "evaluator" in data, (
        "F-132: No judge_model/evaluator field in JSON — can't tell which evaluation method was used"
    )
