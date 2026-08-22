"""Price Optimisation — serves the worked-example optimiser output.

Reads the governed tables written by src/04_models/production/price_optimiser.py
(optimisation_summary, optimisation_curve, optimisation_config). This is a demo
OF optimisation: the app renders the per-segment demand curve + cost line, the
profit-optimal price, the volume/profit frontier, and the governed constraints —
every number traceable to readable code, the wedge against a black-box optimiser.
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from server.config import (fqn, get_catalog, get_schema, get_workspace_host,
                           get_bundle_files_base, get_workspace_client,
                           resolve_job_by_name)
from server.sql import execute_query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/optimisation", tags=["optimisation"])

# The governed optimiser job (name is a stable literal in resources/price_optimiser.yml,
# not workspace-derived, so resolve-by-name is portable across targets).
OPTIMISER_JOB_NAME = "Price optimisation — worked example (new-business profit) (gen2)"
NOTEBOOK_REL = "04_models/production/price_optimiser"   # under {bundle_files_base}
AGENT_ENDPOINT = "pwg2_chat_agent"                       # hosts the rate_change persona


async def _safe(sql: str):
    try:
        return await execute_query(sql)
    except Exception as e:
        logger.warning("optimisation query failed: %s", str(e)[:160])
        return None


# The SQL Statement API returns every value as a string; the UI does maths on
# these (.toFixed, comparisons), so coerce numeric columns to real numbers.
_NUM_COLS = {
    "n_quotes", "elasticity", "market_ref", "cost_line", "current_multiplier",
    "current_conversion", "current_profit_per_quote", "optimal_multiplier",
    "optimal_conversion", "optimal_profit_per_quote", "profit_uplift_per_quote",
    "profit_uplift_pct", "price_multiplier", "expected_conversion", "price",
    "expected_profit_per_quote", "rate_change_cap", "target_loss_ratio",
    "margin_floor",
    # monitoring
    "quotes", "converted", "actual_conversion", "avg_vs_market",
    "expected_conversion", "drift",
}
_BOOL_COLS = {"within_rate_cap"}


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
async def optimisation_summary():
    """Per-segment current-vs-optimal, the price/demand/profit curve for the
    frontier, and the governed objective/constraint config."""
    summary = await _safe(f"""
        SELECT segment, n_quotes, elasticity, market_ref, cost_line,
               current_multiplier, current_conversion, current_profit_per_quote,
               optimal_multiplier, optimal_conversion, optimal_profit_per_quote,
               profit_uplift_per_quote, profit_uplift_pct, binding_constraint
        FROM {fqn('optimisation_summary')} ORDER BY segment
    """)
    curve = await _safe(f"""
        SELECT segment, price_multiplier, expected_conversion,
               price, expected_profit_per_quote, within_rate_cap
        FROM {fqn('optimisation_curve')} ORDER BY segment, price_multiplier
    """)
    config = await _safe(f"""
        SELECT version, objective, rate_change_cap, target_loss_ratio,
               margin_floor, demand_source, cost_source, created_at
        FROM {fqn('optimisation_config')} ORDER BY created_at DESC LIMIT 1
    """)

    if summary is None:
        return {
            "available": False,
            "message": "Optimisation not run yet on this workspace. Run the "
                       "'Price optimisation — worked example' job (bundle key "
                       "price_optimiser).",
            "segments": [], "curve": [], "config": None,
        }

    return {
        "available": True,
        "segments": _coerce(summary) or [],
        "curve": _coerce(curve) or [],
        "config": (_coerce(config) or [None])[0],
    }


@router.get("/assets")
async def assets():
    """Ready deep-links into the platform for every asset the How-it-works tab
    describes — the governed tables, the notebook, the job, the agent endpoint —
    so a viewer can click straight through to the real thing."""
    host = get_workspace_host().rstrip("/")
    cat, sch = get_catalog(), get_schema()
    job_id = resolve_job_by_name(OPTIMISER_JOB_NAME)
    nb = f"{get_bundle_files_base()}/{NOTEBOOK_REL}"
    # The #workspace fragment wants the workspace path WITHOUT the /Workspace prefix.
    nb_ws = nb[len("/Workspace"):] if nb.startswith("/Workspace") else nb
    tbls = ["quotes", "optimisation_summary", "optimisation_curve",
            "optimisation_config", "optimisation_monitoring"]
    return {
        "workspace_host": host,
        "catalog": cat, "schema": sch,
        "tables": {t: f"{host}/explore/data/{cat}/{sch}/{t}" for t in tbls},
        "notebook_url": f"{host}/#workspace{nb_ws}",
        "job_id": job_id or None,
        "job_url": f"{host}/jobs/{job_id}" if job_id else None,
        "agent_endpoint": AGENT_ENDPOINT,
        "agent_url": f"{host}/ml/endpoints/{AGENT_ENDPOINT}",
        "experiment_url": f"{host}/ml/experiments",
    }


class RunRequest(BaseModel):
    rate_change_cap: float | None = None
    target_loss_ratio: float | None = None
    margin_floor: float | None = None


@router.post("/run")
async def run_optimiser(req: RunRequest):
    """Trigger the real price_optimiser job — optionally with new tuning levers —
    and return the run id to poll. This is the 'this is how it runs' beat: a real
    governed job, not a client-side illusion."""
    job_id = resolve_job_by_name(OPTIMISER_JOB_NAME)
    if not job_id:
        return {"ok": False, "error": "optimiser job not found in this workspace"}
    params = {}
    if req.rate_change_cap is not None:   params["rate_change_cap"] = str(req.rate_change_cap)
    if req.target_loss_ratio is not None: params["target_loss_ratio"] = str(req.target_loss_ratio)
    if req.margin_floor is not None:      params["margin_floor"] = str(req.margin_floor)
    try:
        body: dict = {"job_id": int(job_id)}
        if params:
            body["job_parameters"] = params
        resp = get_workspace_client().api_client.do("POST", "/api/2.1/jobs/run-now", body=body)
        return {"ok": True, "run_id": resp.get("run_id"), "job_id": job_id, "params": params}
    except Exception as e:
        logger.warning("optimiser run-now failed: %s", str(e)[:200])
        return {"ok": False, "error": str(e)[:200]}


@router.get("/run/{run_id}")
async def run_status(run_id: int):
    """Poll a triggered run so the UI can show it executing → succeeded."""
    try:
        r = get_workspace_client().api_client.do(
            "GET", "/api/2.1/jobs/runs/get", query={"run_id": run_id})
        state = r.get("state", {}) or {}
        return {
            "run_id": run_id,
            "life_cycle_state": state.get("life_cycle_state"),
            "result_state": state.get("result_state"),
            "state_message": state.get("state_message"),
            "run_page_url": r.get("run_page_url"),
        }
    except Exception as e:
        return {"run_id": run_id, "error": str(e)[:200]}


@router.get("/monitoring")
async def monitoring():
    """Monthly actual conversion vs the demand model's expectation (drift) — the
    'is the model still calibrated?' monitor beat. Moves with the rolling month."""
    rows = await _safe(f"""
        SELECT cast(month as string) AS month, quotes, converted,
               actual_conversion, avg_vs_market, expected_conversion, drift
        FROM {fqn('optimisation_monitoring')} ORDER BY month
    """)
    if rows is None:
        return {"available": False, "months": []}
    return {"available": True, "months": _coerce(rows) or []}
