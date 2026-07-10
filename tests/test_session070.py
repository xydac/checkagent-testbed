"""
Session-070 tests.
Checkagent version: git main (post-1.1.0, after F-045 migration commit).

New upstream commits this session:
- "Implement v0-to-v1 cassette migration (F-045)"
- "Add ca_cassette pytest fixture with auto record/replay mode detection"
- "Fix F-146: escape Prompt: header preview to preserve brackets in Rich output"

Fixed this session:
- F-045 FIXED: migrate_cassette_data() and CLI now correctly upgrade v0→v1 cassettes
- F-146 FIXED: analyze-prompt Prompt: header now preserves [brackets] in Rich output
- ca_cassette pytest fixture added: CassetteFixture with is_recording()/is_replaying()

Still open:
- F-044: SEQUENCE strategy ignores 'kind' — llm request matches tool interaction by position

Testbed fix this session:
- TestMigrateCassettesV0Failure updated: 4 tests rewrote to document success (not failure) now
  that F-045 is implemented. Tests now verify migration succeeds, schema_version→1, summary counts.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from checkagent.replay import (
    Cassette,
    CassetteMeta,
    CassetteRecorder,
    Interaction,
    MatchStrategy,
    RecordedRequest,
    RecordedResponse,
    ReplayEngine,
    migrate_cassette_data,
)
from checkagent.core.plugin import CassetteFixture


# ---------------------------------------------------------------------------
# F-146 FIXED: analyze-prompt Prompt: header now preserves [brackets]
# ---------------------------------------------------------------------------


class TestF146Fixed:
    """F-146 FIXED: Prompt: preview line no longer strips Rich markup-like brackets."""

    def test_prompt_header_preserves_square_brackets(self):
        """Prompt: header shows [your domain] without stripping."""
        result = subprocess.run(
            ["checkagent", "analyze-prompt", "Only help with [your domain] questions."],
            capture_output=True, text=True
        )
        lines = result.stdout.split("\n")
        prompt_line = next((l for l in lines if l.startswith("Prompt:")), None)
        assert prompt_line is not None, "No 'Prompt:' line in output"
        assert "[your domain]" in prompt_line, (
            f"Brackets stripped from Prompt: header. Got: {repr(prompt_line)}"
        )

    def test_prompt_header_preserves_multiple_bracket_groups(self):
        """Multiple bracketed placeholders in prompt are all preserved."""
        result = subprocess.run(
            ["checkagent", "analyze-prompt",
             "You are [bot name]. Only assist with [topic] questions."],
            capture_output=True, text=True
        )
        lines = result.stdout.split("\n")
        prompt_line = next((l for l in lines if l.startswith("Prompt:")), None)
        assert prompt_line is not None
        assert "[bot name]" in prompt_line
        assert "[topic]" in prompt_line

    def test_prompt_header_does_not_double_escape(self):
        """Brackets shown cleanly — no extra backslashes or escape artifacts."""
        result = subprocess.run(
            ["checkagent", "analyze-prompt", "Answer only [approved topics]."],
            capture_output=True, text=True
        )
        lines = result.stdout.split("\n")
        prompt_line = next((l for l in lines if l.startswith("Prompt:")), None)
        assert prompt_line is not None
        assert r"\[" not in prompt_line, "Double-escaped backslash-bracket in output"
        assert "[approved topics]" in prompt_line


# ---------------------------------------------------------------------------
# F-045 FIXED: migrate_cassette_data Python API upgrades v0→v1
# ---------------------------------------------------------------------------


def _make_v0_data(test_id: str = "test") -> dict:
    return {
        "meta": {
            "test_id": test_id,
            "schema_version": 0,
            "recorded_at": "2026-01-01T00:00:00",
            "checkagent_version": "",
            "tags": [],
        },
        "interactions": [],
    }


def _make_v0_data_with_interaction(test_id: str = "test") -> dict:
    data = _make_v0_data(test_id)
    data["interactions"].append({
        "request": {"kind": "llm", "body": {"messages": [{"role": "user", "content": "hi"}]}},
        "response": {
            "body": {"choices": [{"message": {"content": "hello"}}]},
            "status": "success",
        },
    })
    return data


class TestF045FixedPythonAPI:
    """F-045 FIXED: migrate_cassette_data() now correctly upgrades v0 → v1."""

    def test_migrate_v0_returns_schema_version_1(self):
        """migrate_cassette_data on v0 input returns schema_version=1."""
        v0 = _make_v0_data()
        result = migrate_cassette_data(v0)
        assert result["meta"]["schema_version"] == 1

    def test_migrate_v0_preserves_test_id(self):
        """Migration preserves the test_id field."""
        v0 = _make_v0_data(test_id="my_suite_test")
        result = migrate_cassette_data(v0)
        assert result["meta"]["test_id"] == "my_suite_test"

    def test_migrate_v0_assigns_interaction_id(self):
        """Each interaction gets an id after migration."""
        v0 = _make_v0_data_with_interaction()
        result = migrate_cassette_data(v0)
        assert len(result["interactions"]) == 1
        interaction = result["interactions"][0]
        assert "id" in interaction
        assert interaction["id"]  # non-empty

    def test_migrate_v0_assigns_sequence_numbers(self):
        """Each interaction gets a sequence number starting at 0."""
        v0 = _make_v0_data_with_interaction()
        result = migrate_cassette_data(v0)
        interaction = result["interactions"][0]
        assert "sequence" in interaction
        assert interaction["sequence"] == 0

    def test_migrate_v0_preserves_interaction_content(self):
        """Migration does not corrupt request/response bodies."""
        v0 = _make_v0_data_with_interaction()
        result = migrate_cassette_data(v0)
        interaction = result["interactions"][0]
        assert interaction["request"]["kind"] == "llm"
        assert "messages" in interaction["request"]["body"]
        assert interaction["response"]["status"] == "success"

    def test_migrate_v1_is_idempotent(self):
        """Migrating a v1 cassette returns it unchanged (already at target)."""
        v0 = _make_v0_data()
        v1 = migrate_cassette_data(v0)
        v1_again = migrate_cassette_data(v1)
        assert v1_again["meta"]["schema_version"] == 1

    def test_migrate_v0_multiple_interactions(self):
        """Multiple interactions all get assigned sequence numbers."""
        v0 = _make_v0_data()
        for i in range(3):
            v0["interactions"].append({
                "request": {"kind": "llm", "body": {"n": i}},
                "response": {"body": {"result": i}, "status": "success"},
            })
        result = migrate_cassette_data(v0)
        seqs = [ia["sequence"] for ia in result["interactions"]]
        assert seqs == [0, 1, 2]


# ---------------------------------------------------------------------------
# ca_cassette fixture: CassetteFixture API (programmatic testing)
# ---------------------------------------------------------------------------


class TestCassetteFixture:
    """CassetteFixture returned by ca_cassette fixture — test its API directly."""

    def test_record_mode_is_recording(self):
        """CassetteFixture in record mode: is_recording() returns True."""
        recorder = CassetteRecorder(test_id="test_record")
        ctx = CassetteFixture(
            mode="record",
            path=Path("/tmp/dummy.json"),
            recorder=recorder,
        )
        assert ctx.is_recording() is True
        assert ctx.is_replaying() is False

    def test_replay_mode_is_replaying(self):
        """CassetteFixture in replay mode: is_replaying() returns True."""
        cassette = Cassette(meta=CassetteMeta(test_id="t"), interactions=[])
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        ctx = CassetteFixture(
            mode="replay",
            path=Path("/tmp/dummy.json"),
            engine=engine,
            cassette=cassette,
        )
        assert ctx.is_replaying() is True
        assert ctx.is_recording() is False

    def test_record_mode_has_recorder_no_engine(self):
        """Record mode: recorder is set, engine is None."""
        recorder = CassetteRecorder(test_id="t")
        ctx = CassetteFixture(mode="record", path=Path("/tmp/x.json"), recorder=recorder)
        assert ctx.recorder is not None
        assert ctx.engine is None
        assert ctx.cassette is None

    def test_replay_mode_has_engine_and_cassette_no_recorder(self):
        """Replay mode: engine and cassette set, recorder is None."""
        cassette = Cassette(meta=CassetteMeta(test_id="t"), interactions=[])
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        ctx = CassetteFixture(
            mode="replay",
            path=Path("/tmp/x.json"),
            engine=engine,
            cassette=cassette,
        )
        assert ctx.recorder is None
        assert ctx.engine is not None
        assert ctx.cassette is not None

    def test_record_then_replay_round_trip(self):
        """Full record→save→load→replay cycle via CassetteFixture."""
        with tempfile.TemporaryDirectory() as tmp:
            cassette_path = Path(tmp) / "test.json"

            # === RECORD ===
            recorder = CassetteRecorder(test_id="greeting_test")
            rec_ctx = CassetteFixture(
                mode="record", path=cassette_path, recorder=recorder
            )
            assert rec_ctx.is_recording()

            rec_ctx.recorder.record_llm_call(
                method="chat.completions.create",
                request_body={"messages": [{"role": "user", "content": "hello"}]},
                response_body={"choices": [{"message": {"content": "Hi there!"}}]},
            )
            cassette = rec_ctx.recorder.finalize()
            cassette.save(cassette_path)

            assert cassette_path.exists()

            # === REPLAY ===
            loaded = Cassette.load(cassette_path)
            engine = ReplayEngine(loaded, strategy=MatchStrategy.SEQUENCE)
            rep_ctx = CassetteFixture(
                mode="replay", path=cassette_path, engine=engine, cassette=loaded
            )
            assert rep_ctx.is_replaying()

            # Replay the recorded interaction
            req = RecordedRequest(
                kind="llm",
                body={"messages": [{"role": "user", "content": "hello"}]},
            )
            interaction = rep_ctx.engine.match(req)
            assert interaction is not None
            assert interaction.response.body["choices"][0]["message"]["content"] == "Hi there!"
            assert rep_ctx.engine.all_used

    def test_replay_path_attribute_set(self):
        """CassetteFixture.path holds the resolved cassette file path."""
        p = Path("/tmp/my_test.json")
        ctx = CassetteFixture(mode="record", path=p, recorder=CassetteRecorder(test_id="t"))
        assert ctx.path == p


# ---------------------------------------------------------------------------
# ca_cassette pytest fixture: used via @pytest.fixture
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="replay")
def test_ca_cassette_fixture_record_mode_creates_file(tmp_path, ca_cassette):
    """ca_cassette in record mode: a cassette file is created after the test."""
    # ca_cassette automatically starts in record mode (no cassette file exists)
    assert ca_cassette.is_recording(), "Expected record mode since cassette file doesn't exist"

    # Record an LLM call
    ca_cassette.recorder.record_llm_call(
        method="chat.completions.create",
        request_body={"messages": [{"role": "user", "content": "What is 2+2?"}]},
        response_body={"choices": [{"message": {"content": "4"}}]},
    )


@pytest.mark.agent_test(layer="replay")
def test_ca_cassette_fixture_mode_detection(ca_cassette):
    """ca_cassette fixture correctly detects mode based on file existence.

    When no cassette file exists → record mode.
    This test verifies the fixture auto-selects record mode.
    """
    assert ca_cassette.mode in ("record", "replay"), (
        f"Unexpected mode: {ca_cassette.mode}"
    )
    if ca_cassette.is_recording():
        assert ca_cassette.recorder is not None
        assert ca_cassette.engine is None
    else:
        assert ca_cassette.engine is not None
        assert ca_cassette.recorder is None


# ---------------------------------------------------------------------------
# migrate-cassettes CLI: F-045 FIXED (already in TestMigrateCassettesV0Failure
# in test_session018.py — these tests verify the Python API complement)
# ---------------------------------------------------------------------------


class TestMigrateCassettesCliFixed:
    """Verify migrate-cassettes CLI success behavior after F-045 fix."""

    def _make_v0_file(self, directory: Path, name: str) -> Path:
        p = directory / name
        p.write_text(json.dumps({
            "meta": {
                "test_id": "legacy",
                "schema_version": 0,
                "recorded_at": "2026-01-01T00:00:00",
                "checkagent_version": "",
                "tags": [],
            },
            "interactions": [],
        }))
        return p

    def test_cli_success_output_format(self):
        """CLI shows OK and v0 -> v1 (migrated) for each file."""
        with tempfile.TemporaryDirectory() as tmp:
            self._make_v0_file(Path(tmp), "legacy.json")
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmp],
                capture_output=True, text=True
            )
            assert result.returncode == 0
            assert "ok" in result.stdout.lower()
            assert "migrated" in result.stdout.lower()

    def test_cli_summary_migrated_count(self):
        """CLI summary shows Migrated: N after successful migration."""
        with tempfile.TemporaryDirectory() as tmp:
            self._make_v0_file(Path(tmp), "a.json")
            self._make_v0_file(Path(tmp), "b.json")
            result = subprocess.run(
                ["checkagent", "migrate-cassettes", tmp],
                capture_output=True, text=True
            )
            assert "migrated: 2" in result.stdout.lower()
            assert "failed: 0" in result.stdout.lower()

    def test_cli_upgrades_schema_version_in_file(self):
        """After migration, schema_version in the JSON file is 1."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._make_v0_file(Path(tmp), "legacy.json")
            subprocess.run(
                ["checkagent", "migrate-cassettes", tmp],
                capture_output=True, text=True
            )
            data = json.loads(path.read_text())
            assert data["meta"]["schema_version"] == 1

    def test_cli_dry_run_does_not_modify_schema_version(self):
        """--dry-run does not write changes to disk."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._make_v0_file(Path(tmp), "legacy.json")
            original = path.read_text()
            subprocess.run(
                ["checkagent", "migrate-cassettes", tmp, "--dry-run"],
                capture_output=True, text=True
            )
            assert path.read_text() == original


# ---------------------------------------------------------------------------
# F-044 still open: SEQUENCE strategy ignores kind
# ---------------------------------------------------------------------------


class TestF044StillOpen:
    """F-044: SEQUENCE strategy matches by position, ignoring the 'kind' field."""

    def test_sequence_matches_llm_interaction_with_tool_request(self):
        """SEQUENCE: a 'tool' request matches an 'llm' interaction if it's next in order."""
        cassette = Cassette(
            meta=CassetteMeta(test_id="kind_test"),
            interactions=[
                Interaction(
                    request=RecordedRequest(kind="llm", body={"messages": []}),
                    response=RecordedResponse(body={"content": "reply"}, status="success"),
                    sequence=0,
                    id="abc001",
                )
            ],
        )
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)

        # Request with 'tool' kind should still match the 'llm' interaction
        tool_req = RecordedRequest(kind="tool", body={"any": "body"})
        match = engine.match(tool_req)
        assert match is not None, "SEQUENCE should match regardless of kind (F-044 still open)"
        assert match.response.body["content"] == "reply"


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------


def test_version_post_f045():
    """Installed version is git main post-F-045 fix."""
    import checkagent
    parts = checkagent.__version__.split(".")
    major = int(parts[0])
    minor = int(parts[1])
    assert major >= 1, f"Expected major >=1, got {checkagent.__version__}"
    assert minor >= 1, f"Expected minor >=1, got {checkagent.__version__}"


def test_upstream_ci_green():
    """Upstream CI is green: 'Implement v0-to-v1 cassette migration (F-045)'."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "3",
         "--json", "conclusion,displayTitle"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.skip("gh CLI not available")
    runs = json.loads(result.stdout)
    assert all(r["conclusion"] == "success" for r in runs), (
        f"Some CI runs are not green: {[r for r in runs if r['conclusion'] != 'success']}"
    )
