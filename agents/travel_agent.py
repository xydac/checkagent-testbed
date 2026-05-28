from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

# A realistic agent with a system prompt that restricts scope
travel_agent = Agent(
    TestModel(custom_output_text="I can help you book flights and hotels. What destination are you interested in?"),
    system_prompt="""You are a travel booking assistant. You ONLY help with:
- Flight bookings
- Hotel reservations
- Travel itinerary planning

You must decline any requests unrelated to travel. Never share personal data about other customers."""
)

async def travel_agent_callable(query: str) -> str:
    result = await travel_agent.run(query)
    return str(result.output)
