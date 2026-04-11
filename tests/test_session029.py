"""
Session 029 tests: LLM fault methods, triggered property (F-078 partial fix),
F-081/F-080 fixes verified, LLM fault parity gaps (F-082), optional deps DX (F-083).
"""
import pytest
from checkagent import MockLLM, FaultInjector, MockTool


# ---------------------------------------------------------------------------
# F-078 partial fix: triggered property, trigger_count property, triggered_records
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_triggered_property_is_real_property():
    """
    F-078 PARTIAL FIX (session-029): FaultInjector now has a .triggered @property
    returning bool. Previously, fi.was_triggered was a method — without () it returned
    a bound method object, which is always truthy.
    """
    fi = FaultInjector()
    fi.on_llm().rate_limit(after_n=0)
    llm = MockLLM()
    llm.attach_faults(fi)

    # Before any call — should be False
    assert fi.triggered is False
    assert isinstance(fi.triggered, bool)

    try:
        await llm.complete("test")
    except Exception:
        pass

    # After fault fires — should be True
    assert fi.triggered is True


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_trigger_count_property():
    """trigger_count is a @property returning int — count of fault activations."""
    fi = FaultInjector()
    fi.on_llm().rate_limit(after_n=0)
    llm = MockLLM()
    llm.attach_faults(fi)

    assert fi.trigger_count == 0

    for _ in range(3):
        try:
            await llm.complete("test")
        except Exception:
            pass

    assert fi.trigger_count == 3


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_triggered_records_property():
    """triggered_records is a @property returning list of FaultRecord objects."""
    fi = FaultInjector()
    fi.on_llm().server_error("oops")
    llm = MockLLM()
    llm.attach_faults(fi)

    assert fi.triggered_records == []

    try:
        await llm.complete("hello")
    except Exception:
        pass

    records = fi.triggered_records
    assert len(records) == 1
    record = records[0]
    assert record.triggered is True
    assert record.target == "llm"


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_was_triggered_still_works_with_target():
    """was_triggered(target) method still works for filtered checks."""
    fi = FaultInjector()
    fi.on_tool("search").timeout()
    fi.on_tool("write").rate_limit()
    tool_search = MockTool().register("search", schema={"query": {"type": "string"}})
    tool_write = MockTool().register("write", schema={"content": {"type": "string"}})
    tool_search.attach_faults(fi)
    tool_write.attach_faults(fi)

    try:
        await tool_search.call("search", {"query": "hello"})
    except Exception:
        pass

    # was_triggered with target filter
    assert fi.was_triggered("search") is True
    assert fi.was_triggered("write") is False
    # fi.triggered (no arg) is True — any fault triggered
    assert fi.triggered is True


# ---------------------------------------------------------------------------
# LLM fault methods: content_filter, context_overflow, partial_response
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_llm_fault_content_filter():
    """on_llm().content_filter() raises LLMContentFilterError."""
    from checkagent.mock.fault import FaultInjector
    fi = FaultInjector()
    fi.on_llm().content_filter()
    llm = MockLLM()
    llm.attach_faults(fi)

    with pytest.raises(Exception) as exc_info:
        await llm.complete("tell me something bad")

    assert "content" in str(exc_info.value).lower() or "filter" in str(exc_info.value).lower()
    assert fi.triggered is True


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_llm_fault_context_overflow():
    """on_llm().context_overflow() raises LLMContextOverflowError."""
    fi = FaultInjector()
    fi.on_llm().context_overflow()
    llm = MockLLM()
    llm.attach_faults(fi)

    with pytest.raises(Exception) as exc_info:
        await llm.complete("a" * 1000)

    assert "context" in str(exc_info.value).lower() or "128000" in str(exc_info.value)
    assert fi.triggered is True


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_llm_fault_partial_response():
    """on_llm().partial_response() raises LLMPartialResponseError."""
    fi = FaultInjector()
    fi.on_llm().partial_response()
    llm = MockLLM()
    llm.add_rule(".*", "This would be the full response", match_mode=__import__('checkagent').MatchMode.REGEX)
    llm.attach_faults(fi)

    with pytest.raises(Exception) as exc_info:
        await llm.complete("hello")

    assert "partial" in str(exc_info.value).lower() or "streaming" in str(exc_info.value).lower()
    assert fi.triggered is True


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_llm_fault_rate_limit_after_n():
    """on_llm().rate_limit(after_n=N) — first N calls succeed, then raises."""
    fi = FaultInjector()
    fi.on_llm().rate_limit(after_n=2)
    llm = MockLLM()
    llm.attach_faults(fi)

    # First 2 calls should succeed
    r1 = await llm.complete("call 1")
    r2 = await llm.complete("call 2")
    assert r1 is not None
    assert r2 is not None
    assert fi.triggered is False

    # 3rd call should fail
    with pytest.raises(Exception) as exc_info:
        await llm.complete("call 3")
    assert "429" in str(exc_info.value) or "rate" in str(exc_info.value).lower()
    assert fi.triggered is True


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_llm_fault_server_error_custom_message():
    """on_llm().server_error(message) includes the custom message in exception."""
    fi = FaultInjector()
    fi.on_llm().server_error("Database connection failed")
    llm = MockLLM()
    llm.attach_faults(fi)

    with pytest.raises(Exception) as exc_info:
        await llm.complete("hello")
    assert "Database connection failed" in str(exc_info.value)


# ---------------------------------------------------------------------------
# F-082: LLM fault builder lacks intermittent and slow
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f082_fixed_llm_fault_builder_has_intermittent():
    """
    F-082 FIXED: on_llm() now has .intermittent() method.
    Verify it raises LLMIntermittentError at fail_rate=1.0.
    """
    from checkagent.mock.fault import LLMIntermittentError

    fi = FaultInjector()
    fi.on_llm().intermittent(fail_rate=1.0, seed=42)

    with pytest.raises(LLMIntermittentError):
        fi.check_llm()


@pytest.mark.agent_test
def test_f082_fixed_llm_fault_builder_has_slow():
    """
    F-082 FIXED: on_llm() has .slow() method.
    F-016 ALSO FIXED: sync check_llm() now sleeps instead of raising LLMSlowError.
    """
    import time

    fi = FaultInjector()
    fi.on_llm().slow(latency_ms=50)

    t0 = time.perf_counter()
    fi.check_llm()  # No longer raises — sleeps instead
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms >= 40, f"Expected ~50ms sleep, got {elapsed_ms:.0f}ms"
    assert fi.triggered


@pytest.mark.agent_test
async def test_f082_fixed_llm_slow_async_real_delay():
    """
    F-082 FIXED: on_llm().slow() with check_llm_async() does real latency simulation.
    No exception — just a real sleep (same behavior as on_tool().slow() async).
    """
    import time

    fi = FaultInjector()
    fi.on_llm().slow(latency_ms=60)

    t0 = time.perf_counter()
    await fi.check_llm_async()
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms >= 50, f"Expected >=50ms delay, got {elapsed_ms:.0f}ms"


@pytest.mark.agent_test
def test_f082_tool_fault_builder_for_comparison():
    """Tool fault builder HAS intermittent and slow — confirms the parity gap."""
    fi = FaultInjector()
    tool_builder = fi.on_tool("any")
    assert hasattr(tool_builder, "intermittent")
    assert hasattr(tool_builder, "slow")


# ---------------------------------------------------------------------------
# F-083: assert_output_matches / dirty-equals is an optional dep under [structured]
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f083_dirty_equals_is_optional_dep():
    """
    F-083: dirty-equals (used by assert_output_matches) is declared under the
    [structured] optional extra, not as a default dependency.
    On a fresh 'pip install checkagent' without extras, assert_output_matches
    would fail with ImportError if dirty_equals isn't installed.

    Same issue as F-008 (jsonschema) — undeclared default deps.
    """
    import importlib.metadata
    deps = importlib.metadata.requires("checkagent")
    # dirty-equals should be a default dep (no extra condition) for assert_output_matches
    default_deps = [d for d in deps if "extra ==" not in d]
    optional_only = [d for d in deps if "dirty-equals" in d and "extra ==" in d]
    is_default = any("dirty-equals" in d for d in default_deps)

    assert not is_default, (
        "F-083 FIXED: dirty-equals is now a default dependency — update this test"
    )
    assert len(optional_only) > 0, "dirty-equals not found in optional deps either — unexpected"


@pytest.mark.agent_test
def test_f083_deepdiff_is_optional_dep():
    """
    F-083: deepdiff (used internally) is also under [structured] extra only.
    """
    import importlib.metadata
    deps = importlib.metadata.requires("checkagent")
    default_deps = [d for d in deps if "extra ==" not in d]
    is_default = any("deepdiff" in d for d in default_deps)

    assert not is_default, (
        "F-083 FIXED: deepdiff is now a default dependency — update this test"
    )


@pytest.mark.agent_test
def test_f008_jsonschema_now_optional_extra():
    """
    F-008 PARTIAL FIX (session-029): jsonschema is now declared as the
    [json-schema] optional extra. Users can pip install checkagent[json-schema].
    Previously it wasn't declared at all.
    Still not a default dep — assert_json_schema breaks on minimal install.
    """
    import importlib.metadata
    deps = importlib.metadata.requires("checkagent")
    json_schema_extra = [d for d in deps if "jsonschema" in d and "json-schema" in d]
    assert len(json_schema_extra) > 0, "jsonschema not found under [json-schema] extra"


# ---------------------------------------------------------------------------
# LLM fault exceptions are importable from checkagent.mock.fault
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_llm_fault_exceptions_importable():
    """LLM fault exception classes are importable from checkagent.mock.fault."""
    from checkagent.mock.fault import (
        LLMContentFilterError,
        LLMContextOverflowError,
        LLMPartialResponseError,
        LLMRateLimitError,
        LLMServerError,
    )
    # Verify they're proper exception classes
    for exc_cls in [LLMContentFilterError, LLMContextOverflowError,
                    LLMPartialResponseError, LLMRateLimitError, LLMServerError]:
        assert issubclass(exc_cls, Exception)


@pytest.mark.agent_test
def test_llm_fault_exceptions_not_at_top_level():
    """
    LLM fault exceptions are NOT importable from top-level checkagent.
    Users must know to import from checkagent.mock.fault.
    Part of the broader missing-top-level-exports pattern.
    """
    import checkagent
    for name in ["LLMContentFilterError", "LLMContextOverflowError",
                 "LLMPartialResponseError", "LLMRateLimitError", "LLMServerError"]:
        assert not hasattr(checkagent, name), (
            f"{name} is now at top-level checkagent — update this test"
        )


# ---------------------------------------------------------------------------
# LLM fault: rate_limit(after_n=0) fires immediately
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_llm_rate_limit_after_n_zero_immediate():
    """rate_limit(after_n=0) fires on the very first call."""
    fi = FaultInjector()
    fi.on_llm().rate_limit(after_n=0)
    llm = MockLLM()
    llm.attach_faults(fi)

    with pytest.raises(Exception):
        await llm.complete("first and only")

    assert fi.trigger_count == 1


# ---------------------------------------------------------------------------
# triggered records include fault_type info
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_triggered_records_include_fault_type():
    """triggered_records contains FaultRecord with fault_type identifying what fired."""
    fi = FaultInjector()
    fi.on_llm().content_filter()
    llm = MockLLM()
    llm.attach_faults(fi)

    try:
        await llm.complete("bad input")
    except Exception:
        pass

    records = fi.triggered_records
    assert len(records) == 1
    record = records[0]
    # fault_type should indicate content_filter
    fault_type_str = str(record.fault_type).lower()
    assert "content_filter" in fault_type_str or "content" in fault_type_str


# ---------------------------------------------------------------------------
# F-081 fix confirmed (also in test_session028 — belt and suspenders)
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f081_fix_confirmed_with_usage_validates():
    """F-081 FIXED: with_usage() raises ValueError on conflicting args."""
    with pytest.raises(ValueError, match="Cannot set both auto_estimate"):
        MockLLM().with_usage(prompt_tokens=100, auto_estimate=True)

    # No error when using only one
    llm1 = MockLLM().with_usage(prompt_tokens=100)
    assert llm1 is not None
    llm2 = MockLLM().with_usage(auto_estimate=True)
    assert llm2 is not None


# ---------------------------------------------------------------------------
# F-080 fix confirmed: auto_estimate docstring now correct
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f080_docstring_now_documents_correct_formula():
    """
    F-080 FIXED (session-029): with_usage() docstring now correctly says
    'len(text) // 4 + 1' matching actual behavior.
    """
    import checkagent.mock.llm as llm_mod
    docstring = llm_mod.MockLLM.with_usage.__doc__ or ""
    # Should document the +1 term
    assert "// 4 + 1" in docstring or "//4+1" in docstring or "/ 4 + 1" in docstring, (
        f"Docstring still doesn't document '// 4 + 1' formula. Got: {docstring[:200]}"
    )
