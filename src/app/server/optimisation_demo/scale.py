"""Scale-benchmark support (WP5) — pure, testable core.

The scale story is honest only if the distributed path produces the *same* coefficients as
the reference path before any timing is compared, and only if the cache is keyed on
everything that can change the coefficients. This module provides both, with no Spark
import so they can be unit tested off-platform:

* :func:`coeff_cache_key` — a stable key over the input population, model, feature
  contract, candidate grid and world. A change to any of these invalidates the entry;
  a compatible change (a different objective or sales threshold, which does not change the
  coefficients) reuses it.
* :func:`coefficients_agree` — element-wise agreement of two coefficient maps within a
  declared tolerance, returning the max absolute/relative difference so a benchmark can
  *verify agreement before comparing timings* and never claim a speedup on mismatched math.

The scale is primarily in scoring/scenario evaluation, not the segment-level MILP: more
opportunities multiply the scoring work but leave the compact per-segment solve unchanged
unless the solver's own dimensions (segments × candidates × worlds) grow.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Iterable, Optional


def _h(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def hash_grid(factors: Iterable[float]) -> str:
    return _h([round(float(f), 6) for f in sorted(factors)])


def hash_world(market_scale: float, cost_scale: float) -> str:
    return _h({"market_scale": round(float(market_scale), 6), "cost_scale": round(float(cost_scale), 6)})


def coeff_cache_key(*, input_hash: str, model_hash: str, feature_hash: str,
                    grid_hash: str, world_hash: str) -> str:
    """Cache key for a scored coefficient block. Objective/threshold are deliberately NOT
    part of the key: they change the *solve*, not the coefficients, so a re-solve under a
    compatible objective or a different sales floor reuses the cached coefficients."""
    return _h({"input": input_hash, "model": model_hash, "feature": feature_hash,
               "grid": grid_hash, "world": world_hash})


def coefficients_agree(
    serial: dict[Any, dict[str, float]],
    distributed: dict[Any, dict[str, float]],
    rtol: float = 1e-6,
    atol: float = 1e-6,
    fields: tuple[str, ...] = ("expected_margin", "expected_sales"),
) -> dict[str, Any]:
    """Verify two coefficient maps agree within tolerance BEFORE comparing timings.

    Returns ok + the max absolute and relative differences and any keys that are missing on
    one side. Keys mismatch or any field out of tolerance ⇒ ok=False (never compare timings)."""
    keys_s, keys_d = set(serial), set(distributed)
    missing = sorted([str(k) for k in (keys_s ^ keys_d)])
    max_abs = 0.0
    max_rel = 0.0
    worst: Optional[str] = None
    for k in (keys_s & keys_d):
        for f in fields:
            a = float(serial[k][f]); b = float(distributed[k][f])
            d = abs(a - b)
            r = d / max(abs(a), 1e-12)
            if d > max_abs:
                max_abs, worst = d, f"{k}:{f}"
            max_rel = max(max_rel, r)
    within = (not missing) and all(
        abs(float(serial[k][f]) - float(distributed[k][f])) <= atol + rtol * abs(float(serial[k][f]))
        for k in (keys_s & keys_d) for f in fields
    )
    return {"ok": bool(within), "missing_keys": missing,
            "max_abs_diff": max_abs, "max_rel_diff": max_rel, "worst_at": worst,
            "n_keys": len(keys_s & keys_d)}


def duration_breakdown(prep_s: float, score_s: float, solve_s: float, startup_s: float) -> dict[str, float]:
    """Report phases separately (startup vs preparation vs scoring vs solve) — never a
    single opaque total. Total is their sum, reported alongside, not instead of."""
    for name, v in (("prep", prep_s), ("score", score_s), ("solve", solve_s), ("startup", startup_s)):
        if v is not None and (not math.isfinite(v) or v < 0):
            raise ValueError(f"{name} duration must be finite and non-negative")
    total = float(prep_s) + float(score_s) + float(solve_s) + float(startup_s)
    return {"startup_s": round(float(startup_s), 3), "prep_s": round(float(prep_s), 3),
            "score_s": round(float(score_s), 3), "solve_s": round(float(solve_s), 3),
            "total_s": round(total, 3)}
