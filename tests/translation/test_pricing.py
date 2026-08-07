from app.translation.pricing import estimate_cost_usd


def test_estimate_cost_usd_computes_pro_model_cost():
    usage = {"deepseek-v4-pro": {"input": 1_000_000, "output": 1_000_000}}

    cost = estimate_cost_usd(usage)

    assert cost == 0.435 + 0.87


def test_estimate_cost_usd_computes_flash_model_cost():
    usage = {"deepseek-v4-flash": {"input": 1_000_000, "output": 1_000_000}}

    cost = estimate_cost_usd(usage)

    assert cost == 0.14 + 0.28


def test_estimate_cost_usd_sums_across_multiple_models():
    usage = {
        "deepseek-v4-pro": {"input": 1_000_000, "output": 0},
        "deepseek-v4-flash": {"input": 0, "output": 1_000_000},
    }

    cost = estimate_cost_usd(usage)

    assert cost == 0.435 + 0.28


def test_estimate_cost_usd_ignores_unknown_models():
    usage = {"some-future-model": {"input": 1_000_000, "output": 1_000_000}}

    cost = estimate_cost_usd(usage)

    assert cost == 0.0


def test_estimate_cost_usd_returns_zero_for_empty_usage():
    assert estimate_cost_usd({}) == 0.0
