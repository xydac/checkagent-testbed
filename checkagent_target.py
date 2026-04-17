"""Generated CheckAgent wrapper — calls agents.echo_agent:echo_agent.run()."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.echo_agent import echo_agent as _target


async def checkagent_target(prompt: str) -> str:
    """Async wrapper: delegates to echo_agent.run()."""
    result = _target.run(prompt)
    if asyncio.iscoroutine(result):
        result = await result
    return str(result)
