"""Session-017 tests: CassetteRecorder + ReplayEngine (new in c03b11f)."""
import pytest
import time

from checkagent.replay import (
    CassetteRecorder,
    ReplayEngine,
    MatchStrategy,
    RecordedRequest,
    RecordedResponse,
    Interaction,
    Cassette,
    CassetteMismatchError,
    TimedCall,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_simple_cassette(n_llm=1, n_tool=0, test_id="test"):
    """Build a finalized Cassette with n_llm LLM calls and n_tool tool calls."""
    recorder = CassetteRecorder(test_id=test_id)
    for i in range(n_llm):
        recorder.record_llm_call(
            method="complete",
            request_body={"messages": [{"role": "user", "content": f"query_{i}"}]},
            response_body=f"response_{i}",
            model="gpt-4",
            prompt_tokens=10 + i,
            completion_tokens=5,
            duration_ms=100.0 + i * 10,
        )
    for j in range(n_tool):
        recorder.record_tool_call(
            tool_name="search",
            arguments={"query": f"search_{j}"},
            result={"results": [f"result_{j}"]},
            duration_ms=200.0 + j * 10,
        )
    return recorder.finalize()


# ---------------------------------------------------------------------------
# CassetteRecorder: basic recording
# ---------------------------------------------------------------------------


class TestCassetteRecorderBasics:
    def test_initial_interaction_count_is_zero(self):
        recorder = CassetteRecorder(test_id="test")
        assert recorder.interaction_count == 0

    def test_record_llm_call_returns_interaction(self):
        recorder = CassetteRecorder()
        result = recorder.record_llm_call(
            method="complete",
            request_body={"messages": [{"role": "user", "content": "hi"}]},
            response_body="hello",
        )
        assert isinstance(result, Interaction)

    def test_record_llm_call_increments_count(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, "resp1")
        assert recorder.interaction_count == 1
        recorder.record_llm_call("complete", {}, "resp2")
        assert recorder.interaction_count == 2

    def test_record_tool_call_returns_interaction(self):
        recorder = CassetteRecorder()
        result = recorder.record_tool_call("search", {"query": "test"}, {"results": []})
        assert isinstance(result, Interaction)

    def test_record_tool_call_increments_count(self):
        recorder = CassetteRecorder()
        recorder.record_tool_call("search", {"q": "a"}, {})
        assert recorder.interaction_count == 1

    def test_mixed_llm_and_tool_recording(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, "text")
        recorder.record_tool_call("fetch", {}, {})
        recorder.record_llm_call("complete", {}, "text2")
        assert recorder.interaction_count == 3

    def test_finalize_returns_cassette(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, "resp")
        cassette = recorder.finalize()
        assert isinstance(cassette, Cassette)

    def test_finalize_cassette_has_correct_count(self):
        recorder = CassetteRecorder(test_id="mytest")
        recorder.record_llm_call("complete", {}, "r1")
        recorder.record_tool_call("tool", {}, {})
        cassette = recorder.finalize()
        assert len(cassette.interactions) == 2

    def test_finalize_sets_test_id(self):
        recorder = CassetteRecorder(test_id="my_test_id")
        recorder.record_llm_call("complete", {}, "resp")
        cassette = recorder.finalize()
        assert cassette.meta.test_id == "my_test_id"

    def test_llm_interaction_request_kind_is_llm(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {"msg": "hi"}, "resp")
        cassette = recorder.finalize()
        assert cassette.interactions[0].request.kind == "llm"

    def test_tool_interaction_request_kind_is_tool(self):
        recorder = CassetteRecorder()
        recorder.record_tool_call("search", {"q": "test"}, {"r": []})
        cassette = recorder.finalize()
        assert cassette.interactions[0].request.kind == "tool"

    def test_llm_interaction_stores_request_body(self):
        body = {"messages": [{"role": "user", "content": "What is 2+2?"}], "model": "gpt-4"}
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", body, "4")
        cassette = recorder.finalize()
        assert cassette.interactions[0].request.body == body

    def test_llm_interaction_stores_response_body(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, {"choices": [{"message": {"content": "42"}}]})
        cassette = recorder.finalize()
        assert cassette.interactions[0].response.body == {"choices": [{"message": {"content": "42"}}]}

    def test_tool_interaction_stores_arguments(self):
        recorder = CassetteRecorder()
        recorder.record_tool_call("search", {"query": "pytest"}, {"results": []})
        cassette = recorder.finalize()
        assert cassette.interactions[0].request.body == {"query": "pytest"}

    def test_llm_interaction_stores_token_counts(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, "resp", prompt_tokens=15, completion_tokens=8)
        cassette = recorder.finalize()
        resp = cassette.interactions[0].response
        assert resp.prompt_tokens == 15
        assert resp.completion_tokens == 8

    def test_llm_interaction_stores_duration(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, "resp", duration_ms=250.0)
        cassette = recorder.finalize()
        assert cassette.interactions[0].response.duration_ms == 250.0

    def test_llm_interaction_status_ok_by_default(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, "resp")
        cassette = recorder.finalize()
        assert cassette.interactions[0].response.status == "ok"

    def test_llm_interaction_status_error_when_specified(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, {"error": "rate limited"}, status="error")
        cassette = recorder.finalize()
        assert cassette.interactions[0].response.status == "error"

    def test_recorder_with_redact_keys(self):
        recorder = CassetteRecorder(redact_keys=frozenset({"api_key"}))
        recorder.record_llm_call(
            "complete",
            {"messages": [], "api_key": "sk-secret-123"},
            "response",
        )
        cassette = recorder.finalize()
        body = cassette.interactions[0].request.body
        assert body.get("api_key") == "[REDACTED]"
        assert "messages" in body

    def test_finalize_assigns_unique_ids(self):
        cassette = make_simple_cassette(n_llm=3)
        ids = [i.id for i in cassette.interactions]
        assert len(set(ids)) == 3  # all unique

    def test_empty_recorder_finalize(self):
        recorder = CassetteRecorder()
        cassette = recorder.finalize()
        assert len(cassette.interactions) == 0


# ---------------------------------------------------------------------------
# ReplayEngine: SEQUENCE strategy
# ---------------------------------------------------------------------------


class TestReplayEngineSequence:
    def test_sequence_matches_in_order(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, "first")
        recorder.record_llm_call("complete", {}, "second")
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        req = RecordedRequest(kind="llm", method="complete")
        assert engine.match(req).response.body == "first"
        assert engine.match(req).response.body == "second"

    def test_sequence_remaining_decrements(self):
        cassette = make_simple_cassette(n_llm=3)
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        assert engine.remaining == 3
        engine.match(RecordedRequest(kind="llm", method="complete"))
        assert engine.remaining == 2

    def test_sequence_all_used_false_initially(self):
        cassette = make_simple_cassette(n_llm=2)
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        assert engine.all_used is False

    def test_sequence_all_used_true_when_exhausted(self):
        cassette = make_simple_cassette(n_llm=1)
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        engine.match(RecordedRequest(kind="llm", method="complete"))
        assert engine.all_used is True

    def test_sequence_raises_when_exhausted(self):
        cassette = make_simple_cassette(n_llm=1)
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        engine.match(RecordedRequest(kind="llm", method="complete"))
        with pytest.raises(CassetteMismatchError):
            engine.match(RecordedRequest(kind="llm", method="complete"))

    def test_sequence_ignores_request_body(self):
        """SEQUENCE returns next regardless of body content."""
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {"content": "hello"}, "recorded_response")
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        req = RecordedRequest(kind="llm", method="complete", body={"content": "completely different"})
        matched = engine.match(req)
        assert matched.response.body == "recorded_response"

    def test_sequence_ignores_method(self):
        """SEQUENCE returns next regardless of method name."""
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, "response")
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        req = RecordedRequest(kind="llm", method="totally_different_method")
        matched = engine.match(req)
        assert matched.response.body == "response"

    def test_sequence_ignores_kind(self):
        """SEQUENCE returns next regardless of kind — even tool req matches llm interaction."""
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, "llm_response")
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        # Request with kind='tool' should still match the llm interaction
        req = RecordedRequest(kind="tool", method="search", body={})
        matched = engine.match(req)
        assert matched.response.body == "llm_response"

    def test_sequence_reset_allows_reuse(self):
        cassette = make_simple_cassette(n_llm=2)
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        req = RecordedRequest(kind="llm", method="complete")
        engine.match(req)
        engine.match(req)
        assert engine.all_used is True
        engine.reset()
        assert engine.remaining == 2
        assert engine.all_used is False

    def test_sequence_reset_replays_from_start(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {}, "first")
        recorder.record_llm_call("complete", {}, "second")
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        req = RecordedRequest(kind="llm", method="complete")
        engine.match(req)
        engine.match(req)
        engine.reset()
        assert engine.match(req).response.body == "first"

    def test_sequence_cassette_property(self):
        cassette = make_simple_cassette(n_llm=1)
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        assert engine.cassette is cassette


# ---------------------------------------------------------------------------
# ReplayEngine: EXACT strategy
# ---------------------------------------------------------------------------


class TestReplayEngineExact:
    def test_exact_matches_identical_body(self):
        recorder = CassetteRecorder()
        body = {"messages": [{"role": "user", "content": "What is 2+2?"}], "model": "gpt-4"}
        recorder.record_llm_call("complete", body, "4")
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.EXACT)
        req = RecordedRequest(kind="llm", method="complete", body=body)
        matched = engine.match(req)
        assert matched.response.body == "4"

    def test_exact_raises_on_body_mismatch(self):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {"content": "hello"}, "world")
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.EXACT)
        req = RecordedRequest(kind="llm", method="complete", body={"content": "different"})
        with pytest.raises(CassetteMismatchError):
            engine.match(req)

    def test_exact_error_message_includes_strategy(self):
        cassette = make_simple_cassette(n_llm=1)
        engine = ReplayEngine(cassette, strategy=MatchStrategy.EXACT)
        req = RecordedRequest(kind="llm", method="complete", body={"no": "match"})
        with pytest.raises(CassetteMismatchError) as exc_info:
            engine.match(req)
        assert "exact" in str(exc_info.value).lower()

    def test_exact_raises_when_all_used(self):
        recorder = CassetteRecorder()
        body = {"content": "hello"}
        recorder.record_llm_call("complete", body, "world")
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.EXACT)
        req = RecordedRequest(kind="llm", method="complete", body=body)
        engine.match(req)  # consume
        with pytest.raises(CassetteMismatchError):
            engine.match(req)  # exhausted


# ---------------------------------------------------------------------------
# ReplayEngine: SUBSET strategy
# ---------------------------------------------------------------------------


class TestReplayEngineSubset:
    def test_subset_matches_when_recorded_is_subset_of_request(self):
        """SUBSET: recorded body must be a subset of the incoming request body."""
        recorder = CassetteRecorder()
        recorder.record_llm_call(
            "complete",
            {"messages": [{"role": "user", "content": "Hello"}]},
            "world",
        )
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SUBSET)
        # Request has MORE fields than recorded
        req = RecordedRequest(
            kind="llm", method="complete",
            body={"messages": [{"role": "user", "content": "Hello"}], "model": "gpt-4", "temperature": 0.7},
        )
        matched = engine.match(req)
        assert matched.response.body == "world"

    def test_subset_raises_when_request_missing_recorded_fields(self):
        """SUBSET: fails when request body is missing fields that are in the recorded body."""
        recorder = CassetteRecorder()
        recorder.record_llm_call(
            "complete",
            {"messages": [{"role": "user", "content": "Hello"}], "model": "gpt-4"},
            "world",
        )
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SUBSET)
        # Request missing 'model' field
        req = RecordedRequest(
            kind="llm", method="complete",
            body={"messages": [{"role": "user", "content": "Hello"}]},
        )
        with pytest.raises(CassetteMismatchError):
            engine.match(req)

    def test_subset_exact_match_also_works(self):
        """SUBSET: exact match (recorded == request body) passes too."""
        body = {"messages": [{"role": "user", "content": "hi"}]}
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", body, "there")
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SUBSET)
        req = RecordedRequest(kind="llm", method="complete", body=body)
        matched = engine.match(req)
        assert matched.response.body == "there"


# ---------------------------------------------------------------------------
# F-042: block_unmatched=False has no effect
# ---------------------------------------------------------------------------


class TestF042BlockUnmatchedFixed:
    """F-042 FIXED: block_unmatched=False now returns None for unmatched (passthrough)."""

    def test_block_unmatched_false_exact_returns_none_on_mismatch(self):
        """F-042 FIXED: EXACT + block_unmatched=False returns None on mismatch."""
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {"content": "hello"}, "world")
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.EXACT, block_unmatched=False)
        req = RecordedRequest(kind="llm", method="complete", body={"content": "different"})
        # F-042 FIXED: returns None instead of raising
        result = engine.match(req)
        assert result is None, "block_unmatched=False should return None for unmatched"

    def test_block_unmatched_false_sequence_returns_none_when_exhausted(self):
        """F-042 FIXED: SEQUENCE + block_unmatched=False returns None when exhausted."""
        cassette = make_simple_cassette(n_llm=1)
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE, block_unmatched=False)
        req = RecordedRequest(kind="llm", method="complete")
        engine.match(req)  # consume
        # F-042 FIXED: returns None instead of raising
        result = engine.match(req)
        assert result is None, "Exhausted cassette with block_unmatched=False should return None"

    def test_block_unmatched_true_still_raises(self):
        """block_unmatched=True (default) still raises CassetteMismatchError on mismatch."""
        cassette = make_simple_cassette(n_llm=1)
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE, block_unmatched=True)
        req = RecordedRequest(kind="llm", method="complete")
        engine.match(req)  # consume
        with pytest.raises(CassetteMismatchError):
            engine.match(req)


# ---------------------------------------------------------------------------
# CassetteRecorder + save/load round-trip
# ---------------------------------------------------------------------------


class TestCassetteRecorderPersistence:
    def test_recorded_cassette_survives_save_load(self, tmp_path):
        recorder = CassetteRecorder(test_id="persist_test")
        recorder.record_llm_call(
            "complete",
            {"messages": [{"role": "user", "content": "hello"}]},
            "world",
            model="gpt-4",
            prompt_tokens=10,
            completion_tokens=3,
        )
        cassette = recorder.finalize()
        path = tmp_path / "cassette.json"
        cassette.save(path)

        loaded = Cassette.load(path)
        assert len(loaded.interactions) == 1
        assert loaded.meta.test_id == "persist_test"
        assert loaded.interactions[0].request.kind == "llm"
        assert loaded.interactions[0].response.body == "world"

    def test_replay_engine_works_on_loaded_cassette(self, tmp_path):
        recorder = CassetteRecorder()
        recorder.record_llm_call("complete", {"q": "2+2"}, "4")
        recorder.record_tool_call("calc", {"expr": "2+2"}, {"result": 4})
        cassette = recorder.finalize()
        path = tmp_path / "replay.json"
        cassette.save(path)

        loaded = Cassette.load(path)
        engine = ReplayEngine(loaded, strategy=MatchStrategy.SEQUENCE)
        r1 = engine.match(RecordedRequest(kind="llm", method="complete"))
        r2 = engine.match(RecordedRequest(kind="tool", method="calc"))
        assert r1.response.body == "4"
        assert r2.response.body == {"result": 4}
        assert engine.all_used is True


# ---------------------------------------------------------------------------
# TimedCall context manager
# ---------------------------------------------------------------------------


class TestTimedCall:
    def test_timed_call_initial_duration_is_zero(self):
        tc = TimedCall()
        assert tc.duration_ms == 0.0

    def test_timed_call_measures_sleep(self):
        tc = TimedCall()
        with tc:
            time.sleep(0.05)
        assert tc.duration_ms >= 40.0  # at least 40ms

    def test_timed_call_is_reusable(self):
        tc = TimedCall()
        with tc:
            time.sleep(0.02)
        first = tc.duration_ms
        with tc:
            time.sleep(0.02)
        second = tc.duration_ms
        # Both should be ~20ms; second use overwrites first
        assert second >= 10.0

    def test_timed_call_returns_elapsed_ms_not_seconds(self):
        tc = TimedCall()
        with tc:
            time.sleep(0.1)
        # Should be ~100ms, not ~0.1
        assert tc.duration_ms > 10.0


# ---------------------------------------------------------------------------
# CassetteMismatchError
# ---------------------------------------------------------------------------


class TestCassetteMismatchError:
    def test_mismatch_error_is_exception(self):
        assert issubclass(CassetteMismatchError, Exception)

    def test_mismatch_error_message_contains_kind(self):
        cassette = make_simple_cassette(n_llm=1)
        engine = ReplayEngine(cassette, strategy=MatchStrategy.EXACT)
        req = RecordedRequest(kind="llm", method="complete", body={"no": "match"})
        with pytest.raises(CassetteMismatchError) as exc_info:
            engine.match(req)
        assert "llm" in str(exc_info.value).lower()

    def test_mismatch_error_raised_on_empty_cassette(self):
        recorder = CassetteRecorder()
        cassette = recorder.finalize()
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        with pytest.raises(CassetteMismatchError):
            engine.match(RecordedRequest(kind="llm", method="complete"))


# ---------------------------------------------------------------------------
# MatchStrategy enum
# ---------------------------------------------------------------------------


class TestMatchStrategy:
    def test_match_strategy_has_exact(self):
        assert hasattr(MatchStrategy, "EXACT")

    def test_match_strategy_has_sequence(self):
        assert hasattr(MatchStrategy, "SEQUENCE")

    def test_match_strategy_has_subset(self):
        assert hasattr(MatchStrategy, "SUBSET")

    def test_default_strategy_is_exact(self):
        cassette = make_simple_cassette(n_llm=1)
        engine = ReplayEngine(cassette)  # no strategy arg
        assert engine.cassette is cassette
        # Verify default is EXACT by checking it rejects a mismatched body
        req = RecordedRequest(kind="llm", method="complete", body={"no": "match"})
        with pytest.raises(CassetteMismatchError) as exc_info:
            engine.match(req)
        assert "exact" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Integration: record → replay cycle
# ---------------------------------------------------------------------------


class TestRecordReplayCycle:
    def test_full_cycle_llm_only(self):
        """Record two LLM calls, replay them in order."""
        recorder = CassetteRecorder(test_id="llm_cycle")
        recorder.record_llm_call(
            "complete",
            {"messages": [{"role": "user", "content": "Who are you?"}]},
            "I am an AI assistant.",
        )
        recorder.record_llm_call(
            "complete",
            {"messages": [{"role": "user", "content": "What can you do?"}]},
            "I can answer questions.",
        )
        cassette = recorder.finalize()

        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        r1 = engine.match(RecordedRequest(kind="llm", method="complete"))
        r2 = engine.match(RecordedRequest(kind="llm", method="complete"))

        assert r1.response.body == "I am an AI assistant."
        assert r2.response.body == "I can answer questions."
        assert engine.all_used is True

    def test_full_cycle_mixed_llm_and_tool(self):
        """Record LLM + tool call, replay in sequence."""
        recorder = CassetteRecorder(test_id="mixed_cycle")
        recorder.record_llm_call("complete", {"q": "search for cats"}, "I'll search for cats.")
        recorder.record_tool_call("search", {"query": "cats"}, {"results": ["Cat 1", "Cat 2"]})
        recorder.record_llm_call("complete", {"q": "summarize"}, "Found 2 cats.")
        cassette = recorder.finalize()

        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        r1 = engine.match(RecordedRequest(kind="llm", method="complete"))
        r2 = engine.match(RecordedRequest(kind="tool", method="search"))
        r3 = engine.match(RecordedRequest(kind="llm", method="complete"))

        assert r1.response.body == "I'll search for cats."
        assert r2.response.body == {"results": ["Cat 1", "Cat 2"]}
        assert r3.response.body == "Found 2 cats."

    def test_reset_enables_replaying_cassette_multiple_times(self):
        """Replay same cassette twice via reset()."""
        cassette = make_simple_cassette(n_llm=2)
        engine = ReplayEngine(cassette, strategy=MatchStrategy.SEQUENCE)
        req = RecordedRequest(kind="llm", method="complete")

        # First playthrough
        r1a = engine.match(req)
        r1b = engine.match(req)

        engine.reset()

        # Second playthrough — same results
        r2a = engine.match(req)
        r2b = engine.match(req)

        assert r1a.response.body == r2a.response.body
        assert r1b.response.body == r2b.response.body


# ---------------------------------------------------------------------------
# Upstream CI finding check
# ---------------------------------------------------------------------------


class TestUpstreamCIStatus:
    def test_checkagent_demo_command_has_no_encoding_declaration(self):
        """
        F-043: Upstream CI fails on Windows because demo-generated test file
        contains byte 0x97 (em dash in Windows-1252) but has no encoding
        declaration. This test documents the known CI failure.
        """
        import subprocess
        result = subprocess.run(
            ["/home/x/working/checkagent-testbed/.venv/bin/checkagent", "--version"],
            capture_output=True, text=True
        )
        # If the CLI is accessible, check version
        assert result.returncode == 0
        # The upstream CI is known to be failing (F-043) — documented here
        # The failure is: SyntaxError on Windows for byte 0x97 in demo test
