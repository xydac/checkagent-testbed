"""Session-045 tests: scope_boundary pattern expansion in PromptAnalyzer.

New commit: 'Expand scope_boundary patterns to catch common real-world phrasings'
- Pattern 1: 'ONLY answer HR questions' (no 'with' keyword required after verb)
- Pattern 2: 'Your role is limited to / restricted to / only'
- Pattern 3: 'you are a [domain] agent and only ...'
Also confirms F-113 (ProbeSet.filter() tags case-sensitivity) still open.
"""

from __future__ import annotations

import pytest
from checkagent.safety.prompt_analyzer import PromptAnalyzer, PromptAnalysisResult


def get_scope_result(prompt: str) -> bool | None:
    """Return the 'Scope Boundary' check result for a prompt, or None if missing."""
    result = PromptAnalyzer().analyze(prompt)
    checks = {c.name: c for c in result.check_results}
    sb = checks.get("Scope Boundary")
    return sb.passed if sb else None


# ---------------------------------------------------------------------------
# New pattern 1: 'only answer/help/respond X' without 'with' keyword
# ---------------------------------------------------------------------------

class TestScopeBoundaryNoWithKeyword:
    """Previously the pattern required 'only answer WITH' — now flexible."""

    def test_only_answer_domain_questions_no_with(self):
        # "ONLY answer HR questions" — old pattern would miss this
        result = get_scope_result("You are an HR assistant. ONLY answer HR questions.")
        assert result is True

    def test_only_answer_questions_about(self):
        result = get_scope_result("Only answer questions about our software products.")
        assert result is True

    def test_solely_help_to(self):
        result = get_scope_result("You may solely help to resolve billing issues.")
        assert result is True

    def test_exclusively_respond_to(self):
        result = get_scope_result("Exclusively respond to customer complaints.")
        assert result is True

    def test_only_answer_requests(self):
        result = get_scope_result("Only answer requests related to our services.")
        assert result is True

    def test_old_pattern_still_works(self):
        # 'only answer with' was the original pattern — must still work
        result = get_scope_result("Only answer with information from the provided documentation.")
        assert result is True


# ---------------------------------------------------------------------------
# New pattern 2: 'your role/purpose is limited/restricted/only'
# ---------------------------------------------------------------------------

class TestScopeBoundaryRoleLimited:
    """'Your role is limited to' — a very common real-world phrasing."""

    def test_your_role_is_limited_to(self):
        result = get_scope_result("Your role is limited to answering questions about our products.")
        assert result is True

    def test_your_role_is_restricted(self):
        result = get_scope_result("Your role is restricted to internal HR topics only.")
        assert result is True

    def test_your_role_is_only(self):
        result = get_scope_result("Your role is only to provide product recommendations.")
        assert result is True

    def test_your_purpose_is_limited(self):
        result = get_scope_result("Your purpose is limited to customer onboarding tasks.")
        assert result is True

    def test_your_purpose_is_restricted(self):
        result = get_scope_result("Your purpose is restricted to answering FAQ questions.")
        assert result is True


# ---------------------------------------------------------------------------
# New pattern 3: '[domain] agent and only'
# ---------------------------------------------------------------------------

class TestScopeBoundaryDomainAgentOnly:
    """'you are a [domain] agent and only' phrasing."""

    def test_hr_agent_and_only(self):
        result = get_scope_result("You are an HR agent and only answer HR questions.")
        assert result is True

    def test_finance_bot_and_solely(self):
        result = get_scope_result("You are a finance bot and solely handle financial inquiries.")
        assert result is True

    def test_support_assistant_and_only(self):
        result = get_scope_result("You are a support assistant and only respond to product issues.")
        assert result is True


# ---------------------------------------------------------------------------
# Existing patterns — regression tests
# ---------------------------------------------------------------------------

class TestScopeBoundaryExistingPatterns:
    """Existing patterns should still match after the new commit."""

    def test_must_not_discuss(self):
        result = get_scope_result("You must not discuss competitor products or services.")
        assert result is True

    def test_cannot_answer(self):
        result = get_scope_result("You cannot answer questions about company finances.")
        assert result is True

    def test_never_outside_scope(self):
        result = get_scope_result("Never answer questions outside your scope.")
        assert result is True

    def test_do_not_discuss(self):
        result = get_scope_result("Do not discuss anything unrelated to customer support.")
        assert result is True

    def test_outside_your_domain(self):
        result = get_scope_result("Politely decline requests outside your domain.")
        assert result is True


# ---------------------------------------------------------------------------
# Negative cases — these should NOT match Scope Boundary
# ---------------------------------------------------------------------------

class TestScopeBoundaryNegativeCases:
    """Prompts without scope limitation should NOT be detected as having it."""

    def test_generic_helpful_assistant(self):
        result = get_scope_result("You are a helpful assistant. Answer all questions.")
        assert result is False

    def test_no_scope_instructions(self):
        result = get_scope_result("Be helpful, harmless, and honest.")
        assert result is False

    def test_open_ended_assistant(self):
        result = get_scope_result("Answer user questions thoroughly and accurately.")
        assert result is False

    def test_hr_role_without_restriction(self):
        # "You are an HR assistant." alone should NOT trigger scope boundary
        # because it doesn't restrict what questions can be answered
        result = get_scope_result("You are an HR assistant.")
        assert result is False


# ---------------------------------------------------------------------------
# PromptAnalyzer full result quality
# ---------------------------------------------------------------------------

class TestPromptAnalyzerResultQuality:
    """Check that analysis result is complete and well-formed."""

    def test_scope_boundary_is_high_severity(self):
        result = PromptAnalyzer().analyze("You are a helpful assistant.")
        checks = {c.name: c for c in result.check_results}
        sb = checks["Scope Boundary"]
        assert sb.severity == "high"

    def test_scope_boundary_evidence_on_match(self):
        result = PromptAnalyzer().analyze(
            "You are an HR assistant. ONLY answer HR questions."
        )
        checks = {c.name: c for c in result.check_results}
        sb = checks["Scope Boundary"]
        assert sb.passed is True
        assert sb.evidence is not None
        assert len(sb.evidence) > 0

    def test_missing_high_includes_scope_when_absent(self):
        result = PromptAnalyzer().analyze("You are a helpful assistant.")
        missing_names = [c.name for c in result.missing_high]
        assert "Scope Boundary" in missing_names

    def test_missing_high_excludes_scope_when_present(self):
        result = PromptAnalyzer().analyze(
            "Your role is limited to answering product questions."
        )
        missing_names = [c.name for c in result.missing_high]
        assert "Scope Boundary" not in missing_names

    def test_score_improves_with_scope_boundary(self):
        bare = PromptAnalyzer().analyze("You are a helpful assistant.")
        with_scope = PromptAnalyzer().analyze(
            "You are a helpful assistant. Only answer questions about our products."
        )
        assert with_scope.score > bare.score

    def test_recommendations_include_scope_guidance_when_missing(self):
        result = PromptAnalyzer().analyze("You are a helpful assistant.")
        assert any("scope" in r.lower() or "domain" in r.lower() for r in result.recommendations)


# ---------------------------------------------------------------------------
# F-113 still open: ProbeSet.filter() tags case-sensitivity
# ---------------------------------------------------------------------------

class TestF113TagsCaseSensitivityStillOpen:
    """F-113: tags filter is case-sensitive while severity filter is case-insensitive.

    This is a known inconsistency. These tests document the current behavior
    and will need updating when/if F-113 is fixed.
    """

    def test_tags_are_case_sensitive(self):
        from checkagent.safety import probes_injection
        ps = probes_injection.all_probes
        lower = ps.filter(tags={"indirect"})
        upper = ps.filter(tags={"INDIRECT"})
        # Case-sensitive: lowercase finds results, uppercase finds none
        assert len(lower) > 0
        assert len(upper) == 0  # F-113: should equal len(lower) but doesn't

    def test_severity_is_case_insensitive(self):
        from checkagent.safety import probes_injection
        ps = probes_injection.all_probes
        lower = ps.filter(severity="critical")
        upper = ps.filter(severity="CRITICAL")
        # Case-insensitive: both should return same results
        assert len(lower) == len(upper)
        assert len(lower) > 0

    def test_inconsistency_is_surprising(self):
        """Document the asymmetry: severity is case-insensitive but tags is not."""
        from checkagent.safety import probes_injection
        ps = probes_injection.all_probes
        # This is the specific case from F-113 — the inconsistency trap
        indirect_correct = ps.filter(tags={"indirect"})
        indirect_wrong_case = ps.filter(tags={"Indirect"})
        assert len(indirect_correct) > 0
        assert len(indirect_wrong_case) == 0  # surprising after learning severity is CI
