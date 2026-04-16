"""Generated CheckAgent wrapper — calls agents.langchain_lcel_class_agent:LCELAgent.invoke()."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.langchain_lcel_class_agent import LCELAgent as _target


async def checkagent_target(prompt: str) -> str:
    """Async wrapper: delegates to LCELAgent.invoke()."""
    result = _target.invoke(prompt)
    if asyncio.iscoroutine(result):
        result = await result
    return str(result)
