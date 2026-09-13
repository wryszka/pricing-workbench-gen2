"""A small, versioned **synthetic business-evidence pack** (WP4).

The distinctive Decision-Review demonstration connects the pricing decision to evidence
that lives *outside* the optimiser — claims experience, a finance planning assumption,
and a distribution/customer-outcome summary. Each item carries the provenance a
reviewer needs to judge it: an id, the owning function, observation/effective dates, the
population it maps to, its denominator/sample size, a definition, a synthetic label and a
known limitation. Sources are related (finance's assumption is informed by the same book
as claims), and that relationship is recorded so correlated estimates are never counted
as independent corroboration.

This module is the canonical definition (pure, no Spark/LLM); a job persists it to a
governed Delta table for the app to read, and the pack is hashed so a review can be tied
to the exact evidence it saw. Raw customer rows never appear here — only aggregates.

Reproducible filming case: the included claims **cost stress is +5%** (`cost_scale`
1.05); a separate, comparable finance **planning assumption is +8%** for the same horizon
and population. The evidence adapter (see :mod:`decision_review`) deterministically detects
that +8% lies outside the included claims stresses and lets the reviewer draft that stress
— while stating that a planning assumption is not proof of future claims inflation.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

PACK_VERSION = "biz-evidence-v1"

# Every value is synthetic and labelled. `kind` drives how the fact layer reads it:
#   claims_experience      — observed claims data (a rate/ratio)
#   finance_cost_assumption— a forward planning assumption (NOT observed experience)
#   distribution_outcome   — a customer-outcome / distribution summary
_ITEMS: list[dict[str, Any]] = [
    {
        "evidence_id": "CLAIMS-MOTOR-2026H1",
        "kind": "claims_experience",
        "title": "Motor claims severity trend, H1 2026",
        "source_owner": "Claims Analytics",
        "observation_date": "2026-06-30",
        "effective_date": "2026-01-01",
        "population_mapping": "motor_new_business_all_segments",
        "denominator": 48213,          # claims observations behind the trend
        "sample_size": 48213,
        "definition": "Year-on-year change in average incurred claim severity, motor NB.",
        "value": {"metric": "severity_trend", "annual_multiplier": 1.05},
        "synthetic": True,
        "known_limitation": "Half-year view; large-loss volatility not fully credible at segment level.",
        "related_to": [],
    },
    {
        "evidence_id": "FIN-PLAN-CLAIMSINFL-2026",
        "kind": "finance_cost_assumption",
        "title": "Finance planning assumption — claims inflation 2026",
        "source_owner": "Finance Planning",
        "observation_date": "2026-05-15",
        "effective_date": "2026-01-01",
        "population_mapping": "motor_new_business_all_segments",
        "denominator": None,            # a planning assumption, not an observation
        "sample_size": None,
        "definition": "Planning claims-inflation assumption used in the 2026 cost plan, same horizon/population.",
        "value": {"metric": "claims_inflation", "annual_multiplier": 1.08},
        "synthetic": True,
        "known_limitation": "A planning assumption, NOT observed experience; set for prudence and budgeting.",
        # Informed by the same book as the claims trend — correlated, not independent.
        "related_to": ["CLAIMS-MOTOR-2026H1"],
    },
    {
        "evidence_id": "DIST-OUTCOME-OLDER-2026H1",
        "kind": "distribution_outcome",
        "title": "Customer-outcome summary — older-driver segment",
        "source_owner": "Conduct & Distribution",
        "observation_date": "2026-06-30",
        "effective_date": "2026-01-01",
        "population_mapping": "segment:70+",           # narrower population than the plans
        "denominator": 3120,
        "sample_size": 3120,
        "definition": "Complaint rate and shopping-around index for the 70+ segment.",
        "value": {"complaint_rate": 0.011, "shopping_index": 0.34},
        "synthetic": True,
        "known_limitation": "Segment-level; outcome signals are lagging and partly self-reported.",
        "related_to": [],
    },
]


def evidence_pack() -> dict[str, Any]:
    """The canonical pack (version + items). Pure; safe to import anywhere."""
    return {"pack_version": PACK_VERSION, "items": [dict(i) for i in _ITEMS]}


def pack_hash(pack: dict[str, Any] | None = None) -> str:
    """Stable content hash so a review can be tied to the exact evidence it saw."""
    pack = pack or evidence_pack()
    return hashlib.sha256(
        json.dumps(pack, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def get_item(evidence_id: str) -> dict[str, Any] | None:
    for i in _ITEMS:
        if i["evidence_id"] == evidence_id:
            return dict(i)
    return None
