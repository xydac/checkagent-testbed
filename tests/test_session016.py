"""Session 016 — Cassette data model (checkagent.replay)

Focus:
- Verify F-036 regression is fixed (all 10 xfails from session-015 now pass)
- Explore new checkagent.replay cassette module added in 6a8eaf4
- Document findings: F-039, F-040, F-041
- CI status: upstream CI still red (F-008: jsonschema missing dep)

Upgrade: ed0b21a → 6a8eaf4
"""

import json
import tempfile
import warnings
from pathlib import Path

import pytest

pytest_plugins = ["checkagent"]


# ---------------------------------------------------------------------------
# F-036 FIXED: all modules restored (xfails now pass — promote these)
# ---------------------------------------------------------------------------


class TestF036Fixed:
    """F-036 regression (ed0b21a stripping modules) is fixed in 6a8eaf4."""

    def test_datasets_importable(self):
        from checkagent.datasets import (
            GoldenDataset,
            TestCase,
            load_dataset,
            load_cases,
            parametrize_cases,
        )

        assert GoldenDataset is not None

    def test_eval_metrics_importable(self):
        from checkagent.eval.metrics import (
            task_completion,
            step_efficiency,
            tool_correctness,
            trajectory_match,
        )

        assert callable(task_completion)

    def test_eval_aggregate_importable(self):
        from checkagent.eval.aggregate import (
            aggregate_scores,
            RunSummary,
            detect_regressions,
            compute_step_stats,
        )

        assert RunSummary is not None

    def test_eval_evaluator_importable(self):
        from checkagent.eval.evaluator import Evaluator, EvaluatorRegistry

        assert Evaluator is not None

    def test_ci_importable(self):
        from checkagent.ci import (
            GateResult,
            GateVerdict,
            QualityGateReport,
            evaluate_gates,
            generate_pr_comment,
        )

        assert evaluate_gates is not None

    def test_safety_importable(self):
        from checkagent.safety import (
            PromptInjectionDetector,
            PIILeakageScanner,
            ToolCallBoundaryValidator,
        )

        assert PromptInjectionDetector is not None

    def test_cost_tracking_importable(self):
        from checkagent import (
            CostTracker,
            CostBreakdown,
            CostReport,
            BudgetExceededError,
        )

        assert CostTracker is not None


# ---------------------------------------------------------------------------
# CI status (informational — F-008 breaks checkagent's own CI)
# ---------------------------------------------------------------------------


class TestCIStatusFinding:
    """Upstream CI is red due to F-008 (jsonschema undeclared dependency).

    This is documented; tests here just verify the local environment works
    because we manually installed jsonschema.
    """

    def test_jsonschema_installed_locally(self):
        """We manually installed jsonschema (workaround for F-008).

        Upstream CI is broken because jsonschema isn't in checkagent's deps.
        """
        import jsonschema

        assert jsonschema is not None

    def test_assert_json_schema_works_when_dep_present(self):
        from checkagent import assert_json_schema

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        # Should not raise — dep is present locally
        assert_json_schema({"name": "Alice"}, schema)


# ---------------------------------------------------------------------------
# New: checkagent.replay cassette module
# ---------------------------------------------------------------------------


class TestCassetteImports:
    """F-041: Cassette types not exported from top-level checkagent."""

    def test_cassette_not_at_top_level(self):
        """F-041: Cassette and friends absent from top-level checkagent namespace."""
        import checkagent

        assert not hasattr(checkagent, "Cassette")
        assert not hasattr(checkagent, "CassetteMeta")
        assert not hasattr(checkagent, "Interaction")
        assert not hasattr(checkagent, "RecordedRequest")
        assert not hasattr(checkagent, "RecordedResponse")
        assert not hasattr(checkagent, "redact_dict")

    def test_replay_submodule_accessible(self):
        """checkagent.replay is accessible as a submodule (not top-level)."""
        from checkagent import replay

        assert hasattr(replay, "Cassette")

    def test_cassette_importable_from_submodule(self):
        from checkagent.replay import (
            Cassette,
            CassetteMeta,
            Interaction,
            RecordedRequest,
            RecordedResponse,
            redact_dict,
            CASSETTE_SCHEMA_VERSION,
        )

        assert CASSETTE_SCHEMA_VERSION == 1


class TestCassetteCreation:
    """Basic cassette construction and defaults."""

    def test_empty_cassette_defaults(self):
        from checkagent.replay import Cassette

        c = Cassette()
        assert c.meta.schema_version == 1
        assert len(c.interactions) == 0
        assert c.meta.content_hash == ""
        assert c.meta.test_id == ""

    def test_cassette_meta_recorded_at_auto_set(self):
        from checkagent.replay import CassetteMeta

        meta = CassetteMeta()
        assert meta.recorded_at  # non-empty

    def test_interaction_id_empty_before_finalize(self):
        from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse

        c = Cassette()
        c.interactions.append(
            Interaction(
                request=RecordedRequest(kind="llm", method="chat", body={"q": "hello"}),
                response=RecordedResponse(status="ok", body="hi"),
            )
        )
        assert c.interactions[0].id == ""

    def test_finalize_assigns_id_and_sequence(self):
        from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse

        c = Cassette()
        for i in range(3):
            c.interactions.append(
                Interaction(
                    request=RecordedRequest(
                        kind="llm", method="chat", body={"prompt": f"msg {i}"}
                    ),
                    response=RecordedResponse(status="ok", body=f"response {i}"),
                )
            )
        c.finalize()
        assert [ix.sequence for ix in c.interactions] == [0, 1, 2]
        assert all(len(ix.id) == 16 for ix in c.interactions)

    def test_finalize_sets_content_hash(self):
        from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse

        c = Cassette()
        c.interactions.append(
            Interaction(
                request=RecordedRequest(kind="tool", method="search", body={"q": "cats"}),
                response=RecordedResponse(status="ok", body=["cat1"]),
            )
        )
        c.finalize()
        assert len(c.meta.content_hash) == 64  # SHA-256 hex


class TestInteractionIdDeterminism:
    """Interaction.compute_id() is deterministic and unique per request."""

    def test_same_request_same_id(self):
        from checkagent.replay import Interaction, RecordedRequest, RecordedResponse

        req = RecordedRequest(kind="llm", method="chat", body={"prompt": "hello"})
        resp = RecordedResponse(status="ok", body="hi")
        i1 = Interaction(request=req, response=resp)
        i2 = Interaction(request=req, response=resp)
        assert i1.compute_id() == i2.compute_id()

    def test_different_request_different_id(self):
        from checkagent.replay import Interaction, RecordedRequest, RecordedResponse

        resp = RecordedResponse(status="ok", body="hi")
        i1 = Interaction(
            request=RecordedRequest(kind="llm", method="chat", body={"prompt": "hello"}),
            response=resp,
        )
        i2 = Interaction(
            request=RecordedRequest(kind="llm", method="chat", body={"prompt": "world"}),
            response=resp,
        )
        assert i1.compute_id() != i2.compute_id()

    def test_finalize_all_ids_unique(self):
        from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse

        c = Cassette()
        for i in range(5):
            c.interactions.append(
                Interaction(
                    request=RecordedRequest(
                        kind="llm", method="chat", body={"step": i}
                    ),
                    response=RecordedResponse(status="ok", body=f"r{i}"),
                )
            )
        c.finalize()
        ids = [ix.id for ix in c.interactions]
        assert len(set(ids)) == len(ids), "All IDs should be unique"


class TestVerifyIntegrity:
    """Cassette content hash integrity checks."""

    def test_integrity_ok_after_finalize(self):
        from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse

        c = Cassette()
        c.interactions.append(
            Interaction(
                request=RecordedRequest(kind="llm", method="chat", body={"q": "hi"}),
                response=RecordedResponse(status="ok", body="hello"),
            )
        )
        c.finalize()
        assert c.verify_integrity() is True

    def test_integrity_fails_after_tamper(self):
        from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse

        c = Cassette()
        c.interactions.append(
            Interaction(
                request=RecordedRequest(kind="llm", method="chat", body={"q": "hi"}),
                response=RecordedResponse(status="ok", body="hello"),
            )
        )
        c.finalize()
        # Tamper with interaction body
        c.interactions[0].response.body = "tampered!"
        assert c.verify_integrity() is False

    def test_empty_cassette_no_hash_skips_check(self):
        from checkagent.replay import Cassette

        c = Cassette()
        # No hash stored — verify_integrity should return True (nothing to check)
        assert c.verify_integrity() is True


class TestSerializationRoundTrip:
    """JSON serialization/deserialization preserves all data."""

    def test_to_json_from_json_roundtrip(self):
        from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse

        c = Cassette()
        c.interactions.append(
            Interaction(
                request=RecordedRequest(
                    kind="tool", method="search", body={"query": "cats"}
                ),
                response=RecordedResponse(
                    status="ok",
                    body=["cat1", "cat2"],
                    duration_ms=42.5,
                ),
            )
        )
        c.finalize()

        c2 = Cassette.from_json(c.to_json())
        assert c2.meta.content_hash == c.meta.content_hash
        assert len(c2.interactions) == 1
        assert c2.interactions[0].request.body["query"] == "cats"
        assert c2.interactions[0].response.duration_ms == 42.5

    def test_json_top_level_keys(self):
        from checkagent.replay import Cassette

        c = Cassette()
        c.finalize()
        parsed = json.loads(c.to_json())
        assert set(parsed.keys()) == {"meta", "interactions"}

    def test_meta_keys_in_json(self):
        from checkagent.replay import Cassette

        c = Cassette()
        c.finalize()
        parsed = json.loads(c.to_json())
        assert "schema_version" in parsed["meta"]
        assert "content_hash" in parsed["meta"]
        assert "recorded_at" in parsed["meta"]

    def test_error_response_roundtrip(self):
        from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse

        c = Cassette()
        c.interactions.append(
            Interaction(
                request=RecordedRequest(kind="tool", method="db_query", body={"sql": "SELECT 1"}),
                response=RecordedResponse(status="error", body={"error": "connection refused"}),
            )
        )
        c.finalize()
        c2 = Cassette.from_json(c.to_json())
        assert c2.interactions[0].response.status == "error"
        assert c2.interactions[0].response.body["error"] == "connection refused"


class TestFileIO:
    """Cassette.save() and Cassette.load() work correctly."""

    def test_save_creates_file(self, tmp_path):
        from checkagent.replay import Cassette

        c = Cassette()
        c.finalize()
        path = tmp_path / "test.json"
        c.save(path)
        assert path.exists()

    def test_save_creates_parent_dirs(self, tmp_path):
        from checkagent.replay import Cassette

        c = Cassette()
        c.finalize()
        path = tmp_path / "deep" / "nested" / "dir" / "test.json"
        c.save(path)
        assert path.exists()

    def test_load_roundtrip(self, tmp_path):
        from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse

        c = Cassette()
        c.interactions.append(
            Interaction(
                request=RecordedRequest(kind="llm", method="chat", body={"q": "hello"}),
                response=RecordedResponse(status="ok", body="hi", prompt_tokens=5, completion_tokens=3),
            )
        )
        c.finalize()

        path = tmp_path / "cassette.json"
        c.save(path)
        loaded = Cassette.load(path)

        assert loaded.meta.content_hash == c.meta.content_hash
        assert len(loaded.interactions) == 1
        assert loaded.interactions[0].response.prompt_tokens == 5

    def test_load_old_schema_emits_warning(self, tmp_path):
        """Cassette with schema_version < current emits a deprecation warning."""
        from checkagent.replay import Cassette, CASSETTE_SCHEMA_VERSION

        path = tmp_path / "old.json"
        old_data = {
            "meta": {
                "schema_version": 0,
                "checkagent_version": "",
                "recorded_at": "2025-01-01T00:00:00+00:00",
                "content_hash": "",
                "test_id": "",
            },
            "interactions": [],
        }
        path.write_text(json.dumps(old_data))

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Cassette.load(path)
            assert len(w) == 1
            assert "migrate-cassettes" in str(w[0].message)

    def test_cassette_path_helper_builds_correct_path(self, tmp_path):
        from checkagent.replay import Cassette

        path = Cassette.cassette_path(tmp_path, "tests::TestFoo::test_bar", "abc123def456789")
        assert path.parent == tmp_path / "tests" / "TestFoo" / "test_bar"
        assert path.name == "abc123def456.json"

    def test_cassette_path_spaces_replaced(self, tmp_path):
        from checkagent.replay import Cassette

        path = Cassette.cassette_path(tmp_path, "tests::test func with spaces", "abc123def456789")
        assert "test_func_with_spaces" in str(path)


class TestShortHash:
    """short_hash() returns first 12 chars of content hash."""

    def test_short_hash_length(self):
        from checkagent.replay import Cassette

        c = Cassette()
        c.finalize()
        assert len(c.short_hash()) == 12

    def test_short_hash_matches_content_hash_prefix(self):
        from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse

        c = Cassette()
        c.interactions.append(
            Interaction(
                request=RecordedRequest(kind="llm", method="chat", body={"q": "test"}),
                response=RecordedResponse(status="ok", body="result"),
            )
        )
        c.finalize()
        assert c.short_hash() == c.meta.content_hash[:12]

    def test_different_cassettes_different_hashes(self):
        from checkagent.replay import Cassette, Interaction, RecordedRequest, RecordedResponse

        def make_cassette(prompt):
            c = Cassette()
            c.interactions.append(
                Interaction(
                    request=RecordedRequest(kind="llm", method="chat", body={"q": prompt}),
                    response=RecordedResponse(status="ok", body="ok"),
                )
            )
            c.finalize()
            return c

        c1 = make_cassette("hello")
        c2 = make_cassette("world")
        assert c1.short_hash() != c2.short_hash()


class TestRedactDict:
    """redact_dict() sanitizes sensitive keys recursively."""

    def test_api_key_redacted(self):
        from checkagent.replay import redact_dict

        d = {"api_key": "sk-secret", "model": "gpt-4"}
        result = redact_dict(d)
        assert result["api_key"] == "[REDACTED]"
        assert result["model"] == "gpt-4"

    def test_authorization_redacted(self):
        from checkagent.replay import redact_dict

        d = {"authorization": "Bearer tok123", "safe": "value"}
        result = redact_dict(d)
        assert result["authorization"] == "[REDACTED]"
        assert result["safe"] == "value"

    def test_nested_dict_redacted(self):
        from checkagent.replay import redact_dict

        d = {"headers": {"x-api-key": "secret", "content-type": "application/json"}}
        result = redact_dict(d)
        assert result["headers"]["x-api-key"] == "[REDACTED]"
        assert result["headers"]["content-type"] == "application/json"

    def test_list_of_dicts_redacted(self):
        from checkagent.replay import redact_dict

        d = {"items": [{"token": "abc", "name": "foo"}, {"name": "bar"}]}
        result = redact_dict(d)
        assert result["items"][0]["token"] == "[REDACTED]"
        assert result["items"][0]["name"] == "foo"
        assert result["items"][1]["name"] == "bar"

    def test_original_dict_not_mutated(self):
        from checkagent.replay import redact_dict

        d = {"api_key": "secret"}
        redact_dict(d)
        assert d["api_key"] == "secret"  # original unchanged

    def test_non_dict_values_preserved(self):
        from checkagent.replay import redact_dict

        d = {"count": 42, "flag": True, "items": [1, 2, 3]}
        result = redact_dict(d)
        assert result["count"] == 42
        assert result["flag"] is True
        assert result["items"] == [1, 2, 3]


class TestF039MigrateCassettesCommandMissing:
    """F-039: Cassette.load() warns about 'checkagent migrate-cassettes' command
    that does not exist in the CLI.
    """

    def test_warning_references_nonexistent_command(self, tmp_path):
        from checkagent.replay import Cassette

        path = tmp_path / "old.json"
        old_data = {
            "meta": {
                "schema_version": 0,
                "checkagent_version": "",
                "recorded_at": "2025-01-01T00:00:00+00:00",
                "content_hash": "",
                "test_id": "",
            },
            "interactions": [],
        }
        path.write_text(json.dumps(old_data))

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Cassette.load(path)
            assert len(w) == 1
            warning_msg = str(w[0].message)
            assert "migrate-cassettes" in warning_msg

    def test_migrate_cassettes_in_cli(self):
        """F-039 partially fixed: migrate-cassettes command now exists in checkagent CLI.
        (v0->v1 migration still unimplemented — see F-045)
        """
        import subprocess

        result = subprocess.run(
            [".venv/bin/checkagent", "--help"],
            capture_output=True,
            text=True,
        )
        assert "migrate-cassettes" in result.stdout, (
            "migrate-cassettes command not found in CLI. Was it removed?"
        )


class TestF040CheckagentVersionNotPopulated:
    """F-040: CassetteMeta.checkagent_version is never set by finalize().

    The field exists for provenance tracking, but finalize() leaves it as ''
    even though checkagent.__version__ is available.
    """

    def test_checkagent_version_empty_after_finalize(self):
        from checkagent.replay import Cassette

        c = Cassette()
        c.finalize()
        assert c.meta.checkagent_version == "", (
            "F-040: checkagent_version should be auto-populated from "
            "checkagent.__version__ but is always empty"
        )

    def test_checkagent_has_version(self):
        import checkagent

        assert hasattr(checkagent, "__version__")
        assert checkagent.__version__  # non-empty


class TestCassetteMarkerStillNoOp:
    """@pytest.mark.cassette marker is registered but still has no behavior.

    The new cassette data model is available, but the marker doesn't
    auto-load or auto-save cassettes. It's still just a label.
    """

    @pytest.mark.cassette(path="cassettes/test_cassette_marker.json")
    def test_cassette_marker_accepted_no_error(self):
        """@pytest.mark.cassette runs without error — it's a no-op."""
        from checkagent.replay import Cassette

        # Nothing auto-loaded or auto-saved — user must do it manually
        c = Cassette()
        assert len(c.interactions) == 0
