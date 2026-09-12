"""Chapter 2 — synthetic outcome check (pure).

Evaluate an approved release on an independently generated synthetic next period,
drawing outcomes from the FROZEN GENERATOR's true law — NOT the learned model's own
probabilities. So it is an independent check of the decision, not a self-fulfilling
replay. It is still synthetic (we wrote the world); it does not validate real demand
or realised claims.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .data import _true_conversion, _seg_shift


def simulate_outcomes(future: pd.DataFrame, selection: dict[str, float], seed: int = 424242) -> pd.DataFrame:
    """Draw realised purchases at the released per-segment factors from the true law.

    Returns per-segment observed sales + margin-over-modelled-cost + sample count.
    """
    rng = np.random.default_rng(seed)
    seg = future["segment"].to_numpy()
    base = future["baseline_price"].to_numpy()
    market = future["market_premium"].to_numpy()
    factor = np.array([float(selection.get(s, 1.0)) for s in seg])
    offered = base * factor
    cost = (future["expected_claims"].to_numpy()
            + future["per_sale_expenses"].to_numpy()
            + future["commission_rate"].to_numpy() * offered)
    q = _true_conversion(rng, offered / market, _seg_shift(future))
    bought = (rng.random(len(future)) < q).astype(int)
    df = pd.DataFrame({"segment": seg, "obs_sales": bought, "obs_margin": bought * (offered - cost)})
    agg = df.groupby("segment").agg(
        observed_sales=("obs_sales", "sum"),
        observed_margin=("obs_margin", "sum"),
        n=("obs_sales", "count")).reset_index()
    return agg


def compare(expected_by_segment: dict[str, dict[str, float]], observed: pd.DataFrame) -> list[dict[str, Any]]:
    """Join model-expected (from the release's stored scores) with generator-observed."""
    rows = []
    for _, o in observed.iterrows():
        seg = o["segment"]
        exp = expected_by_segment.get(seg, {})
        rows.append({
            "segment": seg, "n": int(o["n"]),
            "expected_sales": round(float(exp.get("expected_sales", 0.0)), 1),
            "observed_sales": int(o["observed_sales"]),
            "expected_margin": round(float(exp.get("expected_margin", 0.0)), 0),
            "observed_margin": round(float(o["observed_margin"]), 0),
        })
    return rows
