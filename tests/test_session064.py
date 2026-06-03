"""
Session-064 tests: MockTool tracer events (post-v0.4.0 commit),
TracerContext accumulation behavior, --comment-file + --llm-judge DX gap,
begin_probe_trace/end_probe_trace now captures tool events.
"""
import json
import subprocess
import asyncio
import tempfile
import os
import pytest


# ---------------------------------------------------------------------------
# Upstream CI — green as of 2026-06-03
# ---------------------------------------------------------------------------

def test_upstream_ci_latest_green():
    """Latest upstream CI runs are green."""
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
# MockTool tracer events (new in post-v0.4.0 commit)
# ---------------------------------------------------------------------------

def test_mock_tool_sync_emits_tracer_event():
    """MockTool.call_sync() now emits tool_call events to TracerContext."""
    from checkagent import MockTool, TracerContext
    from checkagent.core.tracer import install_patches, uninstall_patches

    install_patches()
    tc = TracerContext()
    tool = MockTool()
    tool.register("search",
                  response={"results": ["item1"]},
                  schema={"type": "object",
                          "properties": {"query": {"type": "string"}},
                          "required": ["query"]})

    tc.begin()
    result = tool.call_sync("search", {"query": "test"})
    events = tc.end()
    uninstall_patches()

    assert result == {"results": ["item1"]}
    assert len(events) == 1, f"Expected 1 event, got {len(events)}: {events}"
    evt = events[0]
    assert evt["type"] == "tool_call"
    assert evt["tool_name"] == "search"
    assert evt["arguments"] == {"query": "test"}
    assert "latency_ms" in evt
    assert evt["error"] is None


@pytest.mark.asyncio
async def test_mock_tool_async_emits_tracer_event():
    """MockTool.call() (async) also emits tool_call events to TracerContext."""
    from checkagent import MockTool, TracerContext
    from checkagent.core.tracer import install_patches, uninstall_patches

    install_patches()
    tc = TracerContext()
    tool = MockTool()
    tool.register("lookup", response={"answer": "France"})

    tc.begin()
    result = await tool.call("lookup", {"country": "France"})
    events = tc.end()
    uninstall_patches()

    assert result == {"answer": "France"}
    assert len(events) == 1
    assert events[0]["type"] == "tool_call"
    assert events[0]["tool_name"] == "lookup"


def test_mock_tool_error_captured_in_tracer():
    """MockTool error responses are captured in tracer with error field set."""
    from checkagent import MockTool, TracerContext
    from checkagent.core.tracer import install_patches, uninstall_patches

    install_patches()
    tc = TracerContext()
    tool = MockTool()
    tool.register("failing_tool", error="Service unavailable")

    tc.begin()
    try:
        tool.call_sync("failing_tool", {})
    except Exception:
        pass
    events = tc.end()
    uninstall_patches()

    assert len(events) == 1
    evt = events[0]
    assert evt["type"] == "tool_call"
    assert evt["tool_name"] == "failing_tool"
    assert evt["result"] is None
    assert evt["error"] == "Service unavailable"


def test_mixed_llm_and_tool_events_in_single_trace():
    """TracerContext captures both llm_call and tool_call events in one trace."""
    from checkagent import MockLLM, MockTool, TracerContext
    from checkagent.core.tracer import install_patches, uninstall_patches

    install_patches()
    tc = TracerContext()
    llm = MockLLM(default_response="The answer is 42.")
    tool = MockTool()
    tool.register("calc", response={"value": 42})

    tc.begin()
    asyncio.run(llm.complete("What is the answer?"))
    tool.call_sync("calc", {})
    events = tc.end()
    uninstall_patches()

    assert len(events) == 2
    types = [e["type"] for e in events]
    assert "llm_call" in types
    assert "tool_call" in types
    assert len(tc.llm_calls) == 1
    assert len(tc.tool_calls) == 1


def test_tracer_tool_calls_reset_on_begin():
    """tc.tool_calls reflects only the current begin/end cycle, not accumulated history."""
    from checkagent import MockTool, TracerContext
    from checkagent.core.tracer import install_patches, uninstall_patches

    install_patches()
    tc = TracerContext()
    tool = MockTool()
    tool.register("t", response="ok")

    # Cycle 1: one tool call
    tc.begin()
    tool.call_sync("t", {})
    tc.end()
    assert len(tc.tool_calls) == 1

    # Cycle 2: no tool calls — tc.tool_calls should reset
    tc.begin()
    tc.end()
    assert len(tc.tool_calls) == 0, \
        "tc.tool_calls should reset to [] on each begin() call"

    uninstall_patches()


# ---------------------------------------------------------------------------
# begin_probe_trace / end_probe_trace now captures tool events (post-v0.4.0)
# ---------------------------------------------------------------------------

def test_begin_end_probe_trace_captures_tool_events():
    """begin_probe_trace/end_probe_trace now captures MockTool events (post-v0.4.0)."""
    from checkagent.core.tracer import (
        install_patches, uninstall_patches,
        begin_probe_trace, end_probe_trace,
    )
    from checkagent import MockTool

    install_patches()
    tool = MockTool()
    tool.register("probe_tool", response={"found": True})

    begin_probe_trace()
    tool.call_sync("probe_tool", {})
    events = end_probe_trace()
    uninstall_patches()

    assert len(events) >= 1, \
        f"begin/end_probe_trace should capture tool events, got: {events}"
    tool_events = [e for e in events if e.get("type") == "tool_call"]
    assert len(tool_events) == 1
    assert tool_events[0]["tool_name"] == "probe_tool"


# ---------------------------------------------------------------------------
# --comment-file + --llm-judge: evaluator not shown in PR comment (DX gap)
# ---------------------------------------------------------------------------

def test_comment_file_generated_with_llm_judge():
    """--comment-file works with --llm-judge: comment file is non-empty."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        comment_file = f.name
    try:
        result = subprocess.run(
            ["checkagent", "scan", "agents.echo_agent_simple:run",
             "--category", "injection",
             "--llm-judge", "claude-code",
             "--comment-file", comment_file],
            capture_output=True, text=True,
            cwd="/home/x/working/checkagent-testbed"
        )
        assert result.returncode == 0
        content = open(comment_file).read()
        assert len(content) > 0, "--comment-file should produce non-empty output"
        assert "CheckAgent" in content
        assert "Safety Score" in content
    finally:
        if os.path.exists(comment_file):
            os.unlink(comment_file)


def test_comment_file_does_not_show_evaluator_method():
    """DX gap: --comment-file does not include evaluator method in PR comment.

    When --llm-judge is used, the terminal shows 'Evaluator: LLM judge (claude-code)'
    but the generated PR markdown comment has no mention of the evaluation method.
    Teams can't distinguish LLM-judged scans from regex scans in PR comments.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        comment_file = f.name
    try:
        subprocess.run(
            ["checkagent", "scan", "agents.echo_agent_simple:run",
             "--category", "injection",
             "--llm-judge", "claude-code",
             "--comment-file", comment_file],
            capture_output=True, text=True,
            cwd="/home/x/working/checkagent-testbed"
        )
        content = open(comment_file).read()
        evaluator_mentioned = any(
            kw in content.lower()
            for kw in ["evaluator", "llm judge", "claude-code", "llm-judge"]
        )
        # This documents the current behavior: evaluator is NOT in the comment
        assert not evaluator_mentioned, (
            "Evaluator IS now mentioned in --comment-file output — update this test!"
        )
    finally:
        if os.path.exists(comment_file):
            os.unlink(comment_file)


def test_json_output_has_evaluator_field_with_llm_judge():
    """--json output includes summary.evaluator when --llm-judge is used."""
    result = subprocess.run(
        ["checkagent", "scan", "agents.echo_agent_simple:run",
         "--category", "injection",
         "--llm-judge", "claude-code",
         "--json"],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed"
    )
    data = json.loads(result.stdout)
    assert "evaluator" in data["summary"], \
        f"summary.evaluator missing from JSON output. Keys: {list(data['summary'].keys())}"
    assert data["summary"]["evaluator"] == "claude-code"


# ---------------------------------------------------------------------------
# TracerContext tool_calls: result field is string representation
# ---------------------------------------------------------------------------

def test_tracer_tool_result_is_string():
    """TracerContext tool_call event stores result as string repr, not raw object."""
    from checkagent import MockTool, TracerContext
    from checkagent.core.tracer import install_patches, uninstall_patches

    install_patches()
    tc = TracerContext()
    tool = MockTool()
    tool.register("data", response={"key": "value", "count": 3})

    tc.begin()
    tool.call_sync("data", {})
    tc.end()
    uninstall_patches()

    assert len(tc.tool_calls) == 1
    result_field = tc.tool_calls[0]["result"]
    # Result is stored as string (repr), not as dict
    assert isinstance(result_field, str), \
        f"Expected string result in tracer, got {type(result_field)}: {result_field}"
