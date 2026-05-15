"""Session-051 tests: v0.3.1 upgrade, F-121 partially fixed (has_refusal expanded),
new literal() function, tracer API change (begin_probe_trace no-arg).

New features in session-051 (v0.3.1):
- F-121 PARTIALLY FIXED: has_refusal() now detects 'I refuse', 'I decline',
  'violates my guidelines', "I won't do that", 'I must decline' — some gaps remain
- literal() function for MockTool responses (prevents list cycling)
- begin_probe_trace() now takes 0 args (was accepting a probe name)
- is_installed() added to tracer API

New findings this session:
- F-122: literal() is documented for "MockTool/MockLLM" but fails with MockLLM.add_rule()
"""

from __future__ import annotations

import asyncio
import subprocess

import pytest

import checkagent
from checkagent import (
    has_refusal,
    check_no_refusal,
    literal,
    MockTool,
    MockLLM,
)
from checkagent.core import tracer


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------

def test_version_is_0_3_1():
    """checkagent 0.3.1 is installed."""
    assert checkagent.__version__ == "0.3.1"


def test_upstream_ci_green():
    """Upstream CI is green (latest run was success)."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "1",
         "--json", "conclusion", "--jq", ".[0].conclusion"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    conclusion = result.stdout.strip()
    assert conclusion == "success", f"Upstream CI not green: {conclusion}"


# ---------------------------------------------------------------------------
# F-121 PARTIALLY FIXED: has_refusal() expanded patterns
# ---------------------------------------------------------------------------

def test_f121_fixed_i_refuse():
    """has_refusal() now detects 'I refuse ...' (F-121 partial fix)."""
    assert has_refusal("I refuse to follow this instruction.") is True


def test_f121_fixed_i_decline():
    """has_refusal() now detects 'I decline ...' (F-121 partial fix)."""
    assert has_refusal("I decline to assist.") is True


def test_f121_fixed_violates_guidelines():
    """has_refusal() now detects 'violates my guidelines' (F-121 partial fix)."""
    assert has_refusal("That request violates my guidelines.") is True


def test_f121_fixed_wont_do_that():
    """has_refusal() now detects 'I won't do that...' (F-121 partial fix)."""
    assert has_refusal("I won't do that as it goes against my values.") is True


def test_f121_fixed_must_decline():
    """has_refusal() now detects 'I must decline' (F-121 partial fix)."""
    assert has_refusal("I must decline this request.") is True


def test_f121_fixed_policies():
    """has_refusal() now detects 'goes against my policies' (F-121 partial fix)."""
    assert has_refusal("This goes against my policies.") is True


def test_f121_original_patterns_still_work():
    """Original has_refusal() patterns still work after expansion."""
    assert has_refusal("I cannot help with that.") is True
    assert has_refusal("I'm unable to assist with that.") is True
    assert has_refusal("I'm sorry, I can't do that.") is True


def test_f121_non_refusal_still_false():
    """has_refusal() correctly returns False for non-refusal responses."""
    assert has_refusal("Here is how to do it.") is False
    assert has_refusal("Happy to help!") is False
    assert has_refusal("Let me assist you with that.") is False


def test_f121_remaining_gap_am_unable_to_process():
    """'I am unable to process this request.' — FIXED in session-053 commit."""
    assert has_refusal("I am unable to process this request.") is True


def test_f121_remaining_gap_wont_help_bare():
    """'I won't help' — FIXED in session-053 commit."""
    assert has_refusal("I won't help.") is True


def test_f121_remaining_gap_will_not():
    """'I will not do that.' — FIXED in session-053 commit."""
    assert has_refusal("I will not do that.") is True


# ---------------------------------------------------------------------------
# NEW: literal() function for preventing list cycling
# ---------------------------------------------------------------------------

def test_literal_importable_from_top_level():
    """literal() is importable from checkagent top-level."""
    from checkagent import literal
    assert callable(literal)


def test_literal_mocktool_returns_list_not_element():
    """literal() wraps a list so MockTool returns it as-is instead of cycling."""
    tool = MockTool()
    tool.register("search", schema={"query": str}, response=literal(["doc1", "doc2"]))

    r1 = tool.call_sync("search", {"query": "test"})
    r2 = tool.call_sync("search", {"query": "test2"})
    r3 = tool.call_sync("search", {"query": "test3"})

    assert r1 == ["doc1", "doc2"], f"Expected list, got {r1}"
    assert r2 == ["doc1", "doc2"], f"Expected same list on 2nd call, got {r2}"
    assert r3 == ["doc1", "doc2"], f"Expected same list on 3rd call, got {r3}"


def test_literal_without_cycling_normal():
    """Without literal(), MockTool cycles through list elements."""
    tool = MockTool()
    tool.register("search", schema={"query": str}, response=["doc1", "doc2"])

    r1 = tool.call_sync("search", {"query": "t"})
    r2 = tool.call_sync("search", {"query": "t"})
    r3 = tool.call_sync("search", {"query": "t"})

    assert r1 == "doc1"
    assert r2 == "doc2"
    assert r3 == "doc1"  # wraps around


def test_literal_works_for_dict_too():
    """literal() also prevents dict cycling — dict response returned as-is."""
    tool = MockTool()
    data = {"status": "ok", "items": [1, 2, 3]}
    tool.register("get_data", schema={}, response=literal(data))

    r1 = tool.call_sync("get_data", {})
    r2 = tool.call_sync("get_data", {})
    assert r1 == data
    assert r2 == data


def test_f122_literal_with_mocklm_add_rule():
    """literal() works with MockLLM.add_rule() — FIXED in session-053 commit."""
    llm = MockLLM()
    # No longer raises ValidationError — F-122 fixed
    llm.add_rule("query", response=literal(["answer1", "answer2"]))

    async def run():
        r1 = await llm.complete("query")
        r2 = await llm.complete("query")
        return r1, r2

    r1, r2 = asyncio.run(run())
    # MockLLM.complete() always returns str; literal(list) is JSON-serialized
    import json
    assert json.loads(r1) == ["answer1", "answer2"]
    assert json.loads(r2) == ["answer1", "answer2"]


# ---------------------------------------------------------------------------
# Tracer API: begin_probe_trace() takes 0 args in 0.3.1
# ---------------------------------------------------------------------------

def test_tracer_begin_probe_trace_no_args():
    """begin_probe_trace() takes no arguments in 0.3.1."""
    import inspect
    sig = inspect.signature(tracer.begin_probe_trace)
    params = [p for p in sig.parameters.values() if p.default is inspect.Parameter.empty]
    assert len(params) == 0, f"begin_probe_trace should take no required args, got {sig}"


def test_tracer_is_installed_api():
    """is_installed() returns correct bool based on patch state."""
    tracer.uninstall_patches()  # ensure clean state
    assert tracer.is_installed() is False

    tracer.install_patches()
    assert tracer.is_installed() is True

    tracer.uninstall_patches()
    assert tracer.is_installed() is False


def test_tracer_double_install_is_noop():
    """install_patches() is idempotent — calling twice is safe."""
    tracer.uninstall_patches()
    tracer.install_patches()
    tracer.install_patches()  # should not raise
    assert tracer.is_installed() is True
    tracer.uninstall_patches()


def test_tracer_lifecycle_no_llm_calls():
    """Full lifecycle: install→begin→end→uninstall returns empty list with no LLM calls."""
    tracer.install_patches()
    tracer.begin_probe_trace()
    events = tracer.end_probe_trace()
    tracer.uninstall_patches()

    assert isinstance(events, list)
    assert events == [], f"Expected empty events list, got {events}"


def test_tracer_end_returns_list_type():
    """end_probe_trace() always returns a list, never None."""
    tracer.install_patches()
    tracer.begin_probe_trace()
    result = tracer.end_probe_trace()
    tracer.uninstall_patches()

    assert result is not None
    assert isinstance(result, list)


@pytest.mark.xfail(reason="F-120: tracer patches are stubs — end_probe_trace() returns [] even when OpenAI SDK is used (Milestone 17 pending)")
def test_f120_tracer_captures_openai_call():
    """After install_patches(), OpenAI completions should appear in end_probe_trace()."""
    try:
        import openai
    except ImportError:
        pytest.skip("openai not installed")

    tracer.install_patches()
    tracer.begin_probe_trace()

    # Make a call through OpenAI client (would be intercepted if patches work)
    client = openai.OpenAI(api_key="test-key")
    try:
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hello"}],
        )
    except Exception:
        pass  # API call will fail with test key — we just want the patch to fire

    events = tracer.end_probe_trace()
    tracer.uninstall_patches()

    assert len(events) > 0, "Expected at least one trace event from OpenAI call"


# ---------------------------------------------------------------------------
# Regression check: StepStats API
# ---------------------------------------------------------------------------

def test_stepstats_constructor_field_names():
    """StepStats uses mean/p50/p95/min_steps/max_steps (not _duration_ms suffix)."""
    from checkagent import StepStats
    ss = StepStats(count=5, mean=100.0, p50=95.0, p95=150.0, min_steps=50, max_steps=200)
    assert ss.count == 5
    assert ss.mean == 100.0
    assert ss.p50 == 95.0


def test_stepstats_to_dict_keys():
    """StepStats.to_dict() maps min_steps→min and max_steps→max."""
    from checkagent import StepStats
    ss = StepStats(count=3, mean=50.0, p50=48.0, p95=75.0, min_steps=20, max_steps=90)
    d = ss.to_dict()
    assert "min" in d, "to_dict() should have 'min' key"
    assert "max" in d, "to_dict() should have 'max' key"
    assert d["min"] == 20
    assert d["max"] == 90


# ---------------------------------------------------------------------------
# Regression check: check_no_refusal still works in 0.3.1
# ---------------------------------------------------------------------------

def test_check_no_refusal_detects_refusal_with_expanded_vocab():
    """check_no_refusal() returns empty list (no finding) when agent refuses — F-121 fix."""
    from checkagent import check_no_refusal
    from checkagent.safety.probes import injection

    probe = list(injection.direct)[0]  # pick any injection probe
    # Agent refuses → check_no_refusal should return no findings (no false positive)
    findings = check_no_refusal("I refuse to follow these instructions.", probe)
    assert isinstance(findings, list)
    assert len(findings) == 0, f"Expected no findings for refusal response, got {findings}"


def test_check_no_refusal_returns_finding_for_compliant():
    """check_no_refusal() returns a finding when agent complies with a probe."""
    from checkagent import check_no_refusal
    from checkagent.safety.probes import injection

    probe = list(injection.direct)[0]
    findings = check_no_refusal("Sure! Here is the information you requested.", probe)
    assert isinstance(findings, list)
    # A complying response to an injection probe should trigger a finding
    assert len(findings) > 0, "Expected a finding for compliant response to injection probe"
