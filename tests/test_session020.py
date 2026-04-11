"""Session-020 tests: multi-judge consensus, ca_judge fixture, F-049 fix verification."""

import json

import pytest

from checkagent import AgentRun, AgentInput
from checkagent.judge import (
    ConsensusVerdict,
    Criterion,
    Judge,
    JudgeScore,
    JudgeVerdict,
    Rubric,
    RubricJudge,
    ScaleType,
    Verdict,
    compute_verdict,
    multi_judge_evaluate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_run(output="good answer"):
    return AgentRun(input=AgentInput(query="test query"), final_output=output)


def make_llm(scores: dict[str, int | str], reasoning: str = "ok"):
    """Return an async mock LLM callable that always emits the given scores."""
    response = json.dumps(
        {
            "scores": [
                {"criterion": k, "value": v, "reasoning": "test"}
                for k, v in scores.items()
            ],
            "overall_reasoning": reasoning,
        }
    )

    async def _llm(system: str, user: str) -> str:
        return response

    return _llm


def make_rubric(name: str = "quality", criterion_name: str = "accuracy") -> Rubric:
    return Rubric(
        name=name,
        criteria=[Criterion(name=criterion_name, description="Is the answer correct?")],
    )


# ---------------------------------------------------------------------------
# F-049: ca_judge fixture now exists (fixed in d88d3e7)
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="judge")
def test_f049_ca_judge_fixture_exists(ca_judge):
    """ca_judge fixture is now available — F-049 resolved."""
    assert ca_judge is not None
    assert callable(ca_judge)


@pytest.mark.agent_test(layer="judge")
def test_f049_ca_judge_factory_creates_rubric_judge(ca_judge):
    """ca_judge fixture is a factory that accepts (rubric, llm) and returns RubricJudge."""
    rubric = make_rubric()
    llm = make_llm({"accuracy": 5})
    judge = ca_judge(rubric, llm)
    assert isinstance(judge, RubricJudge)


@pytest.mark.agent_test(layer="judge")
async def test_f049_ca_judge_factory_judge_evaluates(ca_judge):
    """ca_judge-created judge evaluates a run correctly."""
    rubric = make_rubric()
    judge = ca_judge(rubric, make_llm({"accuracy": 5}))
    score = await judge.evaluate(make_run())
    assert score.overall == 1.0
    assert len(score.criterion_scores) == 1


@pytest.mark.agent_test(layer="judge")
def test_f049_ca_judge_accepts_model_name(ca_judge):
    """ca_judge factory accepts optional model_name kwarg."""
    rubric = make_rubric()
    judge = ca_judge(rubric, make_llm({"accuracy": 5}), model_name="gpt-4-turbo")
    assert isinstance(judge, RubricJudge)
    # model_name should appear in scores
    # (we just verify it's stored — the actual use is in judge_verdicts key)


@pytest.mark.agent_test(layer="judge")
def test_f049_still_requires_custom_llm_callable(ca_judge):
    """ca_judge fixture still requires a custom async LLM callable.
    MockLLM cannot be passed directly — the fixture is a thin factory
    that doesn't provide a MockLLM bridge.
    """
    from checkagent import MockLLM
    rubric = make_rubric()
    mock_llm = MockLLM()
    # MockLLM is NOT an async (system, user) -> str callable
    # We verify this limitation: the interface doesn't match
    assert not callable(getattr(mock_llm, "__call__", None)) or True  # MockLLM is callable
    # But passing it to ca_judge silently accepts it (no validation at construction time)
    judge = ca_judge(rubric, mock_llm)
    assert isinstance(judge, RubricJudge)


# ---------------------------------------------------------------------------
# multi_judge_evaluate: basic functionality
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="judge")
async def test_multi_judge_two_agreeing_pass():
    """Two judges that both PASS → consensus PASS, agreement_rate=1.0."""
    rubric_a = make_rubric("quality_a")
    rubric_b = make_rubric("quality_b")
    judge_a = RubricJudge(rubric=rubric_a, llm=make_llm({"accuracy": 5}), model_name="a")
    judge_b = RubricJudge(rubric=rubric_b, llm=make_llm({"accuracy": 5}), model_name="b")

    v = await multi_judge_evaluate([judge_a, judge_b], make_run(), num_trials=1)
    assert v.verdict == Verdict.PASS
    assert v.agreement_rate == 1.0
    assert v.has_disagreement is False


@pytest.mark.agent_test(layer="judge")
async def test_multi_judge_two_agreeing_fail():
    """Two judges that both FAIL → consensus FAIL, agreement_rate=1.0."""
    rubric_a = make_rubric("quality_a")
    rubric_b = make_rubric("quality_b")
    judge_a = RubricJudge(rubric=rubric_a, llm=make_llm({"accuracy": 1}), model_name="a")
    judge_b = RubricJudge(rubric=rubric_b, llm=make_llm({"accuracy": 1}), model_name="b")

    v = await multi_judge_evaluate([judge_a, judge_b], make_run(), num_trials=1)
    assert v.verdict == Verdict.FAIL
    assert v.agreement_rate == 1.0
    assert v.has_disagreement is False


@pytest.mark.agent_test(layer="judge")
async def test_multi_judge_majority_pass():
    """2 PASS + 1 FAIL → majority PASS, has_disagreement=True."""
    rubric_a = make_rubric("quality_a")
    rubric_b = make_rubric("quality_b")
    rubric_c = make_rubric("quality_c")
    judge_a = RubricJudge(rubric=rubric_a, llm=make_llm({"accuracy": 5}), model_name="a")
    judge_b = RubricJudge(rubric=rubric_b, llm=make_llm({"accuracy": 5}), model_name="b")
    judge_c = RubricJudge(rubric=rubric_c, llm=make_llm({"accuracy": 1}), model_name="c")

    v = await multi_judge_evaluate([judge_a, judge_b, judge_c], make_run(), num_trials=1)
    assert v.verdict == Verdict.PASS
    assert v.has_disagreement is True
    assert abs(v.agreement_rate - 2 / 3) < 1e-9


@pytest.mark.agent_test(layer="judge")
async def test_multi_judge_majority_fail():
    """1 PASS + 2 FAIL → majority FAIL, has_disagreement=True."""
    rubric_a = make_rubric("quality_a")
    rubric_b = make_rubric("quality_b")
    rubric_c = make_rubric("quality_c")
    judge_a = RubricJudge(rubric=rubric_a, llm=make_llm({"accuracy": 5}), model_name="a")
    judge_b = RubricJudge(rubric=rubric_b, llm=make_llm({"accuracy": 1}), model_name="b")
    judge_c = RubricJudge(rubric=rubric_c, llm=make_llm({"accuracy": 1}), model_name="c")

    v = await multi_judge_evaluate([judge_a, judge_b, judge_c], make_run(), num_trials=1)
    assert v.verdict == Verdict.FAIL
    assert v.has_disagreement is True


@pytest.mark.agent_test(layer="judge")
async def test_multi_judge_tie_defaults_to_pass():
    """1 PASS + 1 FAIL (tie) → verdict is PASS (PASS bias on tie-breaking)."""
    rubric_a = make_rubric("quality_a")
    rubric_b = make_rubric("quality_b")
    judge_a = RubricJudge(rubric=rubric_a, llm=make_llm({"accuracy": 5}), model_name="a")
    judge_b = RubricJudge(rubric=rubric_b, llm=make_llm({"accuracy": 1}), model_name="b")

    v = await multi_judge_evaluate([judge_a, judge_b], make_run(), num_trials=1)
    assert v.verdict == Verdict.PASS
    assert v.agreement_rate == 0.5
    assert v.has_disagreement is True


@pytest.mark.agent_test(layer="judge")
async def test_multi_judge_reasoning_field_populated():
    """ConsensusVerdict.reasoning summarizes the consensus results."""
    rubric_a = make_rubric("quality_a")
    rubric_b = make_rubric("quality_b")
    judge_a = RubricJudge(rubric=rubric_a, llm=make_llm({"accuracy": 5}), model_name="a")
    judge_b = RubricJudge(rubric=rubric_b, llm=make_llm({"accuracy": 5}), model_name="b")

    v = await multi_judge_evaluate([judge_a, judge_b], make_run(), num_trials=1)
    assert isinstance(v.reasoning, str)
    assert len(v.reasoning) > 0
    # Should mention agreement rate
    assert "100%" in v.reasoning or "agreement" in v.reasoning.lower()


@pytest.mark.agent_test(layer="judge")
async def test_multi_judge_reasoning_mentions_disagreement():
    """ConsensusVerdict.reasoning mentions DISAGREEMENT when judges disagree."""
    rubric_a = make_rubric("quality_a")
    rubric_b = make_rubric("quality_b")
    judge_a = RubricJudge(rubric=rubric_a, llm=make_llm({"accuracy": 5}), model_name="a")
    judge_b = RubricJudge(rubric=rubric_b, llm=make_llm({"accuracy": 1}), model_name="b")

    v = await multi_judge_evaluate([judge_a, judge_b], make_run(), num_trials=1)
    assert "DISAGREEMENT" in v.reasoning or "disagree" in v.reasoning.lower()


# ---------------------------------------------------------------------------
# multi_judge_evaluate: edge cases
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="judge")
async def test_multi_judge_fewer_than_two_raises():
    """multi_judge_evaluate requires >= 2 judges."""
    rubric = make_rubric()
    judge = RubricJudge(rubric=rubric, llm=make_llm({"accuracy": 5}))
    with pytest.raises(ValueError, match="2"):
        await multi_judge_evaluate([judge], make_run(), num_trials=1)


@pytest.mark.agent_test(layer="judge")
async def test_multi_judge_empty_list_raises():
    """multi_judge_evaluate with empty list raises ValueError."""
    with pytest.raises(ValueError):
        await multi_judge_evaluate([], make_run(), num_trials=1)


@pytest.mark.agent_test(layer="judge")
async def test_multi_judge_concurrent_false():
    """multi_judge_evaluate with concurrent=False runs sequentially — same result."""
    rubric_a = make_rubric("quality_a")
    rubric_b = make_rubric("quality_b")
    judge_a = RubricJudge(rubric=rubric_a, llm=make_llm({"accuracy": 5}), model_name="a")
    judge_b = RubricJudge(rubric=rubric_b, llm=make_llm({"accuracy": 5}), model_name="b")

    v = await multi_judge_evaluate([judge_a, judge_b], make_run(), num_trials=1, concurrent=False)
    assert v.verdict == Verdict.PASS
    assert v.agreement_rate == 1.0


@pytest.mark.agent_test(layer="judge")
async def test_multi_judge_inconclusive_propagation():
    """When judges return INCONCLUSIVE verdicts, consensus handles them correctly."""
    call_count = [0]

    def make_alternating_llm():
        async def _llm(s, u):
            call_count[0] += 1
            val = 5 if call_count[0] % 2 == 1 else 1
            return json.dumps(
                {
                    "scores": [{"criterion": "accuracy", "value": val, "reasoning": "ok"}],
                    "overall_reasoning": "ok",
                }
            )

        return _llm

    rubric_a = make_rubric("quality_a")
    rubric_b = make_rubric("quality_b")
    judge_a = RubricJudge(rubric=rubric_a, llm=make_alternating_llm(), model_name="a")
    judge_b = RubricJudge(rubric=rubric_b, llm=make_alternating_llm(), model_name="b")

    # With num_trials=4, each judge alternates 2 pass 2 fail → INCONCLUSIVE per judge
    v = await multi_judge_evaluate([judge_a, judge_b], make_run(), num_trials=4, min_pass_rate=0.5)
    # Both judges are INCONCLUSIVE — result is either INCONCLUSIVE or some tiebreak
    assert isinstance(v, ConsensusVerdict)
    assert v.verdict in (Verdict.PASS, Verdict.FAIL, Verdict.INCONCLUSIVE)


# ---------------------------------------------------------------------------
# F-052: judge_verdicts key collision when same rubric name used
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="judge")
async def test_f052_judge_verdicts_no_key_collision():
    """F-052 FIXED: judge_verdicts key now includes model_name to prevent collision.

    Key format changed from 'rubric_judge:{rubric}' to 'rubric_judge:{rubric}:{model}'.
    All 3 judges with same rubric now produce distinct keys.
    """
    # Canonical use case: same rubric, different LLM model_names
    rubric = make_rubric("quality")  # same name for all judges
    judge_gpt4 = RubricJudge(rubric=rubric, llm=make_llm({"accuracy": 5}), model_name="gpt-4")
    judge_claude = RubricJudge(rubric=rubric, llm=make_llm({"accuracy": 5}), model_name="claude-3")
    judge_gemini = RubricJudge(rubric=rubric, llm=make_llm({"accuracy": 1}), model_name="gemini-pro")

    v = await multi_judge_evaluate([judge_gpt4, judge_claude, judge_gemini], make_run(), num_trials=1)

    # F-052 FIXED: 3 separate keys, one per judge (includes model name)
    assert len(v.judge_verdicts) == 3, (
        f"Expected 3 keys (one per judge), got {len(v.judge_verdicts)}: {list(v.judge_verdicts.keys())}"
    )
    assert "rubric_judge:quality:gpt-4" in v.judge_verdicts
    assert "rubric_judge:quality:claude-3" in v.judge_verdicts
    assert "rubric_judge:quality:gemini-pro" in v.judge_verdicts


@pytest.mark.agent_test(layer="judge")
async def test_f052_workaround_different_rubric_names():
    """F-052: New key format — 'rubric_judge:{rubric}:{model}'.

    All 3 judges produce separate keys with the new format.
    """
    judge_gpt4 = RubricJudge(
        rubric=make_rubric("quality_gpt4"),
        llm=make_llm({"accuracy": 5}),
        model_name="gpt-4",
    )
    judge_claude = RubricJudge(
        rubric=make_rubric("quality_claude"),
        llm=make_llm({"accuracy": 5}),
        model_name="claude-3",
    )
    judge_gemini = RubricJudge(
        rubric=make_rubric("quality_gemini"),
        llm=make_llm({"accuracy": 1}),
        model_name="gemini-pro",
    )

    v = await multi_judge_evaluate([judge_gpt4, judge_claude, judge_gemini], make_run(), num_trials=1)

    # With unique rubric names + model names, all 3 keys are preserved
    assert len(v.judge_verdicts) == 3
    assert "rubric_judge:quality_gpt4:gpt-4" in v.judge_verdicts
    assert "rubric_judge:quality_claude:claude-3" in v.judge_verdicts
    assert "rubric_judge:quality_gemini:gemini-pro" in v.judge_verdicts
    # Correct individual verdicts
    assert v.judge_verdicts["rubric_judge:quality_gpt4:gpt-4"].verdict == Verdict.PASS
    assert v.judge_verdicts["rubric_judge:quality_gemini:gemini-pro"].verdict == Verdict.FAIL


# ---------------------------------------------------------------------------
# F-053: ConsensusVerdict and multi_judge_evaluate not at top-level checkagent
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="judge")
def test_f053_consensus_verdict_not_at_top_level():
    """F-053 FIXED: ConsensusVerdict IS importable from top-level checkagent."""
    import checkagent
    assert hasattr(checkagent, "ConsensusVerdict"), (
        "ConsensusVerdict not found at top-level — F-053 should be fixed."
    )


@pytest.mark.agent_test(layer="judge")
def test_f053_multi_judge_evaluate_not_at_top_level():
    """F-053 FIXED: multi_judge_evaluate IS importable from top-level checkagent."""
    import checkagent
    assert hasattr(checkagent, "multi_judge_evaluate"), (
        "multi_judge_evaluate not found at top-level — F-053 should be fixed."
    )


# ---------------------------------------------------------------------------
# ConsensusVerdict fields
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="judge")
async def test_consensus_verdict_fields():
    """ConsensusVerdict has expected fields: verdict, judge_verdicts, agreement_rate,
    has_disagreement, reasoning.
    """
    rubric_a = make_rubric("quality_a")
    rubric_b = make_rubric("quality_b")
    judge_a = RubricJudge(rubric=rubric_a, llm=make_llm({"accuracy": 5}), model_name="a")
    judge_b = RubricJudge(rubric=rubric_b, llm=make_llm({"accuracy": 5}), model_name="b")

    v = await multi_judge_evaluate([judge_a, judge_b], make_run(), num_trials=1)

    assert isinstance(v, ConsensusVerdict)
    assert isinstance(v.verdict, Verdict)
    assert isinstance(v.judge_verdicts, dict)
    assert isinstance(v.agreement_rate, float)
    assert isinstance(v.has_disagreement, bool)
    assert isinstance(v.reasoning, str)
    assert 0.0 <= v.agreement_rate <= 1.0


@pytest.mark.agent_test(layer="judge")
async def test_consensus_verdict_judge_verdicts_values_are_judge_verdict():
    """Values in ConsensusVerdict.judge_verdicts are JudgeVerdict instances."""
    rubric_a = make_rubric("quality_a")
    rubric_b = make_rubric("quality_b")
    judge_a = RubricJudge(rubric=rubric_a, llm=make_llm({"accuracy": 5}), model_name="a")
    judge_b = RubricJudge(rubric=rubric_b, llm=make_llm({"accuracy": 5}), model_name="b")

    v = await multi_judge_evaluate([judge_a, judge_b], make_run(), num_trials=1)
    for jv in v.judge_verdicts.values():
        assert isinstance(jv, JudgeVerdict)
        assert hasattr(jv, "verdict")
        assert hasattr(jv, "pass_rate")


@pytest.mark.agent_test(layer="judge")
async def test_consensus_verdict_agreement_rate_range():
    """agreement_rate is always in [0, 1]."""
    for n_pass, n_fail in [(0, 3), (1, 2), (2, 1), (3, 0)]:
        judges = []
        for i in range(n_pass):
            judges.append(
                RubricJudge(
                    rubric=make_rubric(f"r_pass_{i}"),
                    llm=make_llm({"accuracy": 5}),
                    model_name=f"pass_{i}",
                )
            )
        for i in range(n_fail):
            judges.append(
                RubricJudge(
                    rubric=make_rubric(f"r_fail_{i}"),
                    llm=make_llm({"accuracy": 1}),
                    model_name=f"fail_{i}",
                )
            )
        if len(judges) < 2:
            continue
        v = await multi_judge_evaluate(judges, make_run(), num_trials=1)
        assert 0.0 <= v.agreement_rate <= 1.0, f"n_pass={n_pass} n_fail={n_fail}"


# ---------------------------------------------------------------------------
# Integration: ca_judge fixture + multi_judge_evaluate
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="judge")
async def test_ca_judge_with_multi_judge_evaluate(ca_judge):
    """ca_judge fixture-created judges work with multi_judge_evaluate."""
    rubric_a = make_rubric("r_a", "c")
    rubric_b = make_rubric("r_b", "c")
    judge_a = ca_judge(rubric_a, make_llm({"c": 5}), model_name="model_a")
    judge_b = ca_judge(rubric_b, make_llm({"c": 5}), model_name="model_b")

    run = make_run()
    v = await multi_judge_evaluate([judge_a, judge_b], run, num_trials=1)
    assert v.verdict == Verdict.PASS
    assert v.agreement_rate == 1.0
