"""WP5 scale-benchmark core — cache keying + coefficient-agreement gate + phase timing."""
import pytest

from server.optimisation_demo import scale


def test_cache_key_changes_with_inputs_but_not_objective():
    base = dict(input_hash="i", model_hash="m", feature_hash="f",
                grid_hash=scale.hash_grid([0.99, 1.0, 1.01]), world_hash=scale.hash_world(1.0, 1.0))
    k0 = scale.coeff_cache_key(**base)
    # Objective/threshold are not part of the key (they change the solve, not coefficients),
    # so a compatible re-solve reuses the SAME cached coefficients.
    assert scale.coeff_cache_key(**base) == k0
    # A changed input invalidates the entry.
    assert scale.coeff_cache_key(**{**base, "input_hash": "i2"}) != k0
    assert scale.coeff_cache_key(**{**base, "model_hash": "m2"}) != k0
    assert scale.coeff_cache_key(**{**base, "world_hash": scale.hash_world(1.0, 1.05)}) != k0
    # A changed candidate grid invalidates.
    assert scale.coeff_cache_key(**{**base, "grid_hash": scale.hash_grid([0.98, 1.0])}) != k0


def test_grid_hash_order_independent():
    assert scale.hash_grid([1.0, 1.05, 0.95]) == scale.hash_grid([0.95, 1.0, 1.05])


def test_coefficients_agree_within_tolerance():
    s = {("A", 1.0): {"expected_margin": 100.0, "expected_sales": 700.0}}
    d = {("A", 1.0): {"expected_margin": 100.0 + 1e-9, "expected_sales": 700.0}}
    r = scale.coefficients_agree(s, d)
    assert r["ok"] is True and r["missing_keys"] == [] and r["max_abs_diff"] < 1e-6


def test_coefficients_disagreement_blocks_timing():
    s = {("A", 1.0): {"expected_margin": 100.0, "expected_sales": 700.0}}
    d = {("A", 1.0): {"expected_margin": 101.0, "expected_sales": 700.0}}   # 1.0 off
    r = scale.coefficients_agree(s, d)
    assert r["ok"] is False and r["max_abs_diff"] == pytest.approx(1.0)
    assert r["worst_at"] == "('A', 1.0):expected_margin"


def test_coefficients_missing_key_blocks():
    s = {("A", 1.0): {"expected_margin": 1.0, "expected_sales": 1.0},
         ("B", 1.0): {"expected_margin": 1.0, "expected_sales": 1.0}}
    d = {("A", 1.0): {"expected_margin": 1.0, "expected_sales": 1.0}}
    r = scale.coefficients_agree(s, d)
    assert r["ok"] is False and r["missing_keys"]


def test_duration_breakdown_reports_phases_separately():
    b = scale.duration_breakdown(prep_s=2.0, score_s=10.0, solve_s=0.5, startup_s=30.0)
    assert b["total_s"] == pytest.approx(42.5)
    assert b["startup_s"] == 30.0 and b["score_s"] == 10.0
    with pytest.raises(ValueError):
        scale.duration_breakdown(prep_s=-1, score_s=1, solve_s=1, startup_s=1)
