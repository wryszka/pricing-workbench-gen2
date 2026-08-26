"""Control-tower overview — a single aggregate the landing page renders as a
current-state dashboard: the live rate book, portfolio KPIs, model/endpoint
health, governance freshness, a process ribbon, and (lazily) an LLM narrative.

Every metric is computed independently and defensively: a query that fails
(missing table on a partial build, renamed column) yields null for that metric
rather than 500-ing the whole page. This is a demo control tower — it must
degrade gracefully, never blank out.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter

from server.config import fqn, get_workspace_client
from server.sql import execute_query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/overview", tags=["overview"])

# Serving endpoints whose health the control tower reports.
_ENDPOINTS = {
    "rating_engine": "pwg2_pricing_scorer",
    "chat_agent":    "pwg2_chat_agent",
    "governance_agent": "pwg2_governance_agent",
    "motor_scorer":  "pwg2_motor_scorer_direct",
}
_FM_ENDPOINT = os.getenv("AGENT_FM_ENDPOINT", "databricks-claude-sonnet-4-6")


async def _scalar(sql: str):
    """Run a one-cell query; return the value or None on any failure."""
    try:
        rows = await execute_query(sql)
        if rows:
            return list(rows[0].values())[0]
    except Exception as e:
        logger.info("overview scalar failed (%s): %s", sql[:60], e)
    return None


async def _row(sql: str) -> dict | None:
    try:
        rows = await execute_query(sql)
        return dict(rows[0]) if rows else None
    except Exception as e:
        logger.info("overview row failed (%s): %s", sql[:60], e)
        return None


@router.get("")
async def overview():
    # --- Live rate book (rolling releases: champion = current month) ----------
    live = await _row(f"""
        SELECT release_id, display_name, cast(effective_date AS string) AS effective_date,
               freq_glm_version, sev_glm_version, demand_gbm_version, fraud_gbm_version,
               rating_engine_version, narrative
        FROM {fqn('pricing_engine_releases')}
        WHERE status = 'champion'
        ORDER BY effective_date DESC LIMIT 1
    """)
    prev = await _row(f"""
        SELECT display_name, cast(effective_date AS string) AS effective_date
        FROM {fqn('pricing_engine_releases')}
        WHERE status = 'previous_champion'
        ORDER BY effective_date DESC LIMIT 1
    """)
    release_count = await _scalar(f"SELECT COUNT(*) FROM {fqn('pricing_engine_releases')}")

    # --- Portfolio KPIs -------------------------------------------------------
    book_size = await _scalar(f"SELECT COUNT(*) FROM {fqn('internal_commercial_policies')}")
    gwp       = await _scalar(f"SELECT SUM(current_premium) FROM {fqn('internal_commercial_policies')}")
    incurred  = await _scalar(f"SELECT SUM(incurred_amount) FROM {fqn('internal_claims_history')}")
    quotes_30d = await _scalar(f"""
        SELECT COUNT(*) FROM {fqn('quotes')}
        WHERE created_at >= current_timestamp() - INTERVAL 30 DAYS
    """)
    bind = await _row(f"""
        SELECT
            SUM(CASE WHEN quote_status = 'BOUND' THEN 1 ELSE 0 END) AS bound,
            COUNT(*) AS total
        FROM {fqn('quotes')}
    """)

    # 5-year loss ratio: total incurred over ~5 years of earned premium.
    loss_ratio = None
    try:
        if gwp and incurred is not None and float(gwp) > 0:
            loss_ratio = round(float(incurred) / (float(gwp) * 5.0), 3)
    except Exception:
        loss_ratio = None
    bind_rate = None
    try:
        if bind and bind.get("total"):
            bind_rate = round(float(bind["bound"] or 0) / float(bind["total"]), 3)
    except Exception:
        bind_rate = None

    kpis = {
        "book_size":   int(book_size) if book_size is not None else None,
        "gwp":         float(gwp) if gwp is not None else None,
        "loss_ratio":  loss_ratio,
        "quotes_30d":  int(quotes_30d) if quotes_30d is not None else None,
        "bind_rate":   bind_rate,
    }

    # --- Governance freshness -------------------------------------------------
    gov = await _row(f"""
        SELECT COUNT(*) AS packs, cast(MAX(generated_at) AS string) AS latest
        FROM {fqn('governance_packs_index')}
    """)

    # --- Endpoint health (serverless; READY even when scaled to zero) ---------
    endpoint_health = {}
    try:
        w = get_workspace_client()
        for key, name in _ENDPOINTS.items():
            try:
                ep = w.serving_endpoints.get(name)
                ready = str(ep.state.ready) if ep.state and ep.state.ready else ""
                endpoint_health[key] = {"name": name, "ready": "READY" in ready}
            except Exception:
                endpoint_health[key] = {"name": name, "ready": False}
    except Exception as e:
        logger.info("overview endpoint health failed: %s", e)

    # --- Process ribbon: presence-based stage health --------------------------
    mart_rows  = await _scalar(f"SELECT COUNT(*) FROM {fqn('unified_pricing_table_live')}")
    gov_packs  = (gov or {}).get("packs") or 0
    stages = [
        {"key": "ingestion",  "label": "Ingestion",     "ok": bool(book_size),
         "metric": f"{int(book_size):,} policies" if book_size else "no data"},
        {"key": "mart",       "label": "Modelling Mart", "ok": bool(mart_rows),
         "metric": f"{int(mart_rows):,} rows" if mart_rows else "no data"},
        {"key": "dev",        "label": "Model Dev",      "ok": bool(live),
         "metric": "4 champions" if live else "no champions"},
        {"key": "deployment", "label": "Deployment",     "ok": bool(endpoint_health.get("rating_engine", {}).get("ready")),
         "metric": "rating engine READY" if endpoint_health.get("rating_engine", {}).get("ready") else "scaled to zero"},
        {"key": "pricing",    "label": "Pricing Engine",  "ok": bool(live),
         "metric": (live or {}).get("display_name", "no live release")},
        {"key": "governance", "label": "Governance",      "ok": bool(gov_packs),
         "metric": f"{int(gov_packs)} packs" if gov_packs else "no packs"},
    ]

    return {
        "live_release":    live,
        "prev_release":    prev,
        "release_count":   int(release_count) if release_count is not None else None,
        "kpis":            kpis,
        "governance":      gov,
        "endpoint_health": endpoint_health,
        "stages":          stages,
    }


@router.get("/ai-summary")
async def ai_summary():
    """A 2-3 sentence 'where we are / what to look at' narrative over the current
    state. Calls the FM endpoint; falls back to a deterministic template so the
    strip always renders even if the FM is unavailable."""
    data = await overview()
    live = data.get("live_release") or {}
    k = data.get("kpis") or {}

    facts = []
    if live.get("display_name"):
        facts.append(f"Live rate book: {live['display_name']} "
                     f"(rating engine {live.get('rating_engine_version', '?')}).")
    if k.get("book_size"):
        facts.append(f"Book: {k['book_size']:,} policies.")
    if k.get("loss_ratio") is not None:
        facts.append(f"5-year loss ratio {k['loss_ratio']:.0%}.")
    if k.get("quotes_30d") is not None:
        facts.append(f"{k['quotes_30d']:,} quotes in the last 30 days"
                     + (f", {k['bind_rate']:.0%} bound." if k.get('bind_rate') is not None else "."))
    not_ready = [v["name"] for v in (data.get("endpoint_health") or {}).values() if not v.get("ready")]
    fact_str = " ".join(facts)

    # Template fallback (always available).
    fallback = (fact_str + (" All serving endpoints are warm." if not not_ready
                else f" {len(not_ready)} endpoint(s) scaled to zero — first call will cold-start.")).strip()

    try:
        import requests
        w = get_workspace_client()
        host = w.config.host.rstrip("/")
        token = w.config.authenticate()
        prompt = (
            "You are a pricing-operations control tower. In 2-3 short sentences, "
            "summarise the current state for a chief pricing actuary and say what to "
            "look at. Be specific and use the figures. Do not invent numbers.\n\n"
            f"Facts: {fact_str}"
        )
        resp = requests.post(
            f"{host}/serving-endpoints/{_FM_ENDPOINT}/invocations",
            headers={**token, "Content-Type": "application/json"},
            json={"messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 200, "temperature": 0.2},
            timeout=30,
        )
        resp.raise_for_status()
        j = resp.json()
        text = ((j.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        return {"summary": text.strip() or fallback, "source": "fm" if text.strip() else "fallback"}
    except Exception as e:
        logger.info("overview ai-summary FM call failed, using fallback: %s", e)
        return {"summary": fallback, "source": "fallback"}
