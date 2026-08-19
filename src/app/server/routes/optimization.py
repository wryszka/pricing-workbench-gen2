"""`/api/optimization` — the Price Optimization module surface (the new opt_*
tables). Distinct from the older /api/optimisation (the v2 proxy demo). Every
read is defensive: if a table isn't built yet (optimization not run), it returns
an empty/awaiting shape so the app page shows a graceful "run the optimization
job" state rather than erroring.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter

from server.config import fqn, get_bundle_files_base
from server.sql import execute_query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/optimization", tags=["optimization"])


async def _rows(sql: str):
    try:
        return await execute_query(sql)
    except Exception as e:
        logger.info("optimization query empty/failed: %s", str(e)[:120])
        return []


@router.get("/overview")
async def overview():
    scen = await _rows(f"""
        SELECT count(*) AS candidates,
               round(max(expected_profit),0) AS best_profit,
               max_by(scenario_id, expected_profit) AS best_scenario
        FROM {fqn('opt_scenarios')}""")
    hold = await _rows(f"SELECT round(expected_profit,0) AS p FROM {fqn('opt_scenarios')} WHERE scenario_id='hold'")
    fac = await _rows(f"""
        SELECT count(*) AS segments, round(sum(profit_uplift),0) AS total_uplift,
               max(constraint_version) AS constraint_version,
               sum(case when within_corridor then 0 else 1 end) AS breaches
        FROM {fqn('opt_factor_table')}""")
    ready = bool(scen and scen[0].get("candidates"))
    return {
        "ready": ready,
        "candidates": (scen[0].get("candidates") if scen else 0),
        "best_profit": (scen[0].get("best_profit") if scen else None),
        "hold_profit": (hold[0].get("p") if hold else None),
        "factors": (fac[0] if fac else {}),
    }


@router.get("/scenarios")
async def scenarios(limit: int = 30):
    return {"scenarios": await _rows(f"""
        SELECT scenario_id, expected_profit, expected_volume, expected_gwp,
               expected_loss_ratio, avg_factor
        FROM {fqn('opt_scenarios')} ORDER BY expected_profit DESC LIMIT {int(limit)}""")}


@router.get("/factors")
async def factors():
    return {"factors": await _rows(f"""
        SELECT constraint_version, segment, policies, factor, factor_pct,
               gwp_current, expected_profit_opt, profit_uplift, within_corridor
        FROM {fqn('opt_factor_table')} ORDER BY profit_uplift DESC""")}


@router.get("/curves")
async def curves():
    return {"curves": await _rows(f"""
        SELECT segment, price_ratio, p_convert
        FROM {fqn('opt_elasticity_curves')} ORDER BY segment, price_ratio""")}


@router.get("/monitoring")
async def monitoring():
    return {
        "conversion": await _rows(f"""
            SELECT cast(month as string) AS month, quotes, actual_conversion,
                   avg_price_ratio, conversion_drift_mom
            FROM {fqn('opt_conversion_actuals')} ORDER BY month"""),
        "deviation": await _rows(f"""
            SELECT deviation_band, segments, policies
            FROM {fqn('opt_deviation_dist')} ORDER BY deviation_band"""),
    }


@router.get("/constraints")
async def constraints():
    """Return the versioned constraint YAML (policy-as-code) as text so the app
    can show it + its intent. Reads the deployed bundle file."""
    path = os.path.join(get_bundle_files_base(), "09_optimization", "constraints", "default.yaml")
    try:
        with open(path) as fh:
            text = fh.read()
        version = next((ln.split(":", 1)[1].strip().strip('"') for ln in text.splitlines()
                        if ln.startswith("version:")), "v1")
        return {"ok": True, "path": path, "version": version, "yaml": text}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "path": path}
