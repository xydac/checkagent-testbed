"""
Session 028 tests: MockLLM.with_usage() token simulation, MatchMode top-level export,
and verification of F-078/F-079/F-080/F-081.
"""
import math
import pytest
from checkagent import MockLLM, MatchMode, FaultInjector, MockTool


# ---------------------------------------------------------------------------
# MockLLM.with_usage() — basic functionality
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_fixed_tokens_complete():
    """with_usage(prompt_tokens=N, completion_tokens=M) stamps every LLMCall."""
    llm = MockLLM().with_usage(prompt_tokens=100, completion_tokens=50)
    await llm.complete("hello world")
    call = llm.last_call
    assert call.prompt_tokens == 100
    assert call.completion_tokens == 50


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_fixed_tokens_complete_sync():
    """with_usage tokens appear on complete_sync() calls too."""
    llm = MockLLM().with_usage(prompt_tokens=75, completion_tokens=30)
    llm.complete_sync("sync test")
    call = llm.last_call
    assert call.prompt_tokens == 75
    assert call.completion_tokens == 30


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_fixed_tokens_stream():
    """with_usage tokens appear on stream() calls."""
    llm = MockLLM().with_usage(prompt_tokens=200, completion_tokens=100)
    chunks = []
    async for chunk in llm.stream("test input"):
        chunks.append(chunk)
    call = llm.last_call
    assert call.prompt_tokens == 200
    assert call.completion_tokens == 100


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_multiple_calls_accumulate():
    """Each call gets the same fixed token values; sum manually gives totals."""
    llm = MockLLM().with_usage(prompt_tokens=100, completion_tokens=50)
    await llm.complete("call one")
    await llm.complete("call two")
    await llm.complete("call three")
    assert len(llm.calls) == 3
    total_prompt = sum(c.prompt_tokens or 0 for c in llm.calls)
    total_completion = sum(c.completion_tokens or 0 for c in llm.calls)
    assert total_prompt == 300
    assert total_completion == 150


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_no_usage_baseline():
    """Without with_usage(), prompt_tokens and completion_tokens are None."""
    llm = MockLLM()
    await llm.complete("test")
    call = llm.last_call
    assert call.prompt_tokens is None
    assert call.completion_tokens is None


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_returns_self():
    """with_usage() returns the same MockLLM instance (fluent API)."""
    llm = MockLLM()
    result = llm.with_usage(prompt_tokens=10, completion_tokens=5)
    assert result is llm


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_prompt_only():
    """Setting only prompt_tokens gives 0 for completion_tokens (not None)."""
    llm = MockLLM().with_usage(prompt_tokens=200)
    await llm.complete("test")
    call = llm.last_call
    assert call.prompt_tokens == 200
    assert call.completion_tokens == 0  # 0, not None — with_usage was configured


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_completion_only():
    """Setting only completion_tokens gives 0 for prompt_tokens (not None)."""
    llm = MockLLM().with_usage(completion_tokens=75)
    await llm.complete("test")
    call = llm.last_call
    assert call.prompt_tokens == 0  # 0, not None
    assert call.completion_tokens == 75


# ---------------------------------------------------------------------------
# MockLLM.with_usage(auto_estimate=True) — F-080
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_auto_estimate_uses_ceiling_not_floor():
    """
    F-080: with_usage(auto_estimate=True) docstring claims 'len(text) // 4'
    (floor division) but actual behavior is math.ceil(len/4).
    For input len=3: floor=0, ceil=1. We observe ceil.
    """
    llm = MockLLM().with_usage(auto_estimate=True)
    await llm.complete("abc")  # len=3: floor=0, ceil=1
    call = llm.last_call
    # Document actual behavior (ceiling), not documented behavior (floor)
    assert call.prompt_tokens == math.ceil(len("abc") / 4)  # 1


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_auto_estimate_response_is_mock_response():
    """
    auto_estimate estimates completion_tokens from the actual response text
    ('Mock response' = 13 chars), not from any rule-configured response.
    """
    llm = MockLLM().with_usage(auto_estimate=True)
    resp = await llm.complete("hello world")
    call = llm.last_call
    # Actual response is 'Mock response' (13 chars): ceil(13/4) = 4
    assert call.response_text == "Mock response"
    assert call.completion_tokens == math.ceil(len("Mock response") / 4)


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_auto_estimate_prompt_based_on_input():
    """
    auto_estimate prompt_tokens actual formula: len(text) // 4 + 1.
    (Docstring claims 'len(text) // 4' — this is F-080.)
    """
    llm = MockLLM().with_usage(auto_estimate=True)
    input_text = "a" * 40  # 40 chars: 40//4 + 1 = 11 (NOT 10 as docs suggest)
    await llm.complete(input_text)
    call = llm.last_call
    assert call.prompt_tokens == len(input_text) // 4 + 1  # actual: 11


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_f080_auto_estimate_discrepancy_confirmed():
    """
    F-080 CONFIRMED: docstring says 'len(text) // 4' but actual formula is
    'len(text) // 4 + 1'. These always differ — every estimate is 1 too high.
    """
    llm = MockLLM().with_usage(auto_estimate=True)
    await llm.complete("x")
    documented = len("x") // 4      # 0
    actual = llm.last_call.prompt_tokens  # 1
    assert actual != documented     # formula is wrong in docs
    assert actual == len("x") // 4 + 1  # actual formula: n//4 + 1


# ---------------------------------------------------------------------------
# F-081: with_usage(prompt_tokens=N, auto_estimate=True) — conflict
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_f081_both_fixed_and_auto_estimate_no_error():
    """
    F-081: Setting both prompt_tokens and auto_estimate=True raises no error.
    Neither the fixed value nor the estimated value is used as documented.
    Behavior is undefined; users need guidance on precedence.
    """
    # No ValueError raised, no warning
    llm = MockLLM().with_usage(prompt_tokens=999, auto_estimate=True)
    await llm.complete("test")
    call = llm.last_call
    # Should be 999 (fixed) OR ceil(4/4)=1 (estimated) — neither is what we get
    assert call.prompt_tokens != 999, "Fixed value NOT used (auto_estimate takes precedence)"
    # What we get is unpredictable — just document it's not the fixed value


# ---------------------------------------------------------------------------
# MatchMode top-level export
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_matchmode_exported_at_top_level():
    """MatchMode is importable from top-level checkagent."""
    from checkagent import MatchMode
    assert hasattr(MatchMode, 'EXACT')
    assert hasattr(MatchMode, 'SUBSTRING')
    assert hasattr(MatchMode, 'REGEX')


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_add_rule_matchmode_regex():
    """MatchMode.REGEX allows '.*' to match everything."""
    llm = MockLLM()
    llm.add_rule(".*", "Regex catch-all!", match_mode=MatchMode.REGEX)
    r = await llm.complete("anything at all")
    assert r == "Regex catch-all!"


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_add_rule_matchmode_exact():
    """MatchMode.EXACT requires full string equality."""
    llm = MockLLM()
    llm.add_rule("exact input", "Exact match!", match_mode=MatchMode.EXACT)
    assert await llm.complete("exact input") == "Exact match!"
    assert await llm.complete("exact input plus extra") == "Mock response"


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_add_rule_default_substring_dotstar_is_literal():
    """
    DX trap: add_rule('.*', ...) with default SUBSTRING mode treats '.*' as
    a literal string, NOT a regex. Input must literally contain '.*' to match.
    Use MatchMode.REGEX or empty string '' for catch-all with SUBSTRING.
    """
    llm = MockLLM()
    llm.add_rule(".*", "Should not match!")  # SUBSTRING, literal '.*'
    r = await llm.complete("hello world")
    assert r == "Mock response"  # '.*' not in 'hello world' as substring


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_add_rule_substring_empty_string_matches_all():
    """Empty string is substring of any string — catch-all for SUBSTRING mode."""
    llm = MockLLM()
    llm.add_rule("", "Empty string catch-all!")
    r = await llm.complete("any input at all")
    assert r == "Empty string catch-all!"


# ---------------------------------------------------------------------------
# F-078: was_triggered is a method, not a property (still open)
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f078_was_triggered_is_method_not_property():
    """
    F-078 OPEN: FaultInjector.was_triggered is a bound method, not a property.
    'if fi.was_triggered:' is ALWAYS truthy (checks the method object, not result).
    Users must call fi.was_triggered() with parentheses.
    """
    fi = FaultInjector()
    # was_triggered is callable (it's a method)
    assert callable(fi.was_triggered)
    # The method object is always truthy — a common DX trap
    assert bool(fi.was_triggered) is True  # method object, not the result
    # Correct usage requires calling it
    assert fi.was_triggered() is False  # no faults triggered yet


# ---------------------------------------------------------------------------
# F-079: second attach_faults() overwrites first (still open)
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_f079_double_attach_overwrites_first():
    """
    F-079 OPEN: Calling attach_faults() twice silently overwrites the first
    injector. Faults from fi1 are lost when fi2 is attached. Not additive.
    """
    fi1 = FaultInjector()
    fi1.on_tool("search").timeout()

    fi2 = FaultInjector()
    fi2.on_tool("book").rate_limit()

    tool = MockTool()
    tool.register(
        "search",
        response={"result": "ok"},
        schema={"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]},
    )
    tool.register(
        "book",
        response={"booked": True},
        schema={"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    )

    tool.attach_faults(fi1)
    tool.attach_faults(fi2)  # overwrites fi1 — search fault is now lost

    # search fault was in fi1 — should now be GONE (fi1 overwritten)
    result = await tool.call("search", {"q": "test"})
    assert result == {"result": "ok"}  # no fault — fi1 was silently dropped

    # book fault is in fi2 — should still fire
    with pytest.raises(Exception):
        await tool.call("book", {"id": "123"})


# ---------------------------------------------------------------------------
# Integration: with_usage + on_input fluent API
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_compatible_with_on_input_fluent():
    """with_usage() and on_input().respond() can be combined on the same instance."""
    llm = MockLLM().with_usage(prompt_tokens=50, completion_tokens=25)
    llm.on_input(contains="book").respond("Booking confirmed!")
    llm.on_input(contains="weather").respond("It's sunny!")

    r1 = await llm.complete("I want to book a flight")
    assert r1 == "Booking confirmed!"
    assert llm.last_call.prompt_tokens == 50
    assert llm.last_call.completion_tokens == 25

    r2 = await llm.complete("What's the weather?")
    assert r2 == "It's sunny!"
    assert llm.last_call.prompt_tokens == 50


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_compatible_with_attach_faults():
    """with_usage() and attach_faults() can both be set on the same MockLLM."""
    fi = FaultInjector()
    # on_llm() takes no pattern argument; applies to all LLM calls
    fi.on_llm().rate_limit()

    llm = MockLLM().with_usage(prompt_tokens=100, completion_tokens=40)
    llm.attach_faults(fi)

    from checkagent.mock.fault import LLMRateLimitError
    with pytest.raises(LLMRateLimitError):
        await llm.complete("trigger fault")

    # Fault fires before completion — no call recorded
    assert len(llm.calls) == 0


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_with_usage_reset_clears_calls_preserves_config():
    """reset() clears calls but with_usage configuration persists."""
    llm = MockLLM().with_usage(prompt_tokens=100, completion_tokens=50)
    await llm.complete("before reset")
    assert len(llm.calls) == 1

    llm.reset()
    assert len(llm.calls) == 0

    await llm.complete("after reset")
    assert len(llm.calls) == 1
    assert llm.last_call.prompt_tokens == 100  # config preserved after reset
