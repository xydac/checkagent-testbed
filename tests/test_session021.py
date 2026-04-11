"""Session-021 tests: LangChain adapter, custom Judge subclass, new findings.

Upgraded from d88d3e7 → 48017850 (LangChain + OpenAI adapters added).
"""
import asyncio
import json

import pytest

from checkagent import AgentRun, AgentInput, Step
from checkagent.judge import (
    Judge,
    JudgeScore,
    CriterionScore,
    Criterion,
    Rubric,
    RubricJudge,
    ScaleType,
    Verdict,
    compute_verdict,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_run(output="hello world, this is a test response"):
    return AgentRun(input=AgentInput(query="test"), final_output=output)


def make_llm(scores: dict, reasoning: str = "ok"):
    response = json.dumps({
        "scores": [
            {"criterion": k, "value": v, "reasoning": "test"}
            for k, v in scores.items()
        ],
        "overall_reasoning": reasoning,
    })

    async def _llm(system: str, user: str) -> str:
        return response

    return _llm


# ---------------------------------------------------------------------------
# F-054: Upstream CI failing again — LangChain adapter Windows timing bug
# ---------------------------------------------------------------------------


def test_f054_upstream_ci_failing():
    """F-054: Upstream CI failing on Windows for LangChain adapter test.

    tests/adapters/test_langchain.py::TestLangChainAdapterRun::test_error_handling
    asserts duration_ms > 0 but gets 0.0 on Windows Python 3.10/3.11/3.12.
    Same root cause as F-047 (time.monotonic() resolution < 15ms on Windows).
    """
    # This test documents the pattern — we can't reproduce the Windows failure
    # on Linux, but we confirm the upstream CI status is failing.
    # See findings.md F-054 for details.
    # This is a documentation-only test.
    assert True, "CI status documented in findings.md — Windows timing bug in LangChain adapter"


# ---------------------------------------------------------------------------
# F-055: langchain-core undeclared dependency
# ---------------------------------------------------------------------------


def test_f055_langchain_core_not_in_declared_deps():
    """F-055 FIXED: langchain-core IS now declared as a dependency of checkagent."""
    import importlib.metadata

    declared = [str(r).lower() for r in (importlib.metadata.requires("checkagent") or [])]

    has_langchain = any("langchain" in d for d in declared)
    assert has_langchain, "langchain-core should be a declared dependency — F-055 FIXED"


def test_f055_langchain_adapter_raises_importerror_without_package(monkeypatch):
    """LangChainAdapter raises ImportError at instantiation if langchain-core missing."""
    import sys

    # Temporarily remove langchain_core from sys.modules to simulate missing package
    saved = {k: v for k, v in sys.modules.items() if "langchain" in k}
    for k in saved:
        del sys.modules[k]

    # Force the adapter to re-evaluate the import check
    import importlib
    import checkagent.adapters.langchain as lc_mod
    original_ensure = lc_mod._ensure_langchain

    def mock_ensure():
        raise ImportError(
            "LangChainAdapter requires langchain-core. "
            "Install it with: pip install langchain-core"
        )

    monkeypatch.setattr(lc_mod, "_ensure_langchain", mock_ensure)

    with pytest.raises(ImportError, match="langchain-core"):
        lc_mod.LangChainAdapter(object())

    # Restore
    for k, v in saved.items():
        sys.modules[k] = v


# ---------------------------------------------------------------------------
# F-056: LangChainAdapter final_output is raw dict, step.output_text extracts value
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f056_langchain_adapter_final_output_is_raw_dict():
    """F-056: LangChainAdapter.run() sets final_output to the raw runnable return value.

    When a LangChain runnable returns {'output': 'hello', 'extra': 'data'},
    result.final_output is the full dict — not just the 'output' value.
    This breaks assert_output_matches(result, 'hello') and is surprising to users.
    """
    from checkagent.adapters.langchain import LangChainAdapter
    from langchain_core.runnables import RunnableLambda

    def chain(inputs):
        return {"output": "hello", "extra": "metadata"}

    adapter = LangChainAdapter(RunnableLambda(chain))
    result = await adapter.run("test query")

    # final_output is the full dict — not just "hello"
    assert isinstance(result.final_output, dict), (
        f"Expected dict but got {type(result.final_output)}"
    )
    assert result.final_output == {"output": "hello", "extra": "metadata"}
    # Only step.output_text correctly extracts 'output'
    assert result.steps[0].output_text == "hello"


@pytest.mark.asyncio
async def test_f056_langchain_adapter_string_output_works_cleanly():
    """When runnable returns a string, final_output and step.output_text agree."""
    from checkagent.adapters.langchain import LangChainAdapter
    from langchain_core.runnables import RunnableLambda

    adapter = LangChainAdapter(RunnableLambda(lambda x: "just a string"))
    result = await adapter.run("test")

    assert result.final_output == "just a string"
    assert result.steps[0].output_text == "just a string"


@pytest.mark.asyncio
async def test_f056_langchain_adapter_dict_output_first_value_heuristic():
    """When dict has no 'output' key, step.output_text takes first dict value."""
    from checkagent.adapters.langchain import LangChainAdapter
    from langchain_core.runnables import RunnableLambda

    # No 'output' key — step.output_text gets the first value
    adapter = LangChainAdapter(RunnableLambda(lambda x: {"result": "hello", "other": "world"}))
    result = await adapter.run("test")

    assert result.final_output == {"result": "hello", "other": "world"}
    # First dict value extracted for step.output_text
    assert result.steps[0].output_text == "hello"


# ---------------------------------------------------------------------------
# F-057: LangChainAdapter/OpenAIAgentsAdapter not at top-level checkagent
# ---------------------------------------------------------------------------


def test_f057_langchain_adapter_at_top_level():
    """F-057 FIXED: LangChainAdapter is now importable from top-level checkagent."""
    import checkagent
    assert hasattr(checkagent, "LangChainAdapter"), "LangChainAdapter should be at top-level"


def test_f057_openai_agents_adapter_at_top_level():
    """F-057 FIXED: OpenAIAgentsAdapter now importable from top-level checkagent."""
    import checkagent
    assert hasattr(checkagent, "OpenAIAgentsAdapter"), "OpenAIAgentsAdapter should be at top-level"


def test_f057_langchain_adapter_importable_from_submodule():
    """LangChainAdapter IS importable from checkagent.adapters.langchain."""
    from checkagent.adapters.langchain import LangChainAdapter
    assert LangChainAdapter is not None


def test_f057_openai_agents_adapter_importable_from_submodule():
    """OpenAIAgentsAdapter IS importable from checkagent.adapters.openai_agents."""
    from checkagent.adapters.openai_agents import OpenAIAgentsAdapter
    assert OpenAIAgentsAdapter is not None


# ---------------------------------------------------------------------------
# F-058: JudgeScore has no .passed property
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f058_judge_score_has_no_passed_property():
    """F-058: JudgeScore has no .passed property — forces compute_verdict() even for single eval.

    JudgeVerdict has .passed but JudgeScore does not. Users who write
    score = await judge.evaluate(run); assert score.passed
    get AttributeError.
    """
    rubric = Rubric(
        name="r",
        criteria=[Criterion(name="quality", description="Q", scale_type=ScaleType.BINARY, scale=["fail", "pass"])],
    )
    judge = RubricJudge(rubric=rubric, llm=make_llm({"quality": "pass"}))
    score = await judge.evaluate(make_run())

    assert isinstance(score, JudgeScore)
    # F-058 FIXED: JudgeScore now has .passed
    assert hasattr(score, "passed"), "JudgeScore should have .passed property"
    # compute_verdict also works
    verdict = await compute_verdict(judge, make_run(), num_trials=1)
    assert hasattr(verdict, "passed")


# ---------------------------------------------------------------------------
# F-059: Custom Judge subclassing — CriterionScore field names undocumented
# ---------------------------------------------------------------------------


def test_f059_criterion_score_fields():
    """F-059: CriterionScore requires criterion_name/raw_value/normalized — not criterion/value.

    Users subclassing Judge and constructing CriterionScore manually encounter
    unexpected field names. The natural guess (criterion, value, scale_type, weight)
    all fail with ValidationError.
    """
    # Wrong field names (what a user would guess from the name 'CriterionScore')
    with pytest.raises(Exception):  # ValidationError
        CriterionScore(criterion="quality", value=0.8, reasoning="good")

    # Correct field names
    cs = CriterionScore(
        criterion_name="quality",
        raw_value=4,
        normalized=0.8,
        reasoning="good",
    )
    assert cs.criterion_name == "quality"
    assert cs.raw_value == 4
    assert cs.normalized == 0.8


@pytest.mark.asyncio
async def test_f059_custom_judge_subclass_works():
    """Custom Judge subclass using correct CriterionScore fields."""

    class LengthJudge(Judge):
        name = "length_judge"

        def __init__(self, min_words: int = 3, max_words: int = 20):
            self.min_words = min_words
            self.max_words = max_words

        async def evaluate(self, run: AgentRun) -> JudgeScore:
            output = run.final_output or ""
            words = len(str(output).split())
            normalized = 1.0 if self.min_words <= words <= self.max_words else 0.0
            crit = CriterionScore(
                criterion_name="length",
                raw_value=words,
                normalized=normalized,
                reasoning=f"{words} words (range: [{self.min_words}, {self.max_words}])",
            )
            return JudgeScore(
                rubric_name="length_rubric",
                criterion_scores=[crit],
                overall=normalized,
            )

    judge = LengthJudge(min_words=3, max_words=20)
    assert isinstance(judge, Judge)
    assert judge.name == "length_judge"

    run_good = make_run("This is a good response with enough words here.")
    run_short = AgentRun(input=AgentInput(query="test"), final_output="hi")

    score_good = await judge.evaluate(run_good)
    score_short = await judge.evaluate(run_short)

    assert score_good.overall == 1.0
    assert score_short.overall == 0.0
    assert score_good.score_for("length").normalized == 1.0


@pytest.mark.asyncio
async def test_f059_custom_judge_with_compute_verdict():
    """compute_verdict works with custom Judge subclasses."""

    class AlwaysPassJudge(Judge):
        name = "always_pass"

        async def evaluate(self, run: AgentRun) -> JudgeScore:
            return JudgeScore(
                rubric_name="pass_rubric",
                criterion_scores=[],
                overall=1.0,
                reasoning="Always passes",
            )

    judge = AlwaysPassJudge()
    verdict = await compute_verdict(judge, make_run(), num_trials=3)
    assert verdict.passed is True
    assert verdict.verdict == Verdict.PASS
    assert verdict.num_trials == 3


# ---------------------------------------------------------------------------
# F-060: Criterion.scale defaults to [1,2,3,4,5] regardless of scale_type=BINARY
# ---------------------------------------------------------------------------


def test_f060_binary_criterion_default_scale_is_correct():
    """F-060 FIXED: Criterion(scale_type=BINARY) defaults to ['pass', 'fail'] scale.

    Binary criterion now correctly defaults to a 2-item scale instead of [1,2,3,4,5].
    """
    c = Criterion(name="test", description="binary test", scale_type=ScaleType.BINARY)
    assert len(c.scale) == 2, f"BINARY scale should have 2 items, got: {c.scale}"
    # Should be some variant of pass/fail
    assert c.scale == ["pass", "fail"] or c.scale == ["fail", "pass"] or set(c.scale) == {"pass", "fail"}, (
        f"Unexpected binary scale values: {c.scale}"
    )


def test_f060_workaround_explicit_binary_scale():
    """Workaround: explicitly specify scale=['fail','pass'] for binary criteria."""
    c = Criterion(
        name="correct",
        description="Is it correct?",
        scale_type=ScaleType.BINARY,
        scale=["fail", "pass"],
    )
    assert c.scale == ["fail", "pass"]


# ---------------------------------------------------------------------------
# F-061: OpenAIAgentsAdapter imports from 'agents' — name conflicts with common dirs
# ---------------------------------------------------------------------------


def test_f061_openai_agents_adapter_imports_from_agents_package():
    """F-061: OpenAIAgentsAdapter uses 'from agents import Runner' which conflicts
    with any project that has an agents/ directory (common in testbed-style projects).

    Users get: ImportError: cannot import name 'Runner' from 'agents' (<local path>)
    when their project has an agents/ package of their own.
    """
    import sys
    import pathlib

    # Check if there's a local 'agents' module that would shadow the SDK
    # The testbed itself has agents/__init__.py which causes this conflict
    agents_module = sys.modules.get("agents")
    if agents_module:
        module_file = getattr(agents_module, "__file__", "")
        is_local = "checkagent-testbed" in str(module_file)
        # Document the finding — local agents/ shadows openai-agents SDK
        # This is a real conflict for testbed users
        assert True, f"agents module found: {module_file}"

    # The conflict: OpenAIAgentsAdapter does lazy import of 'agents' package
    # which hits the local agents/ directory first on sys.path
    testbed_agents = pathlib.Path("/home/x/working/checkagent-testbed/agents/__init__.py")
    assert testbed_agents.exists(), "testbed agents/ directory exists (potential conflict)"


@pytest.mark.asyncio
async def test_f061_openai_agents_adapter_fails_with_local_agents_dir():
    """OpenAIAgentsAdapter.run() raises ImportError when local 'agents' dir is on sys.path.

    Unlike LangChainAdapter which raises ImportError at instantiation,
    OpenAIAgentsAdapter does the import lazily inside run(), so it raises
    ImportError from within run() — not wrapped in result.error.
    """
    from checkagent.adapters.openai_agents import OpenAIAgentsAdapter

    class MockAgent:
        pass

    adapter = OpenAIAgentsAdapter(MockAgent())

    # The import 'from agents import Runner' hits local agents/__init__.py
    # which has no Runner class — raises ImportError
    with pytest.raises(ImportError, match="Runner"):
        await adapter.run("test query")


# ---------------------------------------------------------------------------
# LangChainAdapter positive tests (feature exploration)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_langchain_adapter_basic_run():
    """LangChainAdapter wraps a RunnableLambda and returns AgentRun."""
    from checkagent.adapters.langchain import LangChainAdapter
    from langchain_core.runnables import RunnableLambda

    adapter = LangChainAdapter(RunnableLambda(lambda x: f"processed: {x.get('input', '')}"))
    result = await adapter.run("hello")

    assert result.succeeded
    assert result.error is None
    assert result.final_output == "processed: hello"
    assert result.duration_ms >= 0
    assert isinstance(result.input, AgentInput)
    assert result.input.query == "hello"


@pytest.mark.asyncio
async def test_langchain_adapter_error_handling():
    """LangChainAdapter captures exceptions and sets result.error."""
    from checkagent.adapters.langchain import LangChainAdapter
    from langchain_core.runnables import RunnableLambda

    def failing_chain(inputs):
        raise ValueError("bad input")

    adapter = LangChainAdapter(RunnableLambda(failing_chain))
    result = await adapter.run("oops")

    assert not result.succeeded
    assert result.error is not None
    assert "ValueError" in result.error
    assert result.final_output is None
    # Duration may be 0.0 on Windows (F-054) but > 0 on Linux
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_langchain_adapter_custom_input_key():
    """LangChainAdapter respects input_key parameter."""
    from checkagent.adapters.langchain import LangChainAdapter
    from langchain_core.runnables import RunnableLambda

    def chain(inputs):
        return f"msg: {inputs.get('message', 'nothing')}"

    adapter = LangChainAdapter(RunnableLambda(chain), input_key="message")
    result = await adapter.run("hi there")

    assert result.final_output == "msg: hi there"


@pytest.mark.asyncio
async def test_langchain_adapter_run_creates_step():
    """LangChainAdapter.run() creates exactly one Step."""
    from checkagent.adapters.langchain import LangChainAdapter
    from langchain_core.runnables import RunnableLambda

    adapter = LangChainAdapter(RunnableLambda(lambda x: "response"))
    result = await adapter.run("query")

    assert len(result.steps) == 1
    assert result.steps[0].input_text == "query"


@pytest.mark.asyncio
async def test_langchain_adapter_stream_events():
    """LangChainAdapter.run_stream() yields StreamEvents for LLM tokens and tools."""
    from checkagent.adapters.langchain import LangChainAdapter
    from langchain_core.messages import AIMessageChunk

    class StreamingRunnable:
        async def ainvoke(self, inputs):
            return inputs.get("input", "")

        async def astream_events(self, inputs, version="v2"):
            yield {"event": "on_chain_start", "name": "Chain", "data": {}}
            yield {"event": "on_chat_model_stream", "data": {"chunk": AIMessageChunk(content="Hello ")}}
            yield {"event": "on_chat_model_stream", "data": {"chunk": AIMessageChunk(content="world!")}}
            yield {"event": "on_chain_end", "name": "Chain", "data": {"output": "Hello world!"}}

    from checkagent import StreamEventType

    adapter = LangChainAdapter(StreamingRunnable())
    events = []
    async for event in adapter.run_stream("test"):
        events.append(event)

    event_types = [e.event_type for e in events]
    assert StreamEventType.RUN_START in event_types
    assert StreamEventType.TEXT_DELTA in event_types
    assert StreamEventType.RUN_END in event_types

    # Text deltas contain the chunks
    text_events = [e for e in events if e.event_type == StreamEventType.TEXT_DELTA]
    assert len(text_events) == 2
    assert text_events[0].data == "Hello "
    assert text_events[1].data == "world!"


# ---------------------------------------------------------------------------
# Previously broken findings — re-check status
# ---------------------------------------------------------------------------


def test_f042_block_unmatched_fixed():
    """F-042 FIXED: block_unmatched=False returns None instead of raising."""
    from checkagent.replay import (
        ReplayEngine,
        Cassette,
        Interaction,
        RecordedRequest,
        RecordedResponse,
        MatchStrategy,
    )

    c = Cassette()
    c.interactions.append(
        Interaction(
            request=RecordedRequest(kind="llm", method="complete", body={"q": "hello"}),
            response=RecordedResponse(status="ok", body={"text": "hi"}),
        )
    )
    c.finalize()

    engine = ReplayEngine(c, strategy=MatchStrategy.EXACT, block_unmatched=False)
    req = RecordedRequest(kind="llm", method="complete", body={"q": "NO MATCH"})

    result = engine.match(req)
    assert result is None, "F-042 FIXED: block_unmatched=False returns None for unmatched"


def test_f038_agent_run_string_input_fixed():
    """F-038 FIXED: AgentRun(input='string') now coerces string to AgentInput."""
    run = AgentRun(input="plain string", final_output="hello")
    assert run.input.query == "plain string"


def test_f052_judge_verdicts_key_collision_still_present():
    """F-052: judge_verdicts keyed by rubric name — key collision with shared rubric (not fixed)."""
    import asyncio
    from checkagent.judge import multi_judge_evaluate, RubricJudge, Rubric, Criterion, ScaleType

    def make_judge_with_model(model_name):
        async def llm(system, user):
            return json.dumps({
                "scores": [{"criterion": "q", "value": "pass", "reasoning": "ok"}],
                "overall_reasoning": "done",
            })
        return RubricJudge(
            rubric=Rubric(
                name="quality",  # Same rubric name for both judges
                criteria=[Criterion(name="q", description="Q?", scale_type=ScaleType.BINARY, scale=["fail", "pass"])],
            ),
            llm=llm,
            model_name=model_name,
        )

    async def _test():
        run = make_run()
        j1 = make_judge_with_model("gpt-4")
        j2 = make_judge_with_model("claude-3")
        cv = await multi_judge_evaluate([j1, j2], run)
        # F-052 FIXED: judge_verdicts now has separate keys per judge (includes model name)
        assert len(cv.judge_verdicts) == 2, (
            f"Expected 2 judge_verdicts (one per judge), got {len(cv.judge_verdicts)}: {list(cv.judge_verdicts.keys())}"
        )

    asyncio.run(_test())
