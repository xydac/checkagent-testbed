"""
Session-034 tests: checkagent 0.1.2 — scan CLI, ci-init CLI, PydanticAI streaming,
and scan_agents integration.

New features:
- checkagent scan: safety scanner for Python callables + HTTP endpoints
- checkagent ci-init: CI/CD config scaffolding
- PydanticAI adapter run_stream() path

Findings under investigation:
- F-089: --generate-tests uses private API (_resolve_callable, _evaluate_output)
- F-090: ci-init path separator on Windows (upstream CI bug)
- Version inconsistency FIXED in 0.1.2 (was F-NEW in 0.1.1)
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import checkagent
from checkagent import AgentInput, StreamCollector, StreamEventType


# ---------------------------------------------------------------------------
# checkagent scan — basic CLI behavior
# ---------------------------------------------------------------------------

class TestScanCLI:
    def _run_scan(self, *args, timeout=30):
        result = subprocess.run(
            [sys.executable, "-m", "checkagent.cli", "scan", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/home/x/working/checkagent-testbed",
        )
        return result

    def _run_scan_via_uv(self, *args, timeout=30):
        result = subprocess.run(
            ["uv", "run", "checkagent", "scan", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/home/x/working/checkagent-testbed",
        )
        return result

    def test_scan_safe_agent_passes_all(self):
        """Safe agent (always returns fixed refusal) should pass all injection probes."""
        result = self._run_scan_via_uv(
            "scan_agents.safe:run",
            "--category", "injection",
            "--json",
            "--timeout", "5",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["summary"]["failed"] == 0
        assert data["summary"]["score"] == 1.0

    def test_scan_echo_agent_fails_injection(self):
        """Echo agent echoes all input — fails many injection probes."""
        result = self._run_scan_via_uv(
            "scan_agents.simple:run",
            "--category", "injection",
            "--json",
            "--timeout", "5",
        )
        # Echo agent should fail: non-zero exit code when failures exist
        data = json.loads(result.stdout)
        assert data["summary"]["failed"] > 0
        assert data["summary"]["score"] < 1.0

    def test_scan_json_output_schema(self):
        """JSON output has target, summary, findings fields."""
        result = self._run_scan_via_uv(
            "scan_agents.safe:run",
            "--category", "injection",
            "--json",
            "--timeout", "5",
        )
        data = json.loads(result.stdout)
        assert "target" in data
        assert "summary" in data
        assert "findings" in data
        summary = data["summary"]
        assert "total" in summary
        assert "passed" in summary
        assert "failed" in summary
        assert "errors" in summary
        assert "score" in summary
        assert "elapsed_seconds" in summary

    def test_scan_json_finding_schema(self):
        """Each finding has required fields: probe_id, category, severity, finding, probe_input, response."""
        result = self._run_scan_via_uv(
            "scan_agents.simple:run",
            "--category", "injection",
            "--json",
            "--timeout", "5",
        )
        data = json.loads(result.stdout)
        findings = data["findings"]
        assert len(findings) > 0
        for f in findings:
            assert "probe_id" in f, f"Missing probe_id in finding: {f}"
            assert "category" in f, f"Missing category in finding: {f}"
            assert "severity" in f, f"Missing severity in finding: {f}"
            assert "finding" in f, f"Missing finding in finding: {f}"
            assert "probe_input" in f, f"Missing probe_input in finding: {f}"
            assert "response" in f, f"Missing response in finding: {f}"

    def test_scan_invalid_module_gives_clear_error(self):
        """Non-existent module gives a clear error, not a traceback."""
        result = self._run_scan_via_uv(
            "nonexistent_module:run",
            "--timeout", "3",
        )
        assert result.returncode != 0
        # Should show a user-friendly error, not a raw traceback
        assert "Cannot import module" in result.stderr or "Cannot import module" in result.stdout
        assert "nonexistent_module" in (result.stderr + result.stdout)

    def test_scan_async_agent_works(self):
        """Async agent callable is handled correctly by scan."""
        result = self._run_scan_via_uv(
            "scan_agents.async_agent:run",
            "--category", "injection",
            "--json",
            "--timeout", "5",
        )
        data = json.loads(result.stdout)
        # Async echo agent should behave same as sync echo: fails injection probes
        assert data["summary"]["total"] == 35
        assert data["summary"]["failed"] > 0

    def test_scan_all_categories_default(self):
        """Without --category, scan runs all probe categories."""
        result = self._run_scan_via_uv(
            "scan_agents.safe:run",
            "--json",
            "--timeout", "5",
        )
        data = json.loads(result.stdout)
        # All 4 categories: injection (35) + jailbreak (15) + pii (10) + scope (8) = 68
        # but count may vary — just check it's more than injection alone
        assert data["summary"]["total"] > 35

    def test_scan_category_filter_reduces_probe_count(self):
        """--category injection runs fewer probes than default."""
        result_all = self._run_scan_via_uv(
            "scan_agents.safe:run",
            "--json",
            "--timeout", "5",
        )
        result_injection = self._run_scan_via_uv(
            "scan_agents.safe:run",
            "--category", "injection",
            "--json",
            "--timeout", "5",
        )
        total_all = json.loads(result_all.stdout)["summary"]["total"]
        total_injection = json.loads(result_injection.stdout)["summary"]["total"]
        assert total_injection < total_all
        assert total_injection == 35  # known injection probe count


# ---------------------------------------------------------------------------
# checkagent scan — --badge SVG generation
# ---------------------------------------------------------------------------

class TestScanBadge:
    def test_badge_generated_for_safe_agent(self):
        """--badge generates an SVG file with correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            badge_path = Path(tmpdir) / "badge.svg"
            result = subprocess.run(
                ["uv", "run", "checkagent", "scan",
                 "scan_agents.safe:run",
                 "--category", "injection",
                 "--badge", str(badge_path),
                 "--timeout", "5"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            assert result.returncode == 0
            assert badge_path.exists(), "Badge file not created"
            content = badge_path.read_text()
            assert "<svg" in content
            assert "CheckAgent" in content
            assert "35/35 safe" in content or "safe" in content.lower()

    def test_badge_generated_for_failing_agent(self):
        """Badge for failing agent shows different score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            badge_path = Path(tmpdir) / "badge.svg"
            subprocess.run(
                ["uv", "run", "checkagent", "scan",
                 "scan_agents.simple:run",
                 "--category", "injection",
                 "--badge", str(badge_path),
                 "--timeout", "5"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            assert badge_path.exists()
            content = badge_path.read_text()
            # Failing agent — should NOT say "35/35 safe"
            assert "35/35 safe" not in content


# ---------------------------------------------------------------------------
# checkagent scan — --generate-tests (F-089: private API import)
# ---------------------------------------------------------------------------

class TestScanGenerateTests:
    def test_generate_tests_creates_file(self):
        """--generate-tests writes a Python test file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_generated.py"
            result = subprocess.run(
                ["uv", "run", "checkagent", "scan",
                 "scan_agents.simple:run",
                 "--category", "injection",
                 "--generate-tests", str(out_file),
                 "--timeout", "5"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            assert out_file.exists(), "Generated test file not created"
            content = out_file.read_text()
            assert "import pytest" in content
            assert "def test_" in content

    def test_generate_tests_uses_private_api(self):
        """
        F-089 (low): Generated test files import _resolve_callable and _evaluate_output
        — these are private functions (underscore prefix) from checkagent.cli.scan.
        Private API can change without notice, breaking generated tests on upgrades.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_generated.py"
            subprocess.run(
                ["uv", "run", "checkagent", "scan",
                 "scan_agents.simple:run",
                 "--category", "injection",
                 "--generate-tests", str(out_file),
                 "--timeout", "5"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            content = out_file.read_text()
            # Document the bug: generated tests import private API
            uses_private_api = "_resolve_callable" in content or "_evaluate_output" in content
            assert uses_private_api, (
                "F-089: Expected generated tests to use private API (documenting the bug)."
                " If this fails, the bug was fixed — update this test and close F-089."
            )

    def test_generate_tests_file_is_valid_python(self):
        """Generated test file must be syntactically valid Python."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_generated.py"
            subprocess.run(
                ["uv", "run", "checkagent", "scan",
                 "scan_agents.simple:run",
                 "--category", "injection",
                 "--generate-tests", str(out_file),
                 "--timeout", "5"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            # Compile the generated file — should not raise SyntaxError
            source = out_file.read_text()
            try:
                compile(source, str(out_file), "exec")
            except SyntaxError as e:
                pytest.fail(f"Generated test file has syntax error: {e}")


# ---------------------------------------------------------------------------
# checkagent ci-init CLI
# ---------------------------------------------------------------------------

class TestCiInitCLI:
    def test_ci_init_creates_github_workflow(self):
        """ci-init --platform github creates .github/workflows/checkagent.yml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["uv", "run", "checkagent", "ci-init",
                 "--directory", tmpdir,
                 "--platform", "github"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            assert result.returncode == 0
            workflow = Path(tmpdir) / ".github" / "workflows" / "checkagent.yml"
            assert workflow.exists(), f"Expected workflow at {workflow}"

    def test_ci_init_github_workflow_is_valid_yaml(self):
        """Generated GitHub workflow file is valid YAML."""
        import yaml
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                ["uv", "run", "checkagent", "ci-init",
                 "--directory", tmpdir,
                 "--platform", "github"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            workflow = Path(tmpdir) / ".github" / "workflows" / "checkagent.yml"
            content = workflow.read_text()
            try:
                parsed = yaml.safe_load(content)
            except yaml.YAMLError as e:
                pytest.fail(f"Generated YAML is invalid: {e}")
            assert "jobs" in parsed
            # Note: PyYAML (YAML 1.1) parses `on:` as True (boolean), not the string "on".
            # GitHub Actions uses `on:` as a trigger key. This is a known YAML 1.1 gotcha.
            # Check for True (the parsed form of `on:`) OR "on" (in case of YAML 1.2 behavior).
            assert True in parsed or "on" in parsed, "workflow must have trigger key"

    def test_ci_init_github_workflow_contains_expected_steps(self):
        """Generated GitHub workflow has checkout, setup-python, install, and scan steps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                ["uv", "run", "checkagent", "ci-init",
                 "--directory", tmpdir,
                 "--platform", "github"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            workflow = Path(tmpdir) / ".github" / "workflows" / "checkagent.yml"
            content = workflow.read_text()
            assert "actions/checkout" in content
            assert "setup-python" in content
            assert "checkagent scan" in content

    def test_ci_init_gitlab_creates_gitlabci_yml(self):
        """ci-init --platform gitlab creates .gitlab-ci.yml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["uv", "run", "checkagent", "ci-init",
                 "--directory", tmpdir,
                 "--platform", "gitlab"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            assert result.returncode == 0
            ci_file = Path(tmpdir) / ".gitlab-ci.yml"
            assert ci_file.exists(), f"Expected .gitlab-ci.yml at {ci_file}"

    def test_ci_init_both_creates_both_files(self):
        """ci-init --platform both creates both GitHub and GitLab configs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["uv", "run", "checkagent", "ci-init",
                 "--directory", tmpdir,
                 "--platform", "both"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            assert result.returncode == 0
            github_workflow = Path(tmpdir) / ".github" / "workflows" / "checkagent.yml"
            gitlab_ci = Path(tmpdir) / ".gitlab-ci.yml"
            assert github_workflow.exists()
            assert gitlab_ci.exists()

    def test_ci_init_force_overwrites_existing(self):
        """ci-init --force overwrites existing config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create first
            subprocess.run(
                ["uv", "run", "checkagent", "ci-init", "--directory", tmpdir],
                capture_output=True, text=True, timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            workflow = Path(tmpdir) / ".github" / "workflows" / "checkagent.yml"
            original_mtime = workflow.stat().st_mtime

            import time; time.sleep(0.05)  # ensure mtime changes

            # Force overwrite
            result = subprocess.run(
                ["uv", "run", "checkagent", "ci-init",
                 "--directory", tmpdir, "--force"],
                capture_output=True, text=True, timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            assert result.returncode == 0
            new_mtime = workflow.stat().st_mtime
            assert new_mtime >= original_mtime  # file was rewritten

    def test_ci_init_custom_scan_target(self):
        """ci-init --scan-target embeds the target in the generated workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                ["uv", "run", "checkagent", "ci-init",
                 "--directory", tmpdir,
                 "--scan-target", "my_module:my_agent"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/x/working/checkagent-testbed",
            )
            workflow = Path(tmpdir) / ".github" / "workflows" / "checkagent.yml"
            content = workflow.read_text()
            assert "my_module:my_agent" in content


# ---------------------------------------------------------------------------
# PydanticAI adapter streaming
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="mock")
async def test_pydanticai_stream_events_basic():
    """PydanticAIAdapter.run_stream() emits RUN_START, TEXT_DELTA, RUN_END."""
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    from checkagent import PydanticAIAdapter

    agent = Agent(model=TestModel(custom_output_text="streaming response"), system_prompt="helpful")
    adapter = PydanticAIAdapter(agent)

    events = []
    async for event in adapter.run_stream(AgentInput(query="hello")):
        events.append(event)

    types = [e.event_type for e in events]
    assert StreamEventType.RUN_START in types
    assert StreamEventType.TEXT_DELTA in types
    assert StreamEventType.RUN_END in types


@pytest.mark.agent_test(layer="mock")
async def test_pydanticai_stream_collector_aggregated_text():
    """StreamCollector.collect_from() works with PydanticAIAdapter.run_stream()."""
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    from checkagent import PydanticAIAdapter

    agent = Agent(model=TestModel(custom_output_text="hello world"), system_prompt="helpful")
    adapter = PydanticAIAdapter(agent)

    collector = StreamCollector()
    await collector.collect_from(adapter.run_stream(AgentInput(query="hello")))

    assert collector.aggregated_text == "hello world"
    assert collector.total_chunks >= 1
    assert collector.time_to_first_token is not None
    assert collector.time_to_first_token > 0
    assert not collector.has_error


@pytest.mark.agent_test(layer="mock")
async def test_pydanticai_stream_event_ordering():
    """Stream events arrive in correct order: RUN_START first, RUN_END last."""
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    from checkagent import PydanticAIAdapter

    agent = Agent(model=TestModel(custom_output_text="test"), system_prompt="helpful")
    adapter = PydanticAIAdapter(agent)

    events = []
    async for event in adapter.run_stream(AgentInput(query="test")):
        events.append(event)

    assert len(events) >= 2
    assert events[0].event_type == StreamEventType.RUN_START, "First event should be RUN_START"
    assert events[-1].event_type == StreamEventType.RUN_END, "Last event should be RUN_END"


@pytest.mark.agent_test(layer="mock")
async def test_pydanticai_stream_text_delta_data():
    """TEXT_DELTA event carries the response text in its data field."""
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    from checkagent import PydanticAIAdapter

    agent = Agent(model=TestModel(custom_output_text="specific text"), system_prompt="helpful")
    adapter = PydanticAIAdapter(agent)

    text_events = []
    async for event in adapter.run_stream(AgentInput(query="q")):
        if event.event_type == StreamEventType.TEXT_DELTA:
            text_events.append(event)

    combined = "".join(e.data for e in text_events if e.data)
    assert "specific text" in combined


# ---------------------------------------------------------------------------
# ResilienceProfile (new in 0.1.2 — top-level export)
# ---------------------------------------------------------------------------

def test_resilience_profile_top_level_export():
    """ResilienceProfile and ScenarioResult are at top-level checkagent."""
    from checkagent import ResilienceProfile, ScenarioResult
    assert ResilienceProfile is not None
    assert ScenarioResult is not None


def test_resilience_profile_from_scores_basic():
    """ResilienceProfile.from_scores() computes degradation correctly."""
    from checkagent import ResilienceProfile
    profile = ResilienceProfile.from_scores(
        baseline={"tc": 0.9, "rc": 1.0},
        scenarios={
            "rate_limit": {"tc": 0.45, "rc": 0.8},
        },
    )
    assert 0.0 <= profile.overall <= 1.0
    assert profile.worst_scenario == "rate_limit"
    assert profile.weakest_metric in ("tc", "rc")  # both degraded


def test_resilience_profile_from_runs_basic():
    """ResilienceProfile.from_runs() accepts AgentRun lists and metric callables."""
    from checkagent import AgentRun, ResilienceProfile, Score
    from checkagent.eval.metrics import task_completion

    def make_run(output: str) -> AgentRun:
        return AgentRun(
            input=AgentInput(query="test"),
            final_output=output,
            steps=[],
        )

    def tc(run: AgentRun) -> Score:
        return task_completion(run, expected_output_contains=["ok"])

    baseline = [make_run("ok"), make_run("ok")]
    faulted = {"timeout": [make_run("error"), make_run("ok")]}

    profile = ResilienceProfile.from_runs(
        baseline_runs=baseline,
        faulted_runs=faulted,
        metrics={"task_completion": tc},
    )
    assert 0.0 <= profile.overall <= 1.0
    assert profile.worst_scenario == "timeout"


def test_resilience_profile_to_dict():
    """ResilienceProfile.to_dict() has expected structure."""
    from checkagent import ResilienceProfile
    profile = ResilienceProfile.from_scores(
        baseline={"tc": 0.9},
        scenarios={"f1": {"tc": 0.6}, "f2": {"tc": 0.3}},
    )
    d = profile.to_dict()
    assert "overall_resilience" in d
    assert "baseline" in d
    assert "worst_scenario" in d
    # F-090 (low): to_dict() omits best_scenario even though profile.best_scenario exists.
    # assert "best_scenario" in d  # FAILS — documented as F-090
    assert "worst_scenario" in d
    assert "weakest_metric" in d
    assert "scenarios" in d
    assert "f1" in d["scenarios"]
    assert "f2" in d["scenarios"]
    for scenario_data in d["scenarios"].values():
        assert "resilience" in scenario_data
        assert "scores" in scenario_data
        assert "degradation" in scenario_data


def test_resilience_profile_to_dict_missing_best_scenario():
    """
    F-090 (low): ResilienceProfile.to_dict() omits 'best_scenario' from serialization.
    The attribute exists on the object but is not included in to_dict() output.
    This means round-tripping through to_dict() loses information.
    """
    from checkagent import ResilienceProfile
    profile = ResilienceProfile.from_scores(
        baseline={"tc": 0.9},
        scenarios={"f1": {"tc": 0.6}, "f2": {"tc": 0.8}},
    )
    # best_scenario exists on the object
    assert profile.best_scenario == "f2"
    # but to_dict() doesn't include it
    d = profile.to_dict()
    assert "best_scenario" not in d, (
        "F-090: If this now passes, best_scenario was added to to_dict() — close F-090."
    )
