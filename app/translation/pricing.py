"""Approximate DeepSeek pricing, USD per 1M tokens
(api-docs.deepseek.com/quick_start/pricing/, see BIBLIOGRAFIA.md section 8).

Used only to estimate cost for the progress dashboard — not a billing
source of truth, DeepSeek's own account dashboard is authoritative.
"""
from __future__ import annotations

PRICING_USD_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "deepseek-v4-pro": {"input": 0.435, "output": 0.87},
    "deepseek-v4-flash": {"input": 0.14, "output": 0.28},
}


def estimate_cost_usd(usage: dict[str, dict[str, int]]) -> float:
    total = 0.0
    for model, counts in usage.items():
        rates = PRICING_USD_PER_MILLION_TOKENS.get(model)
        if not rates:
            continue
        total += counts.get("input", 0) * rates["input"] / 1_000_000
        total += counts.get("output", 0) * rates["output"] / 1_000_000
    return total
