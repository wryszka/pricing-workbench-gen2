"""Chapter 2 — the portfolio decision as a finite-candidate MILP (pure; scipy only).

Choose one candidate price per segment to maximise total expected margin, subject
to (optionally) a floor on total expected sales:

    maximise   Σ_s,k  M_sk · x_sk
    subject to Σ_k x_sk = 1                     for every segment s
               Σ_s,k V_sk · x_sk ≥ sales_floor  (optional)
               x_sk ∈ {0,1}

Solved exactly over the candidate grid with SciPy `milp` (HiGHS). The **actual**
solver status and optimality gap are reported (never a manufactured ``gap=0``), so we
distinguish optimal, feasible-but-time-limited, infeasible and failed.

Movement toward the baseline price is handled by a **second solve** (WP1#5), NOT by a
penalty folded into the primary objective: the first solve maximises expected margin;
the second minimises total price movement subject to keeping total margin within a
*declared monetary tolerance* of the primary optimum. This never distorts the primary
objective and never invents ties. Both solves' evidence and the tolerance are returned.
Invalid candidates (out of bounds) are excluded before solving.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

# Default declared tolerance (£ of total expected margin) within which a
# movement-minimising plan may be preferred over the raw margin optimum. 0.0 = keep
# the exact primary optimum; movement only ever breaks genuine ties.
_MOVEMENT_TOLERANCE = 0.0

# scipy.optimize.milp status → our vocabulary.
_STATUS = {0: "optimal", 1: "time_limited", 2: "infeasible", 3: "unbounded", 4: "failed"}


def _extract(x: np.ndarray, var, coeffs, baseline_price):
    selection: dict[str, float] = {}
    per_segment = []
    total_margin = total_sales = 0.0
    for i, taken in enumerate(np.round(x).astype(int)):
        if taken:
            s, p = var[i]
            m = coeffs[(s, p)]["expected_margin"]
            v = coeffs[(s, p)]["expected_sales"]
            selection[s] = p
            total_margin += m
            total_sales += v
            per_segment.append({"segment": s, "price": p, "expected_margin": m,
                                 "expected_sales": v, "price_delta": p - baseline_price[s]})
    return selection, per_segment, total_margin, total_sales


def solve_portfolio(
    segments: list[str],
    candidates: dict[str, list[float]],
    coeffs: dict[tuple[str, float], dict[str, float]],
    baseline_price: dict[str, float],
    min_portfolio_sales: Optional[float] = None,
    allowed: Optional[set[tuple[str, float]]] = None,
    movement_tolerance: float = _MOVEMENT_TOLERANCE,
) -> dict[str, Any]:
    """Return the best per-segment plan with honest solver evidence (or infeasible).

    `candidates[s]` is the candidate prices for segment s; `coeffs[(s,p)]` carries
    `expected_margin` (M) and `expected_sales` (V). `allowed` optionally restricts
    eligible (segment, price) pairs. `movement_tolerance` is the £-margin band within
    which the second solve may trade margin for a smaller move.
    """
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

    base_constraints = []
    for s in segments:                       # exactly one candidate per segment
        row = np.zeros(nvar)
        for p in candidates[s]:
            if (s, float(p)) in idx:
                row[idx[(s, float(p))]] = 1.0
        base_constraints.append(LinearConstraint(row, lb=1, ub=1))
    if min_portfolio_sales is not None:      # portfolio sales floor
        base_constraints.append(LinearConstraint(V, lb=float(min_portfolio_sales), ub=np.inf))

    # --- Primary solve: maximise expected margin (no movement term). --- #
    res = milp(c=-M, constraints=base_constraints, integrality=np.ones(nvar), bounds=Bounds(0, 1))
    status = _STATUS.get(int(getattr(res, "status", 4)), "failed")
    if res.x is None or status in ("infeasible", "unbounded", "failed"):
        return {"status": status if status != "optimal" else "infeasible", "feasible": False,
                "reason": (res.message or "no feasible plan meeting the requirement")}

    _, _, primary_margin, _ = _extract(res.x, var, coeffs, baseline_price)
    # Real optimality gap from HiGHS (absolute, relative to the dual bound). Never faked.
    gap = None
    try:
        db = getattr(res, "mip_dual_bound", None)
        rel = getattr(res, "mip_gap", None)
        gap = float(abs(db - res.fun)) if db is not None else (float(rel) if rel is not None else None)
    except Exception:
        gap = None

    # --- Movement solve: minimise Σ deviation s.t. margin ≥ primary − tolerance. --- #
    move_constraints = list(base_constraints)
    move_constraints.append(LinearConstraint(M, lb=float(primary_margin) - float(movement_tolerance), ub=np.inf))
    res2 = milp(c=dev, constraints=move_constraints, integrality=np.ones(nvar), bounds=Bounds(0, 1))
    used_movement = res2.x is not None and int(getattr(res2, "status", 4)) in (0, 1)
    x_final = res2.x if used_movement else res.x

    selection, per_segment, total_margin, total_sales = _extract(x_final, var, coeffs, baseline_price)

    # --- WP1#4: independent full-precision feasibility recompute of the extracted plan. --- #
    recomputed_feasible = (len(selection) == len(segments))
    floor_ok = (min_portfolio_sales is None) or (total_sales >= float(min_portfolio_sales) - 1e-6)
    if not (recomputed_feasible and floor_ok):
        return {"status": "recompute_failed", "feasible": False,
                "reason": f"extracted plan failed independent recompute (coverage={recomputed_feasible}, floor_ok={floor_ok})",
                "solver_status": status}

    return {
        "status": status,                    # ACTUAL solver status (optimal / time_limited)
        "feasible": True,
        "gap": gap,                           # ACTUAL gap (may be ~0 for optimal, never forced)
        "note": ("proven optimal on the configured grid" if status == "optimal"
                 else "best found within the solver time limit (not proven optimal)"),
        "selection": selection,
        "per_segment": per_segment,
        "total_expected_margin": round(total_margin, 2),
        "total_expected_sales": round(total_sales, 6),
        "min_portfolio_sales": min_portfolio_sales,
        # Two-solve evidence (WP1#5).
        "primary_total_margin": round(float(primary_margin), 2),
        "movement_tolerance": float(movement_tolerance),
        "movement_solve_used": bool(used_movement),
        "margin_sacrificed_for_movement": round(float(primary_margin) - float(total_margin), 4),
    }
