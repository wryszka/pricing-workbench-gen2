"""Price Optimisation — serves the motor offline-spine (§3–§9, §13).

Reads the governed tables the optimisation notebooks write on personal MOTOR:
  data      → optimisation_quote_response / _renewal_response / _portfolio_snapshot
  elasticity→ conversion_elasticity_motor / retention_elasticity_motor (@champion),
              optimisation_elasticity_curve, + red-team panels
  simulation→ optimisation_scenarios (+ Pareto frontier) / _scenario_segments
  solver    → optimisation_factor_table  (bound by optimisation_constraints/default.yaml)
  monitoring→ optimisation_monitoring / _deviation_dist / _constraint_breaches

Every number is traceable to open code and a versioned constraint file — the wedge
against a black-box optimiser. The approve→deploy gate re-checks the corridor
server-side, so it holds regardless of who (or what) calls it.
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from server.config import (fqn, get_catalog, get_schema, get_workspace_host,
                           get_bundle_files_base, get_workspace_client,
                           get_current_user, resolve_job_by_name)
from server.routes.admin import _require_admin
from server.sql import execute_query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/optimisation", tags=["optimisation"])

# Job names are stable literals in resources/optimisation.yml (not workspace-derived),
# so resolve-by-name is portable across targets.
FULL_JOB_NAME    = "Price optimisation — full build (gen2)"
SOLVER_JOB_NAME  = "Price optimisation — constrained solver (gen2)"
ADVANCE_JOB_NAME = "Price optimisation — advance month (did it work?) (gen2)"
NOTEBOOK_REL    = "04_models/production/optimisation_solver"     # under {bundle_files_base}
CONSTRAINTS_REL = "04_models/production/optimisation_constraints/default.yaml"
AGENT_ENDPOINT  = "pwg2_chat_agent"                             # hosts the rate_change persona
CORRIDOR_PCT    = 15.0                                          # server-side deploy-gate corridor


async def _safe(sql: str, params: dict | None = None):
    try:
        return await execute_query(sql, params)
    except Exception as e:
        logger.warning("optimisation query failed: %s", str(e)[:160])
        return None


# The SQL Statement API returns every value as a string; the UI does maths on
# these, so coerce numeric columns to real numbers.
_NUM_COLS = {
    "policies", "factor", "factor_pct", "conversion_hold", "conversion_opt",
    "gwp_current", "expected_profit_hold", "expected_profit_opt", "profit_uplift",
    "bound_lo", "bound_hi",
    "expected_profit", "expected_volume", "expected_gwp", "expected_loss_ratio",
    "avg_factor", "grid_points", "wallclock_s",
    "price_multiplier", "vs_technical", "conversion_prob", "conversion", "gwp",
    "quotes", "actual_conversion", "expected_conversion", "drift",
    "count", "pct", "breaches", "total", "rate",
    "price_change_pct", "naive_rawprice_conversion", "correct_vs_technical_conversion",
    "month_idx", "true_slope", "recovered_slope", "n_quotes",
    "predicted_conversion", "realized_conversion", "predicted_profit", "realized_profit",
    "profit_delta_pct",
}
_BOOL_COLS = {"within_corridor", "pareto", "outside_corridor"}


def _coerce(rows):
    if not rows:
        return rows
    for r in rows:
        for k, v in list(r.items()):
            if v is None:
                continue
            if k in _NUM_COLS:
                try: r[k] = float(v)
                except (TypeError, ValueError): pass
            elif k in _BOOL_COLS:
                r[k] = str(v).lower() in ("true", "1", "t")
    return rows


@router.get("/summary")
async def summary():
    """The page's first load: the solved factor table, portfolio roll-up, the
    active constraint set, and the monitoring headline."""
    factors = await _safe(f"""
        SELECT constraint_version, segment, policies, factor, factor_pct,
               conversion_hold, conversion_opt, gwp_current,
               expected_profit_hold, expected_profit_opt, profit_uplift,
               bound_lo, bound_hi, binding, within_corridor
        FROM {fqn('optimisation_factor_table')} ORDER BY segment
    """)
    if factors is None:
        return {"available": False,
                "message": "Optimisation not solved yet on this workspace. Run the "
                           "'Price optimisation — full build (gen2)' job "
                           "(bundle key optimisation_full).",
                "factors": [], "rollup": None, "constraint": None, "monitoring_headline": None}
    factors = _coerce(factors) or []
    hold = sum(f.get("expected_profit_hold", 0) or 0 for f in factors)
    opt  = sum(f.get("expected_profit_opt", 0) or 0 for f in factors)
    pol  = sum(f.get("policies", 0) or 0 for f in factors)
    gwp  = sum(f.get("gwp_current", 0) or 0 for f in factors)
    rollup = {
        "segments": len(factors), "policies": pol, "gwp_current": round(gwp, 2),
        "expected_profit_hold": round(hold, 2), "expected_profit_opt": round(opt, 2),
        "profit_uplift": round(opt - hold, 2),
        "profit_uplift_pct": round((opt / hold - 1) * 100, 2) if hold else None,
        "all_within_corridor": all(f.get("within_corridor") for f in factors),
    }
    cver = factors[0].get("constraint_version") if factors else None
    scen_meta = await _safe(f"""
        SELECT any_value(grid_points) AS grid_points, max(wallclock_s) AS wallclock_s,
               count(*) AS candidates, sum(cast(pareto AS int)) AS pareto
        FROM {fqn('optimisation_scenarios')}
    """)
    mon = await _safe(f"""
        SELECT cast(quote_month AS string) AS month, actual_conversion,
               expected_conversion, drift
        FROM {fqn('optimisation_monitoring')} ORDER BY quote_month DESC LIMIT 1
    """)
    return {
        "available": True,
        "factors": factors,
        "rollup": rollup,
        "constraint": {"version": cver},
        "scenario_meta": (_coerce(scen_meta) or [None])[0],
        "monitoring_headline": (_coerce(mon) or [None])[0],
    }


@router.get("/scenarios")
async def scenarios():
    """The efficient frontier — the Pareto-optimal candidates plus the hold
    baseline — and the grid/wall-clock counters ('N is your choice')."""
    frontier = await _safe(f"""
        SELECT scenario_id, expected_profit, expected_volume, expected_gwp,
               expected_loss_ratio, avg_factor, pareto
        FROM {fqn('optimisation_scenarios')}
        WHERE pareto = true OR scenario_id = 'hold'
        ORDER BY expected_volume
    """)
    meta = await _safe(f"""
        SELECT any_value(grid_points) AS grid_points, max(wallclock_s) AS wallclock_s,
               count(*) AS candidates
        FROM {fqn('optimisation_scenarios')}
    """)
    if frontier is None:
        return {"available": False, "frontier": [], "meta": None}
    return {"available": True, "frontier": _coerce(frontier) or [],
            "meta": (_coerce(meta) or [None])[0]}


@router.get("/elasticity")
async def elasticity():
    """Per-segment price→conversion curves (the monotone demand model, surfaced)."""
    rows = await _safe(f"""
        SELECT segment, price_multiplier, vs_technical, conversion_prob, policies
        FROM {fqn('optimisation_elasticity_curve')}
        ORDER BY segment, price_multiplier
    """)
    if rows is None:
        return {"available": False, "curves": []}
    return {"available": True, "curves": _coerce(rows) or []}


@router.get("/monitoring")
async def monitoring():
    """Actual-vs-expected conversion drift over the rolling months, the
    deviation-from-technical distribution, and the corridor/GIPP breach tile."""
    months = await _safe(f"""
        SELECT cast(quote_month AS string) AS month, quotes,
               actual_conversion, expected_conversion, drift
        FROM {fqn('optimisation_monitoring')} ORDER BY quote_month
    """)
    dist = await _safe(f"""
        SELECT vs_technical_band, count, pct, outside_corridor
        FROM {fqn('optimisation_deviation_dist')}
    """)
    breaches = await _safe(f"""
        SELECT check, breaches, total, rate, note
        FROM {fqn('optimisation_constraint_breaches')}
    """)
    if months is None:
        return {"available": False, "months": [], "deviation": [], "breaches": []}
    return {"available": True,
            "months": _coerce(months) or [],
            "deviation": _coerce(dist) or [],
            "breaches": _coerce(breaches) or []}


@router.get("/redteam")
async def redteam():
    """The two validity panels: why raw price gives the wrong elasticity
    (endogeneity), and that the pipeline recovers the injected parameters."""
    endo = await _safe(f"""
        SELECT price_change_pct, naive_rawprice_conversion, correct_vs_technical_conversion
        FROM {fqn('optimisation_redteam_endogeneity')} ORDER BY price_change_pct
    """)
    recov = await _safe(f"""
        SELECT month_idx, true_slope, recovered_slope, n_quotes
        FROM {fqn('optimisation_param_recovery')} ORDER BY month_idx
    """)
    return {"available": endo is not None,
            "endogeneity": _coerce(endo) or [],
            "param_recovery": _coerce(recov) or []}


@router.get("/constraints")
async def constraints():
    """The versioned constraint YAML, read live from the synced bundle file — the
    'open the pricing policy in the room' beat. Its git history is the audit trail."""
    path = f"{get_bundle_files_base()}/{CONSTRAINTS_REL}"
    content, source = None, path
    try:
        wc = get_workspace_client()
        raw = wc.workspace.download(path).read()
        content = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
    except Exception as e:
        logger.warning("constraint yaml read failed (%s): %s", path, str(e)[:160])
    return {"available": content is not None, "path": source, "yaml": content}


@router.get("/assets")
async def assets():
    """Deep-links into the platform for every asset the How-it-works tab names."""
    host = get_workspace_host().rstrip("/")
    cat, sch = get_catalog(), get_schema()
    job_id = resolve_job_by_name(FULL_JOB_NAME)
    nb = f"{get_bundle_files_base()}/{NOTEBOOK_REL}"
    nb_ws = nb[len("/Workspace"):] if nb.startswith("/Workspace") else nb
    tbls = ["optimisation_quote_response", "optimisation_renewal_response",
            "optimisation_portfolio_snapshot", "optimisation_elasticity_curve",
            "optimisation_scenarios", "optimisation_factor_table",
            "optimisation_monitoring"]
    models = ["conversion_elasticity_motor", "retention_elasticity_motor"]
    return {
        "workspace_host": host, "catalog": cat, "schema": sch,
        "tables": {t: f"{host}/explore/data/{cat}/{sch}/{t}" for t in tbls},
        "models": {m: f"{host}/explore/data/models/{cat}/{sch}/{m}" for m in models},
        "notebook_url": f"{host}/#workspace{nb_ws}",
        "job_id": job_id or None,
        "job_url": f"{host}/jobs/{job_id}" if job_id else None,
        "agent_endpoint": AGENT_ENDPOINT,
        "agent_url": f"{host}/ml/endpoints/{AGENT_ENDPOINT}",
        "experiment_url": f"{host}/ml/experiments",
    }


class RunRequest(BaseModel):
    grid_points: int | None = None
    objective: str | None = None
    full: bool = True     # True = whole spine (optimisation_full); False = solver only


@router.post("/run")
async def run(req: RunRequest):
    """Trigger the real governed job — the whole offline spine, or just the solver
    when only constraints/objective changed. 'This is how it runs' — a real DAG,
    not a client-side illusion."""
    name = FULL_JOB_NAME if req.full else SOLVER_JOB_NAME
    job_id = resolve_job_by_name(name)
    if not job_id:
        return {"ok": False, "error": f"job '{name}' not found in this workspace"}
    params = {}
    if req.grid_points is not None: params["grid_points"] = str(req.grid_points)
    if req.objective:               params["objective"] = req.objective
    try:
        body: dict = {"job_id": int(job_id)}
        if params:
            body["job_parameters"] = params
        resp = get_workspace_client().api_client.do("POST", "/api/2.1/jobs/run-now", body=body)
        return {"ok": True, "run_id": resp.get("run_id"), "job_id": job_id, "params": params}
    except Exception as e:
        logger.warning("optimisation run-now failed: %s", str(e)[:200])
        return {"ok": False, "error": str(e)[:200]}


@router.post("/advance")
async def advance_month():
    """Closed-loop 'did it work?' — roll the synthetic timeline forward one month
    under the DEPLOYED prices and realize outcomes. Triggers the governed
    advance-month job; poll with /run/{id} then read /advance/result."""
    job_id = resolve_job_by_name(ADVANCE_JOB_NAME)
    if not job_id:
        return {"ok": False, "error": f"job '{ADVANCE_JOB_NAME}' not found"}
    try:
        resp = get_workspace_client().api_client.do(
            "POST", "/api/2.1/jobs/run-now", body={"job_id": int(job_id)})
        return {"ok": True, "run_id": resp.get("run_id"), "job_id": job_id}
    except Exception as e:
        logger.warning("advance-month run-now failed: %s", str(e)[:200])
        return {"ok": False, "error": str(e)[:200]}


@router.get("/advance/result")
async def advance_result():
    """Per-segment predicted-vs-realized for the most recent advanced month."""
    rows = await _safe(f"""
        SELECT cast(advanced_month AS string) AS advanced_month, segment, policies, factor,
               predicted_conversion, realized_conversion,
               predicted_profit, realized_profit, profit_delta_pct
        FROM {fqn('optimisation_advance_result')} ORDER BY segment
    """)
    if rows is None:
        return {"available": False, "segments": [], "rollup": None}
    rows = _coerce(rows)
    pp = sum(r.get("predicted_profit", 0) or 0 for r in rows)
    rp = sum(r.get("realized_profit", 0) or 0 for r in rows)
    return {"available": True, "segments": rows,
            "rollup": {"predicted_profit": round(pp, 2), "realized_profit": round(rp, 2),
                       "delta_pct": round((rp / pp - 1) * 100, 2) if pp else None,
                       "advanced_month": rows[0].get("advanced_month") if rows else None}}


@router.get("/run/{run_id}")
async def run_status(run_id: int):
    try:
        r = get_workspace_client().api_client.do(
            "GET", "/api/2.1/jobs/runs/get", query={"run_id": run_id})
        state = r.get("state", {}) or {}
        return {"run_id": run_id, "life_cycle_state": state.get("life_cycle_state"),
                "result_state": state.get("result_state"),
                "state_message": state.get("state_message"),
                "run_page_url": r.get("run_page_url")}
    except Exception as e:
        return {"run_id": run_id, "error": str(e)[:200]}


class DeployRequest(BaseModel):
    approver: str | None = None
    note: str | None = None


@router.post("/deploy")
async def deploy(req: DeployRequest):
    """Approve → deploy the solved factor table (the HITL gate). Two enforcements,
    both server-side so no prompt/agent can bypass them: (1) RBAC — the caller must
    be in ADMIN_USERS (the approver role); (2) the ±corridor is re-checked against
    the live factor table. On approval we stamp optimisation_deployment + an
    immutable audit_log row, using bound parameters (injection-proof)."""
    _require_admin("optimisation-deploy")   # RBAC: approver must be in ADMIN_USERS
    rows = await _safe(f"""
        SELECT segment, factor, factor_pct, within_corridor, constraint_version
        FROM {fqn('optimisation_factor_table')}
    """)
    if not rows:
        return {"ok": False, "error": "no factor table to deploy — solve first"}
    rows = _coerce(rows)
    lo, hi = 1 - CORRIDOR_PCT / 100, 1 + CORRIDOR_PCT / 100
    breaches = [r["segment"] for r in rows
                if not (lo - 1e-6 <= (r.get("factor") or 1.0) <= hi + 1e-6)]
    if breaches:
        return {"ok": False, "gated": True,
                "error": f"deploy blocked: {len(breaches)} segment(s) outside the "
                         f"±{CORRIDOR_PCT:.0f}% corridor: {', '.join(breaches[:5])}"}
    cver = str(rows[0].get("constraint_version") or "v1")
    approver = get_current_user() or req.approver or "app_user"
    note = req.note or "approved in app"
    n = len(rows)
    # Stamp the deployment ledger + the immutable audit log (append — the history of
    # deployments IS the record) with BOUND PARAMETERS — user-supplied values can
    # never alter the statement. The table is pre-created by the solver notebook, so
    # the app SP only needs INSERT (MODIFY), never CREATE. Surface write failures.
    p = {"cver": cver, "approver": approver, "note": note}
    dep_ok = await _safe(f"""
        INSERT INTO {fqn('optimisation_deployment')}
        SELECT uuid(), :cver, {n}, :approver, :note, current_timestamp()
    """, p)
    aud_ok = await _safe(f"""
        INSERT INTO {fqn('audit_log')} (event_id, event_type, entity_type, entity_id,
               entity_version, user_id, timestamp, details, source)
        SELECT uuid(), 'optimisation_deploy_approved', 'factor_table', :cver, :cver,
               :approver, current_timestamp(),
               to_json(named_struct('segments', {n}, 'note', :note)), 'optimisation_app'
    """, p)
    if dep_ok is None or aud_ok is None:
        return {"ok": False, "constraint_version": cver, "segments": n,
                "error": "corridor OK but writeback failed — check app-SP MODIFY grants "
                         "on optimisation_deployment / audit_log (run grant_app_sp)."}
    return {"ok": True, "constraint_version": cver, "segments": n,
            "approver": approver, "message": "Factor table approved and deployed (audited)."}
