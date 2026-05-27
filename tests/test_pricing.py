from tobecon_evaluator.pricing import estimate_call_cost


def test_estimate_call_cost():
    estimate = estimate_call_cost(duration_seconds=120, llm_input_tokens=1_000_000, llm_output_tokens=500_000)
    assert round(estimate.stt_usd, 6) == 0.012
    assert round(estimate.llm_input_usd, 6) == 2.5
    assert round(estimate.llm_output_usd, 6) == 7.5
    assert round(estimate.total_usd, 6) == 10.012

