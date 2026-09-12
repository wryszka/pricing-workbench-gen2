"""Chapter 2 — the demand model + its validation (pure; scikit-learn only).

A readable logistic model and a monotone gradient-boosted challenger, trained on the
out-of-time split. At a candidate price we recompute the price-dependent features
coherently (offered/market and offered/baseline) while preserving risk features.

Validation thresholds are FROZEN here (before inspecting final-test results). They are
demo eligibility tolerances, not industry approval standards; failing checks stay
visible and block eligibility.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .data import FEATURES, CANDIDATE_LO, CANDIDATE_HI

# Frozen demo-eligibility thresholds (predeclared).
FROZEN_THRESHOLDS = {
    "min_final_test_obs": 5000,
    "max_weighted_calibration_error": 0.05,   # over 10 probability bins
    "max_abs_mean_pred_minus_conv": 0.03,
    "min_segment_obs_for_check": 200,
    "n_calibration_bins": 10,
}
# Monotone: conversion decreases as either price ratio rises; other features free.
_MONO = [-1 if f in ("offered_over_market", "offered_over_baseline") else 0 for f in FEATURES]


def train_logistic(train: pd.DataFrame) -> Any:
    m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    m.fit(train[FEATURES], train["converted"])
    return m


def train_monotone_gbt(train: pd.DataFrame) -> Any:
    m = HistGradientBoostingClassifier(monotonic_cst=_MONO, max_iter=200,
                                       learning_rate=0.08, max_depth=4, random_state=0)
    m.fit(train[FEATURES], train["converted"])
    return m


def _predict(model: Any, df: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(df[FEATURES])[:, 1]


def predict_at(model: Any, opps: pd.DataFrame, factor: float) -> np.ndarray:
    """Predicted purchase probability at candidate price = baseline × factor.

    Recomputes the price-dependent features coherently; risk features are preserved.
    """
    offered = opps["baseline_price"].to_numpy() * factor
    feats = pd.DataFrame({
        "offered_over_market": offered / opps["market_premium"].to_numpy(),
        "offered_over_baseline": np.full(len(opps), float(factor)),
        "driver_age": opps["driver_age"].to_numpy(),
        "no_claims_years": opps["no_claims_years"].to_numpy(),
        "mileage_k": opps["mileage_k"].to_numpy(),
        "vehicle_value_k": opps["vehicle_value_k"].to_numpy(),
        "vehicle_group": opps["vehicle_group"].to_numpy(),
    })[FEATURES]
    return model.predict_proba(feats)[:, 1]


def _weighted_calibration_error(y: np.ndarray, p: np.ndarray, bins: int) -> float:
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    err = 0.0
    n = len(y)
    for b in range(bins):
        mask = idx == b
        if mask.sum() == 0:
            continue
        err += (mask.sum() / n) * abs(p[mask].mean() - y[mask].mean())
    return float(err)


def monotone_along_price(model: Any, opps: pd.DataFrame, factors=None) -> bool:
    """Mean predicted conversion must not increase as the candidate factor rises."""
    factors = factors if factors is not None else np.round(np.arange(CANDIDATE_LO, CANDIDATE_HI + 1e-9, 0.01), 2)
    means = [float(predict_at(model, opps, f).mean()) for f in factors]
    return all(means[i + 1] <= means[i] + 1e-9 for i in range(len(means) - 1))


def validate(model: Any, final_test: pd.DataFrame, future: pd.DataFrame) -> dict[str, Any]:
    """Run the frozen validation battery on the out-of-time final test set."""
    y = final_test["converted"].to_numpy()
    p = _predict(model, final_test)
    T = FROZEN_THRESHOLDS

    metrics = {
        "final_test_obs": int(len(y)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)),            # secondary
        "weighted_calibration_error": _weighted_calibration_error(y, p, T["n_calibration_bins"]),
        "mean_pred_minus_conv": float(p.mean() - y.mean()),
        "monotone_along_price": monotone_along_price(model, future),
    }

    # Per-segment calibration for groups with enough observations.
    per_segment = []
    ft = final_test.assign(_p=p)
    for seg, g in ft.groupby("segment"):
        n = len(g)
        row = {"segment": seg, "obs": int(n)}
        if n >= T["min_segment_obs_for_check"]:
            row["mean_pred_minus_conv"] = float(g["_p"].mean() - g["converted"].mean())
            row["sufficient"] = True
        else:
            row["sufficient"] = False
        per_segment.append(row)

    failures = []
    if metrics["final_test_obs"] < T["min_final_test_obs"]:
        failures.append(f"final-test obs {metrics['final_test_obs']} < {T['min_final_test_obs']}")
    if metrics["weighted_calibration_error"] > T["max_weighted_calibration_error"]:
        failures.append(f"calibration error {metrics['weighted_calibration_error']:.4f} > {T['max_weighted_calibration_error']}")
    if abs(metrics["mean_pred_minus_conv"]) > T["max_abs_mean_pred_minus_conv"]:
        failures.append(f"mean pred−conv {metrics['mean_pred_minus_conv']:.4f} outside ±{T['max_abs_mean_pred_minus_conv']}")
    if not metrics["monotone_along_price"]:
        failures.append("mean predicted conversion is not monotone decreasing along the price path")

    return {"metrics": metrics, "per_segment": per_segment,
            "passes": len(failures) == 0, "failures": failures,
            "thresholds": T}
