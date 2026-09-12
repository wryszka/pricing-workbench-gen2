"""Chapter 2 — synthetic outcome check draws from the generator, deterministically."""
import numpy as np
from server.optimisation_demo.data import make_future, _true_conversion, _seg_shift
from server.optimisation_demo.monitoring import simulate_outcomes, compare


def test_simulate_deterministic_and_seeded():
    fut = make_future()
    sel = {s: 1.0 for s in fut["segment"].unique()}
    a = simulate_outcomes(fut, sel, seed=1)
    b = simulate_outcomes(fut, sel, seed=1)
    c = simulate_outcomes(fut, sel, seed=2)
    assert a.equals(b)                      # same seed -> identical
    assert not a.equals(c)                  # different seed -> different draw


def test_observed_near_true_expectation_at_baseline():
    fut = make_future()
    sel = {s: 1.0 for s in fut["segment"].unique()}
    obs = simulate_outcomes(fut, sel, seed=7)
    total_obs = obs["observed_sales"].sum()
    # true expected sales at factor 1.0 (offered = baseline)
    q = _true_conversion(np.random.default_rng(0), fut["baseline_price"].to_numpy() / fut["market_premium"].to_numpy(), _seg_shift(fut))
    total_exp = q.sum()
    assert abs(total_obs - total_exp) < 0.05 * total_exp    # within sampling noise


def test_compare_joins_expected_observed():
    fut = make_future()
    sel = {s: 1.0 for s in fut["segment"].unique()}
    obs = simulate_outcomes(fut, sel, seed=3)
    rows = compare({s: {"expected_sales": 100.0, "expected_margin": 5000.0} for s in sel}, obs)
    assert len(rows) == len(obs)
    assert all("observed_sales" in r and "expected_sales" in r for r in rows)
