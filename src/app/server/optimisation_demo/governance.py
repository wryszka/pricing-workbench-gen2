"""Chapter 2 governance — deterministic recompute + content hashes (pure).

Before a plan is approved it is independently recomputed from the stored candidate
scores — never trusting a UI value or a stored boolean. This module has no DB/UI
imports; the job and route call it and enforce the result.

Canonical serialization (:func:`content_hash`) is the trust boundary for the plan
hash: the run job computes it over the solver's selection and stores it on the run
row; the approval procedure compares a caller-supplied hash to that stored value and
rejects a mismatch, so a direct caller cannot approve a plan the validated job never
produced.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Optional

from server.optimisation_demo import coerce


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


def build_and_validate_from_rows(
    score_rows: Iterable[dict[str, Any]],
    expected_segments: list[str],
    min_portfolio_sales: Optional[float] = None,
) -> dict[str, Any]:
    """Strict boundary: build the coefficient table + selection from RAW stored score
    rows and validate against the segments the run was *supposed* to cover.

    Rejects, before any dictionary is constructed (which would silently overwrite a
    collision):

    * duplicate candidate keys — the same (segment, factor) scored twice;
    * duplicate selections — more than one selected candidate for a segment;
    * a `selected` value that isn't a real boolean (no string-truthiness);
    * a selection whose segment set doesn't equal ``expected_segments`` (established
      from the input/model manifest, NOT inferred from the rows being checked).

    On any structural failure it returns ``ok=False`` with reasons and no totals — an
    empty ``expected_segments`` is itself a failure (nothing to approve).
    """
    failures: list[str] = []
    expected = set(expected_segments)
    if not expected:
        return {"ok": False, "failures": ["no expected segments from manifest"], "totals": None,
                "selection": {}, "plan_hash": None}

    coeffs: dict[tuple[str, float], dict[str, float]] = {}
    selection: dict[str, float] = {}
    seen_keys: set[tuple[str, float]] = set()
    selected_count: dict[str, int] = {}

    for i, row in enumerate(score_rows):
        try:
            seg = coerce.as_str(coerce.require(row, "segment"), field=f"row{i}.segment")
            factor = round(coerce.as_float(coerce.require(row, "factor"), field=f"row{i}.factor"), 4)
            key = (seg, factor)
            if key in seen_keys:
                failures.append(f"duplicate candidate key {key}")
                continue
            seen_keys.add(key)
            coeffs[key] = {
                "expected_sales": coerce.as_float(coerce.require(row, "expected_sales"), field=f"row{i}.expected_sales"),
                "expected_margin": coerce.as_float(coerce.require(row, "expected_margin"), field=f"row{i}.expected_margin"),
            }
            if coerce.as_bool(coerce.require(row, "selected"), field=f"row{i}.selected"):
                selected_count[seg] = selected_count.get(seg, 0) + 1
                selection[seg] = factor
        except coerce.CoercionError as e:
            failures.append(str(e))

    dupes = sorted(s for s, n in selected_count.items() if n > 1)
    if dupes:
        failures.append(f"duplicate selections for segment(s) {dupes}")

    if failures:
        return {"ok": False, "failures": failures, "totals": None,
                "selection": {}, "plan_hash": None}

    check = recompute_and_validate(list(expected), selection, coeffs, min_portfolio_sales)
    check["selection"] = selection
    check["plan_hash"] = plan_hash(selection) if check["ok"] else None
    return check
