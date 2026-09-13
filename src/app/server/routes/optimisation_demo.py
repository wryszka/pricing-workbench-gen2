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
from server.optimisation_demo.economics import cost_of

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
    representative = None
    if rep:
        r0 = rep[0]
        # WP1#2 — type the boundary and compute the cost SERVER-SIDE with the same
        # cost_of() the scorer uses. Doing this on the client added SQL strings
        # ("700" + "60" + …) → string concatenation. £700 + £60 + 10%·£1,000 = £860.
        claims = coerce.as_float(r0.get("expected_claims"), field="expected_claims")
        expenses = coerce.as_float(r0.get("per_sale_expenses"), field="per_sale_expenses")
        commission_rate = coerce.as_float(r0.get("commission_rate"), field="commission_rate")
        baseline = coerce.as_float(r0.get("baseline_price"), field="baseline_price")
        representative = {
            "opportunity_id": coerce.as_str(r0.get("opportunity_id"), field="opportunity_id"),
            "driver_age": coerce.opt_int(r0.get("driver_age"), field="driver_age"),
            "vehicle_group": r0.get("vehicle_group"),
            "baseline_price": baseline,
            "market_premium": coerce.as_float(r0.get("market_premium"), field="market_premium"),
            "expected_claims": claims,
            "per_sale_expenses": expenses,
            "commission_rate": commission_rate,
            "modelled_cost": round(cost_of(baseline, claims, expenses, commission_rate), 2),
        }
    return {"ready": True, "segments": rows, "totals": totals,
            "grandma_segment": GRANDMA_SEGMENT,
            "representative_opportunity": representative}


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
    # WP1#6 — period is returned as a SQL string; type it so the client compares
    # numerically (period 10 must follow 9, not sort lexically as "10" < "9").
    period = coerce.opt_int(mx[0].get("p"), field="period") if mx else None
    rows = []
    if period is not None:
        raw = await _safe_q(f"SELECT segment, round(expected_sales,1) expected_sales, observed_sales, "
                            f"round(expected_margin,0) expected_margin, round(observed_margin,0) observed_margin, n "
                            f"FROM {fqn('optimisation_demo_ch2_monitoring')} WHERE release_id = :r AND period = :p ORDER BY segment",
                            {"r": rid, "p": int(period)}) or []
        for r in raw:
            rows.append({
                "segment": coerce.as_str(r.get("segment"), field="segment"),
                "expected_sales": coerce.opt_float(r.get("expected_sales"), field="expected_sales"),
                "observed_sales": coerce.opt_float(r.get("observed_sales"), field="observed_sales"),
                "expected_margin": coerce.opt_float(r.get("expected_margin"), field="expected_margin"),
                "observed_margin": coerce.opt_float(r.get("observed_margin"), field="observed_margin"),
                "n": coerce.opt_int(r.get("n"), field="n"),
            })
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


# --------------------------------------------------------------------------- #
# WP4 — Decision Review (read-only assistant). Deterministic fact layer over a
# Chapter 3 run + the governed business-evidence pack. No prices are chosen, no
# policy altered, no scenario executed, no release approved. The LLM narration is
# an OPTIONAL layer on top; when it isn't wired/available the deterministic facts
# and templated cards ARE the response ("AI review unavailable"), which is honest.
# --------------------------------------------------------------------------- #
from server.optimisation_demo import decision_review as dreview  # noqa: E402
from server.optimisation_demo import business_evidence as bevidence  # noqa: E402


@router.get("/review/ch3/{app_run_id}")
async def review_ch3_challenge(app_run_id: str):
    """Pricing-Challenger facts + ranked cards for a Chapter 3 run — the challenge from
    OUTSIDE the optimiser. Read-only; consumes only governed tables by explicit run id and
    the versioned evidence pack. Returns the deterministic facts and, when uncovered, a
    drafted stress the human may choose to run via the normal control (never auto-run)."""
    if not _APP_RUN_ID.match(app_run_id):
        raise HTTPException(400, "invalid application run id")
    worlds = await _safe_q(f"SELECT world_id, model, market_scale, cost_scale, label "
                           f"FROM {fqn('optimisation_demo_ch3_worlds')} WHERE run_id = :r ORDER BY world_id",
                           {"r": app_run_id})
    comp = await _safe_q(f"SELECT plan, world_id, uplift FROM {fqn('optimisation_demo_ch3_comparison')} "
                         f"WHERE run_id = :r", {"r": app_run_id})
    if not worlds or not comp:
        raise HTTPException(404, "Chapter 3 run not found (or has no worlds/comparison yet)")

    included_cost = sorted({coerce.as_float(w["cost_scale"], field="cost_scale") for w in worlds})
    uplift: dict = {}
    for c in comp:
        plan = coerce.as_str(c["plan"], field="plan")
        uplift.setdefault(plan, {})[coerce.as_str(c["world_id"], field="world_id")] = \
            coerce.as_float(c["uplift"], field="uplift")

    facts = []
    fin = bevidence.get_item("FIN-PLAN-CLAIMSINFL-2026")
    if fin:
        facts.append(dreview.scenario_coverage_gap(included_cost, fin))
    if "robust" in uplift and "nominal" in uplift:
        facts.append(dreview.robust_vs_nominal_tradeoff(uplift["robust"], uplift["nominal"]))
    unchanged = [w for w in worlds if coerce.as_float(w["cost_scale"], field="cs") == 1.0
                 and coerce.as_float(w["market_scale"], field="ms") == 1.0]
    if len(unchanged) >= 2 and "robust" in uplift:
        by_model = {coerce.as_str(w["model"], field="model"):
                    uplift["robust"].get(coerce.as_str(w["world_id"], field="wid")) for w in unchanged}
        by_model = {m: v for m, v in by_model.items() if v is not None}
        if len(by_model) >= 2:
            facts.append(dreview.model_disagreement(by_model))
    claims = bevidence.get_item("CLAIMS-MOTOR-2026H1")
    if claims and fin:
        facts.append(dreview.source_compatibility(claims, fin))

    cards = dreview.challenge_cards(facts, limit=3)
    return {
        "run_id": app_run_id, "role": "pricing_challenger",
        "evidence_pack_version": bevidence.PACK_VERSION,
        "evidence_pack_hash": bevidence.pack_hash(),
        "included_cost_stresses": included_cost,
        "facts": facts, "challenges": cards,
        "ai_review": "unavailable",
        "ai_review_note": "Deterministic evidence review (no language-model narration in this build).",
    }


@router.get("/review/evidence")
async def review_evidence():
    """The versioned synthetic business-evidence pack (read-only) — provenance for each item."""
    pack = bevidence.evidence_pack()
    return {"pack_version": pack["pack_version"], "pack_hash": bevidence.pack_hash(pack),
            "items": pack["items"]}


# --- Review events (append-only human dispositions — NOT approval) --- #
_REVIEW_EVENTS = "optimisation_demo_review_events"


async def _ensure_review_events_table():
    await execute_query(
        f"CREATE TABLE IF NOT EXISTS {fqn(_REVIEW_EVENTS)} ("
        f"event_id STRING, decision_kind STRING, run_id STRING, evidence_pack_hash STRING, "
        f"challenge_fact_id STRING, disposition STRING, reason STRING, reviewer STRING, "
        f"created_at TIMESTAMP) TBLPROPERTIES ('delta.appendOnly' = 'true')")


class ReviewEventRequest(BaseModel):
    decision_kind: str            # "ch3" | "ch2"
    app_run_id: str
    challenge_fact_id: str
    disposition: str              # investigate | accept_with_reason | not_relevant_with_reason
    reason: Optional[str] = None


@router.post("/review/events")
async def review_record_event(req: ReviewEventRequest):
    """Record a human disposition against a challenge — append-only, attributed. This is a
    review event, NOT an approval; it never changes prices, policy or a release."""
    if not _APP_RUN_ID.match(req.app_run_id):
        raise HTTPException(400, "invalid application run id")
    if req.disposition not in dreview.DISPOSITIONS:
        raise HTTPException(400, f"disposition must be one of {dreview.DISPOSITIONS}")
    if req.disposition != "investigate" and not (req.reason and req.reason.strip()):
        raise HTTPException(400, "a reason is required to accept or dismiss a challenge")
    reviewer = get_current_user() or "unknown"
    await _ensure_review_events_table()
    await execute_query(
        f"INSERT INTO {fqn(_REVIEW_EVENTS)} SELECT :eid, :kind, :rid, :ph, :cf, :disp, :reason, :who, current_timestamp()",
        {"eid": uuid.uuid4().hex, "kind": req.decision_kind, "rid": req.app_run_id,
         "ph": bevidence.pack_hash(), "cf": req.challenge_fact_id, "disp": req.disposition,
         "reason": (req.reason or ""), "who": reviewer})
    return {"ok": True, "reviewer": reviewer, "disposition": req.disposition}


async def _review_events(app_run_id: str) -> list[dict]:
    rows = await _safe_q(
        f"SELECT challenge_fact_id, disposition, reason, reviewer, cast(created_at as string) created_at "
        f"FROM {fqn(_REVIEW_EVENTS)} WHERE run_id = :r ORDER BY created_at", {"r": app_run_id})
    return [{"challenge_fact_id": r["challenge_fact_id"], "disposition": r["disposition"],
             "reason": r.get("reason"), "reviewer": r.get("reviewer"),
             "created_at": r.get("created_at")} for r in (rows or [])]


@router.get("/review/events/{app_run_id}")
async def review_list_events(app_run_id: str):
    if not _APP_RUN_ID.match(app_run_id):
        raise HTTPException(400, "invalid application run id")
    return {"run_id": app_run_id, "events": await _review_events(app_run_id)}


@router.get("/review/brief/ch3/{app_run_id}")
async def review_committee_brief(app_run_id: str):
    """Committee briefing for a Chapter 3 decision — deterministic. Every number comes from
    the fact layer; it reflects only a REAL recorded release for the approval line and
    preserves unresolved disagreement. Exportable by the client."""
    if not _APP_RUN_ID.match(app_run_id):
        raise HTTPException(400, "invalid application run id")
    challenge = await review_ch3_challenge(app_run_id)          # reuse the deterministic facts
    events = await _review_events(app_run_id)
    # There is no per-Ch3 release in this build; approval_state is None → "No human decision
    # recorded". (Ch3 approval/release is WP3-remaining; the brief never fakes an approval.)
    tradeoff = next((f for f in challenge["facts"] if f["fact_id"] == "tradeoff.robust_nominal"), None)
    brief = dreview.committee_brief(app_run_id, challenge["challenges"], events,
                                    approval_state=None, tradeoff_fact=tradeoff)
    brief["evidence_pack_hash"] = challenge["evidence_pack_hash"]
    return brief
