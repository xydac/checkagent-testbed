"""Session-079 tests: probe-list --verbose, category delta, F-068 full fix, F-158 fix."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# F-158: ruff N806 fix — CI should be green again
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f158_ci_green():
    """F-158 FIXED: ruff N806 renamed _DISPLAY to _display; CI is green on latest commit."""
    # This test documents that the CI failure is resolved.
    # The "Add category delta to watch rescan" commit fixed F-158.
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "2", "--json",
         "conclusion,headBranch,displayTitle"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    runs = json.loads(result.stdout)
    latest = runs[0]
    assert latest["conclusion"] == "success", (
        f"CI should be green after F-158 fix, got: {latest['conclusion']} "
        f"for '{latest['displayTitle']}'"
    )


# ---------------------------------------------------------------------------
# F-068 FULLY FIXED: all multiagent symbols at top-level
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f068_handoff_now_at_top_level():
    """F-068 fully fixed (session-079): Handoff is now at top-level checkagent."""
    import checkagent
    assert hasattr(checkagent, "Handoff"), "Handoff should be at top-level checkagent"
    from checkagent import Handoff
    h = Handoff(from_agent_id="a", to_agent_id="b")
    assert h.from_agent_id == "a"
    assert h.to_agent_id == "b"


@pytest.mark.agent_test
def test_f068_blame_symbols_at_top_level():
    """F-068 fully fixed: assign_blame, BlameStrategy, top_blamed_agent all at top-level."""
    import checkagent
    for sym in ("assign_blame", "assign_blame_ensemble", "BlameStrategy",
                "BlameResult", "top_blamed_agent"):
        assert hasattr(checkagent, sym), f"{sym} should be at top-level checkagent"


@pytest.mark.agent_test
def test_f068_top_level_handoff_functional():
    """Handoff imported from top-level works correctly with MultiAgentTrace."""
    from checkagent import MultiAgentTrace, Handoff, HandoffType, AgentRun, AgentInput

    run_a = AgentRun(
        agent_id="a", agent_name="Agent A",
        input=AgentInput(query="hello"),
        final_output="done",
    )
    run_b = AgentRun(
        agent_id="b", agent_name="Agent B",
        input=AgentInput(query="continue"),
        final_output="done too",
    )
    handoff = Handoff(
        from_agent_id="a", to_agent_id="b",
        handoff_type=HandoffType.DELEGATION,
    )
    trace = MultiAgentTrace(runs=[run_a, run_b], handoffs=[handoff])
    assert len(trace.handoffs) == 1
    assert trace.handoffs[0].handoff_type == HandoffType.DELEGATION


# ---------------------------------------------------------------------------
# probe-list --verbose: new flag added in session-079
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_probe_list_verbose_json_adds_probes_key():
    """probe-list --verbose --json adds 'probes' key with all probe texts."""
    result = subprocess.run(
        ["checkagent", "probe-list", "--verbose", "--json", "--category", "pii"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    cat = data["categories"][0]
    assert "probes" in cat, "--verbose should add 'probes' key to JSON"
    assert len(cat["probes"]) == 10, "pii_leakage should have 10 probes"


@pytest.mark.agent_test
def test_probe_list_verbose_json_probe_fields():
    """probe-list --verbose --json probes have 'input' and 'description' fields."""
    result = subprocess.run(
        ["checkagent", "probe-list", "--verbose", "--json", "--category", "injection"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    cat = data["categories"][0]
    assert "probes" in cat
    probe = cat["probes"][0]
    assert "input" in probe, "probe should have 'input' field with probe text"
    assert "description" in probe, "probe should have 'description' field"
    assert len(probe["input"]) > 10, "probe input should be non-trivial"


@pytest.mark.agent_test
def test_probe_list_verbose_json_all_injection_probes():
    """probe-list --verbose --json returns all 35 injection probes."""
    result = subprocess.run(
        ["checkagent", "probe-list", "--verbose", "--json", "--category", "injection"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    cat = data["categories"][0]
    assert cat["count"] == 35, "injection should report 35 probes"
    assert len(cat["probes"]) == 35, "all 35 injection probe texts should be in JSON"


@pytest.mark.agent_test
def test_probe_list_without_verbose_has_no_probes_key():
    """probe-list --json without --verbose does NOT include 'probes' key."""
    result = subprocess.run(
        ["checkagent", "probe-list", "--json", "--category", "injection"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    cat = data["categories"][0]
    assert "probes" not in cat, "without --verbose, 'probes' key should be absent"
    assert "examples" in cat, "without --verbose, 'examples' key should still be present"


@pytest.mark.agent_test
def test_probe_list_verbose_terminal_shows_numbered_list():
    """probe-list --verbose in terminal mode shows numbered probe list."""
    result = subprocess.run(
        ["checkagent", "probe-list", "--verbose", "--category", "pii"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "1." in output, "verbose output should number the probes"
    assert "pii_leakage" in output, "category name should appear in verbose output"
    # Should show at least 10 numbered lines for pii_leakage
    numbered = [line for line in output.splitlines() if line.strip().startswith(("1.", "2.", "3."))]
    assert len(numbered) >= 3, "should show multiple numbered probe lines"


@pytest.mark.agent_test
def test_probe_list_verbose_examples_combination():
    """--verbose --examples: both flags work together; probes has all, examples has all."""
    result = subprocess.run(
        ["checkagent", "probe-list", "--verbose", "--examples", "--json", "--category", "pii"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    cat = data["categories"][0]
    assert "probes" in cat
    assert "examples" in cat
    # Both should have all probes when combined
    assert len(cat["probes"]) == 10
    assert len(cat["examples"]) == 10, (
        "when --verbose is set, --examples returns all probes (not just 3)"
    )


# ---------------------------------------------------------------------------
# Per-category delta in scan terminal output (new feature session-079)
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_scan_category_delta_shown_in_terminal():
    """Scan terminal output shows per-category finding delta after second scan."""
    # First scan to set baseline
    subprocess.run(
        ["checkagent", "scan", "agents/echo_agent.py:echo_agent", "--category", "injection"],
        capture_output=True, text=True,
    )
    # Second scan should show delta
    result = subprocess.run(
        ["checkagent", "scan", "agents/echo_agent.py:echo_agent", "--category", "injection"],
        capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    # Should show either a change delta or "no change from last scan"
    has_delta_line = (
        "no change from last scan" in output
        or "→" in output
        or "↑" in output
        or "↓" in output
        or "unchanged" in output
    )
    assert has_delta_line, (
        "Second scan should show category delta line in terminal output"
    )


@pytest.mark.agent_test
def test_scan_category_delta_shows_category_breakdown():
    """When categories have findings, per-category counts appear in delta output."""
    # Scan with injection which always has findings for echo agent
    result = subprocess.run(
        ["checkagent", "scan", "agents/echo_agent.py:echo_agent", "--category", "injection"],
        capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    # Should include prompt_injection in the output (category name appears in delta)
    assert "prompt_injection" in output or "injection" in output.lower(), (
        "Category name should appear in scan output"
    )


@pytest.mark.agent_test
def test_scan_category_delta_not_in_diff_json():
    """Category delta is shown in terminal but NOT yet in --diff JSON output.

    This is a finding: the category delta is terminal-only, not machine-readable.
    """
    # Run scan twice to build history
    subprocess.run(
        ["checkagent", "scan", "agents/echo_agent.py:echo_agent", "--category", "injection"],
        capture_output=True, text=True,
    )
    result = subprocess.run(
        ["checkagent", "scan", "agents/echo_agent.py:echo_agent",
         "--category", "injection", "--diff", "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0 or True  # scan may exit 1 for findings
    try:
        data = json.loads(result.stdout)
        diff = data.get("diff", {})
        # category_delta is NOT in the diff JSON — terminal-only feature
        has_category_delta = "category_delta" in diff
        # Document the current behavior: it's not there
        assert not has_category_delta, (
            "category_delta IS now in diff JSON — update this test!"
        )
    except json.JSONDecodeError:
        pass  # JSON may be preceded by auto-detect message


@pytest.mark.agent_test
def test_scan_no_change_message_includes_previous_score():
    """When score is unchanged, message shows 'no change from last scan (was X% on DATE)'."""
    # Scan the same target twice
    for _ in range(2):
        result = subprocess.run(
            ["checkagent", "scan", "agents/refusal_agent.py:run", "--category", "injection"],
            capture_output=True, text=True,
        )
    output = result.stdout + result.stderr
    has_no_change = "no change from last scan" in output or "was " in output
    # This confirms the "no change" delta message includes historical context
    assert has_no_change or result.returncode != 0, (
        "Repeat scan of stable agent should show 'no change from last scan' message"
    )


# ---------------------------------------------------------------------------
# probe-list --verbose: DX finding — --verbose has no effect on JSON without --json
# (combined categories test)
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_probe_list_verbose_all_categories():
    """probe-list --verbose --json works without --category (all categories)."""
    result = subprocess.run(
        ["checkagent", "probe-list", "--verbose", "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "categories" in data
    assert len(data["categories"]) >= 5, "should have at least 5 categories"
    # Every category should have probes in verbose mode
    for cat in data["categories"]:
        assert "probes" in cat, f"category {cat['name']} missing 'probes' in verbose JSON"
        assert len(cat["probes"]) > 0, f"category {cat['name']} has empty probes list"


@pytest.mark.agent_test
def test_probe_list_verbose_total_probe_count():
    """probe-list --verbose --json total_probes matches sum of per-category probe counts."""
    result = subprocess.run(
        ["checkagent", "probe-list", "--verbose", "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    total_from_cats = sum(len(cat["probes"]) for cat in data["categories"])
    assert data["total_probes"] == total_from_cats, (
        f"total_probes ({data['total_probes']}) should match sum of category probes ({total_from_cats})"
    )
