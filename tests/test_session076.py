"""Session-076 tests: F-062 fixed, F-155 new (compare --url-a), --targeted+--llm-judge compose.

Upstream: v1.4.0 installed, CI green, latest commit "Add scan workflow guide" (docs only).
"""
import json
import subprocess
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# F-062 FIXED: AnthropicAdapter.final_output is now a string, not raw object
# ---------------------------------------------------------------------------

def make_mock_anthropic_message(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text, type="text")]
    msg.usage = MagicMock(input_tokens=10, output_tokens=5)
    return msg


def make_mock_anthropic_client(text: str = "hello", raises=None):
    client = MagicMock()
    if raises:
        client.messages.create = AsyncMock(side_effect=raises)
    else:
        client.messages.create = AsyncMock(return_value=make_mock_anthropic_message(text))
    return client


@pytest.mark.asyncio
async def test_f062_fixed_anthropic_final_output_is_string():
    """F-062 FIXED: AnthropicAdapter.final_output now extracts string from message content."""
    with patch("checkagent.adapters.anthropic._ensure_anthropic"):
        from checkagent.adapters.anthropic import AnthropicAdapter
        client = make_mock_anthropic_client("Hello from Anthropic")
        adapter = AnthropicAdapter(client)
        result = await adapter.run("test query")
    assert result.final_output == "Hello from Anthropic"
    assert isinstance(result.final_output, str)
    assert result.steps[0].output_text == "Hello from Anthropic"


@pytest.mark.asyncio
async def test_f062_fixed_final_output_matches_output_text():
    """F-062 FIXED: final_output and step.output_text both return same string."""
    with patch("checkagent.adapters.anthropic._ensure_anthropic"):
        from checkagent.adapters.anthropic import AnthropicAdapter
        client = make_mock_anthropic_client("Paris is the capital of France")
        adapter = AnthropicAdapter(client)
        result = await adapter.run("What is the capital of France?")
    # Both should return the same extracted string
    assert result.final_output == result.steps[0].output_text
    assert result.final_output == "Paris is the capital of France"


# ---------------------------------------------------------------------------
# F-155 NEW: compare --url-a / --url-b shown in help but not implemented
# ---------------------------------------------------------------------------

def test_f155_compare_url_a_option_does_not_exist():
    """F-155: compare --url-a is shown in help examples but raises 'No such option'.

    The --help for compare shows:
        checkagent compare --url-a http://a/chat --url-b http://b/chat --json
    but the option doesn't actually exist, causing "Error: No such option: --url-a".
    This is a documentation-code mismatch.
    """
    result = subprocess.run(
        ["checkagent", "compare", "--url-a", "http://localhost:9000", "--url-b", "http://localhost:9001"],
        capture_output=True, text=True
    )
    assert result.returncode == 2
    assert "No such option" in result.stderr or "No such option" in result.stdout


def test_f155_compare_help_advertises_url_flags():
    """F-155: compare --help examples reference --url-a/--url-b that don't exist."""
    result = subprocess.run(
        ["checkagent", "compare", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    # The help text mentions url-a/url-b in examples
    combined = result.stdout + result.stderr
    assert "url-a" in combined or "url-b" in combined, (
        "If this fails, the docs bug is fixed — help no longer advertises non-existent flags"
    )
    # But the Options section doesn't list them
    # Split between "Examples" and "Options" sections
    assert "--url-a" not in combined.split("Options:")[1] if "Options:" in combined else True


def test_f155_compare_url_b_option_does_not_exist():
    """F-155: compare --url-b also raises 'No such option'."""
    result = subprocess.run(
        ["checkagent", "compare", "--url-b", "http://localhost:9001", "agent_a:fn", "agent_b:fn"],
        capture_output=True, text=True
    )
    assert result.returncode == 2
    assert "No such option" in result.stderr or "No such option" in result.stdout


# ---------------------------------------------------------------------------
# --targeted + --llm-judge compose correctly
# ---------------------------------------------------------------------------

def test_targeted_and_llm_judge_compose_json_keys():
    """--targeted and --llm-judge can be combined; JSON has prompt_analysis + evaluator."""
    result = subprocess.run(
        [
            "checkagent", "scan",
            "agents/refusal_agent.py:run",
            "--prompt-file", "prompts/secure_hr_agent.txt",
            "--targeted",
            "--llm-judge", "claude-code",
            "--category", "injection",
            "--json",
        ],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    # Find JSON in output (may have non-JSON preamble)
    output = result.stdout + result.stderr
    start = output.find("{")
    assert start >= 0, f"No JSON in output: {output[:300]}"
    data = json.loads(output[start:])

    assert "summary" in data
    assert "prompt_analysis" in data, "F-155 related: --targeted should add prompt_analysis key"
    assert data["summary"]["evaluator"] == "claude-code", "evaluator field should reflect --llm-judge"


def test_targeted_with_good_prompt_reduces_probe_count():
    """--targeted with a well-secured prompt runs fewer probes than the full set."""
    # Full scan (no --targeted)
    full_result = subprocess.run(
        [
            "checkagent", "scan",
            "agents/refusal_agent.py:run",
            "--category", "injection",
            "--json",
        ],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    # Targeted scan
    targeted_result = subprocess.run(
        [
            "checkagent", "scan",
            "agents/refusal_agent.py:run",
            "--prompt-file", "prompts/secure_hr_agent.txt",
            "--targeted",
            "--category", "injection",
            "--json",
        ],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )

    def extract_total(output):
        start = output.find("{")
        d = json.loads(output[start:])
        return d["summary"]["total"]

    full_total = extract_total(full_result.stdout + full_result.stderr)
    targeted_total = extract_total(targeted_result.stdout + targeted_result.stderr)

    # A well-secured prompt (6/8 checks passing) should reduce probe count
    assert targeted_total < full_total, (
        f"--targeted should reduce probes for a well-secured prompt: "
        f"got {targeted_total} vs {full_total} full"
    )


def test_targeted_prompt_analysis_has_correct_structure():
    """--targeted JSON output has prompt_analysis with score, passed_count, total_count, checks."""
    result = subprocess.run(
        [
            "checkagent", "scan",
            "agents/refusal_agent.py:run",
            "--prompt-file", "prompts/secure_hr_agent.txt",
            "--targeted",
            "--category", "injection",
            "--json",
        ],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    output = result.stdout + result.stderr
    start = output.find("{")
    data = json.loads(output[start:])

    pa = data["prompt_analysis"]
    assert "score" in pa
    assert "passed_count" in pa
    assert "total_count" in pa
    assert "checks" in pa
    assert isinstance(pa["checks"], list)
    assert len(pa["checks"]) > 0
    # Each check should have id, name, passed, severity
    check = pa["checks"][0]
    assert "id" in check
    assert "name" in check
    assert "passed" in check
    assert "severity" in check


def test_targeted_without_prompt_file_gives_clear_error():
    """--targeted without --prompt-file gives a clear error message."""
    result = subprocess.run(
        [
            "checkagent", "scan",
            "agents/refusal_agent.py:run",
            "--targeted",
        ],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "--prompt-file" in output, "Error should mention --prompt-file requirement"
    assert "--targeted" in output


# ---------------------------------------------------------------------------
# compare command: callable targets work correctly
# ---------------------------------------------------------------------------

def test_compare_callable_targets_json_structure():
    """compare with two callable targets returns correct JSON structure."""
    result = subprocess.run(
        [
            "checkagent", "compare",
            "agents/refusal_agent.py:run",
            "agents/echo_agent.py:echo_agent",
            "--json",
        ],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)

    assert "agent_a" in data
    assert "agent_b" in data
    assert "score_delta" in data
    assert "winner" in data
    assert "only_agent_a" in data
    assert "only_agent_b" in data


def test_compare_winner_is_higher_scoring_agent():
    """compare winner field correctly identifies the higher-scoring agent.

    F-156: score_delta sign is counter-intuitive — it's computed as agent_b - agent_a,
    so score_delta is NEGATIVE when agent_a is the winner (higher score). Users would
    expect score_delta to be positive when agent_a wins, but it isn't. Undocumented.
    """
    result = subprocess.run(
        [
            "checkagent", "compare",
            "agents/refusal_agent.py:run",   # score ~1.0
            "agents/echo_agent.py:echo_agent",  # score ~0.0
            "--json",
        ],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)

    assert data["winner"] == "agent_a"
    assert data["agent_a"]["score"] > data["agent_b"]["score"]
    # F-156: score_delta = agent_b - agent_a, so NEGATIVE when agent_a wins
    assert data["score_delta"] < 0, (
        "score_delta is agent_b_score - agent_a_score: negative when agent_a wins"
    )


def test_compare_only_agent_b_returns_probe_names():
    """compare only_agent_b returns individual probe name IDs (F-153 verified still fixed)."""
    result = subprocess.run(
        [
            "checkagent", "compare",
            "agents/refusal_agent.py:run",
            "agents/echo_agent.py:echo_agent",
            "--json",
        ],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)

    only_b = data["only_agent_b"]
    # Echo agent should fail many injection probes that refusal agent passes
    assert len(only_b) > 0
    # All entries should be non-empty probe name strings (F-153 fixed)
    for probe_id in only_b:
        assert probe_id != "", f"F-153 regression: found empty string in only_agent_b"
        assert isinstance(probe_id, str)


def test_compare_no_scan_history_gives_friendly_error():
    """compare gives friendly error message when no scan history exists for a target."""
    result = subprocess.run(
        [
            "checkagent", "compare",
            "agents/nonexistent_agent.py:run",
            "agents/refusal_agent.py:run",
        ],
        capture_output=True, text=True, cwd="/home/x/working/checkagent-testbed"
    )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "No scan history" in output or "not found" in output.lower()


# ---------------------------------------------------------------------------
# CI is green — upstream health check
# ---------------------------------------------------------------------------

def test_upstream_ci_green():
    """Upstream CI is green: all 3 latest runs succeeded."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "3"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    output = result.stdout
    # Count non-success lines (excluding header)
    lines = [l for l in output.strip().split("\n") if l.strip() and "\t" in l]
    failed = [l for l in lines if "failure" in l or "cancelled" in l]
    assert len(failed) == 0, f"CI has failing runs:\n{chr(10).join(failed)}"
