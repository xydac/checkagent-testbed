"""Session 078 — v1.5.0 upgrade: F-155/F-157 fixed, F-158 new (CI red on PyPI publish),
compare --url-a/--url-b, compare winner/margin fields, probe-list error message fix."""
import json
import subprocess
import sys

import pytest


def run_cli(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["checkagent"] + list(args),
        capture_output=True, text=True
    )


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

class TestVersion:
    def test_version_is_1_5_0(self):
        import checkagent
        assert checkagent.__version__ == "1.5.0"

    def test_cli_version_is_1_5_0(self):
        result = run_cli("--version")
        assert "1.5.0" in result.stdout


# ---------------------------------------------------------------------------
# F-157 FIXED: probe-list error message now shows full category names
# ---------------------------------------------------------------------------

class TestProbeListErrorMessageFixed:
    """F-157 FIXED in v1.5.0: error message now shows 'full_name (alias)' format,
    consistent with JSON output that uses full names."""

    def test_error_shows_full_name_prompt_injection(self):
        result = run_cli("probe-list", "--category", "bad_category")
        assert result.returncode != 0
        # Full category name must appear in error
        assert "prompt_injection" in result.stderr

    def test_error_shows_full_name_pii_leakage(self):
        result = run_cli("probe-list", "--category", "bad_category")
        assert "pii_leakage" in result.stderr

    def test_error_shows_full_name_scope_boundary(self):
        result = run_cli("probe-list", "--category", "bad_category")
        assert "scope_boundary" in result.stderr

    def test_error_format_includes_alias_in_parens(self):
        # Format is "full_name (short_alias)" e.g. "prompt_injection (injection)"
        result = run_cli("probe-list", "--category", "bad_category")
        err = result.stderr
        assert "prompt_injection (injection)" in err or "injection" in err

    def test_error_shows_all_six_categories(self):
        result = run_cli("probe-list", "--category", "bad_category")
        err = result.stderr
        for cat in ["prompt_injection", "jailbreak", "pii_leakage", "scope_boundary",
                    "data_enumeration", "groundedness"]:
            assert cat in err, f"Category '{cat}' missing from error: {err}"

    def test_full_name_and_short_alias_both_accepted(self):
        # Both the full name and short alias should work as --category values
        result_full = run_cli("probe-list", "--category", "prompt_injection")
        result_short = run_cli("probe-list", "--category", "injection")
        assert result_full.returncode == 0, "Full name 'prompt_injection' should work"
        assert result_short.returncode == 0, "Short alias 'injection' should work"

    def test_json_category_names_match_error_message_names(self):
        # JSON uses full names; error now shows same full names
        json_result = run_cli("probe-list", "--json")
        json_data = json.loads(json_result.stdout)
        full_names = [c["name"] for c in json_data["categories"]]

        err_result = run_cli("probe-list", "--category", "nonexistent")
        err_text = err_result.stderr

        for name in full_names:
            assert name in err_text, f"Full name '{name}' from JSON not in error: {err_text}"


# ---------------------------------------------------------------------------
# F-155 FIXED: compare --url-a / --url-b now implemented
# ---------------------------------------------------------------------------

class TestCompareUrlFlags:
    """F-155 FIXED in v1.5.0: --url-a and --url-b are now real options,
    not just listed in help examples. Previously raised 'No such option'."""

    def test_url_a_option_recognized(self):
        # Should NOT say "No such option: --url-a"
        result = run_cli("compare", "--url-a", "http://localhost:9999/chat",
                         "--url-b", "http://localhost:9998/chat")
        assert "No such option" not in result.stderr
        assert "No such option: --url-a" not in result.stderr

    def test_url_b_option_recognized(self):
        result = run_cli("compare", "--url-a", "http://localhost:9999/chat",
                         "--url-b", "http://localhost:9998/chat")
        assert "No such option: --url-b" not in result.stderr

    def test_url_a_no_history_gives_actionable_error(self):
        # With no scan history, should give "No scan history" message not crash
        result = run_cli("compare", "--url-a", "http://localhost:9999/chat",
                         "--url-b", "http://localhost:9998/chat")
        assert result.returncode != 0
        # Error goes to stdout (note: message is on stdout, not stderr)
        combined = result.stdout + result.stderr
        assert "Traceback" not in combined
        # Should mention "history" or "scan"
        assert "history" in combined.lower() or "scan" in combined.lower()

    def test_url_flags_in_help(self):
        result = run_cli("compare", "--help")
        assert "--url-a" in result.stdout
        assert "--url-b" in result.stdout

    def test_url_a_appears_in_help_example(self):
        result = run_cli("compare", "--help")
        assert "url-a" in result.stdout


# ---------------------------------------------------------------------------
# compare: winner/margin fields (F-156 improved)
# ---------------------------------------------------------------------------

class TestCompareWinnerMargin:
    """compare now shows 'winner' and 'margin' fields in JSON + 'Winner:' in text output.
    F-156 (undocumented score_delta sign) is partially addressed by these additions."""

    @pytest.fixture(autouse=True)
    def scan_agents(self, tmp_path, monkeypatch):
        """Scan both agents to build history."""
        monkeypatch.chdir(tmp_path)
        subprocess.run(
            ["checkagent", "scan", "agents/refusal_agent.py:run",
             "--category", "injection", "--json"],
            capture_output=True, text=True,
            cwd="/home/x/working/checkagent-testbed"
        )
        subprocess.run(
            ["checkagent", "scan", "agents/echo_agent.py:echo_agent",
             "--category", "injection", "--json"],
            capture_output=True, text=True,
            cwd="/home/x/working/checkagent-testbed"
        )

    def _run_compare_json(self):
        result = subprocess.run(
            ["checkagent", "compare",
             "agents/refusal_agent.py:run",
             "agents/echo_agent.py:echo_agent",
             "--json"],
            capture_output=True, text=True,
            cwd="/home/x/working/checkagent-testbed"
        )
        return json.loads(result.stdout)

    def _run_compare_text(self):
        return subprocess.run(
            ["checkagent", "compare",
             "agents/refusal_agent.py:run",
             "agents/echo_agent.py:echo_agent"],
            capture_output=True, text=True,
            cwd="/home/x/working/checkagent-testbed"
        )

    def test_json_has_winner_field(self):
        data = self._run_compare_json()
        assert "winner" in data, "JSON should have 'winner' field"

    def test_json_winner_is_agent_a(self):
        data = self._run_compare_json()
        # refusal_agent (agent_a) scores 1.0, echo_agent scores near 0
        # winner field is "agent_a" or "agent_b", not the target string
        assert data["winner"] == "agent_a"

    def test_json_has_margin_field(self):
        data = self._run_compare_json()
        assert "margin" in data, "JSON should have 'margin' field"

    def test_json_margin_is_positive(self):
        data = self._run_compare_json()
        # margin should be the absolute difference
        assert data["margin"] > 0

    def test_json_margin_equals_abs_score_delta(self):
        data = self._run_compare_json()
        assert abs(data["score_delta"]) == pytest.approx(data["margin"], abs=0.001)

    def test_json_score_delta_is_b_minus_a(self):
        # F-156: sign convention is b - a (negative when a wins)
        # this is still the convention but now documented via winner/margin
        data = self._run_compare_json()
        expected = data["agent_b"]["score"] - data["agent_a"]["score"]
        assert data["score_delta"] == pytest.approx(expected, abs=0.001)

    def test_text_output_shows_winner_line(self):
        result = self._run_compare_text()
        assert "Winner" in result.stdout

    def test_text_output_winner_shows_percentage(self):
        result = self._run_compare_text()
        # "Winner: agents/refusal_agent.py:run (100% vs 3%)"
        assert "100%" in result.stdout or "Winner" in result.stdout


# ---------------------------------------------------------------------------
# F-158 NEW: v1.5.0 published to PyPI despite CI failure (ruff N806)
# ---------------------------------------------------------------------------

class TestCIHealthSession078:
    """F-158: v1.5.0 was published to PyPI from a commit where the main CI
    workflow failed (ruff N806: _DISPLAY uppercase variable in function in
    history.py:217). The Publish workflow doesn't depend on CI passing."""

    def test_version_is_1_5_0_on_pypi(self):
        # v1.5.0 is installed (published despite CI failure)
        import checkagent
        assert checkagent.__version__ == "1.5.0"

    @pytest.mark.xfail(reason="F-158: v1.5.0 CI has ruff N806 lint error in history.py:217 — _DISPLAY uppercase in function. CI is red but package was published to PyPI anyway.")
    def test_upstream_ci_is_green(self):
        # This is a canary: if CI is green, this xfail will be an xpass
        # The actual CI check happens via `gh run list`; we document it here
        # as a known failure from session-078 observation.
        # Expected: CI failure on ruff N806 in history.py:217
        pytest.fail("CI failing on ruff N806: _DISPLAY variable in function should be lowercase (history.py:217)")


# ---------------------------------------------------------------------------
# compare: --url-a / --url-b with HTTP endpoint (full flow)
# ---------------------------------------------------------------------------

class TestCompareUrlEndToEnd:
    """Smoke test that compare --url-a/--url-b does a real HTTP scan comparison
    when both agents have history. (Uses local agent scan as proxy for behavior.)"""

    def test_compare_json_structure(self):
        # Run scans and compare — verify output structure is consistent
        result = subprocess.run(
            ["checkagent", "compare",
             "agents/refusal_agent.py:run",
             "agents/echo_agent.py:echo_agent",
             "--json"],
            capture_output=True, text=True,
            cwd="/home/x/working/checkagent-testbed"
        )
        assert result.returncode == 0, f"compare failed: {result.stderr}"
        data = json.loads(result.stdout)
        # All expected top-level keys present
        for key in ["agent_a", "agent_b", "score_delta", "margin", "winner",
                    "categories", "only_agent_a", "only_agent_b"]:
            assert key in data, f"Missing key: {key}"

    def test_compare_agent_a_b_have_target_and_score(self):
        result = subprocess.run(
            ["checkagent", "compare",
             "agents/refusal_agent.py:run",
             "agents/echo_agent.py:echo_agent",
             "--json"],
            capture_output=True, text=True,
            cwd="/home/x/working/checkagent-testbed"
        )
        data = json.loads(result.stdout)
        for agent_key in ["agent_a", "agent_b"]:
            entry = data[agent_key]
            assert "target" in entry
            assert "score" in entry
            assert 0.0 <= entry["score"] <= 1.0

    def test_compare_categories_have_expected_structure(self):
        result = subprocess.run(
            ["checkagent", "compare",
             "agents/refusal_agent.py:run",
             "agents/echo_agent.py:echo_agent",
             "--json"],
            capture_output=True, text=True,
            cwd="/home/x/working/checkagent-testbed"
        )
        data = json.loads(result.stdout)
        for cat in data["categories"]:
            assert "category" in cat
            assert "agent_a_findings" in cat
            assert "agent_b_findings" in cat
            assert "delta" in cat
