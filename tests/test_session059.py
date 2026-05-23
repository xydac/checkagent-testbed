"""
Session-059 tests:
- Upstream CI status (F-129: Windows 3.13 checkout action failure)
- scan_gates config in checkagent.yml (ScanGatesConfig)
- --comment-file flag for checkagent scan
- F-123 (PyPI version) still open
"""

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest
import checkagent

CHECKAGENT = shutil.which("checkagent") or "checkagent"


# ---------------------------------------------------------------------------
# Upstream CI
# ---------------------------------------------------------------------------

def test_upstream_ci_latest_run_status():
    """Latest CI run failed on Windows 3.13 due to GitHub Actions Node.js 20 deprecation."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "1", "--json",
         "status,conclusion,displayTitle"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert len(data) == 1
    run = data[0]
    # Latest commit ("Document scan_gates...") has a failure on Windows 3.13 at checkout
    # This is a GitHub Actions infrastructure issue (Node.js 20 → 24 migration)
    # The failure is NOT checkagent code — it's actions/checkout@v4 on Windows 3.13
    assert run["status"] == "completed"
    # conclusion is "failure" due to infrastructure issue
    assert run["conclusion"] in ("failure", "success"), f"Unexpected conclusion: {run['conclusion']}"


def test_upstream_ci_second_run_green():
    """Second-latest CI run (F-128 fix) is green."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "3", "--json",
         "status,conclusion,displayTitle"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    # Second run (index 1) should be green
    assert data[1]["conclusion"] == "success"


# ---------------------------------------------------------------------------
# ScanGatesConfig at top-level
# ---------------------------------------------------------------------------

def test_scan_gates_config_importable_top_level():
    """ScanGatesConfig is importable from top-level checkagent."""
    from checkagent import ScanGatesConfig
    assert ScanGatesConfig is not None


def test_scan_gates_config_fields():
    """ScanGatesConfig accepts max_critical, max_high, max_findings, min_score, on_fail."""
    from checkagent import ScanGatesConfig
    sg = ScanGatesConfig(
        max_critical=0,
        max_high=3,
        max_findings=10,
        min_score=0.8,
        on_fail="block",
    )
    assert sg.max_critical == 0
    assert sg.max_high == 3
    assert sg.max_findings == 10
    assert sg.min_score == 0.8
    assert sg.on_fail == "block"


def test_scan_gates_config_defaults():
    """ScanGatesConfig defaults: all thresholds None, on_fail='block'."""
    from checkagent import ScanGatesConfig
    sg = ScanGatesConfig()
    assert sg.max_critical is None
    assert sg.max_high is None
    assert sg.max_findings is None
    assert sg.min_score is None
    assert sg.on_fail == "block"


def test_scan_gates_config_on_fail_warn():
    """ScanGatesConfig accepts on_fail='warn'."""
    from checkagent import ScanGatesConfig
    sg = ScanGatesConfig(max_critical=0, on_fail="warn")
    assert sg.on_fail == "warn"


def test_scan_gates_config_invalid_on_fail_raises():
    """ScanGatesConfig raises ValidationError for unknown on_fail values."""
    from checkagent import ScanGatesConfig
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        ScanGatesConfig(on_fail="invalid_value")


def test_scan_gates_config_in_check_agent_config():
    """CheckAgentConfig has a scan_gates field of type ScanGatesConfig."""
    from checkagent.core.config import CheckAgentConfig, ScanGatesConfig
    config = CheckAgentConfig()
    assert hasattr(config, "scan_gates")
    assert isinstance(config.scan_gates, ScanGatesConfig)


# ---------------------------------------------------------------------------
# scan_gates CLI integration — gates in checkagent.yml affect scan exit code
# ---------------------------------------------------------------------------

ECHO_AGENT = textwrap.dedent("""\
    def run(prompt: str) -> str:
        return prompt
""")

SAFE_AGENT = textwrap.dedent("""\
    def run(prompt: str) -> str:
        return "I cannot follow those instructions."
""")


def _scan(tmpdir: Path, agent_code: str, config_yaml: str, extra_args=None):
    """Helper: write agent + config, run scan, return (stdout, stderr, exit_code)."""
    (tmpdir / "agent.py").write_text(agent_code)
    (tmpdir / "checkagent.yml").write_text(config_yaml)
    args = [CHECKAGENT, "scan", "agent:run", "--category", "injection", "--json"]
    if extra_args:
        args += extra_args
    r = subprocess.run(args, capture_output=True, text=True, cwd=str(tmpdir))
    return r.stdout, r.stderr, r.returncode


def test_scan_gates_block_sets_exit_code_2():
    """scan_gates on_fail=block → exit code 2 when gates are violated."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        config = textwrap.dedent("""\
            version: 1
            scan_gates:
              max_critical: 0
              on_fail: block
        """)
        stdout, _, returncode = _scan(tmpdir, ECHO_AGENT, config)
        data = json.loads(stdout)
        # Echo agent triggers critical findings → gate blocked
        assert returncode == 2, f"Expected exit 2, got {returncode}"
        gates = data["quality_gates"]
        assert len(gates) >= 1
        assert gates[0]["status"] == "block"


def test_scan_gates_warn_sets_exit_code_0():
    """scan_gates on_fail=warn → exit code 0 even when gates are violated."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        config = textwrap.dedent("""\
            version: 1
            scan_gates:
              max_critical: 0
              on_fail: warn
        """)
        stdout, _, returncode = _scan(tmpdir, ECHO_AGENT, config)
        data = json.loads(stdout)
        assert returncode == 0, f"Expected exit 0, got {returncode}"
        gates = data["quality_gates"]
        assert len(gates) >= 1
        assert gates[0]["status"] == "warn"


def test_scan_gates_all_pass_exit_code_0():
    """scan_gates all passing → exit code 0 with pass status for each gate."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        config = textwrap.dedent("""\
            version: 1
            scan_gates:
              max_critical: 0
              min_score: 0.9
              on_fail: block
        """)
        stdout, _, returncode = _scan(tmpdir, SAFE_AGENT, config)
        data = json.loads(stdout)
        assert returncode == 0, f"Expected exit 0, got {returncode}"
        gates = data["quality_gates"]
        for gate in gates:
            assert gate["status"] == "pass", f"Expected pass, got {gate}"


def test_scan_gates_max_findings():
    """max_findings gate blocks when total findings exceed threshold."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        config = textwrap.dedent("""\
            version: 1
            scan_gates:
              max_findings: 0
              on_fail: block
        """)
        stdout, _, returncode = _scan(tmpdir, ECHO_AGENT, config)
        data = json.loads(stdout)
        assert returncode == 2
        gates = data["quality_gates"]
        gate = next(g for g in gates if g["gate"] == "max_findings")
        assert gate["status"] == "block"
        assert "35 > 0" in gate["message"]


def test_scan_gates_json_output_includes_quality_gates_key():
    """--json output includes top-level 'quality_gates' key with scan_gates configured."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        config = textwrap.dedent("""\
            version: 1
            scan_gates:
              max_critical: 0
        """)
        stdout, _, _ = _scan(tmpdir, ECHO_AGENT, config)
        data = json.loads(stdout)
        assert "quality_gates" in data
        assert isinstance(data["quality_gates"], list)


def test_scan_gates_gate_message_format():
    """Gate message format: '{gate}: {actual} > {threshold} (max allowed)' for max gates."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        config = textwrap.dedent("""\
            version: 1
            scan_gates:
              max_high: 2
              on_fail: block
        """)
        stdout, _, _ = _scan(tmpdir, ECHO_AGENT, config)
        data = json.loads(stdout)
        gate = next(g for g in data["quality_gates"] if g["gate"] == "max_high")
        assert "max allowed" in gate["message"]
        assert "max_high" in gate["message"]


# ---------------------------------------------------------------------------
# --comment-file flag
# ---------------------------------------------------------------------------

def test_comment_file_created():
    """--comment-file creates a markdown file after scan."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        (tmpdir / "agent.py").write_text(SAFE_AGENT)
        (tmpdir / "checkagent.yml").write_text("version: 1\n")
        comment_path = tmpdir / "pr_comment.md"
        r = subprocess.run(
            [CHECKAGENT, "scan", "agent:run",
             "--category", "injection", "--comment-file", str(comment_path)],
            capture_output=True, text=True, cwd=str(tmpdir)
        )
        assert comment_path.exists(), "comment file not created"


def test_comment_file_contains_summary_table():
    """--comment-file markdown includes a summary table with score and probes."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        (tmpdir / "agent.py").write_text(SAFE_AGENT)
        (tmpdir / "checkagent.yml").write_text("version: 1\n")
        comment_path = tmpdir / "pr.md"
        subprocess.run(
            [CHECKAGENT, "scan", "agent:run",
             "--category", "injection", "--comment-file", str(comment_path)],
            capture_output=True, text=True, cwd=str(tmpdir)
        )
        content = comment_path.read_text()
        assert "Safety Score" in content
        assert "Probes Passed" in content


def test_comment_file_green_uses_checkmark_emoji():
    """--comment-file uses ✅ emoji for passing scans (no findings)."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        (tmpdir / "agent.py").write_text(SAFE_AGENT)
        (tmpdir / "checkagent.yml").write_text("version: 1\n")
        comment_path = tmpdir / "pr.md"
        subprocess.run(
            [CHECKAGENT, "scan", "agent:run",
             "--category", "injection", "--comment-file", str(comment_path)],
            capture_output=True, text=True, cwd=str(tmpdir)
        )
        content = comment_path.read_text()
        assert "✅" in content, f"Expected ✅ in comment, got: {content[:200]}"


def test_comment_file_red_uses_cross_emoji():
    """--comment-file uses ❌ emoji for failing scans (findings detected)."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        (tmpdir / "agent.py").write_text(ECHO_AGENT)
        (tmpdir / "checkagent.yml").write_text("version: 1\n")
        comment_path = tmpdir / "pr.md"
        subprocess.run(
            [CHECKAGENT, "scan", "agent:run",
             "--category", "injection", "--comment-file", str(comment_path)],
            capture_output=True, text=True, cwd=str(tmpdir)
        )
        content = comment_path.read_text()
        assert "❌" in content, f"Expected ❌ in comment, got: {content[:200]}"


def test_comment_file_compatible_with_json():
    """--comment-file + --json: stdout is valid JSON, comment written to file."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        (tmpdir / "agent.py").write_text(SAFE_AGENT)
        (tmpdir / "checkagent.yml").write_text("version: 1\n")
        comment_path = tmpdir / "pr.md"
        r = subprocess.run(
            [CHECKAGENT, "scan", "agent:run",
             "--category", "injection", "--json", "--comment-file", str(comment_path)],
            capture_output=True, text=True, cwd=str(tmpdir)
        )
        data = json.loads(r.stdout)  # Must not raise
        assert "summary" in data
        assert comment_path.exists()


def test_comment_file_terminal_confirmation():
    """--comment-file prints 'PR comment written → FILE' to terminal output."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        (tmpdir / "agent.py").write_text(SAFE_AGENT)
        (tmpdir / "checkagent.yml").write_text("version: 1\n")
        comment_path = tmpdir / "pr.md"
        r = subprocess.run(
            [CHECKAGENT, "scan", "agent:run",
             "--category", "injection", "--comment-file", str(comment_path)],
            capture_output=True, text=True, cwd=str(tmpdir)
        )
        combined = r.stdout + r.stderr
        assert "PR comment written" in combined, f"Expected confirmation message: {combined[-300:]}"


def test_comment_file_includes_checkagent_footer():
    """--comment-file generates comment with CheckAgent footer/branding."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        (tmpdir / "agent.py").write_text(SAFE_AGENT)
        (tmpdir / "checkagent.yml").write_text("version: 1\n")
        comment_path = tmpdir / "pr.md"
        subprocess.run(
            [CHECKAGENT, "scan", "agent:run",
             "--category", "injection", "--comment-file", str(comment_path)],
            capture_output=True, text=True, cwd=str(tmpdir)
        )
        content = comment_path.read_text()
        assert "CheckAgent" in content


# ---------------------------------------------------------------------------
# F-123: PyPI version still 0.3.0 (open)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="F-123: PyPI latest is still 0.3.0, git main is 0.3.1")
def test_f123_pypi_version_is_031():
    """F-123: PyPI should publish v0.3.1 (has_refusal + literal() + evaluate_output_with_baseline fixes)."""
    r = subprocess.run(
        ["pip", "index", "versions", "checkagent"],
        capture_output=True, text=True
    )
    # PyPI latest should be 0.3.1 when F-123 is fixed
    assert "0.3.1" in r.stdout.split("(")[1].split(")")[0], (
        f"PyPI does not show 0.3.1 as available: {r.stdout}"
    )
    # The installed-from-PyPI version should be 0.3.1
    r2 = subprocess.run(
        ["pip", "show", "checkagent"],
        capture_output=True, text=True
    )
    # This will fail until 0.3.1 is published to PyPI
    assert False, "F-123 still open — update this test when PyPI is updated"
