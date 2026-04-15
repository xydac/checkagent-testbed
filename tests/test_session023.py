"""Session 023 — trace_import module: JsonFileImporter, OtelJsonImporter, PiiScrubber, generate_test_cases.

New feature: production trace import (checkagent import-trace CLI + trace_import API).
Tests verify: JSON/JSONL/OTel import, PII scrubbing, test case generation, CLI behavior.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

import pytest

from checkagent.core.types import AgentInput, AgentRun, Step, ToolCall
from checkagent.trace_import import (
    JsonFileImporter,
    OtelJsonImporter,
    PiiScrubber,
    TraceImporter,
    generate_test_cases,
)


# ---------------------------------------------------------------------------
# TraceImporter protocol
# ---------------------------------------------------------------------------

class TestTraceImporterProtocol:
    def test_json_importer_satisfies_protocol(self):
        importer = JsonFileImporter()
        assert isinstance(importer, TraceImporter)

    def test_otel_importer_satisfies_protocol(self):
        importer = OtelJsonImporter()
        assert isinstance(importer, TraceImporter)


# ---------------------------------------------------------------------------
# JsonFileImporter — file loading
# ---------------------------------------------------------------------------

class TestJsonFileImporterFileLoading:
    def test_file_not_found_raises(self, tmp_path):
        importer = JsonFileImporter()
        with pytest.raises(FileNotFoundError, match="Trace file not found"):
            importer.import_traces(str(tmp_path / "nonexistent.json"))

    def test_json_list_format(self, tmp_path):
        data = [
            {"input": "What is 2+2?", "output": "4"},
            {"input": "Who wrote Hamlet?", "output": "Shakespeare"},
        ]
        f = tmp_path / "traces.json"
        f.write_text(json.dumps(data))
        importer = JsonFileImporter()
        runs = importer.import_traces(str(f))
        assert len(runs) == 2
        assert runs[0].input.query == "What is 2+2?"
        assert runs[0].final_output == "4"

    def test_json_single_object_wrapped_in_list(self, tmp_path):
        data = {"input": "Single trace", "output": "Result"}
        f = tmp_path / "trace.json"
        f.write_text(json.dumps(data))
        importer = JsonFileImporter()
        runs = importer.import_traces(str(f))
        assert len(runs) == 1
        assert runs[0].input.query == "Single trace"

    def test_jsonl_format(self, tmp_path):
        f = tmp_path / "traces.jsonl"
        lines = [
            json.dumps({"input": "First", "output": "A"}),
            "",  # blank line should be skipped
            json.dumps({"input": "Second", "output": "B"}),
        ]
        f.write_text("\n".join(lines))
        importer = JsonFileImporter()
        runs = importer.import_traces(str(f))
        assert len(runs) == 2
        assert runs[0].input.query == "First"
        assert runs[1].input.query == "Second"

    def test_limit_parameter(self, tmp_path):
        data = [{"input": f"query {i}", "output": f"result {i}"} for i in range(10)]
        f = tmp_path / "traces.json"
        f.write_text(json.dumps(data))
        importer = JsonFileImporter()
        runs = importer.import_traces(str(f), limit=3)
        assert len(runs) == 3
        assert runs[0].input.query == "query 0"

    def test_limit_larger_than_dataset(self, tmp_path):
        data = [{"input": "q", "output": "a"}]
        f = tmp_path / "traces.json"
        f.write_text(json.dumps(data))
        importer = JsonFileImporter()
        runs = importer.import_traces(str(f), limit=100)
        assert len(runs) == 1


# ---------------------------------------------------------------------------
# JsonFileImporter — filter support
# ---------------------------------------------------------------------------

class TestJsonFileImporterFilters:
    @pytest.fixture
    def mixed_traces_file(self, tmp_path):
        data = [
            {"input": "q1", "output": "a1"},
            {"input": "q2", "output": None, "error": "TimeoutError"},
            {"input": "q3", "output": "a3"},
        ]
        f = tmp_path / "mixed.json"
        f.write_text(json.dumps(data))
        return str(f)

    def test_filter_error(self, mixed_traces_file):
        importer = JsonFileImporter()
        runs = importer.import_traces(mixed_traces_file, filters={"status": "error"})
        assert len(runs) == 1
        assert runs[0].error == "TimeoutError"

    def test_filter_success(self, mixed_traces_file):
        importer = JsonFileImporter()
        runs = importer.import_traces(mixed_traces_file, filters={"status": "success"})
        assert len(runs) == 2
        assert all(r.error is None for r in runs)

    def test_no_filter_returns_all(self, mixed_traces_file):
        importer = JsonFileImporter()
        runs = importer.import_traces(mixed_traces_file)
        assert len(runs) == 3


# ---------------------------------------------------------------------------
# JsonFileImporter — normalization formats
# ---------------------------------------------------------------------------

class TestJsonFileImporterNormalization:
    def test_flat_format_input_output(self, tmp_path):
        data = [{"input": "hello", "output": "world", "duration_ms": 150.0}]
        f = tmp_path / "t.json"
        f.write_text(json.dumps(data))
        runs = JsonFileImporter().import_traces(str(f))
        run = runs[0]
        assert run.input.query == "hello"
        assert run.final_output == "world"
        assert run.duration_ms == 150.0

    def test_flat_format_missing_input_defaults_to_empty_string(self, tmp_path):
        data = [{"output": "answer"}]
        f = tmp_path / "t.json"
        f.write_text(json.dumps(data))
        runs = JsonFileImporter().import_traces(str(f))
        assert runs[0].input.query == ""

    def test_flat_format_error_field(self, tmp_path):
        data = [{"input": "q", "error": "ServiceDown"}]
        f = tmp_path / "t.json"
        f.write_text(json.dumps(data))
        runs = JsonFileImporter().import_traces(str(f))
        assert runs[0].error == "ServiceDown"
        assert runs[0].final_output is None

    def test_native_format_with_steps_and_tool_calls(self, tmp_path):
        data = [{
            "input": "search for cats",
            "steps": [{
                "step_index": 0,
                "input_text": "search cats",
                "output_text": "5 results",
                "tool_calls": [{"name": "web_search", "arguments": {"q": "cats"}, "result": "..."}],
                "model": "gpt-4o",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "duration_ms": 800.0,
            }],
            "final_output": "Found 5 cats",
            "duration_ms": 1000.0,
        }]
        f = tmp_path / "t.json"
        f.write_text(json.dumps(data))
        runs = JsonFileImporter().import_traces(str(f))
        run = runs[0]
        assert run.input.query == "search for cats"
        assert run.final_output == "Found 5 cats"
        assert len(run.steps) == 1
        assert run.steps[0].model == "gpt-4o"
        assert run.steps[0].prompt_tokens == 100
        assert len(run.tool_calls) == 1
        assert run.tool_calls[0].name == "web_search"
        assert run.tool_calls[0].arguments == {"q": "cats"}

    def test_span_format(self, tmp_path):
        data = [{
            "input": "find dogs",
            "spans": [{
                "input": "LLM reasoning",
                "output": "let me search",
                "tool_calls": [{"name": "search", "arguments": {"q": "dogs"}, "result": "10 results"}],
                "model": "gpt-4",
                "duration_ms": 700.0,
            }],
            "output": "Found 10 dogs",
        }]
        f = tmp_path / "t.json"
        f.write_text(json.dumps(data))
        runs = JsonFileImporter().import_traces(str(f))
        run = runs[0]
        assert run.input.query == "find dogs"
        assert run.final_output == "Found 10 dogs"
        assert len(run.steps) == 1
        assert run.steps[0].output_text == "let me search"
        assert len(run.tool_calls) == 1
        assert run.tool_calls[0].name == "search"

    def test_dict_input_extracts_query_field(self, tmp_path):
        data = [{"input": {"query": "structured query", "context": {"user": "alice"}}, "output": "ok"}]
        f = tmp_path / "t.json"
        f.write_text(json.dumps(data))
        runs = JsonFileImporter().import_traces(str(f))
        assert runs[0].input.query == "structured query"


# ---------------------------------------------------------------------------
# OtelJsonImporter
# ---------------------------------------------------------------------------

def _make_otel_data(traces: list[list[dict]]) -> dict:
    """Build minimal OTLP JSON structure for testing."""
    spans = []
    for trace_spans in traces:
        spans.extend(trace_spans)
    return {"resourceSpans": [{"scopeSpans": [{"spans": spans}]}]}


class TestOtelJsonImporter:
    def test_file_not_found_raises(self, tmp_path):
        importer = OtelJsonImporter()
        with pytest.raises(FileNotFoundError, match="OTel trace file not found"):
            importer.import_traces(str(tmp_path / "no.json"))

    def test_basic_trace_import(self, tmp_path):
        data = _make_otel_data([[
            {
                "traceId": "abc123",
                "spanId": "root1",
                "name": "agent.run",
                "attributes": [
                    {"key": "input", "value": {"stringValue": "What is 2+2?"}},
                    {"key": "output", "value": {"stringValue": "4"}},
                ],
                "startTimeUnixNano": "1000000000",
                "endTimeUnixNano": "3000000000",
                "status": {},
            }
        ]])
        f = tmp_path / "otel.json"
        f.write_text(json.dumps(data))
        runs = OtelJsonImporter().import_traces(str(f))
        assert len(runs) == 1
        run = runs[0]
        assert run.input.query == "What is 2+2?"
        assert run.final_output == "4"
        assert run.duration_ms == 2000.0  # (3e9 - 1e9) / 1e6

    def test_tool_span_as_child(self, tmp_path):
        data = _make_otel_data([[
            {
                "traceId": "t1",
                "spanId": "root",
                "name": "agent",
                "attributes": [{"key": "input", "value": {"stringValue": "find items"}}],
                "status": {},
                "startTimeUnixNano": "0",
                "endTimeUnixNano": "5000000000",
            },
            {
                "traceId": "t1",
                "spanId": "child",
                "parentSpanId": "root",
                "name": "tool.search",
                "attributes": [
                    {"key": "tool.arguments", "value": {"stringValue": '{"q": "items"}'}},
                    {"key": "tool.result", "value": {"stringValue": "found 3"}},
                ],
                "status": {},
                "startTimeUnixNano": "1000000000",
                "endTimeUnixNano": "2000000000",
            },
        ]])
        f = tmp_path / "otel.json"
        f.write_text(json.dumps(data))
        runs = OtelJsonImporter().import_traces(str(f))
        run = runs[0]
        assert len(run.tool_calls) == 1
        assert run.tool_calls[0].name == "tool.search"
        assert run.tool_calls[0].arguments == {"q": "items"}
        assert run.tool_calls[0].result == "found 3"

    def test_error_status_code_2(self, tmp_path):
        data = _make_otel_data([[
            {
                "traceId": "t1",
                "spanId": "s1",
                "name": "agent",
                "attributes": [{"key": "input", "value": {"stringValue": "do thing"}}],
                "status": {"code": 2, "message": "agent failed"},
                "startTimeUnixNano": "0",
                "endTimeUnixNano": "1000000000",
            }
        ]])
        f = tmp_path / "otel.json"
        f.write_text(json.dumps(data))
        runs = OtelJsonImporter().import_traces(str(f))
        assert runs[0].error == "agent failed"

    def test_multiple_traces_grouped_by_trace_id(self, tmp_path):
        data = _make_otel_data([
            [{"traceId": "t1", "spanId": "s1", "name": "agent1", "attributes": [{"key": "input", "value": {"stringValue": "q1"}}], "status": {}, "startTimeUnixNano": "0", "endTimeUnixNano": "1000000000"}],
            [{"traceId": "t2", "spanId": "s2", "name": "agent2", "attributes": [{"key": "input", "value": {"stringValue": "q2"}}], "status": {}, "startTimeUnixNano": "0", "endTimeUnixNano": "1000000000"}],
        ])
        f = tmp_path / "otel.json"
        f.write_text(json.dumps(data))
        runs = OtelJsonImporter().import_traces(str(f))
        assert len(runs) == 2
        queries = {r.input.query for r in runs}
        assert queries == {"q1", "q2"}

    def test_filter_error_status(self, tmp_path):
        data = _make_otel_data([
            [{"traceId": "ok", "spanId": "s1", "name": "agent", "attributes": [{"key": "input", "value": {"stringValue": "ok query"}}], "status": {}, "startTimeUnixNano": "0", "endTimeUnixNano": "1000000000"}],
            [{"traceId": "err", "spanId": "s2", "name": "agent", "attributes": [{"key": "input", "value": {"stringValue": "err query"}}], "status": {"code": 2, "message": "failed"}, "startTimeUnixNano": "0", "endTimeUnixNano": "1000000000"}],
        ])
        f = tmp_path / "otel.json"
        f.write_text(json.dumps(data))
        runs = OtelJsonImporter().import_traces(str(f), filters={"status": "error"})
        assert len(runs) == 1
        assert runs[0].error == "failed"

    def test_metadata_contains_trace_id_and_source(self, tmp_path):
        data = _make_otel_data([[
            {"traceId": "mytrace", "spanId": "s", "name": "agent",
             "attributes": [], "status": {}, "startTimeUnixNano": "0", "endTimeUnixNano": "1000000000"}
        ]])
        f = tmp_path / "otel.json"
        f.write_text(json.dumps(data))
        runs = OtelJsonImporter().import_traces(str(f))
        assert runs[0].metadata["trace_id"] == "mytrace"
        assert runs[0].metadata["source"] == "otel"

    def test_limit_parameter(self, tmp_path):
        spans = []
        for i in range(5):
            spans.append({
                "traceId": f"t{i}", "spanId": f"s{i}", "name": f"agent{i}",
                "attributes": [{"key": "input", "value": {"stringValue": f"q{i}"}}],
                "status": {}, "startTimeUnixNano": "0", "endTimeUnixNano": "1000000000"
            })
        data = {"resourceSpans": [{"scopeSpans": [{"spans": spans}]}]}
        f = tmp_path / "otel.json"
        f.write_text(json.dumps(data))
        runs = OtelJsonImporter().import_traces(str(f), limit=2)
        assert len(runs) == 2


# ---------------------------------------------------------------------------
# PiiScrubber
# ---------------------------------------------------------------------------

class TestPiiScrubber:
    def test_email_replaced(self):
        s = PiiScrubber()
        result = s.scrub_text("Contact us at john@example.com please")
        assert "@" not in result
        assert "<EMAIL_1>" in result

    def test_phone_replaced(self):
        s = PiiScrubber()
        result = s.scrub_text("Call 555-123-4567 for help")
        assert "555" not in result
        assert "<PHONE_1>" in result

    def test_ssn_replaced(self):
        s = PiiScrubber()
        result = s.scrub_text("SSN: 123-45-6789")
        assert "6789" not in result
        assert "<SSN_1>" in result

    def test_credit_card_replaced(self):
        s = PiiScrubber()
        result = s.scrub_text("Card: 4111 1111 1111 1111")
        assert "4111" not in result
        assert "<CREDIT_CARD_1>" in result

    def test_ip_address_replaced(self):
        s = PiiScrubber()
        result = s.scrub_text("Request from 192.168.1.100")
        assert "192.168" not in result
        assert "<IP_ADDR_1>" in result

    def test_same_value_gets_same_placeholder_deterministic(self):
        s = PiiScrubber()
        text = "Email john@test.com, then john@test.com again"
        result = s.scrub_text(text)
        assert result.count("<EMAIL_1>") == 2

    def test_different_values_get_different_numbered_placeholders(self):
        s = PiiScrubber()
        text = "Email john@test.com and jane@test.com"
        result = s.scrub_text(text)
        assert "<EMAIL_1>" in result
        assert "<EMAIL_2>" in result

    def test_reset_clears_counters(self):
        s = PiiScrubber()
        s.scrub_text("john@test.com")
        s.reset()
        result2 = s.scrub_text("jane@test.com")
        # After reset, jane gets EMAIL_1 (not EMAIL_2)
        assert "<EMAIL_1>" in result2

    def test_empty_string_returns_empty(self):
        s = PiiScrubber()
        assert s.scrub_text("") == ""

    def test_no_pii_returns_unchanged(self):
        s = PiiScrubber()
        text = "This is a normal sentence with no personal data."
        assert s.scrub_text(text) == text

    def test_scrub_value_dict(self):
        s = PiiScrubber()
        data = {"email": "test@example.com", "name": "Alice"}
        result = s.scrub_value(data)
        assert "@" not in result["email"]
        assert result["name"] == "Alice"

    def test_scrub_value_nested_dict(self):
        s = PiiScrubber()
        data = {"user": {"email": "test@example.com", "ip": "10.0.0.1"}}
        result = s.scrub_value(data)
        assert "@" not in result["user"]["email"]
        assert "10.0.0.1" not in result["user"]["ip"]

    def test_scrub_value_list(self):
        s = PiiScrubber()
        data = ["foo@bar.com", "no-pii-here", "baz@qux.org"]
        result = s.scrub_value(data)
        assert "@" not in result[0]
        assert result[1] == "no-pii-here"
        assert "@" not in result[2]

    def test_scrub_value_non_string_passthrough(self):
        s = PiiScrubber()
        assert s.scrub_value(42) == 42
        assert s.scrub_value(3.14) == 3.14
        assert s.scrub_value(True) is True
        assert s.scrub_value(None) is None

    def test_extra_patterns(self):
        s = PiiScrubber(extra_patterns=[("API_KEY", r"sk-[a-z0-9]{32}")])
        text = "Key: sk-abcdefghijklmnopqrstuvwxyz123456"
        result = s.scrub_text(text)
        assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in result
        assert "<API_KEY_1>" in result


# ---------------------------------------------------------------------------
# generate_test_cases
# ---------------------------------------------------------------------------

class TestGenerateTestCases:
    def _make_runs(self, n=1, prefix="query") -> list[AgentRun]:
        return [
            AgentRun(
                input=AgentInput(query=f"{prefix} {i}"),
                final_output=f"Answer to {prefix} {i}. More text here.",
            )
            for i in range(n)
        ]

    def test_basic_generation(self):
        runs = self._make_runs(3)
        # F-103: generate_test_cases now returns tuple[GoldenDataset, TraceScreeningResult]
        dataset, _ = generate_test_cases(runs, dataset_name="test-ds")
        assert dataset.name == "test-ds"
        assert len(dataset.cases) == 3

    def test_dataset_description_includes_count(self):
        runs = self._make_runs(5)
        dataset, _ = generate_test_cases(runs)
        assert "5" in dataset.description

    def test_case_id_is_deterministic(self):
        run = AgentRun(input=AgentInput(query="hello world"), final_output="hi")
        dataset1, _ = generate_test_cases([run])
        dataset2, _ = generate_test_cases([run])
        assert dataset1.cases[0].id == dataset2.cases[0].id

    def test_imported_tag_always_added(self):
        runs = self._make_runs(1)
        dataset, _ = generate_test_cases(runs)
        assert "imported" in dataset.cases[0].tags

    def test_extra_tags_added(self):
        runs = self._make_runs(1)
        dataset, _ = generate_test_cases(runs, tags=["regression", "prod"])
        case_tags = dataset.cases[0].tags
        assert "regression" in case_tags
        assert "prod" in case_tags

    def test_error_run_gets_error_tag(self):
        run = AgentRun(
            input=AgentInput(query="bad query"),
            error="ServiceUnavailable",
        )
        dataset, _ = generate_test_cases([run])
        assert "error" in dataset.cases[0].tags

    def test_tool_run_gets_has_tools_tag(self):
        run = AgentRun(
            input=AgentInput(query="search something"),
            steps=[Step(step_index=0, tool_calls=[ToolCall(name="search", arguments={"q": "x"})])],
            final_output="found it",
        )
        dataset, _ = generate_test_cases([run])
        assert "has-tools" in dataset.cases[0].tags

    def test_expected_tools_populated_from_tool_calls(self):
        run = AgentRun(
            input=AgentInput(query="multi-step"),
            steps=[Step(step_index=0, tool_calls=[
                ToolCall(name="search", arguments={}),
                ToolCall(name="fetch", arguments={}),
            ])],
            final_output="done",
        )
        dataset, _ = generate_test_cases([run])
        assert dataset.cases[0].expected_tools == ["search", "fetch"]

    def test_expected_output_contains_extracted_from_final_output(self):
        run = AgentRun(
            input=AgentInput(query="capital of france"),
            final_output="The capital of France is Paris. It is a beautiful city.",
        )
        dataset, _ = generate_test_cases([run], scrub_pii=False)
        assert len(dataset.cases[0].expected_output_contains) > 0
        first = dataset.cases[0].expected_output_contains[0]
        assert len(first) > 10  # should be a real sentence fragment

    def test_pii_scrubbing_on_by_default(self):
        run = AgentRun(
            input=AgentInput(query="Find john@example.com"),
            final_output="Found john@example.com",
        )
        dataset, _ = generate_test_cases([run])
        assert "@" not in dataset.cases[0].input

    def test_pii_scrubbing_disabled(self):
        run = AgentRun(
            input=AgentInput(query="Find john@example.com"),
            final_output="Found result",
        )
        dataset, _ = generate_test_cases([run], scrub_pii=False)
        assert dataset.cases[0].input == "Find john@example.com"

    def test_original_duration_in_metadata(self):
        run = AgentRun(input=AgentInput(query="q"), final_output="a", duration_ms=500.0)
        dataset, _ = generate_test_cases([run])
        assert dataset.cases[0].metadata.get("original_duration_ms") == 500.0

    def test_original_error_in_metadata(self):
        run = AgentRun(input=AgentInput(query="q"), error="Timeout")
        dataset, _ = generate_test_cases([run])
        assert dataset.cases[0].metadata.get("original_error") == "Timeout"

    def test_max_steps_is_double_step_count(self):
        run = AgentRun(
            input=AgentInput(query="q"),
            steps=[
                Step(step_index=0),
                Step(step_index=1),
                Step(step_index=2),
            ],
            final_output="done",
        )
        dataset, _ = generate_test_cases([run])
        assert dataset.cases[0].max_steps == 6  # 3 steps * 2

    def test_max_steps_is_none_for_empty_steps(self):
        run = AgentRun(input=AgentInput(query="q"), final_output="a")
        dataset, _ = generate_test_cases([run])
        # no steps, max_steps should be None or a minimal fallback
        # (None because there are no steps to double)
        # Note: code does max(len(run.steps), 1) * 2 if run.steps else None
        assert dataset.cases[0].max_steps is None

    def test_custom_pii_scrubber_used(self):
        custom_scrubber = PiiScrubber(extra_patterns=[("TOKEN", r"tok-[a-z]+")])
        run = AgentRun(input=AgentInput(query="auth tok-abcdef"), final_output="ok")
        dataset, _ = generate_test_cases([run], pii_scrubber=custom_scrubber)
        assert "tok-abcdef" not in dataset.cases[0].input

    def test_f066_pii_collision_crashes(self):
        """F-066: generate_test_cases raises ValidationError when PII scrubbing
        produces duplicate IDs.

        Two traces "Find john@example.com" and "Find jane@example.com" both
        become "Find <EMAIL_1>" after per-run PII scrubbing, producing the
        same deterministic ID. GoldenDataset rejects duplicate IDs.
        """
        run1 = AgentRun(input=AgentInput(query="Find john@example.com"), final_output="Found John")
        run2 = AgentRun(input=AgentInput(query="Find jane@example.com"), final_output="Found Jane")
        with pytest.raises(Exception):
            generate_test_cases([run1, run2], scrub_pii=True)


# ---------------------------------------------------------------------------
# trace_import not at top-level (F-067)
# ---------------------------------------------------------------------------

class TestF067TraceImportNotAtTopLevel:
    """F-067: trace_import classes not exported from top-level checkagent namespace."""

    def test_trace_importer_not_at_top_level(self):
        import checkagent
        assert not hasattr(checkagent, "TraceImporter")

    def test_json_file_importer_not_at_top_level(self):
        import checkagent
        assert not hasattr(checkagent, "JsonFileImporter")

    def test_otel_importer_not_at_top_level(self):
        import checkagent
        assert not hasattr(checkagent, "OtelJsonImporter")

    def test_pii_scrubber_not_at_top_level(self):
        import checkagent
        assert not hasattr(checkagent, "PiiScrubber")

    def test_generate_test_cases_not_at_top_level(self):
        import checkagent
        assert not hasattr(checkagent, "generate_test_cases")


# ---------------------------------------------------------------------------
# CLI: checkagent import-trace
# ---------------------------------------------------------------------------

class TestCliImportTrace:
    def _run_cli(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["checkagent", "import-trace", *args],
            capture_output=True, text=True
        )

    def test_file_not_found_gives_exit_code_2(self, tmp_path):
        result = self._run_cli(str(tmp_path / "no.json"))
        assert result.returncode == 2
        assert "does not exist" in result.stderr or "does not exist" in result.stdout

    def test_basic_import_creates_output_file(self, tmp_path):
        data = [{"input": "q1", "output": "a1"}, {"input": "q2", "output": "a2"}]
        f = tmp_path / "traces.json"
        f.write_text(json.dumps(data))
        out = tmp_path / "out.json"
        result = self._run_cli(str(f), "-o", str(out))
        assert result.returncode == 0
        assert out.exists()
        dataset = json.loads(out.read_text())
        assert len(dataset["cases"]) == 2

    def test_output_is_valid_golden_dataset(self, tmp_path):
        data = [{"input": "What is AI?", "output": "Artificial Intelligence is..."}]
        f = tmp_path / "traces.json"
        f.write_text(json.dumps(data))
        out = tmp_path / "ds.json"
        self._run_cli(str(f), "-o", str(out), "--dataset-name", "myds")
        dataset = json.loads(out.read_text())
        assert dataset["name"] == "myds"
        assert dataset["version"] == "1"
        assert "cases" in dataset

    def test_pii_scrubbing_enabled_by_default(self, tmp_path):
        data = [{"input": "Email me at test@example.com", "output": "Sent"}]
        f = tmp_path / "traces.json"
        f.write_text(json.dumps(data))
        out = tmp_path / "out.json"
        self._run_cli(str(f), "-o", str(out))
        dataset = json.loads(out.read_text())
        assert "@" not in dataset["cases"][0]["input"]

    def test_no_pii_scrub_flag_preserves_pii(self, tmp_path):
        data = [{"input": "Email me at test@example.com", "output": "Sent"}]
        f = tmp_path / "traces.json"
        f.write_text(json.dumps(data))
        out = tmp_path / "out.json"
        self._run_cli(str(f), "-o", str(out), "--no-pii-scrub")
        dataset = json.loads(out.read_text())
        assert dataset["cases"][0]["input"] == "Email me at test@example.com"

    def test_limit_flag_limits_output_cases(self, tmp_path):
        data = [{"input": f"query {i}", "output": f"ans {i}"} for i in range(10)]
        f = tmp_path / "traces.json"
        f.write_text(json.dumps(data))
        out = tmp_path / "out.json"
        self._run_cli(str(f), "-o", str(out), "--limit", "3")
        dataset = json.loads(out.read_text())
        assert len(dataset["cases"]) == 3

    def test_tag_flag_adds_tags(self, tmp_path):
        data = [{"input": "q", "output": "a"}]
        f = tmp_path / "traces.json"
        f.write_text(json.dumps(data))
        out = tmp_path / "out.json"
        self._run_cli(str(f), "-o", str(out), "--tag", "regression", "--tag", "prod")
        dataset = json.loads(out.read_text())
        tags = dataset["cases"][0]["tags"]
        assert "regression" in tags
        assert "prod" in tags

    def test_jsonl_auto_detected_by_extension(self, tmp_path):
        f = tmp_path / "traces.jsonl"
        f.write_text(
            json.dumps({"input": "first", "output": "a"}) + "\n" +
            json.dumps({"input": "second", "output": "b"}) + "\n"
        )
        out = tmp_path / "out.json"
        result = self._run_cli(str(f), "-o", str(out))
        assert result.returncode == 0
        dataset = json.loads(out.read_text())
        assert len(dataset["cases"]) == 2

    def test_otel_source_flag(self, tmp_path):
        data = _make_otel_data([[
            {"traceId": "t1", "spanId": "s1", "name": "agent",
             "attributes": [{"key": "input", "value": {"stringValue": "otel query"}}],
             "status": {}, "startTimeUnixNano": "0", "endTimeUnixNano": "1000000000"}
        ]])
        f = tmp_path / "otel.json"
        f.write_text(json.dumps(data))
        out = tmp_path / "out.json"
        result = self._run_cli(str(f), "--source", "otel", "-o", str(out))
        assert result.returncode == 0
        dataset = json.loads(out.read_text())
        assert dataset["cases"][0]["input"] == "otel query"

    def test_filter_status_error_flag(self, tmp_path):
        data = [
            {"input": "q1", "output": "ok"},
            {"input": "q2", "error": "failed"},
        ]
        f = tmp_path / "traces.json"
        f.write_text(json.dumps(data))
        out = tmp_path / "out.json"
        self._run_cli(str(f), "-o", str(out), "--filter-status", "error")
        dataset = json.loads(out.read_text())
        assert len(dataset["cases"]) == 1
        assert "error" in dataset["cases"][0]["tags"]

    def test_f066_cli_crashes_with_pii_collision(self, tmp_path):
        """F-066: CLI shows raw ValidationError traceback when PII causes ID collision."""
        data = [
            {"input": "Find john@example.com", "output": "Found John"},
            {"input": "Find jane@example.com", "output": "Found Jane"},
        ]
        f = tmp_path / "dup.json"
        f.write_text(json.dumps(data))
        out = tmp_path / "out.json"
        result = self._run_cli(str(f), "-o", str(out))
        # Should fail — but ideally with a friendly error, not a raw traceback
        assert result.returncode != 0
        # The actual behavior: raw Python traceback (bad UX)
        assert "ValidationError" in result.stderr or "Traceback" in result.stderr
