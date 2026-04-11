"""Session-022: Anthropic/CrewAI/PydanticAI adapters, JUnit XML, new findings.

Upgraded to latest (mark all framework adapters as complete).
New: AnthropicAdapter, CrewAIAdapter, PydanticAIAdapter, checkagent.ci.junit_xml.
"""
import asyncio
import json
from unittest.mock import MagicMock, patch
from xml.etree import ElementTree as ET

import pytest

from checkagent import AgentRun, AgentInput, Step

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_run(output="hello world"):
    return AgentRun(input=AgentInput(query="test"), final_output=output)


def make_mock_anthropic_message(text="Paris"):
    """Minimal fake Anthropic Message response."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    block.__class__.__name__ = "TextBlock"

    usage = MagicMock()
    usage.input_tokens = 10
    usage.output_tokens = 5

    msg = MagicMock()
    msg.content = [block]
    msg.usage = usage
    msg.stop_reason = "end_turn"
    return msg


def make_mock_anthropic_client(text="Paris", raises=None):
    """Fake Anthropic client with async messages.create."""
    client = MagicMock()

    async def async_create(**kwargs):
        if raises:
            raise raises
        return make_mock_anthropic_message(text)

    client.messages = MagicMock()
    client.messages.create = async_create
    # No .stream by default (use run, not run_stream)
    del client.messages.stream
    return client


# ---------------------------------------------------------------------------
# F-054 FIXED: LangChain adapter now uses perf_counter — CI passing on Windows
# ---------------------------------------------------------------------------


def test_f054_langchain_adapter_uses_perf_counter():
    """Verify LangChain adapter source was changed to time.perf_counter."""
    import checkagent.adapters.langchain as la
    import inspect
    src = inspect.getsource(la)
    assert "perf_counter" in src, (
        "F-054: LangChain adapter still using time.monotonic() — "
        "Windows CI will fail again"
    )


# ---------------------------------------------------------------------------
# AnthropicAdapter: basic functionality (F-062, F-063, F-064)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anthropic_adapter_string_input_coercion():
    """AnthropicAdapter.run() accepts plain strings — coerces to AgentInput."""
    with patch("checkagent.adapters.anthropic._ensure_anthropic"):
        from checkagent.adapters.anthropic import AnthropicAdapter
        client = make_mock_anthropic_client("bonjour")
        adapter = AnthropicAdapter(client)
        result = await adapter.run("hello")
    assert result.error is None
    assert isinstance(result, AgentRun)


@pytest.mark.asyncio
async def test_anthropic_adapter_step_output_text():
    """AnthropicAdapter.run() creates a step with correct output_text."""
    with patch("checkagent.adapters.anthropic._ensure_anthropic"):
        from checkagent.adapters.anthropic import AnthropicAdapter
        client = make_mock_anthropic_client("Paris")
        adapter = AnthropicAdapter(client, model="test-model")
        result = await adapter.run(AgentInput(query="What is the capital of France?"))
    assert len(result.steps) == 1
    assert result.steps[0].output_text == "Paris"


@pytest.mark.asyncio
async def test_f062_anthropic_adapter_final_output_is_raw_message():
    """F-062: AnthropicAdapter.final_output is the raw message object, not text.

    This is inconsistent with step.output_text which correctly extracts text.
    Users who call result.final_output expecting a string will get an object.
    """
    with patch("checkagent.adapters.anthropic._ensure_anthropic"):
        from checkagent.adapters.anthropic import AnthropicAdapter
        mock_msg = make_mock_anthropic_message("Paris")
        client = make_mock_anthropic_client("Paris")
        # Override to return the same mock_msg we can check identity
        async def create(**kw):
            return mock_msg
        client.messages.create = create
        adapter = AnthropicAdapter(client)
        result = await adapter.run("test")
    # Bug: final_output is the raw message object, not the text string
    assert result.final_output is not None
    assert result.final_output is not "Paris"  # NOT the string
    # step.output_text correctly extracts text but final_output doesn't
    assert result.steps[0].output_text == "Paris"
    # final_output is the MagicMock message object
    assert hasattr(result.final_output, "content"), (
        "F-062: final_output is raw message object with .content, not the string 'Paris'"
    )


@pytest.mark.asyncio
async def test_anthropic_adapter_error_handling():
    """AnthropicAdapter.run() captures exceptions in AgentRun.error."""
    with patch("checkagent.adapters.anthropic._ensure_anthropic"):
        from checkagent.adapters.anthropic import AnthropicAdapter
        client = make_mock_anthropic_client(
            raises=RuntimeError("API rate limit exceeded")
        )
        adapter = AnthropicAdapter(client)
        result = await adapter.run("test")
    assert result.error is not None
    assert "rate limit exceeded" in result.error
    assert result.final_output is None


@pytest.mark.asyncio
async def test_anthropic_adapter_duration_ms_positive():
    """AnthropicAdapter uses time.perf_counter — duration_ms should be >= 0."""
    with patch("checkagent.adapters.anthropic._ensure_anthropic"):
        from checkagent.adapters.anthropic import AnthropicAdapter
        client = make_mock_anthropic_client("response")
        adapter = AnthropicAdapter(client)
        result = await adapter.run("test")
    assert result.duration_ms >= 0.0


def test_f064_anthropic_not_declared_as_dependency():
    """F-064: anthropic package is not in checkagent's declared dependencies."""
    import importlib.metadata
    d = importlib.metadata.distribution("checkagent")
    reqs = d.metadata.get_all("Requires-Dist") or []
    # Must not be in base deps (might be in an optional extra)
    base_deps = [r for r in reqs if "extra ==" not in r]
    anthropic_in_base = any("anthropic" in r.lower() for r in base_deps)
    assert not anthropic_in_base, (
        "F-064 may be fixed: anthropic is now a base dependency"
    )


def test_f063_anthropic_adapter_at_top_level():
    """F-063 FIXED: AnthropicAdapter now importable from top-level checkagent."""
    import checkagent
    assert hasattr(checkagent, "AnthropicAdapter"), "AnthropicAdapter should be at top-level"


def test_anthropic_adapter_raises_on_missing_package():
    """AnthropicAdapter raises ImportError with helpful message if not installed.

    NOTE: This test requires that the `anthropic` package is NOT installed.
    It was valid at session-022 time but will fail if anthropic is installed.
    We mock out the module to simulate the missing-package scenario.
    """
    import sys
    import importlib
    import unittest.mock as mock

    # Simulate anthropic not being installed by removing it from sys.modules
    # and blocking the import
    saved = sys.modules.pop("anthropic", None)
    saved_adapters = sys.modules.pop("checkagent.adapters.anthropic", None)
    try:
        with mock.patch.dict(sys.modules, {"anthropic": None}):
            import checkagent.adapters.anthropic as aa
            importlib.reload(aa)
            try:
                aa._ensure_anthropic()
                assert False, "Should have raised ImportError"
            except ImportError as e:
                assert "anthropic" in str(e).lower()
                assert "pip install" in str(e)
    finally:
        if saved is not None:
            sys.modules["anthropic"] = saved
        if saved_adapters is not None:
            sys.modules["checkagent.adapters.anthropic"] = saved_adapters


# ---------------------------------------------------------------------------
# CrewAIAdapter: basic functionality (F-063, F-064)
# ---------------------------------------------------------------------------


class MockCrewResult:
    def __init__(self, text="crew task done"):
        self.raw = text
        self.tasks_output = []
        self.token_usage = None


class MockCrew:
    def __init__(self, text="crew task done", raises=None):
        self._text = text
        self._raises = raises

    async def kickoff_async(self, inputs):
        if self._raises:
            raise self._raises
        return MockCrewResult(self._text)


@pytest.mark.asyncio
async def test_crewai_adapter_string_input_coercion():
    """CrewAIAdapter.run() accepts plain strings — coerces to AgentInput."""
    with patch("checkagent.adapters.crewai._ensure_crewai"):
        from checkagent.adapters.crewai import CrewAIAdapter
        adapter = CrewAIAdapter(MockCrew("task complete"))
        result = await adapter.run("do a task")
    assert result.error is None
    assert isinstance(result, AgentRun)


@pytest.mark.asyncio
async def test_crewai_adapter_final_output_is_raw():
    """CrewAIAdapter.final_output = result.raw — correct string extraction."""
    with patch("checkagent.adapters.crewai._ensure_crewai"):
        from checkagent.adapters.crewai import CrewAIAdapter
        adapter = CrewAIAdapter(MockCrew("task complete"))
        result = await adapter.run("do a task")
    # CrewAI correctly sets final_output = result.raw (string)
    assert result.final_output == "task complete"


@pytest.mark.asyncio
async def test_crewai_adapter_error_handling():
    """CrewAIAdapter.run() captures exceptions in AgentRun.error."""
    with patch("checkagent.adapters.crewai._ensure_crewai"):
        from checkagent.adapters.crewai import CrewAIAdapter
        adapter = CrewAIAdapter(MockCrew(raises=ValueError("crew failed")))
        result = await adapter.run("test")
    assert result.error is not None
    assert "crew failed" in result.error


def test_f064_crewai_not_declared_as_dependency():
    """F-064: crewai package is not in checkagent's declared dependencies."""
    import importlib.metadata
    d = importlib.metadata.distribution("checkagent")
    reqs = d.metadata.get_all("Requires-Dist") or []
    base_deps = [r for r in reqs if "extra ==" not in r]
    crewai_in_base = any("crewai" in r.lower() for r in base_deps)
    assert not crewai_in_base, "F-064 may be fixed: crewai is now a base dep"


def test_f063_crewai_adapter_at_top_level():
    """F-063 FIXED: CrewAIAdapter now importable from top-level checkagent."""
    import checkagent
    assert hasattr(checkagent, "CrewAIAdapter"), "CrewAIAdapter should be at top-level"


# ---------------------------------------------------------------------------
# PydanticAIAdapter: basic functionality (F-063, F-064)
# ---------------------------------------------------------------------------


class MockPydanticAIResult:
    def __init__(self, text="pydantic ai result"):
        self.data = text
        self.output = None

    def all_messages(self):
        return []


class MockPydanticAgent:
    def __init__(self, text="pydantic ai result", raises=None):
        self._text = text
        self._raises = raises

    async def run(self, query):
        if self._raises:
            raise self._raises
        return MockPydanticAIResult(self._text)


@pytest.mark.asyncio
async def test_pydantic_ai_adapter_string_input_coercion():
    """PydanticAIAdapter.run() accepts plain strings."""
    with patch("checkagent.adapters.pydantic_ai._ensure_pydantic_ai"):
        from checkagent.adapters.pydantic_ai import PydanticAIAdapter
        adapter = PydanticAIAdapter(MockPydanticAgent("result text"))
        result = await adapter.run("test input")
    assert result.error is None
    assert isinstance(result, AgentRun)


@pytest.mark.asyncio
async def test_pydantic_ai_adapter_final_output_from_data():
    """PydanticAIAdapter.final_output = result.data."""
    with patch("checkagent.adapters.pydantic_ai._ensure_pydantic_ai"):
        from checkagent.adapters.pydantic_ai import PydanticAIAdapter
        adapter = PydanticAIAdapter(MockPydanticAgent("structured output"))
        result = await adapter.run("test")
    assert result.final_output == "structured output"


@pytest.mark.asyncio
async def test_pydantic_ai_adapter_error_handling():
    """PydanticAIAdapter.run() captures exceptions in AgentRun.error."""
    with patch("checkagent.adapters.pydantic_ai._ensure_pydantic_ai"):
        from checkagent.adapters.pydantic_ai import PydanticAIAdapter
        adapter = PydanticAIAdapter(MockPydanticAgent(raises=RuntimeError("model offline")))
        result = await adapter.run("test")
    assert result.error is not None
    assert "model offline" in result.error


def test_f064_pydantic_ai_not_declared_as_dependency():
    """F-064: pydantic-ai package is not in checkagent's declared dependencies."""
    import importlib.metadata
    d = importlib.metadata.distribution("checkagent")
    reqs = d.metadata.get_all("Requires-Dist") or []
    base_deps = [r for r in reqs if "extra ==" not in r]
    pai_in_base = any("pydantic-ai" in r.lower() or "pydantic_ai" in r.lower() for r in base_deps)
    assert not pai_in_base, "F-064 may be fixed: pydantic-ai is now a base dep"


def test_f063_pydantic_ai_adapter_at_top_level():
    """F-063 FIXED: PydanticAIAdapter now importable from top-level checkagent."""
    import checkagent
    assert hasattr(checkagent, "PydanticAIAdapter"), "PydanticAIAdapter should be at top-level"


# ---------------------------------------------------------------------------
# JUnit XML module (new in this release)
# ---------------------------------------------------------------------------


def test_junit_xml_basic_render():
    """render_junit_xml produces valid XML with correct structure."""
    from checkagent.ci.junit_xml import JUnitTestSuite, JUnitTestCase, render_junit_xml
    suite = JUnitTestSuite(
        name="mysuite",
        test_cases=[
            JUnitTestCase(name="test_pass", classname="mymodule", time_s=1.2),
            JUnitTestCase(name="test_fail", classname="mymodule",
                          failure_message="assert 1 == 2"),
            JUnitTestCase(name="test_skip", classname="mymodule",
                          skipped_message="not ready"),
        ]
    )
    xml = render_junit_xml([suite])
    # Must be valid XML
    root = ET.fromstring(xml.split("?>", 1)[-1].strip())
    assert root.tag == "testsuites"
    assert root.get("tests") == "3"
    assert root.get("failures") == "1"


def test_junit_xml_suite_time_aggregation():
    """JUnitTestSuite.time_s sums individual test case times."""
    from checkagent.ci.junit_xml import JUnitTestSuite, JUnitTestCase
    suite = JUnitTestSuite(
        name="t",
        test_cases=[
            JUnitTestCase(name="a", classname="m", time_s=1.5),
            JUnitTestCase(name="b", classname="m", time_s=2.5),
        ]
    )
    assert suite.time_s == pytest.approx(4.0)


def test_junit_xml_from_run_summary_synthetic():
    """from_run_summary creates test cases from RunSummary when no details given."""
    from checkagent.ci.junit_xml import from_run_summary, render_junit_xml
    from checkagent.ci.reporter import RunSummary
    summary = RunSummary(total=5, passed=3, failed=1, skipped=1, errors=0, duration_s=2.0)
    suite = from_run_summary(summary)
    assert suite.tests == 5
    assert suite.failures == 1
    assert suite.skipped == 1
    # Can render without error
    xml = render_junit_xml([suite])
    assert "testsuites" in xml


def test_junit_xml_from_run_summary_with_details():
    """from_run_summary with test_details produces named test cases."""
    from checkagent.ci.junit_xml import from_run_summary
    from checkagent.ci.reporter import RunSummary
    summary = RunSummary(total=2, passed=1, failed=1, skipped=0, errors=0, duration_s=1.0)
    details = [
        {"name": "test_alpha", "classname": "mod.tests", "status": "passed", "time_s": "0.5"},
        {"name": "test_beta", "classname": "mod.tests", "status": "failed",
         "message": "assert False", "text": "long traceback here"},
    ]
    suite = from_run_summary(summary, test_details=details)
    assert suite.tests == 2
    names = [tc.name for tc in suite.test_cases]
    assert "test_alpha" in names
    assert "test_beta" in names
    failed = next(tc for tc in suite.test_cases if tc.name == "test_beta")
    assert failed.failure_message == "assert False"
    assert failed.failure_text == "long traceback here"


def test_junit_xml_from_quality_gate_report():
    """from_quality_gate_report maps gate verdicts to JUnit test cases."""
    from checkagent.ci.junit_xml import from_quality_gate_report, render_junit_xml
    from checkagent.ci.quality_gate import (
        QualityGateReport, GateResult, GateVerdict
    )
    results = [
        GateResult(metric="accuracy", actual=0.85, threshold=0.90,
                   verdict=GateVerdict.BLOCKED, direction="min",
                   message="below threshold"),
        GateResult(metric="latency", actual=120.0, threshold=200.0,
                   verdict=GateVerdict.PASSED, direction="max"),
        GateResult(metric="missing", actual=None, threshold=0.5,
                   verdict=GateVerdict.SKIPPED, direction="min"),
    ]
    report = QualityGateReport(results=results)
    suite = from_quality_gate_report(report)
    assert suite.tests == 3
    assert suite.failures == 1
    assert suite.skipped == 1
    # Blocked gate → failure
    blocked = next(tc for tc in suite.test_cases if "accuracy" in tc.name)
    assert blocked.is_failure
    assert blocked.failure_message == "below threshold"
    # Passed gate → no failure
    passed = next(tc for tc in suite.test_cases if "latency" in tc.name)
    assert passed.is_passed
    # Skipped gate → skipped
    skipped = next(tc for tc in suite.test_cases if "missing" in tc.name)
    assert skipped.is_skipped


def test_junit_xml_properties_on_gate_test_case():
    """from_quality_gate_report attaches actual/threshold as JUnit properties."""
    from checkagent.ci.junit_xml import from_quality_gate_report
    from checkagent.ci.quality_gate import QualityGateReport, GateResult, GateVerdict
    results = [
        GateResult(metric="accuracy", actual=0.85, threshold=0.90,
                   verdict=GateVerdict.BLOCKED, direction="min"),
    ]
    report = QualityGateReport(results=results)
    suite = from_quality_gate_report(report)
    tc = suite.test_cases[0]
    prop_names = {p.name for p in tc.properties}
    assert "actual" in prop_names
    assert "threshold" in prop_names
    assert "direction" in prop_names


def test_f065_junit_xml_not_at_top_level_checkagent():
    """F-065: JUnit XML classes not exported from top-level checkagent namespace."""
    import checkagent
    assert not hasattr(checkagent, "render_junit_xml"), (
        "F-065 may be fixed: render_junit_xml now at top-level"
    )
    assert not hasattr(checkagent, "JUnitTestSuite"), (
        "F-065 may be fixed: JUnitTestSuite now at top-level"
    )


def test_junit_xml_accessible_from_checkagent_ci():
    """JUnit XML IS accessible from checkagent.ci namespace."""
    from checkagent.ci import (
        render_junit_xml,
        from_run_summary,
        from_quality_gate_report,
        JUnitTestSuite,
        JUnitTestCase,
        JUnitProperty,
    )
    assert callable(render_junit_xml)
    assert callable(from_run_summary)
    assert callable(from_quality_gate_report)


def test_junit_xml_render_multiple_suites():
    """render_junit_xml aggregates stats across multiple suites correctly."""
    from checkagent.ci.junit_xml import JUnitTestSuite, JUnitTestCase, render_junit_xml
    s1 = JUnitTestSuite(name="suite1", test_cases=[
        JUnitTestCase(name="a", classname="m"),
        JUnitTestCase(name="b", classname="m", failure_message="fail"),
    ])
    s2 = JUnitTestSuite(name="suite2", test_cases=[
        JUnitTestCase(name="c", classname="m"),
    ])
    xml = render_junit_xml([s1, s2])
    root = ET.fromstring(xml.split("?>", 1)[-1].strip())
    assert root.get("tests") == "3"
    assert root.get("failures") == "1"


# ---------------------------------------------------------------------------
# F-061 still broken: OpenAIAgentsAdapter local 'agents/' conflict
# ---------------------------------------------------------------------------


def test_f061_openai_agents_adapter_still_broken():
    """F-061: OpenAIAgentsAdapter still imports from 'agents' package name.

    Any project with a local agents/ directory will get ImportError at run() time.
    """
    import checkagent.adapters.openai_agents as oa
    import inspect
    src = inspect.getsource(oa)
    # Still uses 'from agents import Runner' — not 'from openai_agents import Runner'
    assert "from agents import Runner" in src, (
        "F-061: import path changed — verify if local agents/ conflict is resolved"
    )


# ---------------------------------------------------------------------------
# Previously broken, still verifying open status
# ---------------------------------------------------------------------------


def test_f042_block_unmatched_false_fixed():
    """F-042 FIXED: ReplayEngine(block_unmatched=False) returns None for unmatched."""
    from checkagent.replay import ReplayEngine, MatchStrategy
    from checkagent.replay.cassette import Cassette, Interaction
    from checkagent.replay.recorder import RecordedRequest, RecordedResponse
    from datetime import datetime, timezone

    cassette = Cassette()
    interaction = Interaction(
        id="t1",
        request=RecordedRequest(kind="llm", method="complete", body={"text": "hi"}),
        response=RecordedResponse(status="ok", body={"text": "hello"}, duration_ms=5.0),
        recorded_at=datetime.now(timezone.utc),
        sequence=0,
    )
    cassette.interactions.append(interaction)
    engine = ReplayEngine(cassette, strategy=MatchStrategy.EXACT, block_unmatched=False)
    result = engine.match(RecordedRequest(kind="llm", method="complete", body={"text": "different"}))
    assert result is None, "F-042 FIXED: block_unmatched=False returns None for unmatched"


def test_f038_agent_run_string_input_fixed():
    """F-038 FIXED: AgentRun(input='string') now coerces string to AgentInput."""
    run = AgentRun(input="plain string", final_output="result")
    assert run.input.query == "plain string"


def test_f052_judge_verdicts_key_collision_fixed():
    """F-052 FIXED: multi_judge_evaluate keys judge_verdicts by 'rubric:model' now."""
    async def _inner():
        from checkagent.judge import multi_judge_evaluate, RubricJudge, Rubric, Criterion
        rubric = Rubric(
            name="shared_rubric",
            criteria=[Criterion(name="clarity", description="Is it clear?", weight=1.0)],
        )
        resp = json.dumps({
            "scores": [{"criterion": "clarity", "value": 4, "reasoning": "good"}],
            "overall_reasoning": "ok",
        })
        async def llm(system, user): return resp
        j1 = RubricJudge(rubric=rubric, llm=llm, model_name="model-a")
        j2 = RubricJudge(rubric=rubric, llm=llm, model_name="model-b")
        run = make_run()
        verdict = await multi_judge_evaluate([j1, j2], run)
        # F-052 FIXED: key is now 'rubric_judge:{rubric}:{model}' — 2 separate entries
        return len(verdict.judge_verdicts)

    count = asyncio.run(_inner())
    assert count == 2, (
        f"F-052 FIXED: Expected 2 (one per judge with model key), got {count}"
    )
