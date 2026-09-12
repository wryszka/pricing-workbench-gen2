"""Chapter 2 acceptance — end-to-end score → solve on the learned-model future snapshot.

The two recording runs (Margin first; Protect sales at 98% of the model's baseline
predicted sales) over the 21-factor grid, using individual costs + the trained model.
"""
import pytest

from server.optimisation_demo.data import make_historic, time_split, make_future
from server.optimisation_demo.demand import train_logistic, predict_at
from server.optimisation_demo.economics import coefficients_from_future
from server.optimisation_demo.portfolio import solve_portfolio

FACTORS = [round(0.90 + 0.01 * i, 2) for i in range(21)]   # 0.90 … 1.10


@pytest.fixture(scope="module")
def setup():
    train, _, _ = time_split(make_historic())
    future = make_future()
    model = train_logistic(train)
    predict_fn = lambda f: predict_at(model, future, f)
    coeffs = coefficients_from_future(future, FACTORS, predict_fn)
    segs = sorted(future["segment"].unique())
    cands = {s: FACTORS for s in segs}
    baseline_key = {s: 1.0 for s in segs}
    baseline_sales = float(predict_at(model, future, 1.0).sum())
    return segs, cands, coeffs, baseline_key, baseline_sales


def test_margin_first_solves(setup):
    segs, cands, coeffs, baseline_key, _ = setup
    r = solve_portfolio(segs, cands, coeffs, baseline_key, min_portfolio_sales=None)
    assert r["feasible"]
    assert set(r["selection"].keys()) == set(segs)      # one factor per segment
    assert all(0.90 - 1e-9 <= f <= 1.10 + 1e-9 for f in r["selection"].values())


def test_protect_sales_98pct(setup):
    segs, cands, coeffs, baseline_key, baseline_sales = setup
    floor = 0.98 * baseline_sales
    r = solve_portfolio(segs, cands, coeffs, baseline_key, min_portfolio_sales=floor)
    assert r["feasible"]
    assert r["total_expected_sales"] >= floor - 1e-6


def test_constrained_margin_not_above_unconstrained(setup):
    segs, cands, coeffs, baseline_key, baseline_sales = setup
    unc = solve_portfolio(segs, cands, coeffs, baseline_key, min_portfolio_sales=None)
    con = solve_portfolio(segs, cands, coeffs, baseline_key, min_portfolio_sales=0.98 * baseline_sales)
    # A stricter feasible set cannot beat the unconstrained optimum for the same objective.
    assert con["total_expected_margin"] <= unc["total_expected_margin"] + 1e-6


def test_impossible_sales_floor_infeasible(setup):
    segs, cands, coeffs, baseline_key, baseline_sales = setup
    # No plan can exceed the maximum achievable sales (well above baseline).
    r = solve_portfolio(segs, cands, coeffs, baseline_key, min_portfolio_sales=baseline_sales * 5)
    assert r["feasible"] is False
