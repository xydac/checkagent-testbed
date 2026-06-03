"""
Session-063 tests: v0.4.0 upgrade — F-089 fixed (resolve_callable public),
F-120 fixed (TracerContext captures MockLLM events), error_warning JSON field,
verbose hint fix, F-123 fixed (v0.3.1+v0.4.0 published to PyPI).
"""
import json
import subprocess
import asyncio
import pytest
import sys


# ---------------------------------------------------------------------------
# Upstream CI — green as of 2026-06-02
# ---------------------------------------------------------------------------

def test_upstream_ci_latest_green():
    """Latest upstream CI runs are green (v0.4.0 release)."""
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
# v0.4.0 version check
# ---------------------------------------------------------------------------

def test_checkagent_version_040():
    """v0.4.0 is installed and version string is correct."""
    import checkagent
    assert checkagent.__version__ == "0.4.0"


def test_pypi_version_now_040():
    """F-123 FIXED: PyPI now has v0.4.0 (was stuck at 0.3.0 for multiple sessions)."""
    result = subprocess.run(
        ["pip", "index", "versions", "checkagent"],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    assert "0.4.0" in combined, f"v0.4.0 not found in pip index: {combined}"


# ---------------------------------------------------------------------------
# F-120 FIXED: TracerContext now captures MockLLM events (v0.4.0)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_f120_tracer_captures_mock_llm_events():
    """F-120 FIXED: TracerContext.begin/end now captures MockLLM events."""
    from checkagent import TracerContext, MockLLM, install_patches, uninstall_patches

    install_patches()
    tc = TracerContext()
    llm = MockLLM(default_response="Hello from mock!")

    tc.begin()
    resp = await llm.complete("test prompt")
    events = tc.end()
    uninstall_patches()

    assert resp == "Hello from mock!"
    assert len(events) == 1, f"Expected 1 event, got {len(events)}: {events}"
    event = events[0]
    assert event["type"] == "llm_call"
    assert event["provider"] == "mock"
    assert "prompt_preview" in event
    assert "response_preview" in event
    assert "latency_ms" in event


@pytest.mark.asyncio
async def test_f120_tracer_llm_calls_property():
    """F-120 FIXED: tc.llm_calls property returns list of LLM events."""
    from checkagent import TracerContext, MockLLM, install_patches, uninstall_patches

    install_patches()
    tc = TracerContext()
    llm = MockLLM(default_response="response A")

    tc.begin()
    await llm.complete("first prompt")
    await llm.complete("second prompt")
    tc.end()
    uninstall_patches()

    assert len(tc.llm_calls) == 2, f"Expected 2 llm_calls, got {len(tc.llm_calls)}"
    assert tc.llm_calls[0]["type"] == "llm_call"


@pytest.mark.asyncio
async def test_f120_tracer_tool_calls_empty_for_mock_tool():
    """MockTool now emits tracer events as of post-v0.4.0 commit; updated in session-064."""
    from checkagent import TracerContext, MockTool, install_patches, uninstall_patches

    install_patches()
    tc = TracerContext()
    tool = MockTool()
    tool.register("search", response={"results": []})

    tc.begin()
    await tool.call("search", {"q": "test"})
    tc.end()
    uninstall_patches()

    # Updated session-064: MockTool now emits tool_call events (post-v0.4.0 commit)
    assert len(tc.tool_calls) == 1, \
        f"Expected 1 tool_call event, got {len(tc.tool_calls)}: {tc.tool_calls}"
    assert tc.tool_calls[0]["tool_name"] == "search"


@pytest.mark.asyncio
async def test_f120_tracer_context_class_importable():
    """TracerContext is importable from top-level checkagent."""
    from checkagent import TracerContext
    tc = TracerContext()
    assert hasattr(tc, "begin")
    assert hasattr(tc, "end")
    assert hasattr(tc, "llm_calls")
    assert hasattr(tc, "tool_calls")


# ---------------------------------------------------------------------------
# error_warning JSON field (new in v0.4.0)
# ---------------------------------------------------------------------------

def test_error_warning_field_present_when_all_probes_fail():
    """v0.4.0: error_warning JSON field present when 100% of probes error."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.error_agent:my_agent",
         "--category", "injection", "--json"],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    assert "error_warning" in data, \
        f"error_warning key missing from JSON. Keys: {list(data.keys())}"
    ew = data["error_warning"]
    assert ew["type"] == "partial_scan"
    assert ew["error_count"] == ew["total_count"]
    assert ew["error_rate"] == 1.0
    assert "message" in ew


def test_error_warning_field_present_for_partial_failures():
    """v0.4.0: error_warning present when 40%+ probes fail."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.partial_error_agent:partial_agent",
         "--category", "injection", "--json"],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    assert "error_warning" in data, \
        f"error_warning key missing for partial failure scan. Keys: {list(data.keys())}"
    ew = data["error_warning"]
    assert ew["error_rate"] > 0.4, \
        f"Expected error_rate > 0.4, got {ew['error_rate']}"


def test_no_error_warning_for_clean_agent():
    """v0.4.0: error_warning absent when probes execute cleanly."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent",
         "--category", "injection", "--json"],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    assert "error_warning" not in data, \
        f"Unexpected error_warning for clean agent: {data.get('error_warning')}"


# ---------------------------------------------------------------------------
# verbose hint fix (new in v0.4.0)
# ---------------------------------------------------------------------------

def test_verbose_hint_says_shown_above_when_verbose_flag_used():
    """v0.4.0: When --verbose is active, hint says 'shown above' not 'Use --verbose'."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.partial_error_agent:partial_agent",
         "--category", "injection", "--verbose"],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed"
    )
    combined = result.stdout + result.stderr
    assert "shown above" in combined, \
        "Expected 'shown above' in verbose output"
    assert "Re-run with --verbose" not in combined, \
        "Should not tell user to Use --verbose when they already are"


def test_verbose_hint_says_rerun_without_verbose_flag():
    """v0.4.0: Without --verbose, hint says 'Re-run with --verbose'."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.partial_error_agent:partial_agent",
         "--category", "injection"],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed"
    )
    combined = result.stdout + result.stderr
    assert "Re-run with --verbose" in combined, \
        "Expected 'Re-run with --verbose' hint in non-verbose output"


# ---------------------------------------------------------------------------
# F-089 FIXED: resolve_callable now public in generated tests
# ---------------------------------------------------------------------------

def test_f089_generated_tests_use_public_api_for_resolve():
    """F-089 FIXED in v0.4.0: generated tests use public resolve_callable."""
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        outfile = f.name

    subprocess.run(
        ["checkagent", "scan", "agents.echo_agent:echo_agent", "-g", outfile],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed",
    )
    content = Path(outfile).read_text()
    assert "resolve_callable" in content, \
        "Generated tests should import resolve_callable (public)"
    assert "_resolve_callable" not in content, \
        "Generated tests should not use private _resolve_callable"


def test_f089_resolve_callable_importable_from_scan():
    """F-089 FIXED: resolve_callable is a public export from checkagent.cli.scan."""
    from checkagent.cli.scan import resolve_callable
    assert callable(resolve_callable)
