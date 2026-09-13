"""WP4 Decision-Review deterministic fact layer + business-evidence pack.

Covers the deterministic evaluation cases from the brief: the omitted +8% assumption,
incompatible populations, correlated (non-independent) sources, model disagreement,
the robust/nominal trade-off computed from one matrix, constraint slack, challenge
ranking (≤3), and stable inference labels. No LLM involved."""
import pytest

from server.optimisation_demo import business_evidence as be
from server.optimisation_demo import decision_review as dr


# --- Evidence pack --- #

def test_evidence_pack_versioned_and_hashed():
    pack = be.evidence_pack()
    assert pack["pack_version"] == "biz-evidence-v1"
    assert be.pack_hash(pack) == be.pack_hash()          # stable
    ids = {i["evidence_id"] for i in pack["items"]}
    assert {"CLAIMS-MOTOR-2026H1", "FIN-PLAN-CLAIMSINFL-2026", "DIST-OUTCOME-OLDER-2026H1"} <= ids
    for i in pack["items"]:
        assert i["synthetic"] is True and i["known_limitation"]
        assert "population_mapping" in i and "observation_date" in i


def test_finance_assumption_flagged_not_experience():
    fin = be.get_item("FIN-PLAN-CLAIMSINFL-2026")
    assert fin["kind"] == "finance_cost_assumption"
    assert fin["denominator"] is None                    # a plan, not an observation
    assert "CLAIMS-MOTOR-2026H1" in fin["related_to"]    # correlated with claims


# --- Headline: +8% lies outside the included +5% claims stress --- #

def test_scenario_coverage_gap_detects_uncovered_assumption():
    fin = be.get_item("FIN-PLAN-CLAIMSINFL-2026")
    f = dr.scenario_coverage_gap([1.00, 1.05], fin)
    assert f["value"]["covered"] is False
    assert f["value"]["gap"] == pytest.approx(0.03)
    assert f["drafted_stress"] == {"cost_scale": 1.08}
    assert f["assumption_not_experience"] is True
    assert "not proof" in f["caveat"]
    assert f["inference"] == "inference"
    assert "FIN-PLAN-CLAIMSINFL-2026" in f["evidence_refs"]


def test_scenario_coverage_gap_covered_when_included():
    fin = be.get_item("FIN-PLAN-CLAIMSINFL-2026")
    f = dr.scenario_coverage_gap([1.00, 1.05, 1.08, 1.10], fin)
    assert f["value"]["covered"] is True
    assert f["drafted_stress"] is None


# --- Source compatibility --- #

def test_incompatible_populations_not_comparable():
    a = be.get_item("CLAIMS-MOTOR-2026H1")               # all segments
    b = be.get_item("DIST-OUTCOME-OLDER-2026H1")         # 70+ only
    f = dr.source_compatibility(a, b)
    assert f["value"]["population_match"] is False
    assert f["compatible"] is False


def test_correlated_sources_not_independent_corroboration():
    a = be.get_item("CLAIMS-MOTOR-2026H1")
    b = be.get_item("FIN-PLAN-CLAIMSINFL-2026")          # related_to claims
    f = dr.source_compatibility(a, b)
    assert f["value"]["correlated"] is True
    assert f["value"]["independent_corroboration"] is False


def test_outdated_evidence_flagged():
    a = be.get_item("CLAIMS-MOTOR-2026H1")               # observed 2026-06-30
    b = be.get_item("FIN-PLAN-CLAIMSINFL-2026")
    f = dr.source_compatibility(a, b, as_of="2027-09-01", stale_days=365)
    assert f["value"]["stale_a"] is True                 # >365 days old


# --- Constraint slack / disagreement / trade-off --- #

def test_constraint_slack_binding_and_not():
    assert dr.constraint_slack(3660.0, 3660.0)["binding"] is True
    nb = dr.constraint_slack(3900.0, 3660.0)
    assert nb["binding"] is False and nb["value"] == pytest.approx(240.0)
    assert dr.constraint_slack(3900.0, None)["binding"] is False


def test_model_disagreement_spread():
    f = dr.model_disagreement({"logit": 90.0, "gbt": 96.0})
    assert f["value"] == pytest.approx(6.0)
    assert f["highest_model"] == "gbt" and f["lowest_model"] == "logit"
    assert dr.model_disagreement({"only": 1.0})["value"] == 0.0


def test_robust_nominal_tradeoff_two_distinct_quantities():
    # robust holds up in the worst world; nominal wins its own best world.
    robust = {"w_base": 100.0, "w_stress": 80.0}
    nominal = {"w_base": 120.0, "w_stress": 60.0}
    f = dr.robust_vs_nominal_tradeoff(robust, nominal)
    # worst-world benefit = robust_worst(80) − nominal_worst(60) = 20
    assert f["value"]["worst_world_benefit"] == pytest.approx(20.0)
    # nominal's best world is w_base; sacrifice there = 120 − 100 = 20
    assert f["value"]["nominal_world_sacrifice"] == pytest.approx(20.0)
    assert f["nominal_best_world"] == "w_base"


# --- Challenge ranking --- #

def test_rank_challenges_prioritises_and_caps_three():
    fin = be.get_item("FIN-PLAN-CLAIMSINFL-2026")
    facts = [
        dr.scenario_coverage_gap([1.00, 1.05], fin),                       # tier 3, uncovered
        dr.robust_vs_nominal_tradeoff({"a": 100.0, "b": 80.0}, {"a": 120.0, "b": 60.0}),  # tier 2
        dr.model_disagreement({"logit": 90.0, "gbt": 96.0}),               # tier 2
        dr.constraint_slack(3660.0, 3660.0),                               # tier 1 binding
        dr.source_compatibility(be.get_item("CLAIMS-MOTOR-2026H1"),
                                be.get_item("FIN-PLAN-CLAIMSINFL-2026")),  # tier 1 correlated
    ]
    ranked = dr.rank_challenges(facts, limit=3)
    assert len(ranked) == 3
    assert ranked[0]["fact_id"] == "coverage.claims_stress"               # highest tier first


def test_rank_challenges_drops_non_issues():
    fin = be.get_item("FIN-PLAN-CLAIMSINFL-2026")
    facts = [
        dr.scenario_coverage_gap([1.00, 1.05, 1.10], fin),   # covered → dropped
        dr.constraint_slack(3900.0, 3660.0),                 # not binding → dropped
        dr.model_disagreement({"only": 1.0}),                # zero → dropped
    ]
    assert dr.rank_challenges(facts) == []


def test_fact_rejects_bad_inference_label():
    with pytest.raises(ValueError):
        dr.fact("x", 1, "guess", "bad label")
