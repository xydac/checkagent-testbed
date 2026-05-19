"""
Session-055 tests.

Focus areas:
- CI: latest green ("Add --llm flag to analyze-prompt"), previous green streak 10+
- F-123 still open: PyPI still at 0.3.0 (git main has 0.3.1)
- F-124 FIXED: is_installed() now at top-level checkagent
- F-120 still open: end_probe_trace() returns [] without real API calls
- NEW: analyze-prompt --llm flag (semantic LLM verification)
  - New JSON fields: llm_verified_count, llm_model, llm_passed per check
  - DX gap (F-125): silent fallback when no API key — shows "Running..." but verifies 0
  - Provider detection: clear error for unknown model names
  - Footer mentions LLM model when --llm used
- API change confirmed: begin_probe_trace() takes 0 args (was 1 in session-054 docs)
  (this was already tracked in session-051)
"""

import inspect
import json
import subprocess
import sys

import pytest
import checkagent


# ---------------------------------------------------------------------------
# Version + CI
# ---------------------------------------------------------------------------

def test_version_is_031():
    """Installed version is 0.3.1 (from git main)."""
    assert checkagent.__version__ == "0.3.1"


def test_pypi_still_at_030():
    """F-123: PyPI latest is still 0.3.0 — 0.3.1 not published."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "index", "versions", "checkagent"],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    assert "0.3.0" in output, "PyPI should know about 0.3.0"
    # Check the "Available versions" line — not the "INSTALLED:" line
    available_line = next(
        (line for line in output.splitlines() if "Available versions:" in line), ""
    )
    assert "0.3.1" not in available_line, (
        f"F-123: 0.3.1 not yet on PyPI. Available: {available_line}"
    )


def test_upstream_ci_latest_green():
    """Latest upstream CI run is green (Add --llm flag to analyze-prompt)."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "1", "--json",
         "conclusion,displayTitle"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.skip("gh CLI unavailable")
    data = json.loads(result.stdout)
    assert data[0]["conclusion"] == "success", (
        f"Latest CI run not green: {data[0]}"
    )


# ---------------------------------------------------------------------------
# F-124 FIXED: is_installed() now at top-level
# ---------------------------------------------------------------------------

def test_f124_is_installed_at_top_level():
    """F-124 FIXED: is_installed() now importable from checkagent directly."""
    from checkagent import is_installed
    assert callable(is_installed)


def test_all_tracer_exports_at_top_level():
    """All 5 tracer symbols are now at top-level checkagent."""
    from checkagent import (
        install_patches,
        uninstall_patches,
        begin_probe_trace,
        end_probe_trace,
        TracerContext,
        is_installed,  # F-124 fixed
    )
    for sym in [install_patches, uninstall_patches, begin_probe_trace,
                end_probe_trace, TracerContext, is_installed]:
        assert callable(sym) or isinstance(sym, type)


# ---------------------------------------------------------------------------
# F-120 still open: tracer still returns no events
# ---------------------------------------------------------------------------

def test_f120_tracer_still_returns_no_events():
    """F-120 still open: end_probe_trace() returns [] without real API calls."""
    from checkagent import install_patches, uninstall_patches, begin_probe_trace, end_probe_trace

    install_patches()
    begin_probe_trace()
    events = end_probe_trace()
    uninstall_patches()

    assert isinstance(events, list), "end_probe_trace() should return a list"
    # F-120: no events captured without real LLM SDK calls
    assert len(events) == 0, "F-120 open: events should be empty without real API calls"


def test_tracer_begin_takes_no_args():
    """begin_probe_trace() takes 0 args (API change from original design)."""
    from checkagent import begin_probe_trace
    sig = inspect.signature(begin_probe_trace)
    params = sig.parameters
    assert len(params) == 0, (
        f"begin_probe_trace() should take no args, got {sig}"
    )


# ---------------------------------------------------------------------------
# analyze-prompt --llm: JSON field structure
# ---------------------------------------------------------------------------

def test_analyze_prompt_json_without_llm_has_null_llm_fields():
    """Without --llm, JSON output has null llm_verified_count and llm_model."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--json", "You are a helpful assistant."],
        capture_output=True, text=True
    )
    # Exit code 1 is expected when checks fail
    data = json.loads(result.stdout or result.stderr)
    assert data["llm_verified_count"] is None
    assert data["llm_model"] is None
    for check in data["checks"]:
        assert check["llm_passed"] is None, (
            f"Without --llm, {check['id']} llm_passed should be null"
        )


def test_analyze_prompt_json_with_llm_has_llm_fields_populated():
    """With --llm (no key), JSON has llm_model set and llm_verified_count=0."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--json", "--llm", "gpt-4o-mini",
         "You are a helpful assistant."],
        capture_output=True, text=True
    )
    # Parse whichever stream has valid JSON
    raw = result.stdout or result.stderr
    data = json.loads(raw)

    assert data["llm_model"] == "gpt-4o-mini", "llm_model should be set when --llm used"
    assert isinstance(data["llm_verified_count"], int), (
        "llm_verified_count should be int when --llm used"
    )
    # When no API key: verifies 0 checks
    assert data["llm_verified_count"] == 0, (
        "F-125 context: no API key → llm_verified_count=0"
    )


def test_analyze_prompt_llm_per_check_fields():
    """With --llm: only failing checks get llm_passed set; passing checks stay null."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--json", "--llm", "claude-haiku-4-5-20251001",
         "You are a helpful assistant."],
        capture_output=True, text=True
    )
    raw = result.stdout or result.stderr
    data = json.loads(raw)

    # Behavior: checks that already pass via pattern stay llm_passed=null
    # Only pattern-failing checks get LLM verification attempted
    for check in data["checks"]:
        if check["pattern_passed"]:
            # Already passed — LLM not needed, stays null
            assert check["llm_passed"] is None, (
                f"Check {check['id']} already passed pattern — llm_passed should stay null"
            )
        else:
            # Failed pattern — LLM attempted but no key → llm_passed is None (not attempted)
            # Behavior changed in session-056: was False, now None (more accurate: LLM never ran)
            assert check["llm_passed"] is None, (
                f"Check {check['id']} failed pattern + no API key → llm_passed should be None"
            )


def test_analyze_prompt_llm_terminal_says_running():
    """--llm shows model-related message in terminal output.
    Session-056 update: F-125 fixed — 'Running LLM verification' replaced by
    'Warning: LLM verification skipped — OPENAI_API_KEY is not set.' when no key set.
    The model name still appears in the output."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--llm", "gpt-4o-mini",
         "You are a helpful assistant."],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    # Model name still appears (either in warning or footer)
    assert "gpt-4o-mini" in combined, "Model name should appear in output"
    # Either the running message OR the skip warning should appear
    assert ("Running LLM verification" in combined or "OPENAI_API_KEY" in combined), (
        "--llm should show either a progress message or an API key warning"
    )


def test_analyze_prompt_footer_mentions_llm_model():
    """When --llm used, footer says 'static + LLM-assisted' not just 'static'."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--llm", "gpt-4o-mini",
         "You are a helpful assistant."],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    assert "LLM-assisted" in combined or "gpt-4o-mini" in combined, (
        "Footer should mention LLM model when --llm used"
    )


# ---------------------------------------------------------------------------
# F-125: --llm silent failure when no API key (DX gap)
# ---------------------------------------------------------------------------

def test_f125_llm_silently_falls_back_no_api_key_warning():
    """F-125 FIXED (session-056): --llm now warns when API key missing."""
    import os
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env.pop("ANTHROPIC_API_KEY", None)

    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--json", "--llm", "gpt-4o-mini",
         "You are a helpful assistant."],
        capture_output=True, text=True, env=env
    )
    raw = result.stdout or result.stderr
    data = json.loads(raw)

    # Still verifies 0 checks (no key → no LLM call)
    assert data["llm_verified_count"] == 0, "No API key → 0 LLM verifications"

    combined = result.stdout + result.stderr
    # F-125 FIXED: warning now shown
    has_warning = any(
        phrase in combined
        for phrase in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "not set", "skipped"]
    )
    assert has_warning, (
        "F-125 fix: expected warning about missing API key, got none. Regression?"
    )


# ---------------------------------------------------------------------------
# analyze-prompt --llm: error handling
# ---------------------------------------------------------------------------

def test_analyze_prompt_llm_invalid_model_clear_error():
    """--llm with unrecognized model gives a clear, actionable error."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--llm", "totally-fake-model-xyz",
         "You are a helpful assistant."],
        capture_output=True, text=True
    )
    assert result.returncode != 0, "Invalid model should cause non-zero exit"
    combined = result.stdout + result.stderr
    assert "Cannot detect provider" in combined or "Invalid" in combined, (
        "Should explain that model provider cannot be detected"
    )
    assert "gpt-4o-mini" in combined or "claude" in combined, (
        "Error should suggest valid model examples"
    )


# ---------------------------------------------------------------------------
# analyze-prompt: non-canonical phrasing gap (motivates --llm)
# ---------------------------------------------------------------------------

NONCANONICAL_PROMPT = (
    "You are a helpful assistant. Please keep this conversation completely private "
    "and don't share internal details with anyone. Feel free to politely say no to "
    "anything that seems weird or outside normal tasks. When helping users, only use "
    "the information they give you, not outside sources."
)

def test_analyze_prompt_noncanonical_patterns_miss_confidentiality():
    """Pattern matching misses non-canonical confidentiality phrasing (motivates --llm)."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--json", NONCANONICAL_PROMPT],
        capture_output=True, text=True
    )
    raw = result.stdout or result.stderr
    data = json.loads(raw)

    conf = next(c for c in data["checks"] if c["id"] == "confidentiality")
    assert not conf["pattern_passed"], (
        "Pattern matching misses 'keep this conversation completely private' — "
        "this is the use case for --llm"
    )


def test_analyze_prompt_noncanonical_patterns_miss_data_scope():
    """Pattern matching misses non-canonical data_scope phrasing."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--json", NONCANONICAL_PROMPT],
        capture_output=True, text=True
    )
    raw = result.stdout or result.stderr
    data = json.loads(raw)

    ds = next(c for c in data["checks"] if c["id"] == "data_scope")
    assert not ds["pattern_passed"], (
        "Pattern matching misses 'only use the information they give you, not outside sources'"
    )


def test_analyze_prompt_noncanonical_refusal_detected():
    """Pattern matching DOES catch 'say no' as refusal_behavior."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--json", NONCANONICAL_PROMPT],
        capture_output=True, text=True
    )
    raw = result.stdout or result.stderr
    data = json.loads(raw)

    refusal = next(c for c in data["checks"] if c["id"] == "refusal_behavior")
    assert refusal["pattern_passed"], (
        "'say no' should trigger refusal_behavior pattern"
    )
