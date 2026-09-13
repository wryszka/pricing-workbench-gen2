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

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from server.config import (get_catalog, get_schema, get_workspace_client,
                           resolve_job_by_name, fqn, get_current_user,
                           get_workspace_host, get_warehouse_id)
from server.sql import execute_query
from server.optimisation_demo import coerce
from server.optimisation_demo import governance as govern
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
    # NB: the SQL statement API returns values as strings — cast before arithmetic.
    totals = {
        "opportunities": int(sum(float(r["opportunities"]) for r in rows)),
        "baseline_sales": round(sum(float(r["baseline_sales"]) for r in rows), 1),
        "baseline_premium": round(sum(float(r["baseline_premium"]) for r in rows), 0),
        "baseline_margin": round(sum(float(r["baseline_margin"]) for r in rows), 0),
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


# --------------------------------------------------------------------------- #
# Chapter 2 governance — approve/release via OBO (real per-user gate)
# --------------------------------------------------------------------------- #
class Ch2ApproveRequest(BaseModel):
    app_run_id: str
    note: Optional[str] = None


@router.post("/ch2/approve")
async def ch2_approve(req: Ch2ApproveRequest, request: Request):
    """Approve + release a Chapter 2 plan — **OBO-only, fail-closed** (WP2).

    The governed UC procedure is CALLed **as the logged-in user** over on-behalf-of
    auth; Unity Catalog enforces the approver-only EXECUTE grant and the procedure
    records `session_user()` as the approver. There is NO service-principal fallback:
    a missing/invalid OBO token, a missing scope, a non-JSON edge rejection, a
    permission denial or any unexpected response leaves the plan UN-approved and
    surfaces an actionable message — none of these ever becomes an approval.

    Before the CALL the plan is independently rebuilt + revalidated from the RAW stored
    scores against the segments the run was meant to cover (from the frozen portfolio
    manifest, not the candidate rows), and the app-recomputed hash must equal the
    trusted hash the validated job wrote. The procedure re-checks the hash server-side,
    so the app-side check is defence-in-depth, not the gate."""
    user_token = request.headers.get("x-forwarded-access-token")
    if not user_token:
        raise HTTPException(403, "Per-user authorization (OBO) is required to approve, and no "
                                 "on-behalf-of token was present. Open the app in a fresh session "
                                 "and accept the authorization prompt (the `sql` scope), then sign "
                                 "in as an approver. Approval is intentionally unavailable without it.")
    if not _APP_RUN_ID.match(req.app_run_id):
        raise HTTPException(400, "invalid application run id")

    run_rows = await _safe_q(
        f"SELECT status, model_eligible, plan_hash, min_portfolio_sales_ratio, baseline_sales "
        f"FROM {fqn('optimisation_demo_ch2_runs')} WHERE run_id = :rid", {"rid": req.app_run_id})
    if not run_rows:
        raise HTTPException(404, "run not found")
    run = run_rows[0]
    if coerce.as_str(run.get("status"), field="status") != "complete":
        raise HTTPException(400, f"run not approvable (status {run.get('status')})")
    if not coerce.opt_bool(run.get("model_eligible"), field="model_eligible"):
        raise HTTPException(400, "run model is not eligible (failed validation, or legacy/unverified) — cannot approve")
    stored_hash = run.get("plan_hash")
    if not stored_hash:
        raise HTTPException(400, "run has no trusted plan hash (legacy/unverified) — re-run under the governed job")

    # Expected segments come from the frozen portfolio manifest, NOT the rows we check.
    manifest_segs = await _safe_q(
        f"SELECT segment FROM {fqn('optimisation_demo_ch2_portfolio_summary')} ORDER BY segment")
    expected_segments = [coerce.as_str(r["segment"], field="segment") for r in (manifest_segs or [])]
    if not expected_segments:
        raise HTTPException(409, "portfolio manifest not available — cannot establish expected segments")

    scores = await _safe_q(
        f"SELECT segment, factor, expected_sales, expected_margin, selected "
        f"FROM {fqn('optimisation_demo_ch2_candidate_scores')} WHERE run_id = :rid",
        {"rid": req.app_run_id}) or []
    ratio = coerce.opt_float(run.get("min_portfolio_sales_ratio"), field="min_portfolio_sales_ratio")
    baseline_sales = coerce.as_float(run.get("baseline_sales"), field="baseline_sales")
    floor = None if ratio is None else ratio * baseline_sales

    # Strict rebuild: rejects duplicate keys / duplicate selections / bad booleans /
    # segment-coverage mismatch BEFORE hashing.
    check = govern.build_and_validate_from_rows(scores, expected_segments, floor)
    if not check["ok"]:
        raise HTTPException(400, "plan failed recompute: " + "; ".join(check["failures"]))
    if check["plan_hash"] != stored_hash:
        logger.warning("ch2 approve: recomputed hash != stored trusted hash (run %s)", req.app_run_id)
        raise HTTPException(409, "recomputed plan hash does not match the validated run — refusing to approve")

    def _esc(v: str) -> str:
        return str(v).replace("'", "''")

    # OBO CALL — approver identity is session_user() inside the procedure; we pass only
    # the run id, the (server-re-verified) hash and an optional note. Any failure is
    # fail-closed.
    import time as _t
    import requests
    stmt = (f"CALL {fqn('optimisation_demo_ch2_approve')}("
            f"'{req.app_run_id}', '{stored_hash}', '{_esc(req.note or 'approved via OBO')}')")
    host = get_workspace_host().rstrip("/")
    headers = {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}
    try:
        r = requests.post(f"{host}/api/2.0/sql/statements", headers=headers, timeout=45,
                          json={"warehouse_id": get_warehouse_id(), "statement": stmt, "wait_timeout": "30s"})
    except Exception as e:
        logger.warning("ch2 approve OBO transport error: %s", str(e)[:200])
        raise HTTPException(502, f"Approval could not reach Unity Catalog over OBO: {str(e)[:160]}")

    try:
        body = r.json()
    except Exception:
        logger.warning("ch2 approve OBO non-JSON %s: %s", r.status_code, r.text[:150])
        raise HTTPException(403, f"On-behalf-of SQL was rejected (HTTP {r.status_code}: likely a missing "
                                 f"`sql` scope on your token). Re-authorize the app in a fresh session and "
                                 f"retry. Approval was NOT recorded.")

    state = (body.get("status") or {}).get("state")
    sid = body.get("statement_id")
    deadline = _t.monotonic() + 40
    while state in ("PENDING", "RUNNING") and sid:
        if _t.monotonic() > deadline:
            raise HTTPException(504, "approval timed out — not recorded")
        _t.sleep(1)
        body = requests.get(f"{host}/api/2.0/sql/statements/{sid}", headers=headers, timeout=20).json()
        state = (body.get("status") or {}).get("state")

    if state != "SUCCEEDED":
        msg = ((body.get("status") or {}).get("error") or {}).get("message") or str(state)
        up = msg.upper()
        if r.status_code in (401, 403) or "PERMISSION" in up or "DENIED" in up or "EXECUTE" in up:
            raise HTTPException(403, f"Approval denied by Unity Catalog — you are not an approver. {msg[:160]}")
        logger.warning("ch2 approve CALL failed (state=%s): %s", state, msg[:200])
        raise HTTPException(400, f"approval blocked: {msg[:200]}")

    # session_user() inside the procedure is the true approver; report it for the UI.
    approver = get_current_user() or "the signed-in user"
    return {"ok": True, "approved_by": approver, "enforced": "obo_user", "recompute": check["totals"]}


@router.get("/ch2/release")
async def ch2_release():
    """The active demo release (most recent) + the release chain head."""
    rel = await _safe_q(f"SELECT release_id, run_id, plan_hash, approver, previous_release_id, "
                        f"cast(released_at as string) released_at FROM {fqn('optimisation_demo_ch2_releases')} "
                        f"ORDER BY released_at DESC LIMIT 1")
    return {"active_release": (rel[0] if rel else None)}


# --------------------------------------------------------------------------- #
# Chapter 2 Check — synthetic outcome check on the active release
# --------------------------------------------------------------------------- #
CH2_CHECK_JOB = "Optimisation demo — Chapter 2 check (gen2)"


@router.post("/ch2/check")
async def ch2_check():
    job_id = resolve_job_by_name(CH2_CHECK_JOB)
    if not job_id:
        raise HTTPException(503, f"Job '{CH2_CHECK_JOB}' not found — deploy the bundle first.")
    try:
        resp = get_workspace_client().api_client.do(
            "POST", "/api/2.1/jobs/run-now",
            body={"job_id": int(job_id), "job_parameters": {"catalog_name": get_catalog(), "schema_name": get_schema()}})
    except Exception as e:
        raise HTTPException(502, f"Could not start the check job: {str(e)[:200]}")
    return {"job_run_id": resp.get("run_id"), "status": "running"}


@router.get("/ch2/monitoring")
async def ch2_monitoring():
    rel = await _safe_q(f"SELECT release_id FROM {fqn('optimisation_demo_ch2_releases')} ORDER BY released_at DESC LIMIT 1")
    if not rel:
        return {"release_id": None, "period": None, "rows": []}
    rid = rel[0]["release_id"]
    mx = await _safe_q(f"SELECT max(period) p FROM {fqn('optimisation_demo_ch2_monitoring')} WHERE release_id = :r", {"r": rid})
    period = mx[0]["p"] if (mx and mx[0].get("p") is not None) else None
    rows = []
    if period is not None:
        rows = await _safe_q(f"SELECT segment, round(expected_sales,1) expected_sales, observed_sales, "
                             f"round(expected_margin,0) expected_margin, round(observed_margin,0) observed_margin, n "
                             f"FROM {fqn('optimisation_demo_ch2_monitoring')} WHERE release_id = :r AND period = :p ORDER BY segment",
                             {"r": rid, "p": int(period)}) or []
    return {"release_id": rid, "period": period, "rows": rows}


# --------------------------------------------------------------------------- #
# Chapter 3 — robust decision across worlds
# --------------------------------------------------------------------------- #
CH3_RUN_JOB = "Optimisation demo — Chapter 3 run (gen2)"


class Ch3RunRequest(BaseModel):
    sales_ratio: Optional[float] = 0.98


@router.post("/ch3/run")
async def ch3_run(req: Ch3RunRequest):
    r = req.sales_ratio if req.sales_ratio is not None else 0.98
    if r < 0 or r > 2:
        raise HTTPException(400, "sales_ratio must be between 0 and 2")
    job_id = resolve_job_by_name(CH3_RUN_JOB)
    if not job_id:
        raise HTTPException(503, f"Job '{CH3_RUN_JOB}' not found — deploy the bundle first.")
    app_run_id = uuid.uuid4().hex
    params = {"catalog_name": get_catalog(), "schema_name": get_schema(),
              "app_run_id": app_run_id, "sales_ratio": str(r)}
    try:
        resp = get_workspace_client().api_client.do(
            "POST", "/api/2.1/jobs/run-now", body={"job_id": int(job_id), "job_parameters": params})
    except Exception as e:
        raise HTTPException(502, f"Could not start the Chapter 3 job: {str(e)[:200]}")
    return {"app_run_id": app_run_id, "job_run_id": resp.get("run_id"), "sales_ratio": r, "status": "running"}


@router.get("/ch3/run/{app_run_id}")
async def ch3_run_status(app_run_id: str, job_run_id: int = Query(...)):
    if not _APP_RUN_ID.match(app_run_id):
        raise HTTPException(400, "invalid application run id")
    life = res = page = None
    try:
        job = get_workspace_client().api_client.do("GET", "/api/2.1/jobs/runs/get", query={"run_id": int(job_run_id)})
        st = job.get("state") or {}
        life, res, page = st.get("life_cycle_state"), st.get("result_state"), job.get("run_page_url")
    except Exception as e:
        logger.warning("ch3 runs/get failed: %s", str(e)[:120])

    run_row = await _safe_q(f"SELECT sales_ratio, n_models, n_worlds, round(robust_worst_uplift,0) robust_worst_uplift, "
                            f"round(nominal_worst_uplift,0) nominal_worst_uplift FROM {fqn('optimisation_demo_ch3_runs')} "
                            f"WHERE run_id = :rid", {"rid": app_run_id})
    result = None
    if run_row:
        worlds = await _safe_q(f"SELECT world_id, model, market_scale, cost_scale, label FROM {fqn('optimisation_demo_ch3_worlds')} "
                               f"WHERE run_id = :rid ORDER BY world_id", {"rid": app_run_id}) or []
        comp = await _safe_q(f"SELECT plan, world_id, round(uplift,0) uplift, round(sales,1) sales, meets_floor "
                             f"FROM {fqn('optimisation_demo_ch3_comparison')} WHERE run_id = :rid", {"rid": app_run_id}) or []
        sel = await _safe_q(f"SELECT plan, segment, factor FROM {fqn('optimisation_demo_ch3_selection')} "
                            f"WHERE run_id = :rid ORDER BY segment", {"rid": app_run_id}) or []
        result = {"run": run_row[0], "worlds": worlds, "comparison": comp, "selection": sel}
    terminal = life in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR")
    if terminal and res == "SUCCESS":
        status = "succeeded" if result else "running"
    elif terminal:
        status = "failed"
    else:
        status = "running"
    return {"app_run_id": app_run_id, "job_run_id": job_run_id, "life_cycle_state": life,
            "result_state": res, "run_page_url": page, "status": status, "result": result}
