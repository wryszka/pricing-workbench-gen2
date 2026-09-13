"""Chapter 2 governance — deterministic recompute rejects bad plans; hashes are stable."""
from server.optimisation_demo.economics import segment_candidate_coefficients
from server.optimisation_demo.governance import (
    recompute_and_validate, plan_hash, policy_hash, content_hash,
    build_and_validate_from_rows,
)

FIXTURE = {
    "candidate_prices": [1000.0, 1050.0, 1100.0],
    "modelled_variable_cost_per_sale": 800.0,
    "segments": [
        {"segment": "A", "opportunities": 1000, "purchase_probabilities": [0.75, 0.74, 0.70]},
        {"segment": "B", "opportunities": 1000, "purchase_probabilities": [0.70, 0.56, 0.40]},
        {"segment": "C", "opportunities": 1000, "purchase_probabilities": [0.80, 0.72, 0.60]},
    ],
}
SEGS = ["A", "B", "C"]
COEFFS = segment_candidate_coefficients(FIXTURE)


def test_valid_plan_recomputes():
    plan = {"A": 1100.0, "B": 1000.0, "C": 1050.0}   # the margin-first plan
    r = recompute_and_validate(SEGS, plan, COEFFS)
    assert r["ok"]
    assert r["totals"]["total_sales"] == 2120.0
    assert r["totals"]["total_margin"] == 530000.0


def test_partial_plan_rejected():
    r = recompute_and_validate(SEGS, {"A": 1100.0, "B": 1000.0}, COEFFS)
    assert not r["ok"] and any("coverage" in f for f in r["failures"])


def test_factor_not_scored_rejected():
    r = recompute_and_validate(SEGS, {"A": 999.0, "B": 1000.0, "C": 1050.0}, COEFFS)
    assert not r["ok"] and any("not a scored candidate" in f for f in r["failures"])


def test_sales_floor_enforced_on_recompute():
    plan = {"A": 1100.0, "B": 1000.0, "C": 1050.0}   # 2,120 sales
    r = recompute_and_validate(SEGS, plan, COEFFS, min_portfolio_sales=2200)
    assert not r["ok"] and any("below the floor" in f for f in r["failures"])


def test_empty_plan_rejected():
    assert not recompute_and_validate(SEGS, {}, COEFFS)["ok"]


def test_hashes_stable_and_order_independent():
    assert plan_hash({"A": 1.0, "B": 1.05}) == plan_hash({"B": 1.05, "A": 1.0})
    assert plan_hash({"A": 1.0}) != plan_hash({"A": 1.05})
    assert policy_hash({"objective": "maximise_expected_margin"}) == content_hash({"objective": "maximise_expected_margin"})


# --- WP2: strict builder from RAW stored rows (SQL strings, dup/coverage checks) --- #

def _row(seg, factor, sales, margin, selected):
    # As the SQL statement API returns them: everything a STRING (booleans "true"/"false").
    return {"segment": seg, "factor": str(factor), "expected_sales": str(sales),
            "expected_margin": str(margin), "selected": ("true" if selected else "false")}


def _grid(selected_by_seg):
    """Two-factor grid for A/B/C; `selected_by_seg` maps segment -> chosen factor."""
    rows = []
    for seg in ("A", "B", "C"):
        for f, (s, m) in {1.0: (750.0, 150000.0), 1.05: (700.0, 175000.0)}.items():
            rows.append(_row(seg, f, s, m, selected=(selected_by_seg.get(seg) == f)))
    return rows


def test_builder_happy_path_from_string_rows():
    rows = _grid({"A": 1.05, "B": 1.0, "C": 1.0})
    r = build_and_validate_from_rows(rows, ["A", "B", "C"])
    assert r["ok"], r["failures"]
    assert r["selection"] == {"A": 1.05, "B": 1.0, "C": 1.0}
    assert r["plan_hash"] == plan_hash({"A": 1.05, "B": 1.0, "C": 1.0})
    # 700 + 750 + 750
    assert r["totals"]["total_sales"] == 2200.0


def test_builder_rejects_string_truthiness_selected():
    # A malformed selected value must NOT be treated as selected (the reviewed bug).
    rows = _grid({"A": 1.0, "B": 1.0, "C": 1.0})
    for row in rows:
        if row["segment"] == "A" and row["factor"] == "1.05":
            row["selected"] = "maybe"   # not a boolean
    r = build_and_validate_from_rows(rows, ["A", "B", "C"])
    assert not r["ok"]
    assert any("boolean" in f.lower() or "recognised" in f.lower() for f in r["failures"])


def test_builder_rejects_duplicate_candidate_key():
    rows = _grid({"A": 1.0, "B": 1.0, "C": 1.0})
    rows.append(_row("A", 1.0, 999.0, 999.0, selected=False))  # duplicate (A,1.0)
    r = build_and_validate_from_rows(rows, ["A", "B", "C"])
    assert not r["ok"] and any("duplicate candidate key" in f for f in r["failures"])


def test_builder_rejects_duplicate_selection():
    rows = _grid({"A": 1.0, "B": 1.0, "C": 1.0})
    for row in rows:
        if row["segment"] == "A":
            row["selected"] = "true"   # both A candidates selected
    r = build_and_validate_from_rows(rows, ["A", "B", "C"])
    assert not r["ok"] and any("duplicate selections" in f for f in r["failures"])


def test_builder_rejects_segment_coverage_mismatch():
    rows = _grid({"A": 1.0, "B": 1.0, "C": 1.0})
    # Expected includes a segment D that has no selection.
    r = build_and_validate_from_rows(rows, ["A", "B", "C", "D"])
    assert not r["ok"] and any("coverage" in f for f in r["failures"])


def test_builder_rejects_empty_expected():
    r = build_and_validate_from_rows(_grid({"A": 1.0}), [])
    assert not r["ok"] and any("no expected segments" in f for f in r["failures"])


def test_builder_enforces_floor():
    rows = _grid({"A": 1.05, "B": 1.05, "C": 1.05})  # 700*3 = 2100
    r = build_and_validate_from_rows(rows, ["A", "B", "C"], min_portfolio_sales=2200)
    assert not r["ok"] and any("below the floor" in f for f in r["failures"])
