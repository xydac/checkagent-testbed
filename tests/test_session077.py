"""Session 077 — probe-list command, F-067 fix verification, probe-list DX findings."""
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
# probe-list: basic output
# ---------------------------------------------------------------------------

class TestProbeListBasic:
    def test_command_exists_in_help(self):
        result = run_cli("--help")
        assert "probe-list" in result.stdout

    def test_default_output_shows_all_categories(self):
        result = run_cli("probe-list")
        assert result.returncode == 0
        for cat in ["prompt_injection", "jailbreak", "pii_leakage", "scope_boundary", "data_enumeration", "groundedness"]:
            assert cat in result.stdout

    def test_default_output_shows_total_probe_count(self):
        result = run_cli("probe-list")
        assert "101 total" in result.stdout

    def test_default_output_shows_owasp_references(self):
        result = run_cli("probe-list")
        assert "LLM01" in result.stdout
        assert "LLM06" in result.stdout
        assert "LLM09" in result.stdout

    def test_default_output_shows_scan_tip(self):
        result = run_cli("probe-list")
        assert "checkagent scan" in result.stdout


# ---------------------------------------------------------------------------
# probe-list: --json output
# ---------------------------------------------------------------------------

class TestProbeListJson:
    def test_json_is_valid(self):
        result = run_cli("probe-list", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "total_probes" in data
        assert "categories" in data

    def test_json_total_probes_is_101(self):
        result = run_cli("probe-list", "--json")
        data = json.loads(result.stdout)
        assert data["total_probes"] == 101

    def test_json_total_probes_matches_sum_of_counts(self):
        result = run_cli("probe-list", "--json")
        data = json.loads(result.stdout)
        total = data["total_probes"]
        sum_counts = sum(c["count"] for c in data["categories"])
        assert total == sum_counts

    def test_json_has_6_categories(self):
        result = run_cli("probe-list", "--json")
        data = json.loads(result.stdout)
        assert len(data["categories"]) == 6

    def test_json_category_has_required_fields(self):
        result = run_cli("probe-list", "--json")
        data = json.loads(result.stdout)
        for cat in data["categories"]:
            assert "name" in cat
            assert "count" in cat
            assert "description" in cat
            assert "owasp" in cat
            assert "examples" in cat

    def test_json_examples_empty_without_flag(self):
        result = run_cli("probe-list", "--json")
        data = json.loads(result.stdout)
        for cat in data["categories"]:
            assert cat["examples"] == []

    def test_json_examples_populated_with_flag(self):
        result = run_cli("probe-list", "--examples", "--json")
        data = json.loads(result.stdout)
        for cat in data["categories"]:
            assert len(cat["examples"]) > 0, f"Category {cat['name']} has no examples"

    def test_json_category_names(self):
        result = run_cli("probe-list", "--json")
        data = json.loads(result.stdout)
        names = {c["name"] for c in data["categories"]}
        assert names == {"prompt_injection", "jailbreak", "pii_leakage", "scope_boundary", "data_enumeration", "groundedness"}


# ---------------------------------------------------------------------------
# probe-list: --category filter
# ---------------------------------------------------------------------------

class TestProbeListCategoryFilter:
    def test_category_injection_short_alias(self):
        result = run_cli("probe-list", "--category", "injection")
        assert result.returncode == 0
        assert "prompt_injection" in result.stdout
        assert "jailbreak" not in result.stdout

    def test_category_prompt_injection_full_name(self):
        result = run_cli("probe-list", "--category", "prompt_injection")
        assert result.returncode == 0
        assert "prompt_injection" in result.stdout

    def test_category_pii_short_alias(self):
        result = run_cli("probe-list", "--category", "pii")
        assert result.returncode == 0
        assert "pii_leakage" in result.stdout

    def test_category_scope_short_alias(self):
        result = run_cli("probe-list", "--category", "scope")
        assert result.returncode == 0
        assert "scope_boundary" in result.stdout

    def test_category_jailbreak(self):
        result = run_cli("probe-list", "--category", "jailbreak")
        assert result.returncode == 0
        assert "jailbreak" in result.stdout
        assert "15 total" in result.stdout

    def test_category_groundedness(self):
        result = run_cli("probe-list", "--category", "groundedness")
        assert result.returncode == 0
        assert "groundedness" in result.stdout
        assert "8 total" in result.stdout

    def test_invalid_category_exits_nonzero(self):
        result = run_cli("probe-list", "--category", "nonexistent")
        assert result.returncode != 0

    def test_invalid_category_shows_valid_options(self):
        result = run_cli("probe-list", "--category", "nonexistent")
        assert "Valid categories" in result.stderr

    def test_category_filter_json(self):
        result = run_cli("probe-list", "--category", "injection", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data["categories"]) == 1
        assert data["categories"][0]["name"] == "prompt_injection"
        assert data["categories"][0]["count"] == 35


# ---------------------------------------------------------------------------
# probe-list: --examples flag
# ---------------------------------------------------------------------------

class TestProbeListExamples:
    def test_examples_section_appears(self):
        result = run_cli("probe-list", "--examples")
        assert result.returncode == 0
        assert "Example Probe Inputs" in result.stdout

    def test_examples_include_injection_probe(self):
        result = run_cli("probe-list", "--examples")
        assert "Ignore all previous instructions" in result.stdout

    def test_examples_with_category_filter(self):
        result = run_cli("probe-list", "--category", "injection", "--examples")
        assert result.returncode == 0
        assert "prompt_injection" in result.stdout
        assert "Ignore all previous instructions" in result.stdout

    def test_examples_category_filter_excludes_others(self):
        result = run_cli("probe-list", "--category", "injection", "--examples")
        assert "pii_leakage" not in result.stdout
        assert "jailbreak" not in result.stdout


# ---------------------------------------------------------------------------
# F-067 FIXED: trace import classes now at top-level checkagent
# ---------------------------------------------------------------------------

class TestF067Fixed:
    """F-067 is fixed — TraceImporter, JsonFileImporter, OtelJsonImporter, PiiScrubber all at top-level."""

    def test_json_file_importer_at_top_level(self):
        import checkagent
        assert hasattr(checkagent, "JsonFileImporter")

    def test_otel_importer_at_top_level(self):
        import checkagent
        assert hasattr(checkagent, "OtelJsonImporter")

    def test_pii_scrubber_at_top_level(self):
        import checkagent
        assert hasattr(checkagent, "PiiScrubber")

    def test_trace_importer_at_top_level(self):
        import checkagent
        assert hasattr(checkagent, "TraceImporter")


# ---------------------------------------------------------------------------
# probe-list DX finding: category name inconsistency in error message
# ---------------------------------------------------------------------------

class TestProbeListCategoryNameConsistency:
    """The error message for invalid category shows short aliases that don't match
    the full category names shown in --json output. This is a DX gap (F-157)."""

    def test_json_category_name_prompt_injection_is_full_name(self):
        # JSON output uses full name "prompt_injection"
        result = run_cli("probe-list", "--json")
        data = json.loads(result.stdout)
        names = [c["name"] for c in data["categories"]]
        assert "prompt_injection" in names

    def test_full_name_accepted_in_category_filter(self):
        # Full names from JSON work as --category values (good!)
        result = run_cli("probe-list", "--category", "prompt_injection")
        assert result.returncode == 0

    def test_error_message_shows_full_category_names(self):
        # F-157 FIXED in v1.5.0: error now shows "full_name (alias)" format
        result = run_cli("probe-list", "--category", "nonexistent")
        error = result.stderr
        # Error shows both full name and alias: "prompt_injection (injection)"
        assert "prompt_injection" in error, f"Error shows: {error}"
