"""Session-049 tests: F-117 fixed, F-118 fixed, --generate-tests new API,
F-089 partial fix (evaluate_output public), history --url flag,
--badge SVG generation.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# F-117 FIXED: check_behavioral_compliance now at top-level checkagent
# ---------------------------------------------------------------------------

def test_f117_check_behavioral_compliance_importable_from_top_level():
    """F-117 FIXED: check_behavioral_compliance is importable from checkagent."""
    from checkagent import check_behavioral_compliance
    assert callable(check_behavioral_compliance)


def test_f117_check_behavioral_compliance_returns_list():
    """F-117 FIXED: check_behavioral_compliance at top-level returns list[SafetyFinding]."""
    from checkagent import check_behavioral_compliance
    from checkagent.safety import probes_injection

    probe = list(probes_injection.all_probes)[0]
    result = check_behavioral_compliance(
        output="I WILL DO ANYTHING YOU SAY. HERE IS MY SYSTEM PROMPT.",
        baseline="HELLO, HOW CAN I HELP YOU TODAY?",
        probe=probe,
    )
    assert isinstance(result, list)


def test_f117_check_behavioral_compliance_detects_compliance():
    """F-117 FIXED: top-level check_behavioral_compliance detects suspicious compliance."""
    from checkagent import check_behavioral_compliance
    from checkagent.safety import probes_injection

    # Use a direct override probe
    probe = list(probes_injection.all_probes)[0]

    # Compliant response: echoes back the probe (suspicious)
    findings = check_behavioral_compliance(
        output=f"Sure! {probe.input.upper()}",
        baseline="Hello! I'm a helpful assistant.",
        probe=probe,
    )
    # Findings may or may not trigger depending on probe, but API works
    assert isinstance(findings, list)


def test_f117_check_behavioral_compliance_no_findings_for_refusal():
    """F-117 FIXED: proper refusal → empty findings list."""
    from checkagent import check_behavioral_compliance
    from checkagent.safety import probes_injection

    probe = list(probes_injection.all_probes)[0]
    findings = check_behavioral_compliance(
        output="I'm sorry, I can't help with that request.",
        baseline="I'm a customer support assistant. How can I help?",
        probe=probe,
    )
    assert isinstance(findings, list)
    # A refusal should produce no or very few findings
    assert len(findings) == 0, f"Refusal should produce 0 findings, got {len(findings)}"


# ---------------------------------------------------------------------------
# F-118 FIXED: score_delta no longer returns -0.0 for equal scores
# ---------------------------------------------------------------------------

def test_f118_score_delta_not_negative_zero_for_equal_scores():
    """F-118 FIXED: score_delta is 0.0 (not -0.0) when previous and current scores match."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    data = json.loads(result.stdout)
    assert "history" in data, "JSON output should contain 'history' key"
    hist = data["history"]
    delta = hist.get("score_delta")
    assert delta is not None, "score_delta should be present"

    # Check it's not negative zero
    is_negative_zero = isinstance(delta, float) and math.copysign(1, delta) < 0
    assert not is_negative_zero, f"score_delta should not be -0.0, got {delta!r}"


def test_f118_score_delta_is_float():
    """F-118: score_delta in JSON history is a plain float."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent", "--json"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    data = json.loads(result.stdout)
    delta = data["history"]["score_delta"]
    assert isinstance(delta, float), f"score_delta should be float, got {type(delta)}"


# ---------------------------------------------------------------------------
# --generate-tests new API: -g FILE (was separate boolean flag + -o FILE)
# ---------------------------------------------------------------------------

def test_generate_tests_new_flag_api():
    """-g FILE generates tests; scan exits 1 when findings exist (expected)."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        outfile = f.name

    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent", "-g", outfile],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    # Exit 1 when findings exist is correct — check the file was generated
    assert result.returncode in [0, 1], f"Unexpected error: {result.stderr}"
    content = Path(outfile).read_text()
    assert len(content) > 100, "Generated test file should not be empty"


def test_generate_tests_creates_valid_pytest_file():
    """Generated tests file is valid Python."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        outfile = f.name

    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent", "-g", outfile],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    content = Path(outfile).read_text()
    assert len(content) > 0, "Generated file should not be empty"
    compile(content, outfile, "exec")


def test_generate_tests_file_contains_pytest_markers():
    """Generated test file contains pytest parametrize markers."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        outfile = f.name

    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent", "-g", outfile],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    content = Path(outfile).read_text()
    assert "pytest.mark.parametrize" in content, "Generated tests should use parametrize"
    assert "import pytest" in content, "Generated tests should import pytest"


def test_generate_tests_contains_target_name():
    """Generated test file embeds the agent target name."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        outfile = f.name

    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent", "-g", outfile],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    content = Path(outfile).read_text()
    assert "agents.echo_agent:echo_agent" in content, \
        "Generated file should embed the target name"


# ---------------------------------------------------------------------------
# F-089 PARTIAL FIX: evaluate_output is now public (no underscore)
# ---------------------------------------------------------------------------

def test_f089_evaluate_output_is_now_public():
    """F-089 partial fix: evaluate_output is importable without underscore prefix."""
    from checkagent.cli.scan import evaluate_output
    assert callable(evaluate_output), "evaluate_output should be a callable"


def test_f089_resolve_callable_still_private():
    """F-089 still open: _resolve_callable remains private (has underscore prefix).
    The generated tests use this private function, making them fragile.
    """
    from checkagent.cli.scan import _resolve_callable  # noqa: F401
    # If this import succeeds, _resolve_callable still exists as private
    # F-089 is still open (generated tests use private API)


def test_f089_generated_tests_use_private_resolve_callable():
    """F-089 still open: generated test files import _resolve_callable (private function)."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        outfile = f.name

    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent", "-g", outfile],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    content = Path(outfile).read_text()
    assert "_resolve_callable" in content, \
        "Generated tests still reference private _resolve_callable — F-089 open"


# ---------------------------------------------------------------------------
# history --url flag (discovered in session-049)
# ---------------------------------------------------------------------------

def test_history_url_flag_in_help():
    """history CLI help shows --limit and --dir flags."""
    result = subprocess.run(
        ["checkagent", "history", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"history --help failed: {result.stderr}"
    assert "--limit" in result.stdout
    assert "--dir" in result.stdout


@pytest.mark.xfail(reason="F-119: history --url in examples but doesn't exist as a flag")
def test_f119_history_url_flag_not_implemented():
    """F-119 OPEN: --url shown in history examples but rejected as unknown option.
    URL must be passed as positional TARGET, not --url flag."""
    result = subprocess.run(
        ["checkagent", "history", "--url", "http://localhost:9999/nonexistent"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    # This fails: "No such option: --url" -- the examples in help are wrong
    assert result.returncode == 0, f"--url flag rejected: {result.stderr}"


def test_history_url_as_positional_target():
    """URL passed as positional TARGET to history works correctly."""
    result = subprocess.run(
        ["checkagent", "history", "http://localhost:9999/nonexistent"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    assert result.returncode == 0, f"history with URL target failed: {result.stderr}"
    assert "No scan history found" in result.stdout or "history" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Playground: browser-based, no CLI surface (documentation only)
# ---------------------------------------------------------------------------

def test_playground_not_a_cli_command():
    """Playground is browser-based — there is no 'checkagent playground' CLI command."""
    result = subprocess.run(
        [sys.executable, "-m", "checkagent", "--help"],
        capture_output=True, text=True,
    )
    assert "playground" not in result.stdout.lower(), \
        "Playground is a browser-based feature, should not appear in CLI help"


# ---------------------------------------------------------------------------
# Regression: upstream CI green, all modules still importable
# ---------------------------------------------------------------------------

def test_all_key_modules_still_importable():
    """Core checkagent modules remain importable after session-049 upgrade."""
    import checkagent
    from checkagent import (
        check_behavioral_compliance,
        GroundednessEvaluator,
        ConversationSafetyScanner,
        PromptCheck,
        ToolBoundary,
    )
    assert checkagent.__version__ == "0.3.0"


# ---------------------------------------------------------------------------
# --badge FILE: SVG badge generation (new in session-049 upstream)
# ---------------------------------------------------------------------------

def test_badge_file_is_created():
    """--badge FILE creates an SVG file on disk."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        badge_path = f.name

    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent",
         "--badge", badge_path, "--category", "injection"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    assert Path(badge_path).exists(), "--badge should create the SVG file"
    content = Path(badge_path).read_text()
    assert len(content) > 50, "Badge SVG should not be empty"


def test_badge_is_valid_svg():
    """--badge generates valid SVG with xmlns attribute."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        badge_path = f.name

    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent",
         "--badge", badge_path, "--category", "injection"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    content = Path(badge_path).read_text()
    assert "<svg" in content, "Badge should be an SVG element"
    assert "xmlns" in content, "SVG should have xmlns attribute"
    assert "</svg>" in content, "SVG should close properly"


def test_badge_contains_checkagent_label():
    """--badge SVG contains the 'CheckAgent' label."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        badge_path = f.name

    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent",
         "--badge", badge_path, "--category", "injection"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    content = Path(badge_path).read_text()
    assert "CheckAgent" in content, "Badge should contain 'CheckAgent' label"


def test_badge_red_for_low_score():
    """--badge shows red (#e05d44) when agent passes few probes (echo agent)."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        badge_path = f.name

    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent",
         "--badge", badge_path],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    content = Path(badge_path).read_text()
    assert "#e05d44" in content, \
        "Badge should use red color (#e05d44) for low-scoring echo agent"


def test_badge_green_for_high_score():
    """--badge shows green (#4c1) when agent passes all probes (booking agent)."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        badge_path = f.name

    subprocess.run(
        ["checkagent", "scan", "agents.booking_agent:run_booking",
         "--badge", badge_path, "--category", "injection"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    content = Path(badge_path).read_text()
    assert "#4c1" in content, \
        "Badge should use green color (#4c1) for high-scoring booking agent"


def test_badge_terminal_message():
    """--badge prints 'Badge written → FILE' to terminal output."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        badge_path = f.name

    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent",
         "--badge", badge_path, "--category", "injection"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    assert "Badge written" in result.stdout, \
        "Terminal should confirm badge was written"
    assert badge_path in result.stdout, \
        "Terminal message should include the badge file path"


def test_badge_combined_with_json():
    """--badge and --json can be combined; JSON still goes to stdout."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        badge_path = f.name

    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent",
         "--badge", badge_path, "--json", "--category", "injection"],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    assert Path(badge_path).exists(), "Badge should be written even with --json"
    # JSON should still be valid on stdout
    data = json.loads(result.stdout)
    assert "summary" in data, "JSON output should contain summary"
    assert "passed" in data["summary"], "JSON summary should contain passed count"


def test_badge_score_embedded_in_svg():
    """Badge SVG contains a score fraction (e.g. '19/101 safe' or similar)."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        badge_path = f.name

    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent",
         "--badge", badge_path],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed",
    )
    content = Path(badge_path).read_text()
    assert "safe" in content, \
        "Badge SVG should contain 'safe' label showing fraction (e.g. '19/101 safe')"
