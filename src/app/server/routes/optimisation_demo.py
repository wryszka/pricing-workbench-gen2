"""Chapter 1 teaching demo — the narrow, honest optimisation flow.

Two connected parts, one shared calculation module (`server.optimisation_demo.core`):
  • `/example`  — the worked example (arithmetic computed in-process by `core`,
                  clearly labelled a WORKED EXAMPLE — never a Databricks run).
  • `/run`      — start the real Databricks job for the SAME example + requirement.
  • `/run/{id}` — live job status + the saved result, read back by the EXACT
                  application run id (never a mutable "latest").

The frontend never re-implements the numbers: the explanation reads `/example`,
the live result reads `/run/{id}`.
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from server.config import (get_catalog, get_schema, get_workspace_client,
                           resolve_job_by_name, fqn)
from server.sql import execute_query
from server.optimisation_demo.core import load_example, optimise, validate_requirement

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/optimisation-demo", tags=["optimisation-demo"])

JOB_NAME = "Optimisation demo — run (gen2)"
CH2_RUN_JOB = "Optimisation demo — Chapter 2 run (gen2)"
GRANDMA_SEGMENT = "70+ · grp≥30"
EXAMPLE_ID = "grandma_bmw_v1"
_APP_RUN_ID = re.compile(r"^[a-f0-9]{32}$")


@router.get("/example")
async def example():
    """The worked example — the exact teaching numbers, straight from `core`.

    Marked `state: worked_example` so the UI can never pass it off as a live run.
    Includes both classroom runs: A (no requirement) and B (≥ 830 expected)."""
    ex = load_example()
    keep = ("example_id", "example_version", "segment_label", "segment_mnemonic",
            "opportunities", "modelled_variable_cost_per_sale", "baseline_price",
            "objective", "assumptions")
    return {
        "state": "worked_example",
        "example": {k: ex.get(k) for k in keep},
        "run_a": optimise(ex, None),
        "run_b": optimise(ex, 830),
    }


class RunRequest(BaseModel):
    min_expected_customers: Optional[float] = None


@router.post("/run")
async def run(req: RunRequest):
    """Start the real Databricks job for this example + requirement.

    Server-side validation of the requirement (never trust the client). Returns a
    fresh application run id + the Databricks job run id; the job computes and
    saves results keyed by the application run id."""
    try:
        validate_requirement(req.min_expected_customers)
    except ValueError as e:
        raise HTTPException(400, str(e))

    job_id = resolve_job_by_name(JOB_NAME)
    if not job_id:
        raise HTTPException(503, f"Job '{JOB_NAME}' not found — deploy the bundle first.")

    app_run_id = uuid.uuid4().hex
    params = {
        "catalog_name": get_catalog(),
        "schema_name": get_schema(),
        "example_id": EXAMPLE_ID,
        "app_run_id": app_run_id,
        "min_expected_customers": ("" if req.min_expected_customers is None
                                   else str(req.min_expected_customers)),
    }
    try:
        r = get_workspace_client().api_client.do(
            "POST", "/api/2.1/jobs/run-now",
            body={"job_id": int(job_id), "job_parameters": params})
    except Exception as e:
        raise HTTPException(502, f"Could not start the Databricks job: {str(e)[:200]}")

    return {"app_run_id": app_run_id, "job_run_id": r.get("run_id"),
            "min_expected_customers": req.min_expected_customers, "status": "running"}


async def _read_result(app_run_id: str) -> Optional[dict]:
    """Read the saved run + candidate rows for this exact application run id.

    Returns None if the tables/rows are not there yet (job still running, or
    first run before the tables exist). Never falls back to another run."""
    try:
        run_row = await execute_query(
            f"SELECT * FROM {fqn('optimisation_demo_runs')} WHERE run_id = :rid", {"rid": app_run_id})
    except Exception as e:
        logger.info("demo run read (not ready): %s", str(e)[:120])
        return None
    if not run_row:
        return None
    try:
        cands = await execute_query(
            f"SELECT * FROM {fqn('optimisation_demo_candidate_results')} "
            f"WHERE run_id = :rid ORDER BY candidate_price", {"rid": app_run_id})
    except Exception:
        cands = []
    return {"run": run_row[0], "candidates": cands}


@router.get("/run/{app_run_id}")
async def run_status(app_run_id: str, job_run_id: int = Query(...)):
    """Live job status + the saved result for this exact application run id."""
    if not _APP_RUN_ID.match(app_run_id):
        raise HTTPException(400, "invalid application run id")

    life = res = page = None
    try:
        job = get_workspace_client().api_client.do(
            "GET", "/api/2.1/jobs/runs/get", query={"run_id": int(job_run_id)})
        st = job.get("state") or {}
        life, res, page = st.get("life_cycle_state"), st.get("result_state"), job.get("run_page_url")
    except Exception as e:
        logger.warning("demo runs/get failed: %s", str(e)[:120])

    result = await _read_result(app_run_id)

    # A failed/incomplete job must never look like a successful new result: only
    # SUCCESS *with* a saved row for this id counts as succeeded.
    terminal = life in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR")
    if terminal and res == "SUCCESS":
        status = "succeeded" if result else "running"  # tiny write lag → still running
    elif terminal:
        status = "failed"
    else:
        status = "running"

    return {"app_run_id": app_run_id, "job_run_id": job_run_id,
            "life_cycle_state": life, "result_state": res, "run_page_url": page,
            "status": status, "result": result}


# --------------------------------------------------------------------------- #
# Chapter 2 — a portfolio (learned demand, individual costs, coupled decisions)
# --------------------------------------------------------------------------- #
async def _safe_q(sql: str, params: dict | None = None):
    try:
        return await execute_query(sql, params)
    except Exception as e:
        logger.info("ch2 read (not ready): %s", str(e)[:120])
        return None


@router.get("/ch2/prepare-status")
async def ch2_prepare_status():
    """Model manifest + validation metrics + whether the portfolio summary is ready."""
    man = await _safe_q(f"SELECT model_version, generator_version, passes, failures, "
                        f"cast(future_delta_version as string) future_delta_version, "
                        f"cast(trained_at as string) trained_at FROM {fqn('optimisation_demo_ch2_model_manifest')} "
                        f"ORDER BY trained_at DESC LIMIT 1")
    if not man:
        return {"prepared": False}
    metrics = await _safe_q(f"SELECT metric, value FROM {fqn('optimisation_demo_ch2_validation')} "
                            f"WHERE model_version = :mv", {"mv": man[0]["model_version"]}) or []
    summ = await _safe_q(f"SELECT count(*) n FROM {fqn('optimisation_demo_ch2_portfolio_summary')}")
    return {"prepared": True, "manifest": man[0],
            "validation": {m["metric"]: m["value"] for m in metrics},
            "portfolio_ready": bool(summ and summ[0].get("n"))}


@router.get("/ch2/portfolio")
async def ch2_portfolio():
    """Per-segment baseline portfolio (opportunities, baseline sales/premium/margin, cost)
    + a representative grandma-segment opportunity. Read model-free from the summary table."""
    rows = await _safe_q(f"SELECT segment, opportunities, round(avg_baseline_price,2) avg_baseline_price, "
                         f"round(avg_expected_claims,2) avg_expected_claims, round(avg_cost,2) avg_cost, "
                         f"round(baseline_sales,1) baseline_sales, round(baseline_premium,0) baseline_premium, "
                         f"round(baseline_margin,0) baseline_margin FROM {fqn('optimisation_demo_ch2_portfolio_summary')} "
                         f"ORDER BY segment")
    if not rows:
        return {"ready": False}
    totals = {
        "opportunities": int(sum(r["opportunities"] for r in rows)),
        "baseline_sales": round(sum(r["baseline_sales"] for r in rows), 1),
        "baseline_premium": round(sum(r["baseline_premium"] for r in rows), 0),
        "baseline_margin": round(sum(r["baseline_margin"] for r in rows), 0),
    }
    rep = await _safe_q(f"SELECT opportunity_id, driver_age, vehicle_group, round(baseline_price,2) baseline_price, "
                        f"round(market_premium,2) market_premium, round(expected_claims,2) expected_claims, "
                        f"round(per_sale_expenses,2) per_sale_expenses, commission_rate "
                        f"FROM {fqn('optimisation_demo_ch2_future')} WHERE segment = :seg LIMIT 1",
                        {"seg": GRANDMA_SEGMENT})
    return {"ready": True, "segments": rows, "totals": totals,
            "grandma_segment": GRANDMA_SEGMENT,
            "representative_opportunity": (rep[0] if rep else None)}


class Ch2RunRequest(BaseModel):
    min_portfolio_sales_ratio: Optional[float] = None   # None = margin-first; e.g. 0.98


@router.post("/ch2/run")
async def ch2_run(req: Ch2RunRequest):
    r = req.min_portfolio_sales_ratio
    if r is not None and (r < 0 or r > 2):
        raise HTTPException(400, "min_portfolio_sales_ratio must be between 0 and 2")
    job_id = resolve_job_by_name(CH2_RUN_JOB)
    if not job_id:
        raise HTTPException(503, f"Job '{CH2_RUN_JOB}' not found — deploy the bundle first.")
    app_run_id = uuid.uuid4().hex
    params = {"catalog_name": get_catalog(), "schema_name": get_schema(),
              "app_run_id": app_run_id,
              "min_portfolio_sales_ratio": ("" if r is None else str(r))}
    try:
        resp = get_workspace_client().api_client.do(
            "POST", "/api/2.1/jobs/run-now",
            body={"job_id": int(job_id), "job_parameters": params})
    except Exception as e:
        raise HTTPException(502, f"Could not start the Chapter 2 job: {str(e)[:200]}")
    return {"app_run_id": app_run_id, "job_run_id": resp.get("run_id"),
            "min_portfolio_sales_ratio": r, "status": "running"}


@router.get("/ch2/run/{app_run_id}")
async def ch2_run_status(app_run_id: str, job_run_id: int = Query(...)):
    if not _APP_RUN_ID.match(app_run_id):
        raise HTTPException(400, "invalid application run id")
    life = res = page = None
    try:
        job = get_workspace_client().api_client.do(
            "GET", "/api/2.1/jobs/runs/get", query={"run_id": int(job_run_id)})
        st = job.get("state") or {}
        life, res, page = st.get("life_cycle_state"), st.get("result_state"), job.get("run_page_url")
    except Exception as e:
        logger.warning("ch2 runs/get failed: %s", str(e)[:120])

    run_row = await _safe_q(f"SELECT run_id, model_version, objective, min_portfolio_sales_ratio, status, "
                            f"round(baseline_sales,1) baseline_sales, round(baseline_margin,0) baseline_margin, "
                            f"round(total_sales,1) total_sales, round(total_margin,0) total_margin, "
                            f"cast(future_delta_version as string) future_delta_version "
                            f"FROM {fqn('optimisation_demo_ch2_runs')} WHERE run_id = :rid", {"rid": app_run_id})
    result = None
    if run_row:
        sel = await _safe_q(f"SELECT segment, factor, round(expected_sales,1) expected_sales, "
                            f"round(expected_margin,0) expected_margin FROM {fqn('optimisation_demo_ch2_candidate_scores')} "
                            f"WHERE run_id = :rid AND selected ORDER BY segment", {"rid": app_run_id})
        result = {"run": run_row[0], "selected": sel or []}

    terminal = life in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR")
    if terminal and res == "SUCCESS":
        status = "succeeded" if result else "running"
    elif terminal:
        status = "failed"
    else:
        status = "running"
    return {"app_run_id": app_run_id, "job_run_id": job_run_id, "life_cycle_state": life,
            "result_state": res, "run_page_url": page, "status": status, "result": result}
