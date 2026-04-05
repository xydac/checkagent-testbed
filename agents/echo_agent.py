"""Echo agent -- simplest possible agent for smoke testing.

Takes a query string, returns it uppercased. That's it.
"""

from checkagent.adapters.generic import wrap


@wrap
async def echo_agent(query: str) -> str:
    return query.upper()
