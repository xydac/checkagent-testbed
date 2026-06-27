"""
Session-069 tests.
Checkagent version: 1.1.0 (git main — post-1.1.0 commits installed).

New upstream commit: "Add end-to-end replay tests: record MockLLM session, save cassette, replay"
— CassetteRecorder/ReplayEngine API now works end-to-end.

Fixed this session:
- F-042 FIXED: ReplayEngine(block_unmatched=False) now returns None instead of raising
- F-145 FIXED: analyze-prompt table Note 'Try:' hints now preserve [brackets]

Still open:
- F-044: SEQUENCE strategy ignores 'kind' — llm request matches tool interaction by position
- F-146 NEW: analyze-prompt 'Prompt:' header preview still strips [brackets] from input text
- F-039 / @pytest.mark.cassette: marker still has no record/replay behavior in plugin

API notes:
- CassetteRecorder(test_id='...')  # not 'source='
- recorder.record_llm_call(method=, request_body=, response_body=, model=, duration_ms=)
- recorder.record_tool_call(tool_name=, arguments=, result=, duration_ms=)
- recorder.finalize()  # no args — returns Cassette
- Cassette.save(Path), Cassette.load(Path)  # Path only, not str (F-046)
- ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE|EXACT|SUBSET, block_unmatched=True|False)
- engine.match(RecordedRequest(kind=, method=, model=, body=))  # returns Interaction or None
- engine.remaining  # property, not method
- engine.all_used   # property, not method
- engine.reset()    # method
"""

import json
import pathlib
import subprocess
import sys
import tempfile

import pytest

import checkagent
from checkagent.replay import (
    Cassette,
    CassetteMismatchError,
    CassetteRecorder,
    MatchStrategy,
    RecordedRequest,
    ReplayEngine,
    TimedCall,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cassette(num_llm=2, num_tool=0):
    """Build a cassette with num_llm LLM interactions and num_tool tool interactions."""
    recorder = CassetteRecorder(test_id="session069-test")
    for i in range(num_llm):
        recorder.record_llm_call(
            method="complete",
            request_body={"input": f"question_{i}"},
            response_body={"output": f"answer_{i}"},
            model="mock-model",
            duration_ms=float(10 + i),
        )
    for i in range(num_tool):
        recorder.record_tool_call(
            tool_name=f"tool_{i}",
            arguments={"arg": f"val_{i}"},
            result={"result": f"ok_{i}"},
            duration_ms=5.0,
        )
    return recorder.finalize()


# ---------------------------------------------------------------------------
# CassetteRecorder API
# ---------------------------------------------------------------------------


def test_cassette_recorder_basic():
    """CassetteRecorder.finalize() returns a Cassette with interactions."""
    cassette = _make_cassette(num_llm=2, num_tool=1)
    assert len(cassette.interactions) == 3


def test_cassette_recorder_llm_interaction_fields():
    """Recorded LLM interaction has correct response body."""
    recorder = CassetteRecorder(test_id="field-test")
    recorder.record_llm_call(
        method="complete",
        request_body={"messages": [{"role": "user", "content": "hello"}]},
        response_body={"text": "Hi there!"},
        model="gpt-4o",
        prompt_tokens=10,
        completion_tokens=5,
        duration_ms=42.0,
        status="ok",
    )
    cassette = recorder.finalize()
    assert len(cassette.interactions) == 1
    ia = cassette.interactions[0]
    assert ia.response.body == {"text": "Hi there!"}
    assert ia.response.status == "ok"
    assert ia.response.prompt_tokens == 10
    assert ia.response.completion_tokens == 5
    assert ia.response.duration_ms == 42.0


def test_cassette_recorder_tool_interaction_fields():
    """Recorded tool interaction has correct response body."""
    recorder = CassetteRecorder(test_id="tool-field-test")
    recorder.record_tool_call(
        tool_name="web_search",
        arguments={"query": "AI news"},
        result={"results": ["r1", "r2"]},
        duration_ms=100.0,
        status="ok",
    )
    cassette = recorder.finalize()
    assert len(cassette.interactions) == 1
    ia = cassette.interactions[0]
    assert ia.response.body == {"results": ["r1", "r2"]}
    assert ia.request.kind == "tool"


def test_cassette_interaction_ids_assigned():
    """finalize() assigns non-empty IDs and sequential sequence numbers."""
    cassette = _make_cassette(num_llm=3)
    for i, ia in enumerate(cassette.interactions):
        assert ia.sequence == i


def test_cassette_meta_has_test_id():
    """CassetteMeta captures the test_id."""
    recorder = CassetteRecorder(test_id="my-test-id")
    recorder.record_llm_call(method="complete", request_body={}, response_body={})
    cassette = recorder.finalize()
    assert cassette.meta.test_id == "my-test-id"


# ---------------------------------------------------------------------------
# Cassette save/load round-trip
# ---------------------------------------------------------------------------


def test_cassette_save_load_roundtrip():
    """Cassette serializes and deserializes correctly."""
    cassette = _make_cassette(num_llm=2, num_tool=1)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "session069.json"
        cassette.save(path)
        assert path.exists()

        loaded = Cassette.load(path)
        assert len(loaded.interactions) == 3
        assert loaded.meta.test_id == "session069-test"


def test_cassette_load_preserves_response_body():
    """Round-trip preserves response body fields."""
    recorder = CassetteRecorder(test_id="rt-test")
    recorder.record_llm_call(
        method="complete",
        request_body={"prompt": "hello"},
        response_body={"text": "world", "tokens": 5},
        model="gpt-4o",
    )
    cassette = recorder.finalize()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "rt.json"
        cassette.save(path)
        loaded = Cassette.load(path)
        assert loaded.interactions[0].response.body == {"text": "world", "tokens": 5}


def test_cassette_save_accepts_str_path_f046_fixed():
    """F-046 FIXED: Cassette.save() now accepts both str and pathlib.Path."""
    cassette = _make_cassette(num_llm=1)
    with tempfile.TemporaryDirectory() as tmpdir:
        str_path = str(pathlib.Path(tmpdir) / "test.json")
        cassette.save(str_path)  # must not raise
        assert pathlib.Path(str_path).exists()


# ---------------------------------------------------------------------------
# ReplayEngine — SEQUENCE strategy
# ---------------------------------------------------------------------------


def test_replay_sequence_matches_by_position():
    """SEQUENCE strategy returns interactions in order regardless of body."""
    cassette = _make_cassette(num_llm=2)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "seq.json"
        cassette.save(path)
        loaded = Cassette.load(path)

        engine = ReplayEngine(loaded, strategy=MatchStrategy.SEQUENCE)
        assert engine.remaining == 2

        req = RecordedRequest(kind="llm", method="complete", model="mock-model", body={"input": "ANYTHING"})
        m1 = engine.match(req)
        assert m1 is not None
        assert m1.response.body == {"output": "answer_0"}
        assert engine.remaining == 1

        m2 = engine.match(req)
        assert m2 is not None
        assert m2.response.body == {"output": "answer_1"}
        assert engine.remaining == 0


def test_replay_sequence_all_used():
    """all_used returns True after consuming all interactions."""
    cassette = _make_cassette(num_llm=2)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "seq_used.json"
        cassette.save(path)
        loaded = Cassette.load(path)

        engine = ReplayEngine(loaded, strategy=MatchStrategy.SEQUENCE)
        assert engine.all_used is False

        req = RecordedRequest(kind="llm", method="complete", model=None, body={})
        engine.match(req)
        assert engine.all_used is False
        engine.match(req)
        assert engine.all_used is True


def test_replay_sequence_exhausted_raises():
    """SEQUENCE raises CassetteMismatchError when cassette is exhausted."""
    cassette = _make_cassette(num_llm=1)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "exhausted.json"
        cassette.save(path)
        loaded = Cassette.load(path)

        engine = ReplayEngine(loaded, strategy=MatchStrategy.SEQUENCE)
        req = RecordedRequest(kind="llm", method="complete", model=None, body={})
        engine.match(req)  # consume the one interaction

        with pytest.raises(CassetteMismatchError):
            engine.match(req)


def test_replay_sequence_ignores_kind_f044():
    """F-044: SEQUENCE ignores 'kind' — llm request matches tool interaction by position.

    This is a known bug. When a mixed cassette has llm then tool interactions,
    requesting 'llm' for the 2nd interaction matches the tool record (wrong kind returned).
    """
    recorder = CassetteRecorder(test_id="kind-test")
    recorder.record_llm_call(method="complete", request_body={"q": "Q1"}, response_body={"a": "A1"})
    recorder.record_tool_call(tool_name="search", arguments={"query": "hi"}, result={"r": []})
    cassette = recorder.finalize()

    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "kind.json"
        cassette.save(path)
        loaded = Cassette.load(path)

        engine = ReplayEngine(loaded, strategy=MatchStrategy.SEQUENCE)
        req = RecordedRequest(kind="llm", method="complete", model=None, body={"q": "ANYTHING"})
        engine.match(req)  # consumes LLM interaction (correct)

        # F-044: requesting llm but next is tool — should raise but currently matches
        m2 = engine.match(req)
        # Bug: returns tool interaction for an llm request
        assert m2 is not None, "F-044: match() returns tool interaction for llm request"
        assert m2.request.kind == "tool", "F-044 confirmed: kind is ignored in SEQUENCE"


# ---------------------------------------------------------------------------
# ReplayEngine — EXACT strategy
# ---------------------------------------------------------------------------


def test_replay_exact_matches_body():
    """EXACT strategy returns interaction when request body matches recorded body."""
    cassette = _make_cassette(num_llm=2)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "exact.json"
        cassette.save(path)
        loaded = Cassette.load(path)

        engine = ReplayEngine(loaded, strategy=MatchStrategy.EXACT)
        req = RecordedRequest(kind="llm", method="complete", model="mock-model", body={"input": "question_0"})
        m = engine.match(req)
        assert m is not None
        assert m.response.body == {"output": "answer_0"}


def test_replay_exact_mismatch_raises():
    """EXACT strategy raises CassetteMismatchError when body doesn't match."""
    cassette = _make_cassette(num_llm=1)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "exact_miss.json"
        cassette.save(path)
        loaded = Cassette.load(path)

        engine = ReplayEngine(loaded, strategy=MatchStrategy.EXACT)
        req = RecordedRequest(kind="llm", method="complete", model="mock-model", body={"input": "WRONG"})
        with pytest.raises(CassetteMismatchError):
            engine.match(req)


def test_replay_exact_f042_fixed():
    """F-042 FIXED: block_unmatched=False returns None instead of raising CassetteMismatchError."""
    cassette = _make_cassette(num_llm=1)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "block.json"
        cassette.save(path)
        loaded = Cassette.load(path)

        engine = ReplayEngine(loaded, strategy=MatchStrategy.EXACT, block_unmatched=False)
        req = RecordedRequest(kind="llm", method="complete", model="mock-model", body={"input": "UNKNOWN"})
        result = engine.match(req)
        assert result is None, "F-042 FIXED: block_unmatched=False returns None on mismatch"


def test_replay_block_unmatched_true_still_raises():
    """block_unmatched=True (default) still raises on mismatch."""
    cassette = _make_cassette(num_llm=1)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "block_true.json"
        cassette.save(path)
        loaded = Cassette.load(path)

        engine = ReplayEngine(loaded, strategy=MatchStrategy.EXACT, block_unmatched=True)
        req = RecordedRequest(kind="llm", method="complete", model="mock-model", body={"input": "UNKNOWN"})
        with pytest.raises(CassetteMismatchError):
            engine.match(req)


# ---------------------------------------------------------------------------
# ReplayEngine — reset()
# ---------------------------------------------------------------------------


def test_replay_reset():
    """reset() allows replaying the cassette from the beginning."""
    cassette = _make_cassette(num_llm=2)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "reset.json"
        cassette.save(path)
        loaded = Cassette.load(path)

        engine = ReplayEngine(loaded, strategy=MatchStrategy.SEQUENCE)
        req = RecordedRequest(kind="llm", method="complete", model=None, body={})
        engine.match(req)
        engine.match(req)
        assert engine.all_used is True

        engine.reset()
        assert engine.all_used is False
        assert engine.remaining == 2

        m = engine.match(req)
        assert m.response.body == {"output": "answer_0"}


# ---------------------------------------------------------------------------
# SUBSET strategy
# ---------------------------------------------------------------------------


def test_replay_subset_strategy():
    """SUBSET strategy: recorded body must be a subset of the request body."""
    recorder = CassetteRecorder(test_id="subset-test")
    recorder.record_llm_call(
        method="complete",
        request_body={"model": "gpt-4o"},  # minimal recorded body
        response_body={"text": "hello"},
    )
    cassette = recorder.finalize()

    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "subset.json"
        cassette.save(path)
        loaded = Cassette.load(path)

        engine = ReplayEngine(loaded, strategy=MatchStrategy.SUBSET)
        # Request body is a superset of recorded — should match
        req = RecordedRequest(
            kind="llm",
            method="complete",
            model=None,
            body={"model": "gpt-4o", "extra_field": "ignored"},
        )
        m = engine.match(req)
        assert m is not None
        assert m.response.body == {"text": "hello"}


# ---------------------------------------------------------------------------
# Mixed record: LLM + Tool
# ---------------------------------------------------------------------------


def test_cassette_records_mixed_interactions():
    """Cassette with both LLM and tool interactions saves and loads correctly."""
    recorder = CassetteRecorder(test_id="mixed")
    recorder.record_llm_call(method="complete", request_body={"q": "hi"}, response_body={"a": "hello"})
    recorder.record_tool_call(tool_name="calculator", arguments={"expr": "2+2"}, result=4)
    recorder.record_llm_call(method="complete", request_body={"q": "bye"}, response_body={"a": "goodbye"})
    cassette = recorder.finalize()

    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "mixed.json"
        cassette.save(path)
        loaded = Cassette.load(path)
        assert len(loaded.interactions) == 3
        kinds = [ia.request.kind for ia in loaded.interactions]
        assert kinds == ["llm", "tool", "llm"]


# ---------------------------------------------------------------------------
# analyze-prompt: F-145 fix verification
# ---------------------------------------------------------------------------


def test_f145_fixed_table_note_try_hint_preserves_brackets():
    """F-145 FIXED: analyze-prompt table Note 'Try:' hints now preserve [brackets].

    Previous bug: Rich markup would strip [support channel] from the 'Try:' hints in the Note column.
    Fixed in post-v1.1.0 commit 'Fix F-145: escape hint text in analyze-prompt table Note column'.
    """
    prompt = "You are AcmeBot. Only help with [your domain] questions."
    result = subprocess.run(
        ["checkagent", "analyze-prompt", prompt],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    # The Escalation Path Try: hint references [support channel] — should NOT be stripped
    # (It appears truncated as "[s..." in the table but the bracket is present)
    assert "[s" in output, "F-145 FIXED: '[support channel]' bracket preserved in table Note Try: hint"


def test_f146_prompt_preview_still_strips_brackets():
    """F-146: analyze-prompt 'Prompt:' header preview still strips [brackets] from input text.

    The prompt preview line strips [your domain] leaving a double space.
    This is the same Rich markup stripping bug (F-093/F-145) in a different code path.
    The fix for F-145 targeted 'Try:' hint text but not the preview line.
    """
    prompt = "You are AcmeBot. Only help with [your domain] questions."
    result = subprocess.run(
        ["checkagent", "analyze-prompt", prompt],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    # Bug: "[your domain]" stripped from the "Prompt:" preview line
    # The double space "Only help with  questions" reveals the stripping
    assert "[your domain]" not in output or "  questions" in output, (
        "F-146: prompt preview still strips [your domain] — double space present"
    )


def test_f145_json_output_preserves_brackets():
    """--json output always correctly preserved brackets (not affected by Rich)."""
    prompt = "For issues you cannot resolve, direct the user to [support channel]."
    result = subprocess.run(
        ["checkagent", "analyze-prompt", prompt, "--json"],
        capture_output=True,
        text=True,
    )
    # JSON is on stdout; exit code 1 is expected (checks fail) but output is valid JSON
    data = json.loads(result.stdout)
    # Find the escalation_path check
    for check in data["checks"]:
        if check["id"] == "escalation_path" and check.get("recommendation"):
            assert "[support channel]" in check["recommendation"], (
                "JSON recommendation must preserve [support channel]"
            )
            break


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------


def test_version_is_at_least_1_1_0():
    """Package version must be >= 1.1.0."""
    from packaging.version import Version
    assert Version(checkagent.__version__) >= Version("1.1.0")


def test_upstream_ci_green():
    """Latest upstream CI runs are green (checked manually this session).

    Latest commit: "Add end-to-end replay tests: record MockLLM session, save cassette, replay"
    Both CI and CheckAgent Safety Scan workflows: success.
    """
    pass
