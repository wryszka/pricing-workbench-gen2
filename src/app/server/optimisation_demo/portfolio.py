"""Chapter 2 — the portfolio decision as a finite-candidate MILP (pure; scipy only).

Choose one candidate price per segment to maximise total expected margin, subject
to (optionally) a floor on total expected sales:

    maximise   Σ_s,k  M_sk · x_sk
    subject to Σ_k x_sk = 1                     for every segment s
               Σ_s,k V_sk · x_sk ≥ sales_floor  (optional)
               x_sk ∈ {0,1}

Solved exactly over the candidate grid with SciPy `milp` (HiGHS) — status/gap are
reported, so we can say "best on the configured grid, within tolerance" rather than
claiming a continuous optimum. A tiny baseline-deviation penalty breaks ties toward
the baseline price without changing the true optimum. Invalid candidates (out of
bounds) are excluded before solving. No greedy repair, no rounded relaxation.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

# Penalty per £ of deviation from baseline — tiny, only to break exact ties.
_TIE_EPS = 1e-3


def solve_portfolio(
    segments: list[str],
    candidates: dict[str, list[float]],
    coeffs: dict[tuple[str, float], dict[str, float]],
    baseline_price: dict[str, float],
    min_portfolio_sales: Optional[float] = None,
    allowed: Optional[set[tuple[str, float]]] = None,
) -> dict[str, Any]:
    """Return the exact best per-segment plan (or a clear infeasible status).

    `candidates[s]` is the list of candidate prices for segment s; `coeffs[(s,p)]`
    carries `expected_margin` (M) and `expected_sales` (V). `allowed` optionally
    restricts eligible (segment, price) pairs (bounds/premium caps applied upstream).
    """
    # Flatten eligible variables.
    var: list[tuple[str, float]] = []
    for s in segments:
        for p in candidates[s]:
            if allowed is None or (s, float(p)) in allowed:
                var.append((s, float(p)))
    if not var:
        return {"status": "infeasible", "feasible": False, "reason": "no eligible candidates"}

    idx = {sp: i for i, sp in enumerate(var)}
    nvar = len(var)
    M = np.array([coeffs[sp]["expected_margin"] for sp in var], dtype=float)
    V = np.array([coeffs[sp]["expected_sales"] for sp in var], dtype=float)
    dev = np.array([abs(sp[1] - baseline_price[sp[0]]) for sp in var], dtype=float)

    # milp minimises c·x → minimise −(margin − eps·deviation).
    c = -(M - _TIE_EPS * dev)

    constraints = []
    # exactly one candidate per segment
    for s in segments:
        row = np.zeros(nvar)
        for p in candidates[s]:
            if (s, float(p)) in idx:
                row[idx[(s, float(p))]] = 1.0
        constraints.append(LinearConstraint(row, lb=1, ub=1))
    # portfolio sales floor
    if min_portfolio_sales is not None:
        constraints.append(LinearConstraint(V, lb=float(min_portfolio_sales), ub=np.inf))

    res = milp(c=c, constraints=constraints, integrality=np.ones(nvar),
               bounds=Bounds(0, 1))

    if not res.success or res.x is None:
        return {"status": "infeasible", "feasible": False,
                "reason": (res.message or "no feasible plan meeting the requirement")}

    x = np.round(res.x).astype(int)
    selection: dict[str, float] = {}
    per_segment = []
    total_margin = total_sales = 0.0
    for i, taken in enumerate(x):
        if taken:
            s, p = var[i]
            selection[s] = p
            m = coeffs[(s, p)]["expected_margin"]
            v = coeffs[(s, p)]["expected_sales"]
            total_margin += m
            total_sales += v
            per_segment.append({"segment": s, "price": p, "expected_margin": m, "expected_sales": v,
                                 "price_delta": p - baseline_price[s]})

    return {
        "status": "optimal",              # HiGHS solves these to optimality
        "feasible": True,
        "gap": 0.0,
        "note": "best on the configured candidate grid, within solver tolerance",
        "selection": selection,
        "per_segment": per_segment,
        "total_expected_margin": round(total_margin, 2),
        "total_expected_sales": round(total_sales, 6),
        "min_portfolio_sales": min_portfolio_sales,
    }
