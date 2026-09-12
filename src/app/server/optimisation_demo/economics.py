"""Chapter 2 — shared expected-outcome economics (pure; no Spark/SDK/UI).

Per opportunity i offered price p:
    cost_i(p)   = expected_claims_i + per_sale_expenses_i + commission_rate_i * p
    margin_i(p) = p - cost_i(p)
Probability-weighted contributions: sales q, premium q·p, claims q·claims, margin q·margin.

Aggregate per (segment, candidate price) into coefficients M (expected margin) and
V (expected sales). We aggregate *individual* probability-weighted contributions —
never a single median-customer curve.
"""
from __future__ import annotations

from typing import Any, Optional


def cost_of(price: float, expected_claims: float,
            per_sale_expenses: float = 0.0, commission_rate: float = 0.0) -> float:
    return expected_claims + per_sale_expenses + commission_rate * price


def score_opportunity(price: float, probability: float, expected_claims: float,
                      per_sale_expenses: float = 0.0, commission_rate: float = 0.0) -> dict[str, float]:
    """One opportunity's probability-weighted expected contributions at an offered price."""
    cost = cost_of(price, expected_claims, per_sale_expenses, commission_rate)
    return {
        "expected_sales": probability,
        "expected_premium": probability * price,
        "expected_claims": probability * expected_claims,
        "expected_margin": probability * (price - cost),
    }


def aggregate(contributions: list[dict[str, float]]) -> dict[str, float]:
    """Sum opportunity contributions into a segment-candidate coefficient."""
    keys = ("expected_sales", "expected_premium", "expected_claims", "expected_margin")
    return {k: float(sum(c[k] for c in contributions)) for k in keys}


def segment_candidate_coefficients(fixture: dict[str, Any]) -> dict[tuple[str, float], dict[str, float]]:
    """Build M_sk / V_sk coefficients for the exact-solver teaching fixture.

    Fixture shape (segment-level demand — the appendix teaching form):
      {
        "candidate_prices": [1000, 1050, 1100],
        "modelled_variable_cost_per_sale": 800,     # flat teaching cost
        "segments": [
          {"segment": "Older/high-group", "opportunities": 1000,
           "purchase_probabilities": [0.75, 0.74, 0.70]},
          ...
        ]
      }
    Each segment's opportunities are homogeneous, so the coefficient is
    n · q · (price − cost) for margin and n · q for sales.
    """
    prices = fixture["candidate_prices"]
    cost = fixture["modelled_variable_cost_per_sale"]
    coeffs: dict[tuple[str, float], dict[str, float]] = {}
    for seg in fixture["segments"]:
        n = seg["opportunities"]
        probs = seg["purchase_probabilities"]
        if len(probs) != len(prices):
            raise ValueError(f"segment {seg['segment']}: {len(probs)} probabilities for {len(prices)} prices")
        for price, q in zip(prices, probs):
            contrib = score_opportunity(price, q, expected_claims=cost)
            coeffs[(seg["segment"], float(price))] = {k: n * v for k, v in contrib.items()}
    return coeffs


def coefficients_from_future(future: Any, factors: list[float], predict_fn) -> dict[tuple[str, float], dict[str, float]]:
    """Score the future opportunity snapshot at each candidate factor and aggregate
    per (segment, factor). `predict_fn(factor)` returns a purchase-probability array
    aligned to the snapshot rows. Individual costs use the three components; we sum
    *individual* probability-weighted contributions (no median-customer curve).
    """
    import numpy as np  # local import keeps the pure teaching path dependency-free
    import pandas as pd

    seg = future["segment"].to_numpy()
    base = future["baseline_price"].to_numpy()
    claims = future["expected_claims"].to_numpy()
    exp = future["per_sale_expenses"].to_numpy()
    comm = future["commission_rate"].to_numpy()
    coeffs: dict[tuple[str, float], dict[str, float]] = {}
    for fct in factors:
        offered = base * fct
        cost = claims + exp + comm * offered
        q = np.asarray(predict_fn(fct), dtype=float)
        df = pd.DataFrame({"segment": seg,
                           "m": q * (offered - cost), "v": q,
                           "prem": q * offered, "cl": q * claims})
        agg = df.groupby("segment").agg(m=("m", "sum"), v=("v", "sum"), prem=("prem", "sum"), cl=("cl", "sum"))
        for s, row in agg.iterrows():
            coeffs[(s, round(float(fct), 4))] = {
                "expected_margin": float(row["m"]), "expected_sales": float(row["v"]),
                "expected_premium": float(row["prem"]), "expected_claims": float(row["cl"]),
            }
    return coeffs


def baseline_plan(fixture: dict[str, Any], baseline_price: float,
                  coeffs: Optional[dict] = None) -> dict[str, float]:
    """Totals at the baseline price across all segments (the comparison reference)."""
    coeffs = coeffs or segment_candidate_coefficients(fixture)
    segs = [s["segment"] for s in fixture["segments"]]
    sales = sum(coeffs[(s, float(baseline_price))]["expected_sales"] for s in segs)
    margin = sum(coeffs[(s, float(baseline_price))]["expected_margin"] for s in segs)
    return {"expected_sales": float(sales), "expected_total_margin": float(margin)}
