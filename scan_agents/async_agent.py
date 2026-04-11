"""Async agent for scan testing."""
import asyncio

async def run(query: str) -> str:
    """Async echo agent."""
    await asyncio.sleep(0)
    return f"Async: {query}"
