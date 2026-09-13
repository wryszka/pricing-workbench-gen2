"""Chapter 2 acceptance — the portfolio MILP, cross-checked against complete enumeration.

Uses the spec's exact-solver appendix fixture (3 segments, £800 cost, prices 1000/1050/1100).
"""
import itertools

import pytest

from server.optimisation_demo.economics import segment_candidate_coefficients, baseline_plan
from server.optimisation_demo.portfolio import solve_portfolio

FIXTURE = {
    "candidate_prices": [1000.0, 1050.0, 1100.0],
    "modelled_variable_cost_per_sale": 800.0,
    "segments": [
        {"segment": "Older/high-group", "opportunities": 1000, "purchase_probabilities": [0.75, 0.74, 0.70]},
        {"segment": "Price-sensitive",  "opportunities": 1000, "purchase_probabilities": [0.70, 0.56, 0.40]},
        {"segment": "Middle",           "opportunities": 1000, "purchase_probabilities": [0.80, 0.72, 0.60]},
    ],
}
SEGS = [s["segment"] for s in FIXTURE["segments"]]
CANDS = {s: FIXTURE["candidate_prices"] for s in SEGS}
BASELINE = {s: 1000.0 for s in SEGS}


@pytest.fixture
def coeffs():
    return segment_candidate_coefficients(FIXTURE)


def _enumerate_best(coeffs, floor):
    """Brute force: best total margin over all price combinations meeting the floor."""
    best = None
    for combo in itertools.product(FIXTURE["candidate_prices"], repeat=len(SEGS)):
        sales = sum(coeffs[(s, float(p))]["expected_sales"] for s, p in zip(SEGS, combo))
        if floor is not None and sales < floor - 1e-6:
            continue
        margin = sum(coeffs[(s, float(p))]["expected_margin"] for s, p in zip(SEGS, combo))
        if best is None or margin > best["margin"] + 1e-9:
            best = {"margin": margin, "sales": sales, "combo": dict(zip(SEGS, [float(p) for p in combo]))}
    return best


def test_baseline(coeffs):
    b = baseline_plan(FIXTURE, 1000.0, coeffs)
    assert b["expected_sales"] == 2250.0
    assert b["expected_total_margin"] == 450000.0


def test_margin_first(coeffs):
    r = solve_portfolio(SEGS, CANDS, coeffs, BASELINE, min_portfolio_sales=None)
    assert r["feasible"]
    assert r["selection"] == {"Older/high-group": 1100.0, "Price-sensitive": 1000.0, "Middle": 1050.0}
    assert r["total_expected_sales"] == 2120.0
    assert r["total_expected_margin"] == 530000.0


def test_protect_sales_2200_couples(coeffs):
    r = solve_portfolio(SEGS, CANDS, coeffs, BASELINE, min_portfolio_sales=2200)
    assert r["feasible"]
    # Middle's price moves to satisfy the shared floor — coupling.
    assert r["selection"] == {"Older/high-group": 1100.0, "Price-sensitive": 1000.0, "Middle": 1000.0}
    assert r["total_expected_sales"] == 2200.0
    assert r["total_expected_margin"] == 510000.0


def test_infeasible_when_target_exceeds_max_sales(coeffs):
    # Max possible sales is 2,250 (all at £1,000); 2,300 cannot be met.
    r = solve_portfolio(SEGS, CANDS, coeffs, BASELINE, min_portfolio_sales=2300)
    assert r["feasible"] is False
    assert r["status"] == "infeasible"


@pytest.mark.parametrize("floor", [None, 2000, 2120, 2200, 2250])
def test_milp_matches_enumeration(coeffs, floor):
    r = solve_portfolio(SEGS, CANDS, coeffs, BASELINE, min_portfolio_sales=floor)
    best = _enumerate_best(coeffs, floor)
    assert best is not None and r["feasible"]
    # The MILP objective must equal the exact enumerated optimum (ties may differ, margin must not).
    assert abs(r["total_expected_margin"] - best["margin"]) < 1e-6
    # Stricter feasible set cannot beat a looser one's optimum for the same objective.
    if floor is not None:
        looser = _enumerate_best(coeffs, None)
        assert best["margin"] <= looser["margin"] + 1e-9


def test_tie_breaks_toward_baseline(coeffs):
    # Price-sensitive ties at 1000 vs 1050 (both £140k); Middle ties at 1050 vs 1100 (both £180k).
    r = solve_portfolio(SEGS, CANDS, coeffs, BASELINE, min_portfolio_sales=None)
    assert r["selection"]["Price-sensitive"] == 1000.0   # nearer baseline than 1050
    assert r["selection"]["Middle"] == 1050.0            # nearer baseline than 1100


# --- WP1#4/#5: honest solver evidence + two-solve movement (no objective distortion) --- #

def _coeffs(spec):
    """spec: {(seg, price): (margin, sales)} -> coeffs dict."""
    return {k: {"expected_margin": m, "expected_sales": s} for k, (m, s) in spec.items()}


def test_status_and_gap_are_real_not_faked(coeffs):
    r = solve_portfolio(SEGS, CANDS, coeffs, BASELINE)
    assert r["feasible"] and r["status"] == "optimal"
    # gap is the ACTUAL solver gap (a number), and ~0 for a proven optimum — but it is
    # read from HiGHS, never hard-set. (Field present + finite + tiny.)
    assert r["gap"] is not None and abs(r["gap"]) < 1e-3


def test_primary_optimum_retained_where_old_penalty_would_distort():
    # Two segments; baseline 1000. For segment A the higher-margin plan (1100) is only
    # £0.05 better than the baseline-price plan — SMALLER than the old 1e-3*deviation
    # penalty (1e-3*100 = £0.10), so the old penalty would have wrongly picked 1000.
    segs = ["A", "B"]
    cands = {"A": [1000.0, 1100.0], "B": [1000.0]}
    baseline = {"A": 1000.0, "B": 1000.0}
    coeffs = _coeffs({
        ("A", 1000.0): (100.00, 700.0),
        ("A", 1100.0): (100.05, 650.0),   # true margin optimum, far from baseline
        ("B", 1000.0): (50.0, 700.0),
    })
    r = solve_portfolio(segs, cands, coeffs, baseline)   # movement_tolerance defaults to 0
    assert r["selection"]["A"] == 1100.0, "must keep the true margin optimum, not the penalty-biased plan"
    assert r["margin_sacrificed_for_movement"] == 0.0
    assert r["status"] == "optimal"


def test_movement_solve_breaks_genuine_ties_toward_baseline():
    # Exact margin tie between 1000 (at baseline) and 1100 (far): movement solve prefers 1000.
    segs = ["A"]
    cands = {"A": [1000.0, 1100.0]}
    baseline = {"A": 1000.0}
    coeffs = _coeffs({("A", 1000.0): (100.0, 700.0), ("A", 1100.0): (100.0, 650.0)})
    r = solve_portfolio(segs, cands, coeffs, baseline)
    assert r["selection"]["A"] == 1000.0
    assert r["movement_solve_used"] is True
    assert r["margin_sacrificed_for_movement"] == 0.0


def test_infeasible_floor_returns_infeasible_status(coeffs):
    r = solve_portfolio(SEGS, CANDS, coeffs, BASELINE, min_portfolio_sales=10_000)
    assert r["feasible"] is False and r["status"] == "infeasible"
    assert "gap" not in r or r.get("gap") is None
