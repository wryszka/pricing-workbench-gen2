"""Chapter 2 acceptance — learned demand model + frozen validation battery.

Trains on the out-of-time split of the frozen synthetic data and checks the
predeclared demo-eligibility thresholds. Labelled a simulation throughout.
"""
import pytest

from server.optimisation_demo.data import make_historic, time_split, make_future
from server.optimisation_demo.demand import (
    train_logistic, train_monotone_gbt, validate, predict_at, monotone_along_price,
)


@pytest.fixture(scope="module")
def data():
    hist = make_historic()
    train, val, test = time_split(hist)
    return train, val, test, make_future()


def test_final_test_split_meets_min_obs(data):
    _, _, test, _ = data
    assert len(test) >= 5000


def test_populations_disjoint_no_leakage(data):
    train, val, test, future = data
    hist_ids = set(train.opportunity_id) | set(val.opportunity_id) | set(test.opportunity_id)
    assert hist_ids.isdisjoint(set(future.opportunity_id))


def test_logistic_passes_frozen_validation(data):
    train, _, test, future = data
    rep = validate(train_logistic(train), test, future)
    assert rep["passes"], rep["failures"]
    assert rep["metrics"]["weighted_calibration_error"] <= 0.05
    assert abs(rep["metrics"]["mean_pred_minus_conv"]) <= 0.03
    assert rep["metrics"]["monotone_along_price"]


def test_monotone_gbt_challenger_is_monotone(data):
    train, _, _, future = data
    assert monotone_along_price(train_monotone_gbt(train), future)


def test_recovery_downward_law_simulation_check(data):
    # Labelled simulation check: mean predicted conversion falls as candidate price rises.
    train, _, _, future = data
    m = train_logistic(train)
    means = [float(predict_at(m, future, f).mean()) for f in (0.90, 1.00, 1.10)]
    assert means[0] > means[1] > means[2]
