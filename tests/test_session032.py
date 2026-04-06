"""Session-032: PydanticAI real agent integration tests.

Tests CheckAgent's PydanticAIAdapter against real PydanticAI agents
using PydanticAI's built-in TestModel (no API key needed).

Findings:
- F-085: Step.input_text is always '' for all PydanticAI steps (output_text captures content)
- F-086: PydanticAIAdapter not exported from top-level checkagent (same pattern as F-057/F-063)
- PydanticAIAdapter correctly handles result.output (1.77.0) via getattr fallback
- Structured output (Pydantic model) flows through final_output as the model instance
- Tool-using agents: 4 steps captured; tool calls not visible as ToolCallRecord (internal to PydanticAI)
"""
import pytest
from agents.pydantic_ai_agent import (
    WeatherResult,
    make_error_agent,
    make_qa_agent,
    make_structured_agent,
    make_weather_agent,
)
from checkagent.adapters.pydantic_ai import PydanticAIAdapter
from checkagent import assert_output_matches, assert_output_schema


# ---------------------------------------------------------------------------
# Basic run
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_basic_run():
    """Adapter returns a successful AgentRun with the right final_output."""
    adapter = PydanticAIAdapter(make_qa_agent("Paris is the capital of France."))
    result = await adapter.run("What is the capital of France?")

    assert result.succeeded
    assert result.error is None
    assert result.final_output == "Paris is the capital of France."


@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_string_input_coercion():
    """Passing a plain string to run() works (same as AgentInput(query=...))."""
    adapter = PydanticAIAdapter(make_qa_agent("42"))
    result = await adapter.run("What is 6 times 7?")
    assert result.succeeded
    assert result.final_output == "42"


@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_agent_input():
    """AgentInput is accepted as run() argument."""
    from checkagent import AgentInput

    adapter = PydanticAIAdapter(make_qa_agent("green"))
    result = await adapter.run(AgentInput(query="What color is grass?", context={"domain": "nature"}))
    assert result.succeeded
    assert result.final_output == "green"


# ---------------------------------------------------------------------------
# Duration and tokens
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_duration_captured():
    """duration_ms is a positive float."""
    adapter = PydanticAIAdapter(make_qa_agent("ok"))
    result = await adapter.run("ping")
    assert result.duration_ms > 0


@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_tokens_extracted():
    """Token counts are extracted from TestModel usage info (non-zero)."""
    adapter = PydanticAIAdapter(make_qa_agent("hello"))
    result = await adapter.run("hi")
    # TestModel tracks usage — should have non-None prompt tokens
    assert result.total_prompt_tokens is not None
    assert result.total_prompt_tokens > 0
    assert result.total_completion_tokens is not None
    assert result.total_completion_tokens > 0


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_steps_captured():
    """Steps are captured: 2 steps for a simple Q&A (request + response)."""
    adapter = PydanticAIAdapter(make_qa_agent("Berlin"))
    result = await adapter.run("Capital of Germany?")
    assert len(result.steps) == 2
    # steps have metadata with 'kind'
    kinds = [s.metadata.get("kind") for s in result.steps]
    assert "request" in kinds
    assert "response" in kinds


@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_step_input_text_empty():
    """F-085: Step.input_text is always '' — output_text carries the content instead."""
    adapter = PydanticAIAdapter(make_qa_agent("yes"))
    result = await adapter.run("Is this a test?")
    for step in result.steps:
        # input_text is always empty — this is a known gap
        assert step.input_text == "", (
            f"F-085: expected empty input_text but got {step.input_text!r} "
            f"for step kind={step.metadata.get('kind')}"
        )


@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_step_output_text_has_content():
    """output_text carries the meaningful content (request prompt or response text)."""
    adapter = PydanticAIAdapter(make_qa_agent("response text here"))
    result = await adapter.run("a question")
    # At least one step should have non-empty output_text
    non_empty = [s for s in result.steps if s.output_text]
    assert len(non_empty) >= 1


# ---------------------------------------------------------------------------
# Tool-using agent
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_tool_agent_succeeds():
    """Agent with an internal tool runs successfully."""
    adapter = PydanticAIAdapter(make_weather_agent())
    result = await adapter.run("What is the weather in Paris?")
    assert result.succeeded
    assert result.error is None
    assert "Weather retrieved successfully" in str(result.final_output)


@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_tool_agent_more_steps():
    """Tool-using agents produce more steps (request + tool call + tool result + final response)."""
    adapter = PydanticAIAdapter(make_weather_agent())
    result = await adapter.run("Weather in Tokyo?")
    # 4 steps: initial request, tool call response, tool result request, final response
    assert len(result.steps) == 4


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_structured_output_type():
    """Structured output agents return a Pydantic model instance as final_output."""
    adapter = PydanticAIAdapter(make_structured_agent())
    result = await adapter.run("Weather?")
    assert result.succeeded
    assert isinstance(result.final_output, WeatherResult)


@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_structured_output_fields():
    """Fields of the structured output are correct."""
    adapter = PydanticAIAdapter(make_structured_agent())
    result = await adapter.run("Weather in Paris?")
    out = result.final_output
    assert isinstance(out, WeatherResult)
    assert out.city == "Paris"
    assert out.temperature == 25.0
    assert out.condition == "Sunny"


@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_assert_output_schema_on_dict():
    """assert_output_schema works when final_output is a Pydantic model dumped to dict."""
    adapter = PydanticAIAdapter(make_structured_agent())
    result = await adapter.run("Weather?")
    # Dump to dict for schema assertion
    assert_output_schema(result.final_output.model_dump(), WeatherResult)


@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_assert_output_matches():
    """assert_output_matches works on structured output dict fields."""
    adapter = PydanticAIAdapter(make_structured_agent())
    result = await adapter.run("Weather?")
    out_dict = result.final_output.model_dump()
    assert_output_matches(out_dict, {"city": "Paris", "temperature": 25.0})


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_error_captured():
    """Exceptions from the agent are captured in AgentRun.error; succeeded=False."""
    adapter = PydanticAIAdapter(make_error_agent())
    result = await adapter.run("anything")
    assert not result.succeeded
    assert result.error is not None
    assert "RuntimeError" in result.error


@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_error_no_exception_raised():
    """Adapter absorbs agent exceptions — run() itself does NOT raise."""
    adapter = PydanticAIAdapter(make_error_agent())
    try:
        result = await adapter.run("trigger error")
        assert not result.succeeded
    except Exception as e:
        pytest.fail(f"Adapter should not raise; got {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Top-level export check (F-086)
# ---------------------------------------------------------------------------

def test_pydantic_ai_adapter_not_at_top_level():
    """F-086: PydanticAIAdapter is not importable from top-level checkagent.

    Must be imported from checkagent.adapters.pydantic_ai instead.
    This is the same pattern as F-057 (LangChain) and F-063 (other adapters).
    """
    try:
        from checkagent import PydanticAIAdapter as _  # noqa: F401
        pytest.fail("F-086 appears fixed — PydanticAIAdapter now at top-level checkagent")
    except ImportError:
        pass  # expected — F-086 still open


def test_pydantic_ai_adapter_in_adapters_init():
    """PydanticAIAdapter IS re-exported from checkagent.adapters (partial improvement).

    It's not at the top-level checkagent namespace (F-086) but it is importable
    from checkagent.adapters — one level better than other adapters.
    """
    from checkagent.adapters import PydanticAIAdapter as _  # noqa: F401


@pytest.mark.asyncio
async def test_pydantic_ai_deprecated_token_attrs():
    """F-087: PydanticAIAdapter uses deprecated request_tokens/response_tokens attributes.

    PydanticAI 1.77.0 renamed these to input_tokens/output_tokens.
    The adapter still reads the old names, triggering DeprecationWarning on every run.
    This will break silently when PydanticAI removes the deprecated attrs.
    """
    import warnings
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    model = TestModel(custom_output_text="test")
    agent = Agent(model=model)
    adapter = PydanticAIAdapter(agent)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        await adapter.run("test")
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]

    messages = [str(d.message) for d in deprecation_warnings]
    token_warnings = [m for m in messages if "tokens" in m.lower()]
    assert len(token_warnings) >= 2, (
        f"F-087: Expected deprecation warnings for request_tokens/response_tokens "
        f"but got: {messages}"
    )


# ---------------------------------------------------------------------------
# Multiple runs (isolation check)
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="mock")
@pytest.mark.asyncio
async def test_pydantic_ai_multiple_runs_isolated():
    """Each adapter.run() call is independent — no state leaks between runs."""
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    responses = iter(["first answer", "second answer"])

    def make_agent():
        resp = next(responses)
        model = TestModel(custom_output_text=resp)
        return Agent(model=model)

    r1 = await PydanticAIAdapter(make_agent()).run("q1")
    r2 = await PydanticAIAdapter(make_agent()).run("q2")

    assert r1.final_output == "first answer"
    assert r2.final_output == "second answer"
