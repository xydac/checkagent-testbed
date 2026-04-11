"""Session-019 tests: judge module — RubricJudge, compute_verdict, Criterion scales, verdicts."""
import json
from json import JSONDecodeError

import pytest

from checkagent import AgentRun, AgentInput, Step
from checkagent.core.types import ToolCall
from checkagent.judge import (
    Criterion,
    CriterionScore,
    Judge,
    JudgeScore,
    JudgeVerdict,
    Rubric,
    RubricJudge,
    ScaleType,
    Verdict,
    compute_verdict,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_run(query="What is 2+2?", output="4", steps=None):
    return AgentRun(
        input=AgentInput(query=query),
        final_output=output,
        steps=steps or [],
    )


def make_llm(scores: dict[str, int | str], reasoning: str = "ok"):
    """Return an async mock LLM callable that always emits the given scores."""
    response = json.dumps({
        "scores": [
            {"criterion": k, "value": v, "reasoning": "test"}
            for k, v in scores.items()
        ],
        "overall_reasoning": reasoning,
    })

    async def _llm(system: str, user: str) -> str:
        return response

    return _llm


# ---------------------------------------------------------------------------
# F-048: Judge module classes not exported from top-level checkagent
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
def test_f048_judge_partial_fix():
    """F-048 FIXED: Rubric, RubricJudge, Criterion, and JudgeScore are now at top-level checkagent."""
    import checkagent
    # These are now at top-level:
    assert hasattr(checkagent, "RubricJudge"), "RubricJudge should be at top-level"
    assert hasattr(checkagent, "JudgeScore"), "JudgeScore should be at top-level"
    assert hasattr(checkagent, "Criterion"), "Criterion should be at top-level"
    assert hasattr(checkagent, "Rubric"), "Rubric now at top-level — F-048 FIXED"


# ---------------------------------------------------------------------------
# F-049: No ca_judge fixture — judge module has no pytest integration
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
def test_f049_ca_judge_fixture_added(request):
    """F-049 fixed in d88d3e7: ca_judge fixture is now registered by checkagent plugin."""
    fixture_names = request.session._fixturemanager._arg2fixturedefs.keys()
    ca_judge_fixtures = [f for f in fixture_names if f in ("ca_judge", "ap_rubric_judge")]
    assert "ca_judge" in ca_judge_fixtures, (
        f"ca_judge fixture still not registered. F-049 not yet fixed."
    )


# ---------------------------------------------------------------------------
# Basic RubricJudge construction and evaluation
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_basic_rubric_judge_evaluate():
    """RubricJudge.evaluate() returns JudgeScore with correct rubric_name and overall."""
    rubric = Rubric(
        name="qa",
        criteria=[Criterion(name="accuracy", description="Accurate?")],
    )
    llm = make_llm({"accuracy": 5})
    judge = RubricJudge(rubric=rubric, llm=llm, model_name="mock")

    score = await judge.evaluate(make_run())

    assert isinstance(score, JudgeScore)
    assert score.rubric_name == "qa"
    assert score.judge_model == "mock"
    assert score.overall == 1.0  # (5-1)/(5-1) = 1.0
    assert len(score.criterion_scores) == 1
    assert score.criterion_scores[0].criterion_name == "accuracy"


@pytest.mark.agent_test(layer="judge")
def test_rubric_judge_name_attr():
    """RubricJudge.name encodes the rubric name."""
    rubric = Rubric(name="my_rubric", criteria=[Criterion(name="q", description="Q")])
    judge = RubricJudge(rubric=rubric, llm=lambda s, u: "")
    assert judge.name == "rubric_judge:my_rubric"


@pytest.mark.agent_test(layer="judge")
def test_judge_repr():
    """Judge.__repr__ uses class name and name attr."""
    rubric = Rubric(name="r", criteria=[Criterion(name="x", description="X")])
    judge = RubricJudge(rubric=rubric, llm=lambda s, u: "")
    assert "RubricJudge" in repr(judge)
    assert "rubric_judge:r" in repr(judge)


# ---------------------------------------------------------------------------
# Numeric scale normalization
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_numeric_scale_min_score():
    """Score of 1 on default [1-5] scale normalizes to 0.0."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])
    score = await RubricJudge(rubric=rubric, llm=make_llm({"q": 1})).evaluate(make_run())
    assert score.overall == 0.0


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_numeric_scale_mid_score():
    """Score of 3 on [1-5] normalizes to 0.5."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])
    score = await RubricJudge(rubric=rubric, llm=make_llm({"q": 3})).evaluate(make_run())
    assert abs(score.overall - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# Binary scale
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_binary_scale_pass():
    """Binary criterion with value 'pass' normalizes to 1.0."""
    rubric = Rubric(
        name="r",
        criteria=[
            Criterion(
                name="safe",
                description="Safe?",
                scale_type=ScaleType.BINARY,
                scale=["fail", "pass"],
            )
        ],
    )
    score = await RubricJudge(rubric=rubric, llm=make_llm({"safe": "pass"})).evaluate(make_run())
    cs = score.score_for("safe")
    assert cs is not None
    assert cs.normalized == 1.0


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_binary_scale_fail():
    """Binary criterion with value 'fail' normalizes to 0.0."""
    rubric = Rubric(
        name="r",
        criteria=[
            Criterion(
                name="safe",
                description="Safe?",
                scale_type=ScaleType.BINARY,
                scale=["fail", "pass"],
            )
        ],
    )
    score = await RubricJudge(rubric=rubric, llm=make_llm({"safe": "fail"})).evaluate(make_run())
    cs = score.score_for("safe")
    assert cs.normalized == 0.0


# ---------------------------------------------------------------------------
# Categorical scale
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_categorical_scale_first_item():
    """Categorical first item (worst) normalizes to 0.0."""
    rubric = Rubric(
        name="r",
        criteria=[
            Criterion(
                name="quality",
                description="Quality",
                scale_type=ScaleType.CATEGORICAL,
                scale=["poor", "fair", "good", "excellent"],
            )
        ],
    )
    score = await RubricJudge(rubric=rubric, llm=make_llm({"quality": "poor"})).evaluate(make_run())
    assert score.score_for("quality").normalized == 0.0


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_categorical_scale_last_item():
    """Categorical last item (best) normalizes to 1.0."""
    rubric = Rubric(
        name="r",
        criteria=[
            Criterion(
                name="quality",
                description="Quality",
                scale_type=ScaleType.CATEGORICAL,
                scale=["poor", "fair", "good", "excellent"],
            )
        ],
    )
    score = await RubricJudge(rubric=rubric, llm=make_llm({"quality": "excellent"})).evaluate(make_run())
    assert score.score_for("quality").normalized == 1.0


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_categorical_scale_mid_item():
    """Categorical middle item normalizes proportionally."""
    rubric = Rubric(
        name="r",
        criteria=[
            Criterion(
                name="quality",
                description="Quality",
                scale_type=ScaleType.CATEGORICAL,
                scale=["poor", "fair", "good", "excellent"],
            )
        ],
    )
    # "good" is index 2 of 4 → 2/3
    score = await RubricJudge(rubric=rubric, llm=make_llm({"quality": "good"})).evaluate(make_run())
    assert abs(score.score_for("quality").normalized - 2 / 3) < 1e-9


# ---------------------------------------------------------------------------
# Weighted criteria
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_weighted_criteria_scoring():
    """Weighted criteria correctly influence overall score."""
    rubric = Rubric(
        name="weighted",
        criteria=[
            Criterion(name="accuracy", description="Accurate?", weight=3.0),
            Criterion(name="brevity", description="Brief?", weight=1.0),
        ],
    )
    # accuracy=5 → 1.0, brevity=1 → 0.0
    # overall = (1.0*3 + 0.0*1) / (3+1) = 0.75
    score = await RubricJudge(rubric=rubric, llm=make_llm({"accuracy": 5, "brevity": 1})).evaluate(make_run())
    assert abs(score.overall - 0.75) < 1e-9


# ---------------------------------------------------------------------------
# JudgeScore helpers
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_score_for_hit():
    """JudgeScore.score_for returns CriterionScore for known criterion."""
    rubric = Rubric(name="r", criteria=[Criterion(name="acc", description="A?")])
    score = await RubricJudge(rubric=rubric, llm=make_llm({"acc": 4})).evaluate(make_run())
    cs = score.score_for("acc")
    assert isinstance(cs, CriterionScore)
    assert cs.criterion_name == "acc"


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_score_for_miss_returns_none():
    """JudgeScore.score_for returns None for unknown criterion name."""
    rubric = Rubric(name="r", criteria=[Criterion(name="acc", description="A?")])
    score = await RubricJudge(rubric=rubric, llm=make_llm({"acc": 4})).evaluate(make_run())
    assert score.score_for("nonexistent") is None


# ---------------------------------------------------------------------------
# Rubric helpers
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
def test_rubric_get_criterion_hit():
    """Rubric.get_criterion returns Criterion for known name."""
    rubric = Rubric(
        name="r",
        criteria=[
            Criterion(name="a", description="A"),
            Criterion(name="b", description="B"),
        ],
    )
    c = rubric.get_criterion("b")
    assert c is not None
    assert c.name == "b"


@pytest.mark.agent_test(layer="judge")
def test_rubric_get_criterion_miss():
    """Rubric.get_criterion returns None for unknown name."""
    rubric = Rubric(name="r", criteria=[Criterion(name="a", description="A")])
    assert rubric.get_criterion("nope") is None


@pytest.mark.agent_test(layer="judge")
def test_rubric_empty_criteria_raises():
    """Rubric with no criteria raises ValidationError."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Rubric(name="bad", criteria=[])


# ---------------------------------------------------------------------------
# Markdown fence stripping
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_markdown_fenced_json_response():
    """RubricJudge parses LLM responses wrapped in markdown code fences."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])

    async def fence_llm(system, user):
        return "```json\n" + json.dumps({
            "scores": [{"criterion": "q", "value": 5, "reasoning": "Good"}],
            "overall_reasoning": "Pass",
        }) + "\n```"

    score = await RubricJudge(rubric=rubric, llm=fence_llm).evaluate(make_run())
    assert score.overall == 1.0


# ---------------------------------------------------------------------------
# F-050: Bad JSON from LLM propagates raw JSONDecodeError
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_f050_bad_json_raises_json_decode_error():
    """LLM returning non-JSON raises raw JSONDecodeError with no helpful checkagent wrapper."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])

    async def bad_llm(system, user):
        return "The answer looks good, 4 out of 5."

    judge = RubricJudge(rubric=rubric, llm=bad_llm)
    # F-050 FIXED: Now raises JudgeParseError (not raw JSONDecodeError)
    from checkagent.judge.judge import JudgeParseError
    with pytest.raises(JudgeParseError):
        await judge.evaluate(make_run())


# ---------------------------------------------------------------------------
# F-051: Unknown criterion names silently produce 0.0 score
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_f051_all_unknown_criterion_names_silently_zero():
    """LLM returning wrong criterion names silently produces overall=0.0 with no warning."""
    rubric = Rubric(name="r", criteria=[Criterion(name="accuracy", description="A?")])

    async def wrong_names_llm(system, user):
        return json.dumps({
            "scores": [{"criterion": "completely_wrong", "value": 5, "reasoning": "High"}],
            "overall_reasoning": "All wrong names",
        })

    judge = RubricJudge(rubric=rubric, llm=wrong_names_llm)
    score = await judge.evaluate(make_run())
    # Silent data loss: criterion_scores empty, overall 0.0
    assert score.criterion_scores == []
    assert score.overall == 0.0


# ---------------------------------------------------------------------------
# compute_verdict — PASS / FAIL / INCONCLUSIVE
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_compute_verdict_pass():
    """All trials passing produces PASS verdict."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])
    judge = RubricJudge(rubric=rubric, llm=make_llm({"q": 5}))
    verdict = await compute_verdict(judge, make_run(), num_trials=3, threshold=0.7)
    assert verdict.verdict == Verdict.PASS
    assert verdict.passed is True
    assert verdict.pass_rate == 1.0
    assert verdict.num_trials == 3


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_compute_verdict_fail():
    """All trials failing produces FAIL verdict."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])
    judge = RubricJudge(rubric=rubric, llm=make_llm({"q": 1}))
    verdict = await compute_verdict(judge, make_run(), num_trials=3, threshold=0.7)
    assert verdict.verdict == Verdict.FAIL
    assert verdict.passed is False
    assert verdict.pass_rate == 0.0


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_compute_verdict_inconclusive():
    """2 of 5 trials passing (pass_rate=0.4) with defaults produces INCONCLUSIVE."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])
    call_count = [0]

    async def mixed_llm(system, user):
        call_count[0] += 1
        value = 5 if call_count[0] % 5 in (1, 2) else 1  # 2 of 5 pass
        return json.dumps({"scores": [{"criterion": "q", "value": value, "reasoning": "x"}],
                           "overall_reasoning": "mixed"})

    judge = RubricJudge(rubric=rubric, llm=mixed_llm)
    verdict = await compute_verdict(judge, make_run(), num_trials=5, threshold=0.7)
    assert verdict.verdict == Verdict.INCONCLUSIVE
    assert verdict.passed is False
    assert abs(verdict.pass_rate - 0.4) < 1e-9


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_compute_verdict_single_trial():
    """num_trials=1 works — returns verdict based on single evaluation."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])
    judge = RubricJudge(rubric=rubric, llm=make_llm({"q": 5}))
    verdict = await compute_verdict(judge, make_run(), num_trials=1, threshold=0.7)
    assert verdict.num_trials == 1
    assert verdict.verdict == Verdict.PASS


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_compute_verdict_zero_trials_raises():
    """num_trials=0 raises ValueError."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])
    judge = RubricJudge(rubric=rubric, llm=make_llm({"q": 5}))
    with pytest.raises(ValueError, match="num_trials must be at least 1"):
        await compute_verdict(judge, make_run(), num_trials=0)


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_compute_verdict_stores_all_trials():
    """JudgeVerdict.trials contains one JudgeScore per trial."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])
    judge = RubricJudge(rubric=rubric, llm=make_llm({"q": 4}))
    verdict = await compute_verdict(judge, make_run(), num_trials=5, threshold=0.7)
    assert len(verdict.trials) == 5
    assert all(isinstance(t, JudgeScore) for t in verdict.trials)


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_compute_verdict_inconclusive_confidence_zero():
    """INCONCLUSIVE verdict has confidence=0.0."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])
    call_count = [0]

    async def mixed_llm(system, user):
        call_count[0] += 1
        value = 5 if call_count[0] % 5 in (1, 2) else 1
        return json.dumps({"scores": [{"criterion": "q", "value": value, "reasoning": "x"}],
                           "overall_reasoning": "mixed"})

    judge = RubricJudge(rubric=rubric, llm=mixed_llm)
    verdict = await compute_verdict(judge, make_run(), num_trials=5, threshold=0.7)
    assert verdict.confidence == 0.0


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_compute_verdict_error_propagates():
    """If judge.evaluate() raises, compute_verdict propagates the exception."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])

    async def error_llm(system, user):
        raise RuntimeError("API timeout")

    judge = RubricJudge(rubric=rubric, llm=error_llm)
    with pytest.raises(RuntimeError, match="API timeout"):
        await compute_verdict(judge, make_run(), num_trials=3)


# ---------------------------------------------------------------------------
# JudgeVerdict fields and passed property
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
def test_judge_verdict_passed_for_pass():
    """JudgeVerdict.passed is True only for PASS verdict."""
    pv = JudgeVerdict(verdict=Verdict.PASS, pass_rate=1.0, threshold=0.7)
    fv = JudgeVerdict(verdict=Verdict.FAIL, pass_rate=0.0, threshold=0.7)
    iv = JudgeVerdict(verdict=Verdict.INCONCLUSIVE, pass_rate=0.4, threshold=0.7)
    assert pv.passed is True
    assert fv.passed is False
    assert iv.passed is False


@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_compute_verdict_reasoning_summary():
    """JudgeVerdict.reasoning includes trial count and pass rate."""
    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])
    judge = RubricJudge(rubric=rubric, llm=make_llm({"q": 5}))
    verdict = await compute_verdict(judge, make_run(), num_trials=3, threshold=0.7)
    assert "3/3" in verdict.reasoning
    assert "100.0%" in verdict.reasoning


# ---------------------------------------------------------------------------
# AgentRun steps and tool calls visible in user prompt
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
@pytest.mark.asyncio
async def test_user_prompt_includes_steps():
    """RubricJudge user prompt includes step input/output and tool calls."""
    captured = {}

    async def capture_llm(system, user):
        captured["user"] = user
        return json.dumps({"scores": [{"criterion": "q", "value": 5, "reasoning": "ok"}],
                           "overall_reasoning": "pass"})

    rubric = Rubric(name="r", criteria=[Criterion(name="q", description="Q")])
    run = AgentRun(
        input=AgentInput(query="Find cats"),
        final_output="Found 3 cats",
        steps=[
            Step(
                input_text="Find cats",
                output_text="Searching...",
                tool_calls=[ToolCall(name="search", arguments={"q": "cats"}, result="3 results")],
            )
        ],
    )
    await RubricJudge(rubric=rubric, llm=capture_llm).evaluate(run)

    user = captured["user"]
    assert "Find cats" in user
    assert "Searching..." in user
    assert "search" in user
    assert "3 results" in user
    assert "Found 3 cats" in user


# ---------------------------------------------------------------------------
# Verdict enum values (str Enum)
# ---------------------------------------------------------------------------

@pytest.mark.agent_test(layer="judge")
def test_verdict_enum_values():
    """Verdict enum has expected string values."""
    assert Verdict.PASS == "pass"
    assert Verdict.FAIL == "fail"
    assert Verdict.INCONCLUSIVE == "inconclusive"


@pytest.mark.agent_test(layer="judge")
def test_scale_type_enum_values():
    """ScaleType enum has expected string values."""
    assert ScaleType.NUMERIC == "numeric"
    assert ScaleType.BINARY == "binary"
    assert ScaleType.CATEGORICAL == "categorical"
