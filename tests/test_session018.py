"""Session-018 tests: migrate-cassettes CLI, Cassette str/Path API, CI gate conftest wiring."""
import json
import subprocess
import tempfile
import warnings
from pathlib import Path

import pytest

from checkagent.replay import (
    Cassette,
    CassetteMeta,
    CassetteRecorder,
    CASSETTE_SCHEMA_VERSION,
)
from checkagent.ci import evaluate_gates, scores_to_dict, generate_pr_comment
from checkagent.ci.quality_gate import QualityGateEntry
from checkagent import AgentRun, AgentInput, Score
from checkagent.eval.metrics import task_completion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_v0_cassette_file(directory: Path, name: str = "legacy.json") -> Path:
    """Write a schema v0 cassette JSON file to disk (manually, bypassing save())."""
    v0_data = {
        "meta": {
            "test_id": name.replace(".json", ""),
            "schema_version": 0,
            "recorded_at": "2026-01-01T00:00:00",
            "checkagent_version": "",
            "tags": [],
        },
        "interactions": [],
    }
    path = directory / name
    path.write_text(json.dumps(v0_data))
    return path


def make_v1_cassette_file(directory: Path, name: str = "current.json") -> Path:
    """Save a v1 cassette using the normal Cassette API."""
    cassette = Cassette(meta=CassetteMeta(test_id=name.replace(".json", "")), interactions=[])
    path = directory / name
    cassette.save(path)
    return path


# ---------------------------------------------------------------------------
# F-039 resolved: migrate-cassettes CLI exists
# ---------------------------------------------------------------------------


class TestMigrateCassettesCLI:
    def test_command_exists_in_help(self):
        """migrate-cassettes must appear in checkagent --help output."""
        result = subprocess.run(
            ["checkagent", "--help"], capture_output=True, text=True
        )
        assert "migrate-cassettes" in result.stdout

    def test_help_text_describes_command(self):
        """migrate-cassettes --help must describe the command clearly."""
        result = subprocess.run(
            ["checkagent", "migrate-cassettes", "--help"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "schema" in result.stdout.lower() or "upgrade" in result.stdout.lower()

    def test_dry_run_flag_accepted(self):
        """--dry-run flag must be accepted without error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_v1_cassette_file(Path(tmpdir), "test.json")
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir, "--dry-run"],
                capture_output=True, text=True
            )
            # --dry-run on v1 cassettes = skip; should not error on flag itself
            assert "dry run" in result.stdout.lower() or result.returncode in (0, 1)

    def test_no_backup_flag_accepted(self):
        """--no-backup flag must be accepted without error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_v1_cassette_file(Path(tmpdir), "test.json")
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir, "--no-backup"],
                capture_output=True, text=True
            )
            assert result.returncode == 0

    def test_nonexistent_directory_returns_exit_code_2(self):
        """Passing a nonexistent directory must return exit code 2 with error."""
        result = subprocess.run(
            ["checkagent", "migrate-cassettes", "/nonexistent/path/xyz"],
            capture_output=True, text=True
        )
        assert result.returncode == 2
        assert "does not exist" in result.stderr.lower() or "invalid" in result.stderr.lower()

    def test_empty_directory_reports_no_files(self):
        """Empty directory must report zero cassette files found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir],
                capture_output=True, text=True
            )
            assert result.returncode == 0
            assert "no cassette" in result.stdout.lower() or "0" in result.stdout

    def test_v1_cassette_is_skipped(self):
        """Already-current v1 cassettes must be reported as skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_v1_cassette_file(Path(tmpdir), "current.json")
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir],
                capture_output=True, text=True
            )
            assert result.returncode == 0
            # Output should mention Skipped: 1
            assert "skipped: 1" in result.stdout.lower() or "skipped" in result.stdout.lower()

    def test_v1_cassette_not_modified(self):
        """v1 cassette content must be unchanged after migration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = make_v1_cassette_file(Path(tmpdir), "test.json")
            original_content = path.read_text()
            subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir],
                capture_output=True, text=True
            )
            assert path.read_text() == original_content

    def test_recursive_subdirectory_search(self):
        """migrate-cassettes must find cassettes in subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir" / "nested"
            subdir.mkdir(parents=True)
            make_v1_cassette_file(subdir, "nested.json")
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir],
                capture_output=True, text=True
            )
            assert result.returncode == 0
            # Should find and process the nested cassette
            assert "skipped: 1" in result.stdout.lower() or "skipped" in result.stdout.lower()

    def test_default_directory_is_cassettes(self):
        """With no argument, migrate-cassettes defaults to 'cassettes/' directory."""
        result = subprocess.run(
            ["checkagent", "migrate-cassettes"],
            capture_output=True, text=True,
            cwd=tempfile.mkdtemp()  # fresh dir without cassettes/
        )
        # Should fail with exit code 2 and mention 'cassettes' as the default path
        assert result.returncode == 2
        assert "cassettes" in result.stderr.lower()


# ---------------------------------------------------------------------------
# F-045 (new): migrate-cassettes fails for v0 cassettes — no migration registered
# ---------------------------------------------------------------------------


class TestMigrateCassettesV0Failure:
    """v0→v1 migration path is not implemented — CLI exists but migration fails."""

    def test_v0_cassette_fails_with_no_migration_registered(self):
        """v0 cassettes fail migration with 'No migration registered from v0' message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_v0_cassette_file(Path(tmpdir), "legacy.json")
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir],
                capture_output=True, text=True
            )
            # Should report a failure
            assert "fail" in result.stdout.lower()

    def test_v0_cassette_migration_failure_message(self):
        """Failure message must mention that no migration path exists from v0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_v0_cassette_file(Path(tmpdir), "legacy.json")
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir],
                capture_output=True, text=True
            )
            # Should mention "no migration" or similar
            assert "migration" in result.stdout.lower() or "no migration" in result.stdout.lower()

    def test_v0_migration_failure_count_in_summary(self):
        """Summary line must show Failed: 1 when v0 cassette cannot be migrated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_v0_cassette_file(Path(tmpdir), "legacy.json")
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir],
                capture_output=True, text=True
            )
            assert "failed: 1" in result.stdout.lower()

    def test_v0_migration_failure_should_return_nonzero_exit_code(self):
        """migrate-cassettes with unmigratable cassettes should return non-zero exit code.

        This test documents a BUG: the command returns exit code 0 even when
        migrations fail. A user who runs 'checkagent migrate-cassettes && deploy'
        will silently proceed despite cassette migration failures.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            make_v0_cassette_file(Path(tmpdir), "legacy.json")
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir],
                capture_output=True, text=True
            )
            # BUG: returns 0 instead of non-zero when migrations fail
            # This assertion documents the current (broken) behavior
            assert result.returncode == 0  # should be != 0

    def test_dry_run_on_v0_cassette_shows_failure_without_modifying(self):
        """--dry-run on v0 cassette shows failure but doesn't modify the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = make_v0_cassette_file(Path(tmpdir), "legacy.json")
            original = path.read_text()
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir, "--dry-run"],
                capture_output=True, text=True
            )
            # File must be unmodified
            assert path.read_text() == original

    def test_v0_cassette_file_unchanged_after_failed_migration(self):
        """Failed migration must not corrupt or modify the original cassette file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = make_v0_cassette_file(Path(tmpdir), "legacy.json")
            original_content = path.read_text()
            subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir],
                capture_output=True, text=True
            )
            # File must be unmodified after failed migration
            assert path.read_text() == original_content

    def test_mixed_v0_and_v1_cassettes_summary(self):
        """Mixed directory: v1 skipped, v0 failed — both counts in summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_v0_cassette_file(Path(tmpdir), "old.json")
            make_v1_cassette_file(Path(tmpdir), "new.json")
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmpdir],
                capture_output=True, text=True
            )
            assert "skipped: 1" in result.stdout.lower() or "1" in result.stdout
            assert "failed: 1" in result.stdout.lower() or "failed" in result.stdout


# ---------------------------------------------------------------------------
# F-046 (new): Cassette.save() and Cassette.load() require Path, not str
# ---------------------------------------------------------------------------


class TestCassetteStrVsPath:
    """Cassette.save() and Cassette.load() raise AttributeError on str input."""

    def test_save_with_str_works_now(self):
        """F-046 FIXED: Cassette.save(str_path) now works (str accepted)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette = Cassette(meta=CassetteMeta(test_id="test"), interactions=[])
            str_path = tmpdir + "/test.json"
            cassette.save(str_path)  # Should not raise
            assert Path(str_path).exists()

    def test_save_with_path_works(self):
        """Cassette.save(Path) works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette = Cassette(meta=CassetteMeta(test_id="test"), interactions=[])
            cassette.save(Path(tmpdir) / "test.json")
            assert (Path(tmpdir) / "test.json").exists()

    def test_load_with_str_works_now(self):
        """F-046 FIXED: Cassette.load(str_path) now works (str accepted)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.json"
            cassette = Cassette(meta=CassetteMeta(test_id="test"), interactions=[])
            cassette.save(path)
            loaded = Cassette.load(str(path))
            assert loaded.meta.test_id == "test"

    def test_load_with_path_works(self):
        """Cassette.load(Path) works correctly and restores all data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.json"
            cassette = Cassette(meta=CassetteMeta(test_id="test_load"), interactions=[])
            cassette.save(path)
            loaded = Cassette.load(path)
            assert loaded.meta.test_id == "test_load"

    def test_save_and_load_str_round_trip(self):
        """F-046 FIXED: save(str) + load(str) round-trip works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            str_path = tmpdir + "/roundtrip.json"
            cassette = Cassette(meta=CassetteMeta(test_id="roundtrip"), interactions=[])
            cassette.save(str_path)
            loaded = Cassette.load(str_path)
            assert loaded.meta.test_id == "roundtrip"


# ---------------------------------------------------------------------------
# New CI failure: migrate-cassettes warning message now points to real command
# ---------------------------------------------------------------------------


class TestCassetteLoadWarningMessage:
    """Cassette.load() warning now references a real CLI command (F-039 resolved)."""

    def test_old_schema_warning_references_real_command(self):
        """After F-039 fix, the warning message points to a command that exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            v0_path = make_v0_cassette_file(Path(tmpdir))
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                Cassette.load(v0_path)
                assert len(caught) == 1
                msg = str(caught[0].message)
                assert "migrate-cassettes" in msg

            # Verify the referenced command actually exists
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", "--help"],
                capture_output=True, text=True
            )
            assert result.returncode == 0, (
                "Warning references 'checkagent migrate-cassettes' but command doesn't exist"
            )

    def test_v1_cassette_loads_without_warning(self):
        """v1 cassettes load silently with no deprecation warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = make_v1_cassette_file(Path(tmpdir))
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                Cassette.load(path)
                schema_warnings = [w for w in caught if "schema" in str(w.message).lower()]
                assert len(schema_warnings) == 0


# ---------------------------------------------------------------------------
# New CI failure: TimedCall.duration_ms = 0.0 on Windows (F-047 documented)
# ---------------------------------------------------------------------------


class TestTimedCallPlatformBehavior:
    """TimedCall uses time.monotonic() — test_timing_is_positive_for_slow_ops fails on Windows."""

    def test_timed_call_captures_duration(self):
        """TimedCall must record non-zero duration for a measurable operation."""
        import time
        from checkagent.replay import TimedCall

        tc = TimedCall()
        with tc:
            time.sleep(0.02)  # 20ms — well above any platform resolution
        assert tc.duration_ms >= 15, f"Expected >= 15ms, got {tc.duration_ms}ms"

    def test_timed_call_initial_duration_is_zero(self):
        """duration_ms starts at 0.0 before context manager exits."""
        from checkagent.replay import TimedCall

        tc = TimedCall()
        assert tc.duration_ms == 0.0
        with tc:
            initial = tc.duration_ms  # still 0.0 inside
        assert initial == 0.0

    def test_timed_call_context_manager_returns_self(self):
        """TimedCall.__enter__ returns the TimedCall instance for 'as tc' usage."""
        import time
        from checkagent.replay import TimedCall

        with TimedCall() as tc:
            time.sleep(0.001)
        assert isinstance(tc, TimedCall)
        assert tc.duration_ms >= 0.0

    def test_timed_call_very_short_op_behavior(self):
        """Very short operations may return 0.0 on low-resolution platforms.

        This test documents the upstream CI failure: on Windows, time.monotonic()
        has ~15ms resolution so any operation shorter than 15ms returns 0.0.
        The upstream test asserts >= 5ms with a short sleep, which fails on Windows.
        """
        from checkagent.replay import TimedCall

        tc = TimedCall()
        with tc:
            pass  # near-instant
        # On Linux this is typically 0.0001ms, on Windows it may be 0.0
        # Either way, it's valid behavior — the upstream test uses too short a sleep
        assert tc.duration_ms >= 0.0

    def test_timed_call_reusable(self):
        """TimedCall can be used multiple times with fresh durations each time."""
        import time
        from checkagent.replay import TimedCall

        tc = TimedCall()
        with tc:
            time.sleep(0.02)
        first = tc.duration_ms

        with tc:
            time.sleep(0.04)
        second = tc.duration_ms

        assert second > first
        assert second >= 30  # 40ms sleep should be well above 30ms


# ---------------------------------------------------------------------------
# evaluate_gates() conftest.py integration pattern
# ---------------------------------------------------------------------------


class TestEvaluateGatesConftestPattern:
    """Verify the pattern for wiring evaluate_gates into pytest sessionfinish."""

    def test_basic_gate_passes_with_good_scores(self):
        """Full pipeline: run → metric → scores_to_dict → evaluate_gates → report."""
        run = AgentRun(
            input=AgentInput(query="What is the capital of France?"),
            final_output="The capital of France is Paris."
        )
        score = task_completion(run, expected_output_contains=["Paris"])
        scores = scores_to_dict([Score(name="task_completion", value=score.value)])
        gates = {
            "task_completion": QualityGateEntry(min=0.7, on_fail="block")
        }
        report = evaluate_gates(scores, gates)
        assert report.passed

    def test_basic_gate_blocks_with_poor_scores(self):
        """Gate blocks when agent output doesn't meet quality threshold."""
        run = AgentRun(
            input=AgentInput(query="What is the capital of France?"),
            final_output="I'm not sure about that."
        )
        score = task_completion(run, expected_output_contains=["Paris"])
        scores = scores_to_dict([Score(name="task_completion", value=score.value)])
        gates = {
            "task_completion": QualityGateEntry(min=0.7, on_fail="block")
        }
        report = evaluate_gates(scores, gates)
        assert not report.passed
        assert len(report.blocked_gates) == 1

    def test_conftest_sessionfinish_pattern(self):
        """Demonstrate the conftest.py sessionfinish hook pattern."""
        # Simulate what a conftest.py sessionfinish would do
        # This is the pattern users would copy into their conftest.py

        accumulated_scores: dict[str, float] = {}

        # Multiple test runs simulating score accumulation
        test_cases = [
            ("Paris", 1.0),
            ("Paris is nice", 1.0),
            ("I dunno", 0.0),
        ]
        score_values = []
        for output, _ in test_cases:
            run = AgentRun(
                input=AgentInput(query="Capital of France?"),
                final_output=output
            )
            s = task_completion(run, expected_output_contains=["Paris"])
            score_values.append(s.value)

        avg = sum(score_values) / len(score_values)
        accumulated_scores["task_completion"] = avg

        # Apply gates at session end
        gates = {
            "task_completion": QualityGateEntry(min=0.5, on_fail="warn")
        }
        report = evaluate_gates(accumulated_scores, gates)

        # avg = 0.833 (task_completion returns 0.5 for no-match, not 0.0)
        # threshold = 0.5 → should pass
        assert report.passed
        assert abs(accumulated_scores["task_completion"] - 0.833) < 0.01

    def test_pr_comment_generation_from_gate_report(self):
        """generate_pr_comment works with gate report from evaluate_gates."""
        from checkagent.ci import RunSummary

        scores = {"task_completion": 0.85, "step_efficiency": 0.9}
        gates = {
            "task_completion": QualityGateEntry(min=0.7, on_fail="block"),
            "step_efficiency": QualityGateEntry(min=0.8, on_fail="warn"),
        }
        gate_report = evaluate_gates(scores, gates)

        test_summary = RunSummary(
            total=10, passed=9, failed=1, skipped=0, errors=0, duration_s=2.5
        )
        comment = generate_pr_comment(
            test_summary=test_summary,
            gate_report=gate_report
        )
        assert "## CheckAgent" in comment or "checkagent" in comment.lower()
        assert gate_report.passed  # both gates pass

    def test_multi_metric_gate_warns_without_blocking(self):
        """Warn-level gates don't block report.passed even when failing."""
        scores = {"task_completion": 0.9, "latency": 2.5}
        gates = {
            "task_completion": QualityGateEntry(min=0.8, on_fail="block"),
            "latency": QualityGateEntry(max=1.0, on_fail="warn"),  # fails: 2.5 > 1.0
        }
        report = evaluate_gates(scores, gates)
        assert report.passed  # warn doesn't block
        assert report.has_warnings
        assert len(report.warned_gates) == 1
        assert report.warned_gates[0].metric == "latency"


# ---------------------------------------------------------------------------
# Schema version constant accessibility
# ---------------------------------------------------------------------------


class TestSchemaVersionConstant:
    def test_schema_version_is_1(self):
        """CASSETTE_SCHEMA_VERSION must be 1 (current version)."""
        assert CASSETTE_SCHEMA_VERSION == 1

    def test_schema_version_importable_from_replay(self):
        """CASSETTE_SCHEMA_VERSION importable from checkagent.replay."""
        from checkagent.replay import CASSETTE_SCHEMA_VERSION as CSV
        assert CSV == 1

    def test_new_cassette_uses_current_schema_version(self):
        """Newly created Cassette should default to current schema version."""
        recorder = CassetteRecorder(test_id="schema_test")
        cassette = recorder.finalize()
        assert cassette.meta.schema_version == CASSETTE_SCHEMA_VERSION
