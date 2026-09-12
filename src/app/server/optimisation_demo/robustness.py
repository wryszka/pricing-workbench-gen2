"""Chapter 3 — robust portfolio optimisation across worlds (pure; scipy only).

A "world" is an immutable (demand model × market scenario × cost scenario). For each
world w we have segment-candidate coefficients M[(w,s,f)] (expected margin) and
V[(w,s,f)] (expected sales), plus that world's baseline margin/sales at factor 1.0.

Robust decision (maximise the worst world's uplift), one factor per segment, with the
inherited per-world sales floor:

    maximise t
    s.t.  t ≤ Σ_sk M_wsk x_sk − baseline_margin_w      for every world w
          Σ_sk V_wsk x_sk ≥ r · baseline_sales_w        for every world w
          Σ_k x_sk = 1                                   for every segment
          x_sk ∈ {0,1},  t continuous

`objective="nominal"` instead maximises the FIRST world's expected margin over the
SAME (all-world) feasible set — so the two answers separate "changed objective" from
"tightened feasibility". Exact finite-candidate MILP (HiGHS); status/gap reported.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

_TIE_EPS = 1e-4   # nudge toward baseline factor to break ties; << any real margin gap


def solve_robust(
    worlds: list[str],
    segments: list[str],
    candidates: dict[str, list[float]],
    M: dict[tuple[str, str, float], float],
    V: dict[tuple[str, str, float], float],
    baseline_margin: dict[str, float],
    baseline_sales: dict[str, float],
    sales_ratio: float = 0.98,
    baseline_factor: float = 1.0,
    objective: str = "robust",
    allowed: Optional[set[tuple[str, float]]] = None,
) -> dict[str, Any]:
    var: list[tuple[str, float]] = []
    for s in segments:
        for f in candidates[s]:
            if allowed is None or (s, float(f)) in allowed:
                var.append((s, float(f)))
    if not var:
        return {"feasible": False, "status": "infeasible", "reason": "no eligible candidates"}
    nx = len(var)
    idx = {sp: i for i, sp in enumerate(var)}
    N = nx + 1          # x variables + t
    T = nx

    c = np.zeros(N)
    if objective == "robust":
        c[T] = -1.0     # maximise t
        for i, (_s, f) in enumerate(var):
            c[i] += _TIE_EPS * abs(f - baseline_factor)
    elif objective == "nominal":
        w0 = worlds[0]
        for i, (s, f) in enumerate(var):
            c[i] = -(M[(w0, s, f)] - _TIE_EPS * abs(f - baseline_factor))
    else:
        raise ValueError(f"unknown objective {objective!r}")

    cons = []
    for s in segments:                                  # one candidate per segment
        row = np.zeros(N)
        for f in candidates[s]:
            if (s, float(f)) in idx:
                row[idx[(s, float(f))]] = 1.0
        cons.append(LinearConstraint(row, lb=1, ub=1))
    for w in worlds:                                    # per-world sales floor
        vrow = np.zeros(N)
        for sp in var:
            vrow[idx[sp]] = V[(w, sp[0], sp[1])]
        cons.append(LinearConstraint(vrow, lb=sales_ratio * baseline_sales[w], ub=np.inf))
        if objective == "robust":                        # t ≤ uplift_w
            mrow = np.zeros(N)
            for sp in var:
                mrow[idx[sp]] = M[(w, sp[0], sp[1])]
            mrow[T] = -1.0
            cons.append(LinearConstraint(mrow, lb=baseline_margin[w], ub=np.inf))

    integrality = np.ones(N)
    integrality[T] = 0
    bounds = Bounds(np.concatenate([np.zeros(nx), [-1e12]]),
                    np.concatenate([np.ones(nx), [1e12]]))
    res = milp(c=c, constraints=cons, integrality=integrality, bounds=bounds)
    if not res.success or res.x is None:
        return {"feasible": False, "status": "infeasible", "reason": (res.message or "no robust-feasible plan")}

    x = np.round(res.x[:nx]).astype(int)
    selection = {var[i][0]: var[i][1] for i in range(nx) if x[i]}
    per_world = []
    worst = None
    for w in worlds:
        m = sum(M[(w, s, selection[s])] for s in segments)
        v = sum(V[(w, s, selection[s])] for s in segments)
        up = m - baseline_margin[w]
        per_world.append({"world": w, "margin": round(m, 2), "uplift": round(up, 2),
                          "sales": round(v, 2), "baseline_margin": round(baseline_margin[w], 2),
                          "sales_floor": round(sales_ratio * baseline_sales[w], 2),
                          "meets_floor": v >= sales_ratio * baseline_sales[w] - 1e-6})
        worst = up if worst is None else min(worst, up)
    return {"feasible": True, "status": "optimal", "gap": 0.0, "selection": selection,
            "worst_uplift": round(worst, 2), "per_world": per_world,
            "nominal_margin": round(sum(M[(worlds[0], s, selection[s])] for s in segments), 2)}
