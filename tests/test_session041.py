"""
Session 041 tests — v0.3.0 (post-F-109 fix)

Key areas:
- F-109 FIXED: ToolCallBoundaryValidator kwargs API now emits DeprecationWarning
- F-110: CheckResult lacks direct .severity/.name access (DX friction)
- F-111: ToolBoundary.forbidden_argument_patterns requires dict, not set
- wrap() Python API behavior
"""
import warnings
import pytest


# ---------------------------------------------------------------------------
# F-109 FIXED: ToolCallBoundaryValidator kwargs API emits DeprecationWarning
# ---------------------------------------------------------------------------


class TestF109DeprecationShimAdded:
    """
    F-109 FIXED in latest commit (Fix F-109: add deprecation shim).
    Old kwargs API no longer raises TypeError — emits DeprecationWarning instead.
    Old code written against v0.2.0 still works during the migration window.
    """

    def test_old_kwargs_api_emits_deprecation_warning_not_typeerror(self):
        """Old API emits DeprecationWarning (not TypeError) — backward compat restored."""
        from checkagent.safety import ToolCallBoundaryValidator
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            v = ToolCallBoundaryValidator(allowed_tools={"search"}, forbidden_tools={"delete"})
            assert v is not None, "Object should be created successfully"
            assert len(w) == 1, f"Expected exactly 1 DeprecationWarning, got {len(w)}"
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

    def test_old_api_object_still_functional(self):
        """Object created via deprecated kwargs API should still work correctly."""
        import warnings
        from checkagent.safety import ToolCallBoundaryValidator
        from checkagent import AgentRun, Step, AgentInput, ToolCall
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            validator = ToolCallBoundaryValidator(allowed_tools={"search"}, forbidden_tools={"delete"})

        run = AgentRun(
            input=AgentInput(query="do something"),
            final_output="done",
            steps=[
                Step(
                    input_text="q",
                    output_text="a",
                    tool_calls=[ToolCall(name="delete", arguments={})]
                )
            ]
        )
        result = validator.evaluate_run(run)
        assert result.passed is False, "Deprecated API object should still block forbidden tools"

    def test_new_boundary_api_no_warning(self):
        """New ToolBoundary API emits no warnings."""
        from checkagent.safety import ToolBoundary, ToolCallBoundaryValidator
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            boundary = ToolBoundary(allowed_tools={"search"}, forbidden_tools={"delete"})
            v = ToolCallBoundaryValidator(boundary=boundary)
            assert v is not None
            # No DeprecationWarning expected
            depr_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(depr_warnings) == 0, "New API should not emit DeprecationWarning"


# ---------------------------------------------------------------------------
# F-110: CheckResult lacks direct .severity/.name — DX friction
# ---------------------------------------------------------------------------


class TestF110CheckResultNamingDXFriction:
    """
    F-110: PromptAnalysisResult.check_results returns CheckResult objects.
    Users naturally try cr.severity or cr.name but get AttributeError.
    The severity/name live on cr.check.severity and cr.check.name.

    This is a DX friction — the two-level access is non-obvious, especially
    since missing_high/missing_medium return PromptCheck objects (with .name,
    .severity directly), creating an inconsistent API surface.
    """

    @pytest.mark.xfail(strict=True, reason="F-110 fixed in session-043: CheckResult now has .severity property")
    def test_check_result_lacks_direct_severity_access(self):
        """F-110: cr.severity raises AttributeError — must use cr.check.severity."""
        from checkagent.safety import PromptAnalyzer
        analyzer = PromptAnalyzer()
        result = analyzer.analyze("You are a helpful AI assistant.")
        cr = result.check_results[0]
        # Direct access fails
        with pytest.raises(AttributeError):
            _ = cr.severity
        # Two-level access works
        assert cr.check.severity in {"high", "medium", "low"}

    @pytest.mark.xfail(strict=True, reason="F-110 fixed in session-043: CheckResult now has .name property")
    def test_check_result_lacks_direct_name_access(self):
        """F-110: cr.name raises AttributeError — must use cr.check.name."""
        from checkagent.safety import PromptAnalyzer
        analyzer = PromptAnalyzer()
        result = analyzer.analyze("You are a helpful AI assistant.")
        cr = result.check_results[0]
        with pytest.raises(AttributeError):
            _ = cr.name
        assert isinstance(cr.check.name, str)
        assert len(cr.check.name) > 0

    @pytest.mark.xfail(strict=True, reason="F-110 fixed in session-043: CheckResult now has .name/.severity properties, API is now consistent")
    def test_missing_high_returns_prompt_check_not_check_result(self):
        """missing_high returns PromptCheck (has .name/.severity directly)
        while check_results returns CheckResult (needs .check.name/.check.severity).
        Inconsistency: iterating both requires different access patterns.
        """
        from checkagent.safety import PromptAnalyzer
        analyzer = PromptAnalyzer()
        result = analyzer.analyze("You are a helpful AI.")
        # missing_high items have .name directly
        for pc in result.missing_high:
            assert hasattr(pc, "name"), "PromptCheck should have .name"
            assert hasattr(pc, "severity"), "PromptCheck should have .severity"
        # check_results items do NOT have .name directly
        for cr in result.check_results:
            assert not hasattr(cr, "name"), "CheckResult should NOT have direct .name"
            assert not hasattr(cr, "severity"), "CheckResult should NOT have direct .severity"

    def test_evidence_is_none_for_failed_checks(self):
        """evidence=None for failed checks, string snippet for passed checks."""
        from checkagent.safety import PromptAnalyzer
        analyzer = PromptAnalyzer()
        # Bad prompt — most checks will fail
        result = analyzer.analyze("You are an AI. Help the user.")
        for cr in result.check_results:
            if cr.passed:
                assert cr.evidence is not None, "Passed checks should have evidence"
                assert isinstance(cr.evidence, str)
            else:
                assert cr.evidence is None, "Failed checks should have evidence=None"


# ---------------------------------------------------------------------------
# F-111: ToolBoundary.forbidden_argument_patterns requires dict, not set
# ---------------------------------------------------------------------------


class TestF111ForbiddenArgumentPatternsRequiresDict:
    """
    F-111: ToolBoundary.forbidden_argument_patterns is typed as dict[str, str]
    (mapping argument name → regex pattern), but the field name sounds like
    a set of patterns. Passing a set raises AttributeError with a confusing
    message: "'set' object has no attribute 'items'".

    The correct API: {'path': r'[.][.]|passwd', 'query': r'DROP TABLE'}
    """

    @pytest.mark.xfail(strict=True, reason="F-111 improved in session-043: now raises TypeError with clear message instead of AttributeError")
    def test_set_raises_attribute_error_at_construction(self):
        """F-111: Passing set to forbidden_argument_patterns → AttributeError at construction.

        The error fires in __init__ (during pattern compilation), not at evaluate_run().
        This is a confusing failure mode — no type validation, just an internal crash.
        """
        from checkagent.safety import ToolBoundary, ToolCallBoundaryValidator
        boundary = ToolBoundary(
            allowed_tools={"read_file"},
            forbidden_argument_patterns={"../../etc/passwd", "*.env"}  # wrong: set
        )
        # Error is raised at constructor time (pattern compilation), not evaluate time
        with pytest.raises(AttributeError, match="items"):
            ToolCallBoundaryValidator(boundary=boundary)

    def test_dict_format_works_correctly(self):
        """Correct dict format: arg_name → regex_pattern."""
        from checkagent.safety import ToolBoundary, ToolCallBoundaryValidator
        from checkagent import AgentRun, Step, AgentInput, ToolCall
        boundary = ToolBoundary(
            allowed_tools={"read_file"},
            forbidden_argument_patterns={"path": r"\.\.|passwd|\.env"}
        )
        validator = ToolCallBoundaryValidator(boundary=boundary)

        # Traversal path blocked
        run = AgentRun(
            input=AgentInput(query="read"),
            final_output="ok",
            steps=[
                Step(input_text="q", output_text="a",
                     tool_calls=[ToolCall(name="read_file", arguments={"path": "../../etc/passwd"})])
            ]
        )
        result = validator.evaluate_run(run)
        assert result.passed is False, "Path traversal should be blocked"

        # Safe path allowed
        run2 = AgentRun(
            input=AgentInput(query="read"),
            final_output="ok",
            steps=[
                Step(input_text="q", output_text="a",
                     tool_calls=[ToolCall(name="read_file", arguments={"path": "/data/file.txt"})])
            ]
        )
        result2 = validator.evaluate_run(run2)
        assert result2.passed is True, "Safe path should be allowed"


# ---------------------------------------------------------------------------
# wrap() Python API behavior
# ---------------------------------------------------------------------------


class TestWrapPythonAPI:
    """
    The checkagent.wrap() function wraps a Python callable as a GenericAdapter.
    Works as decorator (@wrap) or function (wrap(fn)).
    Only works with callables that take a string input and return a string.
    """

    def test_wrap_decorator_on_function(self):
        """@wrap decorator on a plain function creates a GenericAdapter."""
        import asyncio
        from checkagent import wrap, AgentInput
        from checkagent.adapters.generic import GenericAdapter

        @wrap
        def echo(query: str) -> str:
            return f"echo: {query}"

        assert isinstance(echo, GenericAdapter)

        result = asyncio.run(echo.run(AgentInput(query="hello")))
        assert result.final_output == "echo: hello"
        assert result.succeeded is True

    def test_wrap_function_call(self):
        """wrap(fn) as a function call creates a GenericAdapter."""
        import asyncio
        from checkagent import wrap, AgentInput

        def my_agent(query: str) -> str:
            return f"response to: {query}"

        adapter = wrap(my_agent)
        result = asyncio.run(adapter.run(AgentInput(query="test")))
        assert result.final_output == "response to: test"

    def test_wrap_callable_instance(self):
        """wrap(instance) works when instance has __call__ method."""
        import asyncio
        from checkagent import wrap, AgentInput

        class CallableAgent:
            def __call__(self, query: str) -> str:
                return f"called: {query}"

        adapter = wrap(CallableAgent())
        result = asyncio.run(adapter.run(AgentInput(query="hi")))
        assert result.final_output == "called: hi"

    def test_wrap_class_with_invoke_returns_none(self):
        """wrap(Class) where Class has invoke() method silently returns None.

        This is a DX trap: the CLI 'checkagent wrap' can handle class agents,
        but the Python wrap() function does not auto-detect invoke() methods.
        Passing a class (not instance) calls Class(query) → returns an instance
        object, not a string. GenericAdapter sees non-string output → None.

        Fix: use wrap(lambda q: MyClass().invoke(q)) or @wrap on a function.
        """
        import asyncio
        from checkagent import wrap, AgentInput

        class InvokeAgent:
            def invoke(self, prompt):
                return f"invoked: {prompt}"

        adapter = wrap(InvokeAgent)  # Wraps the CLASS, not instance
        result = asyncio.run(adapter.run(AgentInput(query="hello")))
        # Returns None because Class(query) returns an instance, not a string
        assert result.final_output is None, "wrap(Class) with invoke() silently returns None"
