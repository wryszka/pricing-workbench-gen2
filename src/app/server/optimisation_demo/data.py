"""Chapter 2 — frozen synthetic data (pure; numpy/pandas only).

Two datasets, both reproducible from a seed:
  • historic quotes over 24 months, with an actual offered price whose variation is
    generated **independently of the conversion noise** (so demand is identifiable),
    a contemporaneous market benchmark, pre-quote features, month and outcome; and
  • a prospective opportunity snapshot (a separate population) with per-opportunity
    cost inputs, baseline price and market benchmark.

Honesty rules baked in:
  • The true conversion law is logistic in offered/market (declared below) — a
    simulation, not a claim about real demand.
  • Price variation is independent of the conversion draw conditional on features,
    with declared support ±20% covering the 0.90–1.10 candidate range.
  • Historic and future populations are disjoint (separate id ranges) — no leakage.
  • No outcome-derived features (no realised claims at quote time).
  • Labels come from the true law, never from a fitted model.

Nine synthetic segments: age band (under 25 / 25–69 / 70+) × vehicle group
(<15 / 15–29 / ≥30). Age 70 belongs to the 70+ band.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GENERATOR_VERSION = "ch2-demand-v1"
CANDIDATE_LO, CANDIDATE_HI = 0.90, 1.10          # candidate multiplier range
FEATURES = ["offered_over_market", "offered_over_baseline",
            "driver_age", "no_claims_years", "mileage_k", "vehicle_value_k", "vehicle_group"]

# True demand law (logistic in offered/market): intercept + segment shift − sensitivity·(ratio−1).
_BASE_INTERCEPT = 1.15
_SENSITIVITY = 7.5


def age_band(age: np.ndarray) -> np.ndarray:
    return np.where(age < 25, "under 25", np.where(age < 70, "25–69", "70+"))


def vehicle_band(vg: np.ndarray) -> np.ndarray:
    return np.where(vg < 15, "grp<15", np.where(vg < 30, "grp15–29", "grp≥30"))


def segment_of(df: pd.DataFrame) -> pd.Series:
    return pd.Series(age_band(df["driver_age"].to_numpy()), index=df.index) + " · " \
        + pd.Series(vehicle_band(df["vehicle_group"].to_numpy()), index=df.index)


def _draw_population(rng: np.random.Generator, n: int, id_start: int) -> pd.DataFrame:
    driver_age = np.clip(rng.normal(48, 16, n).round(), 18, 88).astype(int)
    vehicle_group = np.clip(rng.normal(22, 12, n).round(), 1, 50).astype(int)
    no_claims_years = np.clip(rng.normal(6, 4, n).round(), 0, 20).astype(int)
    mileage_k = np.clip(rng.normal(9, 3, n), 2, 30).round(1)
    vehicle_value_k = np.clip(rng.normal(18, 9, n), 3, 80).round(1)
    # baseline (loaded) price rises with vehicle value/group, falls with no-claims.
    baseline = (600 + 22 * vehicle_value_k + 9 * vehicle_group - 12 * no_claims_years
                + rng.normal(0, 40, n)).round(2)
    baseline = np.clip(baseline, 300, 3000)
    return pd.DataFrame({
        "opportunity_id": np.arange(id_start, id_start + n),
        "driver_age": driver_age, "vehicle_group": vehicle_group,
        "no_claims_years": no_claims_years, "mileage_k": mileage_k,
        "vehicle_value_k": vehicle_value_k, "baseline_price": baseline,
    })


def _true_conversion(rng, ratio_to_market, seg_shift):
    z = _BASE_INTERCEPT + seg_shift - _SENSITIVITY * (ratio_to_market - 1.0)
    return 1.0 / (1.0 + np.exp(-z))


def _seg_shift(df: pd.DataFrame) -> np.ndarray:
    # Small, declared per-band demand shifts (older/high-group a touch less sensitive-looking).
    band = age_band(df["driver_age"].to_numpy())
    shift = np.where(band == "under 25", -0.35, np.where(band == "70+", 0.25, 0.0))
    return shift


def make_historic(seed: int = 20260912, n_per_month: int = 1400, months: int = 24) -> pd.DataFrame:
    """Historic quotes with independent price variation and true-law outcomes."""
    rng = np.random.default_rng(seed)
    frames = []
    for m in range(1, months + 1):
        pop = _draw_population(rng, n_per_month, id_start=1_000_000 + m * 100_000)
        market = (pop["baseline_price"].to_numpy() * rng.lognormal(0.0, 0.05, len(pop))).round(2)
        # Offered price varies INDEPENDENTLY of the conversion noise (±~20% support).
        offered = (pop["baseline_price"].to_numpy() * rng.lognormal(0.0, 0.09, len(pop))).round(2)
        ratio_market = offered / market
        q = _true_conversion(rng, ratio_market, _seg_shift(pop))
        converted = (rng.random(len(pop)) < q).astype(int)
        f = pop.assign(month=m, market_premium=market, offered_price=offered,
                       offered_over_market=offered / market,
                       offered_over_baseline=offered / pop["baseline_price"].to_numpy(),
                       converted=converted)
        frames.append(f)
    hist = pd.concat(frames, ignore_index=True)
    hist["segment"] = segment_of(hist).to_numpy()
    return hist


def time_split(hist: pd.DataFrame):
    """Out-of-time split: 1–16 train, 17–20 validation, 21–24 final test."""
    return (hist[hist.month <= 16].copy(),
            hist[(hist.month >= 17) & (hist.month <= 20)].copy(),
            hist[hist.month >= 21].copy())


def make_future(seed: int = 20260913, n: int = 5000) -> pd.DataFrame:
    """A separate prospective opportunity snapshot (disjoint population, id range 9_*)."""
    rng = np.random.default_rng(seed)
    pop = _draw_population(rng, n, id_start=9_000_000)
    market = (pop["baseline_price"].to_numpy() * rng.lognormal(0.0, 0.05, n)).round(2)
    # Three cost components (teaching): expected claims + per-sale expenses + commission·price.
    expected_claims = np.clip(pop["baseline_price"].to_numpy() * rng.uniform(0.55, 0.72, n), 100, None).round(2)
    per_sale_expenses = np.round(35 + 0.03 * pop["baseline_price"].to_numpy(), 2)
    commission_rate = np.full(n, 0.10)
    fut = pop.assign(market_premium=market, expected_claims=expected_claims,
                     per_sale_expenses=per_sale_expenses, commission_rate=commission_rate)
    fut["segment"] = segment_of(fut).to_numpy()
    return fut
