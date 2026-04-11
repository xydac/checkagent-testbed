"""
Session 009 — Cost tracking: CostTracker, CostBreakdown, CostReport,
calculate_run_cost, BudgetExceededError.

Upgrade: 8e6a0a8 → e38593a

Focus:
- Confirm F-014 (datasets regression) is fixed
- Explore the new cost tracking API
- Document DX issues around missing top-level exports and missing fixture
"""

import pytest
from checkagent import (
    AgentInput,
    AgentRun,
    BudgetExceededError,
    CostBreakdown,
    CostReport,
    CostTracker,
    Step,
    ToolCall,
    calculate_run_cost,
)
from checkagent.core.config import BudgetConfig
from checkagent.core.cost import BUILTIN_PRICING, ProviderPricing


# ---------------------------------------------------------------------------
# F-014 regression status — datasets module restored in e38593a
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_datasets_f014_goldendataset_importable():
    """F-014 fixed: GoldenDataset is importable again after e38593a."""
    from checkagent.datasets import GoldenDataset  # should not raise

    assert GoldenDataset is not None


@pytest.mark.agent_test(layer="mock")
def test_datasets_f014_evalcase_importable():
    """F-014 fixed (TestCase renamed to EvalCase): EvalCase is importable."""
    from checkagent.datasets import EvalCase  # TestCase renamed to EvalCase

    assert EvalCase is not None


@pytest.mark.agent_test(layer="mock")
def test_datasets_f014_parametrize_cases_importable():
    """F-014 fixed: parametrize_cases is importable again after e38593a."""
    from checkagent.datasets import parametrize_cases  # should not raise

    assert callable(parametrize_cases)


# ---------------------------------------------------------------------------
# calculate_run_cost — basic
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_known_model_returns_breakdown():
    step = Step(model="claude-sonnet", prompt_tokens=1000, completion_tokens=500)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    bd = calculate_run_cost(run)
    assert isinstance(bd, CostBreakdown)


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_correct_token_counts():
    step = Step(model="claude-sonnet", prompt_tokens=1000, completion_tokens=500)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    bd = calculate_run_cost(run)
    assert bd.total_input_tokens == 1000
    assert bd.total_output_tokens == 500
    assert bd.total_tokens == 1500


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_math_matches_builtin_pricing():
    """claude-sonnet: $3.00/M input, $15.00/M output."""
    step = Step(model="claude-sonnet", prompt_tokens=1000, completion_tokens=500)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    bd = calculate_run_cost(run)
    expected = 1000 / 1e6 * 3.0 + 500 / 1e6 * 15.0  # 0.0105
    assert abs(bd.total_cost - expected) < 1e-9


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_per_model_breakdown():
    step = Step(model="claude-sonnet", prompt_tokens=1000, completion_tokens=500)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    bd = calculate_run_cost(run)
    assert "claude-sonnet" in bd.per_model
    model_cost = bd.per_model["claude-sonnet"]
    assert model_cost.input_tokens == 1000
    assert model_cost.output_tokens == 500


# ---------------------------------------------------------------------------
# calculate_run_cost — unpriced steps
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_step_without_model_is_unpriced():
    step = Step(output_text="hello")  # no model set
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    bd = calculate_run_cost(run)
    assert bd.unpriced_steps == 1
    assert bd.total_cost == 0.0


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_unknown_model_is_unpriced():
    step = Step(model="some-unknown-model-xyz", prompt_tokens=1000, completion_tokens=500)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    bd = calculate_run_cost(run)
    assert bd.unpriced_steps == 1
    assert bd.total_cost == 0.0


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_empty_run_zero_cost():
    run = AgentRun(input=AgentInput(query="q"))  # no steps
    bd = calculate_run_cost(run)
    assert bd.unpriced_steps == 0
    assert bd.total_cost == 0.0
    assert bd.total_tokens == 0


# ---------------------------------------------------------------------------
# calculate_run_cost — pricing_overrides and default_pricing
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_pricing_overrides_replace_builtin():
    step = Step(model="claude-sonnet", prompt_tokens=1000, completion_tokens=500)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    # Override with different rate to verify override takes effect
    overrides = {"claude-sonnet": ProviderPricing(input=1.0, output=2.0)}
    bd = calculate_run_cost(run, pricing_overrides=overrides)
    expected = 1000 / 1e6 * 1.0 + 500 / 1e6 * 2.0  # 0.002
    assert abs(bd.total_cost - expected) < 1e-9
    assert bd.unpriced_steps == 0


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_default_pricing_used_for_unknown_model():
    step = Step(model="my-private-model", prompt_tokens=1000, completion_tokens=500)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    default = ProviderPricing(input=2.0, output=10.0)
    bd = calculate_run_cost(run, default_pricing=default)
    expected = 1000 / 1e6 * 2.0 + 500 / 1e6 * 10.0  # 0.007
    assert abs(bd.total_cost - expected) < 1e-9
    assert bd.unpriced_steps == 0


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_overrides_take_priority_over_default():
    step = Step(model="my-model", prompt_tokens=1000, completion_tokens=0)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    overrides = {"my-model": ProviderPricing(input=5.0, output=0.0)}
    default = ProviderPricing(input=1.0, output=0.0)
    bd = calculate_run_cost(run, pricing_overrides=overrides, default_pricing=default)
    expected = 1000 / 1e6 * 5.0
    assert abs(bd.total_cost - expected) < 1e-9


# ---------------------------------------------------------------------------
# calculate_run_cost — multi-model runs
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_multi_model_both_appear_in_per_model():
    step1 = Step(model="claude-sonnet", prompt_tokens=500, completion_tokens=200)
    step2 = Step(model="gpt-4o", prompt_tokens=300, completion_tokens=100)
    run = AgentRun(input=AgentInput(query="q"), steps=[step1, step2])
    bd = calculate_run_cost(run)
    assert "claude-sonnet" in bd.per_model
    assert "gpt-4o" in bd.per_model


@pytest.mark.agent_test(layer="mock")
def test_calculate_run_cost_multi_model_costs_sum_correctly():
    step1 = Step(model="claude-sonnet", prompt_tokens=1000, completion_tokens=0)
    step2 = Step(model="claude-sonnet", prompt_tokens=2000, completion_tokens=0)
    run = AgentRun(input=AgentInput(query="q"), steps=[step1, step2])
    bd = calculate_run_cost(run)
    expected = 3000 / 1e6 * 3.0
    assert abs(bd.total_cost - expected) < 1e-9
    assert bd.per_model["claude-sonnet"].input_tokens == 3000


# ---------------------------------------------------------------------------
# CostBreakdown.to_dict()
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_cost_breakdown_to_dict_has_expected_keys():
    step = Step(model="claude-sonnet", prompt_tokens=100, completion_tokens=50)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    bd = calculate_run_cost(run)
    d = bd.to_dict()
    assert "total_input_tokens" in d
    assert "total_output_tokens" in d
    assert "total_tokens" in d
    assert "total_cost_usd" in d
    assert "unpriced_steps" in d
    assert "per_model" in d


# ---------------------------------------------------------------------------
# CostTracker — basic accumulation
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_cost_tracker_record_returns_cost_breakdown():
    tracker = CostTracker()
    step = Step(model="claude-sonnet", prompt_tokens=100, completion_tokens=50)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    result = tracker.record(run)
    assert isinstance(result, CostBreakdown)


@pytest.mark.agent_test(layer="mock")
def test_cost_tracker_run_count_accumulates():
    tracker = CostTracker()
    run = AgentRun(input=AgentInput(query="q"))
    tracker.record(run)
    tracker.record(run)
    assert tracker.run_count == 2


@pytest.mark.agent_test(layer="mock")
def test_cost_tracker_total_cost_accumulates():
    tracker = CostTracker()
    step = Step(model="claude-sonnet", prompt_tokens=1000, completion_tokens=500)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    single_cost = 1000 / 1e6 * 3.0 + 500 / 1e6 * 15.0  # 0.0105
    tracker.record(run)
    tracker.record(run)
    assert abs(tracker.total_cost - single_cost * 2) < 1e-9


@pytest.mark.agent_test(layer="mock")
def test_cost_tracker_total_tokens_accumulates():
    tracker = CostTracker()
    step = Step(model="claude-sonnet", prompt_tokens=1000, completion_tokens=500)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    tracker.record(run)
    tracker.record(run)
    assert tracker.total_tokens == 3000


@pytest.mark.agent_test(layer="mock")
def test_cost_tracker_runs_property_length():
    tracker = CostTracker()
    run = AgentRun(input=AgentInput(query="q"))
    tracker.record(run)
    tracker.record(run)
    assert len(tracker.runs) == 2


# ---------------------------------------------------------------------------
# CostTracker — summary / CostReport
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_cost_tracker_summary_returns_cost_report():
    tracker = CostTracker()
    step = Step(model="claude-sonnet", prompt_tokens=100, completion_tokens=50)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    tracker.record(run)
    report = tracker.summary()
    assert isinstance(report, CostReport)


@pytest.mark.agent_test(layer="mock")
def test_cost_report_run_count_matches():
    tracker = CostTracker()
    run = AgentRun(input=AgentInput(query="q"))
    tracker.record(run)
    tracker.record(run)
    tracker.record(run)
    report = tracker.summary()
    assert report.run_count == 3


@pytest.mark.agent_test(layer="mock")
def test_cost_report_avg_cost_per_run():
    tracker = CostTracker()
    step = Step(model="claude-sonnet", prompt_tokens=1000, completion_tokens=500)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    tracker.record(run)
    tracker.record(run)
    report = tracker.summary()
    expected_single = 1000 / 1e6 * 3.0 + 500 / 1e6 * 15.0
    assert abs(report.avg_cost_per_run - expected_single) < 1e-9


@pytest.mark.agent_test(layer="mock")
def test_cost_report_budget_utilization_fractions():
    from checkagent.core.config import BudgetConfig

    step = Step(model="claude-sonnet", prompt_tokens=100000, completion_tokens=50000)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    # cost = 1.05
    budget = BudgetConfig(per_suite=2.0, per_ci_run=5.0)
    tracker = CostTracker(budget=budget)
    tracker.record(run)
    report = tracker.summary()
    util = report.budget_utilization()
    assert abs(util["per_suite"] - 1.05 / 2.0) < 1e-9
    assert abs(util["per_ci_run"] - 1.05 / 5.0) < 1e-9


# ---------------------------------------------------------------------------
# CostTracker — budget enforcement
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_cost_tracker_check_test_budget_raises_when_over():
    from checkagent.core.config import BudgetConfig

    step = Step(model="claude-sonnet", prompt_tokens=1000000, completion_tokens=500000)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    budget = BudgetConfig(per_test=0.001)
    tracker = CostTracker(budget=budget)
    bd = tracker.record(run)
    with pytest.raises(BudgetExceededError):
        tracker.check_test_budget(bd)


@pytest.mark.agent_test(layer="mock")
def test_cost_tracker_check_suite_budget_raises_when_over():
    from checkagent.core.config import BudgetConfig

    step = Step(model="claude-sonnet", prompt_tokens=100000, completion_tokens=50000)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    budget = BudgetConfig(per_suite=0.01)
    tracker = CostTracker(budget=budget)
    tracker.record(run)
    with pytest.raises(BudgetExceededError):
        tracker.check_suite_budget()


@pytest.mark.agent_test(layer="mock")
def test_cost_tracker_check_ci_budget_raises_when_over():
    from checkagent.core.config import BudgetConfig

    step = Step(model="claude-sonnet", prompt_tokens=100000, completion_tokens=50000)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    budget = BudgetConfig(per_ci_run=0.01)
    tracker = CostTracker(budget=budget)
    tracker.record(run)
    with pytest.raises(BudgetExceededError):
        tracker.check_ci_budget()


@pytest.mark.agent_test(layer="mock")
def test_cost_tracker_no_budget_set_does_not_raise():
    step = Step(model="claude-sonnet", prompt_tokens=1000000, completion_tokens=500000)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    tracker = CostTracker()  # no budget
    bd = tracker.record(run)
    # None of these should raise when no budget is configured
    tracker.check_test_budget(bd)
    tracker.check_suite_budget()
    tracker.check_ci_budget()


@pytest.mark.agent_test(layer="mock")
def test_budget_exceeded_error_message_mentions_limit_and_actual():
    from checkagent.core.config import BudgetConfig

    step = Step(model="claude-sonnet", prompt_tokens=1000000, completion_tokens=0)
    run = AgentRun(input=AgentInput(query="q"), steps=[step])
    budget = BudgetConfig(per_test=0.001)
    tracker = CostTracker(budget=budget)
    bd = tracker.record(run)
    with pytest.raises(BudgetExceededError) as exc_info:
        tracker.check_test_budget(bd)
    msg = str(exc_info.value)
    assert "0.001" in msg or "0.0010" in msg  # limit mentioned
    assert "per_test" in msg  # which limit triggered


# ---------------------------------------------------------------------------
# DX finding: ProviderPricing / BudgetConfig / BUILTIN_PRICING not top-level
# F-018: must import from checkagent.core.cost / checkagent.core.config
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_f018_provider_pricing_not_importable_from_top_level():
    """F-018: ProviderPricing is not in checkagent.__all__ — requires internal import."""
    import checkagent

    assert not hasattr(checkagent, "ProviderPricing"), (
        "ProviderPricing is now top-level — update F-018 status"
    )


@pytest.mark.agent_test(layer="mock")
def test_f018_budget_config_not_importable_from_top_level():
    """F-018: BudgetConfig is not in checkagent.__all__ — requires internal import."""
    import checkagent

    assert not hasattr(checkagent, "BudgetConfig"), (
        "BudgetConfig is now top-level — update F-018 status"
    )


@pytest.mark.agent_test(layer="mock")
def test_f018_builtin_pricing_not_importable_from_top_level():
    """F-018: BUILTIN_PRICING is not in checkagent.__all__ — requires internal import."""
    import checkagent

    assert not hasattr(checkagent, "BUILTIN_PRICING"), (
        "BUILTIN_PRICING is now top-level — update F-018 status"
    )


# ---------------------------------------------------------------------------
# DX finding: no ap_cost_tracker fixture (F-019)
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_f019_no_ap_cost_tracker_fixture(request):
    """F-019: There is no ap_cost_tracker pytest fixture — must instantiate CostTracker manually."""
    fixture_names = list(request.session._fixturemanager._arg2fixturedefs.keys())
    assert "ap_cost_tracker" not in fixture_names, (
        "ap_cost_tracker fixture now exists — update F-019 status"
    )


# ---------------------------------------------------------------------------
# BUILTIN_PRICING sanity — verify known models are present
# ---------------------------------------------------------------------------


@pytest.mark.agent_test(layer="mock")
def test_builtin_pricing_contains_major_models():
    for model in ("claude-sonnet", "gpt-4o", "gemini-2.0-flash"):
        assert model in BUILTIN_PRICING, f"Expected {model} in BUILTIN_PRICING"


@pytest.mark.agent_test(layer="mock")
def test_builtin_pricing_claude_sonnet_rates():
    pricing = BUILTIN_PRICING["claude-sonnet"]
    assert pricing.input == 3.0  # $3.00 per 1M input tokens
    assert pricing.output == 15.0  # $15.00 per 1M output tokens
