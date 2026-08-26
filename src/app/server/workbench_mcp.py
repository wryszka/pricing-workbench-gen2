"""Workbench MCP tools — the full app surface exposed as callable tools.

Every tool DELEGATES to the existing app route handler, so it reuses the exact
logic AND the exact server-side gate (a gated route stays gated here — the tools
run inside the authenticated /api/mcp request, so get_current_user / _require_admin
work identically). Reads are idempotent; [gated] actions re-check RBAC/policy in
the route they call. Merged into the one MCP server in routes/mcp.py.

Grouped by workbench domain via tool-name prefix: price_ / deploy_ / gov_ /
ingest_ / factory_ / mart_ / book_ / review_.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable

from fastapi import HTTPException

from server.routes import (
    pricing, deployment, governance, datasets, factory_real,
    features, overview, compare, quote_stream, review,
)

logger = logging.getLogger(__name__)


async def _call(coro: Awaitable) -> dict:
    """Run a route handler, normalise to {"ok": ...}. HTTPException (incl. a 403
    from a server-side gate) becomes a clean {"ok": False, "gated"/"error"}."""
    try:
        r = await coro
    except HTTPException as e:
        gated = e.status_code in (401, 403)
        return {"ok": False, **({"gated": True} if gated else {}), "error": f"{e.status_code}: {e.detail}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
    if isinstance(r, dict):
        return {"ok": True, **r}
    return {"ok": True, "data": r}


def _schema(name, desc, props=None, required=None):
    return {"name": name, "description": desc,
            "inputSchema": {"type": "object", "properties": props or {}, "required": required or []}}


# ===========================================================================
# price_ — Pricing Engine, rating config, and mid-term adjustment
# ===========================================================================
async def _t_price_run_quote(a, s, ag):
    return await _call(pricing.run_quote(pricing.QuoteRunRequest(
        features=a.get("features") or {}, policy_id=a.get("policy_id"),
        rating_engine_version=a.get("rating_engine_version"))))

async def _t_price_mta_simulate(a, s, ag):
    return await _call(pricing.simulate_mta(pricing.MtaRequest(
        policy_id=str(a.get("policy_id") or ""), changes=a.get("changes") or {},
        effective_date=a.get("effective_date"), reason=a.get("reason"))))

async def _t_price_read_releases(a, s, ag):        return await _call(pricing.list_releases())
async def _t_price_read_current_release(a, s, ag): return await _call(pricing.current_release())
async def _t_price_read_release(a, s, ag):         return await _call(pricing.get_release(str(a.get("release_id") or "")))
async def _t_price_compare_releases(a, s, ag):
    return await _call(pricing.compare_release(pricing.CompareReleasesRequest(
        release_id=str(a.get("release_id") or ""),
        portfolio_size=int(a.get("portfolio_size") or 2000),
        scenario_id=str(a.get("scenario_id") or "none"))))
async def _t_price_read_rating_config(a, s, ag):   return await _call(pricing.get_rating_config_current())
async def _t_price_read_policy_context(a, s, ag):  return await _call(pricing.policy_context(str(a.get("policy_id") or "")))
async def _t_price_read_model_versions(a, s, ag):  return await _call(pricing.list_model_versions())


# ===========================================================================
# deploy_ — champions, promote/rollback, monthly rate-engine release
# ===========================================================================
async def _t_deploy_read_champions(a, s, ag):       return await _call(deployment.list_champions(require_pack=False))
async def _t_deploy_read_history(a, s, ag):         return await _call(deployment.champion_history(str(a.get("family") or ""), int(a.get("limit") or 10)))
async def _t_deploy_promote(a, s, ag):              return await _call(deployment.set_champion(str(a.get("family") or ""), str(a.get("version") or "")))
async def _t_deploy_rollback(a, s, ag):
    return await _call(deployment.rollback_champion(deployment.RollbackRequest(
        family=str(a.get("family") or ""), note=str(a.get("note") or ""))))
async def _t_deploy_cut_release(a, s, ag):
    return await _call(deployment.cut_rate_engine_release(deployment.RateEngineReleaseRequest(
        note=a.get("note"), effective_date=a.get("effective_date"))))
async def _t_deploy_backfill(a, s, ag):             return await _call(deployment.trigger_inference_backfill())


# ===========================================================================
# gov_ — governance packs, grounded agent, bias & adequacy monitors
# ===========================================================================
async def _t_gov_read_summary(a, s, ag):        return await _call(governance.governance_summary())
async def _t_gov_read_packs(a, s, ag):          return await _call(governance.list_packs())
async def _t_gov_read_pack_text(a, s, ag):      return await _call(governance.pack_text(str(a.get("pack_id") or "")))
async def _t_gov_read_policy_scoring(a, s, ag): return await _call(governance.policy_scoring(str(a.get("policy_id") or "")))
async def _t_gov_ask(a, s, ag):                 return await _call(governance.ask_governance_agent(governance.AskRequest(question=str(a.get("question") or ""))))
async def _t_gov_read_bias(a, s, ag):           return await _call(governance.bias_monitor())
async def _t_gov_bias_investigate(a, s, ag):
    return await _call(governance.bias_investigate(governance.BiasInvestigateRequest(
        question=str(a.get("question") or ""),
        protected_attribute=str(a.get("protected_attribute") or "director_gender"),
        family=a.get("family"))))
async def _t_gov_read_adequacy(a, s, ag):       return await _call(governance.premium_adequacy(str(a.get("cohort_dimension") or "industry_risk_tier")))
async def _t_gov_adequacy_investigate(a, s, ag):
    return await _call(governance.adequacy_investigate(governance.AdequacyInvestigateRequest(
        question=str(a.get("question") or ""),
        cohort_dimension=str(a.get("cohort_dimension") or "industry_risk_tier"))))


# ===========================================================================
# ingest_ — data sources, impact, and the actuary approval gate
# ===========================================================================
async def _t_ingest_read_datasets(a, s, ag):  return await _call(datasets.list_datasets())
async def _t_ingest_read_diff(a, s, ag):      return await _call(datasets.get_dataset_diff(str(a.get("dataset_id") or "")))
async def _t_ingest_read_impact(a, s, ag):    return await _call(datasets.get_dataset_impact(str(a.get("dataset_id") or "")))
async def _t_ingest_read_quality(a, s, ag):   return await _call(datasets.get_dataset_quality(str(a.get("dataset_id") or "")))
async def _t_ingest_approve(a, s, ag):
    return await _call(datasets.approve_dataset(str(a.get("dataset_id") or ""), datasets.ApprovalRequest(
        decision=str(a.get("decision") or ""), reviewer_notes=str(a.get("reviewer_notes") or ""))))


# ===========================================================================
# factory_ — model factory: plan → approve/train → leaderboard → package
# ===========================================================================
async def _t_factory_propose(a, s, ag):
    return await _call(factory_real.propose_plan(factory_real.ProposeRequest(
        family=str(a.get("family") or ""), max_variants=a.get("max_variants"))))
async def _t_factory_approve(a, s, ag):
    return await _call(factory_real.approve_and_train(factory_real.ApproveRequest(
        family=str(a.get("family") or ""), plan=a.get("plan") or [], narrative=a.get("narrative"))))
async def _t_factory_read_run(a, s, ag):         return await _call(factory_real.run_status(str(a.get("run_id") or "")))
async def _t_factory_read_leaderboard(a, s, ag): return await _call(factory_real.leaderboard(str(a.get("run_id") or "")))
async def _t_factory_read_shortlist(a, s, ag):   return await _call(factory_real.shortlist(str(a.get("run_id") or "")))
async def _t_factory_list_runs(a, s, ag):        return await _call(factory_real.list_runs(int(a.get("limit") or 10)))
async def _t_factory_package(a, s, ag):          return await _call(factory_real.generate_pack(str(a.get("run_id") or ""), str(a.get("variant_id") or "")))


# ===========================================================================
# mart_ — modelling mart / feature store
# ===========================================================================
async def _t_mart_read_catalog(a, s, ag):  return await _call(features.feature_catalog())
async def _t_mart_read_profile(a, s, ag):  return await _call(features.mart_profile())
async def _t_mart_read_sources(a, s, ag):  return await _call(features.feature_sources())
async def _t_mart_rebuild(a, s, ag):       return await _call(features.rebuild_feature_table())
async def _t_mart_online_promote(a, s, ag):return await _call(features.promote_online())
async def _t_mart_online_pause(a, s, ag):  return await _call(features.pause_online())


# ===========================================================================
# book_ / review_ — the live rate book, quote stream, model review
# ===========================================================================
async def _t_book_read_overview(a, s, ag):    return await _call(overview.overview())
async def _t_book_recent_quotes(a, s, ag):    return await _call(quote_stream.list_recent(int(a.get("limit") or 50)))
async def _t_book_quote_analytics(a, s, ag):  return await _call(quote_stream.analytics_summary())
async def _t_book_compare_scenarios(a, s, ag):return await _call(compare.list_scenarios(a.get("family")))
async def _t_review_list_families(a, s, ag):  return await _call(review.list_families())
async def _t_review_read_versions(a, s, ag):  return await _call(review.list_versions(str(a.get("family") or "")))
async def _t_review_explainability(a, s, ag):
    return await _call(review.version_explainability(str(a.get("family") or ""), str(a.get("version") or "")))
async def _t_review_generate_pack(a, s, ag):
    return await _call(review.generate_pack(review.GeneratePackRequest(
        family=str(a.get("family") or ""), version=str(a.get("version") or ""))))


# ---------------------------------------------------------------------------
# Schemas + impl registry
# ---------------------------------------------------------------------------
_FAMILY = {"family": {"type": "string", "description": "freq_glm | sev_glm | demand_gbm | fraud_gbm"}}

WORKBENCH_TOOL_SCHEMAS: list[dict[str, Any]] = [
    # price_
    _schema("price_run_quote", "Run a commercial risk through the live pricing engine (4 models + rating config) and return the technical→loaded→final premium breakdown. Provide a feature vector (use price_read_policy_context to fetch one for a known policy).",
            {"features": {"type": "object"}, "policy_id": {"type": "string"}, "rating_engine_version": {"type": "string"}}, ["features"]),
    _schema("price_mta_simulate", "Mid-term adjustment: re-price an in-force policy after a change (e.g. sum insured, cover, risk attributes) against the release live at inception. Returns before/after premium and the delta.",
            {"policy_id": {"type": "string"}, "changes": {"type": "object", "description": "field → new value"}, "effective_date": {"type": "string"}, "reason": {"type": "string"}}, ["policy_id", "changes"]),
    _schema("price_read_releases", "List the monthly rate-engine releases (the rolling rate book)."),
    _schema("price_read_current_release", "Read the live (champion) monthly rate-engine release."),
    _schema("price_read_release", "Read one release by id (e.g. aug_2026).", {"release_id": {"type": "string"}}, ["release_id"]),
    _schema("price_compare_releases", "Portfolio-level premium impact of a candidate release vs the current champion.",
            {"release_id": {"type": "string"}, "portfolio_size": {"type": "integer"}, "scenario_id": {"type": "string"}}, ["release_id"]),
    _schema("price_read_rating_config", "Read the active rating-engine config (loadings, commission, corridor)."),
    _schema("price_read_policy_context", "Fetch an in-force policy's inception/renewal context + feature row (feed into price_run_quote / price_mta_simulate).", {"policy_id": {"type": "string"}}, ["policy_id"]),
    _schema("price_read_model_versions", "List the model versions available to the pricing engine."),
    # deploy_
    _schema("deploy_read_champions", "Read the current champion version of each model family + governance-pack linkage."),
    _schema("deploy_read_history", "Promotion/rollback history for a model family.", _FAMILY, ["family"]),
    _schema("deploy_promote", "[gated] Set a family's champion alias to a version (admin-only; flips champion, demotes prior).", {**_FAMILY, "version": {"type": "string"}}, ["family", "version"]),
    _schema("deploy_rollback", "[gated] Roll a family's champion back to previous_champion with an audit-logged justification (admin-only).", {**_FAMILY, "note": {"type": "string", "description": "≥10 chars"}}, ["family", "note"]),
    _schema("deploy_cut_release", "[gated] Cut the commercial monthly rate-engine release — bundle the 4 champion models + active rating config into one release-of-record (admin-only).", {"note": {"type": "string"}, "effective_date": {"type": "string"}}),
    _schema("deploy_trigger_backfill", "[action] Re-score every in-force policy with the current champions (inference backfill)."),
    # gov_
    _schema("gov_read_summary", "Governance overview — pack counts, latest activity, audit posture."),
    _schema("gov_read_packs", "List generated governance packs (model / version / date / policy)."),
    _schema("gov_read_pack_text", "Extract the text of a governance pack for grounding.", {"pack_id": {"type": "string"}}, ["pack_id"]),
    _schema("gov_read_policy_scoring", "Reproduce how a specific policy was scored — the per-model contributions behind its premium.", {"policy_id": {"type": "string"}}, ["policy_id"]),
    _schema("gov_ask", "Ask the grounded governance agent a question across the packs + audit trail (regulator-facing defence).", {"question": {"type": "string"}}, ["question"]),
    _schema("gov_read_bias", "Read the bias / fair-treatment monitor across protected-attribute proxies."),
    _schema("gov_bias_investigate", "Investigate a bias finding with the grounded agent.", {"question": {"type": "string"}, "protected_attribute": {"type": "string"}, "family": {"type": "string"}}, ["question"]),
    _schema("gov_read_adequacy", "Read the premium-adequacy monitor (loss-ratio spread by cohort).", {"cohort_dimension": {"type": "string"}}),
    _schema("gov_adequacy_investigate", "Investigate a premium-adequacy finding with the grounded agent.", {"question": {"type": "string"}, "cohort_dimension": {"type": "string"}}, ["question"]),
    # ingest_
    _schema("ingest_read_datasets", "List every data source feeding pricing — internal book, vendor feeds, reference data — with row counts, last-ingested and approval state."),
    _schema("ingest_read_diff", "New / changed / removed rows in a dataset's pending vs approved version.", {"dataset_id": {"type": "string"}}, ["dataset_id"]),
    _schema("ingest_read_impact", "Pricing impact of adopting a dataset's pending version (premium + risk-selection change).", {"dataset_id": {"type": "string"}}, ["dataset_id"]),
    _schema("ingest_read_quality", "Data-quality profile of a dataset (completeness, DQ drops).", {"dataset_id": {"type": "string"}}, ["dataset_id"]),
    _schema("ingest_approve", "[action] The actuary approval gate — approve or reject a vendor feed before it can feed pricing (audit-logged).", {"dataset_id": {"type": "string"}, "decision": {"type": "string", "enum": ["approved", "rejected"]}, "reviewer_notes": {"type": "string"}}, ["dataset_id", "decision"]),
    # factory_
    _schema("factory_propose", "Propose a factory run — AI generates candidate model-variant specs for a family.", _FAMILY, ["family"]),
    _schema("factory_approve", "[action] Approve a proposed plan and train the variants.", {**_FAMILY, "plan": {"type": "array"}, "narrative": {"type": "string"}}, ["family", "plan"]),
    _schema("factory_read_run", "Status of a factory run.", {"run_id": {"type": "string"}}, ["run_id"]),
    _schema("factory_read_leaderboard", "Ranked variants for a factory run (Gini etc.).", {"run_id": {"type": "string"}}, ["run_id"]),
    _schema("factory_read_shortlist", "The shortlisted variants for a factory run.", {"run_id": {"type": "string"}}, ["run_id"]),
    _schema("factory_list_runs", "Recent factory runs.", {"limit": {"type": "integer"}}),
    _schema("factory_package", "[action] Package a variant into a governance pack for review.", {"run_id": {"type": "string"}, "variant_id": {"type": "string"}}, ["run_id", "variant_id"]),
    # mart_
    _schema("mart_read_catalog", "The feature catalog — every factor in the modelling mart with provenance."),
    _schema("mart_read_profile", "Profile of the modelling mart (rows, coverage, key stats)."),
    _schema("mart_read_sources", "The approved sources joined into the mart."),
    _schema("mart_rebuild", "[action] Rebuild the modelling-mart feature table from the approved sources."),
    _schema("mart_online_promote", "[action] Promote features to the online store (arm the low-latency serving tier)."),
    _schema("mart_online_pause", "[action] Pause / tear down the online feature store (scale to zero)."),
    # book_ / review_
    _schema("book_read_overview", "The live rate book + portfolio KPIs (the Home control-tower view)."),
    _schema("book_recent_quotes", "Recent quote-stream transactions.", {"limit": {"type": "integer"}}),
    _schema("book_quote_analytics", "Quote-stream analytics — conversion, outliers, funnel."),
    _schema("book_compare_scenarios", "Available model-comparison scenarios.", {"family": {"type": "string"}}),
    _schema("review_list_families", "Model families available for review & promotion."),
    _schema("review_read_versions", "Registered versions of a model family.", _FAMILY, ["family"]),
    _schema("review_explainability", "Explainability (feature importance / relativities) for a model version.", {**_FAMILY, "version": {"type": "string"}}, ["family", "version"]),
    _schema("review_generate_pack", "[action] Generate a governance pack for a model version.", {**_FAMILY, "version": {"type": "string"}}, ["family", "version"]),
]

WORKBENCH_TOOL_IMPLS: dict[str, Any] = {
    "price_run_quote": _t_price_run_quote, "price_mta_simulate": _t_price_mta_simulate,
    "price_read_releases": _t_price_read_releases, "price_read_current_release": _t_price_read_current_release,
    "price_read_release": _t_price_read_release, "price_compare_releases": _t_price_compare_releases,
    "price_read_rating_config": _t_price_read_rating_config, "price_read_policy_context": _t_price_read_policy_context,
    "price_read_model_versions": _t_price_read_model_versions,
    "deploy_read_champions": _t_deploy_read_champions, "deploy_read_history": _t_deploy_read_history,
    "deploy_promote": _t_deploy_promote, "deploy_rollback": _t_deploy_rollback,
    "deploy_cut_release": _t_deploy_cut_release, "deploy_trigger_backfill": _t_deploy_backfill,
    "gov_read_summary": _t_gov_read_summary, "gov_read_packs": _t_gov_read_packs,
    "gov_read_pack_text": _t_gov_read_pack_text, "gov_read_policy_scoring": _t_gov_read_policy_scoring,
    "gov_ask": _t_gov_ask, "gov_read_bias": _t_gov_read_bias, "gov_bias_investigate": _t_gov_bias_investigate,
    "gov_read_adequacy": _t_gov_read_adequacy, "gov_adequacy_investigate": _t_gov_adequacy_investigate,
    "ingest_read_datasets": _t_ingest_read_datasets, "ingest_read_diff": _t_ingest_read_diff,
    "ingest_read_impact": _t_ingest_read_impact, "ingest_read_quality": _t_ingest_read_quality,
    "ingest_approve": _t_ingest_approve,
    "factory_propose": _t_factory_propose, "factory_approve": _t_factory_approve,
    "factory_read_run": _t_factory_read_run, "factory_read_leaderboard": _t_factory_read_leaderboard,
    "factory_read_shortlist": _t_factory_read_shortlist, "factory_list_runs": _t_factory_list_runs,
    "factory_package": _t_factory_package,
    "mart_read_catalog": _t_mart_read_catalog, "mart_read_profile": _t_mart_read_profile,
    "mart_read_sources": _t_mart_read_sources, "mart_rebuild": _t_mart_rebuild,
    "mart_online_promote": _t_mart_online_promote, "mart_online_pause": _t_mart_online_pause,
    "book_read_overview": _t_book_read_overview, "book_recent_quotes": _t_book_recent_quotes,
    "book_quote_analytics": _t_book_quote_analytics, "book_compare_scenarios": _t_book_compare_scenarios,
    "review_list_families": _t_review_list_families, "review_read_versions": _t_review_read_versions,
    "review_explainability": _t_review_explainability, "review_generate_pack": _t_review_generate_pack,
}
