"""Acceptance tests for the optimisation-demo calculation (brief §Acceptance/Calculation).

These prove the worked example is exact and that winners are computed, not hardcoded.
"""
import pytest

from server.optimisation_demo.core import (
    load_example, optimise, score_candidates, select_best, mark_feasibility,
)

# Canonical table from the brief: price -> (customers, margin/sale, total margin, premium)
CANONICAL = {
    900:  (900.0, 100.0,  90000.0, 810000.0),
    950:  (830.0, 150.0, 124500.0, 788500.0),
    1000: (750.0, 200.0, 150000.0, 750000.0),
    1050: (740.0, 250.0, 185000.0, 777000.0),
    1100: (700.0, 300.0, 210000.0, 770000.0),
    1150: (450.0, 350.0, 157500.0, 517500.0),
}


@pytest.fixture
def example():
    return load_example()


# 1. Every fixture row matches the canonical table, including premium.
def test_fixture_rows_match_canonical(example):
    rows = {r["price"]: r for r in score_candidates(example)}
    assert set(rows) == set(CANONICAL)
    for price, (cust, mps, margin, premium) in CANONICAL.items():
        r = rows[price]
        assert r["expected_customers"] == cust
        assert r["margin_per_sale"] == mps
        assert r["expected_total_margin"] == margin
        assert r["expected_premium"] == premium


# 2. Baseline is £1,000 / 750 / £150,000.
def test_baseline(example):
    res = optimise(example)
    assert res["baseline"] == {
        "price": 1000, "expected_customers": 750.0,
        "expected_total_margin": 150000.0, "expected_premium": 750000.0,
    }


# 3. Run A: no requirement -> £1,100 / 700 / £210,000.
def test_run_a(example):
    res = optimise(example, min_expected_customers=None)
    assert res["no_feasible"] is False
    assert res["winner"] == {
        "price": 1100, "expected_customers": 700.0,
        "expected_total_margin": 210000.0, "expected_premium": 770000.0,
    }
    # against baseline: +£100, -50 customers, +£60,000 margin
    assert res["comparison"] == {
        "price_delta": 100.0, "customers_delta": -50.0,
        "margin_delta": 60000.0, "premium_delta": 20000.0,
    }
    assert sum(r["selected"] for r in res["candidates"]) == 1


# 4. Run B: target 830 -> £950 / 830 / £124,500.
def test_run_b(example):
    res = optimise(example, min_expected_customers=830)
    assert res["no_feasible"] is False
    assert res["winner"] == {
        "price": 950, "expected_customers": 830.0,
        "expected_total_margin": 124500.0, "expected_premium": 788500.0,
    }
    # only £900 and £950 are feasible
    feasible = {r["price"] for r in res["candidates"] if r["feasible"]}
    assert feasible == {900, 950}
    # infeasible rows carry the plain reason
    infeasible = [r for r in res["candidates"] if not r["feasible"]]
    assert all(r["feasibility_reason"] == "Below the sales target" for r in infeasible)
    # against baseline: -£50, +80 customers, -£25,500 margin
    assert res["comparison"] == {
        "price_delta": -50.0, "customers_delta": 80.0,
        "margin_delta": -25500.0, "premium_delta": 38500.0,
    }


# 5. A target of 901 returns no feasible candidate; no silent reduction.
def test_target_901_no_feasible(example):
    res = optimise(example, min_expected_customers=901)
    assert res["no_feasible"] is True
    assert res["winner"] is None
    assert res["comparison"] is None
    assert all(not r["feasible"] for r in res["candidates"])


# 6. Ties resolve deterministically: nearest to baseline, then lower price.
def test_ties_deterministic():
    tie = {
        "example_id": "tie", "baseline_price": 1000,
        "opportunities": 1000, "modelled_variable_cost_per_sale": 800,
        "candidates": [
            {"price": 900,  "purchase_probability": 0.60},  # 600 * 100 = 60,000
            {"price": 1000, "purchase_probability": 0.10},  # 100 * 200 = 20,000
            {"price": 1100, "purchase_probability": 0.20},  # 200 * 300 = 60,000  (tie with 900)
        ],
    }
    res = optimise(tie)
    # 900 and 1100 tie at 60,000, equidistant from 1000 -> lower price wins
    assert res["winner"]["price"] == 900
    assert res["winner"]["expected_total_margin"] == 60000.0


# 7. Invalid inputs are rejected clearly.
def test_invalid_inputs(example):
    bad_prob = dict(example, candidates=[{"price": 1000, "purchase_probability": 1.5}])
    with pytest.raises(ValueError, match="purchase_probability"):
        optimise(bad_prob)

    neg_opps = dict(example, opportunities=-5)
    with pytest.raises(ValueError, match="opportunities"):
        optimise(neg_opps)

    no_candidates = dict(example, candidates=[])
    with pytest.raises(ValueError, match="candidates"):
        optimise(no_candidates)

    # baseline not among candidate prices
    bad_baseline = dict(example, baseline_price=999)
    with pytest.raises(ValueError, match="baseline_price"):
        optimise(bad_baseline)

    with pytest.raises(ValueError, match="min_expected_customers"):
        optimise(example, min_expected_customers=-10)


# 8. Winner is the highest-margin feasible row from enumeration — not hardcoded.
def test_winner_not_hardcoded():
    # A different fixture whose winner is £1,000 (not the grandma answers).
    other = {
        "example_id": "other", "baseline_price": 1000,
        "opportunities": 1000, "modelled_variable_cost_per_sale": 800,
        "candidates": [
            {"price": 900,  "purchase_probability": 0.50},  # 500 * 100 = 50,000
            {"price": 1000, "purchase_probability": 0.90},  # 900 * 200 = 180,000  (winner)
            {"price": 1100, "purchase_probability": 0.30},  # 300 * 300 = 90,000
        ],
    }
    res = optimise(other)
    assert res["winner"]["price"] == 1000
    # equals the max feasible expected margin from complete enumeration
    rows = mark_feasibility(score_candidates(other), None)
    best = max(r["expected_total_margin"] for r in rows if r["feasible"])
    assert res["winner"]["expected_total_margin"] == best == 180000.0


# Selection returns None when nothing is feasible (helper-level check).
def test_select_best_none_when_infeasible(example):
    rows = mark_feasibility(score_candidates(example), 100000)
    assert select_best(rows, example["baseline_price"]) is None
