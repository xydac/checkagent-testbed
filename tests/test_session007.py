"""
Session 007 tests — GoldenDataset / parametrize_cases, AgentInput, new datasets module.

New in c786006:
- checkagent.datasets: GoldenDataset, TestCase, load_dataset, load_cases, parametrize_cases
- AgentInput now exported from top-level checkagent
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from checkagent import (
    AgentInput,
    AgentRun,
    MockLLM,
    MockTool,
    Step,
    ToolCall,
    assert_output_matches,
    assert_tool_called,
)
from checkagent.datasets import (
    GoldenDataset,
    TestCase,
    load_cases,
    load_dataset,
    parametrize_cases,
)
from dirty_equals import AnyThing, IsStr

# ---------------------------------------------------------------------------
# Path to golden dataset fixture file
# ---------------------------------------------------------------------------

GOLDEN_PATH = Path(__file__).parent / "golden" / "travel_agent.json"


# ---------------------------------------------------------------------------
# TestCase construction
# ---------------------------------------------------------------------------


def test_testcase_minimal_construction():
    """TestCase requires only id and input."""
    tc = TestCase(id="t001", input="Hello")
    assert tc.id == "t001"
    assert tc.input == "Hello"
    assert tc.expected_tools == []
    assert tc.expected_output_contains == []
    assert tc.expected_output_equals is None
    assert tc.max_steps is None
    assert tc.tags == []
    assert tc.context == {}
    assert tc.metadata == {}


def test_testcase_full_construction():
    """TestCase stores all fields correctly."""
    tc = TestCase(
        id="t002",
        input="Book a flight",
        expected_tools=["search_flights", "book_flight"],
        expected_output_contains=["confirmed", "flight"],
        expected_output_equals=None,
        max_steps=5,
        tags=["booking", "happy-path"],
        context={"user_id": "u123"},
        metadata={"source": "production"},
    )
    assert tc.expected_tools == ["search_flights", "book_flight"]
    assert tc.max_steps == 5
    assert tc.context["user_id"] == "u123"


def test_testcase_missing_id_raises():
    """TestCase without id raises ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="id"):
        TestCase(input="no id here")


# ---------------------------------------------------------------------------
# GoldenDataset construction
# ---------------------------------------------------------------------------


def test_golden_dataset_construction():
    """GoldenDataset stores cases and metadata."""
    cases = [
        TestCase(id="a", input="test a"),
        TestCase(id="b", input="test b"),
    ]
    ds = GoldenDataset(
        name="my-dataset",
        version="1",
        description="Test dataset",
        cases=cases,
    )
    assert ds.name == "my-dataset"
    assert ds.version == "1"
    assert len(ds.cases) == 2


def test_golden_dataset_duplicate_ids_raises():
    """GoldenDataset rejects duplicate case IDs."""
    from pydantic import ValidationError

    cases_data = [
        {"id": "dup", "input": "first"},
        {"id": "dup", "input": "second"},
    ]
    data = {"cases": cases_data}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        tmppath = f.name
    try:
        with pytest.raises(ValidationError, match="Duplicate test case IDs"):
            load_dataset(tmppath)
    finally:
        os.unlink(tmppath)


# ---------------------------------------------------------------------------
# load_dataset — JSON
# ---------------------------------------------------------------------------


def test_load_dataset_json_basic():
    """load_dataset returns GoldenDataset from JSON file."""
    ds = load_dataset(GOLDEN_PATH)
    assert isinstance(ds, GoldenDataset)
    assert ds.name == "travel-agent-golden"
    assert ds.version == "1"
    assert len(ds.cases) == 4


def test_load_dataset_json_case_fields():
    """Loaded cases have correct field values."""
    ds = load_dataset(GOLDEN_PATH)
    book = next(c for c in ds.cases if c.id == "book-paris-001")
    assert book.input == "Book a flight to Paris next Friday"
    assert "search_flights" in book.expected_tools
    assert "book_flight" in book.expected_tools
    assert "Paris" in book.expected_output_contains
    assert book.max_steps == 5
    assert "booking" in book.tags
    assert book.context["user_id"] == "u001"


def test_load_dataset_file_not_found():
    """load_dataset raises FileNotFoundError on missing file."""
    with pytest.raises(FileNotFoundError):
        load_dataset("/nonexistent/path/dataset.json")


def test_load_dataset_unsupported_format():
    """load_dataset raises ValueError on unsupported file format."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("name = 'test'\n")
        tmppath = f.name
    try:
        with pytest.raises(ValueError, match=".toml"):
            load_dataset(tmppath)
    finally:
        os.unlink(tmppath)


# ---------------------------------------------------------------------------
# load_dataset — YAML
# ---------------------------------------------------------------------------


def test_load_dataset_yaml():
    """load_dataset parses YAML files correctly."""
    yaml_content = """
name: yaml-dataset
version: '1'
cases:
  - id: y001
    input: Test YAML input
    expected_output_contains: [success]
    tags: [yaml]
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmppath = f.name
    try:
        ds = load_dataset(tmppath)
        assert ds.name == "yaml-dataset"
        assert len(ds.cases) == 1
        assert ds.cases[0].id == "y001"
    finally:
        os.unlink(tmppath)


def test_load_dataset_yaml_integer_version_raises():
    """YAML with unquoted integer version field raises ValidationError — F-012."""
    yaml_content = """
name: yaml-dataset
version: 2
cases:
  - id: v001
    input: Test
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmppath = f.name
    try:
        # This SHOULD work: version 2 is semantically valid, but pydantic rejects
        # int because GoldenDataset.version is typed as str with no coercion.
        # Filed as F-012.
        with pytest.raises(Exception):
            load_dataset(tmppath)
    finally:
        os.unlink(tmppath)


# ---------------------------------------------------------------------------
# load_cases — tag filtering
# ---------------------------------------------------------------------------


def test_load_cases_no_filter_returns_all():
    """load_cases with no tags returns all cases."""
    cases = load_cases(GOLDEN_PATH)
    assert len(cases) == 4


def test_load_cases_tag_filter():
    """load_cases filters correctly by tag."""
    booking_cases = load_cases(GOLDEN_PATH, tags=["booking"])
    assert all("booking" in c.tags for c in booking_cases)
    ids = [c.id for c in booking_cases]
    assert "book-paris-001" in ids
    assert "cancel-001" not in ids


def test_load_cases_multi_tag_filter():
    """load_cases with multiple tags returns cases matching ANY tag."""
    cases = load_cases(GOLDEN_PATH, tags=["booking", "cancellation"])
    ids = [c.id for c in cases]
    assert "book-paris-001" in ids
    assert "cancel-001" in ids
    assert "status-001" not in ids


def test_load_cases_tag_no_match_returns_empty():
    """load_cases with no matching tag returns empty list."""
    cases = load_cases(GOLDEN_PATH, tags=["nonexistent-tag"])
    assert cases == []


def test_load_cases_empty_tag_list_returns_all():
    """load_cases with tags=[] returns all cases (same as no filter)."""
    all_cases = load_cases(GOLDEN_PATH)
    empty_tag_cases = load_cases(GOLDEN_PATH, tags=[])
    assert len(empty_tag_cases) == len(all_cases)


# ---------------------------------------------------------------------------
# parametrize_cases
# ---------------------------------------------------------------------------


def test_parametrize_cases_returns_tuple():
    """parametrize_cases returns (argname, argvalues)."""
    result = parametrize_cases(GOLDEN_PATH)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_parametrize_cases_argname():
    """parametrize_cases argname is 'test_case'."""
    argname, _ = parametrize_cases(GOLDEN_PATH)
    assert argname == "test_case"


def test_parametrize_cases_argvalues_count():
    """parametrize_cases returns correct number of ParameterSet entries."""
    _, argvals = parametrize_cases(GOLDEN_PATH)
    assert len(argvals) == 4


def test_parametrize_cases_ids_match_case_ids():
    """parametrize_cases uses case id as pytest id."""
    _, argvals = parametrize_cases(GOLDEN_PATH)
    pytest_ids = [av.id for av in argvals]
    assert "book-paris-001" in pytest_ids
    assert "cancel-001" in pytest_ids
    assert "status-001" in pytest_ids
    assert "invalid-001" in pytest_ids


def test_parametrize_cases_tag_filter():
    """parametrize_cases with tags only includes matching cases."""
    _, argvals = parametrize_cases(GOLDEN_PATH, tags=["booking"])
    ids = [av.id for av in argvals]
    assert "book-paris-001" in ids
    assert "cancel-001" not in ids


# ---------------------------------------------------------------------------
# Full parametrized test scenario using golden dataset
# ---------------------------------------------------------------------------


def _make_travel_agent_run(tc: TestCase) -> AgentRun:
    """Simulate a travel agent run for the given TestCase."""
    # A minimal mock that echoes tools from expected_tools
    # and produces output containing expected_output_contains strings
    tool_calls = [
        ToolCall(name=t, arguments={"query": tc.input})
        for t in tc.expected_tools
    ]
    output_text = (
        " ".join(tc.expected_output_contains)
        if tc.expected_output_contains
        else "I cannot help with travel queries."
    )
    step = Step(tool_calls=tool_calls)
    return AgentRun(
        input=AgentInput(query=tc.input),
        final_output={"text": output_text},
        steps=[step],
    )


@pytest.mark.parametrize(*parametrize_cases(GOLDEN_PATH, tags=["happy-path"]))
def test_travel_agent_happy_path(test_case):
    """Happy-path cases: agent calls expected tools and output contains expected strings."""
    run = _make_travel_agent_run(test_case)
    # Verify each expected tool was called
    for tool_name in test_case.expected_tools:
        assert_tool_called(run, tool_name)
    # Verify output contains each expected string
    for fragment in test_case.expected_output_contains:
        assert fragment in run.final_output["text"], f"Expected '{fragment}' in output: {run.final_output!r}"


@pytest.mark.parametrize(*parametrize_cases(GOLDEN_PATH))
def test_travel_agent_output_structure(test_case):
    """All cases: output is a non-empty string."""
    run = _make_travel_agent_run(test_case)
    assert_output_matches(run, {"text": IsStr()})


@pytest.mark.parametrize(*parametrize_cases(GOLDEN_PATH))
def test_travel_agent_max_steps_respected(test_case):
    """All cases: step count does not exceed max_steps when defined."""
    run = _make_travel_agent_run(test_case)
    if test_case.max_steps is not None:
        assert len(run.steps) <= test_case.max_steps


# ---------------------------------------------------------------------------
# AgentInput — new top-level export
# ---------------------------------------------------------------------------


def test_agent_input_construction():
    """AgentInput can be constructed with just a query."""
    ai = AgentInput(query="What flights are available to Tokyo?")
    assert ai.query == "What flights are available to Tokyo?"
    assert ai.context == {}
    assert ai.conversation_history == []
    assert ai.metadata == {}


def test_agent_input_with_context():
    """AgentInput stores context dict."""
    ai = AgentInput(
        query="Book it",
        context={"user_id": "u999", "preferred_class": "business"},
        metadata={"request_id": "r42"},
    )
    assert ai.context["user_id"] == "u999"
    assert ai.metadata["request_id"] == "r42"


def test_agent_input_with_conversation_history():
    """AgentInput stores conversation history."""
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    ai = AgentInput(query="Book a flight", conversation_history=history)
    assert len(ai.conversation_history) == 2
    assert ai.conversation_history[0]["role"] == "user"


def test_agent_input_is_importable_from_top_level():
    """AgentInput is exported from top-level checkagent."""
    import checkagent

    assert hasattr(checkagent, "AgentInput")
    assert checkagent.AgentInput is AgentInput
