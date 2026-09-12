"""Chapter 3 — robust maximin: invariants + enumeration cross-check on a tiny fixture."""
import itertools

import pytest

from server.optimisation_demo.robustness import solve_robust

SEGS = ["A", "B"]
FACTORS = [1.0, 1.1]
CANDS = {s: FACTORS for s in SEGS}
# Two worlds. World w2 punishes raising prices (lower margin at 1.1), so the robust
# plan differs from the nominal (w1-only) plan.
M = {
    ("w1", "A", 1.0): 100, ("w1", "A", 1.1): 130, ("w1", "B", 1.0): 100, ("w1", "B", 1.1): 130,
    ("w2", "A", 1.0): 100, ("w2", "A", 1.1): 60,  ("w2", "B", 1.0): 100, ("w2", "B", 1.1): 60,
}
V = {k: 100.0 for k in M}                    # sales flat → floor non-binding here
BM = {"w1": 200.0, "w2": 200.0}              # baseline margin per world (both at factor 1.0 = 100+100)
BS = {"w1": 200.0, "w2": 200.0}


def _enum_worst(worlds):
    best = None
    for fa, fb in itertools.product(FACTORS, repeat=2):
        sel = {"A": fa, "B": fb}
        worst = min(sum(M[(w, s, sel[s])] for s in SEGS) - BM[w] for w in worlds)
        if best is None or worst > best["worst"] + 1e-9:
            best = {"worst": worst, "sel": sel}
    return best


def test_robust_matches_enumeration():
    r = solve_robust(["w1", "w2"], SEGS, CANDS, M, V, BM, BS, sales_ratio=0.0)
    assert r["feasible"]
    assert abs(r["worst_uplift"] - _enum_worst(["w1", "w2"])["worst"]) < 1e-6
    # robust picks factor 1.0 for both (raising loses in w2): worst uplift 0
    assert r["selection"] == {"A": 1.0, "B": 1.0}
    assert r["worst_uplift"] == 0.0


def test_one_world_robust_equals_nominal():
    rob = solve_robust(["w1"], SEGS, CANDS, M, V, BM, BS, sales_ratio=0.0)
    nom = solve_robust(["w1"], SEGS, CANDS, M, V, BM, BS, sales_ratio=0.0, objective="nominal")
    # single world: maximising worst-world uplift == maximising that world's margin
    assert rob["selection"] == nom["selection"] == {"A": 1.1, "B": 1.1}
    assert rob["nominal_margin"] == nom["nominal_margin"] == 260


def test_adding_a_world_cannot_increase_worst_uplift():
    one = solve_robust(["w1"], SEGS, CANDS, M, V, BM, BS, sales_ratio=0.0)["worst_uplift"]
    two = solve_robust(["w1", "w2"], SEGS, CANDS, M, V, BM, BS, sales_ratio=0.0)["worst_uplift"]
    assert two <= one + 1e-9


def test_duplicate_world_does_not_change_maximin():
    a = solve_robust(["w1", "w2"], SEGS, CANDS, M, V, BM, BS, sales_ratio=0.0)["worst_uplift"]
    b = solve_robust(["w1", "w2", "w2"], SEGS, CANDS, M, V, BM, BS, sales_ratio=0.0)["worst_uplift"]
    assert abs(a - b) < 1e-9


def test_robust_feasible_in_every_world():
    r = solve_robust(["w1", "w2"], SEGS, CANDS, M, V, BM, BS, sales_ratio=0.9)
    assert r["feasible"]
    assert all(w["meets_floor"] for w in r["per_world"])   # not averaged away


def test_infeasible_sales_floor():
    r = solve_robust(["w1", "w2"], SEGS, CANDS, M, V, BM, BS, sales_ratio=5.0)   # impossible
    assert r["feasible"] is False
