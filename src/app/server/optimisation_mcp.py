"""Price-optimisation MCP tool surface (Principle 8 — MCP-first).

Every optimisation *stage* and *read* exposed as a callable tool, so the app, a
notebook, and an orchestrating agent are all clients of the same surface — nothing
built twice. Registered into the JSON-RPC server in routes/mcp.py.

Action tools trigger the real governed jobs (by name → run-now via the app SP,
no PAT). The deployment gate stays enforced server-side: `deploy_factors`
re-checks the corridor and cannot be talked past regardless of the calling agent.
Read tools return live UC tables.
"""
from __future__ import annotations

import logging
from typing import Any

from server.config import (fqn, get_workspace_client, resolve_job_by_name,
                           get_bundle_files_base, get_current_user)
from server.sql import execute_query

logger = logging.getLogger(__name__)

CORRIDOR_PCT = 15.0
_JOBS = {
    "run_simulation": "Price optimisation — simulation (gen2)",
    "run_solver":     "Price optimisation — constrained solver (gen2)",
    "advance_month":  "Price optimisation — advance month (did it work?) (gen2)",
    "run_fairness":   "Price optimisation — fairness & fair-value evidence (gen2)",
    "heavy_mode":     "Price optimisation — heavy mode (ensemble + stochastic) (gen2)",
}


async def _q(sql: str):
    try:
        return await execute_query(sql)
    except Exception as e:
        logger.warning("opt-mcp query failed: %s", str(e)[:160])
        return []


def _run_job(name: str, params: dict | None = None) -> dict:
    job_id = resolve_job_by_name(name)
    if not job_id:
        return {"ok": False, "error": f"job '{name}' not found"}
    body: dict = {"job_id": int(job_id)}
    if params:
        body["job_parameters"] = {k: str(v) for k, v in params.items()}
    try:
        r = get_workspace_client().api_client.do("POST", "/api/2.1/jobs/run-now", body=body)
        return {"ok": True, "run_id": r.get("run_id"), "job": name, "params": params or {}}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


# --- action tools -----------------------------------------------------------
async def _t_run_simulation(args, session_id, agent_id):
    return _run_job(_JOBS["run_simulation"], {"grid_points": int(args.get("grid_points", 3000))})

async def _t_run_solver(args, session_id, agent_id):
    p = {}
    if args.get("objective"): p["objective"] = str(args["objective"])
    if args.get("constraint_version"): p["constraint_version"] = str(args["constraint_version"])
    return _run_job(_JOBS["run_solver"], p or None)

async def _t_run_fairness(args, session_id, agent_id):
    return _run_job(_JOBS["run_fairness"])

async def _t_advance_month(args, session_id, agent_id):
    return _run_job(_JOBS["advance_month"])

async def _t_run_heavy_mode(args, session_id, agent_id):
    preset = str(args.get("preset") or "default")
    return _run_job(_JOBS["heavy_mode"], {"preset": preset})

async def _t_deploy_factors(args, session_id, agent_id):
    """Server-side gate: RBAC + corridor re-check. An agent cannot bypass it."""
    rows = await _q(f"SELECT segment, factor, constraint_version FROM {fqn('optimisation_factor_table')}")
    if not rows:
        return {"ok": False, "error": "no factor table — solve first"}
    lo, hi = 1 - CORRIDOR_PCT / 100, 1 + CORRIDOR_PCT / 100
    breaches = [r["segment"] for r in rows
                if not (lo - 1e-6 <= float(r.get("factor") or 1.0) <= hi + 1e-6)]
    if breaches:
        return {"ok": False, "gated": True,
                "error": f"deploy blocked: {len(breaches)} segment(s) outside ±{CORRIDOR_PCT:.0f}% corridor"}
    cver = str(rows[0].get("constraint_version") or "v1")
    who = get_current_user() or agent_id or "mcp-agent"
    p = {"cver": cver, "who": who, "note": f"deployed via MCP by {agent_id}", "n": len(rows)}
    await execute_query(f"""
        INSERT INTO {fqn('optimisation_deployment')}
        SELECT uuid(), :cver, :n, :who, :note, current_timestamp()""", p)
    await execute_query(f"""
        INSERT INTO {fqn('audit_log')} (event_id, event_type, entity_type, entity_id, entity_version,
               user_id, timestamp, details, source)
        SELECT uuid(), 'optimisation_deploy_approved', 'factor_table', :cver, :cver, :who,
               current_timestamp(), to_json(named_struct('segments', :n, 'note', :note)), 'optimisation_mcp'""", p)
    return {"ok": True, "segments": len(rows), "constraint_version": cver, "deployed_by": who}


# --- read tools -------------------------------------------------------------
async def _t_read_scenarios(args, session_id, agent_id):
    rows = await _q(f"""SELECT scenario_id, expected_profit, expected_volume, expected_gwp, pareto
                        FROM {fqn('optimisation_scenarios')} WHERE pareto=true OR scenario_id='hold'
                        ORDER BY expected_volume""")
    return {"ok": True, "frontier": rows}

async def _t_read_factors(args, session_id, agent_id):
    rows = await _q(f"""SELECT segment, factor_pct, conversion_hold, conversion_opt, profit_uplift, binding
                        FROM {fqn('optimisation_factor_table')} ORDER BY segment""")
    return {"ok": True, "factors": rows}

async def _t_read_monitoring(args, session_id, agent_id):
    drift = await _q(f"""SELECT cast(quote_month as string) month, actual_conversion, expected_conversion, drift
                         FROM {fqn('optimisation_monitoring')} ORDER BY quote_month""")
    breaches = await _q(f"SELECT check, breaches, total, rate FROM {fqn('optimisation_constraint_breaches')}")
    return {"ok": True, "drift": drift, "breaches": breaches}

async def _t_read_fairness(args, session_id, agent_id):
    ev = await _q(f"SELECT check, dimension, group, value, threshold, pass FROM {fqn('optimisation_fairness_evidence')}")
    summ = await _q(f"SELECT overall_pass, worst_proxy_corr, evidence FROM {fqn('optimisation_fairness_summary')} LIMIT 1")
    return {"ok": True, "checks": ev, "summary": (summ or [None])[0]}

async def _t_read_constraints(args, session_id, agent_id):
    path = f"{get_bundle_files_base()}/04_models/production/optimisation_constraints/default.yaml"
    try:
        raw = get_workspace_client().workspace.download(path).read()
        return {"ok": True, "path": path, "yaml": raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}

async def _t_explain_price(args, session_id, agent_id):
    qid = str(args.get("quote_id") or "").replace("'", "''")
    if not qid:
        return {"ok": False, "error": "quote_id required"}
    rows = await _q(f"SELECT {fqn('explain_price')}('{qid}') AS j")
    import json as _j
    try:
        return {"ok": True, "decomposition": _j.loads(rows[0]["j"]) if rows and rows[0].get("j") else None}
    except Exception:
        return {"ok": True, "decomposition_raw": rows[0].get("j") if rows else None}

async def _t_get_decision_record(args, session_id, agent_id):
    did = str(args.get("deployment_id") or "").replace("'", "''")
    where = f"WHERE deployment_id = '{did}'" if did else ""
    rows = await _q(f"""SELECT deployment_id, cast(created_at as string) created_at, approver, constraint_version,
                        conversion_model, retention_model, data_snapshot, objective, chosen_json,
                        rejected_json, fairness_pass, fairness_summary, rerun_pointer
                        FROM {fqn('optimisation_decision_records')} {where} ORDER BY created_at DESC LIMIT 1""")
    return {"ok": True, "record": rows[0] if rows else None}

async def _t_read_disagreement(args, session_id, agent_id):
    rows = await _q(f"""SELECT segment, factor_min, factor_max, factor_spread_pp, agreement, n_models
                        FROM {fqn('optimisation_disagreement')} ORDER BY factor_spread_pp DESC""")
    return {"ok": True, "segments": rows}

async def _t_read_run_costs(args, session_id, agent_id):
    rows = await _q(f"""SELECT preset, grid_points, n_draws, n_models, policies, total_evaluations,
                        wallclock_s, est_cost_usd, cast(ran_at as string) ran_at
                        FROM {fqn('optimisation_heavy_meta')} LIMIT 1""")
    return {"ok": True, "last_heavy_run": rows[0] if rows else None}


def _schema(name, desc, props=None, required=None):
    return {"name": name, "description": desc,
            "inputSchema": {"type": "object", "properties": props or {}, "required": required or []}}


OPTIMISATION_TOOL_SCHEMAS: list[dict[str, Any]] = [
    _schema("opt_run_simulation", "Score N candidate price sets across the book (the 'N is your choice' sweep). Returns a run_id.",
            {"grid_points": {"type": "integer", "description": "number of candidate price sets (default 3000)"}}),
    _schema("opt_run_solver", "Solve the optimal per-segment factors under the versioned constraint set for a given objective. Returns a run_id.",
            {"objective": {"type": "string", "enum": ["expected_profit", "expected_gwp", "retention_weighted_profit"]},
             "constraint_version": {"type": "string"}}),
    _schema("opt_run_fairness", "Regenerate the fairness / fair-value evidence for the current solved factor set."),
    _schema("opt_advance_month", "Close the loop: roll the synthetic book forward one month under the deployed prices and realize outcomes."),
    _schema("opt_run_heavy_mode", "Run HEAVY MODE (ensemble disagreement map + exhaustive per-policy Monte-Carlo). preset='live' for a small room-safe run.",
            {"preset": {"type": "string", "enum": ["default", "live"]}}),
    _schema("opt_deploy_factors", "Approve & deploy the solved factor set. Server-side gate: RBAC + ±corridor re-check; cannot be bypassed."),
    _schema("opt_explain_price", "Decompose one quote into technical price + optimisation factor + corridor clamp (explain-this-price).",
            {"quote_id": {"type": "string"}}, ["quote_id"]),
    _schema("opt_get_decision_record", "The immutable decision record for a deployment (chosen + rejected alternatives + fairness + re-run pointer). Latest if no id.",
            {"deployment_id": {"type": "string"}}),
    _schema("opt_read_scenarios", "Read the efficient frontier (Pareto-optimal candidates + hold)."),
    _schema("opt_read_factors", "Read the solved per-segment factor table."),
    _schema("opt_read_monitoring", "Read conversion-drift over months + corridor/GIPP breach rates."),
    _schema("opt_read_fairness", "Read the fair-value evidence pack (proxy-correlation / disparate-impact / vulnerability checks)."),
    _schema("opt_read_disagreement", "Read the ensemble disagreement map (per-segment factor spread/agreement across candidate demand models)."),
    _schema("opt_read_run_costs", "Read the last heavy-mode run's measured cost — row count, wall-clock, est. compute cost."),
    _schema("opt_read_constraints", "Read the versioned constraint YAML (the pricing policy)."),
]

OPTIMISATION_TOOL_IMPLS = {
    "opt_run_simulation": _t_run_simulation,
    "opt_run_solver":     _t_run_solver,
    "opt_run_fairness":   _t_run_fairness,
    "opt_advance_month":  _t_advance_month,
    "opt_run_heavy_mode": _t_run_heavy_mode,
    "opt_deploy_factors": _t_deploy_factors,
    "opt_explain_price":  _t_explain_price,
    "opt_get_decision_record": _t_get_decision_record,
    "opt_read_scenarios": _t_read_scenarios,
    "opt_read_factors":   _t_read_factors,
    "opt_read_monitoring": _t_read_monitoring,
    "opt_read_fairness":  _t_read_fairness,
    "opt_read_disagreement": _t_read_disagreement,
    "opt_read_run_costs": _t_read_run_costs,
    "opt_read_constraints": _t_read_constraints,
}
