"""Session-074 tests: v1.4.0 — F-150 fixed, compare command, --generate-tests xfail, F-153 new."""

import json
import subprocess

import pytest


# ---------------------------------------------------------------------------
# F-150 FIXED: TargetedProbeSet implements ProbeSet protocol
# ---------------------------------------------------------------------------


def test_f150_targeted_probe_set_len():
    """F-150 FIXED: TargetedProbeSet supports len()."""
    from checkagent import TargetedProbeSet, analyze_prompt, generate_targeted_probes

    result = analyze_prompt("You are a helpful assistant.")
    targeted = generate_targeted_probes(result)
    assert isinstance(targeted, TargetedProbeSet)
    assert len(targeted) > 0
    assert len(targeted) == targeted.total_count


def test_f150_targeted_probe_set_iter():
    """F-150 FIXED: TargetedProbeSet supports iter() — can iterate probes directly."""
    from checkagent import analyze_prompt, generate_targeted_probes
    from checkagent.safety import Probe

    result = analyze_prompt("You are a helpful assistant.")
    targeted = generate_targeted_probes(result)
    probes = list(targeted)
    assert len(probes) > 0
    assert all(isinstance(p, Probe) for p in probes)


def test_f150_targeted_probe_set_filter():
    """F-150 FIXED: TargetedProbeSet.filter() returns a ProbeSet."""
    from checkagent import ProbeSet, analyze_prompt, generate_targeted_probes

    result = analyze_prompt("You are a helpful assistant.")
    targeted = generate_targeted_probes(result)
    filtered = targeted.filter(severity="CRITICAL")
    assert isinstance(filtered, ProbeSet)
    assert len(filtered) > 0
    for probe in filtered:
        assert probe.severity.value.upper() == "CRITICAL"


def test_f150_targeted_probe_set_add():
    """F-150 FIXED: TargetedProbeSet + ProbeSet returns ProbeSet."""
    from checkagent import ProbeSet, analyze_prompt, generate_targeted_probes
    from checkagent.safety import probes_injection

    result = analyze_prompt("You are a helpful assistant.")
    targeted = generate_targeted_probes(result)
    combined = targeted + probes_injection.all_probes
    assert isinstance(combined, ProbeSet)
    # combined has at least as many probes as targeted
    assert len(combined) >= len(targeted)


def test_f150_targeted_probe_set_direct_parametrize_compatible():
    """F-150 FIXED: TargetedProbeSet can be passed directly to parametrize via list()."""
    from checkagent import analyze_prompt, generate_targeted_probes

    result = analyze_prompt("You are a helpful assistant.")
    targeted = generate_targeted_probes(result)
    # Before fix, list(targeted) would raise TypeError; now it works
    probes_list = list(targeted)
    assert len(probes_list) > 0


# ---------------------------------------------------------------------------
# F-152 FIXED: ruff lint, v1.4.0 published to PyPI
# ---------------------------------------------------------------------------


def test_f152_version_is_140():
    """F-152 FIXED and F-151 partially resolved: v1.4.0 now on PyPI and installed."""
    import checkagent

    assert checkagent.__version__ == "1.4.0"


def test_f151_pypi_v140_published():
    """F-151 FIXED: v1.4.0 now published to PyPI (was stuck at v1.1.0 for 19+ days)."""
    import importlib.metadata

    version = importlib.metadata.version("checkagent")
    assert version == "1.4.0"


# ---------------------------------------------------------------------------
# F-056 FIXED: LangChainAdapter final_output now extracts value from dicts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f056_fixed_output_key_extraction():
    """F-056 FIXED: LangChain dict return with 'output' key → final_output is extracted string."""
    from langchain_core.runnables import RunnableLambda

    from checkagent.adapters.langchain import LangChainAdapter

    adapter = LangChainAdapter(RunnableLambda(lambda x: {"output": "extracted", "extra": "ignored"}))
    result = await adapter.run("test")
    assert result.final_output == "extracted"
    assert result.steps[0].output_text == "extracted"


@pytest.mark.asyncio
async def test_f056_fixed_no_output_key_first_value():
    """F-056 FIXED: Dict without 'output' key → first value extracted for both final_output and output_text."""
    from langchain_core.runnables import RunnableLambda

    from checkagent.adapters.langchain import LangChainAdapter

    adapter = LangChainAdapter(RunnableLambda(lambda x: {"result": "first_value", "other": "world"}))
    result = await adapter.run("test")
    # Both now extracted (was: only output_text extracted, final_output was raw dict)
    assert result.final_output == "first_value"
    assert result.steps[0].output_text == "first_value"


# ---------------------------------------------------------------------------
# compare command (new in v1.4.0)
# ---------------------------------------------------------------------------


def test_compare_basic_terminal_output():
    """compare command produces a comparison table with two agent columns."""
    result = subprocess.run(
        [
            "checkagent",
            "compare",
            "agents/echo_agent.py:echo_agent",
            "agents/refusal_agent.py:run",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    output = result.stdout
    assert "Agent Safety Comparison" in output
    assert "Safety Score" in output
    assert "Winner" in output or "winner" in output.lower()


def test_compare_json_structure():
    """compare --json returns correct structure with agent_a, agent_b, categories, winner."""
    result = subprocess.run(
        [
            "checkagent",
            "compare",
            "agents/echo_agent.py:echo_agent",
            "agents/refusal_agent.py:run",
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)

    assert "agent_a" in data
    assert "agent_b" in data
    assert "score_delta" in data
    assert "categories" in data
    assert "winner" in data

    assert data["agent_a"]["target"] == "agents/echo_agent.py:echo_agent"
    assert data["agent_b"]["target"] == "agents/refusal_agent.py:run"
    assert data["winner"] == "agent_b"
    assert isinstance(data["score_delta"], float)


def test_compare_json_score_delta_correct():
    """compare --json score_delta correctly reflects score difference."""
    result = subprocess.run(
        [
            "checkagent",
            "compare",
            "agents/echo_agent.py:echo_agent",
            "agents/refusal_agent.py:run",
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    expected_delta = round(data["agent_b"]["score"] - data["agent_a"]["score"], 4)
    assert abs(data["score_delta"] - expected_delta) < 0.001


def test_compare_json_tie_when_same_agent():
    """compare --json shows winner: tie when comparing identical agents."""
    result = subprocess.run(
        [
            "checkagent",
            "compare",
            "agents/echo_agent.py:echo_agent",
            "agents/echo_agent.py:echo_agent",
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["winner"] == "tie"
    assert data["score_delta"] == 0.0
    assert data["only_agent_a"] == []
    assert data["only_agent_b"] == []


def test_f153_compare_only_agent_a_empty_string_bug():
    """F-153: compare --json only_agent_a returns [''] instead of actual unique category names.

    When agent_a has findings in categories that agent_b doesn't, only_agent_a should
    contain those category names. Instead it contains [''] (a list with one empty string).
    """
    result = subprocess.run(
        [
            "checkagent",
            "compare",
            "agents/echo_agent.py:echo_agent",
            "agents/refusal_agent.py:run",
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    # BUG: only_agent_a is [''] but should be ['pii_leakage', 'prompt_injection']
    # (categories where echo fails but refusal doesn't)
    assert data["only_agent_a"] == [""]  # Documents the current buggy behavior
    # What it SHOULD be:
    # assert 'pii_leakage' in data['only_agent_a']
    # assert 'prompt_injection' in data['only_agent_a']


# ---------------------------------------------------------------------------
# --generate-tests enhanced: regression tests + xfail for findings (v1.4.0)
# ---------------------------------------------------------------------------


def test_generate_tests_includes_xfail_for_findings(tmp_path):
    """--generate-tests now includes xfail tests for current findings."""
    output_file = tmp_path / "test_generated.py"
    result = subprocess.run(
        [
            "checkagent",
            "scan",
            "agents/echo_agent.py:echo_agent",
            "--category",
            "injection",
            "--generate-tests",
            str(output_file),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0  # echo agent has findings → non-zero exit
    content = output_file.read_text()
    assert "pytest.mark.xfail" in content
    assert "Known safety gap" in content


def test_generate_tests_includes_regression_tests_for_passed(tmp_path):
    """--generate-tests includes regression tests for probes that passed."""
    output_file = tmp_path / "test_generated.py"
    subprocess.run(
        [
            "checkagent",
            "scan",
            "agents/refusal_agent.py:run",
            "--category",
            "injection",
            "--generate-tests",
            str(output_file),
        ],
        capture_output=True,
        text=True,
    )
    content = output_file.read_text()
    # refusal agent passes all, so should have regression tests but no xfail
    assert "def test_" in content
    assert "pytest.mark.xfail" not in content


def test_generate_tests_terminal_shows_counts(tmp_path):
    """--generate-tests terminal output shows regression + xfail test counts."""
    output_file = tmp_path / "test_generated.py"
    result = subprocess.run(
        [
            "checkagent",
            "scan",
            "agents/echo_agent.py:echo_agent",
            "--category",
            "injection",
            "--generate-tests",
            str(output_file),
        ],
        capture_output=True,
        text=True,
    )
    # Terminal should mention regression + xfail counts
    output = result.stdout + result.stderr
    assert "regression" in output.lower()
    assert "xfail" in output.lower()


def test_generate_tests_xfail_tests_run_as_xfailed(tmp_path):
    """xfail tests in generated file actually run as xfailed (not failures) in pytest."""
    output_file = tmp_path / "test_generated.py"
    subprocess.run(
        [
            "checkagent",
            "scan",
            "agents/echo_agent.py:echo_agent",
            "--category",
            "injection",
            "--generate-tests",
            str(output_file),
        ],
        capture_output=True,
        text=True,
    )
    # Run the generated tests — should have xfailed not failures
    pytest_result = subprocess.run(
        ["pytest", str(output_file), "--tb=short", "-q"],
        capture_output=True,
        text=True,
    )
    assert "failed" not in pytest_result.stdout.lower() or "xfailed" in pytest_result.stdout.lower()
    assert "xfailed" in pytest_result.stdout.lower()
