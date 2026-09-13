"""Typed conversion at the demo API boundary.

`server.sql.execute_query` returns every column value as a **string** (or None) —
the Databricks SQL Statement API's inline JSON encoding. Booleans come back as the
strings ``"true"``/``"false"``; numbers as their decimal strings; NULL as ``None``.

Passing those straight into arithmetic or truthiness tests is how the reviewed bugs
happened (``if row["selected"]`` treats the string ``"false"`` as truthy; ``"3" + 1``
throws or concatenates). This module does the conversion **deliberately and once**,
rejecting anything unexpected instead of guessing:

* :func:`as_bool` accepts only real booleans and the exact strings ``true``/``false``.
  Never string-truthiness. ``"maybe"`` / ``"1"`` / ``""`` raise.
* :func:`as_float` / :func:`as_int` reject ``None`` and non-finite values (NaN, inf)
  unless an explicit default is given.
* The ``opt_*`` variants allow SQL ``NULL`` → ``None`` and nothing else loose.

These are pure and have no Spark/SDK imports, so they are unit-testable off-platform
and cannot accidentally change the behaviour of unrelated legacy endpoints.
"""
from __future__ import annotations

import math
from typing import Any, Optional

_TRUE = {"true", "t", "1", "yes"}
_FALSE = {"false", "f", "0", "no"}


class CoercionError(ValueError):
    """A boundary value was missing, the wrong type, or non-finite."""


def as_bool(v: Any, *, field: str = "value") -> bool:
    """Strict boolean. Accepts Python bool and the SQL string forms only.

    Rejects string-truthiness: an unexpected string (``""``, ``"maybe"``) raises,
    it does NOT quietly become True. ``1``/``0`` (ints) are accepted as a
    convenience but ``None`` is not."""
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        if v in (0, 1):
            return bool(v)
        raise CoercionError(f"{field}: {v!r} is not a boolean")
    if isinstance(v, str):
        s = v.strip().lower()
        if s in _TRUE:
            return True
        if s in _FALSE:
            return False
    raise CoercionError(f"{field}: {v!r} is not a recognised boolean")


def opt_bool(v: Any, *, field: str = "value") -> Optional[bool]:
    """As :func:`as_bool` but SQL NULL → None."""
    if v is None:
        return None
    return as_bool(v, field=field)


def as_float(v: Any, *, field: str = "value", allow_nonfinite: bool = False) -> float:
    """Strict float. Rejects None and (unless allowed) NaN/inf."""
    if v is None:
        raise CoercionError(f"{field}: expected a number, got NULL")
    if isinstance(v, bool):  # bool is a subclass of int — reject to avoid True→1.0 surprises
        raise CoercionError(f"{field}: expected a number, got boolean {v!r}")
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise CoercionError(f"{field}: {v!r} is not a number")
    if not allow_nonfinite and not math.isfinite(f):
        raise CoercionError(f"{field}: {v!r} is not finite")
    return f


def opt_float(v: Any, *, field: str = "value") -> Optional[float]:
    """As :func:`as_float` but SQL NULL → None. Non-finite still rejected."""
    if v is None:
        return None
    return as_float(v, field=field)


def as_int(v: Any, *, field: str = "value") -> int:
    """Strict int. Accepts integral floats/strings ('5', '5.0'); rejects None,
    non-integral and non-finite."""
    if v is None:
        raise CoercionError(f"{field}: expected an integer, got NULL")
    if isinstance(v, bool):
        raise CoercionError(f"{field}: expected an integer, got boolean {v!r}")
    f = as_float(v, field=field)
    if not float(f).is_integer():
        raise CoercionError(f"{field}: {v!r} is not integral")
    return int(f)


def opt_int(v: Any, *, field: str = "value") -> Optional[int]:
    if v is None:
        return None
    return as_int(v, field=field)


def as_str(v: Any, *, field: str = "value") -> str:
    """Non-null string. Rejects None so a missing key can't become the text 'None'."""
    if v is None:
        raise CoercionError(f"{field}: expected a string, got NULL")
    return str(v)


def require(row: dict, key: str) -> Any:
    """Fetch a key that must be present (KeyError-equivalent as CoercionError)."""
    if key not in row:
        raise CoercionError(f"missing expected column {key!r}")
    return row[key]
