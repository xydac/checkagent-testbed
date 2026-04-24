"""
Session 044 tests — v0.3.0 (no upstream changes since session-043)

Key areas:
- Stale tests from session-041/042 converted to xfail (8 tests, done in those files)
- PydanticAI structured output via wrap() — final_output is Pydantic model, not str
- assert_output_schema / assert_json_schema with Pydantic model final_output
- CrewAI adapter: importable, lazy import raises ImportError at instantiation
- wrap() TypeError message for unrecognized objects lists all adapters
- --llm-judge error paths (Anthropic + OpenAI) verified manually
"""
import asyncio
import pytest


# ---------------------------------------------------------------------------
# PydanticAI structured output via wrap()
# ---------------------------------------------------------------------------


class TestWrapPydanticAIStructuredOutput:
    """wrap(Agent(output_type=SomeModel)) auto-detects PydanticAIAdapter
    and final_output is the Pydantic model instance, not a str.

    This is intentional and correct — adapters pass through framework output
    types as-is. But users should be aware that final_output is not always str.
    """

    def test_no_output_type_gives_string_final_output(self):
        """Default Agent (no output_type) → final_output is str."""
        pytest.importorskip("pydantic_ai")
        from pydantic_ai import Agent
        from pydantic_ai.models.test import TestModel
        from checkagent import wrap

        agent = Agent(TestModel())
        adapter = wrap(agent)
        result = asyncio.run(adapter.run("plan a trip"))
        assert result.succeeded
        assert isinstance(result.final_output, str)

    def test_output_type_gives_pydantic_model_final_output(self):
        """Agent(output_type=Model) → final_output is Model instance, not str."""
        pytest.importorskip("pydantic_ai")
        from pydantic_ai import Agent
        from pydantic_ai.models.test import TestModel
        from pydantic import BaseModel
        from checkagent import wrap

        class TripPlan(BaseModel):
            destination: str
            days: int

        agent = Agent(TestModel(), output_type=TripPlan)
        adapter = wrap(agent)
        result = asyncio.run(adapter.run("plan a 7-day trip to Tokyo"))
        assert result.succeeded
        assert isinstance(result.final_output, TripPlan), (
            f"Expected TripPlan instance, got {type(result.final_output).__name__}"
        )
        # TestModel gives minimal valid values
        assert isinstance(result.final_output.destination, str)
        assert isinstance(result.final_output.days, int)

    def test_assert_output_schema_works_with_model_instance(self):
        """assert_output_schema validates a Pydantic model instance correctly."""
        pytest.importorskip("pydantic_ai")
        from pydantic_ai import Agent
        from pydantic_ai.models.test import TestModel
        from pydantic import BaseModel
        from checkagent import wrap, assert_output_schema

        class TripPlan(BaseModel):
            destination: str
            days: int

        agent = Agent(TestModel(), output_type=TripPlan)
        adapter = wrap(agent)
        result = asyncio.run(adapter.run("plan a trip"))
        # Should pass — final_output is already a valid TripPlan
        assert_output_schema(result, TripPlan)

    def test_assert_output_schema_fails_with_wrong_schema(self):
        """assert_output_schema raises when final_output doesn't match schema."""
        pytest.importorskip("pydantic_ai")
        from pydantic_ai import Agent
        from pydantic_ai.models.test import TestModel
        from pydantic import BaseModel
        from checkagent import wrap, assert_output_schema
        from checkagent.eval.assertions import StructuredAssertionError

        class TripPlan(BaseModel):
            destination: str
            days: int

        class WrongSchema(BaseModel):
            city: str
            nights: int

        agent = Agent(TestModel(), output_type=TripPlan)
        adapter = wrap(agent)
        result = asyncio.run(adapter.run("plan a trip"))
        # Should fail — TripPlan doesn't have city/nights fields
        with pytest.raises(StructuredAssertionError, match="city"):
            assert_output_schema(result, WrongSchema)

    def test_assert_json_schema_works_with_model_instance_as_data(self):
        """assert_json_schema accepts Pydantic model instance as the data argument."""
        pytest.importorskip("pydantic_ai")
        from pydantic_ai import Agent
        from pydantic_ai.models.test import TestModel
        from pydantic import BaseModel
        from checkagent import wrap, assert_json_schema

        class TripPlan(BaseModel):
            destination: str
            days: int

        agent = Agent(TestModel(), output_type=TripPlan)
        adapter = wrap(agent)
        result = asyncio.run(adapter.run("plan a trip"))

        json_schema = {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "days": {"type": "integer"},
            },
            "required": ["destination", "days"],
        }
        # Pass final_output directly (not the AgentRun) — Pydantic instances accepted
        assert_json_schema(result.final_output, json_schema)


# ---------------------------------------------------------------------------
# CrewAI adapter lazy import behavior
# ---------------------------------------------------------------------------


class TestCrewAIAdapterLazyImport:
    """CrewAIAdapter imports cleanly but raises ImportError at instantiation
    when crewai is not installed. This is the correct lazy-import pattern.
    """

    def test_crewai_adapter_importable_without_crewai(self):
        """CrewAIAdapter class can be imported even without crewai installed."""
        from checkagent.adapters.crewai import CrewAIAdapter
        assert CrewAIAdapter is not None

    def test_crewai_adapter_raises_on_instantiation_without_crewai(self):
        """CrewAIAdapter raises ImportError at instantiation when crewai missing."""
        try:
            import crewai  # noqa: F401
            pytest.skip("crewai is installed — lazy import test not applicable")
        except ImportError:
            pass

        from checkagent.adapters.crewai import CrewAIAdapter

        class FakeCrew:
            def kickoff(self, inputs=None):
                return type("Result", (), {"raw": "done"})()

        with pytest.raises(ImportError, match="crewai"):
            CrewAIAdapter(FakeCrew())

    def test_wrap_lists_crewai_adapter_in_error(self):
        """wrap() TypeError for unrecognized objects lists CrewAIAdapter."""
        from checkagent import wrap

        class SomeRandomObject:
            pass

        with pytest.raises(TypeError) as exc_info:
            wrap(SomeRandomObject())

        error_msg = str(exc_info.value)
        assert "CrewAIAdapter" in error_msg, (
            "wrap() TypeError should list CrewAIAdapter as an option"
        )
        assert "checkagent.adapters.crewai" in error_msg


# ---------------------------------------------------------------------------
# wrap() TypeError message completeness
# ---------------------------------------------------------------------------


class TestWrapTypeErrorMessageCompleteness:
    """wrap() raises TypeError for non-callable, non-framework objects.
    The error message should list all available framework adapters.
    """

    def test_error_lists_all_framework_adapters(self):
        """TypeError message includes all 4 framework adapters."""
        from checkagent import wrap

        class Unrecognized:
            pass

        with pytest.raises(TypeError) as exc_info:
            wrap(Unrecognized())

        error_msg = str(exc_info.value)
        expected_adapters = [
            "PydanticAIAdapter",
            "LangChainAdapter",
            "CrewAIAdapter",
            "OpenAIAgentsAdapter",
        ]
        for adapter_name in expected_adapters:
            assert adapter_name in error_msg, (
                f"wrap() TypeError missing {adapter_name} in help message"
            )

    def test_error_includes_lambda_workaround(self):
        """TypeError message suggests lambda workaround."""
        from checkagent import wrap

        class Unrecognized:
            pass

        with pytest.raises(TypeError) as exc_info:
            wrap(Unrecognized())

        assert "lambda" in str(exc_info.value).lower(), (
            "wrap() TypeError should mention lambda as workaround"
        )

    def test_plain_callable_still_works(self):
        """Plain callables still wrap without error."""
        from checkagent import wrap

        def my_agent(query: str) -> str:
            return f"response to: {query}"

        adapter = wrap(my_agent)
        result = asyncio.run(adapter.run("hello"))
        assert result.succeeded
        assert "response to: hello" in result.final_output

    def test_pydantic_ai_auto_detected(self):
        """wrap() auto-detects PydanticAI Agent without TypeError."""
        pytest.importorskip("pydantic_ai")
        from pydantic_ai import Agent
        from pydantic_ai.models.test import TestModel
        from checkagent import wrap
        from checkagent.adapters.pydantic_ai import PydanticAIAdapter

        agent = Agent(TestModel())
        adapter = wrap(agent)
        assert isinstance(adapter, PydanticAIAdapter)

    def test_langchain_runnable_auto_detected(self):
        """wrap() auto-detects LangChain Runnable without TypeError."""
        pytest.importorskip("langchain_core")
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.language_models.fake_chat_models import FakeChatModel
        from checkagent import wrap
        from checkagent.adapters.langchain import LangChainAdapter

        chain = (
            ChatPromptTemplate.from_template("{input}")
            | FakeChatModel(responses=["ok"])
            | StrOutputParser()
        )
        adapter = wrap(chain)
        assert isinstance(adapter, LangChainAdapter)
