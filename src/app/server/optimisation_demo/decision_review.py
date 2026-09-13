"""Decision-Review deterministic fact layer (WP4).

The review assistant is only ever *narration on top of deterministic facts*. This module
computes those facts — money, counts, constraint slack, model disagreement, scenario
coverage and source compatibility — each as a structured record with a stable ``fact_id``,
a numeric ``value`` and an ``inference`` label that never blurs the three things a reviewer
must keep apart:

* ``observed_data``  — measured, from data or evidence;
* ``model_output``   — a model's prediction/selection;
* ``inference``      — a computed consequence or comparison (still deterministic here).

The LLM sits above this: it may phrase a fact and pose a question, but every numeric claim
it makes is validated back against these fact values, and a narration failure never changes
a computation or an approval. All functions are pure (no Spark/LLM/DB), so they are unit
tested off-platform and reused by the API route and the tools.

The headline demonstration is :func:`scenario_coverage_gap`: it detects that a finance
planning assumption (+8% claims inflation) lies **outside** the claims stresses actually
included in the run (+5%), and hands the reviewer a drafted stress — while labelling the
planning number an assumption, not observed experience.
"""
from __future__ import annotations

from typing import Any, Optional

INFERENCE_KINDS = ("observed_data", "model_output", "inference")


def fact(fact_id: str, value: Any, inference: str, summary: str,
         evidence_refs: Optional[list[str]] = None, **extra: Any) -> dict[str, Any]:
    """Build one structured fact. `inference` must be one of INFERENCE_KINDS."""
    if inference not in INFERENCE_KINDS:
        raise ValueError(f"inference must be one of {INFERENCE_KINDS}, got {inference!r}")
    rec = {"fact_id": fact_id, "value": value, "inference": inference,
           "summary": summary, "evidence_refs": list(evidence_refs or [])}
    rec.update(extra)
    return rec


# --------------------------------------------------------------------------- #
# Constraint slack — is the portfolio sales floor binding, and by how much?
# --------------------------------------------------------------------------- #
def constraint_slack(total_expected_sales: float, floor: Optional[float]) -> dict[str, Any]:
    """Slack on the portfolio sales floor. Binding iff slack ≈ 0.

    A constraint is only called 'binding' with a computed slack — never asserted."""
    if floor is None:
        return fact("slack.sales_floor", None, "inference", "No sales floor in this run.",
                    binding=False)
    slack = float(total_expected_sales) - float(floor)
    binding = abs(slack) <= max(1.0, 1e-6 * abs(float(floor)))  # within ~1 expected sale
    return fact("slack.sales_floor", round(slack, 4), "inference",
                (f"Sales floor {'binding' if binding else 'not binding'}: expected sales exceed the "
                 f"floor by {slack:.1f}."),
                binding=bool(binding), floor=float(floor),
                total_expected_sales=float(total_expected_sales))


# --------------------------------------------------------------------------- #
# Model disagreement — where do the demand models most diverge?
# --------------------------------------------------------------------------- #
def model_disagreement(predictions_by_model: dict[str, float]) -> dict[str, Any]:
    """Spread across model predictions at a point (e.g. expected sales for a segment).

    Returns the absolute spread (max − min) as a deterministic `inference`."""
    vals = {m: float(v) for m, v in predictions_by_model.items()}
    if len(vals) < 2:
        return fact("disagreement.models", 0.0, "inference",
                    "Only one model — no disagreement to report.", n_models=len(vals))
    hi_m = max(vals, key=vals.get)
    lo_m = min(vals, key=vals.get)
    spread = vals[hi_m] - vals[lo_m]
    return fact("disagreement.models", round(spread, 6), "inference",
                f"Models disagree by {spread:.3g} (highest {hi_m}, lowest {lo_m}).",
                highest_model=hi_m, lowest_model=lo_m, values=vals)


# --------------------------------------------------------------------------- #
# Robust vs nominal trade-off — WP3#6 (from ONE comparison matrix)
# --------------------------------------------------------------------------- #
def robust_vs_nominal_tradeoff(
    robust_by_world: dict[str, float],
    nominal_by_world: dict[str, float],
) -> dict[str, Any]:
    """Worst-world benefit AND nominal-world sacrifice, computed explicitly from the same
    per-world uplift matrices. The *worst-world benefit* is robust_worst − nominal_worst;
    the *nominal-world sacrifice* is the margin the robust plan gives up in the world the
    nominal plan optimises for. These are different quantities — never label the gap
    between two worst-world numbers the 'cost of insurance'."""
    worlds = sorted(set(robust_by_world) & set(nominal_by_world))
    if not worlds:
        return fact("tradeoff.robust_nominal", None, "inference", "No shared worlds to compare.")
    robust_worst = min(robust_by_world[w] for w in worlds)
    nominal_worst = min(nominal_by_world[w] for w in worlds)
    worst_world_benefit = robust_worst - nominal_worst
    # The world the nominal plan does best in = the world it optimises for.
    nominal_best_world = max(worlds, key=lambda w: nominal_by_world[w])
    nominal_world_sacrifice = nominal_by_world[nominal_best_world] - robust_by_world[nominal_best_world]
    return fact("tradeoff.robust_nominal",
                {"worst_world_benefit": round(worst_world_benefit, 4),
                 "nominal_world_sacrifice": round(nominal_world_sacrifice, 4)},
                "inference",
                (f"Worst-world benefit of robust vs nominal: {worst_world_benefit:.0f}. "
                 f"Nominal-world sacrifice (in {nominal_best_world}): {nominal_world_sacrifice:.0f}."),
                robust_worst=round(robust_worst, 4), nominal_worst=round(nominal_worst, 4),
                nominal_best_world=nominal_best_world)


# --------------------------------------------------------------------------- #
# Scenario coverage — the headline: an external assumption outside the included stresses
# --------------------------------------------------------------------------- #
def scenario_coverage_gap(
    included_claims_stresses: list[float],
    external_assumption: dict[str, Any],
    tol: float = 1e-9,
) -> dict[str, Any]:
    """Detect whether an external claims-cost assumption lies OUTSIDE the run's included
    claims stresses (given as cost multipliers, e.g. [1.00, 1.05]).

    `external_assumption` carries at least `annual_multiplier` and provenance fields. If the
    assumption exceeds the largest included stress (beyond `tol`), it is uncovered and we
    draft the stress — but the fact records that a planning assumption is not observed
    claims inflation."""
    included = sorted(float(x) for x in included_claims_stresses)
    # The multiplier may be top-level or nested under an evidence item's `value`.
    _v = external_assumption.get("value")
    if isinstance(_v, dict) and "annual_multiplier" in _v:
        ext = float(_v["annual_multiplier"])
    else:
        ext = float(external_assumption["annual_multiplier"])
    hi = max(included) if included else 1.0
    covered = ext <= hi + tol
    is_assumption = external_assumption.get("kind") == "finance_cost_assumption"
    gap = round(ext - hi, 6)
    return fact(
        "coverage.claims_stress",
        {"external_multiplier": ext, "max_included_multiplier": hi, "gap": gap, "covered": covered},
        # This is an inference about coverage; the external number's own status is separate.
        "inference",
        (f"Included claims stresses top out at {(hi-1)*100:.0f}%; the external assumption is "
         f"{(ext-1)*100:.0f}% — {'covered' if covered else 'NOT covered'}."),
        evidence_refs=[external_assumption["evidence_id"]] if external_assumption.get("evidence_id") else [],
        covered=covered,
        drafted_stress=(None if covered else {"cost_scale": ext}),
        assumption_not_experience=bool(is_assumption),
        caveat=("A finance planning assumption is not proof of future claims inflation."
                if is_assumption else "External claims-experience figure."),
    )


# --------------------------------------------------------------------------- #
# Source compatibility — can two evidence items be compared / corroborate?
# --------------------------------------------------------------------------- #
def source_compatibility(item_a: dict[str, Any], item_b: dict[str, Any],
                         as_of: Optional[str] = None, stale_days: int = 365) -> dict[str, Any]:
    """Population / recency / independence compatibility between two evidence items.

    Flags: population mismatch (can't compare directly); a correlated relationship
    (`related_to`) so the two are NOT independent corroboration; and staleness of either
    observation date relative to `as_of`."""
    from datetime import date

    pop_match = item_a.get("population_mapping") == item_b.get("population_mapping")
    correlated = (item_b.get("evidence_id") in (item_a.get("related_to") or [])
                  or item_a.get("evidence_id") in (item_b.get("related_to") or []))

    def _stale(item: dict[str, Any]) -> Optional[bool]:
        od = item.get("observation_date")
        if not od or not as_of:
            return None
        try:
            d0 = date.fromisoformat(od)
            d1 = date.fromisoformat(as_of)
            return (d1 - d0).days > stale_days
        except ValueError:
            return None

    stale_a, stale_b = _stale(item_a), _stale(item_b)
    compatible = pop_match and not correlated
    return fact(
        "compatibility.sources",
        {"population_match": pop_match, "correlated": correlated,
         "stale_a": stale_a, "stale_b": stale_b, "independent_corroboration": (pop_match and not correlated)},
        "inference",
        ("Same population; independent — may corroborate." if compatible else
         ("Correlated sources — NOT independent corroboration." if correlated else
          "Different populations — not directly comparable.")),
        evidence_refs=[i for i in (item_a.get("evidence_id"), item_b.get("evidence_id")) if i],
        compatible=bool(compatible),
    )


# --------------------------------------------------------------------------- #
# Challenge ranking — deterministic, evidence-based priority; at most three
# --------------------------------------------------------------------------- #
# Higher tier = more material. The rule is fixed and explainable, never LLM-decided.
_TIER = {
    "coverage.claims_stress": 3,     # an omitted, material, comparable assumption
    "tradeoff.robust_nominal": 2,
    "disagreement.models": 2,
    "slack.sales_floor": 1,
    "compatibility.sources": 1,
}


def _magnitude(f: dict[str, Any]) -> float:
    """A deterministic magnitude used only to order within a tier."""
    fid, v = f["fact_id"], f.get("value")
    try:
        if fid == "coverage.claims_stress":
            return 0.0 if v.get("covered") else abs(float(v.get("gap", 0.0)))
        if fid == "tradeoff.robust_nominal":
            return abs(float(v.get("nominal_world_sacrifice", 0.0)))
        if fid == "disagreement.models":
            return abs(float(v))
        if fid == "slack.sales_floor":
            # A binding (near-zero-slack) floor is more material → invert.
            return 1.0 / (1.0 + abs(float(v))) if v is not None else 0.0
        if fid == "compatibility.sources":
            return 1.0 if (v and v.get("correlated")) else 0.0
    except (TypeError, ValueError, AttributeError):
        return 0.0
    return 0.0


def rank_challenges(candidate_facts: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    """Return at most `limit` material challenges, most material first.

    Priority = (tier, magnitude). Facts that carry no live concern are dropped: a covered
    coverage gap, a non-binding floor with large slack, compatible sources, zero
    disagreement. The rule is deterministic so the same evidence always yields the same
    ranking — the LLM never decides ordering."""
    scored = []
    for f in candidate_facts:
        fid = f["fact_id"]
        v = f.get("value")
        # Drop non-issues.
        if fid == "coverage.claims_stress" and (v is None or v.get("covered")):
            continue
        if fid == "slack.sales_floor" and (v is None or not f.get("binding")):
            continue
        if fid == "disagreement.models" and (not v):
            continue
        if fid == "compatibility.sources" and (v is None or not v.get("correlated")):
            continue
        if fid == "tradeoff.robust_nominal" and v is None:
            continue
        scored.append((_TIER.get(fid, 0), _magnitude(f), f))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [f for _, _, f in scored[:limit]]
