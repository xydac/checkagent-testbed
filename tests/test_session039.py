"""Session-039 tests: F-105 fix verification, --report HTML, groundedness scan, F-099 status."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


TESTBED_ROOT = Path(__file__).parent.parent
PYTHONPATH_ENV = {**os.environ, "PYTHONPATH": str(TESTBED_ROOT)}


def run_scan(*args, cwd=None):
    """Helper to run checkagent scan and return completed process."""
    return subprocess.run(
        ["checkagent", "scan", *args],
        capture_output=True,
        text=True,
        cwd=cwd or TESTBED_ROOT,
        env=PYTHONPATH_ENV,
    )


class TestF105WrapFixed:
    """F-105 FIXED: checkagent wrap now correctly instantiates class before calling .invoke()."""

    def test_wrap_generates_instantiated_class(self, tmp_path):
        """wrap creates _agent = _target() then _agent.invoke() — not unbound call."""
        agent_file = tmp_path / "my_class_agent.py"
        agent_file.write_text(
            'class MyAgent:\n    def invoke(self, text: str) -> str:\n        return f"ok: {text}"\n'
        )
        result = subprocess.run(
            ["checkagent", "wrap", "my_class_agent:MyAgent", "--force"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(tmp_path)},
        )
        assert result.returncode == 0, result.stderr
        wrapper = (tmp_path / "checkagent_target.py").read_text()
        # Must instantiate: _agent = _target()
        assert "_agent = _target()" in wrapper, "wrapper must instantiate the class"
        # Must call on instance: _agent.invoke(prompt)
        assert "_agent.invoke(prompt)" in wrapper, "wrapper must call on instance"
        # Must NOT use unbound call (the old broken pattern)
        assert "_target.invoke(prompt)" not in wrapper, "old broken pattern still present"

    def test_wrap_generated_wrapper_executes_successfully(self, tmp_path):
        """Generated wrapper actually runs without TypeError."""
        agent_file = tmp_path / "stateless_agent.py"
        agent_file.write_text(
            'class StatelessAgent:\n    def invoke(self, text: str) -> str:\n        return "safe response"\n'
        )
        subprocess.run(
            ["checkagent", "wrap", "stateless_agent:StatelessAgent", "--force"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(tmp_path)},
        )
        scan = subprocess.run(
            ["checkagent", "scan", "checkagent_target:checkagent_target",
             "--category", "injection", "--json"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(tmp_path)},
        )
        import json
        # Strip any diagnostic lines before JSON
        stdout = scan.stdout.strip()
        lines = stdout.split("\n")
        json_start = next(i for i, l in enumerate(lines) if l.startswith("{"))
        data = json.loads("\n".join(lines[json_start:]))
        assert data["summary"]["errors"] == 0, f"wrapper had errors: {data}"
        assert data["summary"]["total"] == 35

    def test_wrap_plain_function_still_says_no_wrapper_needed(self, tmp_path):
        """Plain functions still get 'No wrapper needed' message."""
        func_file = tmp_path / "plain_func.py"
        func_file.write_text(
            'async def my_agent(prompt: str) -> str:\n    return "pong"\n'
        )
        result = subprocess.run(
            ["checkagent", "wrap", "plain_func:my_agent"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(tmp_path)},
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "No wrapper needed" in combined or "scan directly" in combined.lower()


class TestScanReportHTML:
    """--report FILE generates an HTML compliance report."""

    def test_report_file_is_created(self):
        """--report flag creates an HTML file at the specified path."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            report_path = f.name
        try:
            result = run_scan(
                "agents.echo_agent:echo_agent",
                "--category", "injection",
                "--report", report_path,
            )
            assert Path(report_path).exists(), "HTML report file not created"
            assert Path(report_path).stat().st_size > 100, "HTML report is empty"
        finally:
            Path(report_path).unlink(missing_ok=True)

    def test_report_is_valid_html(self):
        """Generated report contains valid HTML structure."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            report_path = f.name
        try:
            run_scan(
                "agents.echo_agent:echo_agent",
                "--category", "injection",
                "--report", report_path,
            )
            html = Path(report_path).read_text()
            assert "<!DOCTYPE html>" in html
            assert "<html" in html
            assert "</html>" in html
            assert "<table" in html
        finally:
            Path(report_path).unlink(missing_ok=True)

    def test_report_contains_summary_stats(self):
        """HTML report includes scan summary stats."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            report_path = f.name
        try:
            run_scan(
                "agents.echo_agent:echo_agent",
                "--category", "injection",
                "--report", report_path,
            )
            html = Path(report_path).read_text()
            assert "Total safety tests" in html or "Probes" in html
            assert "Resistance" in html or "resistance" in html
        finally:
            Path(report_path).unlink(missing_ok=True)

    def test_report_contains_owasp_mapping(self):
        """HTML report includes OWASP LLM Top 10 regulatory mapping."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            report_path = f.name
        try:
            run_scan(
                "agents.echo_agent:echo_agent",
                "--category", "injection",
                "--report", report_path,
            )
            html = Path(report_path).read_text()
            assert "OWASP" in html
        finally:
            Path(report_path).unlink(missing_ok=True)

    def test_report_contains_eu_ai_act_mapping(self):
        """HTML report includes EU AI Act regulatory mapping."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            report_path = f.name
        try:
            run_scan(
                "agents.echo_agent:echo_agent",
                "--category", "injection",
                "--report", report_path,
            )
            html = Path(report_path).read_text()
            assert "EU AI Act" in html
        finally:
            Path(report_path).unlink(missing_ok=True)

    def test_report_works_alongside_json(self):
        """--report and --json flags work simultaneously."""
        import json
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            report_path = f.name
        try:
            result = run_scan(
                "agents.echo_agent:echo_agent",
                "--category", "injection",
                "--report", report_path,
                "--json",
            )
            # HTML file should exist
            assert Path(report_path).exists()
            html = Path(report_path).read_text()
            assert "<!DOCTYPE html>" in html
            # JSON should also be on stdout (may have diagnostic prefix line)
            stdout = result.stdout.strip()
            lines = stdout.split("\n")
            json_start = next((i for i, l in enumerate(lines) if l.startswith("{")), None)
            assert json_start is not None, "No JSON found in stdout"
            data = json.loads("\n".join(lines[json_start:]))
            assert "summary" in data
        finally:
            Path(report_path).unlink(missing_ok=True)

    def test_report_message_in_output(self):
        """Terminal output confirms report was written."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            report_path = f.name
        try:
            result = run_scan(
                "agents.echo_agent:echo_agent",
                "--category", "injection",
                "--report", report_path,
            )
            combined = result.stdout + result.stderr
            assert "report" in combined.lower() and report_path in combined
        finally:
            Path(report_path).unlink(missing_ok=True)


class TestGroundednessScanCategory:
    """groundedness is now a valid --category for checkagent scan."""

    def test_groundedness_category_runs_8_probes(self):
        """Groundedness scan runs exactly 8 probes."""
        import json
        result = run_scan(
            "agents.echo_agent:echo_agent",
            "--category", "groundedness",
            "--json",
        )
        stdout = result.stdout.strip()
        lines = stdout.split("\n")
        json_start = next((i for i, l in enumerate(lines) if l.startswith("{")), None)
        assert json_start is not None
        data = json.loads("\n".join(lines[json_start:]))
        assert data["summary"]["total"] == 8

    def test_groundedness_category_produces_no_errors(self):
        """Groundedness scan runs without errors on echo agent."""
        import json
        result = run_scan(
            "agents.echo_agent:echo_agent",
            "--category", "groundedness",
            "--json",
        )
        stdout = result.stdout.strip()
        lines = stdout.split("\n")
        json_start = next((i for i, l in enumerate(lines) if l.startswith("{")), None)
        data = json.loads("\n".join(lines[json_start:]))
        assert data["summary"]["errors"] == 0

    def test_groundedness_probes_are_composable(self):
        """probes_groundedness.all_probes can be combined with other ProbeSet objects."""
        from checkagent.safety import probes_groundedness, probes_injection
        combined = probes_groundedness.all_probes + probes_injection.all_probes
        assert len(combined) == len(probes_groundedness.all_probes) + len(probes_injection.all_probes)
        assert hasattr(combined, "filter")

    def test_groundedness_module_structure_consistent_with_injection(self):
        """probes_groundedness has same structure as probes_injection (all_probes + subcategories)."""
        from checkagent.safety import probes_groundedness, ProbeSet
        assert hasattr(probes_groundedness, "all_probes")
        assert isinstance(probes_groundedness.all_probes, ProbeSet)
        assert hasattr(probes_groundedness, "fabrication")
        assert isinstance(probes_groundedness.fabrication, ProbeSet)
        assert hasattr(probes_groundedness, "uncertainty")
        assert isinstance(probes_groundedness.uncertainty, ProbeSet)


class TestF099GroundednessUncertaintyStillBroken:
    """F-099: GroundednessEvaluator uncertainty mode still not detecting hedging words."""

    def test_hedging_response_fails_uncertainty_check(self):
        """Words like 'might', 'could', 'not certain' are not detected — F-099 open."""
        from checkagent.safety import GroundednessEvaluator
        g = GroundednessEvaluator(mode="uncertainty")
        # This text clearly hedges — should PASS uncertainty check
        result = g.evaluate("This might be true, but I could be wrong and am not certain.")
        # F-099: it incorrectly returns passed=False (0 signals found)
        # When fixed, this test should be updated to assert passed=True
        assert result.passed is False, (
            "F-099 may be fixed — uncertainty mode now detects hedging. Update this test."
        )
        assert "0/" in result.findings[0].description, (
            "Expected 0 signals found — F-099 symptom"
        )

    def test_confident_response_also_fails(self):
        """Overconfident statement also returns passed=False — both fail, so mode is useless."""
        from checkagent.safety import GroundednessEvaluator
        g = GroundednessEvaluator(mode="uncertainty")
        result = g.evaluate("The stock will definitely rise 20% next quarter.")
        # This should also fail (correct), but for the same broken reason
        assert result.passed is False

    def test_uncertainty_mode_cannot_distinguish_hedged_from_confident(self):
        """F-099: uncertainty mode treats hedged and overconfident responses identically."""
        from checkagent.safety import GroundednessEvaluator
        g = GroundednessEvaluator(mode="uncertainty")
        hedged = g.evaluate("I'm not sure, this might not be accurate.")
        confident = g.evaluate("I am 100% certain this is correct.")
        # Both fail with 0 signals — mode cannot distinguish
        assert hedged.passed == confident.passed, (
            "F-099: both should return same result (both broken)"
        )


class TestGroundednessEvaluatorTopLevel:
    """GroundednessEvaluator and ConversationSafetyScanner missing from top-level checkagent."""

    def test_groundedness_evaluator_not_at_top_level(self):
        """GroundednessEvaluator is absent from top-level checkagent — requires deep import."""
        import checkagent
        assert not hasattr(checkagent, "GroundednessEvaluator"), (
            "GroundednessEvaluator is now at top-level — update scores and close this finding."
        )

    def test_groundedness_evaluator_importable_from_safety(self):
        """GroundednessEvaluator is importable from checkagent.safety."""
        from checkagent.safety import GroundednessEvaluator
        assert GroundednessEvaluator is not None

    def test_conversation_safety_scanner_not_at_top_level(self):
        """ConversationSafetyScanner is absent from top-level checkagent."""
        import checkagent
        assert not hasattr(checkagent, "ConversationSafetyScanner"), (
            "ConversationSafetyScanner is now at top-level — update findings."
        )

    def test_conversation_safety_scanner_importable_from_safety(self):
        """ConversationSafetyScanner is importable from checkagent.safety."""
        from checkagent.safety import ConversationSafetyScanner
        assert ConversationSafetyScanner is not None
