"""PydanticAI agents for CheckAgent integration testing.

Uses PydanticAI's TestModel so no real API key is needed.
"""
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel


class WeatherResult(BaseModel):
    city: str
    temperature: float
    condition: str


def make_qa_agent(answer: str = "42") -> Agent:
    """A simple Q&A agent that returns a fixed string answer."""
    model = TestModel(custom_output_text=answer)
    return Agent(model=model, system_prompt="You are a helpful assistant.")


def make_weather_agent() -> Agent:
    """A weather agent that uses a tool internally."""
    model = TestModel(call_tools="all", custom_output_text="Weather retrieved successfully.")
    agent: Agent = Agent(model=model, system_prompt="You are a weather assistant.")

    @agent.tool_plain
    def get_weather(city: str) -> str:
        """Get the weather for a city."""
        return f"Sunny, 25°C in {city}"

    return agent


def make_structured_agent() -> Agent:
    """An agent that returns structured (Pydantic model) output."""
    model = TestModel(
        custom_output_args={"city": "Paris", "temperature": 25.0, "condition": "Sunny"}
    )
    return Agent(model=model, output_type=WeatherResult)


def make_error_agent() -> Agent:
    """An agent wired to raise an exception on every invocation."""
    from pydantic_ai.models.test import TestModel as _TM

    class _ErrorModel(_TM):
        async def request(self, *args, **kwargs):  # type: ignore[override]
            raise RuntimeError("Simulated agent failure")

    return Agent(model=_ErrorModel())
