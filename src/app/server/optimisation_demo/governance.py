"""Chapter 2 governance — deterministic recompute + content hashes (pure).

Before a plan is approved it is independently recomputed from the stored candidate
scores — never trusting a UI value or a stored boolean. This module has no DB/UI
imports; the job and route call it and enforce the result.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional


def content_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def policy_hash(policy: dict[str, Any]) -> str:
    return content_hash(policy)


def plan_hash(selection: dict[str, float]) -> str:
    """Hash the selected factor per segment (order-independent, rounded)."""
    return content_hash({k: round(float(v), 6) for k, v in sorted(selection.items())})


def recompute_and_validate(
    segments: list[str],
    selection: dict[str, float],
    coeffs: dict[tuple[str, float], dict[str, float]],
    min_portfolio_sales: Optional[float] = None,
) -> dict[str, Any]:
    """Re-derive totals + feasibility from the stored scores. Returns ok/failures/totals.

    Checks: exactly one permissible factor per segment; complete segment coverage;
    the portfolio sales floor holds on the UNROUNDED total. Reject empty/partial/
    mismatched plans.
    """
    failures: list[str] = []
    if not selection:
        return {"ok": False, "failures": ["empty plan"], "totals": None}
    if set(selection.keys()) != set(segments):
        missing = sorted(set(segments) - set(selection))
        extra = sorted(set(selection) - set(segments))
        failures.append(f"plan coverage mismatch (missing {missing}, extra {extra})")

    total_sales = total_margin = 0.0
    for s in segments:
        f = selection.get(s)
        key = (s, round(float(f), 4)) if f is not None else None
        if key is None or key not in coeffs:
            failures.append(f"segment {s}: chosen factor {f} is not a scored candidate")
            continue
        total_sales += coeffs[key]["expected_sales"]
        total_margin += coeffs[key]["expected_margin"]

    if min_portfolio_sales is not None and total_sales < float(min_portfolio_sales) - 1e-6:
        failures.append(f"expected sales {total_sales:.2f} below the floor {float(min_portfolio_sales):.2f}")

    return {"ok": len(failures) == 0, "failures": failures,
            "totals": {"total_sales": round(total_sales, 6), "total_margin": round(total_margin, 2)}}
