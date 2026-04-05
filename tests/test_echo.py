"""Smoke tests for the echo agent using MockLLM and GenericAdapter."""

import pytest

from agents.echo_agent import echo_agent


@pytest.mark.agent_test(layer="mock")
async def test_echo_basic(ap_mock_llm):
    """Echo agent should return uppercased input."""
    result = await echo_agent.run("hello world")

    assert result.succeeded
    assert result.final_output == "HELLO WORLD"


@pytest.mark.agent_test(layer="mock")
async def test_echo_preserves_input(ap_mock_llm):
    """The run should record what was sent in."""
    result = await echo_agent.run("test input")

    assert result.input.query == "test input"
    assert result.steps[0].output_text == "TEST INPUT"


@pytest.mark.agent_test(layer="mock")
async def test_echo_empty_string(ap_mock_llm):
    """Edge case: empty string."""
    result = await echo_agent.run("")

    assert result.succeeded
    assert result.final_output == ""
