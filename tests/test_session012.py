"""
Session 012 tests — new probe categories (jailbreak/pii/scope), task_completion
list logic, AgentRun silent field drop, ProbeSet filter semantics.

New findings this session:
- F-027: AgentRun/Step silently drop unknown fields (no ValueError)
- Three new probe categories: jailbreak (15), pii (10), scope (8) = 68 total
- task_completion expected_output_contains list uses AND logic with partial scores
- ProbeSet.filter(tags={...}) uses OR logic
- F-005: init still broken (12th session), conftest.py now generated but empty
- F-024, F-025: path boundary bugs still open
"""

import pytest

from checkagent import AgentInput, AgentRun, Step, ToolCall
from checkagent.eval.metrics import task_completion
from checkagent.safety import (
    ProbeSet,
    SafetyCategory,
    Severity,
    ToolBoundary,
    ToolCallBoundaryValidator,
    probes_jailbreak,
    probes_pii,
    probes_scope,
)
from checkagent.safety.probes import injection, jailbreak, pii, scope


# ---------------------------------------------------------------------------
# New probe categories — presence and counts
# ---------------------------------------------------------------------------


class TestJailbreakProbes:
    def test_jailbreak_all_probes_count(self):
        jb = jailbreak.all_probes
        assert len(jb) == 15

    def test_jailbreak_roleplay_count(self):
        assert len(jailbreak.roleplay) == 7

    def test_jailbreak_encoding_count(self):
        assert len(jailbreak.encoding) == 8

    def test_jailbreak_all_have_jailbreak_category(self):
        for p in jailbreak.all_probes:
            assert p.category == SafetyCategory.JAILBREAK

    def test_jailbreak_roleplay_probes_have_roleplay_tag(self):
        for p in jailbreak.roleplay:
            assert "roleplay" in p.tags

    def test_jailbreak_encoding_probes_have_encoding_tag(self):
        for p in jailbreak.encoding:
            assert "encoding" in p.tags

    def test_jailbreak_has_critical_probes(self):
        critical = jailbreak.all_probes.filter(severity="critical")
        assert len(critical) >= 1

    def test_jailbreak_has_high_severity_probes(self):
        high = jailbreak.all_probes.filter(severity="high")
        assert len(high) >= 1

    def test_jailbreak_all_probes_have_nonempty_input(self):
        for p in jailbreak.all_probes:
            assert isinstance(p.input, str) and len(p.input) > 0

    def test_jailbreak_all_probes_have_names(self):
        names = [p.name for p in jailbreak.all_probes]
        assert len(set(names)) == len(names), "Duplicate probe names"


class TestPiiProbes:
    def test_pii_all_probes_count(self):
        assert len(pii.all_probes) == 10

    def test_pii_extraction_count(self):
        assert len(pii.extraction) == 10

    def test_pii_all_have_pii_category(self):
        for p in pii.all_probes:
            assert p.category == SafetyCategory.PII_LEAKAGE

    def test_pii_extraction_probes_have_extraction_tag(self):
        for p in pii.extraction:
            assert "extraction" in p.tags

    def test_pii_probes_nonempty_inputs(self):
        for p in pii.all_probes:
            assert isinstance(p.input, str) and len(p.input) > 0

    def test_pii_probes_unique_names(self):
        names = [p.name for p in pii.all_probes]
        assert len(set(names)) == len(names)


class TestScopeProbes:
    def test_scope_all_probes_count(self):
        assert len(scope.all_probes) == 8

    def test_scope_boundary_count(self):
        assert len(scope.boundary) == 8

    def test_scope_probes_have_boundary_tag(self):
        for p in scope.boundary:
            assert "boundary" in p.tags

    def test_scope_has_high_severity_probes(self):
        high = scope.all_probes.filter(severity="high")
        assert len(high) >= 1

    def test_scope_has_critical_probes(self):
        critical = scope.all_probes.filter(severity="critical")
        assert len(critical) >= 1

    def test_scope_probes_nonempty_inputs(self):
        for p in scope.all_probes:
            assert isinstance(p.input, str) and len(p.input) > 0


# ---------------------------------------------------------------------------
# probes_jailbreak / probes_pii / probes_scope safety namespace aliases
# ---------------------------------------------------------------------------


def test_probes_jailbreak_is_jailbreak_module():
    """probes_jailbreak from checkagent.safety IS the jailbreak module."""
    import checkagent.safety.probes.jailbreak as jb_direct

    assert probes_jailbreak is jb_direct


def test_probes_pii_is_pii_module():
    import checkagent.safety.probes.pii as pii_direct

    assert probes_pii is pii_direct


def test_probes_scope_is_scope_module():
    import checkagent.safety.probes.scope as scope_direct

    assert probes_scope is scope_direct


# ---------------------------------------------------------------------------
# Total probe library count (all 4 categories combined)
# ---------------------------------------------------------------------------


def test_total_probe_library_count():
    all_probes = (
        injection.all_probes
        + jailbreak.all_probes
        + pii.all_probes
        + scope.all_probes
    )
    assert len(all_probes) == 68


def test_combined_probes_unique_names():
    all_probes = (
        injection.all_probes
        + jailbreak.all_probes
        + pii.all_probes
        + scope.all_probes
    )
    names = [p.name for p in all_probes]
    assert len(set(names)) == len(names), "Duplicate names across probe categories"


def test_combined_probeset_name():
    combined = injection.all_probes + jailbreak.all_probes
    assert "injection.all" in combined.name
    assert "jailbreak.all" in combined.name


# ---------------------------------------------------------------------------
# ProbeSet.filter semantics — category, severity, tags
# ---------------------------------------------------------------------------


def test_filter_category_string_value():
    all_combined = (
        injection.all_probes
        + jailbreak.all_probes
        + pii.all_probes
        + scope.all_probes
    )
    only_jb = all_combined.filter(category="jailbreak")
    assert len(only_jb) == 15


def test_filter_category_enum():
    all_combined = (
        injection.all_probes
        + jailbreak.all_probes
        + pii.all_probes
        + scope.all_probes
    )
    only_pii = all_combined.filter(category=SafetyCategory.PII_LEAKAGE)
    assert len(only_pii) == 10


def test_filter_severity_lowercase_string():
    critical = jailbreak.all_probes.filter(severity="critical")
    assert len(critical) >= 1
    for p in critical:
        assert p.severity == Severity.CRITICAL


def test_filter_severity_enum_object():
    critical = jailbreak.all_probes.filter(severity=Severity.CRITICAL)
    assert len(critical) >= 1


def test_filter_severity_uppercase_string_returns_empty():
    """Filter with uppercase severity string returns nothing — filter is case-sensitive."""
    result = jailbreak.all_probes.filter(severity="CRITICAL")
    # This documents the DX gotcha: uppercase doesn't match
    assert len(result) == 0


def test_filter_tags_or_logic():
    """ProbeSet.filter(tags={...}) uses OR logic — matches any probe with ANY of the tags."""
    roleplay_only = jailbreak.all_probes.filter(tags={"roleplay"})
    persona_only = jailbreak.all_probes.filter(tags={"persona"})
    both = jailbreak.all_probes.filter(tags={"roleplay", "persona"})
    # OR logic: len(both) >= max(len(roleplay_only), len(persona_only))
    assert len(both) >= len(roleplay_only)
    assert len(both) >= len(persona_only)


def test_filter_tags_subset_of_superset():
    """Filtering on a superset of tags returns at least as many as any single tag."""
    encoding_only = jailbreak.all_probes.filter(tags={"encoding"})
    encoding_plus = jailbreak.all_probes.filter(tags={"encoding", "roleplay"})
    assert len(encoding_plus) >= len(encoding_only)


# ---------------------------------------------------------------------------
# task_completion — list of expected_output_contains (AND logic)
# ---------------------------------------------------------------------------


def make_run(final_output):
    return AgentRun(
        input=AgentInput(query="test"),
        final_output=final_output,
    )


def test_task_completion_list_all_present():
    run = make_run("The answer is 42 and also Paris")
    s = task_completion(run, expected_output_contains=["42", "Paris"], check_no_error=False)
    assert s.value == 1.0
    assert s.passed is True


def test_task_completion_list_one_missing():
    run = make_run("The answer is 42 and also Paris")
    s = task_completion(run, expected_output_contains=["42", "MISSING"], check_no_error=False)
    assert s.value == 0.5
    assert s.passed is False


def test_task_completion_list_all_missing():
    run = make_run("The answer is 42 and also Paris")
    s = task_completion(run, expected_output_contains=["NOPE", "MISSING"], check_no_error=False)
    assert s.value == 0.0
    assert s.passed is False


def test_task_completion_list_partial_score_with_threshold():
    """Partial matches pass if score >= threshold."""
    run = make_run("The answer is 42 and also Paris")
    s = task_completion(run, expected_output_contains=["42", "MISSING"], check_no_error=False, threshold=0.5)
    assert s.value == 0.5
    assert s.passed is True


def test_task_completion_list_partial_score_below_threshold():
    run = make_run("The answer is 42")
    s = task_completion(run, expected_output_contains=["42", "MISSING", "ALSO_MISSING"], check_no_error=False, threshold=0.5)
    assert s.value == pytest.approx(0.333, rel=0.01)
    assert s.passed is False


def test_task_completion_list_reason_shows_fraction():
    run = make_run("42 and Paris and also London")
    s = task_completion(run, expected_output_contains=["42", "Paris", "MISSING"], check_no_error=False)
    assert "2/3" in s.reason


def test_task_completion_list_metadata_has_checks():
    run = make_run("42 and Paris")
    s = task_completion(run, expected_output_contains=["42", "MISSING"], check_no_error=False)
    assert "checks" in s.metadata
    assert s.metadata["checks"] == [True, False]


def test_task_completion_list_and_check_no_error():
    """check_no_error=True (default) adds an implicit pass/fail check for run.error."""
    run = make_run("42 and Paris")
    s = task_completion(run, expected_output_contains=["42", "Paris"])  # check_no_error=True by default
    # 3 checks: check_no_error + 2 contains
    assert len(s.metadata["checks"]) == 3
    assert s.metadata["checks"][0] is True  # no error


def test_task_completion_list_with_error_run():
    """Run with error field set — check_no_error check fails."""
    run = AgentRun(input=AgentInput(query="test"), final_output="42", error="something went wrong")
    s = task_completion(run, expected_output_contains=["42"])  # check_no_error=True
    # error check fails even though output contains "42"
    assert s.metadata["checks"][0] is False  # error check


# ---------------------------------------------------------------------------
# F-027: AgentRun / Step silently drop unknown fields
# ---------------------------------------------------------------------------


def test_agentrun_silently_drops_output_field():
    """AgentRun(output=...) is silently discarded — correct field is final_output."""
    run = AgentRun(input=AgentInput(query="test"), output="silently lost")
    # No ValueError raised — silent drop
    assert run.final_output is None


def test_agentrun_silently_drops_unknown_fields():
    """AgentRun accepts any unknown field without raising ValueError."""
    run = AgentRun(input=AgentInput(query="test"), totally_made_up="value")
    assert not hasattr(run, "totally_made_up")


def test_step_silently_drops_output_field():
    """Step(output=...) is silently discarded — correct field is output_text."""
    step = Step(output="silently lost")
    assert step.output_text is None


def test_step_silently_drops_input_field():
    """Step(input=...) is silently discarded — correct field is input_text."""
    step = Step(input="silently lost")
    assert step.input_text is None


def test_agentrun_correct_field_names():
    """Document correct field names: final_output, not output."""
    run = AgentRun(input=AgentInput(query="test"), final_output="stored correctly")
    assert run.final_output == "stored correctly"


def test_step_correct_field_names():
    """Document correct field names: output_text / input_text, not output / input."""
    step = Step(input_text="correct input", output_text="correct output")
    assert step.input_text == "correct input"
    assert step.output_text == "correct output"


# ---------------------------------------------------------------------------
# F-005: checkagent init still broken (12th session)
# Document the new conftest.py generation but note it remains empty
# ---------------------------------------------------------------------------


def test_f005_init_generates_empty_conftest():
    """
    checkagent init now generates tests/conftest.py (new in session-012)
    but the file is empty — still no asyncio_mode or pythonpath config.
    F-005 remains open.
    """
    import subprocess
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(["checkagent", "init", tmpdir], capture_output=True)
        conftest = Path(tmpdir) / "tests" / "conftest.py"
        assert conftest.exists(), "tests/conftest.py should be generated"
        content = conftest.read_text().strip()
        # The conftest.py is (nearly) empty — just a docstring
        # It does NOT configure asyncio_mode or pythonpath
        assert "asyncio_mode" not in content
        assert "pythonpath" not in content


# ---------------------------------------------------------------------------
# F-024, F-025: Path boundary security bugs — still open
# ---------------------------------------------------------------------------


def _make_path_run(path_value: str) -> AgentRun:
    tc = ToolCall(name="read_file", arguments={"path": path_value})
    step = Step(tool_calls=[tc])
    return AgentRun(input=AgentInput(query="read file"), steps=[step])


def test_f024_path_prefix_confusion_still_open():
    """F-024: /dataextra/file.txt passes /data boundary — still a bug."""
    boundary = ToolBoundary(allowed_paths=["/data"])
    validator = ToolCallBoundaryValidator(boundary)
    result = validator.evaluate_run(_make_path_run("/dataextra/file.txt"))
    # BUG: this passes when it should fail
    assert result.passed is True  # documents the bug


def test_f025_path_traversal_still_open():
    """F-025: /data/../etc/passwd passes /data boundary — still a bug."""
    boundary = ToolBoundary(allowed_paths=["/data"])
    validator = ToolCallBoundaryValidator(boundary)
    result = validator.evaluate_run(_make_path_run("/data/../etc/passwd"))
    # BUG: this passes when it should fail
    assert result.passed is True  # documents the bug
