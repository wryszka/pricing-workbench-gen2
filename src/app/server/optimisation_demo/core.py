"""Pure optimisation-demo calculations — the whole lesson, in plain Python.

No Spark, no Databricks SDK, no UI, no model-serving imports belong here. The
point of this module is that a presenter can read it top to bottom and explain
every number.

The objective is fixed: **maximise expected margin**. The human changes a sales
requirement (a minimum number of *expected* customers); that changes which
permitted candidate price wins. Both answers fall out of the same visible
arithmetic and the same objective.

Arithmetic (per candidate offered price):
    expected_customers    = opportunities × purchase_probability
    margin_per_sale        = offered_price − modelled_variable_cost_per_sale
    expected_total_margin  = expected_customers × margin_per_sale
    expected_premium       = expected_customers × offered_price

Selection: the highest-expected-margin candidate that is *feasible* (meets the
sales requirement). We enumerate every supplied candidate — this is exact over
the candidate set and easy to teach; there is no solver, no interpolation, no
learned model here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

OBJECTIVE = "maximise_expected_margin"

# Money and probabilities are supplied as clean values; a tiny tolerance keeps
# float arithmetic from breaking exact comparisons (e.g. 0.83 × 1000 == 830).
_EPS = 1e-6


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_example(example: dict[str, Any]) -> None:
    """Reject a malformed example with a clear, presenter-legible message."""
    if not isinstance(example, dict):
        raise ValueError("example must be an object")
    for key in ("example_id", "opportunities", "modelled_variable_cost_per_sale",
                "baseline_price", "candidates"):
        if example.get(key) is None:
            raise ValueError(f"example is missing required field '{key}'")

    opps = example["opportunities"]
    if not isinstance(opps, (int, float)) or opps <= 0:
        raise ValueError("opportunities must be a positive number")

    cost = example["modelled_variable_cost_per_sale"]
    if not isinstance(cost, (int, float)) or cost < 0:
        raise ValueError("modelled_variable_cost_per_sale must be a non-negative number")

    candidates = example["candidates"]
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidates must be a non-empty list")

    prices = []
    for i, c in enumerate(candidates):
        price = c.get("price")
        prob = c.get("purchase_probability")
        if not isinstance(price, (int, float)) or price <= 0:
            raise ValueError(f"candidate {i}: price must be a positive number")
        if not isinstance(prob, (int, float)) or not (0.0 <= prob <= 1.0):
            raise ValueError(f"candidate {i} (price {price}): purchase_probability must be between 0 and 1")
        prices.append(price)

    baseline = example["baseline_price"]
    if baseline not in prices:
        raise ValueError(
            f"baseline_price {baseline} must be one of the candidate prices "
            f"so it can be evaluated as a comparison; candidate prices are {sorted(prices)}"
        )


def validate_requirement(min_expected_customers: Optional[float]) -> None:
    """The only requirement in this demo: an optional minimum on expected customers."""
    if min_expected_customers is None:
        return
    if not isinstance(min_expected_customers, (int, float)) or min_expected_customers < 0:
        raise ValueError("min_expected_customers must be a non-negative number or omitted")


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def _round_money(x: float) -> float:
    return round(x + 0.0, 2)


def score_candidate(price: float, probability: float,
                    opportunities: float, cost_per_sale: float) -> dict[str, float]:
    """The four teaching equations for a single offered price."""
    expected_customers = opportunities * probability
    margin_per_sale = price - cost_per_sale
    expected_total_margin = expected_customers * margin_per_sale
    expected_premium = expected_customers * price
    return {
        "price": price,
        "purchase_probability": probability,
        "expected_customers": round(expected_customers, 6),
        "margin_per_sale": _round_money(margin_per_sale),
        "expected_total_margin": _round_money(expected_total_margin),
        "expected_premium": _round_money(expected_premium),
    }


def score_candidates(example: dict[str, Any]) -> list[dict[str, float]]:
    opps = example["opportunities"]
    cost = example["modelled_variable_cost_per_sale"]
    rows = [
        score_candidate(c["price"], c["purchase_probability"], opps, cost)
        for c in example["candidates"]
    ]
    rows.sort(key=lambda r: r["price"])
    return rows


def mark_feasibility(rows: list[dict[str, Any]],
                     min_expected_customers: Optional[float]) -> list[dict[str, Any]]:
    """Tag each candidate feasible/infeasible with a plain reason."""
    for r in rows:
        if min_expected_customers is None:
            r["feasible"] = True
            r["feasibility_reason"] = "No sales requirement"
        elif r["expected_customers"] >= min_expected_customers - _EPS:
            r["feasible"] = True
            r["feasibility_reason"] = "Meets the sales target"
        else:
            r["feasible"] = False
            r["feasibility_reason"] = "Below the sales target"
    return rows


def select_best(rows: list[dict[str, Any]], baseline_price: float) -> Optional[dict[str, Any]]:
    """Highest expected margin among feasible candidates.

    Deterministic tie rule: nearest to the baseline price, then the lower price.
    Returns None when no candidate is feasible.
    """
    feasible = [r for r in rows if r["feasible"]]
    if not feasible:
        return None
    best_margin = max(r["expected_total_margin"] for r in feasible)
    tied = [r for r in feasible if abs(r["expected_total_margin"] - best_margin) <= _EPS]
    tied.sort(key=lambda r: (abs(r["price"] - baseline_price), r["price"]))
    return tied[0]


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def optimise(example: dict[str, Any],
             min_expected_customers: Optional[float] = None) -> dict[str, Any]:
    """Validate → score every candidate → mark feasibility → select the winner.

    Returns a structured result with the full candidate table, the baseline
    comparison, the winner (or a clear no-feasible-solution status), and the
    requirement that produced it.
    """
    validate_example(example)
    validate_requirement(min_expected_customers)

    baseline_price = example["baseline_price"]
    rows = mark_feasibility(score_candidates(example), min_expected_customers)

    baseline = next(r for r in rows if r["price"] == baseline_price)
    winner = select_best(rows, baseline_price)

    for r in rows:
        r["selected"] = bool(winner is not None and r["price"] == winner["price"])

    comparison = None
    if winner is not None:
        comparison = {
            "price_delta": _round_money(winner["price"] - baseline["price"]),
            "customers_delta": round(winner["expected_customers"] - baseline["expected_customers"], 6),
            "margin_delta": _round_money(winner["expected_total_margin"] - baseline["expected_total_margin"]),
            "premium_delta": _round_money(winner["expected_premium"] - baseline["expected_premium"]),
        }

    return {
        "example_id": example.get("example_id"),
        "example_version": example.get("example_version"),
        "segment_label": example.get("segment_label"),
        "opportunities": example["opportunities"],
        "modelled_variable_cost_per_sale": example["modelled_variable_cost_per_sale"],
        "baseline_price": baseline_price,
        "objective": OBJECTIVE,
        "requirement": {"min_expected_customers": min_expected_customers},
        "candidates": rows,
        "baseline": {
            "price": baseline["price"],
            "expected_customers": baseline["expected_customers"],
            "expected_total_margin": baseline["expected_total_margin"],
            "expected_premium": baseline["expected_premium"],
        },
        "winner": None if winner is None else {
            "price": winner["price"],
            "expected_customers": winner["expected_customers"],
            "expected_total_margin": winner["expected_total_margin"],
            "expected_premium": winner["expected_premium"],
        },
        "no_feasible": winner is None,
        "comparison": comparison,
    }


def validate_result(example: dict[str, Any], result: dict[str, Any]) -> None:
    """Independently re-check a result before it is saved/trusted (job asserts this).

    Confirms candidate coverage, per-row arithmetic, and selection consistency —
    so an incomplete or inconsistent result can never be marked a success.
    """
    cand_prices = {c["price"] for c in example["candidates"]}
    row_prices = {r["price"] for r in result["candidates"]}
    if cand_prices != row_prices:
        raise ValueError(f"candidate coverage mismatch: inputs {sorted(cand_prices)} vs results {sorted(row_prices)}")

    opps = example["opportunities"]
    cost = example["modelled_variable_cost_per_sale"]
    for r in result["candidates"]:
        exp_cust = opps * r["purchase_probability"]
        exp_margin = exp_cust * (r["price"] - cost)
        if abs(r["expected_customers"] - exp_cust) > 1e-3:
            raise ValueError(f"row {r['price']}: expected_customers off ({r['expected_customers']} vs {exp_cust})")
        if abs(r["expected_total_margin"] - exp_margin) > 1e-2:
            raise ValueError(f"row {r['price']}: expected_total_margin off ({r['expected_total_margin']} vs {exp_margin})")

    selected = [r for r in result["candidates"] if r.get("selected")]
    if result["no_feasible"]:
        if selected or result["winner"] is not None:
            raise ValueError("no_feasible result must have no selected row and no winner")
    else:
        if len(selected) != 1:
            raise ValueError(f"expected exactly one selected row, found {len(selected)}")
        if selected[0]["price"] != result["winner"]["price"]:
            raise ValueError("selected row does not match winner")
        feasible = [r for r in result["candidates"] if r["feasible"]]
        best = max(r["expected_total_margin"] for r in feasible)
        if result["winner"]["expected_total_margin"] < best - _EPS:
            raise ValueError("winner is not the highest-margin feasible candidate")


def load_example(path: str | Path | None = None) -> dict[str, Any]:
    """Load the canonical example.json (default: alongside this module)."""
    p = Path(path) if path else Path(__file__).with_name("example.json")
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)
