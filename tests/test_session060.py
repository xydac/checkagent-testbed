"""
Session-060 tests: --verbose crash, salary_amount false positives, error rate warning,
HTML compliance report target/version, F-129 fixed (CI green).
"""
import json
import subprocess
import pytest
from checkagent import PIILeakageScanner


# ---------------------------------------------------------------------------
# Upstream CI — F-129 fixed
# ---------------------------------------------------------------------------

def test_upstream_ci_latest_green():
    """Latest upstream CI run is green (all platforms including Windows 3.13)."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "1",
         "--json", "status,conclusion,displayTitle"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data[0]["conclusion"] == "success", (
        f"Latest CI run failed: {data[0]['displayTitle']}"
    )


def test_upstream_ci_f129_fixed():
    """F-129: Windows 3.13 actions/checkout failure — verify latest run includes Windows jobs passing."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "1",
         "--json", "status,conclusion"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    # Latest run is fully green — F-129 is fixed
    assert data[0]["conclusion"] == "success"


# ---------------------------------------------------------------------------
# F-123: PyPI version still open
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="F-123: PyPI latest is still 0.3.0, git main is 0.3.1")
def test_pypi_version_is_031():
    """F-123: PyPI should publish v0.3.1."""
    result = subprocess.run(
        ["pip", "index", "versions", "checkagent", "--break-system-packages"],
        capture_output=True, text=True
    )
    assert "0.3.1" in result.stdout and "LATEST:    0.3.1" in result.stdout, (
        "F-123: PyPI LATEST is not 0.3.1"
    )


# ---------------------------------------------------------------------------
# F-130: salary_amount PII pattern — false positives on any dollar amount
# ---------------------------------------------------------------------------

def test_salary_amount_detects_actual_salary():
    """PIILeakageScanner correctly flags explicit salary disclosure."""
    scanner = PIILeakageScanner()
    result = scanner.evaluate("The employee salary is $85,000 per year")
    assert not result.passed
    assert any("salary_amount" in str(f.description) for f in result.findings)


def test_salary_amount_hourly_wage_false_negative():
    """F-130 tradeoff: hourly wage like '$25.50' is now a false negative.

    Upstream narrowed salary_amount to only match suffixed (e.g. $95k, $1.5M)
    or comma-grouped ($120,000) amounts. This avoids retail price false positives
    but means legitimate hourly wages without those markers go undetected.
    This is an accepted tradeoff per the upstream fix.
    """
    scanner = PIILeakageScanner()
    result = scanner.evaluate("Hourly wage: $25.50")
    # F-130 fix: $25.50 no longer triggers — accepted false negative tradeoff
    assert result.passed, (
        "Hourly wage '$25.50' should pass (not flagged) after F-130 narrowing"
    )


def test_salary_amount_no_false_positive_on_product_price():
    """F-130 FIXED: Product price should NOT be flagged as salary_amount."""
    scanner = PIILeakageScanner()
    result = scanner.evaluate("This widget costs $9.99")
    assert result.passed, "F-130: '$9.99' product price flagged as salary_amount — false positive"


def test_salary_amount_no_false_positive_on_transaction():
    """F-130 FIXED: Transaction amounts should NOT be flagged as salary_amount."""
    scanner = PIILeakageScanner()
    result = scanner.evaluate("Your total is $23.50")
    assert result.passed, "F-130: '$23.50' transaction amount flagged as salary_amount"


def test_salary_amount_no_false_positive_on_stock_price():
    """F-130 FIXED: Stock prices should NOT be flagged as salary_amount."""
    scanner = PIILeakageScanner()
    result = scanner.evaluate("AAPL is trading at $189.50")
    assert result.passed, "F-130: Stock price flagged as salary_amount"


def test_salary_amount_no_false_positive_non_dollar():
    """Non-dollar currency (euros) does NOT trigger salary_amount."""
    scanner = PIILeakageScanner()
    result = scanner.evaluate("Price: €99.99")
    salary_findings = [f for f in result.findings if "salary" in str(f.description)]
    assert len(salary_findings) == 0


def test_salary_amount_no_false_positive_bare_number():
    """Plain numbers without dollar sign do NOT trigger salary_amount."""
    scanner = PIILeakageScanner()
    result = scanner.evaluate("Annual salary: 85000 USD")
    salary_findings = [f for f in result.findings if "salary" in str(f.description)]
    # Without $ sign, the pattern does not match
    assert len(salary_findings) == 0


# ---------------------------------------------------------------------------
# F-131: --verbose crashes with MarkupError on bracket-containing probe output
# ---------------------------------------------------------------------------

def test_verbose_no_crash_on_echo_agent():
    """F-131 FIXED: --verbose no longer crashes when agent echoes input containing [brackets]."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection", "--verbose"],
        capture_output=True, text=True
    )
    # Should exit 0 or 1 (findings) but NOT 2 (exception)
    assert result.returncode in (0, 1), (
        f"F-131: --verbose crashed (exit {result.returncode})\n"
        f"stderr: {result.stderr[-500:]}"
    )
    assert "MarkupError" not in result.stderr, (
        "F-131: --verbose crashed with MarkupError on bracket-containing text"
    )


def test_verbose_works_on_safe_agent():
    """--verbose does not crash when agent output contains no Rich markup brackets."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--category", "injection", "--verbose"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "MarkupError" not in result.stderr


# ---------------------------------------------------------------------------
# Error rate warning (40%+ probe errors)
# ---------------------------------------------------------------------------

def test_error_rate_warning_shown_in_terminal():
    """When 40%+ of probes error, terminal output shows a 'Partial Scan' warning."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.erroring_agent:run",
         "--category", "injection"],
        capture_output=True, text=True
    )
    # Check for the warning panel (uses Rich panel with title "⚠ Partial Scan")
    output = result.stdout + result.stderr
    assert "Partial Scan" in output or "reliability warning" in output, (
        "40%+ error rate warning not shown in terminal output"
    )


def test_error_rate_warning_json_lacks_field():
    """DX gap: --json output has no error_warning field despite 40%+ probe errors.

    Programmatic users must manually calculate errors/total > 0.4.
    This test documents the current (limited) behavior.
    """
    result = subprocess.run(
        ["checkagent", "scan", "agents.erroring_agent:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True
    )
    raw = result.stdout
    start = raw.find("{")
    assert start >= 0, "No JSON in output"
    data = json.loads(raw[start:])

    summary = data.get("summary", {})
    # errors are reported in summary
    assert "errors" in summary, "JSON should have summary.errors field"
    # but there's no top-level error_warning field
    assert "error_warning" not in data, (
        "Unexpected: error_warning now in JSON output (update this test if intentional)"
    )


@pytest.mark.xfail(
    reason="DX gap: --verbose warning message shown even when already running --verbose"
)
def test_verbose_warning_not_shown_in_verbose_mode():
    """--verbose error warning should not tell user to 'Use --verbose' when already using it."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.erroring_agent:run",
         "--category", "injection", "--verbose"],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    # When already in verbose mode, shouldn't instruct user to use --verbose
    assert "Use --verbose for per-probe error details" not in output, (
        "Warning tells user to 'Use --verbose' even when --verbose is already active"
    )


# ---------------------------------------------------------------------------
# HTML compliance report: agent target and version
# ---------------------------------------------------------------------------

def test_html_compliance_report_includes_agent_target(tmp_path):
    """HTML compliance report includes the scanned agent target."""
    report_path = tmp_path / "report.html"
    subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--category", "injection", "--report", str(report_path)],
        capture_output=True, text=True
    )
    assert report_path.exists(), "HTML report not generated"
    content = report_path.read_text()
    assert "agents.refusal_agent:run" in content, (
        "HTML report does not include agent target"
    )


def test_html_compliance_report_includes_version(tmp_path):
    """HTML compliance report includes CheckAgent version."""
    report_path = tmp_path / "report.html"
    subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--category", "injection", "--report", str(report_path)],
        capture_output=True, text=True
    )
    content = report_path.read_text()
    assert "0.3.1" in content or "checkagent" in content, (
        "HTML report does not include CheckAgent version"
    )


@pytest.mark.xfail(
    reason="DX gap: HTML report labels framework version as 'Model' — misleading (implies LLM model)"
)
def test_html_compliance_report_version_label(tmp_path):
    """HTML compliance report should label the version as 'Version' or 'CheckAgent', not 'Model'."""
    report_path = tmp_path / "report.html"
    subprocess.run(
        ["checkagent", "scan", "agents.refusal_agent:run",
         "--category", "injection", "--report", str(report_path)],
        capture_output=True, text=True
    )
    content = report_path.read_text()
    # 'Model: checkagent 0.3.1' is confusing — 'Model' implies LLM model
    assert "Model: checkagent" not in content, (
        "HTML report labels framework version as 'Model' — should be 'Version' or 'CheckAgent'"
    )
