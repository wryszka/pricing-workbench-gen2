"""Chapter 2 — policy/run contracts (pure). Reject unknown keys and unsupported values."""
from __future__ import annotations

from typing import Any, Optional

ALLOWED_OBJECTIVES = {"maximise_expected_margin"}
DEFAULT_FACTORS = [round(0.90 + 0.01 * i, 2) for i in range(21)]   # 0.90 … 1.10 (Ch2 live grid)
_POLICY_KEYS = {"objective", "candidate_factors", "min_portfolio_sales_ratio"}


def validate_policy(policy: dict[str, Any]) -> None:
    unknown = set(policy) - _POLICY_KEYS
    if unknown:
        raise ValueError(f"unsupported policy keys: {sorted(unknown)}")
    obj = policy.get("objective", "maximise_expected_margin")
    if obj not in ALLOWED_OBJECTIVES:
        raise ValueError(f"unsupported objective {obj!r}; allowed: {sorted(ALLOWED_OBJECTIVES)}")
    factors = policy.get("candidate_factors", DEFAULT_FACTORS)
    if not factors or any((not isinstance(f, (int, float)) or f <= 0) for f in factors):
        raise ValueError("candidate_factors must be positive numbers")
    r = policy.get("min_portfolio_sales_ratio")
    if r is not None and (not isinstance(r, (int, float)) or r < 0):
        raise ValueError("min_portfolio_sales_ratio must be a non-negative number or omitted")


def normalise_policy(objective: str = "maximise_expected_margin",
                     candidate_factors: Optional[list[float]] = None,
                     min_portfolio_sales_ratio: Optional[float] = None) -> dict[str, Any]:
    policy = {"objective": objective,
              "candidate_factors": candidate_factors or DEFAULT_FACTORS,
              "min_portfolio_sales_ratio": min_portfolio_sales_ratio}
    validate_policy(policy)
    return policy
