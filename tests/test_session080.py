"""Session-080 tests: v1.6.0 upgrade, F-159/F-160 fixed, F-079 test corrected."""
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# v1.6.0 upgrade confirmation
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_v160_installed():
    """v1.6.0 is the installed version from git main."""
    import checkagent
    assert checkagent.__version__ == "1.6.0"


@pytest.mark.agent_test
def test_upstream_ci_green():
    """Upstream CI is green on the v1.6.0 bump commit."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "3", "--json",
         "conclusion,displayTitle"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    runs = json.loads(result.stdout)
    assert runs[0]["conclusion"] == "success", (
        f"Latest CI run should be green, got: {runs[0]['conclusion']} "
        f"for '{runs[0]['displayTitle']}'"
    )


# ---------------------------------------------------------------------------
# F-159: category_delta now in diff --json output (FIXED in v1.6.0)
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f159_category_delta_in_diff_json():
    """F-159 FIXED: diff --json now includes category_delta key at top level."""
    agents_dir = Path(__file__).parent.parent / "agents"
    echo_agent = str(agents_dir / "echo_agent.py") + ":echo_agent"

    # Run a scan to get current JSON output
    scan_result = subprocess.run(
        ["checkagent", "scan", echo_agent, "--json"],
        capture_output=True, text=True,
    )
    # Save scan output for diffing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(scan_result.stdout)
        scan_file = f.name

    # Diff the scan against itself — category_delta should show zeros
    diff_result = subprocess.run(
        ["checkagent", "diff", scan_file, scan_file, "--json"],
        capture_output=True, text=True,
    )
    assert diff_result.returncode == 0, f"diff command failed: {diff_result.stderr}"
    data = json.loads(diff_result.stdout)

    assert "category_delta" in data, (
        f"F-159 regression: category_delta missing from diff JSON. Keys: {list(data.keys())}"
    )


@pytest.mark.agent_test
def test_f159_category_delta_structure():
    """category_delta has correct per-category structure with baseline/current/delta."""
    agents_dir = Path(__file__).parent.parent / "agents"
    echo_agent = str(agents_dir / "echo_agent.py") + ":echo_agent"

    scan_result = subprocess.run(
        ["checkagent", "scan", echo_agent, "--json"],
        capture_output=True, text=True,
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(scan_result.stdout)
        scan_file = f.name

    diff_result = subprocess.run(
        ["checkagent", "diff", scan_file, scan_file, "--json"],
        capture_output=True, text=True,
    )
    data = json.loads(diff_result.stdout)
    category_delta = data.get("category_delta", {})

    assert isinstance(category_delta, dict), "category_delta should be a dict"
    assert len(category_delta) > 0, "category_delta should have at least one category"

    # Each entry should have baseline, current, delta
    for cat_name, entry in category_delta.items():
        assert "baseline" in entry, f"category_delta[{cat_name}] missing 'baseline'"
        assert "current" in entry, f"category_delta[{cat_name}] missing 'current'"
        assert "delta" in entry, f"category_delta[{cat_name}] missing 'delta'"
        # Self-diff should have delta=0
        assert entry["delta"] == 0, (
            f"Self-diff should have delta=0 for {cat_name}, got {entry['delta']}"
        )


@pytest.mark.agent_test
def test_f159_scan_diff_flag_also_has_category_delta():
    """scan --diff --json also exposes category_delta in the diff key."""
    agents_dir = Path(__file__).parent.parent / "agents"
    echo_agent = str(agents_dir / "echo_agent.py") + ":echo_agent"

    result = subprocess.run(
        ["checkagent", "scan", echo_agent, "--diff", "--json"],
        capture_output=True, text=True,
    )
    # scan --diff may fail if no history yet, that's OK
    if result.returncode != 0:
        pytest.skip("No scan history available for --diff test")

    data = json.loads(result.stdout)
    diff_key = data.get("diff", {})
    assert "category_delta" in diff_key, (
        f"F-159: scan --diff --json 'diff' key missing category_delta. "
        f"diff keys: {list(diff_key.keys())}"
    )


# ---------------------------------------------------------------------------
# F-160: probe-list --verbose --examples duplication FIXED in v1.6.0
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_f160_probe_list_verbose_examples_not_duplicated():
    """F-160 FIXED: --verbose --examples together no longer duplicates all probes in examples."""
    result = subprocess.run(
        ["checkagent", "probe-list",
         "--verbose", "--examples", "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    cats = data.get("categories", [])
    assert len(cats) > 0

    for cat in cats:
        examples = cat.get("examples", [])
        probes = cat.get("probes", [])
        # With F-160 fix: examples should be limited (3) not equal to all probes
        assert len(examples) <= 3, (
            f"F-160 regression in {cat['name']}: examples count {len(examples)} "
            f"should be <=3 when --examples used alongside --verbose"
        )
        # probes should have the full list
        assert len(probes) > 3, (
            f"{cat['name']}: probes count {len(probes)} should be >3 in --verbose mode"
        )


@pytest.mark.agent_test
def test_f160_verbose_only_shows_all_probes():
    """--verbose alone: probes key has full probe list; examples stays at default (<=3)."""
    result = subprocess.run(
        ["checkagent", "probe-list", "--verbose", "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    cats = data.get("categories", [])

    for cat in cats:
        probes = cat.get("probes", [])
        examples = cat.get("examples", [])
        # probes should have the full list in --verbose mode
        assert len(probes) > 0, f"{cat['name']}: probes should be present in --verbose mode"
        # examples stays at default (3) regardless of --verbose
        assert len(examples) <= 3, (
            f"{cat['name']}: examples should be <=3 without --examples flag, "
            f"got {len(examples)}"
        )
        # Key invariant: probes count should be > examples count (not equal)
        assert len(probes) > len(examples), (
            f"F-160: {cat['name']}: probes ({len(probes)}) should exceed "
            f"examples ({len(examples)}) in --verbose mode"
        )


@pytest.mark.agent_test
def test_f160_examples_only_no_probes_field():
    """--examples alone: examples key has <=3 items; probes key is absent/empty."""
    result = subprocess.run(
        ["checkagent", "probe-list", "--examples", "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    cats = data.get("categories", [])

    for cat in cats:
        examples = cat.get("examples", [])
        probes = cat.get("probes", [])
        assert len(examples) <= 3, f"{cat['name']}: examples should be <=3 without --verbose"
        assert len(probes) == 0, (
            f"{cat['name']}: probes should be empty without --verbose flag, got {len(probes)}"
        )


# ---------------------------------------------------------------------------
# F-079 test update: test that the fix is permanent
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_f079_double_attach_fix_confirmed_in_v160():
    """F-079 confirmed still fixed in v1.6.0: second attach_faults() raises ValueError."""
    from checkagent import MockTool, FaultInjector

    fi1 = FaultInjector()
    fi1.on_tool("search").timeout()

    fi2 = FaultInjector()
    fi2.on_tool("book").rate_limit()

    tool = MockTool()
    tool.register("search", response={"result": "ok"},
                  schema={"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]})
    tool.register("book", response={"booked": True},
                  schema={"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]})

    tool.attach_faults(fi1)

    with pytest.raises(ValueError, match="FaultInjector is already attached"):
        tool.attach_faults(fi2)

    # idempotent: same injector is fine
    tool.attach_faults(fi1)


# ---------------------------------------------------------------------------
# v1.6.0 PyPI release check
# ---------------------------------------------------------------------------

@pytest.mark.agent_test
def test_v160_on_pypi():
    """v1.6.0 is available on PyPI (not just git main)."""
    result = subprocess.run(
        ["pip", "index", "versions", "checkagent"],
        capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    assert "1.6.0" in output, (
        f"v1.6.0 should be on PyPI. pip output: {output[:200]}"
    )
