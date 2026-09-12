"""Chapter 2 governance — deterministic recompute rejects bad plans; hashes are stable."""
from server.optimisation_demo.economics import segment_candidate_coefficients
from server.optimisation_demo.governance import (
    recompute_and_validate, plan_hash, policy_hash, content_hash,
)

FIXTURE = {
    "candidate_prices": [1000.0, 1050.0, 1100.0],
    "modelled_variable_cost_per_sale": 800.0,
    "segments": [
        {"segment": "A", "opportunities": 1000, "purchase_probabilities": [0.75, 0.74, 0.70]},
        {"segment": "B", "opportunities": 1000, "purchase_probabilities": [0.70, 0.56, 0.40]},
        {"segment": "C", "opportunities": 1000, "purchase_probabilities": [0.80, 0.72, 0.60]},
    ],
}
SEGS = ["A", "B", "C"]
COEFFS = segment_candidate_coefficients(FIXTURE)


def test_valid_plan_recomputes():
    plan = {"A": 1100.0, "B": 1000.0, "C": 1050.0}   # the margin-first plan
    r = recompute_and_validate(SEGS, plan, COEFFS)
    assert r["ok"]
    assert r["totals"]["total_sales"] == 2120.0
    assert r["totals"]["total_margin"] == 530000.0


def test_partial_plan_rejected():
    r = recompute_and_validate(SEGS, {"A": 1100.0, "B": 1000.0}, COEFFS)
    assert not r["ok"] and any("coverage" in f for f in r["failures"])


def test_factor_not_scored_rejected():
    r = recompute_and_validate(SEGS, {"A": 999.0, "B": 1000.0, "C": 1050.0}, COEFFS)
    assert not r["ok"] and any("not a scored candidate" in f for f in r["failures"])


def test_sales_floor_enforced_on_recompute():
    plan = {"A": 1100.0, "B": 1000.0, "C": 1050.0}   # 2,120 sales
    r = recompute_and_validate(SEGS, plan, COEFFS, min_portfolio_sales=2200)
    assert not r["ok"] and any("below the floor" in f for f in r["failures"])


def test_empty_plan_rejected():
    assert not recompute_and_validate(SEGS, {}, COEFFS)["ok"]


def test_hashes_stable_and_order_independent():
    assert plan_hash({"A": 1.0, "B": 1.05}) == plan_hash({"B": 1.05, "A": 1.0})
    assert plan_hash({"A": 1.0}) != plan_hash({"A": 1.05})
    assert policy_hash({"objective": "maximise_expected_margin"}) == content_hash({"objective": "maximise_expected_margin"})
